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

import json
import os
import shutil
import sys
import tempfile
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

        # Strip any dynamically-registered MK-successor node a previous
        # test's _register_next_mk_node() call left behind. world["research"]
        # is a module-level singleton, so without this, a stray successor
        # node from an earlier test (e.g. "freighter_mark_iii") can get
        # drawn into *this* test's pool -- refresh_draw_pool()'s RNG is
        # unseeded -- and shift which node ends up at a given pool
        # position. This was the confirmed root cause of a real flaky
        # failure in test_mk_progression_stops_at_mark_v (~1 in 4-6 full
        # -suite runs); verified fixed by running the full suite 30 times
        # after this change with zero failures, versus reproducing the
        # failure repeatedly before it.
        dynamic_ids = [
            nid for nid in list(state.nodes)
            if nid.startswith("freighter_mark_") or nid.startswith("light_warship_mark_")
        ]
        for nid in dynamic_ids:
            state.nodes.pop(nid, None)
            state.completed.discard(nid)
            state.rp_invested.pop(nid, None)
        for lane_id, pool in state.active_pool.items():
            state.active_pool[lane_id] = [t for t in pool if t not in dynamic_ids]

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

    def test_the_newly_registered_mk_node_is_never_dropped_across_many_trials(self):
        """Regression test for a real bug found and fixed 2026-09-04:
        handle_invest() registers the MK successor node into the pool
        (_register_next_mk_node()) and then immediately calls
        refresh_draw_pool() to see if completing this node opened up
        anything else -- but that refresh used to do a full unweighted
        re-draw with no protection for the node it had JUST added, so it
        competed on equal footing with every other eligible candidate and
        could be silently dropped despite the player having just been
        told "New research now available." (Independently confirmed at
        roughly 1 in 6 trials before the fix.) The single-shot test above
        already asserts this, but with an unseeded internal RNG
        (refresh_draw_pool's default `rng=random.Random()`) that
        assertion alone had real per-run flake risk; running it many
        times here makes that risk visible instead of silently passing
        6 times out of 7.
        """
        for trial in range(25):
            self.setUp()  # fresh ship_classes/research state each trial
            state = game.world["research"]
            state.rp_stockpile["logistics_and_industry"] = 1000.0
            pos = _pool_position("logistics_and_industry", "li_freighter_mk2_hull_design")

            game.handle_invest(["logistics_and_industry", pos])

            self.assertIn(
                "freighter_mark_iii", state.active_pool["logistics_and_industry"],
                f"dropped on trial {trial}",
            )

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

    def test_in_progress_builds_count_toward_fleet_target_not_just_in_service(self):
        """Regression test for a real bug: fleet_counts used to be seeded
        from in_service counts ALONE, so a build already in flight from a
        prior step (a slot with building_class_id still set) was
        invisible to the FLEET_TARGET check -- every other free slot
        could each start ANOTHER build of the same class without any of
        them seeing each other's pending work, overshooting the cap once
        they all completed. Confirmed independently with a 400-step
        advance_world() run from a fresh game (light_warship reached 11
        in_service against a target of 10).

        Setup: FLEET_TARGET["freighter"]=6, 4 already in_service, one
        slot already mid-build (not completing this step) -- so only 1
        more freighter should ever be startable (4 + 1 in-flight + 1 new
        = 6, the target), not 3 more from the 3 free slots available.
        """
        game.world["ship_classes"]["freighter"].in_service = ["Hull A", "Hull B", "Hull C", "Hull D"]
        game.world["locations"]["mars"]["refined_metal"] = 10  # below expansion reserve -- isolate to step 3
        game.world["shipyard_slots"] = [
            {"locked_category": "logistics", "building_class_id": "freighter", "steps_remaining": 5},
            {"locked_category": "logistics", "building_class_id": None, "steps_remaining": 0},
            {"locked_category": "logistics", "building_class_id": None, "steps_remaining": 0},
            {"locked_category": "logistics", "building_class_id": None, "steps_remaining": 0},
        ]

        game.update_shipyard()

        free_slots_now_building = sum(
            1 for slot in game.world["shipyard_slots"][1:] if slot["building_class_id"] is not None
        )
        self.assertEqual(free_slots_now_building, 1, "should start exactly 1 new build, not 3")

    def test_a_fresh_game_never_overshoots_fleet_target_over_many_steps(self):
        """End-to-end version of the bug above: run update_shipyard() for
        many steps from a fresh, realistic starting shipyard and confirm
        in_service never exceeds FLEET_TARGET for either class -- this is
        the actual player-visible symptom the unit test above targets
        directly.
        """
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian", "CSV Concord"]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=["LWS Vigilant"]),
        }
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200},
            "light_warship": {"combat_rating": 40},
        }
        game.world["shipyard"] = Shipyard(
            location="mars", slots_total=1, flexible=1, target_minimum=game.SHIPYARD_TARGET_MINIMUM
        )
        game.world["shipyard_slots"] = [
            {"locked_category": None, "building_class_id": None, "steps_remaining": 0}
        ]
        game.world["ships"] = {}

        for _ in range(400):
            game.world["locations"]["mars"]["refined_metal"] = 100000  # never metal-constrained
            game.update_shipyard()

        freighters = len(game.world["ship_classes"]["freighter"].in_service)
        light_warships = len(game.world["ship_classes"]["light_warship"].in_service)
        self.assertLessEqual(freighters, game.FLEET_TARGET["freighter"])
        self.assertLessEqual(light_warships, game.FLEET_TARGET["light_warship"])


class ShipyardTargetMinimumIntegrationTests(unittest.TestCase):
    """Regression tests for a real bug: Shipyard.target_minimum defaulted
    to 100, a number picked before FLEET_TARGET (the 16-hull fleet cap)
    existed and never reconciled with it. With no combat/hull-loss
    mechanic, in_service counts only ever grow toward FLEET_TARGET and
    then stay there -- so every slot above what's needed to reach
    FLEET_TARGET was guaranteed to sit permanently idle while expand()
    kept spending Mars's refined metal toward 100 regardless. Fixed
    2026-09-04 by introducing SHIPYARD_TARGET_MINIMUM = sum(FLEET_TARGET
    .values()) and passing it explicitly in build_ship_and_facility_state().
    """

    def test_shipyard_target_minimum_matches_fleet_target_total(self):
        self.assertEqual(game.SHIPYARD_TARGET_MINIMUM, sum(game.FLEET_TARGET.values()))
        self.assertNotEqual(game.SHIPYARD_TARGET_MINIMUM, 100)

    def test_new_game_shipyard_is_built_with_the_reconciled_target(self):
        game.build_ship_and_facility_state()
        self.assertEqual(game.world["shipyard"].target_minimum, game.SHIPYARD_TARGET_MINIMUM)

    def test_expansion_never_grows_past_the_fleet_target_total(self):
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=[]),
        }
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200},
            "light_warship": {"combat_rating": 40},
        }
        game.world["shipyard"] = Shipyard(
            location="mars", slots_total=1, flexible=1, target_minimum=game.SHIPYARD_TARGET_MINIMUM
        )
        game.world["shipyard_slots"] = [
            {"locked_category": None, "building_class_id": None, "steps_remaining": 0}
        ]
        game.world["ships"] = {}
        game.world["multipliers"] = {
            "construction_time_multiplier": 1.0,
            "research_time_multiplier": 1.0,
            "universal_efficiency_multiplier": 1.0,
        }
        # Effectively unlimited metal -- expansion should still stop at
        # SHIPYARD_TARGET_MINIMUM, not keep growing toward the old 100.
        for _ in range(200):
            game.world["locations"]["mars"]["refined_metal"] = 100000
            game.update_shipyard()
        self.assertEqual(game.world["shipyard"].slots_total, game.SHIPYARD_TARGET_MINIMUM)
        self.assertLess(game.world["shipyard"].slots_total, 100)


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

    def test_reprimand_charge_is_sentenced_immediately(self):
        # insubordination_under_command's typical sentence is Reprimand and
        # Restitution -- the one tier with no fixed term and no labor-
        # economy effect (see PenalLaborEconomyIntegrationTests for
        # desertion_of_post/Toil Legion and sabotage/Penal Legion, which
        # get "serving" instead as of the 2026-09-05 labor-economy wiring).
        game.handle_charge(["subject_b", "insubordination_under_command"])
        record = game.world["penal_records"][-1]
        self.assertEqual(record["status"], "sentenced")

    def test_unknown_article_is_rejected_without_filing_a_record(self):
        game.handle_charge(["subject_c", "not_a_real_article"])
        self.assertEqual(len(game.world["penal_records"]), 0)


