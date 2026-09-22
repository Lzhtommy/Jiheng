from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from electronics_research_agent.orchestrator.dispatch import group_universe_by_l3
from electronics_research_agent.orchestrator.run import main, run_research
from electronics_research_agent.taxonomy.universe import load_universe


class TestDispatch(unittest.TestCase):
    def test_group_l3(self):
        grouped = group_universe_by_l3()
        self.assertEqual(len(grouped["270202"]), 4)
        self.assertEqual(len(grouped["270108"]), 2)
        self.assertEqual(len(grouped["270601"]), 3)
        self.assertEqual(sum(len(v) for v in grouped.values()), 17)

    def test_run_no_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = run_research("2099-01-01", out_dir=Path(tmp) / "out", use_db=False)
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["universe_size"], 17)
            self.assertFalse(manifest["db_used"])
            self.assertEqual(len(manifest["l3_written"]), 16)
            self.assertEqual(len(manifest["l2_written"]), 6)
            brief = (dest / "l1" / "brief.md").read_text(encoding="utf-8")
            self.assertIn("电子", brief)
            note = (dest / "l3" / "270108" / "note.md").read_text(encoding="utf-8")
            self.assertIn("北方华创", note)
            self.assertIn("长川科技", note)
            echem = json.loads((dest / "l3" / "270601" / "note.json").read_text(encoding="utf-8"))
            self.assertEqual(len(echem["companies"]), 3)
            stub = json.loads((dest / "l3" / "270104" / "note.json").read_text(encoding="utf-8"))
            self.assertEqual(stub["companies"], [])
            self.assertFalse(stub["active"])

    def test_cli_map(self):
        rc = main(["map", "--codes", "002371,300054"])
        self.assertEqual(rc, 0)

    def test_cli_universe_count(self):
        self.assertEqual(len(load_universe()), 17)


if __name__ == "__main__":
    unittest.main()
