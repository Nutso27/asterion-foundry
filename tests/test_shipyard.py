"""Tests for shipyard slot expansion and no-idle rotation.

Run from the repository root with:
    python -m unittest tests/test_shipyard.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shipyard import LOGISTICS, WARSHIP, Shipyard, expand, next_build_assignment  # noqa: E402


class ExpandTests(unittest.TestCase):
    def test_fills_warship_minimum_first(self):
        yard = Shipyard(location="mars", slots_total=1)
        yard, added, spent = expand(yard, available_refined_metal=1000, cost_per_slot=10, batch_size=3)
        self.assertEqual(added, 3)
        self.assertEqual(yard.warship_locked, 3)
        self.assertEqual(yard.logistics_locked, 0)
        self.assertEqual(yard.flexible, 0)
        self.assertEqual(spent, 30)

    def test_fills_logistics_minimum_after_warship(self):
        yard = Shipyard(location="mars", slots_total=1, warship_locked=5)
        yard, added, _ = expand(yard, available_refined_metal=1000, cost_per_slot=10, batch_size=3)
        self.assertEqual(yard.logistics_locked, 3)
        self.assertEqual(yard.flexible, 0)

    def test_overflow_goes_flexible(self):
        yard = Shipyard(location="mars", slots_total=1, warship_locked=5, logistics_locked=5)
        yard, added, _ = expand(yard, available_refined_metal=1000, cost_per_slot=10, batch_size=3)
        self.assertEqual(yard.flexible, 3)

    def test_never_exceeds_target_minimum(self):
        yard = Shipyard(location="mars", slots_total=99, target_minimum=100)
        yard, added, _ = expand(yard, available_refined_metal=10000, cost_per_slot=1, batch_size=3)
        self.assertEqual(added, 1)
        self.assertEqual(yard.slots_total, 100)

    def test_stops_when_out_of_metal(self):
        yard = Shipyard(location="mars", slots_total=1)
        yard, added, spent = expand(yard, available_refined_metal=15, cost_per_slot=10, batch_size=3)
        self.assertEqual(added, 1)
        self.assertEqual(spent, 10)


class NextBuildAssignmentTests(unittest.TestCase):
    def test_single_category_slot_just_builds_its_category(self):
        result = next_build_assignment(
            allowed_categories=[WARSHIP], fleet_counts={}, demand_counts={}
        )
        self.assertEqual(result, WARSHIP)

    def test_flexible_slot_avoids_surplus_category(self):
        result = next_build_assignment(
            allowed_categories=[WARSHIP, LOGISTICS],
            fleet_counts={WARSHIP: 10, LOGISTICS: 1},
            demand_counts={WARSHIP: 2, LOGISTICS: 2},
        )
        self.assertEqual(result, LOGISTICS)

    def test_flexible_slot_falls_back_when_all_surplus(self):
        result = next_build_assignment(
            allowed_categories=[WARSHIP, LOGISTICS],
            fleet_counts={WARSHIP: 20, LOGISTICS: 10},
            demand_counts={WARSHIP: 2, LOGISTICS: 2},
        )
        self.assertEqual(result, LOGISTICS)


if __name__ == "__main__":
    unittest.main()
