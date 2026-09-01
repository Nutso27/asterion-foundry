"""Integration tests for the game-loop wiring in src/main.py.

These tests import the `main` module directly. main.py's bottom-of-file
`main()` call is guarded by `if __name__ == "__main__":`, so importing it
here builds the starting `world` (research, ship classes, shipyard, labs,
penal code) without launching the interactive command loop or blocking on
input().

Each test resets relevant pieces of `world` in setUp so tests don't leak
state into each other, since `world` is a module-level singleton.

Run from the repository root with:
    python -m unittest tests/test_main_integration.py -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main as game  # noqa: E402
from research.lab_specialization import (  # noqa: E402
    PERPETUAL_CONSTRUCTION_OPTIMIZATION,
    PERPETUAL_RESEARCH_METHODOLOGY,
    PERPETUAL_UNIVERSAL_IMPROVEMENT,
)
from ship_design import ShipClass  # noqa: E402
from shipyard import Shipyard  # noqa: E402
from penal_code import PenalCode  # noqa: E402


def _pool_position(lane_id, tech_id):
    """1-based position of `tech_id` in a lane's current active pool."""
    pool = game.world["research"].active_pool[lane_id]
    return str(pool.index(tech_id) + 1)


class ShipDesignIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Fresh ship classes/stats for every test so completed-MK state
        # from one test never leaks into another.
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=[]),
        }
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200},
            "light_warship": {"combat_rating": 40},
        }
        state = game.world["research"]
        state.completed.discard("li_freighter_mk2_hull_design")
        state.completed.discard("md_light_warship_mk2_hull_design")
        state.rp_invested.pop("li_freighter_mk2_hull_design", None)
        state.rp_invested.pop("md_light_warship_mk2_hull_design", None)
        if "li_freighter_mk2_hull_design" not in state.active_pool["logistics_and_industry"]:
            state.active_pool["logistics_and_industry"].append("li_freighter_mk2_hull_design")
        if "md_light_warship_mk2_hull_design" not in state.active_pool["military_doctrine"]:
            state.active_pool["military_doctrine"].append("md_light_warship_mk2_hull_design")

    def test_completing_mk2_upgrades_class_and_registers_mk3(self):
        state = game.world["research"]
        state.rp_stockpile["logistics_and_industry"] = 1000.0
        pos = _pool_position("logistics_and_industry", "li_freighter_mk2_hull_design")

        game.handle_invest(["logistics_and_industry", pos])

        ship_class = game.world["ship_classes"]["freighter"]
        self.assertEqual(ship_class.current_mk, "Mark II")
        self.assertTrue(ship_class.retired_from_production)
        self.assertEqual(game.world["ship_class_stats"]["freighter"]["cargo_capacity"], 250)
        self.assertIn("freighter_mark_iii", state.active_pool["logistics_and_industry"])

    def test_cargo_effect_key_applies_exactly_once(self):
        """Regression test: the generic per-class effect loop and the MK
        node's own cargo multiplier key must not both apply the same
        completion's cargo bump.
        """
        state = game.world["research"]
        state.rp_stockpile["logistics_and_industry"] = 1000.0
        pos = _pool_position("logistics_and_industry", "li_freighter_mk2_hull_design")

        game.handle_invest(["logistics_and_industry", pos])

        # 200 * 1.25 = 250, rounded. If the effect applied twice this
        # would instead be 200 * 1.25 * 1.25 = 313 (rounded).
        self.assertEqual(game.world["ship_class_stats"]["freighter"]["cargo_capacity"], 250)

    def test_mk_progression_stops_at_mark_v(self):
        state = game.world["research"]
        lane = "logistics_and_industry"

        # Drive Mark I -> II -> III -> IV -> V.
        for _ in range(4):
            state.rp_stockpile[lane] = 1000.0
            pool = state.active_pool[lane]
            mk_node_id = next(t for t in pool if t == "li_freighter_mk2_hull_design" or t.startswith("freighter_mark_"))
            game.handle_invest([lane, str(pool.index(mk_node_id) + 1)])

        ship_class = game.world["ship_classes"]["freighter"]
        self.assertEqual(ship_class.current_mk, "Mark V")
        pool = state.active_pool[lane]
        self.assertFalse(any(t.startswith("freighter_mark_") for t in pool))

    def test_light_warship_mk2_upgrades_combat_rating(self):
        state = game.world["research"]
        state.rp_stockpile["military_doctrine"] = 1000.0
        pos = _pool_position("military_doctrine", "md_light_warship_mk2_hull_design")

        game.handle_invest(["military_doctrine", pos])

        ship_class = game.world["ship_classes"]["light_warship"]
        self.assertEqual(ship_class.current_mk, "Mark II")
        self.assertEqual(game.world["ship_class_stats"]["light_warship"]["combat_rating"], 52)


