"""Rebuild the exact pinned beta routing snapshot with trusted main code.

Only data fetched from the beta base commit is used; no beta-branch Python is
ever executed by the privileged publisher. All local or fetched LSR bytes must
match the beta manifest before the routing oracle is constructed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from loon_resources import remote_entries
from route_diagnostics import Router

ROOT = Path(__file__).resolve().parents[1]
MAX_RESOURCE_BYTES = 8 * 1024 * 1024
MAX_RESOURCES = 128


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_router(client, base: str, profile: bytes, manifest: dict, *, root: Path = ROOT) -> Router:
    if manifest.get("schema_version") != 2:
        raise ValueError("beta publisher requires a schema-v2 pinned runtime manifest")
    declared = manifest.get("runtime_resources")
    if not isinstance(declared, list) or not 1 <= len(declared) <= MAX_RESOURCES:
        raise ValueError("beta resource inventory is missing or excessive")
    entries = remote_entries(profile.decode("utf-8"))
    if entries != [{k: r[k] for k in ("uri", "commit", "path", "policy", "tag", "enabled")}
                   for r in declared]:
        raise ValueError("beta profile and pinned resources disagree")
    with TemporaryDirectory(prefix="loonkit-beta-route-") as folder:
        snapshot = Path(folder)
        (snapshot / "LoonKit.lcf").write_bytes(profile)
        (snapshot / "build").mkdir()
        (snapshot / "build" / "release_manifest.json").write_text(
            json.dumps({"runtime_resources": declared}), encoding="utf-8")
        for entry, row in zip(entries, declared):
            rel = Path(row["path"])
            if (rel.is_absolute() or ".." in rel.parts or
                    not rel.parts or rel.parts[0] != "rules" or
                    not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64):
                raise ValueError("unsafe beta resource manifest path/hash")
            local = (root / rel).resolve()
            if not local.is_relative_to(root.resolve()):
                raise ValueError("beta resource escapes trusted checkout")
            # Reuse verified local bytes without a second disk read.
            local_bytes = local.read_bytes() if local.is_file() else None
            if local_bytes is not None and sha256(local_bytes) == row["sha256"]:
                raw = local_bytes
            else:
                raw = client.file(row["path"], row["commit"])
            if len(raw) > MAX_RESOURCE_BYTES or sha256(raw) != row["sha256"]:
                raise ValueError("beta resource hash mismatch: " + row["path"])
            destination = snapshot / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        return Router(snapshot)