class EarthEconomyIntegrationTests(unittest.TestCase):
    """Covers the 2026-09-04 fix: Earth's support_supplies used to be a
    pure one-way drain (freighter pickup, outpost seeding) with nothing
    anywhere producing more of it. update_earth() now adds a flat trickle
    each step, and CSV Meridian's Earth-side pickup respects a reserve
    floor the same way its Mars-side metal pickup already did.
    """

    def setUp(self):
        world_locations = game.world["locations"]
        world_locations["earth"]["support_supplies"] = 1000.0
        # Full replacement, not just setting "csv_meridian" -- world["ships"]
        # is a module-level singleton, and update_freighters() (2026-09-04)
        # now loops over every freighter in it. Without this, a leftover
        # "csv_concord" or shipyard-built freighter from another test class
        # (which may run before or after this one -- unittest doesn't
        # guarantee file order across classes) could also pick up cargo in
        # the same update_freighters() call and throw off these exact-value
        # assertions on Earth's stockpile.
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

    def test_update_earth_adds_the_production_trickle(self):
        before = game.world["locations"]["earth"]["support_supplies"]
        game.update_earth()
        after = game.world["locations"]["earth"]["support_supplies"]
        self.assertAlmostEqual(after - before, game.EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP)

    def test_freighter_pickup_never_drains_earth_below_its_reserve(self):
        # Earth starts well above the reserve, with less on hand than the
        # ship could carry -- the ship should stop at the reserve floor,
        # not empty Earth out just because it has cargo room to spare.
        game.world["locations"]["earth"]["support_supplies"] = (
            game.EARTH_SUPPORT_SUPPLIES_RESERVE + 50.0
        )
        game.update_freighters()
        self.assertAlmostEqual(
            game.world["locations"]["earth"]["support_supplies"],
            game.EARTH_SUPPORT_SUPPLIES_RESERVE,
        )
        self.assertAlmostEqual(game.world["ships"]["csv_meridian"]["cargo_support_supplies"], 50.0)

    def test_freighter_takes_nothing_when_earth_is_at_or_below_reserve(self):
        game.world["locations"]["earth"]["support_supplies"] = game.EARTH_SUPPORT_SUPPLIES_RESERVE
        game.update_freighters()
        self.assertEqual(game.world["ships"]["csv_meridian"]["cargo_support_supplies"], 0)
        self.assertAlmostEqual(
            game.world["locations"]["earth"]["support_supplies"],
            game.EARTH_SUPPORT_SUPPLIES_RESERVE,
        )


class FreighterLoopIntegrationTests(unittest.TestCase):
    """Regression tests for a real bug found and fixed 2026-09-04:
    update_csv_meridian() (now update_freighters()) was hardcoded to
    world["ships"]["csv_meridian"] alone. CSV Concord -- a second
    freighter present since the very start of the game -- and every
    freighter the shipyard built afterward sat "idle_at_mars" forever,
    never actually touched by any update function. show_status() had
    the identical bug (only ever printed CSV Meridian's line).
    """

    def setUp(self):
        game.world["locations"]["mars"]["refined_metal"] = game.FREIGHTER_METAL_PICKUP_RESERVE + 100.0
        game.world["locations"]["earth"]["support_supplies"] = 1000.0
        game.world["ships"] = {
            "csv_meridian": {
                "name": "CSV Meridian", "status": "idle_at_earth",
                "cargo_capacity": 200, "cargo_support_supplies": 0, "cargo_refined_metal": 0,
                "travel_remaining": 0, "class_id": "freighter", "mk": "Mark I",
            },
            "csv_concord": {
                "name": "CSV Concord", "status": "idle_at_mars",
                "cargo_capacity": 200, "cargo_support_supplies": 0, "cargo_refined_metal": 0,
                "travel_remaining": 0, "class_id": "freighter", "mk": "Mark I",
            },
            "lws_vigilant": {
                "name": "LWS Vigilant", "status": "escorting Earth-Mars corridor",
                "class_id": "light_warship", "mk": "Mark I", "combat_rating": 40,
            },
        }

    def test_csv_concord_actually_advances_through_the_loop(self):
        game.update_freighters()
        concord = game.world["ships"]["csv_concord"]
        self.assertEqual(concord["status"], "transit_to_earth")
        self.assertGreater(concord["cargo_refined_metal"], 0)

    def test_a_freshly_shipyard_built_freighter_joins_the_loop(self):
        game.world["ship_classes"] = {
            "freighter": ShipClass(
                id="freighter", category="logistics", in_service=["CSV Meridian", "CSV Concord"]
            ),
        }
        game.world["ship_class_stats"] = {"freighter": {"cargo_capacity": 200}}
        # Enough above the reserve for CSV Concord (also idle_at_mars in
        # this test's setUp) AND the new ship to each take a full load --
        # otherwise CSV Concord alone could exhaust the available metal
        # and starve the very ship this test is about.
        game.world["locations"]["mars"]["refined_metal"] = game.FREIGHTER_METAL_PICKUP_RESERVE + 500.0
        game._hull_counters["freighter"] = 0  # deterministic hull numbering for this test
        game._complete_ship_build("freighter")

        new_ship_id = next(k for k in game.world["ships"] if k.startswith("csv_hull_"))
        new_ship = game.world["ships"][new_ship_id]
        self.assertEqual(new_ship["status"], "idle_at_mars")  # delivered idle, as documented

        game.update_freighters()
        self.assertEqual(new_ship["status"], "transit_to_earth")
        self.assertGreater(new_ship["cargo_refined_metal"], 0)

    def test_two_freighters_idle_at_mars_split_the_metal_above_reserve(self):
        game.world["ships"]["csv_meridian"]["status"] = "idle_at_mars"
        # Only 60 above the reserve -- not enough for both ships to take a
        # full 200-unit load, so this also exercises the documented
        # first-come-first-served behavior for two ships sharing one step.
        game.world["locations"]["mars"]["refined_metal"] = game.FREIGHTER_METAL_PICKUP_RESERVE + 60.0

        game.update_freighters()

        total_loaded = (
            game.world["ships"]["csv_meridian"]["cargo_refined_metal"]
            + game.world["ships"]["csv_concord"]["cargo_refined_metal"]
        )
        self.assertAlmostEqual(total_loaded, 60.0)
        self.assertAlmostEqual(
            game.world["locations"]["mars"]["refined_metal"], game.FREIGHTER_METAL_PICKUP_RESERVE
        )

    def test_show_status_prints_every_freighter_not_just_csv_meridian(self):
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_status()
        output = buf.getvalue()
        self.assertIn("CSV Meridian", output)
        self.assertIn("CSV Concord", output)


def _make_established_colony(
    colony_id, name="Test Colony", specialization="forge_world", population=0,
    raw_metal=0.0, refined_metal=0.0, distance_steps=5,
):
    """Build an established colony dict with every field update_tithes()
    and show_colonies() expect, bypassing survey/outpost/specialize so
    each test can set exactly the population/stock it needs.
    """
    game.world["colonies"][colony_id] = {
        "name": name, "status": "established", "specialization": specialization,
        "support_supplies": 1000.0, "raw_metal": raw_metal, "refined_metal": refined_metal,
        "population": population, "distance_steps": distance_steps,
        "tithe_grade": None, "tithe_shortfall_streak": 0,
        "garrison_rating": 0.0, "continuance_hall": False,
        "fuel_reserve": 0.0, "trade_throughput": 0.0,
    }
    return game.world["colonies"][colony_id]


