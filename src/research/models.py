"""Data structures for the Asterion Collegium research system.

Every class here is a plain ``dataclass``: a labeled container with no
hidden behavior, the same style used in ``src/main.py``'s ``world``
dictionary. Keeping the data simple makes the engine functions in
``engine.py`` easy to read, test, and change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TechLane:
    """One of the four broad research lanes.

    A lane is a category, not a queue: many tech nodes can belong to the
    same lane, and the discovery pool (see ``engine.refresh_draw_pool``)
    rotates a handful of them into view at a time.
    """

    id: str
    name: str
    description: str


@dataclass
class TechNode:
    """A single researchable technology.

    ``tier`` measures how deep a node sits in its lane's prerequisite
    chain (1 = foundational, higher = builds on earlier work). It is a
    dependency depth, not an equipment quality rating — completing a
    tier-3 node does not mean "tier 3 gear" anywhere else in the game.

    ``effect`` must describe a concrete, measurable change to what the
    Directorate can build, move, or fight with. A node with an empty or
    cosmetic-only effect should not exist in the data file.
    """

    id: str
    name: str
    lane: str
    tier: int
    prerequisites: list[str]
    rp_cost: float
    draw_weight: float
    effect: dict
    flavor_text: str = ""
    mutually_exclusive_with: list[str] = field(default_factory=list)
    pilot_project_enabled: bool = False
    pilot_base_success_chance: float = 0.15
    pilot_partial_progress_pct: float = 0.25
    pilot_funding_rp: float = 0.0


@dataclass
class Lab:
    """A physical research facility.

    ``quality`` is a 0.0-1.0 rating of instrumentation and infrastructure.
    ``specialties`` lists the lane ids this lab is built for; a lab can
    still host scientists from other lanes, just less effectively.
    """

    id: str
    name: str
    location: str
    capacity: int
    quality: float
    specialties: list[str] = field(default_factory=list)
    assigned_scientist_ids: list[str] = field(default_factory=list)


@dataclass
class Scientist:
    """An individual Collegium researcher.

    ``skill`` is a 0.0-1.0 rating in their ``specialty_lane``. Assigning a
    scientist outside their specialty is allowed but is not boosted by
    this skill value in the RP-generation formula (see ``engine.py``).
    """

    id: str
    name: str
    specialty_lane: str
    skill: float
    assigned_lab_id: Optional[str] = None


@dataclass
class PilotProjectResult:
    """The outcome of one pilot-project trial (the risk-layer mechanic).

    ``success`` completes the node immediately regardless of remaining
    ``rp_cost``. On failure, ``rp_banked`` is the partial progress kept
    (per ``TechNode.pilot_partial_progress_pct``) and ``rp_lost`` is the
    committed research points that are gone for good — the trial's real
    risk.
    """

    tech_id: str
    success: bool
    chance_used: float
    rp_banked: float
    rp_lost: float
    note: str
