"""Verify an owner-only duplicate cleanup against the complete archived release."""
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_upstream_703 import owner
from audit_v702 import lines

FIXES={
    "Our-Netflix": ("DOMAIN-SUFFIX,fast.com", "Speedtest", "Netflix"),
    "Our-TikTok": ("DOMAIN-SUFFIX,trae.ai", "AI", "TikTok"),
    "Our-ChinaDirect-Scoped": ("DOMAIN-SUFFIX,minimax.io", "AI", "DIRECT"),
}

class RuleOwnerCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=json.loads((ROOT/"build/baselines/generated/v7.0.4/release_manifest.json").read_text())
        cls.new=json.loads((ROOT/"build/release_manifest.json").read_text())
        cls.profile=(ROOT/"LoonKit.lcf").read_text(encoding="utf-8")

    def test_only_four_exact_rules_were_removed_from_three_resources(self):
        old_by_tag={r["tag"]:r for r in self.old["runtime_resources"]}
        removed={
            "Our-Netflix":["DOMAIN-SUFFIX,fast.com"],
            "Our-TikTok":["DOMAIN-SUFFIX,trae.ai"],
            "Our-ChinaDirect-Scoped":["DOMAIN-SUFFIX,minimax.io","DOMAIN-SUFFIX,z.ai"],
        }
        self.assertEqual([x["tag"] for x in self.old["runtime_resources"]],
                         [x["tag"] for x in self.new["runtime_resources"]])
        for row in self.new["runtime_resources"]:
            before=old_by_tag[row["tag"]]
            self.assertEqual(before["policy"],row["policy"])
            self.assertEqual(before["tag"],row["tag"])
            old_bytes=(ROOT/before["path"]).read_bytes()
            actual=(ROOT/row["path"]).read_bytes()
            for item in removed.get(row["tag"], []):
                needle=(item+"\n").encode()
                self.assertEqual(old_bytes.count(needle),1)
                old_bytes=old_bytes.replace(needle,b"",1)
            self.assertEqual(actual,old_bytes,row["tag"])
            self.assertEqual(row["matcher_count"],before["matcher_count"]-len(removed.get(row["tag"], [])))

    def test_owner_priorities_and_profile_except_pins_are_identical(self):
        rows=self.new["runtime_resources"]
        remote={r["path"]:lines((ROOT/r["path"]).read_bytes()) for r in rows}
        local=[line.strip() for line in self.profile.split("[Rule]\n",1)[1].split("\n[",1)[0].splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
        for host,policy in (("fast.com","Speedtest"),("trae.ai","AI"),
                            ("minimax.io","AI"),("z.ai","AI")):
            self.assertEqual(owner(host,remote,rows,local),policy,host)
        old=(ROOT/"build/baselines/generated/v7.0.4/LoonKit.lcf").read_text()
        version=self.new["label"]
        actual=self.profile.replace("# LoonKit "+version+"\n","# LoonKit v7.0.4\n",1)
        current_plugin=self.profile.split("[Plugin]\n",1)[1].split("\n[",1)[0]
        previous_plugin=old.split("[Plugin]\n",1)[1].split("\n[",1)[0]
        actual=actual.replace("[Plugin]\n"+current_plugin,
                              "[Plugin]\n"+previous_plugin,1)
        old_rows={r["tag"]:r for r in self.old["runtime_resources"]}
        for row in rows:
            actual=actual.replace(row["uri"],old_rows[row["tag"]]["uri"])
        self.assertEqual(actual,old)

if __name__=="__main__": unittest.main()