class TitheSystemIntegrationTests(unittest.TestCase):
    """Covers the 2026-09-04 Tithe System: per-colony Tithe Grades, the
    fixed-quota assessment every TITHE_CYCLE_STEPS, convoys that take real
    per-colony travel time to reach Mars, and the shortfall -> Bureau
    audit -> Penal Code escalation chain.
    """

    def setUp(self):
        game.world["colonies"] = {}
        game.world["tithe_convoys"] = []
        game.world["tithe_system"] = {"doctrine": "test doctrine", "log": []}
        game.world["audit_system"] = {
            "doctrine": "test doctrine", "active_concealments": [], "log": [], "last_audit_step": {},
        }
        game.world["penal_records"] = []
        game.world["penal_code"] = PenalCode.default_code()
        game.world["locations"]["mars"]["raw_metal"] = 0.0
        game.world["locations"]["mars"]["refined_metal"] = 0.0
        # High enough that AUDIT_COST_SUPPORT_SUPPLIES never blocks a test
        # here regardless of execution order or how many audits it runs.
        game.world["locations"]["mars"]["support_supplies"] = 1000.0
        # Land exactly on a tithe-cycle step every time a test calls
        # advance-equivalent helpers below, regardless of what earlier
        # tests left world["time"] at.
        game.world["time"] = 0

    def test_exempt_specialization_never_gets_a_grade_or_assessed(self):
        colony = _make_established_colony("c1", specialization="agri_world", population=5000)
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()
        self.assertIsNone(colony["tithe_grade"])
        self.assertEqual(game.world["tithe_convoys"], [])
        self.assertEqual(game.world["audit_system"]["active_concealments"], [])

    def test_grade_rises_with_population_and_specialization(self):
        low_pop = _make_established_colony("c1", specialization="mining_world", population=0)
        self.assertEqual(game._tithe_grade_level(low_pop), 1)  # base only
        high_pop = _make_established_colony("c2", specialization="forge_world", population=999999)
        self.assertEqual(game._tithe_grade_level(high_pop), game.MAX_TITHE_GRADE)  # capped

    def test_full_payment_deducts_stock_and_dispatches_a_convoy(self):
        colony = _make_established_colony(
            "c1", specialization="mining_world", population=0,
            raw_metal=100.0, refined_metal=100.0, distance_steps=7,
        )
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()

        owed = game.TITHE_GRADE_QUOTA[1]  # mining_world base grade, no population bump
        self.assertEqual(colony["refined_metal"], 100.0 - owed)  # refined paid first
        self.assertEqual(colony["raw_metal"], 100.0)
        self.assertEqual(colony["tithe_shortfall_streak"], 0)
        self.assertEqual(len(game.world["tithe_convoys"]), 1)
        self.assertEqual(game.world["tithe_convoys"][0]["steps_remaining"], 7)
        self.assertEqual(len(game.world["tithe_system"]["log"]), 1)

    def test_shortfall_opens_an_auditable_concealment(self):
        colony = _make_established_colony("c1", specialization="mining_world", population=0, raw_metal=1.0)
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()

        self.assertEqual(colony["raw_metal"], 0.0)  # everything it had went out
        self.assertEqual(colony["tithe_shortfall_streak"], 1)
        concealments = game.world["audit_system"]["active_concealments"]
        self.assertEqual(len(concealments), 1)
        self.assertEqual(concealments[0]["kind"], "tithe_shortfall")
        self.assertEqual(concealments[0]["colony_id"], "c1")

    def test_successful_audit_clears_shortfall_and_resets_streak(self):
        colony = _make_established_colony("c1", specialization="mining_world", population=0)
        colony["tithe_shortfall_streak"] = 1
        game.world["audit_system"]["active_concealments"] = [{
            "kind": "tithe_shortfall", "seat_id": "chancellor_general", "colony_id": "c1",
            "colony_name": "Test Colony", "started_cycle": 0, "total_shortfall": 20.0, "cycles_short": 1,
        }]
        original_chance = game.AUDIT_SUCCESS_CHANCE
        game.AUDIT_SUCCESS_CHANCE = 1.0  # deterministic: force success
        try:
            game.handle_audit(["c1"])
        finally:
            game.AUDIT_SUCCESS_CHANCE = original_chance

        self.assertEqual(colony["tithe_shortfall_streak"], 0)
        self.assertEqual(game.world["audit_system"]["active_concealments"], [])
        self.assertEqual(len(game.world["audit_system"]["log"]), 1)

    def test_auditing_the_seat_id_never_matches_a_tithe_shortfall(self):
        """Regression test for a real bug found after the Tithe System
        shipped: every tithe shortfall shares seat_id "chancellor_general",
        so matching concealments by seat_id let `audit chancellor_general`
        silently resolve one arbitrary colony out of several open
        shortfalls and leave the rest untouched. A tithe shortfall must be
        targeted by its own colony_id -- 'chancellor_general' should never
        match one, no matter how many colonies are short at once.
        """
        _make_established_colony("colony_a", name="Colony A")
        _make_established_colony("colony_b", name="Colony B")
        game.world["audit_system"]["active_concealments"] = [
            {"kind": "tithe_shortfall", "seat_id": "chancellor_general", "colony_id": "colony_a",
             "colony_name": "Colony A", "started_cycle": 0, "total_shortfall": 5.0, "cycles_short": 1},
            {"kind": "tithe_shortfall", "seat_id": "chancellor_general", "colony_id": "colony_b",
             "colony_name": "Colony B", "started_cycle": 0, "total_shortfall": 5.0, "cycles_short": 1},
        ]
        original_chance = game.AUDIT_SUCCESS_CHANCE
        game.AUDIT_SUCCESS_CHANCE = 1.0
        try:
            game.handle_audit(["chancellor_general"])
            self.assertEqual(len(game.world["audit_system"]["active_concealments"]), 2)  # neither touched
            self.assertEqual(game.world["audit_system"]["log"], [])

            game.handle_audit(["colony_a"])  # targeting by colony_id still works
            self.assertEqual(len(game.world["audit_system"]["active_concealments"]), 1)
            self.assertEqual(game.world["audit_system"]["active_concealments"][0]["colony_id"], "colony_b")
        finally:
            game.AUDIT_SUCCESS_CHANCE = original_chance

    def test_catching_up_later_clears_a_stale_concealment(self):
        """A colony that fell short once but pays in full on a later
        cycle shouldn't leave a permanently open, uncatchable concealment
        behind it.
        """
        colony = _make_established_colony("c1", specialization="mining_world", population=0, raw_metal=1.0)
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()
        self.assertEqual(len(game.world["audit_system"]["active_concealments"]), 1)

        colony["raw_metal"] = 100.0
        game.world["time"] = game.TITHE_CYCLE_STEPS * 2
        game.update_tithes()

        self.assertEqual(colony["tithe_shortfall_streak"], 0)
        self.assertEqual(game.world["audit_system"]["active_concealments"], [])

    def test_persistent_shortfall_escalates_to_a_penal_code_charge(self):
        colony = _make_established_colony("c1", name="Karsk Deep", specialization="mining_world", population=0)
        for cycle in range(1, game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1):
            game.world["time"] = game.TITHE_CYCLE_STEPS * cycle
            game.update_tithes()

        self.assertEqual(colony["tithe_shortfall_streak"], 0)  # cleared by the escalation itself
        self.assertEqual(game.world["audit_system"]["active_concealments"], [])
        self.assertEqual(len(game.world["penal_records"]), 1)
        record = game.world["penal_records"][0]
        self.assertEqual(record["article_id"], "hoarding_of_strategic_supply")
        self.assertIn("Karsk Deep", record["name"])

    def test_convoy_travel_time_matches_the_colony_distance_and_delivers_to_mars(self):
        colony = _make_established_colony(
            "c1", specialization="forge_world", population=0, refined_metal=100.0, distance_steps=3,
        )
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()
        owed = game.TITHE_GRADE_QUOTA[2]  # forge_world base grade
        self.assertEqual(game.world["tithe_convoys"][0]["steps_remaining"], 3)

        game.update_tithe_convoys()
        game.update_tithe_convoys()
        self.assertEqual(len(game.world["tithe_convoys"]), 1)  # not delivered yet
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], 0.0)

        game.update_tithe_convoys()
        self.assertEqual(game.world["tithe_convoys"], [])
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], owed)

    def test_survey_assigns_a_distance_within_the_configured_band(self):
        game.world["locations"]["mars"]["refined_metal"] = game.SURVEY_COST
        game.handle_survey(["Frontier", "Reach"])
        colony = game.world["colonies"]["frontier_reach"]
        low, high = game.SURVEY_DISTANCE_RANGE_STEPS
        self.assertGreaterEqual(colony["distance_steps"], low)
        self.assertLessEqual(colony["distance_steps"], high)

    def test_convoy_delivery_timing_matches_the_real_advance_world_call_order(self):
        """Regression test for a real bug: advance_world() used to call
        update_tithes() (which can dispatch a brand-new convoy with
        steps_remaining = colony['distance_steps']) immediately followed
        by update_tithe_convoys() (which decrements every convoy once) in
        the SAME step -- so a freshly-dispatched convoy was decremented
        once before the player ever saw its real travel time, delivering
        one step earlier than distance_steps actually says. Fixed by
        calling update_tithe_convoys() BEFORE update_tithes() in
        advance_world(), so a convoy dispatched this step isn't touched
        until the *next* one. This test calls them in that same fixed
        order directly (not via advance_world(), to avoid dragging in
        unrelated systems like the shipyard/freighters) to pin the
        contract between the two functions independent of how
        advance_world() happens to be wired at any given moment.
        """
        colony = _make_established_colony(
            "c1", specialization="forge_world", population=0, refined_metal=100.0, distance_steps=3,
        )
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithe_convoys()  # nothing in transit yet -- no-op
        game.update_tithes()  # dispatches a new convoy this step
        self.assertEqual(game.world["tithe_convoys"][0]["steps_remaining"], 3)

        owed = game.TITHE_GRADE_QUOTA[2]  # forge_world base grade
        for step in range(1, 4):
            game.world["time"] += 1
            game.update_tithe_convoys()
            game.update_tithes()
            if step < 3:
                self.assertEqual(
                    len(game.world["tithe_convoys"]), 1, f"delivered too early, at step {step}"
                )
                self.assertEqual(game.world["locations"]["mars"]["refined_metal"], 0.0)

        # Exactly 3 real steps after dispatch -- matching distance_steps.
        self.assertEqual(game.world["tithe_convoys"], [])
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], owed)

    def test_advance_world_itself_calls_convoy_advance_before_tithe_assessment(self):
        """Locks in the actual call order inside advance_world() (not
        just the contract between the two functions, covered above) --
        a future edit could otherwise silently swap the order back
        without any test catching it.
        """
        call_order = []
        original_convoys = game.update_tithe_convoys
        original_tithes = game.update_tithes

        def spy_convoys():
            call_order.append("convoys")
            original_convoys()

        def spy_tithes():
            call_order.append("tithes")
            original_tithes()

        game.update_tithe_convoys = spy_convoys
        game.update_tithes = spy_tithes
        try:
            game.advance_world()
        finally:
            game.update_tithe_convoys = original_convoys
            game.update_tithes = original_tithes

        self.assertIn("convoys", call_order)
        self.assertIn("tithes", call_order)
        self.assertLess(call_order.index("convoys"), call_order.index("tithes"))


