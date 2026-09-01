"""Lab specialization — fixed perpetual programs vs. Lab #1's flexible pool.

See docs/systems/lab-specialization.md for the full design this implements.
"""

from __future__ import annotations

FLEXIBLE_AUTO_RESEARCH = "flexible_auto_research"
PERPETUAL_CONSTRUCTION_OPTIMIZATION = "perpetual_construction_optimization"
PERPETUAL_RESEARCH_METHODOLOGY = "perpetual_research_methodology"
PERPETUAL_UNIVERSAL_IMPROVEMENT = "perpetual_universal_improvement"

# Fixed role by construction order. Any lab number not listed here
# (i.e. 4 and above) defaults to PERPETUAL_UNIVERSAL_IMPROVEMENT.
_FIXED_ROLE_BY_LAB_NUMBER = {
    1: FLEXIBLE_AUTO_RESEARCH,
    2: PERPETUAL_CONSTRUCTION_OPTIMIZATION,
    3: PERPETUAL_RESEARCH_METHODOLOGY,
}


def default_lab_role(lab_number: int) -> str:
    """Return the permanent role assigned to a lab at construction time.

    Lab #1 is always flexible. Labs #2 and #3 have their own dedicated
    fixed programs. Every lab #4 and beyond defaults to
    PERPETUAL_UNIVERSAL_IMPROVEMENT.
    """
    if lab_number < 1:
        raise ValueError("lab_number must be 1 or greater")
    return _FIXED_ROLE_BY_LAB_NUMBER.get(lab_number, PERPETUAL_UNIVERSAL_IMPROVEMENT)


def apply_perpetual_tick(
    multiplier: float, magnitude_per_tick: float, floor: float
) -> float:
    """Advance a running multiplier by one perpetual-program tick.

    Moves ``multiplier`` toward ``floor`` by ``magnitude_per_tick`` but
    never crosses the floor, so "perpetual improvement forever" still has
    a hard, sane limit.
    """
    if magnitude_per_tick < 0:
        raise ValueError("magnitude_per_tick must be non-negative")
    new_value = multiplier - magnitude_per_tick
    return max(new_value, floor)
