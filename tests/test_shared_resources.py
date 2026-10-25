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

if __name__=="__main__":unittest.main()