class TitheSaveCompatibilityTests(unittest.TestCase):
    """Regression test for a real bug found after the Tithe System
    shipped: a colony saved before it existed has no distance_steps/
    tithe_grade/tithe_shortfall_streak keys, and update_tithes()/
    show_colonies() raised a KeyError on it instead of loading cleanly.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        game.world["colonies"] = {}

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_backfills_missing_tithe_fields_on_an_old_colony(self):
        old_style_colony = {
            "name": "Old Colony", "status": "established", "specialization": "forge_world",
            "support_supplies": 10.0, "raw_metal": 5.0, "refined_metal": 5.0, "population": 50,
        }
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"colonies": {"old_colony": old_style_colony}}, f)

        game.load_game()

        colony = game.world["colonies"]["old_colony"]
        self.assertIn("distance_steps", colony)
        self.assertIn("tithe_grade", colony)
        self.assertIn("tithe_shortfall_streak", colony)

        # Both call sites that used to raise KeyError on a pre-Tithe-System
        # colony must now run cleanly.
        game.world["time"] = game.TITHE_CYCLE_STEPS
        game.update_tithes()
        game.show_colonies()


class PilotHandlerIntegrationTests(unittest.TestCase):
    """Regression test for the main.py side of the 2026-09-04 pilot-project
    fix: handle_pilot() used to gate applying a node's ship-design effect
    (and refreshing the draw pool) on result.success alone, which misses
    the case where a failed pilot roll still completes the node via prior
    investment (see attempt_pilot_project()'s own fix in
    src/research/engine.py, and its regression test in test_research.py).
    Verifies handle_pilot() checks actual completion, not just whether
    the roll succeeded.
    """

    def setUp(self):
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=[]),
        }
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200},
            "light_warship": {"combat_rating": 40},
        }

    def test_effect_applies_when_a_failed_roll_still_completes_the_node(self):
        from research.engine import _complete_node
        from research.models import PilotProjectResult

        state = game.world["research"]
        tech_id = "li_freighter_mk2_hull_design"
        lane = "logistics_and_industry"
        if tech_id not in state.active_pool[lane]:
            state.active_pool[lane].append(tech_id)

        def fake_failed_but_completed(state_arg, tech_id_arg, lab_id_arg, rng=None):
            node = state_arg.nodes[tech_id_arg]
            state_arg.rp_invested[tech_id_arg] = node.rp_cost  # simulate: already fully invested
            _complete_node(state_arg, node)
            return PilotProjectResult(
                tech_id=tech_id_arg, success=False, chance_used=0.5,
                rp_banked=node.rp_cost, rp_lost=0.0,
                note="Pilot project failed, but completed via prior investment.",
            )

        original = game.attempt_pilot_project
        game.attempt_pilot_project = fake_failed_but_completed
        try:
            pos = _pool_position(lane, tech_id)
            game.handle_pilot([lane, pos])
        finally:
            game.attempt_pilot_project = original

        # If handle_pilot() were still gating on result.success, this
        # would still read "Mark I" -- the effect would silently never
        # apply even though the node is completed in research state.
        self.assertEqual(game.world["ship_classes"]["freighter"].current_mk, "Mark II")


class AuditCostCooldownIntegrationTests(unittest.TestCase):
    """Regression tests for a design decision made 2026-09-04, under
    explicit authorization ("patch everything") after being flagged
    earlier as a balance call: `audit <target>` used to have no cost and
    no cooldown. With AUDIT_SUCCESS_CHANCE at 0.7 and free, unlimited,
    instant retries, a real concealment was never a genuine risk -- spam
    `audit` a few times and the odds of missing it approach zero. Now a
    real audit attempt (one that matches an open concealment) costs
    AUDIT_COST_SUPPORT_SUPPLIES and starts a per-target
    AUDIT_COOLDOWN_STEPS cooldown, win or lose.
    """

    def setUp(self):
        game.world["audit_system"] = {
            "doctrine": "test doctrine", "active_concealments": [], "log": [], "last_audit_step": {},
        }
        game.world["colonies"] = {}
        game.world["penal_records"] = []
        game.world["time"] = 0
        game.world["locations"]["mars"]["support_supplies"] = 1000.0

    def _open_silent_drain(self):
        game.world["audit_system"]["active_concealments"] = [{
            "kind": "silent_drain", "seat_id": "forge_marshal",
            "started_cycle": 0, "drain_per_cycle": 2, "total_concealed": 4.0,
        }]

    def test_a_real_audit_attempt_costs_support_supplies(self):
        self._open_silent_drain()
        before = game.world["locations"]["mars"]["support_supplies"]
        game.handle_audit(["forge_marshal"])
        after = game.world["locations"]["mars"]["support_supplies"]
        self.assertAlmostEqual(before - after, game.AUDIT_COST_SUPPORT_SUPPLIES)

    def test_auditing_a_clean_target_costs_nothing(self):
        before = game.world["locations"]["mars"]["support_supplies"]
        game.handle_audit(["forge_marshal"])  # nothing concealed -- clean
        after = game.world["locations"]["mars"]["support_supplies"]
        self.assertEqual(before, after)

    def test_cooldown_blocks_an_immediate_re_audit_of_the_same_target(self):
        self._open_silent_drain()
        original_chance = game.AUDIT_SUCCESS_CHANCE
        game.AUDIT_SUCCESS_CHANCE = 0.0  # force failure so the concealment stays open
        try:
            game.handle_audit(["forge_marshal"])
            spent_after_first = game.world["locations"]["mars"]["support_supplies"]
            game.handle_audit(["forge_marshal"])  # same step -- must be blocked by cooldown
            spent_after_second = game.world["locations"]["mars"]["support_supplies"]
        finally:
            game.AUDIT_SUCCESS_CHANCE = original_chance

        self.assertEqual(spent_after_first, spent_after_second)  # no second charge
        # Blocked, not resolved -- the concealment must still be open.
        self.assertEqual(len(game.world["audit_system"]["active_concealments"]), 1)

    def test_re_audit_is_allowed_again_once_the_cooldown_elapses(self):
        self._open_silent_drain()
        original_chance = game.AUDIT_SUCCESS_CHANCE
        game.AUDIT_SUCCESS_CHANCE = 0.0
        try:
            game.handle_audit(["forge_marshal"])
            game.world["time"] += game.AUDIT_COOLDOWN_STEPS
            game.AUDIT_SUCCESS_CHANCE = 1.0
            game.handle_audit(["forge_marshal"])
        finally:
            game.AUDIT_SUCCESS_CHANCE = original_chance

        self.assertEqual(game.world["audit_system"]["active_concealments"], [])

    def test_insufficient_support_supplies_blocks_the_attempt(self):
        self._open_silent_drain()
        game.world["locations"]["mars"]["support_supplies"] = game.AUDIT_COST_SUPPORT_SUPPLIES - 1.0
        before = game.world["locations"]["mars"]["support_supplies"]
        game.handle_audit(["forge_marshal"])
        after = game.world["locations"]["mars"]["support_supplies"]
        self.assertEqual(before, after)  # nothing spent, no attempt made
        self.assertEqual(len(game.world["audit_system"]["active_concealments"]), 1)  # untouched


class SaveLoadCorruptionIntegrationTests(unittest.TestCase):
    """Regression tests for a real bug found and fixed 2026-09-04:
    load_game() only ever caught FileNotFoundError. A state.json that
    exists but is corrupted -- truncated by a crash or a full disk
    mid-write, hand-edited into invalid JSON, or valid JSON in a shape
    this version's dataclass constructors don't recognize -- crashed the
    game on every single launch (both the unconditional call at import
    time and the `load` command) instead of failing gracefully.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_truncated_json_does_not_crash_load(self):
        with open(game.SAVE_FILE, "w") as f:
            f.write('{"time": 5, "locations": {')  # deliberately truncated / invalid JSON

        try:
            game.load_game()  # must not raise
        except Exception as exc:  # pragma: no cover - the whole point of this test
            self.fail(f"load_game() raised on corrupted JSON instead of handling it: {exc!r}")

        # The broken file is left in place, not silently deleted -- the
        # player can inspect or recover it by hand if they want to.
        self.assertTrue(os.path.exists(game.SAVE_FILE))

    def test_valid_json_with_an_incompatible_shape_does_not_crash_load(self):
        # Valid JSON, but "shipyard" doesn't match the Shipyard dataclass's
        # fields at all -- simulates a save from an incompatible version.
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"shipyard": {"totally_unexpected_field": 1}}, f)

        try:
            game.load_game()  # must not raise
        except Exception as exc:  # pragma: no cover - the whole point of this test
            self.fail(f"load_game() raised on an incompatible save shape instead of handling it: {exc!r}")

    def test_a_clean_valid_save_still_round_trips_normally(self):
        game.world["time"] = 42
        game.save_game()
        game.world["time"] = 0
        game.load_game()
        self.assertEqual(game.world["time"], 42)

    def test_a_failed_load_leaves_world_completely_untouched(self):
        """Regression test for a real bug: reconstruction steps used to
        run interleaved with direct writes into `world` (e.g. lab_roles
        was written by the flat key-copy loop BEFORE research was
        reconstructed). If research's reconstruction then raised,
        load_game()'s except-clause caught it and said "starting fresh
        instead of crashing" -- true for the exception, false for
        `world`, which was left holding a mix of old state and whatever
        had already been written. The next ordinary command touching
        that half-updated system (e.g. `labs`) then crashed for real.
        Fixed by doing every reconstruction that can raise into local
        variables BEFORE writing anything into `world`, so a raise
        anywhere in that phase leaves `world` completely untouched --
        this test's save is deliberately bad in the research block
        specifically to prove lab_roles/council (written by a step that
        now runs AFTER research reconstruction) are never touched.
        """
        original_lab_roles = dict(game.world["lab_roles"])
        original_council = dict(game.world["council"])

        bad_save = {
            "lab_roles": {**original_lab_roles, "totally_new_lab_from_bad_save": "flexible_auto_research"},
            "council": {"totally_different": "council data"},
            "research": {
                "labs": {"lab_bad": {"unexpected_field_that_lab_does_not_take": 1}},
                "scientists": {}, "rp_stockpile": {}, "rp_invested": {}, "active_pool": {}, "completed": [],
            },
        }
        with open(game.SAVE_FILE, "w") as f:
            json.dump(bad_save, f)

        game.load_game()  # must not raise, and must not partially apply

        self.assertEqual(game.world["lab_roles"], original_lab_roles)
        self.assertEqual(game.world["council"], original_council)


