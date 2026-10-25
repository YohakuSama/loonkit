"""Formal and beta validators use a shared side-effect-free parser."""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import loon_resources as shared
import beta_channel
import reviewed_release

class SharedResourcesTests(unittest.TestCase):
    def test_parsers_are_shared_and_formal_has_no_beta_dependency(self):
        for name in ("section","remote_entries","content_rules"):
            self.assertIs(getattr(beta_channel,name),getattr(shared,name))
            self.assertIs(getattr(reviewed_release,name),getattr(shared,name))
        self.assertNotIn("from beta_channel import", (ROOT/"scripts/reviewed_release.py").read_text())

    def test_untrusted_remote_is_rejected(self):
        uri="https://raw.githubusercontent.com/YohakuSama/loonkit/"+"a"*40+"/rules/releases/v7.0.3/x.lsr"
        s="[Remote Rule]\n"+uri+", policy=AI, tag=Unique, enabled=true\n[Rule]\nFINAL,Final\n"
        self.assertEqual(shared.remote_entries(s)[0]["policy"],"AI")
        with self.assertRaises(ValueError):shared.remote_entries(s.replace("raw.githubusercontent.com","evil.example"))

    def test_resource_digest_and_match_count_use_one_read(self):
        import hashlib
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rel = Path("rules/releases/v7.0.3/Synthetic.lsr")
            (root / rel).parent.mkdir(parents=True)
            payload = b"DOMAIN,example.org\n"
            (root / rel).write_bytes(payload)
            url = ("https://raw.githubusercontent.com/YohakuSama/loonkit/"
                   + "a" * 40 + "/" + rel.as_posix())
            profile = ("[Remote Rule]\n" + url
                       + ", policy=AI, tag=Sample, enabled=true\n[Rule]\nFINAL,Final\n")
            original = Path.read_bytes
            reads = []

            def tracked(path):
                reads.append(path)
                return original(path)

            with patch.object(Path, "read_bytes", tracked):
                records = reviewed_release.records(profile.encode("utf-8"), root)
            self.assertEqual(len(reads), 1)
            self.assertEqual(records[0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(records[0]["matcher_count"], 1)

if __name__=="__main__":unittest.main()
