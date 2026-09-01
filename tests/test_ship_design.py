"""Tests for ship design MK progression and retirement-from-production.

Run from the repository root with:
    python -m unittest tests/test_ship_design.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ship_design import (  # noqa: E402
    MkResearchProject,
    ShipClass,
    complete_mk_research,
    propose_new_hull_class,
)


class ShipClassTests(unittest.TestCase):
    def test_rejects_invalid_category(self):
        with self.assertRaises(ValueError):
            ShipClass(id="freighter", category="cosmetic")


class CompleteMkResearchTests(unittest.TestCase):
    def setUp(self):
        self.ship_class = ShipClass(
            id="freighter", category="logistics", in_service=["CSV Meridian", "CSV Concord"]
        )
        self.project = MkResearchProject(
            id="freighter_mk2",
            ship_class_id="freighter",
            from_mk="Mark I",
            to_mk="Mark II",
            effect="Improved cargo capacity and armor.",
        )

    def test_switches_current_mk_and_retires_previous(self):
        updated, _ = complete_mk_research(self.ship_class, self.project)
        self.assertEqual(updated.current_mk, "Mark II")
        self.assertTrue(updated.retired_from_production)

    def test_does_not_touch_in_service_hulls(self):
        updated, _ = complete_mk_research(self.ship_class, self.project)
        self.assertEqual(updated.in_service, ["CSV Meridian", "CSV Concord"])

    def test_self_renewing_returns_next_project(self):
        _, next_project = complete_mk_research(self.ship_class, self.project)
        self.assertIsNotNone(next_project)
        self.assertEqual(next_project.from_mk, "Mark II")
        self.assertEqual(next_project.to_mk, "Mark III")

    def test_no_next_project_past_end_of_sequence(self):
        top = ShipClass(id="freighter", category="logistics", current_mk="Mark V")
        top_project = MkResearchProject(
            id="x", ship_class_id="freighter", from_mk="Mark IV", to_mk="Mark V", effect=""
        )
        top.current_mk = "Mark IV"
        _, next_project = complete_mk_research(top, top_project)
        self.assertIsNone(next_project)

    def test_mismatched_class_raises(self):
        bad_project = MkResearchProject(
            id="x", ship_class_id="light_warship", from_mk="Mark I", to_mk="Mark II", effect=""
        )
        with self.assertRaises(ValueError):
            complete_mk_research(self.ship_class, bad_project)

    def test_wrong_starting_mk_raises(self):
        bad_project = MkResearchProject(
            id="x", ship_class_id="freighter", from_mk="Mark II", to_mk="Mark III", effect=""
        )
        with self.assertRaises(ValueError):
            complete_mk_research(self.ship_class, bad_project)


class ProposeNewHullClassTests(unittest.TestCase):
    def test_proposes_missing_category_only(self):
        classes = [ShipClass(id="freighter", category="logistics")]
        result = propose_new_hull_class(classes)
        self.assertEqual(result, "new_warship_class_study")

    def test_no_proposal_when_both_categories_present(self):
        classes = [
            ShipClass(id="freighter", category="logistics"),
            ShipClass(id="light_warship", category="warship"),
        ]
        self.assertIsNone(propose_new_hull_class(classes))


if __name__ == "__main__":
    unittest.main()
