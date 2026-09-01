"""The Asterion Collegium research engine.

This module has three layers, matching the three-part design brief this
system was built from:

1. **Lab & specialist layer** — ``generate_rp`` turns staffed labs and
   assigned scientists into research points (RP) per lane, per cycle,
   with diminishing returns on stacking scientists.
2. **Weighted discovery layer** — ``refresh_draw_pool`` rotates a small,
   weighted-random selection of eligible tech nodes into view per lane,
   so the player is never staring at (or grinding toward) one fixed
   tree; ``invest_rp`` slowly completes a node from banked RP.
3. **R&D pipeline / risk layer** — ``attempt_pilot_project`` lets a
   staffed node be gambled on early: a probability roll can finish it
   immediately, but failure only banks partial progress and burns the
   RP that was committed to the attempt.

No node in ``data/technologies.json`` is a dead end: every node's
``effect`` names a concrete build/move/fight change (see
``docs/systems/research.md`` for the full rationale).
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from .models import Lab, PilotProjectResult, Scientist, TechLane, TechNode

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "technologies.json"
DEFAULT_POOL_SIZE = 3


def load_technologies(path: Path = DEFAULT_DATA_PATH) -> tuple[dict[str, TechLane], dict[str, TechNode]]:
    """Read the technology data file and build lane and node lookup tables.

    Returns two dictionaries keyed by id: ``(lanes, nodes)``. Loading is
    intentionally separate from ``ResearchState`` so tests and tools can
    validate the data file on its own.
    """
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    lanes = {lane["id"]: TechLane(**lane) for lane in raw["lanes"]}
    nodes = {node["id"]: TechNode(**node) for node in raw["nodes"]}
    return lanes, nodes


@dataclass
class ResearchState:
    """The Collegium's full research state: facilities, staff, and progress.

    This is the single object engine functions read and mutate. It plays
    the same role for this system that the ``world`` dictionary plays in
    ``src/main.py`` — one place to look to understand "what is true right
    now."
    """

    lanes: dict[str, TechLane]
    nodes: dict[str, TechNode]
    labs: dict[str, Lab] = field(default_factory=dict)
    scientists: dict[str, Scientist] = field(default_factory=dict)
    rp_stockpile: dict[str, float] = field(default_factory=dict)
    rp_invested: dict[str, float] = field(default_factory=dict)
    active_pool: dict[str, list[str]] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    trial_log: list[PilotProjectResult] = field(default_factory=list)

    @classmethod
    def new_game_start(cls, data_path: Path = DEFAULT_DATA_PATH) -> "ResearchState":
        """Build a fresh state with the starter technology set and no staff.

        Labs and scientists are added later via ``add_lab``/``add_scientist``
        as the surrounding simulation reaches that point (e.g. once the
        Mars forge complex is built, per the project's own lesson order).
        """
        lanes, nodes = load_technologies(data_path)
        state = cls(lanes=lanes, nodes=nodes)
        for lane_id in lanes:
            state.rp_stockpile[lane_id] = 0.0
            state.active_pool[lane_id] = []
        return state

    def add_lab(self, lab: Lab) -> None:
        self.labs[lab.id] = lab

    def add_scientist(self, scientist: Scientist) -> None:
        self.scientists[scientist.id] = scientist


def _diminishing(value: float, rate: float) -> float:
    """Map a raw contribution to [0, 1) with diminishing returns.

    Uses ``1 - e^(-rate * value)``: the first unit of skill, funding, or
    lab quality matters most, and each additional unit matters a little
    less. This shape is reused across RP generation and pilot-project
    success chance so that stacking one factor is never optimal on its
    own.
    """
    return 1.0 - math.exp(-rate * max(value, 0.0))


def generate_rp(state: ResearchState, dt: float = 1.0) -> dict[str, float]:
    """Advance research point generation by ``dt`` cycles.

    For every lab, sum the contribution of its assigned scientists with
    diminishing returns (so five average scientists beat one brilliant
    one, but not by five times), scale by lab quality, and add the result
    to the lab's best-matching lane. Returns the RP generated per lane
    this call, and also adds it to ``state.rp_stockpile``.
    """
    generated: dict[str, float] = {lane_id: 0.0 for lane_id in state.lanes}

    for lab in state.labs.values():
        if not lab.assigned_scientist_ids:
            continue

        # Group this lab's staff by the lane they actually specialize in.
        by_lane: dict[str, list[Scientist]] = {}
        for sci_id in lab.assigned_scientist_ids:
            scientist = state.scientists.get(sci_id)
            if scientist is None:
                continue
            by_lane.setdefault(scientist.specialty_lane, []).append(scientist)

        for lane_id, staff in by_lane.items():
            if lane_id not in state.lanes:
                continue

            # Diminishing returns on the *team's* combined skill, not just
            # each scientist individually: two average researchers beat one,
            # but adding a third or fourth yields steadily less than the
            # last, so stacking generalists never out-produces a small,
            # well-matched, well-equipped team.
            skill_total = _diminishing(sum(s.skill for s in staff), 0.55)

            lane_match_bonus = 1.15 if lane_id in lab.specialties else 0.75
            base_output_per_cycle = 2.0  # baseline RP/cycle for one fully-staffed, average lab

            lane_rp = base_output_per_cycle * lab.quality * lane_match_bonus * skill_total * dt
            generated[lane_id] += lane_rp

    for lane_id, amount in generated.items():
        state.rp_stockpile[lane_id] = state.rp_stockpile.get(lane_id, 0.0) + amount

    return generated


def _is_eligible(state: ResearchState, node: TechNode) -> bool:
    """A node can appear in the discovery pool if its prerequisites are
    met, it is not already completed, and no mutually-exclusive
    alternative has already been chosen.
    """
    if node.id in state.completed:
        return False
    if any(prereq not in state.completed for prereq in node.prerequisites):
        return False
    if any(alt in state.completed for alt in node.mutually_exclusive_with):
        return False
    return True


def refresh_draw_pool(
    state: ResearchState,
    lane_id: str,
    pool_size: int = DEFAULT_POOL_SIZE,
    rng: random.Random | None = None,
) -> list[str]:
    """Roll a new weighted-random selection of visible nodes for one lane.

    Eligible nodes are drawn without replacement, weighted by
    ``draw_weight``, up to ``pool_size`` (2-4 by design). Nodes already
    in progress (some RP invested) are always kept visible so the player
    is never in the middle of research and unable to keep funding it.
    """
    rng = rng or random.Random()
    eligible = [n for n in state.nodes.values() if n.lane == lane_id and _is_eligible(state, n)]

    in_progress_ids = {
        n.id for n in eligible if state.rp_invested.get(n.id, 0.0) > 0.0
    }
    pool = list(in_progress_ids)

    remaining_slots = max(pool_size - len(pool), 0)
    candidates = [n for n in eligible if n.id not in in_progress_ids]

    while remaining_slots > 0 and candidates:
        weights = [max(n.draw_weight, 0.01) for n in candidates]
        chosen = rng.choices(candidates, weights=weights, k=1)[0]
        pool.append(chosen.id)
        candidates.remove(chosen)
        remaining_slots -= 1

    state.active_pool[lane_id] = pool
    return pool


def invest_rp(state: ResearchState, tech_id: str, amount: float) -> bool:
    """Spend banked RP from a node's lane toward that node.

    Returns True if the node completed as a result of this investment.
    Spending more than is banked in the lane is not allowed; call with
    whatever is available. Completing a node applies its effect via
    ``apply_effect`` and clears any now-invalid mutually-exclusive
    alternatives out of the active pool.
    """
    node = state.nodes[tech_id]
    if node.id in state.completed:
        return False

    lane_bank = state.rp_stockpile.get(node.lane, 0.0)
    spend = min(amount, lane_bank)
    if spend <= 0:
        return False

    state.rp_stockpile[node.lane] = lane_bank - spend
    state.rp_invested[tech_id] = state.rp_invested.get(tech_id, 0.0) + spend

    if state.rp_invested[tech_id] >= node.rp_cost:
        _complete_node(state, node)
        return True
    return False


def _complete_node(state: ResearchState, node: TechNode) -> None:
    state.completed.add(node.id)
    state.rp_invested.pop(node.id, None)
    for lane_id, pool in state.active_pool.items():
        state.active_pool[lane_id] = [
            nid
            for nid in pool
            if nid == node.id or nid not in node.mutually_exclusive_with
        ]


def calculate_pilot_success_chance(
    node: TechNode,
    lab: Lab,
    scientists: list[Scientist],
    funding_rp: float,
) -> float:
    """The R&D pipeline / risk layer's success-probability formula.

    Combines four diminishing-returns components — a flat base chance,
    assigned specialist skill, lab quality, and how much RP is being
    risked relative to the node's full cost — then applies a tier
    penalty (deeper, more advanced nodes are harder to shortcut).
    Clamped to [0.05, 0.85]: a pilot project is never a sure thing and
    never truly hopeless.
    """
    avg_skill = (sum(s.skill for s in scientists) / len(scientists)) if scientists else 0.0
    funding_ratio = funding_rp / node.rp_cost if node.rp_cost > 0 else 0.0

    skill_component = _diminishing(avg_skill, 1.5)
    lab_component = _diminishing(lab.quality, 1.2)
    funding_component = _diminishing(funding_ratio, 2.0)

    tier_penalty = 0.07 * max(node.tier - 1, 0)

    chance = (
        node.pilot_base_success_chance
        + 0.30 * skill_component
        + 0.20 * lab_component
        + 0.25 * funding_component
        - tier_penalty
    )
    return min(max(chance, 0.05), 0.85)


def attempt_pilot_project(
    state: ResearchState,
    tech_id: str,
    lab_id: str,
    rng: random.Random | None = None,
) -> PilotProjectResult:
    """Run one pilot-project trial: commit RP now for a chance to finish
    the node immediately instead of waiting on steady accumulation.

    The node must be ``pilot_project_enabled`` and have enough RP already
    banked in its lane to cover ``node.pilot_funding_rp``. On success the
    node completes outright (any remaining rp_cost is waived). On
    failure, ``pilot_partial_progress_pct`` of the committed RP is banked
    as permanent progress toward the node and the rest is lost — the
    trial's real cost.
    """
    rng = rng or random.Random()
    node = state.nodes[tech_id]
    lab = state.labs[lab_id]

    if not node.pilot_project_enabled:
        raise ValueError(f"{tech_id} has no pilot-project pathway")
    if node.id in state.completed:
        raise ValueError(f"{tech_id} is already completed")

    lane_bank = state.rp_stockpile.get(node.lane, 0.0)
    funding = min(node.pilot_funding_rp, lane_bank)
    if funding <= 0:
        raise ValueError(f"not enough banked RP in lane '{node.lane}' to fund a pilot project")

    scientists = [
        state.scientists[sid]
        for sid in lab.assigned_scientist_ids
        if sid in state.scientists and state.scientists[sid].specialty_lane == node.lane
    ]

    chance = calculate_pilot_success_chance(node, lab, scientists, funding)
    state.rp_stockpile[node.lane] = lane_bank - funding

    roll = rng.random()
    if roll < chance:
        _complete_node(state, node)
        result = PilotProjectResult(
            tech_id=tech_id,
            success=True,
            chance_used=chance,
            rp_banked=node.rp_cost,
            rp_lost=0.0,
            note=f"Pilot project succeeded ({chance:.0%} chance). {node.name} completed outright.",
        )
    else:
        banked = funding * node.pilot_partial_progress_pct
        lost = funding - banked
        state.rp_invested[tech_id] = state.rp_invested.get(tech_id, 0.0) + banked
        result = PilotProjectResult(
            tech_id=tech_id,
            success=False,
            chance_used=chance,
            rp_banked=banked,
            rp_lost=lost,
            note=(
                f"Pilot project failed ({chance:.0%} chance). "
                f"{banked:.1f} RP banked as partial progress, {lost:.1f} RP lost."
            ),
        )

    state.trial_log.append(result)
    return result
