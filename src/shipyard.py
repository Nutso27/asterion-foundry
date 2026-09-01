"""Shipyard slot expansion and no-idle production rotation.

See docs/systems/shipyard.md for the full design this implements.
"""

from __future__ import annotations

from dataclasses import dataclass

WARSHIP = "warship"
LOGISTICS = "logistics"


@dataclass
class Shipyard:
    """A slotted production facility.

    ``flexible`` slots are not locked to either category and are handed out
    by ``next_build_assignment`` based on current demand.
    """

    location: str
    slots_total: int = 1
    target_minimum: int = 100
    warship_minimum: int = 5
    warship_locked: int = 0
    logistics_minimum: int = 5
    logistics_locked: int = 0
    flexible: int = 0

    def free_slots_needed_for_minimums(self) -> int:
        """How many more locked slots are needed to satisfy both guarantees."""
        warship_gap = max(0, self.warship_minimum - self.warship_locked)
        logistics_gap = max(0, self.logistics_minimum - self.logistics_locked)
        return warship_gap + logistics_gap


def expand(
    yard: Shipyard,
    available_refined_metal: float,
    cost_per_slot: float = 50.0,
    batch_size: int = 3,
) -> tuple[Shipyard, int, float]:
    """Add up to ``batch_size`` slots, funded from ``available_refined_metal``.

    New slots fill the warship guarantee first, then the logistics
    guarantee, and only then join the flexible pool. Never exceeds
    ``target_minimum`` total slots. Returns (updated_yard, slots_added,
    metal_spent).
    """
    slots_added = 0
    metal_spent = 0.0

    while (
        slots_added < batch_size
        and yard.slots_total < yard.target_minimum
        and available_refined_metal - metal_spent >= cost_per_slot
    ):
        yard.slots_total += 1
        metal_spent += cost_per_slot

        if yard.warship_locked < yard.warship_minimum:
            yard.warship_locked += 1
        elif yard.logistics_locked < yard.logistics_minimum:
            yard.logistics_locked += 1
        else:
            yard.flexible += 1

        slots_added += 1

    return yard, slots_added, metal_spent


def next_build_assignment(
    allowed_categories: list[str],
    fleet_counts: dict[str, int],
    demand_counts: dict[str, int],
    surplus_threshold: float = 1.5,
) -> str:
    """Pick what a free slot should build next under the no-idle rotation rule.

    ``allowed_categories`` is what this particular slot may build (a locked
    slot only lists its own category; a flexible slot lists both).
    ``fleet_counts`` and ``demand_counts`` are keyed by category. A category
    is treated as being in surplus when its fleet count is at least
    ``surplus_threshold`` times its demand count, in which case this
    function steers toward the other allowed category instead.
    """
    if len(allowed_categories) == 1:
        return allowed_categories[0]

    def is_surplus(category: str) -> bool:
        demand = demand_counts.get(category, 0)
        fleet = fleet_counts.get(category, 0)
        if demand <= 0:
            return fleet > 0
        return fleet >= demand * surplus_threshold

    non_surplus = [c for c in allowed_categories if not is_surplus(c)]
    if non_surplus:
        # Prefer whichever non-surplus category has the smallest fleet
        # count relative to its demand (falling behind the most).
        return min(
            non_surplus,
            key=lambda c: fleet_counts.get(c, 0) - demand_counts.get(c, 0),
        )

    # Every allowed category is in surplus — fall back to the one with the
    # smallest absolute surplus so nothing sits idle.
    return min(
        allowed_categories,
        key=lambda c: fleet_counts.get(c, 0) - demand_counts.get(c, 0),
    )