class HullCounterSaveLoadIntegrationTests(unittest.TestCase):
    """Regression tests for a real bug found and fixed 2026-09-04:
    _hull_counters is a module-level global, not part of `world`, so it
    used to reset to {"freighter": 1, "light_warship": 0} on every
    process start regardless of what was saved. The next hull the
    shipyard completed after a save/load reused an already-taken hull
    id, silently overwriting that ship's entry in world["ships"] and
    duplicating its name in ship_classes[...].in_service.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        self.original_hull_counters = dict(game._hull_counters)
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=[]),
        }
        game.world["ship_class_stats"] = {"freighter": {"cargo_capacity": 200}}
        game.world["ships"] = {}

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        game._hull_counters.clear()
        game._hull_counters.update(self.original_hull_counters)

    def test_hull_counters_round_trip_through_save_and_load(self):
        game._hull_counters["freighter"] = 4
        game._complete_ship_build("freighter")  # -> csv_hull_05
        self.assertIn("csv_hull_05", game.world["ships"])

        game.save_game()
        game._hull_counters["freighter"] = 1  # simulate a fresh process restart with no save yet applied

        game.load_game()
        game._complete_ship_build("freighter")

        self.assertIn("csv_hull_06", game.world["ships"])  # not a repeat of csv_hull_05
        self.assertEqual(len(game.world["ships"]), 2)  # no ship silently overwritten
        self.assertEqual(len(game.world["ship_classes"]["freighter"].in_service), 2)  # no duplicate name

    def test_backfill_infers_counters_from_existing_ship_ids_on_a_pre_fix_save(self):
        # Simulate a save made before hull_counters was persisted: no
        # "hull_counters" key at all, but ships already include a
        # high-numbered hull that a naive default counter would collide with.
        game.world["ships"] = {"csv_hull_09": {
            "name": "CSV Hull-09", "status": "idle_at_mars", "cargo_capacity": 200,
            "cargo_support_supplies": 0, "cargo_refined_metal": 0, "travel_remaining": 0,
            "class_id": "freighter", "mk": "Mark I",
        }}
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"ships": game.world["ships"]}, f)

        game._hull_counters["freighter"] = 1  # what a fresh process would start with
        game.load_game()
        game._complete_ship_build("freighter")

        self.assertIn("csv_hull_10", game.world["ships"])  # not csv_hull_02 -- no collision


class DynamicResearchNodeSaveLoadIntegrationTests(unittest.TestCase):
    """Regression test for a real bug found and fixed 2026-09-04: nodes
    registered at runtime (the self-renewing MK successor projects
    _register_next_mk_node() creates, e.g. "freighter_mark_iii") were
    never included in save_game()'s research_save dict. On the next
    load, build_research_state() rebuilds state.nodes fresh from
    technologies.json alone -- which never had the dynamic node -- while
    active_pool/completed still named it, crashing `research`/`invest`/
    `pilot` with a KeyError the moment any of them looked it up. This is
    a very ordinary sequence: complete an MK research node, save, reload.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
        }
        game.world["ship_class_stats"] = {"freighter": {"cargo_capacity": 200}}

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_a_dynamically_registered_node_survives_a_save_and_load_cycle(self):
        state = game.world["research"]
        lane = "logistics_and_industry"
        state.rp_stockpile[lane] = 1000.0
        tech_id = "li_freighter_mk2_hull_design"
        if tech_id not in state.active_pool[lane]:
            state.active_pool[lane].append(tech_id)
        pos = _pool_position(lane, tech_id)

        game.handle_invest([lane, pos])  # completes MK2, registers "freighter_mark_iii"
        self.assertIn("freighter_mark_iii", game.world["research"].nodes)

        game.save_game()
        game.load_game()

        # Before the fix, this line itself would KeyError -- the node
        # would be referenced by active_pool but absent from state.nodes.
        state = game.world["research"]
        self.assertIn("freighter_mark_iii", state.nodes)
        self.assertIn("freighter_mark_iii", state.active_pool[lane])

        # And the commands that actually look the node up must work too,
        # not just the raw dict membership check above.
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_research()  # must not crash
        self.assertIn("Freighter", buf.getvalue())


