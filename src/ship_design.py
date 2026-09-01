"""Ship design — MK progression and retirement-from-production.

See docs/systems/ship-design.md for the full design this implements.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ALLOWED_CATEGORIES = ("warship", "logistics")

# MK generations progress in this fixed order. "Mark I" is always the
# starting generation for a class already in service.
MK_SEQUENCE = ["Mark I", "Mark II", "Mark III", "Mark IV", "Mark V"]


@dataclass
class ShipClass:
    """A buildable ship class and its current production generation."""

    id: str
    category: str  # must be one of ALLOWED_CATEGORIES
    current_mk: str = "Mark I"
    in_service: list[str] = field(default_factory=list)
    retired_from_production: bool = False

    def __post_init__(self):
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"category must be one of {ALLOWED_CATEGORIES}, got {self.category!r}"
            )


@dataclass
class MkResearchProject:
    """A completed (or pending) MK-improvement research project."""

    id: str
    ship_class_id: str
    from_mk: str
    to_mk: str
    effect: str


def _next_mk(current_mk: str) -> str | None:
    """Return the generation after ``current_mk``, or None if at the end."""
    try:
        idx = MK_SEQUENCE.index(current_mk)
    except ValueError:
        return None
    if idx + 1 >= len(MK_SEQUENCE):
        return None
    return MK_SEQUENCE[idx + 1]


def complete_mk_research(
    ship_class: ShipClass, project: MkResearchProject
) -> tuple[ShipClass, MkResearchProject | None]:
    """Apply a completed MK research project to its ship class.

    Switches ``current_mk`` to the new generation, flags the previous
    production line as retired, and — because this progression is
    self-renewing — returns a stub for the *next* generation's research
    project (or None if the class has reached the end of MK_SEQUENCE).
    Never touches ``in_service``: existing hulls keep their original MK.
    """
    if project.ship_class_id != ship_class.id:
        raise ValueError("project.ship_class_id does not match ship_class.id")
    if project.from_mk != ship_class.current_mk:
        raise ValueError(
            f"project expects class at {project.from_mk!r}, but it is at {ship_class.current_mk!r}"
        )

    ship_class.current_mk = project.to_mk
    ship_class.retired_from_production = True  # the from_mk line is retired

    successor_to_mk = _next_mk(project.to_mk)
    next_project = None
    if successor_to_mk is not None:
        next_project = MkResearchProject(
            id=f"{ship_class.id}_{successor_to_mk.lower().replace(' ', '_')}",
            ship_class_id=ship_class.id,
            from_mk=project.to_mk,
            to_mk=successor_to_mk,
            effect="Incremental improvement — details to be set when researched.",
        )

    return ship_class, next_project


def propose_new_hull_class(existing_classes: list[ShipClass]) -> str | None:
    """Suggest a new hull class only when a genuine roster gap exists.

    Only ever proposes something inside ALLOWED_CATEGORIES. Returns None
    when no gap is evident in this minimal first version (a class already
    exists for each allowed category).
    """
    categories_present = {c.category for c in existing_classes}
    for category in ALLOWED_CATEGORIES:
        if category not in categories_present:
            return f"new_{category}_class_study"
    return None
