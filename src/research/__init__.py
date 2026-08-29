"""Asterion Foundry — Research System.

This package is the Asterion Collegium's research and technology engine.
It is the project's canonical research system: any future lesson that adds
research to the main simulation loop should build on top of this module
instead of inventing a second one.

See ``docs/systems/research.md`` for the full design write-up and
``src/research/data/technologies.json`` for the starter technology set.
"""

from .models import Lab, PilotProjectResult, Scientist, TechLane, TechNode
from .engine import ResearchState, load_technologies

__all__ = [
    "Lab",
    "PilotProjectResult",
    "Scientist",
    "TechLane",
    "TechNode",
    "ResearchState",
    "load_technologies",
]
