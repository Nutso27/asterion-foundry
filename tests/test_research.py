"""Tests for the Asterion Collegium research system.

Run from the repository root with:
    python -m unittest tests/test_research.py -v
or:
    python -m unittest discover -s tests

These use only the standard library (``unittest``), matching the rest of
this project's zero-dependency approach.
"""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research import Lab, ResearchState, Scientist, load_technologies  # noqa: E402
from research.engine import (  # noqa: E402
    add_evidence,
    attempt_pilot_project,
    calculate_pilot_success_chance,
    generate_rp,
    invest_rp,
    refresh_draw_pool,
)


class TechnologyDataTests(unittest.TestCase):
    """The data file itself must satisfy the design's hard requirements."""

    def setUp(self):
        self.lanes, self.nodes = load_technologies()

    def test_at_least_ten_technologies(self):
        self.assertGreaterEqual(len(self.nodes), 10)

    def test_exactly_five_lanes(self):
        self.assertEqual(len(self.lanes), 5)
        expected = {
            "physics_and_materials",
            "logistics_and_industry",
            "biology_and_colonization",
            "military_doctrine",
            "xenology",
        }
        self.assertEqual(set(self.lanes.keys()), expected)

    def test_every_node_has_a_lane_that_exists(self):
        for node in self.nodes.values():
            self.assertIn(node.lane, self.lanes)

    def test_no_dead_end_nodes(self):
        """Every node must name a concrete, non-empty mechanical effect."""
        for node in self.nodes.values():
            self.assertTrue(node.effect, f"{node.id} has no effect")

    def test_prerequisites_reference_real_nodes(self):
        for node in self.nodes.values():
            for prereq in node.prerequisites:
                self.assertIn(prereq, self.nodes, f"{node.id} lists unknown prereq {prereq}")

    def test_at_least_one_non_deterministic_branch_exists(self):
        """At least one pair of nodes must be mutually exclusive, giving
        the player a real fork rather than one guaranteed path.
        """
        has_branch = any(node.mutually_exclusive_with for node in self.nodes.values())
        self.assertTrue(has_branch)