class CouncilSeatWiringIntegrationTests(unittest.TestCase):
    """Coverage and regression tests for the 2026-09-05 Council-seat wiring:
    first_minister, marshal_general, and first_steward_of_continuance were
    the last three of the ten Council seats with no live data behind them
    (see lore/gaps.md's "Lore ahead of code" entry -- Colonial Warden and
    Chancellor-General were wired in earlier sessions). All three are
    read-only aggregates over data the game already tracks; see
    docs/systems/council-seats.md for the full design writeup, including
    why fortress_world (garrison_rating) and civilian_world (Continuance
    Hall) needed real per-cycle effects first.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        game.world["colonies"] = {}
        game.world["locations"]["earth"]["support_supplies"] = 500.0

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _council_output(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_council()
        return buf.getvalue()

    def test_first_minister_reports_total_population_and_earth_reserve(self):
        _make_established_colony("c1", specialization="civilian_world", population=300)
        _make_established_colony("c2", specialization="mining_world", population=100)
        # A surveyed (not yet established) colony must not count toward
        # either the population total or the established-colony count.
        game.world["colonies"]["c3"] = {
            "name": "Unsettled", "status": "surveyed", "specialization": None,
            "support_supplies": 0.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 0,
            "distance_steps": 5, "tithe_grade": None, "tithe_shortfall_streak": 0,
            "garrison_rating": 0.0, "continuance_hall": False,
        }
        output = self._council_output()
        self.assertIn("400 colonist(s) across 2 established colony(ies)", output)
        self.assertIn("Earth support reserve: 500", output)

    def test_marshal_general_reports_aggregate_garrison_rating(self):
        fortress = _make_established_colony("c1", specialization="fortress_world")
        fortress["garrison_rating"] = 12.0
        _make_established_colony("c2", specialization="mining_world")  # contributes 0
        output = self._council_output()
        self.assertIn("1 fortress world(s), total garrison rating 12", output)

    def test_fortress_world_garrison_rating_actually_accumulates_via_update_colonies(self):
        fortress = _make_established_colony("c1", specialization="fortress_world")
        game.update_colonies()
        self.assertEqual(fortress["garrison_rating"], game.FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE)
        game.update_colonies()
        self.assertEqual(fortress["garrison_rating"], 2 * game.FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE)

    def test_non_fortress_colonies_never_accumulate_garrison_rating(self):
        colony = _make_established_colony("c1", specialization="mining_world")
        for _ in range(5):
            game.update_colonies()
        self.assertEqual(colony["garrison_rating"], 0.0)

    def test_first_steward_of_continuance_reports_continuance_hall_progress(self):
        grown = _make_established_colony(
            "c1", specialization="civilian_world", population=game.CONTINUANCE_HALL_POPULATION_THRESHOLD,
        )
        _make_established_colony("c2", specialization="mining_world", population=10)
        game.update_colonies()  # crosses the threshold for c1, not for c2
        self.assertTrue(grown["continuance_hall"])
        output = self._council_output()
        self.assertIn("1 of 2 established colony(ies) have raised a Continuance Hall", output)

    def test_continuance_hall_is_a_one_way_flag_that_never_resets(self):
        colony = _make_established_colony(
            "c1", specialization="civilian_world", population=game.CONTINUANCE_HALL_POPULATION_THRESHOLD,
        )
        game.update_colonies()
        self.assertTrue(colony["continuance_hall"])
        colony["population"] = 0  # even if population somehow dropped afterward
        game.update_colonies()
        self.assertTrue(colony["continuance_hall"])  # stays True, never un-set

    def test_load_backfills_garrison_rating_and_continuance_hall_on_a_pre_fix_save(self):
        # Simulate a save made before the 2026-09-05 Council-seat wiring:
        # no "garrison_rating" or "continuance_hall" key on the colony at
        # all. Without the setdefault() backfill in _apply_loaded_save(),
        # the very next update_colonies()/show_colonies()/show_council()
        # call would KeyError on this colony.
        game.world["colonies"] = {"c1": {
            "name": "Old Colony", "status": "established", "specialization": "fortress_world",
            "support_supplies": 100.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 50,
            "distance_steps": 5, "tithe_grade": None, "tithe_shortfall_streak": 0,
        }}
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"colonies": game.world["colonies"]}, f)

        game.load_game()  # must not KeyError

        colony = game.world["colonies"]["c1"]
        self.assertEqual(colony["garrison_rating"], 0.0)
        self.assertFalse(colony["continuance_hall"])
        game.update_colonies()  # must not KeyError either, now that it's backfilled
        self.assertEqual(colony["garrison_rating"], game.FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE)

    def test_colonial_warden_reports_colony_counts_by_status(self):
        # Colonial Warden / remaining specializations pass (2026-09-05):
        # this seat had no live_status line at all before this pass (see
        # docs/systems/council-seats.md). Covers the read-only aggregate
        # over every status a colony can be in.
        game.world["colonies"]["surveyed_only"] = {
            "name": "Unsettled", "status": "surveyed", "specialization": None,
            "support_supplies": 0.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 0,
            "distance_steps": 5, "tithe_grade": None, "tithe_shortfall_streak": 0,
            "garrison_rating": 0.0, "continuance_hall": False,
            "fuel_reserve": 0.0, "trade_throughput": 0.0,
        }
        game.world["colonies"]["outpost_only"] = {
            "name": "Fledgling", "status": "outpost", "specialization": None,
            "support_supplies": 50.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 50,
            "distance_steps": 5, "tithe_grade": None, "tithe_shortfall_streak": 0,
            "garrison_rating": 0.0, "continuance_hall": False,
            "fuel_reserve": 0.0, "trade_throughput": 0.0,
        }
        _make_established_colony("c1", specialization="mining_world")
        _make_established_colony("c2", specialization="forge_world")
        output = self._council_output()
        self.assertIn(
            "4 colony survey(s) on file -- 1 awaiting outpost, "
            "1 outpost(s) awaiting specialization, 2 established",
            output,
        )

    def test_quartermaster_general_reports_fuel_and_trade_totals(self):
        fuel = _make_established_colony("c1", specialization="fuel_world")
        fuel["fuel_reserve"] = 18.0
        trade = _make_established_colony("c2", specialization="depot_trade_world")
        trade["trade_throughput"] = 24.0
        _make_established_colony("c3", specialization="mining_world")  # contributes 0 to both
        output = self._council_output()
        self.assertIn("Directorate fuel reserve 18; trade throughput 24", output)

    def test_fuel_world_and_depot_trade_world_accumulate_via_update_colonies(self):
        fuel = _make_established_colony("c1", specialization="fuel_world")
        trade = _make_established_colony("c2", specialization="depot_trade_world")
        game.update_colonies()
        self.assertEqual(fuel["fuel_reserve"], game.FUEL_WORLD_RESERVE_PER_CYCLE)
        self.assertEqual(trade["trade_throughput"], game.DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE)
        game.update_colonies()
        self.assertEqual(fuel["fuel_reserve"], 2 * game.FUEL_WORLD_RESERVE_PER_CYCLE)
        self.assertEqual(trade["trade_throughput"], 2 * game.DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE)

    def test_non_fuel_or_trade_colonies_never_accumulate_those_stats(self):
        colony = _make_established_colony("c1", specialization="mining_world")
        for _ in range(5):
            game.update_colonies()
        self.assertEqual(colony["fuel_reserve"], 0.0)
        self.assertEqual(colony["trade_throughput"], 0.0)

    def test_load_backfills_fuel_reserve_and_trade_throughput_on_a_pre_fix_save(self):
        # Same backfill pattern as garrison_rating/continuance_hall above,
        # for a save made before THIS pass: no "fuel_reserve" or
        # "trade_throughput" key on the colony at all.
        game.world["colonies"] = {"c1": {
            "name": "Old Colony", "status": "established", "specialization": "fuel_world",
            "support_supplies": 100.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 50,
            "distance_steps": 5, "tithe_grade": None, "tithe_shortfall_streak": 0,
            "garrison_rating": 0.0, "continuance_hall": False,
        }}
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"colonies": game.world["colonies"]}, f)

        game.load_game()  # must not KeyError

        colony = game.world["colonies"]["c1"]
        self.assertEqual(colony["fuel_reserve"], 0.0)
        self.assertEqual(colony["trade_throughput"], 0.0)
        game.update_colonies()  # must not KeyError either, now that it's backfilled
        self.assertEqual(colony["fuel_reserve"], game.FUEL_WORLD_RESERVE_PER_CYCLE)


class PenalLaborEconomyIntegrationTests(unittest.TestCase):
    """Coverage and regression tests for the 2026-09-05 Penal Code labor-
    economy wiring: Toil Legion and Penal Legion sentences -- explicitly
    flagged as unwired in docs/systems/penal-code.md's own "What this
    version explicitly does not include yet" section -- now apply a real,
    fixed-term effect (Mars refined-metal output for Toil Legion,
    Directorate-wide garrison rating for Penal Legion) instead of being a
    record with no consequence. See docs/systems/penal-code.md and
    docs/systems/council-seats.md for the full design.
    """

    def setUp(self):
        game.world["penal_code"] = PenalCode.default_code()
        game.world["penal_records"] = []
        game.world["legion_penal_garrison_rating"] = 0.0
        game.world["colonies"] = {}
        game.world["locations"]["mars"]["refined_metal"] = 0.0
        # A couple of tests below call show_council()/advance_world(), both
        # of which read world["ship_classes"]["light_warship"] -- restore
        # it explicitly rather than relying on whatever an earlier test
        # class (some of which replace world["ship_classes"] with a
        # freighter-only dict and never restore it) left behind.
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=[]),
            "light_warship": ShipClass(id="light_warship", category="warship", in_service=[]),
        }

    def test_toil_legion_charge_is_filed_as_serving_with_a_fixed_term(self):
        game.handle_charge(["subject_a", "desertion_of_post"])  # typical sentence: Toil Legion
        record = game.world["penal_records"][-1]
        self.assertEqual(record["status"], "serving")
        self.assertEqual(record["term_remaining"], game.TOIL_LEGION_TERM_STEPS)

    def test_penal_legion_charge_is_filed_as_serving_with_a_fixed_term(self):
        game.handle_charge(["subject_b", "sabotage_of_directorate_property"])  # typical sentence: Penal Legion
        record = game.world["penal_records"][-1]
        self.assertEqual(record["status"], "serving")
        self.assertEqual(record["term_remaining"], game.PENAL_LEGION_TERM_STEPS)

    def test_toil_legion_labor_adds_refined_metal_at_mars_each_step(self):
        game.handle_charge(["subject_a", "desertion_of_post"])
        game.update_penal_labor()
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], game.TOIL_LEGION_REFINED_METAL_PER_CYCLE)
        game.update_penal_labor()
        self.assertEqual(
            game.world["locations"]["mars"]["refined_metal"], 2 * game.TOIL_LEGION_REFINED_METAL_PER_CYCLE
        )

    def test_penal_legion_labor_adds_directorate_wide_garrison_rating_each_step(self):
        game.handle_charge(["subject_b", "sabotage_of_directorate_property"])
        game.update_penal_labor()
        self.assertEqual(game.world["legion_penal_garrison_rating"], game.PENAL_LEGION_GARRISON_PER_CYCLE)
        game.update_penal_labor()
        self.assertEqual(game.world["legion_penal_garrison_rating"], 2 * game.PENAL_LEGION_GARRISON_PER_CYCLE)

    def test_term_expires_and_stops_applying_its_effect(self):
        game.handle_charge(["subject_a", "desertion_of_post"])
        record = game.world["penal_records"][-1]
        for _ in range(game.TOIL_LEGION_TERM_STEPS):
            game.update_penal_labor()
        self.assertEqual(record["status"], "term_served")
        self.assertEqual(record["term_remaining"], 0)
        metal_at_expiry = game.world["locations"]["mars"]["refined_metal"]

        game.update_penal_labor()  # one more step after the term ends
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], metal_at_expiry)  # no further output

    def test_records_under_other_statuses_are_untouched(self):
        game.handle_charge(["subject_c", "treason_against_the_directorate"])  # awaiting_confirmation
        game.handle_charge(["subject_d", "insubordination_under_command"])  # sentenced, no term at all
        game.update_penal_labor()
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], 0.0)
        self.assertEqual(game.world["legion_penal_garrison_rating"], 0.0)
        for record in game.world["penal_records"]:
            self.assertIn(record["status"], ("awaiting_confirmation", "sentenced"))

    def test_council_reports_penal_legion_count_and_garrison_contribution(self):
        game.handle_charge(["subject_b", "sabotage_of_directorate_property"])
        game.update_penal_labor()
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_council()
        output = buf.getvalue()
        self.assertIn("1 Penal Legion sentence(s) serving", output)
        self.assertIn(f"+{game.PENAL_LEGION_GARRISON_PER_CYCLE:.0f} garrison", output)

    def test_docket_shows_remaining_term_for_a_serving_sentence(self):
        game.handle_charge(["subject_a", "desertion_of_post"])
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_docket()
        self.assertIn(f"({game.TOIL_LEGION_TERM_STEPS} step(s) remaining)", buf.getvalue())

    def test_advance_world_itself_runs_penal_labor_every_step(self):
        # A full advance_world() also runs Mars's own forge complex and the
        # shipyard, both of which touch refined_metal independently -- so
        # this checks that update_penal_labor() actually ran (the term
        # ticked down by exactly one), not an absolute refined-metal
        # amount that other systems in the same step would make brittle.
        game.handle_charge(["subject_a", "desertion_of_post"])
        record = game.world["penal_records"][-1]
        game.world["time"] = 0
        game.advance_world()
        self.assertEqual(record["term_remaining"], game.TOIL_LEGION_TERM_STEPS - 1)


class PenalLaborSaveCompatibilityTests(unittest.TestCase):
    """Regression tests for loading a save made before the 2026-09-05
    Penal Code labor-economy wiring: no "legion_penal_garrison_rating" key
    at the top level, and any already-filed Toil/Penal Legion record has
    the old generic "sentenced" status with no "term_remaining" at all.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=[]),
        }
        game.world["ship_class_stats"] = {"freighter": {"cargo_capacity": 200}}

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_pre_fix_toil_legion_record_becomes_term_served_on_load(self):
        game.world["penal_records"] = [
            {"name": "Old Subject", "article_id": "desertion_of_post", "tier": "toil_legion", "status": "sentenced"},
        ]
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"penal_records": game.world["penal_records"]}, f)

        game.load_game()  # must not KeyError

        record = game.world["penal_records"][0]
        self.assertEqual(record["status"], "term_served")
        self.assertEqual(record["term_remaining"], 0)
        self.assertEqual(game.world["legion_penal_garrison_rating"], 0.0)

        game.update_penal_labor()  # must not KeyError, and must apply no further effect
        self.assertEqual(record["term_remaining"], 0)

    def test_serving_record_missing_term_remaining_does_not_crash(self):
        # Can't happen through normal play (_file_charge() always sets
        # term_remaining in the same assignment as "serving"), but a
        # hand-edited or partially-written save could produce this shape --
        # update_penal_labor() used to do a bare `-= 1` and crash.
        game.world["penal_records"] = [
            {"name": "Malformed", "article_id": "desertion_of_post", "tier": game.SentencingTier.TOIL_LEGION,
             "status": "serving"},
        ]
        game.update_penal_labor()  # must not raise KeyError
        record = game.world["penal_records"][0]
        self.assertEqual(record["status"], "term_served")

    def test_load_backfills_a_serving_record_missing_term_remaining(self):
        game.world["penal_records"] = [
            {"name": "Old Serving Subject", "article_id": "sabotage_of_directorate_property",
             "tier": "penal_legion", "status": "serving"},
        ]
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"penal_records": game.world["penal_records"]}, f)

        game.load_game()  # must not KeyError

        record = game.world["penal_records"][0]
        self.assertEqual(record["status"], "term_served")
        self.assertEqual(record["term_remaining"], 0)
        game.update_penal_labor()  # must not KeyError, and must apply no further effect
        self.assertEqual(game.world["legion_penal_garrison_rating"], 0.0)


