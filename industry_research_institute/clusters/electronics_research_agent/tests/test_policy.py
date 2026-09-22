from __future__ import annotations

import unittest

from electronics_research_agent.agents.roles import build_org
from electronics_research_agent.config import load_settings
from electronics_research_agent.policy.specs import policy_for


class TestPolicy(unittest.TestCase):
    def test_equipment_slice(self):
        card = policy_for("270100", "270108")
        self.assertTrue(card.sliced)
        self.assertEqual(card.spec_id, "sw2_270100__equipment")
        self.assertEqual(card.primary_chain[0], "EV_EBITDA")

    def test_packaging_slice(self):
        card = policy_for("270100", "270107")
        self.assertEqual(card.spec_id, "sw2_270100__packaging")

    def test_discrete_falls_back_to_l2(self):
        card = policy_for("270100", "270102")
        self.assertFalse(card.sliced)
        self.assertEqual(card.spec_id, "sw2_270100")
        self.assertEqual(card.primary_chain[0], "PE_TTM")
        self.assertIn("无独立切片", card.fallback_note)

    def test_e_chem_ev(self):
        card = policy_for("270600", "270601")
        self.assertEqual(card.spec_id, "sw2_270600")
        self.assertEqual(card.primary_chain[0], "EV_EBITDA")

    def test_org_active_slots(self):
        org = build_org(load_settings())
        self.assertEqual(org.chief.code, "270000")
        self.assertEqual(sum(1 for s in org.supervisors.values() if s.active), 3)
        self.assertEqual(sum(1 for s in org.researchers.values() if s.active), 7)
        self.assertEqual(len(org.supervisors), 6)
        self.assertEqual(len(org.researchers), 16)


if __name__ == "__main__":
    unittest.main()
