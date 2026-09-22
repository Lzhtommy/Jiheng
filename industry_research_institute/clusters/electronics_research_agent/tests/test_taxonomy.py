from __future__ import annotations

import unittest

from electronics_research_agent.taxonomy.map_stock import map_stock
from electronics_research_agent.taxonomy.sw import load_taxonomy
from electronics_research_agent.taxonomy.universe import load_universe


class TestTaxonomy(unittest.TestCase):
    def test_universe_size(self):
        stocks = load_universe()
        self.assertEqual(len(stocks), 17)
        self.assertEqual(len({s.stock_code for s in stocks}), 17)

    def test_map_universe_equipment(self):
        hit = map_stock("002371")
        self.assertTrue(hit.found)
        self.assertEqual(hit.stock_name, "北方华创")
        self.assertEqual(hit.l1_name, "电子")
        self.assertEqual(hit.l2_name, "半导体")
        self.assertEqual(hit.l3_name, "半导体设备")
        self.assertEqual(hit.l3_code, "270108")
        self.assertEqual(hit.source, "universe_v1")

    def test_map_universe_e_chem(self):
        hit = map_stock("300054.SZ")
        self.assertEqual(hit.l2_name, "电子化学品Ⅱ")
        self.assertEqual(hit.l3_name, "电子化学品Ⅲ")
        self.assertIn("3985", hit.class_sw_note)

    def test_map_members_fallback(self):
        tax = load_taxonomy()
        uni_codes = {s.stock_code for s in load_universe()}
        extra = next(code for code in tax.members if code not in uni_codes)
        hit = map_stock(extra, tax)
        self.assertTrue(hit.found)
        self.assertEqual(hit.source, "members_csv")
        self.assertEqual(hit.l1_code, "270000")

    def test_tree_counts(self):
        tax = load_taxonomy()
        self.assertEqual(len(tax.l1), 1)
        self.assertEqual(len(tax.l2), 6)
        self.assertEqual(len(tax.l3), 16)
        self.assertGreaterEqual(len(tax.members), 17)

    def test_all_universe_in_members(self):
        tax = load_taxonomy()
        for stock in load_universe():
            member = tax.members[stock.stock_code]
            self.assertEqual(member.l3_code, stock.l3_code, stock.stock_code)
            self.assertEqual(member.l2_code, stock.l2_code, stock.stock_code)


if __name__ == "__main__":
    unittest.main()
