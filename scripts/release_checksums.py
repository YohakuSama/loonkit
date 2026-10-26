"""Independent, read-only public checksum and historical identity validation."""
import hashlib
from pathlib import Path
import re


def sha(content):
    return hashlib.sha256(content).hexdigest()


def check_public_checksums(root: Path, release: dict, spec: dict) -> str:
    """Read-only agreement check; never regenerate a release manifest or profile."""
    version = spec["stable_release_version"]
    digest = sha((root / "LoonKit.lcf").read_bytes())
    if release["label"] != version or release["profile_sha256"] != {"LoonKit.lcf": digest}:
        raise ValueError("published profile/manifest checksum or version mismatch")

    # The ledger retains historical identities without a document pair per release.
    # Historical pairs may still exist during a version bump; validate every pair
    # present, while always requiring the current release's public checksums.
    expected = {version: digest}
    for old, value in spec.get("historical_profile_sha256", {}).items():
        if (not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", old)
                or not re.fullmatch(r"[a-f0-9]{64}", value) or old == version):
            raise ValueError("invalid historical checksum identity")
        expected[old] = value
    docs = {p.name.removeprefix("RELEASE_CHECKSUM_").removesuffix(".md")
            for p in (root / "docs").glob("RELEASE_CHECKSUM_*.md")}
    sums = {p.name.removeprefix("SHA256SUMS.")
            for p in (root / "release").glob("SHA256SUMS.*")}
    if docs != sums or version not in docs or not docs <= expected.keys():
        raise ValueError("unexpected missing, stale or duplicate public checksum files")
    for ver in sorted(docs):
        value = expected[ver]
        doc_path = root / "docs" / ("RELEASE_CHECKSUM_" + ver + ".md")
        sums_path = root / "release" / ("SHA256SUMS." + ver)
        expected_line = value + "  LoonKit.lcf"
        if sums_path.read_text(encoding="utf-8") != expected_line + "\n":
            raise ValueError("release SHA256SUMS does not match pinned version " + ver)
        document = doc_path.read_text(encoding="utf-8")
        if (ver not in document or
                re.findall(r"(?m)^[0-9a-f]{64}  LoonKit\.lcf$", document) != [expected_line] or
                len(re.findall(r"\b[0-9a-f]{64}\b", document)) != 1):
            raise ValueError("release checksum documentation does not match pinned version " + ver)
    return digest