class ShipyardIntegrationTests(unittest.TestCase):
    def setUp(self):
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=[]),
        }
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200},
            "light_warship": {"combat_rating": 40},
        }
        game.world["shipyard"] = Shipyard(location="mars", slots_total=1, flexible=1)
        game.world["shipyard_slots"] = [
            {"locked_category": None, "building_class_id": None, "steps_remaining": 0}
        ]
        game.world["ships"] = {
            "csv_meridian": {
                "name": "CSV Meridian",
                "status": "idle_at_earth",
                "cargo_capacity": 200,
                "cargo_support_supplies": 0,
                "cargo_refined_metal": 0,
                "travel_remaining": 0,
                "class_id": "freighter",
                "mk": "Mark I",
            }
        }
        game.world["multipliers"] = {
            "construction_time_multiplier": 1.0,
            "research_time_multiplier": 1.0,
            "universal_efficiency_multiplier": 1.0,
        }
        game.world["locations"]["mars"]["refined_metal"] = 10  # below expansion reserve

    def test_free_slot_is_never_left_idle(self):
        game.update_shipyard()
        slot = game.world["shipyard_slots"][0]
        self.assertIsNotNone(slot["building_class_id"])
        self.assertGreater(slot["steps_remaining"], 0)

    def test_completed_build_spawns_ship_and_reassigns_slot(self):
        slot = game.world["shipyard_slots"][0]
        slot["building_class_id"] = "freighter"
        slot["steps_remaining"] = 1

        game.update_shipyard()

        self.assertEqual(len(game.world["ship_classes"]["freighter"].in_service), 2)
        self.assertEqual(len(game.world["ships"]), 2)
        # The freed slot must immediately pick up a new build (no idle).
        self.assertIsNotNone(slot["building_class_id"])

    def test_expansion_spends_metal_above_reserve_only(self):
        game.world["locations"]["mars"]["refined_metal"] = game.SHIPYARD_METAL_RESERVE + game.SLOT_EXPAND_COST
        game.update_shipyard()
        self.assertEqual(game.world["shipyard"].slots_total, 2)
        self.assertAlmostEqual(game.world["locations"]["mars"]["refined_metal"], game.SHIPYARD_METAL_RESERVE)


class LabSpecializationIntegrationTests(unittest.TestCase):
    def setUp(self):
        game.world["lab_roles"] = {"mars_collegium_lab": "flexible_auto_research"}
        game.world["multipliers"] = {
            "construction_time_multiplier": 1.0,
            "research_time_multiplier": 1.0,
            "universal_efficiency_multiplier": 1.0,
        }

    def test_tick_only_fires_on_interval_steps(self):
        game.world["lab_roles"]["lab2"] = PERPETUAL_CONSTRUCTION_OPTIMIZATION
        game.world["time"] = 3  # not a multiple of LAB_TICK_INTERVAL_STEPS (5)
        game.update_lab_specialization()
        self.assertEqual(game.world["multipliers"]["construction_time_multiplier"], 1.0)

        game.world["time"] = 5
        game.update_lab_specialization()
        self.assertLess(game.world["multipliers"]["construction_time_multiplier"], 1.0)

    def test_each_fixed_role_ticks_its_own_multiplier(self):
        game.world["lab_roles"]["lab2"] = PERPETUAL_CONSTRUCTION_OPTIMIZATION
        game.world["lab_roles"]["lab3"] = PERPETUAL_RESEARCH_METHODOLOGY
        game.world["lab_roles"]["lab4"] = PERPETUAL_UNIVERSAL_IMPROVEMENT
        game.world["time"] = 10

        game.update_lab_specialization()

        m = game.world["multipliers"]
        self.assertLess(m["construction_time_multiplier"], 1.0)
        self.assertLess(m["research_time_multiplier"], 1.0)
        self.assertLess(m["universal_efficiency_multiplier"], 1.0)

    def test_multiplier_never_crosses_floor(self):
        game.world["lab_roles"]["lab2"] = PERPETUAL_CONSTRUCTION_OPTIMIZATION
        game.world["multipliers"]["construction_time_multiplier"] = game.LAB_TICK_FLOOR
        game.world["time"] = 5

        game.update_lab_specialization()

        self.assertEqual(game.world["multipliers"]["construction_time_multiplier"], game.LAB_TICK_FLOOR)


class PenalCodeIntegrationTests(unittest.TestCase):
    def setUp(self):
        game.world["penal_code"] = PenalCode.default_code()
        game.world["penal_records"] = []

    def test_capital_charge_requires_confirmation_before_carrying_out(self):
        game.handle_charge(["subject_a", "treason_against_the_directorate"])
        record = game.world["penal_records"][-1]
        self.assertEqual(record["status"], "awaiting_confirmation")

        game.handle_confirm_servitor(["subject_a", "no", "yes"])
        self.assertEqual(record["status"], "awaiting_confirmation")  # still pending

        game.handle_confirm_servitor(["subject_a", "yes", "yes"])
        self.assertEqual(record["status"], "carried_out")

    def test_non_capital_charge_is_sentenced_immediately(self):
        game.handle_charge(["subject_b", "desertion_of_post"])
        record = game.world["penal_records"][-1]
        self.assertEqual(record["status"], "sentenced")

    def test_unknown_article_is_rejected_without_filing_a_record(self):
        game.handle_charge(["subject_c", "not_a_real_article"])
        self.assertEqual(len(game.world["penal_records"]), 0)


if __name__ == "__main__":
    unittest.main()
