#!/usr/bin/env python3
"""Version-neutral LoonKit release renderer and verifier.

A checked-in, SHA256-pinned base plus explicit one-occurrence edits produce the
exact published profile. No network dependency during rendering or version bump.
The full historical archive remains available via immutable Git tags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECIPE = "build/release_recipe.json"
VERSION = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)\Z")
HEADER = re.compile(r"\A# LoonKit v[0-9]+\.[0-9]+\.[0-9]+\n")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(root: Path, name: str) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def path_under(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("invalid relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("path escapes repository")
    return path


def render(root: Path = ROOT, recipe: dict | None = None, *, base_bytes: bytes | None = None) -> bytes:
    recipe = recipe if recipe is not None else load(root, RECIPE)
    if recipe.get("schema_version") != 1 or not VERSION.fullmatch(str(recipe.get("target_version", ""))):
        raise ValueError("invalid release recipe version")
    base = recipe.get("base")
    if not isinstance(base, dict) or not DIGEST.fullmatch(str(base.get("sha256", ""))):
        raise ValueError("missing pinned base checksum")
    source = path_under(root, base.get("path"))
    source_bytes = source.read_bytes() if base_bytes is None else base_bytes
    if sha256(source_bytes) != base["sha256"]:
        raise ValueError("pinned profile baseline changed")
    text = source_bytes.decode("utf-8")
    if not HEADER.match(text):
        raise ValueError("unsupported baseline header")
    text = HEADER.sub("# LoonKit " + recipe["target_version"] + "\n", text, count=1)
    patches = recipe.get("changes")
    if not isinstance(patches, list) or len(patches) > 200:
        raise ValueError("release changes must be a bounded list")
    for i, patch in enumerate(patches):
        if not isinstance(patch, dict) or set(patch) != {"find", "replace"}:
            raise ValueError("invalid change entry " + str(i))
        old, new = patch["find"], patch["replace"]
        if not isinstance(old, str) or not old or not isinstance(new, str) or old == new:
            raise ValueError("invalid or no-op change " + str(i))
        if text.count(old) != 1:
            raise ValueError("change anchor missing or ambiguous: " + str(i))
        text = text.replace(old, new, 1)
    return text.encode("utf-8")


def section(profile: str, name: str) -> list[str]:
    marker = "[" + name + "]\n"
    if profile.count(marker) != 1:
        raise ValueError("missing or ambiguous profile section: " + name)
    tail = profile.split(marker, 1)[1].split("\n[", 1)[0]
    return [line.strip() for line in tail.splitlines() if line.strip() and not line.lstrip().startswith(("#", ";", "//"))]


def check(root: Path = ROOT, *, remote: bool = False) -> dict:
    # Imports here avoid a circular dependency: verify_release dispatches to us,
    # while its stable checksum verifier remains the single compatibility gate.
    from reviewed_release import validate_records
    from verify_release import check_public_checksums
    from source_lock import check_lock

    spec = load(root, "build/release_spec.json")
    manifest = load(root, "build/release_manifest.json")
    recipe = load(root, RECIPE)
    version = recipe["target_version"]
    if (spec.get("release_engine") != "generic" or
            spec.get("stable_release_version") != version or
            manifest.get("label") != version):
        raise ValueError("release versions or engine configuration disagree")
    rendered = render(root, recipe)
    actual = (root / "LoonKit.lcf").read_bytes()
    if rendered != actual:
        raise ValueError("production profile differs from pinned declarative build")
    digest = sha256(actual)
    if manifest.get("profile_sha256") != {"LoonKit.lcf": digest}:
        raise ValueError("profile manifest digest differs")
    text = actual.decode("utf-8")
    groups = section(text, "Proxy Group")
    names = [line.split("=", 1)[0].strip() for line in groups]
    if any("=" not in line for line in groups) or len(names) != len(set(names)):
        raise ValueError("invalid or duplicate proxy group")
    rules = section(text, "Rule")
    if not rules or rules[-1] != "FINAL,Final" or "GEOIP,CN,DIRECT,no-resolve" not in rules:
        raise ValueError("default fallback rules changed")
    resources = manifest.get("runtime_resources")
    if not isinstance(resources, list) or not resources:
        raise ValueError("missing runtime resource manifest")
    pin = spec.get("release_assets_commit")
    if not re.fullmatch(r"[a-f0-9]{40}", str(pin)):
        raise ValueError("release assets must be pinned")
    if any(row.get("commit") != pin or not row.get("path", "").startswith("rules/releases/")
           or not row.get("path", "").endswith(".lsr") for row in resources):
        raise ValueError("remote rule asset escaped pinned release")
    entries = validate_records(actual, resources, root, remote=remote)
    if (len(entries) != manifest.get("remote_subscription_count") or
            sum(row["matcher_count"] for row in entries) != manifest.get("remote_rule_count") or
            manifest.get("remote_rule_count") != manifest.get("runtime_rule_matcher_count")):
        raise ValueError("runtime rule counts or owners differ")
    if len(set(row["tag"] for row in entries)) != len(entries):
        raise ValueError("duplicate remote rule tag")
    known_policies = set(names) | {"DIRECT", "REJECT"}
    if any(row["policy"] not in known_policies for row in entries):
        raise ValueError("subscription refers to an undeclared policy group")
    plugin = path_under(root, manifest["plugin_path"]).read_bytes()
    if sha256(plugin) != manifest["plugin_sha256"]:
        raise ValueError("plugin checksum differs")
    gate_path = spec.get("release_gate_file")
    if gate_path:
        gate = load(root, gate_path)
        if gate.get("version") != version or gate.get("release_profile_sha256") != digest:
            raise ValueError("release decision doesn't match profile")
    check_lock(root)
    check_public_checksums(root, manifest, spec)
    return {"version": version, "profile_sha256": digest, "groups": len(groups),
            "resources": len(entries), "matchers": manifest["remote_rule_count"],
            "remote_checked": remote}


def json_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_outputs(root: Path, spec: dict, manifest: dict, recipe: dict,
                  *, base_bytes: bytes | None = None) -> tuple[dict[str, bytes], str]:
    if spec.get("release_engine") != "generic" or recipe["target_version"] != spec["stable_release_version"]:
        raise ValueError("recipe/spec mismatch")
    profile = render(root, recipe, base_bytes=base_bytes)
    digest = sha256(profile)
    version = recipe["target_version"]
    manifest["label"] = version
    manifest["profile_sha256"] = {"LoonKit.lcf": digest}
    manifest["reviewed_recipe"] = RECIPE
    manifest["runtime_change"] = {
        "version": version,
        "runtime_semantics": "EXPLICIT_DECLARATIVE_RECIPE",
        "recipe_change_count": len(recipe["changes"]),
    }
    active = "\n".join(line for line in profile.decode("utf-8").splitlines()
                       if line.strip() and not line.lstrip().startswith("#")) + "\n"
    spec["current_runtime_directives_sha256"] = sha256(active.encode("utf-8"))
    return {
        "LoonKit.lcf": profile,
        "build/release_manifest.json": json_bytes(manifest),
        "build/release_spec.json": json_bytes(spec),
        RECIPE: json_bytes(recipe),
        "release/SHA256SUMS." + version: (digest + "  LoonKit.lcf\n").encode(),
        "docs/RELEASE_CHECKSUM_" + version + ".md":
            ("# " + version + " profile SHA256\n\n" + digest + "  LoonKit.lcf\n").encode(),
    }, digest


def apply_outputs(root: Path, outputs: dict[str, bytes]) -> None:
    """Stage all outputs, then replace with rollback on an ordinary I/O failure.

    A multi-file update is NOT crash-atomic; fail-fast validation and rollback
    protect normal exceptions, and clean Git commits are the publication unit.
    """
    staged: list[tuple[Path, Path, Path | None]] = []
    installed: list[tuple[Path, Path | None]] = []

    def temp_copy(target: Path, data: bytes) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, name = tempfile.mkstemp(prefix=".loonkit-stage-", dir=target.parent)
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return Path(name)

    try:
        for name, body in sorted(outputs.items()):
            if not isinstance(body, bytes):
                raise ValueError("non-byte output: " + name)
            target = path_under(root, name)
            if target.exists() and not target.is_file():
                raise ValueError("output is not a file: " + name)
            backup = temp_copy(target, target.read_bytes()) if target.exists() else None
            staged.append((target, temp_copy(target, body), backup))
        for target, staged_path, backup in staged:
            os.replace(staged_path, target)
            installed.append((target, backup))
    except Exception:
        for target, backup in reversed(installed):
            if backup is None:
                target.unlink(missing_ok=True)
            else:
                os.replace(backup, target)
        raise
    finally:
        for target, new_path, backup in staged:
            new_path.unlink(missing_ok=True)
            if backup is not None:
                backup.unlink(missing_ok=True)


def write(root: Path = ROOT) -> str:
    spec = load(root, "build/release_spec.json")
    manifest = load(root, "build/release_manifest.json")
    recipe = load(root, RECIPE)
    outputs, digest = build_outputs(root, spec, manifest, recipe)
    apply_outputs(root, outputs)
    return digest


def require_clean_git_checkout(root: Path) -> None:
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=root, text=True, capture_output=True, check=True)
    if result.stdout.strip():
        raise ValueError("working tree is dirty; commit or stash edits before changing version")


def start_next(root: Path, target: str, *, require_clean: bool = True) -> str:
    if not VERSION.fullmatch(target):
        raise ValueError("expected version like v7.0.5")
    if require_clean:
        require_clean_git_checkout(root)
    check(root)
    spec = load(root, "build/release_spec.json")
    old = spec["stable_release_version"]
    if tuple(map(int, VERSION.fullmatch(target).groups())) <= tuple(map(int, VERSION.fullmatch(old).groups())):
        raise ValueError("next release version must increase")
    current = (root / "LoonKit.lcf").read_bytes()
    frozen_path = "build/baselines/generated/" + old + "/LoonKit.lcf"
    archived = path_under(root, frozen_path)
    if archived.exists() and archived.read_bytes() != current:
        raise ValueError("existing historical snapshot differs: " + old)

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None
    if readme is not None and readme.count("当前版本：**" + old + "**") != 1:
        raise ValueError("README version cannot be updated uniquely")

    old_digest = sha256(current)
    spec.setdefault("historical_profile_sha256", {})[old] = old_digest
    spec["previous_formal_profile_sha256"] = old_digest
    spec["previous_formal_profile_path"] = frozen_path
    spec["stable_release_version"] = target
    # A new release must not inherit a prior release's personal attestations.
    spec["release_gate_file"] = None
    manifest = load(root, "build/release_manifest.json")
    manifest["previous_release"] = {"version": old, "profile_sha256": old_digest}
    recipe = {"schema_version": 1, "target_version": target,
              "base": {"path": frozen_path, "sha256": old_digest},
              "changes": []}
    outputs, digest = build_outputs(root, spec, manifest, recipe, base_bytes=current)
    outputs[frozen_path] = current
    if readme is not None:
        outputs["README.md"] = readme.replace(
            "当前版本：**" + old + "**", "当前版本：**" + target + "**", 1).encode("utf-8")
    apply_outputs(root, outputs)
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true", help="render profile and regenerate its checksums")
    group.add_argument("--start-next", metavar="VERSION", help="start a new release without a version-specific script")
    parser.add_argument("--remote", action="store_true", help="check exact pinned upstream bytes")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(remote=args.remote), sort_keys=True))
    elif args.write:
        if args.remote:
            parser.error("--remote works only with --check")
        print(write())
    else:
        if args.remote:
            parser.error("--remote works only with --check")
        print(start_next(ROOT, args.start_next))


if __name__ == "__main__":
    main()
