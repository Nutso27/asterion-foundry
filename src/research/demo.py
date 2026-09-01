"""A runnable walkthrough of the research engine.

Run from the repository root with:
    python src/research/demo.py

This is not a game lesson on its own — it exists so you can watch the
three layers (lab/specialist output, weighted discovery pool, pilot
project risk) work on real numbers before wiring the system into
``src/main.py``.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research import Lab, ResearchState, Scientist  # noqa: E402
from research.engine import attempt_pilot_project, generate_rp, invest_rp, refresh_draw_pool  # noqa: E402


def main():
    rng = random.Random(7)
    state = ResearchState.new_game_start()

    lab = Lab(
        id="mars_primary_lab",
        name="Mars Collegium Laboratory",
        location="mars",
        capacity=8,
        quality=0.6,
        specialties=["physics_and_materials", "logistics_and_industry"],
    )
    state.add_lab(lab)

    for i, (lane, skill) in enumerate(
        [
            ("physics_and_materials", 0.7),
            ("physics_and_materials", 0.5),
            ("logistics_and_industry", 0.65),
        ]
    ):
        sci = Scientist(id=f"sci_{i}", name=f"Savant {i}", specialty_lane=lane, skill=skill)
        state.add_scientist(sci)
        lab.assigned_scientist_ids.append(sci.id)

    print("=== Cycle 1: generating RP ===")
    generated = generate_rp(state, dt=1.0)
    for lane_id, amount in generated.items():
        if amount:
            print(f"  {lane_id}: +{amount:.2f} RP (stockpile now {state.rp_stockpile[lane_id]:.2f})")

    print("\n=== Refreshing discovery pools ===")
    for lane_id in state.lanes:
        pool = refresh_draw_pool(state, lane_id, rng=rng)
        names = [state.nodes[nid].name for nid in pool]
        print(f"  {lane_id}: {names}")

    print("\n=== Investing accumulated RP ===")
    for _ in range(20):
        generate_rp(state, dt=1.0)
    for lane_id, pool in state.active_pool.items():
        if not pool:
            continue
        target = pool[0]
        completed = invest_rp(state, target, state.rp_stockpile[lane_id])
        status = "COMPLETED" if completed else "in progress"
        print(f"  Invested lane '{lane_id}' RP into {state.nodes[target].name}: {status}")

    print("\n=== Attempting a pilot project (risk layer) ===")
    state.rp_stockpile["physics_and_materials"] = 200.0
    if "pm_focused_energy_emitters" not in state.completed:
        result = attempt_pilot_project(state, "pm_focused_energy_emitters", "mars_primary_lab", rng=rng)
        print(f"  {result.note}")

    print("\n=== Completed technologies ===")
    for tech_id in sorted(state.completed):
        print(f"  - {state.nodes[tech_id].name}: {state.nodes[tech_id].effect}")


if __name__ == "__main__":
    main()