class ColonySupportSustainabilityIntegrationTests(unittest.TestCase):
    """Regression tests for a real, severe bug found and fixed 2026-09-05
    during a full-game stress-test pass: update_colonies() used to keep
    charging COLONY_SUPPORT_CONSUMPTION forever for "established" colonies
    too, with only agri_world's per-cycle effect ever offsetting it and no
    colony-resupply mechanic existing anywhere in the game. Under the
    shipped constants (OUTPOST_SUPPORT_SEED 50.0 / COLONY_SUPPORT_CONSUMPTION
    5.0), EVERY non-agri_world colony permanently stalled at exactly cycle
    10 after founding -- the default outcome of ordinary play for 6 of 8
    specializations, not an edge case. This cascaded into unbounded
    Penal Code charge generation (a permanently-stalled mining/forge
    colony can never pay another tithe) and made the same day's
    Continuance Hall milestone unreachable under default tuning. See
    update_colonies()'s docstring for the full fix rationale.
    """

    def setUp(self):
        game.world["colonies"] = {}
        game.world["locations"]["mars"]["refined_metal"] = 1000.0
        game.world["locations"]["earth"]["support_supplies"] = 1000.0

    def test_established_mining_world_never_stalls_from_support_supplies(self):
        game.handle_survey(["Test"])
        game.handle_outpost(["test"])
        game.handle_specialize(["test", "mining_world"])
        colony = game.world["colonies"]["test"]

        for _ in range(30):
            game.update_colonies()

        # An established colony is never billed for support supplies at
        # all -- its stock from outposting sits exactly where it was.
        self.assertEqual(colony["support_supplies"], game.OUTPOST_SUPPORT_SEED)
        self.assertEqual(colony["raw_metal"], 30 * game.SPECIALIZATION_EFFECTS["mining_world"]["raw_metal_per_cycle"])

    def test_fortress_world_garrison_rating_keeps_accumulating_past_the_old_stall_point(self):
        # Before the fix, this would freeze permanently at 4 cycles' worth
        # (the colony stalled at cycle 10, having only paid support for
        # cycles 1-9 -- see the module docstring's "froze permanently
        # after 40 points" note).
        garrison = _make_established_colony("c1", specialization="fortress_world")
        garrison["support_supplies"] = 1000.0
        for _ in range(15):
            game.update_colonies()
        self.assertEqual(garrison["garrison_rating"], 15 * game.FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE)

    def test_continuance_hall_is_reachable_under_shipped_default_constants(self):
        game.handle_survey(["Civic"])
        game.handle_outpost(["civic"])
        game.handle_specialize(["civic", "civilian_world"])
        colony = game.world["colonies"]["civic"]

        for _ in range(15):
            game.update_colonies()

        self.assertTrue(colony["continuance_hall"])
        self.assertGreaterEqual(colony["population"], game.CONTINUANCE_HALL_POPULATION_THRESHOLD)

    def test_outpost_phase_still_requires_support_supplies(self):
        # The fix only exempts "established" colonies -- an outpost that
        # hasn't specialized yet should still stall if its seed runs out,
        # since it hasn't reached self-sufficiency yet.
        game.handle_survey(["Fragile"])
        game.handle_outpost(["fragile"])
        colony = game.world["colonies"]["fragile"]
        colony["support_supplies"] = game.COLONY_SUPPORT_CONSUMPTION  # exactly one cycle's worth left

        game.update_colonies()
        self.assertEqual(colony["support_supplies"], 0.0)

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.update_colonies()
        self.assertIn("lacks support supplies", buf.getvalue())


class TitheEscalationDedupIntegrationTests(unittest.TestCase):
    """Regression test for a defensive fix made 2026-09-05 alongside the
    colony-support-stall fix above: a stress run on the OLD code (a
    permanently-stalled colony that could never again pay its tithe) hit
    194 duplicate "hoarding_of_strategic_supply" charges against the same
    two colonies over 2000 steps. The stall itself is fixed above, but
    _escalate_tithe_shortfall() now also refuses to stack a second charge
    on an administrator already "serving" one for the exact same offense,
    as cheap defense in depth against any future scenario that reaches
    persistent delinquency.
    """

    def setUp(self):
        game.world["colonies"] = {}
        game.world["tithe_convoys"] = []
        game.world["tithe_system"] = {"doctrine": "test doctrine", "log": []}
        game.world["audit_system"] = {
            "doctrine": "test doctrine", "active_concealments": [], "log": [], "last_audit_step": {},
        }
        game.world["penal_records"] = []
        game.world["penal_code"] = PenalCode.default_code()
        game.world["locations"]["mars"]["raw_metal"] = 0.0
        game.world["locations"]["mars"]["refined_metal"] = 0.0
        game.world["time"] = 0

    def test_second_escalation_does_not_stack_while_the_first_is_still_serving(self):
        colony = _make_established_colony("c1", name="Karsk Deep", specialization="mining_world", population=0)
        for cycle in range(1, game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1):
            game.world["time"] = game.TITHE_CYCLE_STEPS * cycle
            game.update_tithes()
        self.assertEqual(len(game.world["penal_records"]), 1)  # first escalation fires normally

        # Force a second escalation window immediately, while the first
        # Toil Legion sentence is still "serving" -- this is exactly the
        # scenario a permanently-delinquent colony hits every
        # TITHE_SHORTFALL_CHARGE_THRESHOLD cycles forever.
        for cycle in range(
            game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1,
            2 * game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1,
        ):
            game.world["time"] = game.TITHE_CYCLE_STEPS * cycle
            game.update_tithes()

        hoarding_records = [r for r in game.world["penal_records"] if r["article_id"] == "hoarding_of_strategic_supply"]
        self.assertEqual(len(hoarding_records), 1)  # still just the one -- no duplicate stacked on top
        self.assertEqual(colony["tithe_shortfall_streak"], 0)  # still cleared even without a new charge

    def test_a_new_escalation_can_fire_again_once_the_first_term_is_served(self):
        colony = _make_established_colony("c1", name="Karsk Deep", specialization="mining_world", population=0)
        for cycle in range(1, game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1):
            game.world["time"] = game.TITHE_CYCLE_STEPS * cycle
            game.update_tithes()
        first_record = game.world["penal_records"][0]
        first_record["status"] = "term_served"  # simulate the term having run its course

        for cycle in range(
            game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1,
            2 * game.TITHE_SHORTFALL_CHARGE_THRESHOLD + 1,
        ):
            game.world["time"] = game.TITHE_CYCLE_STEPS * cycle
            game.update_tithes()

        hoarding_records = [r for r in game.world["penal_records"] if r["article_id"] == "hoarding_of_strategic_supply"]
        self.assertEqual(len(hoarding_records), 2)  # a real second offense after serving the first is not suppressed


