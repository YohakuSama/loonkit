#!/usr/bin/env python3
"""Build the stable profile and inventory from one structured source model."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import profile_model
from loon_resources import ROOT, content_rules, pinned_uri, section
from release_checksums import check_public_checksums
from reviewed_release import records
from runtime_assets import check as check_runtime_assets
from source_lock import check_lock

VERSION = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)\Z")


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


def render(root: Path = ROOT, model: dict | None = None, spec: dict | None = None) -> bytes:
    model = profile_model.load(root) if model is None else model
    spec = load(root, "build/release_spec.json") if spec is None else spec
    return profile_model.render(model, spec["stable_release_version"])


def manifest_for(root: Path, profile: bytes, spec: dict, model: dict) -> dict:
    entries = records(profile, root)
    tags, matchers = defaultdict(list), defaultdict(set)
    for source, entry in zip(model["remote_rules"], entries):
        group = source["source_group"]
        tags[group].append(entry["tag"])
        matchers[group].update(content_rules((root / entry["path"]).read_bytes()))
    plugin_path = pinned_uri(model["plugins"][0])["path"]
    active = "\n".join(line for line in profile.decode().splitlines()
                       if line.strip() and not line.lstrip().startswith(("#", ";", "//"))) + "\n"
    count = sum(row["matcher_count"] for row in entries)
    manifest = {
        "schema_version": 2,
        "label": spec["stable_release_version"],
        "profile_sha256": {"LoonKit.lcf": sha256(profile)},
        "runtime_directives_sha256": sha256(active.encode()),
        "remote_subscription_count": len(entries),
        "remote_rule_count": count,
        "runtime_rule_matcher_count": count,
        "runtime_resources": entries,
        "source_group_tags": dict(tags),
        "source_group_counts": {group: len(values) for group, values in matchers.items()},
        "plugin_path": plugin_path,
        "plugin_sha256": sha256(path_under(root, plugin_path).read_bytes()),
        "service_roots": model["service_roots"],
        "device_test": "NOT_CLAIMED",
        "publication": {"status": "VERSIONED_RELEASE", "channel": "stable"},
    }
    if "previous_release" in spec:
        manifest["previous_release"] = spec["previous_release"]
    return manifest


def check(root: Path = ROOT, *, remote: bool = False) -> dict:
    spec = load(root, "build/release_spec.json")
    validate_spec(spec)
    model = profile_model.load(root)
    expected = render(root, model, spec)
    profile = (root / "LoonKit.lcf").read_bytes()
    if profile != expected:
        raise ValueError("production profile differs from structured source model")
    rules = [line.strip() for line in section(profile.decode(), "Rule").splitlines() if line.strip()]
    if not rules or rules[-1] != "FINAL,Final" or "GEOIP,CN,DIRECT,no-resolve" not in rules:
        raise ValueError("default fallback rules changed")
    manifest = load(root, "build/release_manifest.json")
    if manifest != manifest_for(root, profile, spec, model):
        raise ValueError("release inventory differs from structured source model or asset bytes")
    check_lock(root)
    assets = check_runtime_assets(root, remote=remote)
    check_public_checksums(root, manifest, spec)
    return {"version": spec["stable_release_version"], "profile_sha256": sha256(profile),
            "groups": len(model["groups"]), "resources": manifest["remote_subscription_count"],
            "matchers": manifest["remote_rule_count"], "runtime_assets": assets["assets"], "remote_checked": remote}


def json_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_spec(spec: dict) -> None:
    required = {"schema_version", "release_engine", "stable_release_version", "status", "historical_profile_sha256"}
    if (not isinstance(spec, dict) or not required <= spec.keys() or set(spec) - required - {"previous_release"}
            or spec["schema_version"] != 3 or spec["release_engine"] != "structured"
            or spec["status"] != "FORMAL_RELEASE" or not VERSION.fullmatch(str(spec["stable_release_version"]))
            or not isinstance(spec["historical_profile_sha256"], dict)):
        raise ValueError("unknown stable release specification")
    previous = spec.get("previous_release")
    if previous is not None and (not isinstance(previous, dict) or set(previous) != {"version", "profile_sha256"}
                                 or previous["version"] not in spec["historical_profile_sha256"]
                                 or previous["profile_sha256"] != spec["historical_profile_sha256"][previous["version"]]):
        raise ValueError("previous release differs from historical checksum ledger")


def build_outputs(root: Path, spec: dict, model: dict) -> tuple[dict[str, bytes], str]:
    validate_spec(spec)
    profile = render(root, model, spec)
    manifest = manifest_for(root, profile, spec, model)
    version, digest = spec["stable_release_version"], sha256(profile)
    return {
        "LoonKit.lcf": profile,
        "build/release_manifest.json": json_bytes(manifest),
        "build/release_spec.json": json_bytes(spec),
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
    outputs, digest = build_outputs(root, load(root, "build/release_spec.json"), profile_model.load(root))
    apply_outputs(root, outputs)
    return digest


def require_clean_git_checkout(root: Path) -> None:
    result = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=root, text=True, capture_output=True, check=True)
    if result.stdout.strip():
        raise ValueError("working tree is dirty; commit or stash edits before changing version")


def start_next(root: Path, target: str, *, require_clean: bool = True) -> str:
    if not VERSION.fullmatch(target):
        raise ValueError("expected version like v7.0.10")
    if require_clean:
        require_clean_git_checkout(root)
    check(root)
    spec = load(root, "build/release_spec.json")
    old = spec["stable_release_version"]
    if tuple(map(int, VERSION.fullmatch(target).groups())) <= tuple(map(int, VERSION.fullmatch(old).groups())):
        raise ValueError("next release version must increase")
    if target in spec["historical_profile_sha256"]:
        raise ValueError("next release version is already recorded")
    readme_path = root / "README.md"
    readme = readme_path.read_text() if readme_path.is_file() else None
    if readme is not None and readme.count("当前版本：**" + old + "**") != 1:
        raise ValueError("README version cannot be updated uniquely")
    old_digest = sha256((root / "LoonKit.lcf").read_bytes())
    spec["historical_profile_sha256"][old] = old_digest
    spec["previous_release"] = {"version": old, "profile_sha256": old_digest}
    spec["stable_release_version"] = target
    outputs, digest = build_outputs(root, spec, profile_model.load(root))
    if readme is not None:
        outputs["README.md"] = readme.replace(old, target).encode()
    notes = "docs/RELEASE_NOTES_" + target + ".md"
    if not (root / notes).exists():
        outputs[notes] = ("# LoonKit " + target + "\n\n使用当前结构化配置及固定资源构建。\n").encode()
    apply_outputs(root, outputs)
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--check", action="store_true")
    operation.add_argument("--write", action="store_true")
    operation.add_argument("--start-next", metavar="VERSION")
    parser.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check(remote=args.remote), sort_keys=True))
    elif args.remote:
        parser.error("--remote requires --check")
    elif args.write:
        print(write())
    else:
        print(start_next(ROOT, args.start_next))