class ResearchStateTests(unittest.TestCase):
    def setUp(self):
        self.state = ResearchState.new_game_start()
        self.lab = Lab(
            id="lab_1",
            name="Collegium Primary Laboratory",
            location="mars",
            capacity=6,
            quality=0.7,
            specialties=["physics_and_materials"],
        )
        self.scientist = Scientist(
            id="sci_1", name="Test Savant", specialty_lane="physics_and_materials", skill=0.8
        )
        self.lab.assigned_scientist_ids.append(self.scientist.id)
        self.state.add_lab(self.lab)
        self.state.add_scientist(self.scientist)

    def test_generate_rp_produces_positive_output_for_staffed_lab(self):
        generated = generate_rp(self.state, dt=1.0)
        self.assertGreater(generated["physics_and_materials"], 0.0)
        self.assertGreater(self.state.rp_stockpile["physics_and_materials"], 0.0)

    def test_generate_rp_is_zero_for_unstaffed_lane(self):
        generated = generate_rp(self.state, dt=1.0)
        self.assertEqual(generated["military_doctrine"], 0.0)

    def test_more_scientists_help_but_with_diminishing_returns(self):
        generate_rp(self.state, dt=1.0)
        one_scientist_output = self.state.rp_stockpile["physics_and_materials"]

        second = Scientist(
            id="sci_2", name="Second Savant", specialty_lane="physics_and_materials", skill=0.8
        )
        self.state.add_scientist(second)
        self.lab.assigned_scientist_ids.append(second.id)

        self.state.rp_stockpile["physics_and_materials"] = 0.0
        generate_rp(self.state, dt=1.0)
        two_scientist_output = self.state.rp_stockpile["physics_and_materials"]

        # Two scientists must beat one, but must not simply double the output.
        self.assertGreater(two_scientist_output, one_scientist_output)
        self.assertLess(two_scientist_output, one_scientist_output * 2.0)

    def test_invest_rp_completes_node_at_threshold(self):
        node_id = "pm_refined_alloy_process"
        self.state.rp_stockpile["physics_and_materials"] = 1000.0

        completed = invest_rp(self.state, node_id, self.state.nodes[node_id].rp_cost)
        self.assertTrue(completed)
        self.assertIn(node_id, self.state.completed)

    def test_invest_rp_partial_amount_does_not_complete(self):
        node_id = "pm_refined_alloy_process"
        self.state.rp_stockpile["physics_and_materials"] = 1000.0

        completed = invest_rp(self.state, node_id, 5.0)
        self.assertFalse(completed)
        self.assertNotIn(node_id, self.state.completed)

    def test_completing_a_node_removes_its_mutually_exclusive_alternative(self):
        self.state.rp_stockpile["physics_and_materials"] = 1000.0
        refresh_draw_pool(self.state, "physics_and_materials", pool_size=4, rng=random.Random(1))
        refresh_draw_pool(self.state, "military_doctrine", pool_size=4, rng=random.Random(1))

        invest_rp(
            self.state, "pm_focused_energy_emitters", self.state.nodes["pm_focused_energy_emitters"].rp_cost
        )
        self.assertIn("pm_focused_energy_emitters", self.state.completed)

        refresh_draw_pool(self.state, "military_doctrine", pool_size=4, rng=random.Random(2))
        self.assertNotIn("md_kinetic_mass_drivers", self.state.active_pool["military_doctrine"])

    def test_draw_pool_respects_prerequisites(self):
        pool = refresh_draw_pool(self.state, "physics_and_materials", pool_size=4, rng=random.Random(0))
        # pm_stress_lattice_theory requires pm_refined_alloy_process, not yet completed.
        self.assertNotIn("pm_stress_lattice_theory", pool)

    def test_draw_pool_respects_requested_size(self):
        pool = refresh_draw_pool(self.state, "physics_and_materials", pool_size=2, rng=random.Random(0))
        self.assertLessEqual(len(pool), 2)

    def test_guaranteed_ids_are_never_dropped_by_a_refresh(self):
        """Regression test for a real bug: a node registered at runtime
        with 0 RP invested (e.g. a freshly-unlocked MK successor project)
        used to compete on equal footing with every other eligible node
        the moment the pool was next refreshed, and could be silently
        dropped despite the player just having been told it was
        available. guaranteed_ids protects it the same way an
        already-in-progress node is protected. Run across many seeds
        (unprotected, this was observed to fail in ~1 of 6 trials) to
        make sure this isn't a coincidence of one particular draw.
        """
        node_id = "pm_stress_lattice_theory"  # not yet eligible on its own (needs a prereq)
        self.state.completed.add("pm_refined_alloy_process")  # ...so make it eligible now
        # pool_size=1 against 2 equally-eligible candidates -- real
        # competition, so this only proves something if guaranteed_ids
        # is actually forcing the node in regardless of the draw.
        for seed in range(30):
            pool = refresh_draw_pool(
                self.state, "physics_and_materials", pool_size=1,
                rng=random.Random(seed), guaranteed_ids={node_id},
            )
            self.assertIn(node_id, pool, f"dropped on seed {seed}")

    def test_without_guaranteed_ids_a_new_node_can_still_be_dropped(self):
        """Sanity check that the test above is actually exercising the
        bug's real conditions, not passing vacuously -- pool_size=1 with
        two equally-eligible candidates and no guaranteed_ids must be
        able to drop either one across enough seeds.
        """
        self.state.completed.add("pm_refined_alloy_process")
        node_id = "pm_stress_lattice_theory"
        dropped_at_least_once = any(
            node_id not in refresh_draw_pool(
                self.state, "physics_and_materials", pool_size=1, rng=random.Random(seed),
            )
            for seed in range(30)
        )
        self.assertTrue(dropped_at_least_once)


class PilotProjectTests(unittest.TestCase):
    def setUp(self):
        self.state = ResearchState.new_game_start()
        self.lab = Lab(
            id="lab_1",
            name="Collegium Primary Laboratory",
            location="mars",
            capacity=6,
            quality=0.7,
            specialties=["physics_and_materials"],
        )
        self.scientist = Scientist(
            id="sci_1", name="Test Savant", specialty_lane="physics_and_materials", skill=0.8
        )
        self.lab.assigned_scientist_ids.append(self.scientist.id)
        self.state.add_lab(self.lab)
        self.state.add_scientist(self.scientist)
        self.state.rp_stockpile["physics_and_materials"] = 1000.0

    def test_success_chance_is_clamped(self):
        node = self.state.nodes["pm_focused_energy_emitters"]
        chance = calculate_pilot_success_chance(node, self.lab, [self.scientist], funding_rp=1000.0)
        self.assertGreaterEqual(chance, 0.05)
        self.assertLessEqual(chance, 0.85)

    def test_rejects_non_pilot_node(self):
        with self.assertRaises(ValueError):
            attempt_pilot_project(self.state, "pm_refined_alloy_process", "lab_1", rng=random.Random(0))

    def test_success_completes_node_immediately(self):
        # Seed an RNG draw guaranteed below any clamped chance ceiling (0.85).
        rng = random.Random()
        rng.random = lambda: 0.01  # force a roll that always beats the success chance
        result = attempt_pilot_project(self.state, "pm_focused_energy_emitters", "lab_1", rng=rng)
        self.assertTrue(result.success)
        self.assertIn("pm_focused_energy_emitters", self.state.completed)
        self.assertEqual(result.rp_lost, 0.0)

    def test_failure_banks_partial_progress_and_loses_the_rest(self):
        rng = random.Random()
        rng.random = lambda: 0.99  # force a roll that always loses to the success chance
        node = self.state.nodes["pm_focused_energy_emitters"]
        result = attempt_pilot_project(self.state, "pm_focused_energy_emitters", "lab_1", rng=rng)

        self.assertFalse(result.success)
        self.assertNotIn("pm_focused_energy_emitters", self.state.completed)
        self.assertGreater(result.rp_banked, 0.0)
        self.assertGreater(result.rp_lost, 0.0)
        self.assertAlmostEqual(result.rp_banked + result.rp_lost, node.pilot_funding_rp, places=5)
        self.assertEqual(self.state.rp_invested["pm_focused_energy_emitters"], result.rp_banked)

    def test_failed_pilot_still_completes_a_node_already_near_full_investment(self):
        """Regression test for a real bug: only invest_rp() used to check
        whether rp_invested had crossed rp_cost, so a failed pilot's
        partial banking could push a node past its cost (if enough was
        already invested beforehand via plain `invest`) without the node
        ever actually being marked complete. Fixed 2026-09-04.
        """
        node = self.state.nodes["pm_focused_energy_emitters"]  # cost=100
        invest_rp(self.state, "pm_focused_energy_emitters", 85.0)  # short of completing on its own
        self.assertNotIn("pm_focused_energy_emitters", self.state.completed)

        rng = random.Random()
        rng.random = lambda: 0.99  # force the pilot roll itself to fail
        result = attempt_pilot_project(self.state, "pm_focused_energy_emitters", "lab_1", rng=rng)

        self.assertFalse(result.success)  # the roll failed...
        self.assertIn("pm_focused_energy_emitters", self.state.completed)  # ...but it's done
        self.assertNotIn("pm_focused_energy_emitters", self.state.rp_invested)  # cleared on completion
        self.assertIn("completed via", result.note)