class ShipClassBackfillIntegrationTests(unittest.TestCase):
    """Regression test for a real bug found 2026-09-05 (stress-test pass,
    independently confirmed by two separate investigations): unlike every
    other historical field _apply_loaded_save() restores (colonies, hull
    counters, audit_system, penal records...), a save whose "ship_classes"
    object was missing an entire category (e.g. no "light_warship" key at
    all -- a hand edit, a truncated write, a future class rename) loaded
    with a silent "full state restored" message, then crashed the very
    next `advance` or `council` command with an uncaught KeyError, since
    update_shipyard() and show_council() both do a hardcoded
    world["ship_classes"]["light_warship"/"freighter"] lookup with no
    .get() guard.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        game.world["ship_class_stats"] = {
            "freighter": {"cargo_capacity": 200}, "light_warship": {"combat_rating": 40},
        }

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_backfills_a_ship_class_missing_entirely_from_the_save(self):
        # Save only has "freighter" -- "light_warship" is entirely absent,
        # not just missing a field on it.
        saved_ship_classes = {
            "freighter": {"id": "freighter", "category": "logistics", "current_mk": "Mark I",
                          "in_service": ["CSV Meridian"], "retired_from_production": False},
        }
        with open(game.SAVE_FILE, "w") as f:
            json.dump({"ship_classes": saved_ship_classes}, f)

        game.load_game()  # must not KeyError, must not silently skip ship_classes entirely

        self.assertIn("light_warship", game.world["ship_classes"])
        self.assertEqual(game.world["ship_classes"]["light_warship"].in_service, [])
        self.assertIn("freighter", game.world["ship_classes"])
        self.assertEqual(game.world["ship_classes"]["freighter"].in_service, ["CSV Meridian"])

        # The two real crash sites the stress pass found -- neither should
        # raise now that the backfilled class exists.
        game.world["colonies"] = {}
        game.world["penal_records"] = []
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            game.show_council()  # used to KeyError on ship_classes["light_warship"]
        self.assertIn("0 light warship(s) in service", buf.getvalue())


class DynamicNodePersistentGuaranteeIntegrationTests(unittest.TestCase):
    """Regression test for a real bug found 2026-09-05 (stress-test pass):
    handle_invest()/handle_pilot() only ever guaranteed a freshly-
    registered MK-successor node against the ONE refresh_draw_pool() call
    immediately following its own registration. Any LATER, unrelated
    completion in the same lane called refresh_draw_pool() with no
    guaranteed_ids for it at all, so a still-uninvested dynamic node could
    be silently evicted from the pool -- confirmed at ~16% (49/300 trials)
    for a completely ordinary sequence. Fixed via
    _guaranteed_dynamic_node_ids(), which recomputes every live dynamic
    node id in the lane on every call, not just the one right after
    registration.
    """

    def setUp(self):
        game.world["ship_classes"] = {
            "freighter": ShipClass(id="freighter", category="logistics", in_service=["CSV Meridian"]),
        }
        game.world["ship_class_stats"] = {"freighter": {"cargo_capacity": 200}}

    def test_dynamic_node_survives_unrelated_same_lane_completions(self):
        state = game.world["research"]
        lane = "logistics_and_industry"
        state.rp_stockpile[lane] = 1000.0

        mk2_id = "li_freighter_mk2_hull_design"
        if mk2_id not in state.active_pool[lane]:
            state.active_pool[lane].append(mk2_id)
        game.handle_invest([lane, str(_pool_position(lane, mk2_id))])
        self.assertIn("freighter_mark_iii", state.active_pool[lane])

        # Two more, entirely unrelated same-lane completions -- neither
        # touches freighter_mark_iii, both trigger their own
        # refresh_draw_pool() call the old code never re-guaranteed it on.
        for other_id in ("li_cargo_hold_optimization", "li_fuel_reclamation_cycles"):
            if other_id not in state.active_pool[lane]:
                state.active_pool[lane].append(other_id)
            state.rp_stockpile[lane] = 1000.0
            game.handle_invest([lane, str(_pool_position(lane, other_id))])
            self.assertIn(
                "freighter_mark_iii", state.active_pool[lane],
                "freighter_mark_iii was evicted by an unrelated same-lane completion",
            )


class StandingOrdersIntegrationTests(unittest.TestCase):
    """Coverage for the equipment-and-asset-upgrades standing order
    (update_standing_orders()/show_standing_orders()) -- previously the
    only system in main.py's own docstring system table with zero
    automated tests, per the 2026-09-04 audit's coverage section.
    """

    def setUp(self):
        game.world["locations"]["mars"]["refined_metal"] = 0.0
        game.world["equipment_status"] = {
            "frontline_combat": {"tier_index": 0, "tiers": [
                "Standard issue", "Reinforced-pattern armor and weapon mounts",
                "Forge-tempered plating, upgraded fire-control", "Collegium-pattern advanced war matériel",
            ]},
            "industrial": {"tier_index": 0, "tiers": [
                "Standard issue", "Reinforced extraction and refinery tooling",
                "Automated forge-line hardware", "Collegium-pattern advanced industrial systems",
            ]},
            "administrative_personal": {"tier_index": 0, "tiers": [
                "Standard issue", "Improved personal gear and office equipment",
                "Forge-tempered personal kit", "Collegium-pattern advanced administrative systems",
            ]},
        }
        game.world["standing_orders"]["equipment_and_asset_upgrades"]["log"] = []

    def test_no_upgrade_when_metal_at_or_below_reserve(self):
        game.world["locations"]["mars"]["refined_metal"] = game.EQUIPMENT_METAL_RESERVE
        game.update_standing_orders()
        self.assertEqual(game.world["equipment_status"]["frontline_combat"]["tier_index"], 0)
        self.assertEqual(len(game.world["standing_orders"]["equipment_and_asset_upgrades"]["log"]), 0)

    def test_surplus_above_reserve_and_cost_funds_frontline_first(self):
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST
        )
        game.update_standing_orders()
        self.assertEqual(game.world["equipment_status"]["frontline_combat"]["tier_index"], 1)
        self.assertEqual(game.world["equipment_status"]["industrial"]["tier_index"], 0)
        self.assertEqual(game.world["equipment_status"]["administrative_personal"]["tier_index"], 0)

    def test_exactly_one_upgrade_per_call_even_with_metal_for_several(self):
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST * 5
        )
        game.update_standing_orders()
        total_tiers_advanced = sum(
            status["tier_index"] for status in game.world["equipment_status"].values()
        )
        self.assertEqual(total_tiers_advanced, 1)

    def test_cost_is_deducted_from_mars_refined_metal(self):
        start = game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST + 10.0
        game.world["locations"]["mars"]["refined_metal"] = start
        game.update_standing_orders()
        self.assertAlmostEqual(
            game.world["locations"]["mars"]["refined_metal"], start - game.EQUIPMENT_UPGRADE_COST
        )

    def test_priority_order_moves_to_industrial_once_frontline_is_maxed(self):
        game.world["equipment_status"]["frontline_combat"]["tier_index"] = 3  # already maxed
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST
        )
        game.update_standing_orders()
        self.assertEqual(game.world["equipment_status"]["industrial"]["tier_index"], 1)

    def test_no_upgrade_left_to_fund_once_every_category_is_maxed(self):
        for status in game.world["equipment_status"].values():
            status["tier_index"] = 3
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST * 5
        )
        before = game.world["locations"]["mars"]["refined_metal"]
        game.update_standing_orders()
        self.assertEqual(game.world["locations"]["mars"]["refined_metal"], before)
        self.assertEqual(len(game.world["standing_orders"]["equipment_and_asset_upgrades"]["log"]), 0)

    def test_each_upgrade_appends_one_log_entry_with_cycle_and_new_tier(self):
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST
        )
        game.world["time"] = 42
        game.update_standing_orders()
        log = game.world["standing_orders"]["equipment_and_asset_upgrades"]["log"]
        self.assertEqual(len(log), 1)
        entry = log[0]
        self.assertEqual(entry["effective_cycle"], 42)
        self.assertEqual(entry["category"], "frontline_combat")
        self.assertEqual(
            entry["new_tier"], "Reinforced-pattern armor and weapon mounts"
        )

    def test_advance_world_itself_calls_update_standing_orders(self):
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST + 200.0
        )
        game.advance_world()
        self.assertEqual(
            len(game.world["standing_orders"]["equipment_and_asset_upgrades"]["log"]), 1
        )

    def test_show_standing_orders_runs_without_error_on_a_fresh_and_partially_upgraded_state(self):
        game.show_standing_orders()  # fresh: no logged actions yet
        game.world["locations"]["mars"]["refined_metal"] = (
            game.EQUIPMENT_METAL_RESERVE + game.EQUIPMENT_UPGRADE_COST
        )
        game.update_standing_orders()
        game.show_standing_orders()  # now with one logged action


class ResourceTransferHelperIntegrationTests(unittest.TestCase):
    """Direct coverage for withdraw_above_reserve()/deposit() -- the
    2026-09-07 shared resource-transfer helpers extracted from the
    freighter loop's and tithe convoys' previously-duplicated pickup/
    delivery arithmetic. The freighter and tithe convoy test classes
    above already exercise these indirectly; these tests cover the
    helpers' own edge cases directly, since they're now a piece of
    shared infrastructure other systems are expected to build on.
    """

    def setUp(self):
        self.location = {"support_supplies": 0.0, "refined_metal": 0.0}

    def test_withdraws_up_to_capacity_when_surplus_is_plentiful(self):
        self.location["refined_metal"] = 1000.0
        amount = game.withdraw_above_reserve(self.location, "refined_metal", reserve=60.0, capacity=200.0)
        self.assertEqual(amount, 200.0)
        self.assertEqual(self.location["refined_metal"], 800.0)

    def test_withdraws_only_the_surplus_above_reserve_when_capacity_exceeds_it(self):
        self.location["refined_metal"] = 100.0
        amount = game.withdraw_above_reserve(self.location, "refined_metal", reserve=60.0, capacity=200.0)
        self.assertEqual(amount, 40.0)
        self.assertEqual(self.location["refined_metal"], 60.0)

    def test_withdraws_nothing_when_at_or_below_reserve(self):
        self.location["refined_metal"] = 60.0
        amount = game.withdraw_above_reserve(self.location, "refined_metal", reserve=60.0, capacity=200.0)
        self.assertEqual(amount, 0.0)
        self.assertEqual(self.location["refined_metal"], 60.0)

        self.location["refined_metal"] = 10.0
        amount = game.withdraw_above_reserve(self.location, "refined_metal", reserve=60.0, capacity=200.0)
        self.assertEqual(amount, 0.0)
        self.assertEqual(self.location["refined_metal"], 10.0)

    def test_never_withdraws_below_zero_capacity(self):
        self.location["refined_metal"] = 1000.0
        amount = game.withdraw_above_reserve(self.location, "refined_metal", reserve=60.0, capacity=0.0)
        self.assertEqual(amount, 0.0)
        self.assertEqual(self.location["refined_metal"], 1000.0)

    def test_deposit_adds_to_existing_stock(self):
        self.location["support_supplies"] = 50.0
        game.deposit(self.location, "support_supplies", 25.0)
        self.assertEqual(self.location["support_supplies"], 75.0)

    def test_deposit_of_zero_is_a_no_op(self):
        self.location["support_supplies"] = 50.0
        game.deposit(self.location, "support_supplies", 0.0)
        self.assertEqual(self.location["support_supplies"], 50.0)

    def test_withdraw_then_deposit_round_trips_exactly(self):
        source = {"refined_metal": 500.0}
        destination = {"refined_metal": 0.0}
        amount = game.withdraw_above_reserve(source, "refined_metal", reserve=60.0, capacity=200.0)
        game.deposit(destination, "refined_metal", amount)
        self.assertEqual(source["refined_metal"], 300.0)
        self.assertEqual(destination["refined_metal"], 200.0)


if __name__ == "__main__":
    unittest.main()