class EvidenceGatingIntegrationTests(unittest.TestCase):
    """Coverage for the xenology lane's evidence-gating mechanism
    (TechNode.evidence_required / ResearchState.evidence_banked /
    add_evidence()) -- added 2026-09-07, resolving the gap
    lore/gaps.md flagged where no xenology lane existed at all.
    """

    def setUp(self):
        self.state = ResearchState.new_game_start()

    def test_xenology_node_absent_from_pool_with_no_evidence_banked(self):
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_point_defense_grids", 1000.0)
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_salvage_field_recovery", 1000.0)
        pool = refresh_draw_pool(self.state, "xenology", guaranteed_ids={"xn_fragment_baseline_analysis"})
        self.assertNotIn("xn_fragment_baseline_analysis", pool)

    def test_xenology_node_absent_from_pool_with_evidence_but_no_prerequisite(self):
        add_evidence(self.state, 1)
        pool = refresh_draw_pool(self.state, "xenology", guaranteed_ids={"xn_fragment_baseline_analysis"})
        self.assertNotIn("xn_fragment_baseline_analysis", pool)

    def test_xenology_node_appears_once_both_evidence_and_prerequisite_are_met(self):
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_point_defense_grids", 1000.0)
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_salvage_field_recovery", 1000.0)
        add_evidence(self.state, 1)
        pool = refresh_draw_pool(self.state, "xenology", guaranteed_ids={"xn_fragment_baseline_analysis"})
        self.assertIn("xn_fragment_baseline_analysis", pool)

    def test_add_evidence_returns_the_new_total(self):
        self.assertEqual(add_evidence(self.state, 1), 1)
        self.assertEqual(add_evidence(self.state, 2), 3)

    def test_downstream_xenology_nodes_need_no_additional_evidence(self):
        """xn_comparative_hull_metallurgy and xn_countermeasure_doctrine
        both have evidence_required=0 -- they chain off a normal
        prerequisite once the lane's evidence gate is cleared once,
        since xenos_fragments can never be replenished (see
        handle_study_fragments()'s docstring) and no node should be an
        unreachable dead end.
        """
        self.assertEqual(self.state.nodes["xn_comparative_hull_metallurgy"].evidence_required, 0)
        self.assertEqual(self.state.nodes["xn_countermeasure_doctrine"].evidence_required, 0)

    def test_completing_the_gated_node_still_requires_its_own_rp_cost(self):
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_point_defense_grids", 1000.0)
        self.state.rp_stockpile["military_doctrine"] = 1000.0
        invest_rp(self.state, "md_salvage_field_recovery", 1000.0)
        add_evidence(self.state, 1)

        node = self.state.nodes["xn_fragment_baseline_analysis"]
        self.state.rp_stockpile["xenology"] = node.rp_cost - 10.0
        invest_rp(self.state, "xn_fragment_baseline_analysis", node.rp_cost - 10.0)
        self.assertNotIn("xn_fragment_baseline_analysis", self.state.completed)

        self.state.rp_stockpile["xenology"] = 10.0
        invest_rp(self.state, "xn_fragment_baseline_analysis", 10.0)
        self.assertIn("xn_fragment_baseline_analysis", self.state.completed)


if __name__ == "__main__":
    unittest.main()
