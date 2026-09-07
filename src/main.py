"""Asterion Foundry — Lessons 01-04: Forge Production, Freight Logistics,
Collegium Research, and the Directorate's four command-and-control systems
(Penal Code, Lab Specialization, Shipyard Slots, Ship Design/MK).

Run from the repository root with:
    python src/main.py
or on some Windows installations:
    py src/main.py

This program is intentionally small. Its job is to teach one complete loop:
player command -> function -> game data changes -> terminal output.

Current setting:
- Earth holds essential support supplies.
- Mars is humanity's first forge world.
- Mars consumes support supplies, extracts raw metal, and refines part of it.
- Every freighter (CSV Meridian, CSV Concord, and any the shipyard builds
  later) automatically ferries support supplies from Earth to Mars, and
  refined metal back from Mars to Earth, so Mars no longer stalls on its
  own the way it did in Lesson 01. See update_freighters().
- The Asterion Collegium runs a small research lab on Mars. Research
  points (RP) accumulate automatically each step; spending them on a
  technology, or gambling on an early breakthrough with a pilot project,
  is a deliberate player choice. See docs/systems/research.md.
- The Mars Shipyard grows toward a 100-slot target, guarantees a floor of
  warship and logistics slots, and keeps every slot working by rotating
  what it builds. See docs/systems/shipyard.md.
- Ship classes (freighter, light warship) carry an MK generation that
  improves through research and never stops researching once a MK
  completes. See docs/systems/ship-design.md.
- The Asterion Collegium's labs beyond the first are permanently fixed to
  one background improvement program instead of joining the flexible
  research pool. See docs/systems/lab-specialization.md.
- The Directorate Penal Code lets the player charge and sentence named
  individuals under five founding articles, with Servitor Conversion
  gated behind a two-step confirmation. See docs/systems/penal-code.md.

=====================================================================
WHERE EVERYTHING LIVES (read this before you go looking for something)
=====================================================================

Every system below follows the same three-layer pattern used throughout
this file: (1) a **data module** in `src/` that has no knowledge of this
game loop at all and is unit-tested on its own, (2) a **world state
entry** in the `world` dict right below this docstring, and (3) a small
set of **update_*() / show_*() / handle_*() functions** in this file that
connect the two. To customize a system, you almost always want the
constants near the top of its section below, not the data module itself.

| System              | Data module                          | world state key(s)                              | Constants to tweak (this file)                          | Commands |
|---------------------|---------------------------------------|--------------------------------------------------|----------------------------------------------------------|----------|
| Research            | `src/research/`                       | `world["research"]`                              | see `docs/systems/research.md`                            | research, invest, pilot |
| Ship design / MK    | `src/ship_design.py`                  | `world["ship_classes"]`, `world["ship_class_stats"]` | `BASE_BUILD_TIME_STEPS`, MK effect multipliers in `technologies.json` | fleet (view only — MK advances via research) |
| Shipyard slots      | `src/shipyard.py`                     | `world["shipyard"]`, `world["shipyard_slots"]`   | `SHIPYARD_METAL_RESERVE`, `SLOT_EXPAND_COST`, `SHIPYARD_EXPAND_BATCH_SIZE`, `BASE_BUILD_TIME_STEPS`, `SHIPYARD_TARGET_MINIMUM` | shipyard |
| Lab specialization  | `src/research/lab_specialization.py`  | `world["lab_roles"]`, `world["multipliers"]`     | `LAB_BUILD_COST`, `LAB_TICK_INTERVAL_STEPS`, `LAB_TICK_MAGNITUDE`, `LAB_TICK_FLOOR` | labs, build_lab |
| Directorate Penal Code | `src/penal_code.py`                | `world["penal_code"]`, `world["penal_records"]`  | edit `PenalCode.default_code()` in `penal_code.py` to add/change articles | docket, charge, confirm_servitor |
| Tithe System        | none (lives entirely in this file, see docs/systems/tithe-system.md) | `world["tithe_system"]`, `world["tithe_convoys"]`, `world["colonies"]`'s `tithe_grade`/`tithe_shortfall_streak`/`distance_steps` fields, `world["audit_system"]["active_concealments"]` | `TITHE_ELIGIBLE_SPECIALIZATIONS`, `TITHE_GRADE_*`, `TITHE_CYCLE_STEPS`, `TITHE_SHORTFALL_CHARGE_THRESHOLD`, `SURVEY_DISTANCE_RANGE_STEPS` | tithes, colonies (standing), audit (shortfalls) |
| Freighter logistics loop | none (lives entirely in this file) | `world["ships"]` entries with `class_id == "freighter"` | `TRAVEL_TIME_STEPS`, `EARTH_SUPPORT_SUPPLIES_RESERVE`, `FREIGHTER_METAL_PICKUP_RESERVE` | status (view only — runs automatically every `advance`) |

Every one of these constants is defined once, near the top of its
section below, with a comment explaining what raising or lowering it
does. Change the constant, not the function body, when you just want to
retune a number.
"""

import json
import random
from dataclasses import asdict

from research import Lab, ResearchState, Scientist, load_technologies
from research.engine import add_evidence, attempt_pilot_project, generate_rp, invest_rp, refresh_draw_pool
from research.lab_specialization import (
    FLEXIBLE_AUTO_RESEARCH,
    PERPETUAL_CONSTRUCTION_OPTIMIZATION,
    PERPETUAL_RESEARCH_METHODOLOGY,
    PERPETUAL_UNIVERSAL_IMPROVEMENT,
    apply_perpetual_tick,
    default_lab_role,
)
from ship_design import MkResearchProject, ShipClass, complete_mk_research
from research.models import TechNode
from shipyard import LOGISTICS, WARSHIP, Shipyard, expand, next_build_assignment
from penal_code import CAPITAL_TIER, PenalCode, SentencingTier, charge, confirm_capital_sentence

# How many `advance` steps CSV Meridian spends in transit, each direction.
TRAVEL_TIME_STEPS = 2

# ---------------------------------------------------------------------------
# Shipyard tuning — see docs/systems/shipyard.md for the full design.
# Raise SHIPYARD_METAL_RESERVE to make the Directorate hoard more refined
# metal before spending any on new slots. Lower SLOT_EXPAND_COST or raise
# SHIPYARD_EXPAND_BATCH_SIZE to grow the shipyard faster.
# ---------------------------------------------------------------------------
SHIPYARD_METAL_RESERVE = 50.0
SLOT_EXPAND_COST = 30.0
SHIPYARD_EXPAND_BATCH_SIZE = 3
EQUIPMENT_METAL_RESERVE = 20.0
EQUIPMENT_UPGRADE_COST = 40.0
FREIGHTER_METAL_PICKUP_RESERVE = 60.0
# ---------------------------------------------------------------------------
# Earth's support-supply loop (added 2026-09-04, flagged as a design call --
# see the audit doc for the full reasoning, sanity-check the numbers).
#
# Until this change, Earth's support_supplies only ever went DOWN (freighter
# pickup, outpost seeding) with nothing anywhere in the codebase adding to
# it -- a one-way drain that would silently and permanently stall Mars,
# the shipyard, and every colony roughly 260-300 `advance` steps in, with
# no in-game warning. DESIGN_SPINE.md already frames Earth as the
# long-term "food/life-support base" -- this gives it a first, minimal
# version of that role now rather than leaving the drain unaddressed.
#
# EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP: a flat trickle from Earth's
# population and infrastructure, added every step in update_earth().
# Deliberately simple (no scaling, no multiplier hookup yet) -- treat it
# the same way as the colony specializations' "flavor only" notes: a
# placeholder until Earth gets a real economy system of its own.
#
# EARTH_SUPPORT_SUPPLIES_RESERVE: mirrors FREIGHTER_METAL_PICKUP_RESERVE's
# existing pattern (Gotcha #3 in the project brief) -- CSV Meridian now
# only picks up support supplies at Earth *above* this floor, the same way
# it already only picks up refined metal at Mars above its own reserve.
# Without this, one freighter load (up to 200) could still empty Earth in
# a single trip even with production running.
EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP = 15.0
EARTH_SUPPORT_SUPPLIES_RESERVE = 500.0
# How many entries world["events"] keeps before the oldest are dropped --
# see world["events"]'s own init comment for why this log exists.
EVENT_LOG_MAX_ENTRIES = 200
# Fleet caps: once a class hits this many in-service hulls, the shipyard
# stops building more of that class (locked slots for a capped class
# simply idle rather than force a build). Existing hulls above this
# number (from before the cap existed) are left alone -- only future
# builds are affected.
FLEET_TARGET = {"freighter": 6, "light_warship": 10}
# Bug found and fixed 2026-09-04: Shipyard.target_minimum defaulted to 100
# (see src/shipyard.py), a number chosen before FLEET_TARGET existed and
# never reconciled with it. With no combat/hull-loss mechanic yet, fleet
# counts only ever grow toward FLEET_TARGET and then stay there forever --
# so every slot beyond what's needed to reach FLEET_TARGET's 16 total hulls
# was guaranteed to sit permanently idle the moment the cap was hit, while
# expand() kept spending Mars's refined metal to build it. Tying the actual
# target to FLEET_TARGET means expansion can never overshoot into slots
# that have no possible use. If a hull-loss/combat-attrition mechanic is
# added later, revisit this -- it may be worth raising again to give the
# shipyard standing replacement capacity.
SHIPYARD_TARGET_MINIMUM = sum(FLEET_TARGET.values())
# Audit mechanic (Lesson 09): these three numbers are new game balance,
# not reproduced from the compendium -- it establishes the Halvorsen
# precedent narratively but never gives exact odds/amounts. Tune freely.
AUDIT_CONCEALMENT_CHANCE_PER_CYCLE = 0.05
AUDIT_SILENT_DRAIN_RANGE = (1, 3)   # extra support supplies/cycle, concealed
AUDIT_SUCCESS_CHANCE = 0.7           # Bureau's odds of catching it, once triggered
# Design decision made 2026-09-04, explicitly authorized ("patch everything")
# after being flagged in an earlier pass as a balance call rather than a
# clear-cut bug -- tune or revert freely, this is a judgment call, not a
# correctness fix like the others in this file's history.
#
# Bug this closes: `audit <target>` had no cost and no cooldown. With
# AUDIT_SUCCESS_CHANCE at 0.7 and free, instant, unlimited retries, a
# player could spam the same command on the same target every turn and
# the probability of NOT catching a real concealment within a few
# attempts approaches zero (0.3^3 is already under 3%) -- which
# undermines the entire concealment mechanic (both forge_marshal's
# silent drain and the Tithe System's shortfalls), since "the Bureau
# eventually always finds it for free" isn't meaningfully different from
# "there's no concealment risk at all."
#
# AUDIT_COST_SUPPORT_SUPPLIES: spent from Mars's stockpile per real audit
# attempt (one that actually matched an open concealment), win or lose --
# dispatching Bureau investigators has a cost regardless of outcome. An
# audit of a target with nothing to find stays free and instant (no
# resources committed investigating a clean seat/colony).
# AUDIT_COOLDOWN_STEPS: after a real audit attempt on a given target, that
# same target can't be re-audited until this many `advance` steps have
# passed -- this is what actually closes the same-turn-spam loophole; the
# cost alone wouldn't, since a player who can afford it repeatedly could
# still spam within a single turn.
AUDIT_COST_SUPPORT_SUPPLIES = 15.0
AUDIT_COOLDOWN_STEPS = 3

# Persistence (Lesson 10): only the plain-dict portions of world round-trip
# through JSON. See save_game() for what is deliberately left out.
SAVE_FILE = "state.json"

# Colony system (Lesson 11) -- per DESIGN_SPINE.md's survey -> outpost ->
# sustain -> specialize chain (dev order items 9-10). Hive world dropped
# from the specialization list -- explicitly out of first-prototype scope
# per the Design Spine's own guardrails.
SURVEY_COST = 20.0            # refined metal, from Mars
OUTPOST_COST = 60.0           # refined metal, from Mars
OUTPOST_SUPPORT_SEED = 50.0   # support supplies, from Earth -- the expedition's starting stock
SPECIALIZE_COST = 80.0        # refined metal, from Mars
COLONY_SUPPORT_CONSUMPTION = 5.0  # flat per-cycle cost once an outpost exists

# Design decision (2026-09-05, "improve all systems" pass -- Council/colony
# wiring): fortress_world used to be pure flavor because no combat/defense
# mechanic existed to give it a number. Combat still doesn't exist (that's
# DESIGN_SPINE.md dev order item 13), but the Legions' own Council seat
# (Marshal-General) does, and per Downloads\The Directorate\Asterion Foundry
# — Command & Rank Structure.md its mandate is explicitly "stress-testing
# Mars's untested perimeter defense grid" / "Legion Readiness Report...
# garrison, and defense-grid readiness" -- real ground-defense bookkeeping,
# not combat resolution. This gives fortress_world a genuine, accumulating
# stat -- garrison rating -- that Marshal-General's Council entry reports on
# (see show_council()), so the specialization stops being a dead end without
# inventing combat itself. Explicitly named as fleet/combat groundwork, the
# same way shipyard.md's SHIPYARD_TARGET_MINIMUM note already anticipated
# this kind of stat becoming useful again later. Tunable, like every other
# per-cycle rate in this dict.
FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE = 4

# Design decision (2026-09-05): civilian_world's population growth fed
# nothing beyond its own colony's display number and Tithe Grade math (see
# tithe-system.md's "Who owes a tithe" section, which calls this out by
# name as a dead end). Per the same lore source's "Office of Human
# Continuance" material (Branch H, First Steward of Continuance): "each
# colony has a Continuance Hall... one of the first permanent civic
# buildings after life support and industry" -- i.e. a milestone a colony
# grows into, not an instant flag. CONTINUANCE_HALL_POPULATION_THRESHOLD is
# the population a colony needs before it raises one; crossing it is a
# real, one-way, per-colony event (see update_colonies()) that First
# Steward of Continuance's Council entry reports on, instead of population
# just being a number nothing downstream ever reads.
CONTINUANCE_HALL_POPULATION_THRESHOLD = 150

# Design decision (2026-09-05, "Colonial Warden / remaining specializations"
# pass): fuel_world and depot_trade_world were this codebase's last two
# flavor-only specializations, for the same reason fortress_world/
# civilian_world used to be -- no mechanic existed to give either a number.
# Both are explicitly logistics-flavored (a fuel depot, a trade depot), and
# Quartermaster-General's own Council domain ("Freight, convoys, supply
# routes, logistics doctrine") was sitting nearly as thin as Marshal-
# General's was before that seat's fix -- its live_status was a bare
# freighter count with no data behind "supply routes" or "logistics
# doctrine" at all. Following the exact same precedent as
# FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE: give each a real, accumulating,
# per-colony stat and report it on the Council seat whose domain already
# implies it, rather than inventing a new resource-sink mechanic (a real
# fuel-consumption-for-travel system, or a real multi-colony trade network)
# immediately after the stress-test pass whose entire point was closing
# down forever-stalling resource dependencies. Like garrison_rating, this
# is explicitly logistics groundwork a future pass can read (e.g. reducing
# freighter travel time, or a real colony-to-colony trade route), not a
# completed fuel/trade economy on its own. Tunable, like every other
# per-cycle rate in this dict.
FUEL_WORLD_RESERVE_PER_CYCLE = 6
DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE = 6

# Only specializations whose effects map onto resources this codebase
# already tracks get real mechanical numbers. fortress_world, civilian_world,
# fuel_world, and depot_trade_world were all in this position until the
# 2026-09-05 Council-seat wiring pass (see docs/systems/council-seats.md
# for the full writeup of all four).
SPECIALIZATION_EFFECTS = {
    "mining_world": {"raw_metal_per_cycle": 10},
    "forge_world": {"raw_metal_per_cycle": 10, "refined_metal_per_cycle": 6},
    "research_world": {"rp_lane": "physics_and_materials", "rp_per_cycle": 1.0},
    "agri_world": {"support_supplies_per_cycle": 8},  # simplification -- no separate
                                                        # food resource exists; see
                                                        # DESIGN_SPINE.md's note that
                                                        # Earth's food economy is a
                                                        # future, unimplemented system
    "civilian_world": {"population_growth_per_cycle": 10},
    "fuel_world": {"fuel_reserve_per_cycle": FUEL_WORLD_RESERVE_PER_CYCLE},
    "fortress_world": {"garrison_rating_per_cycle": FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE},
    "depot_trade_world": {"trade_throughput_per_cycle": DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE},
}
# How many `advance` steps a slot needs to finish one hull of each class,
# before the lab-specialization construction-time multiplier is applied.
BASE_BUILD_TIME_STEPS = {"freighter": 4, "light_warship": 6}
CATEGORY_TO_CLASS = {LOGISTICS: "freighter", WARSHIP: "light_warship"}

# ---------------------------------------------------------------------------
# The Tithe System (Lesson 12) -- wires the Chancellor-General seat (already
# named in world["council"]/Branch I as "tithes, census, records", with a
# Tithe Clerk rank already in its ladder, but with no live data behind it)
# to real mechanics, and gives colonies' material output somewhere to go
# instead of sitting in a colony-local stockpile nothing else ever reads.
# See docs/systems/tithe-system.md for the full design.
#
# Deliberately per-planet, not a shared pool: each colony keeps producing
# and stockpiling its own resources exactly as before (see
# SPECIALIZATION_EFFECTS/update_colonies() -- unchanged). The tithe is the
# *only* thing that crosses between a colony and the wider Directorate
# economy, and it moves the same way CSV Meridian's cargo does: taken from
# one location's stockpile now, delivered into another's after real
# travel time. This is a first version, not a final one -- flag anything
# that feels off rather than silently retuning it.
#
# Only mining_world and forge_world colonies owe a material tithe right
# now -- they're the only specializations that produce raw_metal/refined_
# metal (see SPECIALIZATION_EFFECTS above). Every other specialization is
# tithe-exempt for the same reason several of them are already "flavor
# only" for production: there's no tithe-able resource type for them yet.
# Population/research/food tithes would need their own design pass once
# those are real, spendable resources rather than a display number.
TITHE_ELIGIBLE_SPECIALIZATIONS = {"mining_world", "forge_world"}

# Tithe Grade: a colony's obligation level, recalculated every tithe cycle
# so it can climb as the colony grows ("the machine demands more" is the
# intended feel). Base level comes from specialization -- forge worlds are
# squeezed harder than mining worlds, matching the Chancellery's doctrine
# that industrial output is taxed heaviest -- plus +1 grade for every
# population threshold crossed, capped at Grade V.
TITHE_GRADE_BASE_BY_SPECIALIZATION = {"forge_world": 2, "mining_world": 1}
TITHE_GRADE_POPULATION_THRESHOLDS = [200, 500, 900]
MAX_TITHE_GRADE = 4
TITHE_GRADE_NAMES = {
    0: "Grade I -- Nominal",
    1: "Grade II -- Standard",
    2: "Grade III -- Elevated",
    3: "Grade IV -- Exacting",
    4: "Grade V -- Crushing",
}
# Flat quota owed per tithe cycle, by grade -- refined metal first, then
# raw metal for the remainder. Flat, not a percentage of current stock: a
# percentage-of-stock levy can never actually produce a shortfall (it
# always takes less than everything a colony has), which would make the
# whole audit/Penal-Code consequence chain below unreachable. A fixed
# quota is what actually creates the risk of falling short.
TITHE_GRADE_QUOTA = {0: 10.0, 1: 20.0, 2: 35.0, 3: 55.0, 4: 80.0}
TITHE_CYCLE_STEPS = 10  # how often tithes are assessed and collected

# Consecutive shortfall cycles (with no successful Bureau audit correcting
# one in between) before the Chancellery escalates a colony's persistent
# shortfall into a formal Penal Code charge. hoarding_of_strategic_supply
# already exists for exactly this ("Withholding rationed or strategic
# material from the Quartermaster Corps") -- reusing it instead of adding
# a parallel punishment system.
TITHE_SHORTFALL_CHARGE_THRESHOLD = 2

# One-way travel time (in `advance` steps) from a newly surveyed colony to
# Mars, randomized at survey time -- you don't know how far into space a
# target actually is until you've surveyed it. This is what makes travel
# time a real, varying, per-destination property instead of one flat
# constant used everywhere: a far colony's tithe leaves on schedule but
# takes many more steps to actually arrive at Mars than a near one's does.
# CSV Meridian's Earth-Mars run deliberately keeps its own fixed
# TRAVEL_TIME_STEPS rather than being folded into this -- it's an
# established, already-named corridor ("the Earth-Mars corridor" in the
# Vigilant's own status), not a newly discovered, unknown-distance target.
SURVEY_DISTANCE_RANGE_STEPS = (3, 12)

# ---------------------------------------------------------------------------
# Lab specialization tuning — see docs/systems/lab-specialization.md.
# LAB_TICK_MAGNITUDE is how much a multiplier improves per tick; raise it
# for a faster-paying-off Collegium. LAB_TICK_FLOOR is the hard limit each
# multiplier can never cross, no matter how many labs or how much time.
# ---------------------------------------------------------------------------
LAB_BUILD_COST = 60.0
LAB_TICK_INTERVAL_STEPS = 5
LAB_TICK_MAGNITUDE = 0.01
LAB_TICK_FLOOR = 0.5

# A dictionary is a labeled container for information.
# `world` holds the entire current state of this tiny simulation.
world = {
    "time": 29,
    "locations": {
        "earth": {
            "name": "Earth",
            "support_supplies": 13165.0,
            "raw_metal": 0,
            "refined_metal": 0,
        },
        "mars": {
            "name": "Mars",
            "support_supplies": 113.0,
            "raw_metal": 225.0,
            "refined_metal": 362.0,
        },
    },
    "ships": {
        "csv_meridian": {
            "name": "CSV Meridian",
            # One of: idle_at_earth, transit_to_mars, idle_at_mars, transit_to_earth
            "status": "idle_at_earth",
            "cargo_capacity": 200,
            "cargo_support_supplies": 0,
            "cargo_refined_metal": 0,
            "travel_remaining": 0,
            "class_id": "freighter",
            "mk": "Mark I",    
        },
                "csv_concord": {
            "name": "CSV Concord",
            "status": "idle_at_mars",
            "cargo_capacity": 200,
            "cargo_support_supplies": 0,
            "cargo_refined_metal": 0,
            "travel_remaining": 0,
            "class_id": "freighter",
            "mk": "Mark I",
        },
        "lws_vigilant": {
            "name": "LWS Vigilant",
            "status": "escorting Earth-Mars corridor",
            "class_id": "light_warship",
            "mk": "Mark I",
            "combat_rating": 40,
        },
        "pc_ward": {"name": "PC Ward", "status": "escorting Earth-Mars corridor"},
        "pc_sentinel": {"name": "PC Sentinel", "status": "on alert, Earth orbit"},
        "pc_bastion": {"name": "PC Bastion", "status": "on alert, Earth orbit"},
    },
    "xenos_fragments": 3,
    # Directorate-wide (not per-colony) ground-defense contribution from
    # Penal Legion sentences currently being served -- see
    # PENAL_LEGION_GARRISON_PER_CYCLE's comment and update_penal_labor()
    # for the full Penal Code labor-economy wiring this is part of.
    "legion_penal_garrison_rating": 0.0,
}

# Sequential hull numbers for ships the shipyard builds beyond the ones
# the game starts with. CSV Meridian is hull 01 of the freighter line.
_hull_counters = {"freighter": 1, "light_warship": 0}


def build_research_state():
    """Create the Asterion Collegium's starting research state.

    One small lab on Mars, staffed by one starting scientist, is enough
    to make research progress from the very first `advance` step. See
    `docs/systems/research.md` for the full design this wires into the
    simulation.
    """
    state = ResearchState.new_game_start()

    lab = Lab(
        id="mars_collegium_lab",
        name="Mars Collegium Laboratory",
        location="mars",
        capacity=4,
        quality=0.5,
        specialties=["physics_and_materials", "logistics_and_industry"],
    )
    state.add_lab(lab)

    scientist = Scientist(
        id="savant_voss",
        name="Savant Voss",
        specialty_lane="physics_and_materials",
        skill=0.6,
    )
    lab.assigned_scientist_ids.append(scientist.id)
    state.add_scientist(scientist)

    for lane_id in state.lanes:
        refresh_draw_pool(state, lane_id)

    return state


def build_ship_and_facility_state():
    """Create the starting state for ship classes, the shipyard, labs,
    lab-specialization multipliers, and the Penal Code.

    See docs/systems/ship-design.md, docs/systems/shipyard.md,
    docs/systems/lab-specialization.md, and docs/systems/penal-code.md
    for the full design each of these wires into the simulation.
    """
    world["ship_classes"] = {
        "freighter": ShipClass(
            id="freighter", category="logistics", current_mk="Mark I", in_service=["CSV Meridian", "CSV Concord"],
        ),
        "light_warship": ShipClass(
            id="light_warship", category="warship", current_mk="Mark I", in_service=["LWS Vigilant"],
        ),
    }

    # Stats used whenever the shipyard completes a new hull of a class.
    # Ship-design MK research raises these; see _apply_ship_design_effect().
    world["ship_class_stats"] = {
        "freighter": {"cargo_capacity": 200},
        "light_warship": {"combat_rating": 40},
    }

    # One flexible slot to start, matching the shipyard's single serial
    # production line before any expansion order is placed.
    world["shipyard"] = Shipyard(
        location="mars", slots_total=1, flexible=1, target_minimum=SHIPYARD_TARGET_MINIMUM
    )
    world["shipyard_slots"] = [
        {"locked_category": None, "building_class_id": None, "steps_remaining": 0}
    ]

    # Lab #1 is always the flexible auto-research lab (see build_research_state).
    world["lab_roles"] = {"mars_collegium_lab": FLEXIBLE_AUTO_RESEARCH}
    # Cycle-29 sync (Lesson 05): these three numbers aren't guesses — each
    # one ticks via Collegium Lab #2/#3 (construction/research time, -2%
    # every 5 cycles) or Lab #4-#6 (universal efficiency). In this codebase
    # lower is better on all three (see show_labs()'s own printed text and
    # update_mars()'s cost formula) — a lower universal_efficiency_multiplier
    # means a cheaper Mars support cost per cycle.
    world["multipliers"] = {
        "construction_time_multiplier": 0.98,   # lower = faster builds
        "research_time_multiplier": 0.98,       # lower = faster research
        "universal_efficiency_multiplier": 1.0,    # lower = cheaper Mars support cost
    }

    world["penal_code"] = PenalCode.default_code()
    world["penal_records"] = []

        # Command Structure (Lesson 06). Council seats, Branches A-K with rank
    # ladders, and the Vigil's deliberate exclusion -- all per the Master
    # Compendium's Council/Branch breakdown. No seat holders are invented
    # here beyond what the compendium actually names (Grand Director,
    # Forge-Marshal Halvorsen) -- every other seat is explicitly "Vacant"
    # rather than guessed, since the compendium doesn't name who holds them.
    world["council"] = {
        "first_minister": {"holder": "Vacant", "branch": "E",
                            "domain": "Civil government, population, food & life support, policy"},
        "forge_marshal": {"holder": "Halvorsen", "branch": "B",
                           "domain": "Forge worlds' heavy industry, refining, fabrication, shipbuilding"},
        "high_savant": {"holder": "Vacant", "branch": "C", "domain": "The Asterion Collegium (research)"},
        "grand_admiral": {"holder": "Vacant", "branch": "A",
                           "domain": "Military fleets, escorts, naval doctrine"},
        "quartermaster_general": {"holder": "Vacant", "branch": "F",
                                   "domain": "Freight, convoys, supply routes, logistics doctrine"},
        "colonial_warden": {"holder": "Vacant", "branch": "D",
                             "domain": "Survey, colonization, colony specialization"},
        "marshal_general": {"holder": "Vacant", "branch": "G", "domain": "The Legions (ground forces)"},
        "first_steward_of_continuance": {"holder": "Vacant", "branch": "H",
                                          "domain": "Office of Human Continuance -- civic culture, education, memory"},
        "chancellor_general": {"holder": "Vacant", "branch": "I",
                                "domain": "The Chancellery -- tithes, census, records, cross-branch reporting"},
        "provost_general": {"holder": "Vacant", "branch": "J",
                             "domain": "The Bureau -- counter-espionage, loyalty oversight, internal security"},
    }

    # world["branches"] holds every branch's rank ladder, keyed by its
    # letter -- including K, even though Branch K has no Council seat.
    # This is deliberate: a branch existing and a branch having a Council
    # seat are two different facts, and K is proof they don't always
    # coincide.
    world["branches"] = {
        "A": {"name": "Navy", "council_seat": "grand_admiral",
              "ranks": ["Fleet Marshal (Dominion)", "Sector Admiral", "Admiral", "Commodore", "Captain",
                        "Commander", "Lieutenant", "Ensign", "Chief Petty Officer", "Crewman"],
              "civilian_freight_ranks": ["Convoy Marshal", "Master", "First Officer", "Chief Engineer", "Deckhand"]},
        "B": {"name": "Forge & Industry", "council_seat": "forge_marshal",
              "ranks": ["Dominion Forge-Marshal", "Sector Forge Marshal", "Forge Governor", "Foundry Overseer",
                        "Shift Marshal", "Line Chief", "Forgehand", "Laborer"]},
        "C": {"name": "The Asterion Collegium", "council_seat": "high_savant",
              "ranks": ["Dominion Savant", "Sector Savant", "Savant-Director", "Senior Archivist",
                        "Archivist", "Adept"]},
        "D": {"name": "Colonial Administration", "council_seat": "colonial_warden",
              "ranks": ["Dominion Warden", "Sector Warden", "Survey Commander", "Colony Governor",
                        "Settlement Marshal", "Foreman"]},
        "E": {"name": "Civil Government", "council_seat": "first_minister",
              "ranks": ["Dominion Minister", "Sector Minister", "Planetary Governor", "Regional Governor", "Clerk"],
              "earth_only_ranks": ["Minister of Population & Labor", "Minister of Food & Life Support",
                                    "Minister of Policy & Records"]},
        "F": {"name": "Logistics & Supply", "council_seat": "quartermaster_general",
              "ranks": ["Dominion Quartermaster", "Sector Quartermaster", "Depot Master", "Convoy Marshal"]},
        "G": {"name": "The Legions", "council_seat": "marshal_general",
              "ranks": ["Dominion Marshal", "Sector Marshal", "Legion Commander", "Colonel", "Captain",
                        "Lieutenant", "Sergeant", "Trooper"]},
        "H": {"name": "Office of Human Continuance", "council_seat": "first_steward_of_continuance",
              "ranks": ["Dominion Steward", "Sector Steward", "World Curator", "Civic Advocate",
                        "Archivist-Aide", "Candidate"]},
        "I": {"name": "The Chancellery", "council_seat": "chancellor_general",
              "ranks": ["Dominion Chancellor", "Sector Chancellor", "World Registrar", "Tithe Clerk",
                        "Scrivener", "Adept-Scrivener"]},
        "J": {"name": "The Bureau", "council_seat": "provost_general",
              "ranks": ["Dominion Provost", "Sector Provost", "Station Chief", "Case Officer",
                        "Field Agent", "Informant (unranked)"]},
        "K": {"name": "The Vigil", "council_seat": None,
              "ranks": ["Seeker", "Seeker's Hand", "Agents (ad hoc)"],
              "note": "No Council seat -- deliberately outside the ten-seat structure. Includes the "
                      "ultra-secret Silent Blades cadre, intentionally left undetailed."},
    }

    world["vigil"] = {
        "top_rank": "First Seekers",
        "reports_to": "Grand Director directly, privately",
        "note": "Overlaps in jurisdiction with the Bureau (Branch J); mutual distrust between the two "
                "is intentional, not a bug to fix.",
    }

    # Entities outside the Directorate entirely -- not branches, not
    # subordinate to any Council seat. Kept separate from world["branches"]
    # for the same reason the Vigil is kept separate from world["council"]:
    # the data structure itself should reflect what's actually outside
    # the chain of command, not just note it in a comment.
    world["outside_directorate"] = {
        "chartered_trading_houses": "Independent merchant houses, tithe-paying but self-governing.",
        "wayfarers_guild": "Star-lane charting, relay stations. Parent branch unresolved -- explicitly "
                            "undecided between Logistics (F) and the Collegium (C); do not hard-code it "
                            "under either.",
    }

    # Standing Orders (Lesson 07): the infrastructure-expansion order
    # already runs implicitly inside update_shipyard() -- this makes it
    # visible and logged, rather than adding a second competing mechanism.
    # The equipment order is genuinely new behavior; nothing upgraded
    # equipment before this.
    world["standing_orders"] = {
        "infrastructure_expansion": {
            "status": "active",
            "policy": "Whenever Mars refined metal exceeds routine operational needs, "
                      "queue additional infrastructure rather than letting surplus sit idle.",
            "priority": ["1. Correct identified bottlenecks", "2. Defenses", "3. General expansion"],
            "log": [],
        },
        "equipment_and_asset_upgrades": {
            "status": "active",
            "policy": "As refined metal allows, incrementally upgrade the quality of equipment "
                      "already fielded across the empire.",
            "priority": ["1. Frontline/combat equipment", "2. Industrial equipment",
                         "3. Administrative/personal equipment"],
            "log": [],
        },
    }

    world["equipment_status"] = {
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

    # Directorate Code (Lesson 08): constitutional/structural law, distinct
    # from the Penal Code (individual criminal offenses). Cross-referenced
    # via enforced_by rather than merged -- they're related, not the same
    # system. Two articles are honestly left with gaps below; see chat notes.
    world["directorate_code"] = {
        "sovereignty": {
            "name": "Sovereignty",
            "description": "All authority within Directorate space flows from the Grand Director.",
            "enforced_by": ["treason_against_the_directorate"],
        },
        "honest_reporting": {
            "name": "Honest Reporting",
            "description": "Concealed or falsified figures are discoverable through audits; correction "
                          "is rewarded over concealment (the Halvorsen precedent).",
            "enforced_by": [],  # deliberately empty -- handled via audit/correction, not the Penal Code
        },
        "requisition_authority": {
            "name": "Requisition Authority",
            "description": "The Directorate's standing right to requisition resources and labor as needed.",
            "enforced_by": ["hoarding_of_strategic_supply"],
        },
        "chain_of_command": {
            "name": "Chain of Command",
            "description": "Orders flow down an unambiguous hierarchy; no intermediary may be bypassed "
                          "or defied.",
            "enforced_by": ["insubordination_under_command", "desertion_of_post"],
        },
        "xenos_contact_protocol": {
            "name": "Xenos Contact Protocol",
            "description": "Mandated procedure for any confirmed non-human contact.",
            "enforced_by": [],  # no first-contact incident has occurred since cycle 3
        },
    }

    world["audit_system"] = {
        "doctrine": "The Directorate rewards correction over concealment; audits exist to "
                    "surface honest bad news, not to punish it (the Halvorsen precedent).",
        # Generalized (Lesson 12) from a single slot to a list: forge_marshal's
        # silent metal drain and any number of colonies' tithe shortfalls can
        # now be open at the same time, each tagged by "kind" and looked up
        # by seat_id (forge_marshal) or colony_id (tithe shortfalls).
        "active_concealments": [],
        "log": [],
        # Added 2026-09-04 alongside AUDIT_COST_SUPPORT_SUPPLIES /
        # AUDIT_COOLDOWN_STEPS -- see handle_audit()'s docstring for why.
        # Keyed by target (seat_id or colony_id), value is the world["time"]
        # of that target's last real audit attempt (one that actually
        # matched an open concealment and rolled/charged for it).
        "last_audit_step": {},
    }

    # world["colonies"] is empty at cycle 29 -- nothing in the compendium
    # describes a second colony existing yet, so this starts genuinely
    # empty rather than seeded, unlike everything else synced tonight.
    world["colonies"] = {}

    # Tithe System (Lesson 12) -- see docs/systems/tithe-system.md.
    world["tithe_system"] = {
        "doctrine": "Every material world owes the Directorate its due. Correction is "
                    "rewarded over concealment, the same as any other Chancellery audit.",
        "log": [],
    }
    # In-transit tithe deliveries: [{colony_id, colony_name, refined_metal,
    # raw_metal, steps_remaining}, ...]. Advanced every step in
    # update_tithe_convoys(), independent of the tithe cycle itself.
    world["tithe_convoys"] = []
    # Added 2026-09-07 (audit section 6.3's recommendation): a persistent
    # log of events worth noticing, distinct from the constant stream of
    # routine print() output every update_*() function already produces.
    # Without this, an alert (Mars stalling, a concealment caught, a
    # colony running short) only ever existed as one line scrolling past
    # in the terminal -- gone for good if you weren't watching right when
    # it printed. log_event() appends here AND prints, so nothing about
    # existing output changes; `events` just gives a way to look back.
    # Capped at EVENT_LOG_MAX_ENTRIES so a very long playthrough doesn't
    # grow this without bound.
    world["events"] = []
    # Cycle-29 sync (Lesson 05): the compendium says Labs #2-#6 are already
    # built and operational; Lab #7 is still under construction, so it's
    # deliberately NOT added here — build_lab (in-game command) adds it later.
    # capacity=0 because these are "perpetual program" labs (see
    # docs/systems/lab-specialization.md) — they don't hold researcher
    # slots the way Lab #1 does, they just tick a multiplier on a timer.
    for lab_number in range(2, 7):
        role = default_lab_role(lab_number)
        lab_id = f"collegium_lab_{lab_number:02d}"
        lab = Lab(
            id=lab_id, name=f"Collegium Laboratory {lab_number}",
            location="mars", capacity=0, quality=0.5, specialties=[],
        )
        world["research"].add_lab(lab)
        world["lab_roles"][lab_id] = role 

def show_status():
    """Print the resource stockpiles for every current location, every
    freighter's status, and one-line summaries of research, the
    shipyard, the Collegium's labs, and the Penal Code docket.
    """
    print(f"\n=== ASTERION FOUNDRY // SIMULATION STEP {world['time']} ===")

    # `.values()` gives us each location dictionary stored in `locations`.
    for location in world["locations"].values():
        print(
            f"{location['name']}: "
            f"Support supplies {location['support_supplies']} | "
            f"Raw metal {location['raw_metal']} | "
            f"Refined metal {location['refined_metal']}"
        )

    # Bug found and fixed 2026-09-04: this used to print only
    # world["ships"]["csv_meridian"], so CSV Concord and any
    # shipyard-built freighter were invisible here even after
    # update_freighters() started actually running their supply routes.
    # Every freighter gets its own line now.
    status_labels = {
        "idle_at_earth": "docked at Earth, loading",
        "idle_at_mars": "docked at Mars, loading",
    }
    for ship in world["ships"].values():
        if ship.get("class_id") != "freighter":
            continue
        if ship["status"] in status_labels:
            label = status_labels[ship["status"]]
        else:
            destination = "Mars" if ship["status"] == "transit_to_mars" else "Earth"
            label = f"in transit to {destination} ({ship['travel_remaining']} step(s) remaining)"
        print(
            f"{ship['name']}: {label} | "
            f"Cargo: {ship['cargo_support_supplies']} support supplies, "
            f"{ship['cargo_refined_metal']} refined metal"
        )

    research_state = world["research"]
    total_banked = sum(research_state.rp_stockpile.values())
    print(
        f"Asterion Collegium: {total_banked:.1f} RP banked across all lanes, "
        f"{len(research_state.completed)} technologies completed. "
        "Type 'research' for details."
    )

    yard = world["shipyard"]
    print(
        f"Mars Shipyard: {yard.slots_total}/{yard.target_minimum} slots "
        f"({yard.warship_locked} warship-locked, {yard.logistics_locked} logistics-locked, "
        f"{yard.flexible} flexible). Type 'shipyard' for details."
    )

    print(
        f"Collegium Laboratories: {len(world['lab_roles'])} operational. "
        "Type 'labs' for details."
    )

    if world["penal_records"]:
        print(
            f"Directorate Docket: {len(world['penal_records'])} record(s) on file. "
            "Type 'docket' for details."
        )

def _completed_effect_multiplier(effect_key, default=1.0):
    """Combine 'effect_key' across every completed research node that 
    defines it. Nodes without that key are simply skipped
    """
    multiplier = default
    for tech_id in world["research"].completed:
        effect = world["research"].nodes[tech_id].effect
        if effect_key in effect:
            multiplier *= effect[effect_key]
    return multiplier

def update_mars():
    mars = world["locations"]["mars"]
    consumption_multiplier = _completed_effect_multiplier("support_supply_consumption_multiplier")
    yield_multiplier = _completed_effect_multiplier("refined_metal_yield_multiplier")

    cost = max(1, round(10 * world["multipliers"]["universal_efficiency_multiplier"] * consumption_multiplier))

    if mars["support_supplies"] >= cost:
        mars["support_supplies"] -= cost
        mars["raw_metal"] += 15
        mars["raw_metal"] -= 10
        refined_gain = round(8 * yield_multiplier)
        mars["refined_metal"] += refined_gain
        print(
            f"Mars forge complexes consumed {cost} support supplies, "
            f"extracted 15 raw metal, and refined 10 raw metal into {refined_gain} refined metal."
        )
    else:
        log_event("ALERT: Mars lacks support supplies. Forge complexes are idle; extraction and refining have stopped.")

def seed_completed_research():
    """Fast-forward the Collegium to its cycle-29 research state, using
    invest_rp() -- the same function the `invest` command calls -- so
    seeding goes through the exact completion path the game already
    trusts, rather than poking internal state directly.

    Only two of the narrative's completed techs have a real equivalent
    in this code's tech tree; see the Lesson 05 chat notes for why.
    """
    state = world["research"]

    completed_at_seed = [
        "pm_refined_alloy_process",     # closest equivalent to "Refinement Process Optimization"
        "bc_closed_loop_life_support",  # closest equivalent to "Servitor & Robotic Labor Automation"
    ]
    for tech_id in completed_at_seed:
        node = state.nodes[tech_id]
        state.rp_stockpile[node.lane] = node.rp_cost
        completed = invest_rp(state, tech_id, node.rp_cost)
        if completed:
            refresh_draw_pool(state, node.lane)
            print(f"[seed] {node.name} marked complete.")
        else:
            print(f"[seed] WARNING: {node.name} did not complete — check rp_cost.")    

def update_earth():
    """Run one Earth update: a flat trickle of support supplies from
    Earth's population and infrastructure base.

    This is a deliberately minimal first version of Earth's own economy
    (see EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP's comment above for
    the full reasoning) -- it exists to stop support_supplies from being
    a one-way drain, not to be Earth's final production model.
    """
    earth = world["locations"]["earth"]
    earth["support_supplies"] += EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP
    print(
        f"Earth's population and infrastructure base produces "
        f"{EARTH_SUPPORT_SUPPLIES_PRODUCTION_PER_STEP:.0f} support supplies this step "
        f"(reserves: {earth['support_supplies']:.0f})."
    )


def log_event(text):
    """Print `text` (unchanged behavior) and also append it to
    world["events"] as {cycle, text}, trimming to EVENT_LOG_MAX_ENTRIES.
    See world["events"]'s own init comment for why this exists. Call
    this instead of a bare print() for anything a player could
    reasonably want to look back at later -- a stall, a concealment
    caught, a milestone reached -- not for routine per-step flavor text
    (a normal freighter run, a normal tithe payment) that's expected and
    frequent enough that logging every instance would just be noise.
    """
    world["events"].append({"cycle": world["time"], "text": text})
    if len(world["events"]) > EVENT_LOG_MAX_ENTRIES:
        world["events"] = world["events"][-EVENT_LOG_MAX_ENTRIES:]
    print(text)


def show_events(args=None):
    """Print the most recent logged events, newest last. Defaults to the
    last 10; `events <n>` shows the last n instead.
    """
    count = 10
    if args:
        try:
            count = int(args[0])
        except ValueError:
            print(f"Usage: events [count]. '{args[0]}' isn't a number.")
            return

    recent = world["events"][-count:]
    print(f"\n=== EVENTS (last {len(recent)} of {len(world['events'])}) ===")
    if not recent:
        print("  No events logged yet.")
        return
    for entry in recent:
        print(f"  Cycle {entry['cycle']}: {entry['text']}")


def withdraw_above_reserve(location, resource, reserve, capacity):
    """Withdraw up to `capacity` units of `resource` from `location`,
    never dropping its stock below `reserve`. Returns the amount
    actually withdrawn (may be less than `capacity` if there isn't that
    much surplus). Mutates `location` in place.

    Added 2026-09-07 as the first piece of a shared resource-transfer
    path (audit section 6.1's recommendation): the freighter loop's
    Earth pickup and Mars pickup were previously two separately
    hand-written copies of the exact same "never drain below a reserve
    floor" arithmetic (see FREIGHTER_METAL_PICKUP_RESERVE's and
    EARTH_SUPPORT_SUPPLIES_RESERVE's own comments for why that floor
    exists at each location) -- one audited function now backs both,
    and any future pickup-style system (a second freight route, a
    colony-to-colony transfer) gets the reserve-respecting behavior for
    free instead of needing to reimplement it correctly.
    """
    available = max(0.0, location[resource] - reserve)
    amount = min(capacity, available)
    location[resource] -= amount
    return amount


def deposit(location, resource, amount):
    """Add `amount` of `resource` into `location`. Added alongside
    withdraw_above_reserve() (see its docstring) as the single audited
    path a delivery should go through, instead of every delivery site
    (freighter unload, tithe convoy arrival, and any future one) writing
    its own `location[resource] += amount`.
    """
    location[resource] += amount


def update_freighters():
    """Run one logistics step for every freighter in `world["ships"]`.

    Each freighter independently cycles: load support supplies at Earth,
    travel to Mars, unload, load refined metal at Mars, travel back to
    Earth, unload, and repeat. See DESIGN_SPINE.md's "First loop" for the
    design this implements. There is no player command for this yet —
    like Mars's forge complex, it simply runs every time the simulation
    advances.

    Bug found and fixed 2026-09-04: this used to be update_csv_meridian(),
    hardcoded to `world["ships"]["csv_meridian"]` alone. CSV Concord (a
    second freighter present since the very start of the game) and every
    freighter the shipyard built afterward sat "idle_at_mars" forever —
    delivered into the fleet but never touched by any update function, so
    they could never actually run a supply route. Fixed by looping over
    every ship with `class_id == "freighter"` instead of one hardcoded
    key; each freighter carries its own `status`/`cargo_*`/
    `travel_remaining` fields already (set at creation in both the
    starting `world["ships"]` literal and `_complete_ship_build()`), so no
    other state needed to change. Ships are processed in `world["ships"]`
    insertion order, so if two freighters are both loading from the same
    reserve-limited stockpile on the same step, the first one processed
    gets first claim on what's above the reserve — the same
    first-come-first-served pattern `update_shipyard()`'s no-idle
    assignment already uses.
    """
    for ship in world["ships"].values():
        if ship.get("class_id") != "freighter":
            continue

        if ship["status"] == "idle_at_earth":
            earth = world["locations"]["earth"]
            # Mirrors FREIGHTER_METAL_PICKUP_RESERVE's pattern at Mars: never
            # load Earth down below its own reserve floor, even if the ship
            # has room to carry more.
            load_amount = withdraw_above_reserve(
                earth, "support_supplies", EARTH_SUPPORT_SUPPLIES_RESERVE, ship["cargo_capacity"]
            )
            ship["cargo_support_supplies"] = load_amount
            ship["status"] = "transit_to_mars"
            ship["travel_remaining"] = TRAVEL_TIME_STEPS
            print(f"{ship['name']} loaded {load_amount} support supplies at Earth and departed for Mars.")

        elif ship["status"] == "transit_to_mars":
            ship["travel_remaining"] -= 1
            if ship["travel_remaining"] <= 0:
                mars = world["locations"]["mars"]
                delivered = ship["cargo_support_supplies"]
                deposit(mars, "support_supplies", delivered)
                ship["cargo_support_supplies"] = 0
                ship["status"] = "idle_at_mars"
                print(f"{ship['name']} arrived at Mars and unloaded {delivered} support supplies.")
            else:
                print(f"{ship['name']} is in transit to Mars ({ship['travel_remaining']} step(s) remaining).")

        elif ship["status"] == "idle_at_mars":
            mars = world["locations"]["mars"]
            load_amount = withdraw_above_reserve(
                mars, "refined_metal", FREIGHTER_METAL_PICKUP_RESERVE, ship["cargo_capacity"]
            )
            ship["cargo_refined_metal"] = load_amount
            ship["status"] = "transit_to_earth"
            ship["travel_remaining"] = TRAVEL_TIME_STEPS
            print(f"{ship['name']} loaded {load_amount} refined metal at Mars and departed for Earth.")

        elif ship["status"] == "transit_to_earth":
            ship["travel_remaining"] -= 1
            if ship["travel_remaining"] <= 0:
                earth = world["locations"]["earth"]
                delivered = ship["cargo_refined_metal"]
                deposit(earth, "refined_metal", delivered)
                ship["cargo_refined_metal"] = 0
                ship["status"] = "idle_at_earth"
                print(f"{ship['name']} arrived at Earth and delivered {delivered} refined metal.")
            else:
                print(f"{ship['name']} is in transit to Earth ({ship['travel_remaining']} step(s) remaining).")


def update_research():
    """Run one Collegium research step: generate RP for every staffed lab.

    RP accumulates automatically each step, the same way Mars production
    does. Spending it — via the `invest` or `pilot` commands — is always
    a deliberate player choice, never automatic.

    The lab-specialization research-time multiplier (see
    docs/systems/lab-specialization.md) is applied here as an effective
    dt: as the multiplier improves toward its floor of 0.5, research
    accumulates up to twice as fast.
    """
    dt = 1.0 / max(world["multipliers"]["research_time_multiplier"], 0.01)
    generated = generate_rp(world["research"], dt=dt)
    produced = {lane: amount for lane, amount in generated.items() if amount > 0}

    if produced:
        parts = ", ".join(f"{lane}: +{amount:.1f} RP" for lane, amount in produced.items())
        print(f"Asterion Collegium generated research points ({parts}).")
    else:
        print("Asterion Collegium labs are unstaffed or idle; no research points generated.")


def update_lab_specialization():
    """Advance every fixed-role lab's perpetual program by one tick.

    Ticks happen every LAB_TICK_INTERVAL_STEPS simulation steps, not
    every step, so the Collegium's background improvement is gradual.
    See docs/systems/lab-specialization.md for the full design.
    """
    if world["time"] % LAB_TICK_INTERVAL_STEPS != 0:
        return

    multipliers = world["multipliers"]
    ticked_any = False
    for role in world["lab_roles"].values():
        if role == PERPETUAL_CONSTRUCTION_OPTIMIZATION:
            multipliers["construction_time_multiplier"] = apply_perpetual_tick(
                multipliers["construction_time_multiplier"], LAB_TICK_MAGNITUDE, LAB_TICK_FLOOR
            )
            ticked_any = True
        elif role == PERPETUAL_RESEARCH_METHODOLOGY:
            multipliers["research_time_multiplier"] = apply_perpetual_tick(
                multipliers["research_time_multiplier"], LAB_TICK_MAGNITUDE, LAB_TICK_FLOOR
            )
            ticked_any = True
        elif role == PERPETUAL_UNIVERSAL_IMPROVEMENT:
            multipliers["universal_efficiency_multiplier"] = apply_perpetual_tick(
                multipliers["universal_efficiency_multiplier"], LAB_TICK_MAGNITUDE, LAB_TICK_FLOOR
            )
            ticked_any = True

    if ticked_any:
        print(
            "Fixed-role laboratories advance their perpetual programs "
            f"(construction x{multipliers['construction_time_multiplier']:.2f}, "
            f"research x{multipliers['research_time_multiplier']:.2f}, "
            f"efficiency x{multipliers['universal_efficiency_multiplier']:.2f})."
        )


def _register_next_mk_node(class_id, next_project):
    """Insert the successor MK research project into the Collegium's data
    so it is immediately investable — the self-renewing part of MK
    progression. See docs/systems/ship-design.md.
    """
    state = world["research"]
    ship_class = world["ship_classes"][class_id]
    lane_id = "logistics_and_industry" if ship_class.category == "logistics" else "military_doctrine"
    stat_key = "cargo_capacity_multiplier" if class_id == "freighter" else "combat_rating_multiplier"
    effect_key = f"{class_id}_{stat_key}"

    new_node = TechNode(
        id=next_project.id,
        name=f"{class_id.replace('_', ' ').title()} {next_project.to_mk} Hull Design",
        lane=lane_id,
        tier=2,
        prerequisites=[],
        rp_cost=150.0,
        draw_weight=2.0,
        effect={
            "ship_design_mk_upgrade": class_id,
            "to_mk": next_project.to_mk,
            effect_key: 1.15,
        },
        flavor_text=(
            f"Incremental refinement of the {class_id.replace('_', ' ')} production line, "
            f"superseding {next_project.from_mk}."
        ),
    )
    state.nodes[new_node.id] = new_node
    lane_pool = state.active_pool.setdefault(lane_id, [])
    if new_node.id not in lane_pool:
        lane_pool.append(new_node.id)
    print(f"New research now available: {new_node.name} (lane: {lane_id}). Type 'research' to view it.")


def _apply_ship_design_effect(tech_id, node):
    """Apply a completed research node's effect, if it names one this
    game loop knows how to apply.

    Recognized effect keys (see docs/systems/ship-design.md and
    docs/systems/shipyard.md):
      - "ship_design_mk_upgrade": <class_id>  (with "to_mk")
            Advances that ship class's production MK, retires the old
            production line, and registers the self-renewing successor
            research project.
      - "<class_id>_cargo_capacity_multiplier" / "..._combat_rating_multiplier"
            Multiplies the named stat used for future hulls of that class.

    Returns the id of a newly-registered MK successor node, if this call
    registered one, else None -- see refresh_draw_pool()'s guaranteed_ids
    for why the caller needs this (bug found and fixed 2026-09-04: a
    freshly-registered node could otherwise be silently dropped by the
    very next draw-pool refresh the caller runs right after this).
    """
    effect = node.effect
    newly_registered_id = None

    for class_id in world["ship_class_stats"]:
        cargo_key = f"{class_id}_cargo_capacity_multiplier"
        combat_key = f"{class_id}_combat_rating_multiplier"
        if cargo_key in effect:
            stats = world["ship_class_stats"][class_id]
            stats["cargo_capacity"] = round(stats["cargo_capacity"] * effect[cargo_key])
            print(f"{class_id} cargo capacity increased to {stats['cargo_capacity']} for future construction.")
        if combat_key in effect:
            stats = world["ship_class_stats"][class_id]
            stats["combat_rating"] = round(stats["combat_rating"] * effect[combat_key])
            print(f"{class_id} combat rating increased to {stats['combat_rating']} for future construction.")

    # Note: the legacy li_cargo_hold_optimization node (Lesson 03) already
    # uses the key "freighter_cargo_capacity_multiplier", which the generic
    # per-class loop above matches directly (class_id "freighter" +
    # "_cargo_capacity_multiplier") — no separate handling needed for it.

    if "ship_design_mk_upgrade" in effect:
        class_id = effect["ship_design_mk_upgrade"]
        ship_class = world["ship_classes"][class_id]
        project = MkResearchProject(
            id=tech_id,
            ship_class_id=class_id,
            from_mk=ship_class.current_mk,
            to_mk=effect["to_mk"],
            effect=node.flavor_text,
        )
        updated_class, next_project = complete_mk_research(ship_class, project)
        world["ship_classes"][class_id] = updated_class
        print(
            f"{class_id} production line upgraded to {effect['to_mk']}. "
            "Previous MK's production line is retired; existing hulls are unaffected."
        )
        if next_project is not None:
            _register_next_mk_node(class_id, next_project)
            newly_registered_id = next_project.id
        else:
            print(f"{class_id} has reached its final researchable generation ({effect['to_mk']}).")

    return newly_registered_id


def show_research():
    """Print the Collegium's current research status: banked RP per lane,
    each lane's active discovery pool, and completed technologies.
    """
    state = world["research"]
    print("\n=== ASTERION COLLEGIUM RESEARCH STATUS ===")

    for lane_id, lane in state.lanes.items():
        banked = state.rp_stockpile.get(lane_id, 0.0)
        print(f"\n{lane.name} [{lane_id}] - {banked:.1f} RP banked")

        pool = state.active_pool.get(lane_id, [])
        if not pool:
            print("  No eligible technologies available right now.")
            continue

        for index, tech_id in enumerate(pool, start=1):
            node = state.nodes[tech_id]
            invested = state.rp_invested.get(tech_id, 0.0)
            pilot_note = " [pilot project available]" if node.pilot_project_enabled else ""
            print(
                f"  {index}. {node.name} - {invested:.1f}/{node.rp_cost:.0f} RP "
                f"(tier {node.tier}){pilot_note}"
            )
            print(f"     Effect: {node.effect}")

    if state.completed:
        print("\nCompleted technologies:")
        for tech_id in sorted(state.completed):
            print(f"  - {state.nodes[tech_id].name}")

    print(
        "\nUse 'invest <lane_id> <pool position>' to spend banked RP, "
        "or 'pilot <lane_id> <pool position>' to gamble on an early breakthrough."
    )


def _guaranteed_dynamic_node_ids(state, lane_id):
    """Every node currently in this lane's active_pool that isn't part of
    the base technology set from technologies.json -- i.e. every
    dynamically-registered MK-successor node (see _register_next_mk_node())
    still sitting in the pool, uninvested and uncompleted.

    Bug found and fixed 2026-09-05 (stress-test pass): handle_invest()/
    handle_pilot() used to pass guaranteed_ids covering ONLY the node just
    registered THIS call, protecting it from exactly one refresh_draw_pool()
    call -- the one immediately following its own registration. Any LATER,
    unrelated completion in the same lane called refresh_draw_pool() with
    no guaranteed_ids at all, so a still-0-RP dynamic node from an earlier
    call competed on equal footing with every other eligible candidate and
    could be evicted -- confirmed at ~16% (49/300 trials) with a
    completely ordinary sequence: complete an MK node, then complete two
    unrelated same-lane techs before ever touching the new one. The node
    wasn't lost forever (a later refresh could re-draw it), but it vanished
    from `research`/`invest`/`pilot` for an indeterminate stretch, directly
    contradicting the "New research now available" message printed at
    registration. Fixed by recomputing the full set of live dynamic node
    ids in this lane on every call, not just the one right after
    registration -- so a dynamic node stays protected for its entire
    uninvested lifetime, not just its first refresh.
    """
    base_ids = set(load_technologies()[1].keys())
    return {tech_id for tech_id in state.active_pool.get(lane_id, []) if tech_id not in base_ids}


def handle_invest(args):
    """Handle the `invest <lane_id> <pool position>` command.

    Spends everything currently banked in that lane's RP stockpile into
    the chosen pool entry. Completing a node applies its effect
    immediately (see _apply_ship_design_effect) and reopens a slot in
    that lane's discovery pool.
    """
    state = world["research"]
    if len(args) != 2:
        print("Usage: invest <lane_id> <pool position>. Type 'research' to see both.")
        return

    lane_id, position_text = args
    if lane_id not in state.lanes:
        print(f"Unknown lane '{lane_id}'. Type 'research' to see valid lane ids.")
        return

    pool = state.active_pool.get(lane_id, [])
    try:
        position = int(position_text)
        if position < 1:
            raise IndexError
        tech_id = pool[position - 1]
    except (ValueError, IndexError):
        print(f"'{position_text}' is not a valid pool position for {lane_id}. Type 'research' to see options.")
        return

    node = state.nodes[tech_id]
    banked = state.rp_stockpile.get(lane_id, 0.0)
    if banked <= 0:
        print(f"No banked RP in {lane_id} yet. Advance the simulation to accumulate more.")
        return

    completed = invest_rp(state, tech_id, banked)
    if completed:
        print(f"{node.name} is complete! Effect applied: {node.effect}")
        newly_registered_id = _apply_ship_design_effect(tech_id, node)
        guaranteed = _guaranteed_dynamic_node_ids(state, lane_id)
        if newly_registered_id:
            guaranteed.add(newly_registered_id)
        refresh_draw_pool(state, lane_id, guaranteed_ids=guaranteed)
    else:
        progress = state.rp_invested.get(tech_id, 0.0)
        print(f"Invested {banked:.1f} RP into {node.name} ({progress:.1f}/{node.rp_cost:.0f} RP so far).")


def handle_pilot(args):
    """Handle the `pilot <lane_id> <pool position>` command: gamble on an
    early breakthrough using the Mars Collegium Laboratory.
    """
    state = world["research"]
    if len(args) != 2:
        print("Usage: pilot <lane_id> <pool position>. Type 'research' to see both.")
        return

    lane_id, position_text = args
    if lane_id not in state.lanes:
        print(f"Unknown lane '{lane_id}'. Type 'research' to see valid lane ids.")
        return

    pool = state.active_pool.get(lane_id, [])
    try:
        position = int(position_text)
        if position < 1:
            raise IndexError
        tech_id = pool[position - 1]
    except (ValueError, IndexError):
        print(f"'{position_text}' is not a valid pool position for {lane_id}. Type 'research' to see options.")
        return

    try:
        result = attempt_pilot_project(state, tech_id, "mars_collegium_lab")
    except ValueError as error:
        print(f"Cannot start a pilot project: {error}")
        return

    print(result.note)
    # Checking state.completed rather than result.success: a failed pilot
    # can still complete a node outright if enough RP was already banked
    # from a prior `invest` (see attempt_pilot_project()'s fix, 2026-09-04)
    # -- result.success only reflects whether the pilot *roll* itself
    # succeeded, not whether the node ended up completed as a result of
    # this call.
    if tech_id in state.completed:
        newly_registered_id = _apply_ship_design_effect(tech_id, state.nodes[tech_id])
        guaranteed = _guaranteed_dynamic_node_ids(state, lane_id)
        if newly_registered_id:
            guaranteed.add(newly_registered_id)
        refresh_draw_pool(state, lane_id, guaranteed_ids=guaranteed)


def _complete_ship_build(class_id):
    """Spawn a newly built hull of `class_id` and add it to the fleet.

    New ships appear idle at Mars. A freighter joins the automatic supply
    loop on the very next `advance` step, same as CSV Meridian and CSV
    Concord — update_freighters() loops over every ship with
    `class_id == "freighter"` rather than one hardcoded ship (fixed
    2026-09-04; see that function's docstring).
    """
    ship_class = world["ship_classes"][class_id]
    _hull_counters[class_id] += 1
    hull_number = _hull_counters[class_id]

    if class_id == "freighter":
        name = f"CSV Hull-{hull_number:02d}"
        key = f"csv_hull_{hull_number:02d}"
        world["ships"][key] = {
            "name": name,
            "status": "idle_at_mars",
            "cargo_capacity": world["ship_class_stats"]["freighter"]["cargo_capacity"],
            "cargo_support_supplies": 0,
            "cargo_refined_metal": 0,
            "travel_remaining": 0,
            "class_id": "freighter",
            "mk": ship_class.current_mk,
        }
    else:
        name = f"LWS Hull-{hull_number:02d}"
        key = f"lws_hull_{hull_number:02d}"
        world["ships"][key] = {
            "name": name,
            "status": "idle_at_mars",
            "class_id": "light_warship",
            "mk": ship_class.current_mk,
            "combat_rating": world["ship_class_stats"]["light_warship"]["combat_rating"],
        }

    ship_class.in_service.append(name)
    print(f"Shipyard completed construction: {name} ({ship_class.current_mk}) has joined the fleet at Mars.")


def update_shipyard():
    """Run one shipyard step: expand toward the slot target if metal
    allows, advance any hull currently under construction, and — the
    no-idle rotation rule — immediately assign a new build to every slot
    that just went free or was already empty. See docs/systems/shipyard.md.
    """
    yard = world["shipyard"]
    slots = world["shipyard_slots"]
    mars = world["locations"]["mars"]

    # 1. Expand toward the 100-slot target using metal above the reserve.
    available = mars["refined_metal"] - SHIPYARD_METAL_RESERVE
    if available > 0 and yard.slots_total < yard.target_minimum:
        before = (yard.warship_locked, yard.logistics_locked, yard.flexible)
        yard, added, spent = expand(
            yard, available, cost_per_slot=SLOT_EXPAND_COST, batch_size=SHIPYARD_EXPAND_BATCH_SIZE
        )
        world["shipyard"] = yard
        if added:
            mars["refined_metal"] -= spent
            after = (yard.warship_locked, yard.logistics_locked, yard.flexible)
            for _ in range(after[0] - before[0]):
                slots.append({"locked_category": WARSHIP, "building_class_id": None, "steps_remaining": 0})
            for _ in range(after[1] - before[1]):
                slots.append({"locked_category": LOGISTICS, "building_class_id": None, "steps_remaining": 0})
            for _ in range(after[2] - before[2]):
                slots.append({"locked_category": None, "building_class_id": None, "steps_remaining": 0})
            print(
                f"Shipyard expanded by {added} slot(s) (spent {spent:.0f} refined metal). "
                f"Total slots: {yard.slots_total}/{yard.target_minimum}."
            )
            world["standing_orders"]["infrastructure_expansion"]["log"].append({
                "effective_cycle": world["time"],
                "reason": f"Infrastructure-expansion standing order: shipyard expanded by {added} slot(s).",
                "slots_added": added,
            })

    # 2. Advance slots already building; completions free the slot.
    for slot in slots:
        if slot["building_class_id"] is not None:
            slot["steps_remaining"] -= 1
            if slot["steps_remaining"] <= 0:
                _complete_ship_build(slot["building_class_id"])
                slot["building_class_id"] = None

    # 3. No idle slots: assign every free slot a build immediately,
    # steering away from whichever category is already in surplus.
    #
    # Bug found and fixed 2026-09-04: fleet_counts used to be seeded from
    # in_service counts alone. Builds already in flight from a PRIOR step
    # (a slot with building_class_id still set, not yet complete) were
    # invisible to the FLEET_TARGET check below, so while e.g. one
    # light_warship build was mid-construction, every other slot that
    # freed up during those same steps could each start an additional
    # light_warship build too -- none of them could see the others'
    # pending work, only the (unchanged) in_service count. Once all of
    # those completed, the fleet ended up over FLEET_TARGET, contradicting
    # the promise at FLEET_TARGET's own definition ("the shipyard stops
    # building more of that class"). Confirmed with a 400-step
    # advance_world() run from a fresh game: light_warship in_service
    # reached 11 against a target of 10. Counting in-flight builds
    # (already-advanced this step, in the loop above) toward the same cap
    # closes this -- a category at or above FLEET_TARGET once existing
    # hulls AND pending construction are both counted stops attracting
    # new builds, the same way it already did for in_service alone.
    pending_counts = {WARSHIP: 0, LOGISTICS: 0}
    class_to_category = {class_id: category for category, class_id in CATEGORY_TO_CLASS.items()}
    for slot in slots:
        category = class_to_category.get(slot["building_class_id"])
        if category is not None:
            pending_counts[category] += 1

    fleet_counts = {
        WARSHIP: len(world["ship_classes"]["light_warship"].in_service) + pending_counts[WARSHIP],
        LOGISTICS: len(world["ship_classes"]["freighter"].in_service) + pending_counts[LOGISTICS],
    }
    demand_counts = {WARSHIP: fleet_counts[LOGISTICS], LOGISTICS: fleet_counts[WARSHIP]}
    build_time_multiplier = world["multipliers"]["construction_time_multiplier"]

    for slot in slots:
        if slot["building_class_id"] is None:
            allowed = [slot["locked_category"]] if slot["locked_category"] else [WARSHIP, LOGISTICS]
            allowed = [c for c in allowed if fleet_counts[c] < FLEET_TARGET[CATEGORY_TO_CLASS[c]]]
            if not allowed:
                continue  # every category this slot could build is at cap -- idle this step
            category = next_build_assignment(allowed, fleet_counts, demand_counts)
            class_id = CATEGORY_TO_CLASS[category]
            slot["building_class_id"] = class_id
            slot["steps_remaining"] = max(1, round(BASE_BUILD_TIME_STEPS[class_id] * build_time_multiplier))
            # Credit this slot's pending build so the next free slot in
            # this same step doesn't pile onto the identical shortfall.
            fleet_counts[category] += 1


def show_shipyard():
    """Print the Mars Shipyard's slot counts, guarantees, and current
    construction queue.
    """
    yard = world["shipyard"]
    slots = world["shipyard_slots"]
    print("\n=== MARS SHIPYARD ===")
    print(f"Location: {yard.location}")
    print(f"Slots: {yard.slots_total}/{yard.target_minimum} target")
    print(f"  Warship-locked: {yard.warship_locked}/{yard.warship_minimum} minimum")
    print(f"  Logistics-locked: {yard.logistics_locked}/{yard.logistics_minimum} minimum")
    print(f"  Flexible: {yard.flexible}")

    building = [slot for slot in slots if slot["building_class_id"]]
    if building:
        print("\nCurrently building:")
        for slot in building:
            print(
                f"  {slot['building_class_id']} — {slot['steps_remaining']} step(s) remaining "
                f"(slot type: {slot['locked_category'] or 'flexible'})"
            )
    else:
        print("\nNo slots currently building (will assign next step).")

    print(
        f"\nConstruction time multiplier: x{world['multipliers']['construction_time_multiplier']:.2f} "
        "(improves via lab specialization, see 'labs')"
    )
    print(
        f"Expansion uses refined metal above a reserve of {SHIPYARD_METAL_RESERVE:.0f} "
        f"at {SLOT_EXPAND_COST:.0f} metal/slot, {SHIPYARD_EXPAND_BATCH_SIZE} slot(s) per batch."
    )


def show_fleet():
    """Print every ship class's current MK, per-hull stats, and roster."""
    print("\n=== FLEET STATUS ===")
    for class_id, ship_class in world["ship_classes"].items():
        stats = world["ship_class_stats"][class_id]
        stats_text = ", ".join(f"{key}: {value}" for key, value in stats.items())
        retired_note = " (previous MK's production line retired)" if ship_class.retired_from_production else ""
        print(f"\n{class_id} [{ship_class.category}] — current production: {ship_class.current_mk}{retired_note}")
        print(f"  Stats for newly built hulls: {stats_text}")
        roster = ", ".join(ship_class.in_service) if ship_class.in_service else "none"
        print(f"  In service ({len(ship_class.in_service)}): {roster}")


def handle_build_lab():
    """Handle the `build_lab` command: spend refined metal at Mars to
    construct the Collegium's next laboratory, with its role assigned
    automatically by construction order. See docs/systems/lab-specialization.md.
    """
    mars = world["locations"]["mars"]
    if mars["refined_metal"] < LAB_BUILD_COST:
        print(
            f"Not enough refined metal to build a new lab "
            f"(need {LAB_BUILD_COST:.0f}, have {mars['refined_metal']:.0f})."
        )
        return

    mars["refined_metal"] -= LAB_BUILD_COST
    state = world["research"]
    lab_number = len(world["lab_roles"]) + 1
    role = default_lab_role(lab_number)
    lab_id = f"collegium_lab_{lab_number:02d}"

    lab = Lab(
        id=lab_id, name=f"Collegium Laboratory {lab_number}", location="mars", capacity=0, quality=0.5, specialties=[]
    )
    state.add_lab(lab)
    world["lab_roles"][lab_id] = role
    print(f"{lab.name} constructed on Mars for {LAB_BUILD_COST:.0f} refined metal. Assigned role: {role}.")


def show_labs():
    """Print every Collegium laboratory and its permanently assigned role,
    plus the current value of every lab-specialization multiplier.
    """
    print("\n=== ASTERION COLLEGIUM — LABORATORIES ===")
    for lab_id, role in world["lab_roles"].items():
        lab = world["research"].labs[lab_id]
        print(f"  {lab.name} [{lab_id}] — role: {role}")

    multipliers = world["multipliers"]
    print(
        f"\nMultipliers — construction time x{multipliers['construction_time_multiplier']:.2f}, "
        f"research time x{multipliers['research_time_multiplier']:.2f}, "
        f"Mars support-supply efficiency x{multipliers['universal_efficiency_multiplier']:.2f}"
    )
    print(f"Lower is better on all three; each has a hard floor of {LAB_TICK_FLOOR:.2f}.")
    print(f"\nUse 'build_lab' to construct the next lab for {LAB_BUILD_COST:.0f} refined metal.")


# ---------------------------------------------------------------------------
# Penal Code labor-economy wiring (2026-09-05, "improve all systems" pass).
# See docs/systems/penal-code.md's "What this version explicitly does not
# include yet" section, which flags this exact gap by name: "No tie-in yet
# to the labor economy... a filed record does not yet remove anyone from,
# or add anyone to, a workforce pool." Toil Legion ("forced labor
# assignment") and Penal Legion ("forced military/hazard-duty assignment")
# are the two non-capital tiers whose own descriptions already say what
# kind of work they mean -- this wiring takes those descriptions at face
# value rather than inventing new meaning for either one.
#
# Toil Legion labor is assigned to Mars's forge complex, the Directorate's
# one real industrial hub, for a fixed term -- a steady refined-metal trickle
# while the sentence is being served, nothing once it's done.
#
# Penal Legion hazard duty is assigned to garrison/defense work -- the same
# kind of number FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE just gave
# Marshal-General's Council seat its first real data (see
# docs/systems/council-seats.md), except Directorate-wide rather than tied
# to one fortress_world colony, since a sentenced individual isn't a
# colony. update_penal_labor() (called from advance_world()) applies both
# effects every step and expires them once each sentence's fixed term ends.
TOIL_LEGION_TERM_STEPS = 10
PENAL_LEGION_TERM_STEPS = 6            # more dangerous duty, shorter fixed term
TOIL_LEGION_REFINED_METAL_PER_CYCLE = 3.0
PENAL_LEGION_GARRISON_PER_CYCLE = 2.0

_LEGION_TERM_STEPS = {
    SentencingTier.TOIL_LEGION: TOIL_LEGION_TERM_STEPS,
    SentencingTier.PENAL_LEGION: PENAL_LEGION_TERM_STEPS,
}


def update_penal_labor():
    """Apply one step's worth of Toil/Penal Legion labor for every penal
    record currently serving one of those two sentences, then decrement
    its remaining term -- expiring it (status "term_served") the step its
    term reaches zero, exactly like a fixed-term sentence should. Records
    under every other status (awaiting_confirmation, carried_out, a
    Reprimand-and-Restitution "sentenced" record with no term at all) are
    untouched; this function only ever looks at "serving" records.

    Hardened 2026-09-05 (stress-test pass): a "serving" record is only
    ever produced by _file_charge() today, which always sets
    "term_remaining" in the same dict-literal assignment -- so this can't
    happen through normal play. But a hand-edited or partially-written
    save file could still produce a "serving" record with no
    "term_remaining" key at all, and this function used to do a bare
    `record["term_remaining"] -= 1`, which raised an uncaught KeyError on
    the very next `advance` -- crashing the whole program on a save that
    load_game() had just reported loading successfully. `.get(..., 0)`
    makes a record like that expire immediately (treated as already
    served) instead of crashing; see the matching load-time backfill in
    _apply_loaded_save() for records this can reach without ever going
    through this function.
    """
    mars = world["locations"]["mars"]
    for record in world["penal_records"]:
        if record["status"] != "serving":
            continue

        if record["tier"] == SentencingTier.TOIL_LEGION:
            mars["refined_metal"] += TOIL_LEGION_REFINED_METAL_PER_CYCLE
        elif record["tier"] == SentencingTier.PENAL_LEGION:
            world["legion_penal_garrison_rating"] += PENAL_LEGION_GARRISON_PER_CYCLE

        record["term_remaining"] = record.get("term_remaining", 0) - 1
        if record["term_remaining"] <= 0:
            record["status"] = "term_served"
            print(f"{record['name']}'s {record['tier'].value.replace('_', ' ')} term has been served in full.")


def _file_charge(name, article_id):
    """Core of the `charge` command, factored out (Lesson 12) so automatic
    escalations -- e.g. a colony's persistent tithe shortfall, see
    _escalate_tithe_shortfall() -- file a charge exactly the way a
    manually typed `charge <name> <article_id>` would. Returns the filed
    record, or None if the article is unknown.
    """
    code = world["penal_code"]
    try:
        tier = charge(code, article_id)
    except KeyError:
        print(f"Unknown article '{article_id}'. Type 'docket' to see valid article ids.")
        return None

    record = {"name": name, "article_id": article_id, "tier": tier, "status": "sentenced"}

    if tier == CAPITAL_TIER:
        record["status"] = "awaiting_confirmation"
        print(
            f"{name} charged under '{code.articles[article_id].name}': "
            "typical sentence is SERVITOR CONVERSION (capital, irreversible)."
        )
        print("This cannot be carried out without both a Vigil referral and Grand Director confirmation.")
        print(f"Use: confirm_servitor {name} <yes/no> <yes/no>   (vigil referral, then grand director confirmation)")
    elif tier in _LEGION_TERM_STEPS:
        # Penal Code labor-economy wiring (2026-09-05): a Toil/Penal Legion
        # sentence now actually does something for its fixed term instead
        # of being a record with no consequence beyond its own text -- see
        # update_penal_labor() for what "serving" means for each tier.
        record["status"] = "serving"
        record["term_remaining"] = _LEGION_TERM_STEPS[tier]
        print(
            f"{name} charged under '{code.articles[article_id].name}': sentenced to "
            f"{tier.value.replace('_', ' ').upper()} for {record['term_remaining']} step(s)."
        )
    else:
        print(f"{name} charged under '{code.articles[article_id].name}': sentenced to {tier.value.replace('_', ' ').upper()}.")

    world["penal_records"].append(record)
    return record


def handle_charge(args):
    """Handle the `charge <name> <article_id>` command: sentence a named
    individual under the Directorate Penal Code. See docs/systems/penal-code.md.
    """
    if len(args) != 2:
        print("Usage: charge <name> <article_id>. Type 'docket' to see valid article ids.")
        return
    name, article_id = args
    _file_charge(name, article_id)


def handle_confirm_servitor(args):
    """Handle `confirm_servitor <name> <vigil yes/no> <grand_director yes/no>`:
    the required two-step sign-off gate before a Servitor Conversion
    sentence can actually be carried out.
    """
    if len(args) != 3:
        print("Usage: confirm_servitor <name> <vigil yes/no> <grand_director yes/no>")
        return

    name, vigil_text, gd_text = args
    vigil = vigil_text in ("yes", "y", "true")
    grand_director = gd_text in ("yes", "y", "true")

    record = next(
        (
            r
            for r in reversed(world["penal_records"])
            if r["name"] == name and r["status"] == "awaiting_confirmation"
        ),
        None,
    )
    if record is None:
        print(f"No pending Servitor Conversion sentence found for '{name}'.")
        return

    try:
        confirm_capital_sentence(referred_by_vigil=vigil, confirmed_by_grand_director=grand_director)
    except ValueError as error:
        print(f"Sentence not carried out: {error}")
        return

    record["status"] = "carried_out"
    print(f"Servitor Conversion carried out on {name}. The sentence is irreversible.")

def show_council():
    """Print the ten-seat Council roster with each seat's domain backed
    by a live number pulled from the actual system it oversees, the full
    Branch A-K rank ladders, the Vigil's deliberate exclusion, and
    entities entirely outside the Directorate.
    """
    print("\n=== THE DIRECTORATE COUNCIL ===")
    print("The Grand Director sits above all ten seats -- not one of the ten.\n")

    live_status = {
        # Council-seat wiring (2026-09-05): first_minister, marshal_general,
        # and first_steward_of_continuance were the last three seats with no
        # backing system (see lore/gaps.md's "Lore ahead of code" entry --
        # Colonial Warden and Chancellor-General were wired in earlier
        # sessions). All three are read-only aggregates over data the game
        # already tracks; see docs/systems/council-seats.md for the design
        # writeup of each, including why fortress_world/civilian_world
        # needed real per-cycle effects first (SPECIALIZATION_EFFECTS).
        "first_minister": lambda: (
            f"{sum(c['population'] for c in world['colonies'].values() if c['status'] == 'established')} "
            "colonist(s) across "
            f"{sum(1 for c in world['colonies'].values() if c['status'] == 'established')} "
            "established colony(ies); Earth support reserve: "
            f"{world['locations']['earth']['support_supplies']:.0f}"
        ),
        "marshal_general": lambda: (
            f"{sum(1 for c in world['colonies'].values() if c.get('specialization') == 'fortress_world')} "
            "fortress world(s), total garrison rating "
            f"{sum(c.get('garrison_rating', 0.0) for c in world['colonies'].values()):.0f}; "
            f"{sum(1 for r in world['penal_records'] if r['status'] == 'serving' and r['tier'] == SentencingTier.PENAL_LEGION)} "
            f"Penal Legion sentence(s) serving, +{world['legion_penal_garrison_rating']:.0f} garrison"
        ),
        "first_steward_of_continuance": lambda: (
            f"{sum(1 for c in world['colonies'].values() if c.get('continuance_hall'))} of "
            f"{sum(1 for c in world['colonies'].values() if c['status'] == 'established')} "
            "established colony(ies) have raised a Continuance Hall"
        ),
        # Colonial Warden / remaining specializations pass (2026-09-05):
        # colonial_warden was the only wired seat with no live_status line
        # at all (see docs/systems/council-seats.md's note on why -- it
        # predates this pass and works through the `colonies` command
        # instead). This closes that gap with the same kind of read-only
        # aggregate first_minister already uses: zero new state, just a
        # real count over world["colonies"] for the seat's actual domain
        # ("Survey, colonization, colony specialization").
        "colonial_warden": lambda: (
            f"{len(world['colonies'])} colony survey(s) on file -- "
            f"{sum(1 for c in world['colonies'].values() if c['status'] == 'surveyed')} awaiting outpost, "
            f"{sum(1 for c in world['colonies'].values() if c['status'] == 'outpost')} outpost(s) awaiting specialization, "
            f"{sum(1 for c in world['colonies'].values() if c['status'] == 'established')} established"
        ),
        "grand_admiral": lambda: (
            f"{len(world['ship_classes']['light_warship'].in_service)} light warship(s) in service"
        ),
        # fuel_world/depot_trade_world (2026-09-05): see
        # FUEL_WORLD_RESERVE_PER_CYCLE's design-decision comment for why
        # these two specializations' new stats report here rather than
        # under Grand Admiral or Colonial Warden.
        "quartermaster_general": lambda: (
            f"{len(world['ship_classes']['freighter'].in_service)} freighter(s) in service; "
            f"Directorate fuel reserve {sum(c.get('fuel_reserve', 0.0) for c in world['colonies'].values()):.0f}; "
            f"trade throughput {sum(c.get('trade_throughput', 0.0) for c in world['colonies'].values()):.0f}"
        ),
        "forge_marshal": lambda: (
            f"Mars refined metal: {world['locations']['mars']['refined_metal']:.1f}"
        ),
        "high_savant": lambda: (
            f"{len(world['research'].completed)} technologies completed, "
            f"{len(world['lab_roles'])} labs operational"
        ),
        "provost_general": lambda: (
            f"{len(world['penal_records'])} record(s) on file"
        ),
        "chancellor_general": lambda: (
            f"{len(world['tithe_system']['log'])} tithe(s) remitted in full, "
            f"{sum(1 for c in world['colonies'].values() if c.get('tithe_shortfall_streak', 0) > 0)} "
            "colony(ies) currently short"
        ),
    }

    for seat_id, seat in world["council"].items():
        print(f"  {seat_id}: {seat['holder']} (Branch {seat['branch']})")
        print(f"      {seat['domain']}")
        if seat_id in live_status:
            print(f"      Current: {live_status[seat_id]()}")

    print("\n=== BRANCHES A-K ===")
    for letter, branch in world["branches"].items():
        seat_note = f"Council seat: {branch['council_seat']}" if branch["council_seat"] else "No Council seat"
        print(f"\n  Branch {letter} -- {branch['name']} ({seat_note})")
        print(f"    Ranks: {' -> '.join(branch['ranks'])}")
        if "note" in branch:
            print(f"    {branch['note']}")

    print("\nThe Vigil (Branch K) is not listed in the Council above -- deliberately excluded.")
    vigil = world["vigil"]
    print(f"  Top rank: {vigil['top_rank']} | Reports to: {vigil['reports_to']}")
    print(f"  {vigil['note']}")

    print("\n=== OUTSIDE THE DIRECTORATE ENTIRELY ===")
    for name, note in world["outside_directorate"].items():
        print(f"  {name.replace('_', ' ').title()}: {note}")

def show_docket():
    """Print the Directorate Penal Code's articles and every charge record
    filed so far.
    """
    code = world["penal_code"]
    print("\n=== DIRECTORATE PENAL CODE ===")
    print(f'Doctrine: "{code.doctrine}"')
    for article in code.articles.values():
        print(f"  [{article.id}] {article.name} — typical sentence: {article.typical_sentence.value.replace('_', ' ')}")
        print(f"      {article.description}")

    if world["penal_records"]:
        print("\nRecords:")
        for record in world["penal_records"]:
            line = f"  {record['name']} — {record['article_id']} — {record['tier'].value} — {record['status']}"
            if record["status"] == "serving":
                line += f" ({record['term_remaining']} step(s) remaining)"
            print(line)

    print("\nUse 'charge <name> <article_id>' to sentence someone. Capital sentences additionally need 'confirm_servitor'.")


def show_directorate_code():
    """Print the five-article Directorate Code, each cross-referenced
    against the Penal Code articles that actually enforce it -- or noted
    as an honest gap where none do.
    """
    code = world["directorate_code"]
    penal_code = world["penal_code"]
    print("\n=== THE DIRECTORATE CODE ===")
    for article_id, article in code.items():
        print(f"\n  [{article_id}] {article['name']}")
        print(f"      {article['description']}")
        if article["enforced_by"]:
            enforcers = ", ".join(
                penal_code.articles[pid].name for pid in article["enforced_by"]
            )
            print(f"      Enforced by (Penal Code): {enforcers}")
        else:
            print(f"      Enforced by: no Penal Code article covers this yet.")


def update_standing_orders():
    """Run the equipment-and-asset-upgrades standing order: spend refined
    metal above a small reserve to upgrade one equipment category per
    step, always in priority order (frontline first). Logged with
    effective_cycle and reason, matching how the compendium logs rate
    changes -- never applied silently.
    """
    mars = world["locations"]["mars"]
    available = mars["refined_metal"] - EQUIPMENT_METAL_RESERVE

    if available < EQUIPMENT_UPGRADE_COST:
        return

    for category in ["frontline_combat", "industrial", "administrative_personal"]:
        status = world["equipment_status"][category]
        if status["tier_index"] + 1 < len(status["tiers"]):
            mars["refined_metal"] -= EQUIPMENT_UPGRADE_COST
            status["tier_index"] += 1
            new_tier = status["tiers"][status["tier_index"]]
            world["standing_orders"]["equipment_and_asset_upgrades"]["log"].append({
                "effective_cycle": world["time"],
                "reason": f"Equipment-and-asset-upgrades standing order: {category} funded from surplus.",
                "category": category,
                "new_tier": new_tier,
            })
            print(f"Standing order (equipment upgrades): {category.replace('_', ' ')} upgraded to '{new_tier}'.")
            return  # one upgrade per step -- matches "incrementally"


def show_standing_orders():
    """Print both standing orders' policy, priority order, and every
    automatic action logged under them so far, plus current equipment tiers.
    """
    print("\n=== STANDING ORDERS ===")
    for order_id, order in world["standing_orders"].items():
        print(f"\n{order_id} [{order['status']}]")
        print(f"  Policy: {order['policy']}")
        for line in order["priority"]:
            print(f"    {line}")
        if order["log"]:
            print(f"  Recent actions:")
            for entry in order["log"][-5:]:
                print(f"    Cycle {entry['effective_cycle']}: {entry['reason']}")
        else:
            print("  No actions logged yet.")

    print("\n=== EQUIPMENT STATUS ===")
    for category, status in world["equipment_status"].items():
        print(f"  {category.replace('_', ' ').title()}: {status['tiers'][status['tier_index']]}")


def update_audit():
    """Run one honest-reporting audit-system step: the forge_marshal
    silent-drain roll (unchanged since Lesson 09). Tithe shortfalls are
    opened directly by update_tithes() -- this only owns the forge_marshal
    roll and the existing metal-drain tick.

    Deliberately prints nothing while a concealment is active and
    undetected -- an audit-worthy discrepancy that announces itself in
    the normal status output wouldn't be much of a concealment.
    """
    concealments = world["audit_system"]["active_concealments"]
    mars = world["locations"]["mars"]

    active = next(
        (c for c in concealments if c["kind"] == "silent_drain" and c["seat_id"] == "forge_marshal"),
        None,
    )
    if active is None:
        if random.random() < AUDIT_CONCEALMENT_CHANCE_PER_CYCLE:
            concealments.append({
                "kind": "silent_drain",
                "seat_id": "forge_marshal",
                "started_cycle": world["time"],
                "drain_per_cycle": random.randint(*AUDIT_SILENT_DRAIN_RANGE),
                "total_concealed": 0.0,
            })
        return

    drain = min(active["drain_per_cycle"], mars["support_supplies"])
    mars["support_supplies"] -= drain
    active["total_concealed"] += drain


def handle_audit(args):
    """Handle `audit <seat_id or colony_id>`: the Bureau attempts to
    uncover any active concealment tied to that target -- forge_marshal's
    silent metal drain, or a colony's tithe shortfall under the
    Chancellor-General's ledger (generalized in Lesson 12; both kinds
    share one discovery/correction mechanic, see update_audit()).

    Design decision made 2026-09-04 (see AUDIT_COST_SUPPORT_SUPPLIES /
    AUDIT_COOLDOWN_STEPS's comment for the full reasoning): a real audit
    attempt -- one that actually matches an open concealment -- now costs
    support supplies and starts a per-target cooldown, win or lose.
    Without this, AUDIT_SUCCESS_CHANCE being anything less than 1.0
    barely mattered, since free unlimited retries made eventual discovery
    a near-certainty. Auditing a target with nothing to find stays free
    and instant.
    """
    if len(args) != 1:
        print(
            "Usage: audit <seat_id or colony_id>. Currently: 'forge_marshal', "
            "or any colony_id with an open tithe shortfall (see 'colonies')."
        )
        return

    target = args[0]
    concealments = world["audit_system"]["active_concealments"]
    # Match seat_id only for seat-level concealments (forge_marshal) and
    # colony_id only for tithe shortfalls -- every tithe shortfall shares
    # the same seat_id ("chancellor_general"), so matching on seat_id for
    # those too would let `audit chancellor_general` silently resolve
    # whichever colony's shortfall happened to be first in the list and
    # leave every other colony's shortfall untouched, with no indication
    # that more than one was open. A tithe shortfall must be targeted by
    # its own colony_id, exactly as the usage message says.
    concealment = next(
        (c for c in concealments if (
            (c["kind"] == "silent_drain" and c["seat_id"] == target)
            or (c["kind"] == "tithe_shortfall" and c["colony_id"] == target)
        )),
        None,
    )

    if concealment is None:
        print(f"Bureau audit of {target}: no discrepancy found. Reported figures check out.")
        return

    last_audit_step = world["audit_system"]["last_audit_step"]
    last_step = last_audit_step.get(target)
    if last_step is not None and world["time"] - last_step < AUDIT_COOLDOWN_STEPS:
        steps_left = AUDIT_COOLDOWN_STEPS - (world["time"] - last_step)
        print(
            f"Bureau audit of {target}: investigators are still tied up from the last audit "
            f"({steps_left} step(s) before {target} can be re-audited)."
        )
        return

    mars = world["locations"]["mars"]
    if mars["support_supplies"] < AUDIT_COST_SUPPORT_SUPPLIES:
        print(
            f"Bureau audit of {target}: insufficient support supplies to dispatch investigators "
            f"(need {AUDIT_COST_SUPPORT_SUPPLIES:.0f}, Mars has {mars['support_supplies']:.0f})."
        )
        return
    mars["support_supplies"] -= AUDIT_COST_SUPPORT_SUPPLIES
    last_audit_step[target] = world["time"]

    if random.random() < AUDIT_SUCCESS_CHANCE:
        cycles = world["time"] - concealment["started_cycle"]
        log_entry = {
            "seat_id": concealment["seat_id"], "discovered_cycle": world["time"],
            "kind": concealment["kind"], "outcome": "corrected, no charge (Halvorsen precedent)",
        }
        if concealment["kind"] == "silent_drain":
            log_event(
                f"Bureau audit of {target}: CONCEALMENT DISCOVERED. "
                f"{concealment['total_concealed']:.0f} support supplies silently diverted over "
                f"{cycles} cycle(s), unreported since cycle {concealment['started_cycle']}."
            )
            log_entry["total_concealed"] = concealment["total_concealed"]
        else:
            log_event(
                f"Bureau audit of {concealment['colony_name']}: SHORTFALL EXPLAINED. "
                f"{concealment['total_shortfall']:.1f} in unmet tithe over "
                f"{concealment['cycles_short']} cycle(s) corrected, not concealed."
            )
            log_entry["total_shortfall"] = concealment["total_shortfall"]
            log_entry["colony_name"] = concealment["colony_name"]
            world["colonies"][concealment["colony_id"]]["tithe_shortfall_streak"] = 0
        print(
            "Per Directorate doctrine (reward correction over concealment): no charge filed. "
            f"{target} is ordered to correct the figures going forward."
        )
        world["audit_system"]["log"].append(log_entry)
        world["audit_system"]["active_concealments"] = [c for c in concealments if c is not concealment]
    else:
        print(
            f"Bureau audit of {target}: inconclusive. No discrepancy found this pass "
            f"({AUDIT_COST_SUPPORT_SUPPLIES:.0f} support supplies spent regardless; "
            f"re-audit possible in {AUDIT_COOLDOWN_STEPS} step(s))."
        )


def show_audit():
    """Print the audit doctrine and every past discovered concealment.
    Deliberately never reveals whether a concealment is currently active
    -- that would defeat the point of 'audit' being a real gamble.
    """
    audit = world["audit_system"]
    print("\n=== BUREAU AUDIT LOG (Honest Reporting) ===")
    print(f"Doctrine: {audit['doctrine']}")
    if audit["log"]:
        print("\nPast audits:")
        for entry in audit["log"]:
            if entry["kind"] == "silent_drain":
                print(
                    f"  Cycle {entry['discovered_cycle']}: {entry['seat_id']} -- "
                    f"{entry['total_concealed']:.0f} concealed, {entry['outcome']}"
                )
            else:
                print(
                    f"  Cycle {entry['discovered_cycle']}: {entry.get('colony_name', entry['seat_id'])} -- "
                    f"{entry['total_shortfall']:.1f} unmet tithe, {entry['outcome']}"
                )
    else:
        print("\nNo concealment has been discovered yet.")


def show_tithes():
    """Print the Chancellery's tithe doctrine and every fully-remitted
    tithe on record. Open shortfalls and convoys in transit show under
    'colonies'; discovered/corrected shortfalls show under 'audit' --
    this is the "what's actually been collected" ledger, not the
    discrepancy log.
    """
    tithe_system = world["tithe_system"]
    print("\n=== CHANCELLERY TITHE LEDGER ===")
    print(f"Doctrine: {tithe_system['doctrine']}")
    if tithe_system["log"]:
        print("\nRemitted in full:")
        for entry in tithe_system["log"][-10:]:
            print(
                f"  Cycle {entry['cycle']}: {entry['colony_name']} ({entry['grade']}) -- "
                f"{entry['paid']:.1f} remitted"
            )
    else:
        print("\nNo tithe has been remitted in full yet.")
    print("\nType 'colonies' for each colony's current Tithe Grade, standing, and convoys en route.")
    print("Type 'audit <colony_id>' to investigate a colony currently running a shortfall.")


def save_game():
    """Save the full world state to state.json.

    Plain-dict portions save directly. The three object-based systems
    each get explicit handling:
      - ship_classes / shipyard: dataclasses.asdict() -- they're simple,
        flat dataclasses, nothing nested that asdict() can't already handle.
      - research: the MUTABLE state saves (labs, scientists, rp_stockpile,
        rp_invested, active_pool, completed, trial_log). Base lanes/nodes
        from technologies.json are NOT saved -- they're reloaded fresh on
        load, since that file is the source of truth for tech
        definitions. Nodes registered at RUNTIME (the self-renewing MK
        successor projects _register_next_mk_node() creates -- e.g.
        "freighter_mark_iii" -- see docs/systems/ship-design.md) are NOT
        in technologies.json, so they DO need to be saved explicitly
        (see "dynamic_nodes" below) or they simply cease to exist on the
        next load even though active_pool/completed still reference them.
      - penal_code: the code itself (articles/doctrine) is NOT saved,
        for the same reason -- default_code() is the source of truth.
        Only world["penal_records"] saves, with each record's
        SentencingTier enum converted to its .value string, since raw
        enums aren't JSON-serializable.
    """
    state = world["research"]
    # Bug found and fixed 2026-09-04: only base-technologies.json node ids
    # need to be excluded from the save -- everything else in state.nodes
    # was registered at runtime and would silently vanish from
    # state.nodes on the next load (while active_pool/completed still
    # named it), crashing `research`/`invest`/`pilot` with a KeyError the
    # moment they tried to look that node up. See dynamic_nodes below.
    base_node_ids = set(load_technologies()[1].keys())
    dynamic_nodes_save = {
        node_id: asdict(node) for node_id, node in state.nodes.items() if node_id not in base_node_ids
    }
    research_save = {
        "labs": {lab_id: asdict(lab) for lab_id, lab in state.labs.items()},
        "scientists": {sci_id: asdict(sci) for sci_id, sci in state.scientists.items()},
        "rp_stockpile": state.rp_stockpile,
        "rp_invested": state.rp_invested,
        "active_pool": state.active_pool,
        "completed": list(state.completed),  # set -> list, JSON has no set type
        "trial_log": [asdict(result) for result in state.trial_log],
        "dynamic_nodes": dynamic_nodes_save,
        "evidence_banked": state.evidence_banked,
    }

    penal_records_save = [
        {**record, "tier": record["tier"].value} for record in world["penal_records"]
    ]

    saveable = {
        "time": world["time"],
        "locations": world["locations"],
        "ships": world["ships"],
        "xenos_fragments": world["xenos_fragments"],
        "legion_penal_garrison_rating": world["legion_penal_garrison_rating"],
        "multipliers": world["multipliers"],
        "council": world["council"],
        "standing_orders": world["standing_orders"],
        "equipment_status": world["equipment_status"],
        "directorate_code": world["directorate_code"],
        "audit_system": world["audit_system"],
        "colonies": world["colonies"],
        "tithe_system": world["tithe_system"],
        "tithe_convoys": world["tithe_convoys"],
        "events": world["events"],
        "ship_classes": {cid: asdict(sc) for cid, sc in world["ship_classes"].items()},
        "ship_class_stats": world["ship_class_stats"],
        "shipyard": asdict(world["shipyard"]),
        "shipyard_slots": world["shipyard_slots"],
        "lab_roles": world["lab_roles"],
        "research": research_save,
        "penal_records": penal_records_save,
        # Bug found and fixed 2026-09-04: _hull_counters is a module-level
        # global, not part of `world`, so it used to be silently excluded
        # from every save and reset to its {"freighter": 1, "light_warship":
        # 0} default on the next process start. The very next hull the
        # shipyard completed after a save/load would then reuse an
        # already-taken hull id/name (e.g. "CSV Hull-02" again), silently
        # overwriting that ship's dict in world["ships"] -- destroying any
        # cargo/travel state it was mid-carrying -- and adding a duplicate
        # name to ship_classes[...].in_service, which also threw off
        # update_shipyard()'s fleet-count-vs-FLEET_TARGET bookkeeping.
        "hull_counters": dict(_hull_counters),
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(saveable, f, indent=2)
    print(f"Saved to {SAVE_FILE} -- full state, including research, shipyard, and penal records.")


def load_game():
    """Load the full world state from state.json, if it exists.

    Rebuilds ship_classes/shipyard from their saved dicts via each
    dataclass's constructor. Rebuilds research by starting fresh from
    build_research_state() (reloading lanes/nodes from
    technologies.json, the source of truth), then overwriting its
    mutable fields from the save. Reconstructs each penal record's
    SentencingTier enum from its saved .value string.

    Bug found and fixed 2026-09-04: this used to only catch
    FileNotFoundError. A save file that's present but corrupted --
    truncated by a crash or a full disk mid-write, hand-edited into
    invalid JSON, or valid JSON with a shape this version's dataclass
    constructors don't recognize -- would raise straight out of this
    function and crash the game on every single launch (both the
    unconditional call at import time and the `load` command), with no
    way to recover except manually deleting state.json outside the game.
    Now both failure modes are caught: a JSON parse failure never even
    starts applying the save, and a parse-succeeds-but-shape-is-wrong
    failure is reported without pretending the corrupt file didn't
    exist, so the player can decide whether to keep playing on
    module-level defaults or go fix/delete the file by hand.
    """
    try:
        with open(SAVE_FILE) as f:
            saved = json.load(f)
    except FileNotFoundError:
        print(f"No {SAVE_FILE} found -- starting fresh.")
        return
    except json.JSONDecodeError as exc:
        print(
            f"WARNING: {SAVE_FILE} exists but is not valid JSON ({exc}). "
            "It may have been corrupted by an interrupted write (a crash, a "
            "full disk) or a hand edit. Starting fresh instead of crashing -- "
            f"the broken file is left at {SAVE_FILE} in case you want to "
            "inspect or recover it by hand; the next 'save' command will "
            "overwrite it with a clean file."
        )
        return

    try:
        _apply_loaded_save(saved)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        print(
            f"WARNING: {SAVE_FILE} parsed as valid JSON, but its contents "
            f"don't match what this version of the game expects ({exc!r}). "
            "Starting fresh instead of crashing -- this can happen if the "
            "file is from an incompatible version or was hand-edited. Some "
            "fields may have already been partially applied before the "
            "error; if anything looks wrong, restart the game or delete "
            f"{SAVE_FILE} for a guaranteed-clean start. The broken file has "
            "been left in place; the next 'save' command will overwrite it."
        )
        return

    print(f"Loaded from {SAVE_FILE} -- full state restored.")


def _apply_loaded_save(saved):
    """Overwrite `world` in place from an already-JSON-parsed save dict.

    Split out of load_game() so that function can wrap this call in one
    try/except covering every reconstruction step (dataclasses, sets,
    enums) rather than needing a matching except clause after each one.

    Bug found and fixed 2026-09-04: every reconstruction step used to run
    interleaved with direct writes into `world` (e.g. lab_roles was
    written by the flat key-copy loop BEFORE the research block ran, and
    research's own reconstruction could raise). If a later step raised,
    load_game()'s except-clause caught it and told the player "starting
    fresh instead of crashing" -- true for the exception itself, but
    false for `world`, which was left holding a mix of old state and
    whatever earlier steps had already written. The very next ordinary
    command touching that half-updated system (e.g. `labs`, if lab_roles
    now named a lab research.labs didn't have) crashed for real, despite
    the message claiming a clean fresh start. Fixed by doing every
    reconstruction that can raise (dataclasses, sets, enums) into LOCAL
    variables first; only once ALL of them have succeeded does this
    function write anything into `world`, in one block at the end. A
    raise anywhere in the reconstruction phase below now leaves `world`
    completely untouched, exactly as the warning message promises.
    """
    # --- Reconstruction phase: build locals, don't touch `world` yet. ---

    new_ship_classes = None
    if "ship_classes" in saved:
        new_ship_classes = {cid: ShipClass(**sc) for cid, sc in saved["ship_classes"].items()}
        # Hardening added 2026-09-05 (stress-test pass): every other
        # historical field this function restores gets a matching backfill
        # for a save that predates it or is missing it (colonies, hull
        # counters, audit_system, penal records...) -- this one didn't. A
        # save whose "ship_classes" object is missing "freighter" or
        # "light_warship" entirely (hand edit, truncated write, a future
        # class rename) used to load with a silent "full state restored"
        # message, then crash the very next `advance` or `council` command
        # with an uncaught KeyError (update_shipyard() and show_council()
        # both do a hardcoded world["ship_classes"]["light_warship"/
        # "freighter"] lookup, no .get()). Backfilling an empty-roster
        # class (no invented phantom ships) instead keeps every downstream
        # command working; it can't retroactively invent ships that may
        # have genuinely been lost, but it also can't make things worse
        # than the crash it replaces.
        for missing_class_id, category in (("freighter", "logistics"), ("light_warship", "warship")):
            if missing_class_id not in new_ship_classes:
                new_ship_classes[missing_class_id] = ShipClass(
                    id=missing_class_id, category=category, current_mk="Mark I", in_service=[],
                )

    new_shipyard = None
    if "shipyard" in saved:
        new_shipyard = Shipyard(**saved["shipyard"])

    new_research_state = None
    research_missing_nodes = set()
    if "research" in saved:
        r = saved["research"]
        state = build_research_state()  # fresh lanes/nodes from technologies.json

        # Bug found and fixed 2026-09-04: nodes registered at runtime (the
        # self-renewing MK successor projects _register_next_mk_node()
        # creates, e.g. "freighter_mark_iii") aren't in technologies.json,
        # so build_research_state() alone never recreates them. Restore
        # them before active_pool/completed, which may reference them.
        for node_id, node_dict in r.get("dynamic_nodes", {}).items():
            state.nodes[node_id] = TechNode(**node_dict)

        state.labs = {lab_id: Lab(**lab) for lab_id, lab in r["labs"].items()}
        state.scientists = {sci_id: Scientist(**sci) for sci_id, sci in r["scientists"].items()}
        state.rp_stockpile = r["rp_stockpile"]
        state.rp_invested = r["rp_invested"]
        state.active_pool = r["active_pool"]
        state.completed = set(r["completed"])
        # Backfill for a save made before evidence_banked existed (2026-09-07):
        # default to 0, same "no evidence banked yet" state a fresh game
        # starts in -- never a crash, and never silently inventing
        # evidence the player didn't actually earn via study_fragments.
        state.evidence_banked = r.get("evidence_banked", 0)

        # Defensive backfill for a save made before dynamic_nodes existed:
        # active_pool/completed can still name a dynamic node id with no
        # corresponding definition to restore. Rather than leaving a
        # dangling id that KeyErrors the next time research/invest/pilot
        # looks it up, drop it here and report it once, instead of
        # crashing deep inside an unrelated command later.
        for lane_id, pool in state.active_pool.items():
            research_missing_nodes.update(tech_id for tech_id in pool if tech_id not in state.nodes)
            state.active_pool[lane_id] = [tech_id for tech_id in pool if tech_id in state.nodes]
        research_missing_nodes.update(tech_id for tech_id in state.completed if tech_id not in state.nodes)
        state.completed = {tech_id for tech_id in state.completed if tech_id in state.nodes}

        new_research_state = state

    new_penal_records = None
    if "penal_records" in saved:
        new_penal_records = [
            {**record, "tier": SentencingTier(record["tier"])} for record in saved["penal_records"]
        ]

    # --- Commit phase: every reconstruction above succeeded, so it's now
    # safe to start writing into `world`. Nothing below this line should
    # be able to raise on a malformed save -- only on a genuine bug. ---

    for key in ["time", "locations", "ships", "xenos_fragments", "multipliers",
                "council", "standing_orders", "equipment_status", "directorate_code",
                "audit_system", "colonies", "tithe_system", "tithe_convoys", "events",
                "ship_class_stats", "shipyard_slots", "lab_roles",
                "legion_penal_garrison_rating"]:
        if key in saved:
            world[key] = saved[key]

    # Backfill for a save made before the 2026-09-05 Penal Code labor-
    # economy wiring: no top-level "legion_penal_garrison_rating" at all.
    # (The matching per-record backfill -- for a Toil/Penal Legion record
    # that predates "serving"/"term_remaining" entirely -- runs further
    # below, after new_penal_records is committed into world; it can't run
    # here, since world["penal_records"] at this point is still whatever
    # it was BEFORE this load, not the save's own records.)
    world.setdefault("legion_penal_garrison_rating", 0.0)

    if new_ship_classes is not None:
        world["ship_classes"] = new_ship_classes
    if new_shipyard is not None:
        world["shipyard"] = new_shipyard

    # Backfill fields the Tithe System added (Lesson 12) onto any colony
    # saved before it existed -- without this, update_tithes()/
    # show_colonies() raise a KeyError on a colony dict that predates
    # these keys, crashing the game on load instead of just treating that
    # colony as exempt/unsurveyed-distance until it's naturally
    # recomputed. A random distance here (rather than 0) keeps travel
    # time meaningful even for a colony that was never freshly surveyed
    # under this version.
    for colony in world.get("colonies", {}).values():
        colony.setdefault("distance_steps", random.randint(*SURVEY_DISTANCE_RANGE_STEPS))
        colony.setdefault("tithe_grade", None)
        colony.setdefault("tithe_shortfall_streak", 0)
        # Same backfill pattern for the 2026-09-05 Council-seat wiring
        # (garrison_rating for Marshal-General, continuance_hall for First
        # Steward of Continuance): a save from before that change won't
        # have either key, which would otherwise KeyError the first time
        # update_colonies()/show_colonies()/show_council() reads them.
        # False/0.0 is always correct for a pre-existing colony to start
        # from -- garrison rating only ever accumulates going forward, and
        # a colony either already has enough population to raise a
        # Continuance Hall next step (harmless one-step delay) or doesn't.
        colony.setdefault("garrison_rating", 0.0)
        colony.setdefault("continuance_hall", False)
        # Same backfill pattern again for the 2026-09-05 Colonial Warden /
        # remaining-specializations pass (fuel_reserve for fuel_world,
        # trade_throughput for depot_trade_world, both summed into
        # Quartermaster-General's Council entry): a save from before this
        # pass won't have either key, which would otherwise KeyError the
        # first time show_council()/show_colonies() reads them. 0.0 is
        # always correct for a pre-existing colony -- both stats only ever
        # accumulate going forward.
        colony.setdefault("fuel_reserve", 0.0)
        colony.setdefault("trade_throughput", 0.0)

    # Same backfill pattern for AUDIT_COST_SUPPORT_SUPPLIES/
    # AUDIT_COOLDOWN_STEPS (added 2026-09-04): a save from before that
    # change won't have "last_audit_step" in its audit_system dict, which
    # would otherwise KeyError the first time handle_audit() runs.
    if "audit_system" in world:
        world["audit_system"].setdefault("last_audit_step", {})

    # Bug found and fixed 2026-09-04: _hull_counters is a module-level
    # global (see its definition near build_ship_and_facility_state()),
    # not part of `world`, so it used to reset to {"freighter": 1,
    # "light_warship": 0} on every process start regardless of what was
    # saved -- the next hull the shipyard completed after a save/load
    # could then reuse an already-taken hull id, silently overwriting
    # that ship's entry in world["ships"] and duplicating its name in
    # ship_classes[...].in_service.
    if "hull_counters" in saved:
        _hull_counters.update(saved["hull_counters"])
    else:
        # Backfill for a save made before hull_counters was persisted:
        # infer each counter from the highest hull number already present
        # in world["ships"], so freshly-generated numbering can't collide
        # with a hull that already exists in this save.
        for ship_id in world.get("ships", {}):
            if ship_id.startswith("csv_hull_"):
                _hull_counters["freighter"] = max(_hull_counters["freighter"], int(ship_id.rsplit("_", 1)[-1]))
            elif ship_id.startswith("lws_hull_"):
                _hull_counters["light_warship"] = max(
                    _hull_counters["light_warship"], int(ship_id.rsplit("_", 1)[-1])
                )

    if new_research_state is not None:
        if research_missing_nodes:
            print(
                f"WARNING: this save references {len(research_missing_nodes)} research node(s) "
                f"that predate saving dynamic research nodes properly "
                f"({', '.join(sorted(research_missing_nodes))}) -- they could not be restored and "
                "have been dropped. This should only affect a save made before 2026-09-04."
            )
        world["research"] = new_research_state

    if new_penal_records is not None:
        world["penal_records"] = new_penal_records

    # Backfill for a save made before the 2026-09-05 Penal Code labor-
    # economy wiring: a Toil/Penal Legion record from back then was filed
    # with the old generic "sentenced" status and no "term_remaining" at
    # all -- update_penal_labor() only ever acts on status == "serving",
    # so left alone such a record would just sit inert forever, which is
    # a safe but slightly wrong "did this sentence ever happen" outcome.
    # Marking it "term_served" instead is the only choice that can't
    # retroactively grant free labor output or garrison strength for a
    # sentence the player already saw resolved under the old rules -- the
    # alternative (guessing a remaining term) would let a reload silently
    # hand out labor/garrison the player never actually earned.
    for record in world.get("penal_records", []):
        if record.get("status") == "sentenced" and record.get("tier") in _LEGION_TERM_STEPS:
            record["status"] = "term_served"
            record.setdefault("term_remaining", 0)
        # Hardening added 2026-09-05 (stress-test pass): a "serving" record
        # with no "term_remaining" at all can't come from normal play (see
        # update_penal_labor()'s docstring), only a hand-edited or
        # partially-written save -- treat it the same way, as already
        # served, rather than relying solely on update_penal_labor()'s own
        # .get() default to avoid crashing on the next `advance`.
        elif record.get("status") == "serving" and "term_remaining" not in record:
            record["status"] = "term_served"
            record["term_remaining"] = 0


def handle_study_fragments():
    """Spend banked xenos fragments on a direct Collegium analysis pass.

    Wired into the research lane/tech-tree system as of 2026-09-07: this
    is the sole way world["research"].evidence_banked ever increases,
    which is what makes the xenology lane's evidence-gated first node
    (xn_fragment_baseline_analysis, see TechNode.evidence_required)
    reachable at all. Xenos fragments were seeded once at the cycle-29
    sync with nothing that replenishes them, so at most one analysis is
    ever possible in the current game -- by design, this call only ever
    needs to bank 1 evidence, never more (see docs/systems/research.md's
    xenology section for the full reasoning, including why every other
    xenology node chains off this one via a normal prerequisite instead
    of requiring further evidence that could never be banked).

    Design decision made 2026-09-07, not previously confirmed by Ryan
    (see lore/gaps.md's "Xenology's unlock gate" entry): the lane's
    first node also requires md_salvage_field_recovery already
    completed, on top of this evidence. gaps.md flagged two possible
    readings of the narrative's "locked behind completion of the
    salvage operation" -- the xenos_fragments evidence mechanic, or a
    real salvage-related tech node -- without confirming either. Both
    gates are applied here rather than picking one, since the existing
    md_salvage_field_recovery node's own flavor text ("what looked like
    scrap starts yielding intact components and data cores") reads as a
    strong match for "the salvage operation," and requiring both doesn't
    contradict the narrative's language either way. Worth confirming
    directly if new Perplexity content clarifies which was meant.
    """
    if world["xenos_fragments"] < 3:
        print(f"Insufficient xenos fragments for analysis (have {world['xenos_fragments']}, need 3).")
        return
    world["xenos_fragments"] -= 3
    print(
        "The Collegium completes its first formal analysis of the recovered hull fragments. "
        "Construction methods are unlike anything in the Directorate's own engineering tradition -- "
        "confirmed non-human origin, but no further conclusions can yet be drawn."
    )
    state = world["research"]
    add_evidence(state, 1)
    refresh_draw_pool(state, "xenology", guaranteed_ids={"xn_fragment_baseline_analysis"})
    if "xn_fragment_baseline_analysis" in state.active_pool.get("xenology", []):
        log_event(
            "Xenology: fragment analysis complete. 'Fragment Baseline Analysis' is now available for "
            "research under the xenology lane."
        )
    elif "xn_fragment_baseline_analysis" not in state.completed:
        log_event(
            "Xenology: fragment analysis complete and evidence banked, but 'Fragment Baseline Analysis' "
            "still requires Salvage Field Recovery Doctrine researched first."
        )


def handle_survey(args):
    """Handle `survey <name>`: spend refined metal at Mars to survey a
    new colony target. Creates the colony in "surveyed" status -- not
    yet an outpost, produces nothing, consumes nothing.
    """
    if len(args) < 1:
        print("Usage: survey <name>")
        return
    name = " ".join(args)
    colony_id = name.lower().replace(" ", "_")
    if colony_id in world["colonies"]:
        print(f"A colony survey named '{name}' already exists.")
        return

    mars = world["locations"]["mars"]
    if mars["refined_metal"] < SURVEY_COST:
        print(f"Not enough refined metal to survey (need {SURVEY_COST:.0f}, have {mars['refined_metal']:.0f}).")
        return

    mars["refined_metal"] -= SURVEY_COST
    distance_steps = random.randint(*SURVEY_DISTANCE_RANGE_STEPS)
    world["colonies"][colony_id] = {
        "name": name, "status": "surveyed", "specialization": None,
        "support_supplies": 0.0, "raw_metal": 0.0, "refined_metal": 0.0, "population": 0,
        # How far this target actually turned out to be, in one-way
        # `advance` steps to Mars -- unknown until surveyed. See
        # SURVEY_DISTANCE_RANGE_STEPS's comment for why this isn't fixed.
        "distance_steps": distance_steps,
        "tithe_grade": None,
        "tithe_shortfall_streak": 0,
        # Council-seat wiring (2026-09-05): garrison_rating only ever grows
        # for fortress_world colonies (see FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE),
        # but every colony gets the field so Marshal-General's aggregate sum
        # in show_council() never has to guess whether it's present.
        "garrison_rating": 0.0,
        # continuance_hall flips True once population crosses
        # CONTINUANCE_HALL_POPULATION_THRESHOLD (see update_colonies()) --
        # deliberately not tied to a specific specialization, since the
        # lore frames it as something any colony eventually grows into.
        "continuance_hall": False,
        # fuel_reserve/trade_throughput (2026-09-05, Colonial Warden pass):
        # only ever grow for fuel_world/depot_trade_world colonies (see
        # FUEL_WORLD_RESERVE_PER_CYCLE/DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE),
        # but every colony gets both fields so Quartermaster-General's
        # aggregate sums in show_council() never have to guess whether
        # they're present -- same pattern as garrison_rating above.
        "fuel_reserve": 0.0,
        "trade_throughput": 0.0,
    }
    print(
        f"Survey complete: '{name}' is viable for an outpost, {distance_steps} step(s) from Mars. "
        f"Use 'outpost {colony_id}' to establish one."
    )


def handle_outpost(args):
    """Handle `outpost <colony_id>`: establish an outpost at a surveyed
    colony, spending refined metal (Mars) and seeding support supplies
    (Earth) for the expedition, per DESIGN_SPINE.md's colony chain.
    """
    if len(args) != 1:
        print("Usage: outpost <colony_id>. Type 'colonies' to see valid ids.")
        return
    colony_id = args[0]
    colony = world["colonies"].get(colony_id)
    if colony is None or colony["status"] != "surveyed":
        print(f"'{colony_id}' is not a surveyed colony awaiting an outpost. Type 'colonies' to check.")
        return

    mars = world["locations"]["mars"]
    earth = world["locations"]["earth"]
    if mars["refined_metal"] < OUTPOST_COST or earth["support_supplies"] < OUTPOST_SUPPORT_SEED:
        print("Insufficient resources to establish this outpost (refined metal at Mars, support supplies from Earth).")
        return

    mars["refined_metal"] -= OUTPOST_COST
    earth["support_supplies"] -= OUTPOST_SUPPORT_SEED
    colony["status"] = "outpost"
    colony["support_supplies"] = OUTPOST_SUPPORT_SEED
    colony["population"] = 50
    print(f"Outpost established at '{colony['name']}'. Population 50. Use 'specialize {colony_id} <type>' when ready.")


def handle_specialize(args):
    """Handle `specialize <colony_id> <type>`: commit an existing outpost
    to one of the specializations DESIGN_SPINE.md lists (minus hive world
    -- explicitly out of scope). Moves the colony to "established" status.
    """
    if len(args) != 2:
        types = ", ".join(SPECIALIZATION_EFFECTS.keys())
        print(f"Usage: specialize <colony_id> <type>. Valid types: {types}")
        return
    colony_id, spec_type = args
    colony = world["colonies"].get(colony_id)
    if colony is None or colony["status"] != "outpost":
        print(f"'{colony_id}' is not an outpost ready to specialize. Type 'colonies' to check.")
        return
    if spec_type not in SPECIALIZATION_EFFECTS:
        types = ", ".join(SPECIALIZATION_EFFECTS.keys())
        print(f"Unknown specialization '{spec_type}'. Valid types: {types}")
        return

    mars = world["locations"]["mars"]
    if mars["refined_metal"] < SPECIALIZE_COST:
        print(f"Not enough refined metal to specialize (need {SPECIALIZE_COST:.0f}, have {mars['refined_metal']:.0f}).")
        return

    mars["refined_metal"] -= SPECIALIZE_COST
    colony["specialization"] = spec_type
    colony["status"] = "established"
    flavor_only = not SPECIALIZATION_EFFECTS[spec_type]
    note = " (flavor only -- no mechanical effect exists for this type yet)" if flavor_only else ""
    print(f"'{colony['name']}' specialized as {spec_type}{note}.")

    grade = _tithe_grade_level(colony)
    colony["tithe_grade"] = grade
    if grade is not None:
        print(
            f"The Chancellery assesses '{colony['name']}' at {TITHE_GRADE_NAMES[grade]} "
            f"({TITHE_GRADE_QUOTA[grade]:.0f} owed every {TITHE_CYCLE_STEPS} steps)."
        )


def update_colonies():
    """Run one production/consumption step for every outpost/established
    colony: consume support supplies during the fragile pre-established
    "outpost" phase, and -- for established colonies -- apply their
    specialization's effect, using only resource types this codebase
    already tracks.

    Bug found and fixed 2026-09-05 (stress-test pass): this used to keep
    charging COLONY_SUPPORT_CONSUMPTION forever, for "established" colonies
    too, with only agri_world's support_supplies_per_cycle ever offsetting
    it. Every other specialization (6 of 8) had no way to receive more
    support supplies once established -- no colony-resupply mechanic exists
    anywhere in the game, unlike Earth->Mars (freighters) or colony->Mars
    (tithe convoys) -- so with the shipped constants (OUTPOST_SUPPORT_SEED
    50.0 / COLONY_SUPPORT_CONSUMPTION 5.0/cycle), EVERY non-agri_world
    colony permanently stalled at exactly cycle 10 after founding, forever
    after printing "Growth and output stalled." This wasn't a rare edge
    case -- it was the default outcome of ordinary play for 6 of 8
    specializations, and it cascaded badly: a stalled mining_world/
    forge_world colony can never pay another tithe, so
    _escalate_tithe_shortfall() kept re-filing "hoarding_of_strategic_supply"
    charges against it forever (194 duplicate charges in one 2000-step
    stress run); a stalled fortress_world's garrison_rating -- this
    session's own new "accumulating" stat -- froze permanently after 40
    points; a stalled civilian_world's population growth also froze,
    which additionally made the just-added Continuance Hall milestone
    unreachable under default tuning (population stops one step before a
    later cycle would have re-checked it).

    Fixed by treating support supplies as funding only the "outpost"
    phase -- the fragile pre-established expedition, per
    OUTPOST_SUPPORT_SEED's own existing comment ("the expedition's
    starting stock") -- not an indefinite external dependency an
    established colony has no way to ever resolve on its own. Once a
    colony reaches "established" status, its specialization's own effects
    (raw_metal, refined_metal, population, RP, garrison_rating) ARE its
    self-sufficiency; nothing else in this codebase bills an established
    colony for anything ongoing (Mars/Earth don't either), so singling out
    support supplies as the one forever-cost with only one specialization
    able to pay it was the actual defect, not a difficulty curve. agri_world's
    support_supplies_per_cycle effect is unchanged -- it still accumulates,
    still doesn't feed anything else (see tithe-system.md's "Who owes a
    tithe" dead-end note, still accurate) -- this fix just stops it being
    the only specialization compatible with the game continuing to run.
    """
    for colony in world["colonies"].values():
        if colony["status"] not in ("outpost", "established"):
            continue

        if colony["status"] == "outpost":
            if colony["support_supplies"] >= COLONY_SUPPORT_CONSUMPTION:
                colony["support_supplies"] -= COLONY_SUPPORT_CONSUMPTION
            else:
                log_event(f"ALERT: '{colony['name']}' lacks support supplies. Growth and output stalled.")
                continue

        # Council-seat wiring (2026-09-05): a colony raises its Continuance
        # Hall once population crosses CONTINUANCE_HALL_POPULATION_THRESHOLD
        # -- a real, one-way milestone (never re-checked once True) that
        # First Steward of Continuance's Council entry reports on. This is
        # deliberately outside the "established"-only block below: the lore
        # ("each colony has a Continuance Hall") doesn't tie it to any one
        # specialization, only to population, so it stays correct even if a
        # future change lets population grow some other way.
        if not colony["continuance_hall"] and colony["population"] >= CONTINUANCE_HALL_POPULATION_THRESHOLD:
            colony["continuance_hall"] = True
            log_event(f"'{colony['name']}' has grown enough to raise a Continuance Hall.")

        if colony["status"] == "established":
            effects = SPECIALIZATION_EFFECTS[colony["specialization"]]
            if "raw_metal_per_cycle" in effects:
                colony["raw_metal"] += effects["raw_metal_per_cycle"]
            if "refined_metal_per_cycle" in effects:
                colony["refined_metal"] += effects["refined_metal_per_cycle"]
            if "support_supplies_per_cycle" in effects:
                colony["support_supplies"] += effects["support_supplies_per_cycle"]
            if "population_growth_per_cycle" in effects:
                colony["population"] += effects["population_growth_per_cycle"]
            if "garrison_rating_per_cycle" in effects:
                colony["garrison_rating"] += effects["garrison_rating_per_cycle"]
            if "fuel_reserve_per_cycle" in effects:
                colony["fuel_reserve"] += effects["fuel_reserve_per_cycle"]
            if "trade_throughput_per_cycle" in effects:
                colony["trade_throughput"] += effects["trade_throughput_per_cycle"]
            if "rp_lane" in effects:
                state = world["research"]
                lane = effects["rp_lane"]
                state.rp_stockpile[lane] = state.rp_stockpile.get(lane, 0.0) + effects["rp_per_cycle"]


def _tithe_grade_level(colony):
    """Current Tithe Grade level (0-4) for an established colony, or None
    if its specialization owes no material tithe (see
    TITHE_ELIGIBLE_SPECIALIZATIONS). Recomputed live rather than cached
    on the colony, since population growth can raise it over time.
    """
    spec = colony["specialization"]
    if spec not in TITHE_ELIGIBLE_SPECIALIZATIONS:
        return None
    level = TITHE_GRADE_BASE_BY_SPECIALIZATION[spec]
    for threshold in TITHE_GRADE_POPULATION_THRESHOLDS:
        if colony["population"] >= threshold:
            level += 1
    return min(level, MAX_TITHE_GRADE)


def _open_or_refresh_tithe_shortfall(colony_id, colony, shortfall):
    """Register this cycle's unmet tithe as something the Bureau can
    audit -- reuses the same discovery/correction mechanic that already
    covers forge_marshal's silent metal drain (see update_audit()),
    rather than building a second parallel concealment system.
    """
    concealments = world["audit_system"]["active_concealments"]
    existing = next(
        (c for c in concealments if c["kind"] == "tithe_shortfall" and c["colony_id"] == colony_id),
        None,
    )
    if existing:
        existing["total_shortfall"] += shortfall
        existing["cycles_short"] += 1
    else:
        concealments.append({
            "kind": "tithe_shortfall",
            "seat_id": "chancellor_general",
            "colony_id": colony_id,
            "colony_name": colony["name"],
            "started_cycle": world["time"],
            "total_shortfall": shortfall,
            "cycles_short": 1,
        })
    print(
        f"Tithe assessment: '{colony['name']}' falls short by {shortfall:.1f} "
        f"({colony['tithe_shortfall_streak']} cycle(s) running)."
    )


def _escalate_tithe_shortfall(colony_id, colony):
    """After TITHE_SHORTFALL_CHARGE_THRESHOLD consecutive shortfalls with
    no Bureau audit correcting one in between, the Chancellery refers the
    colony's administrator for formal charges instead of carrying the
    discrepancy indefinitely. Clears the open concealment -- it's now a
    matter of record, not something left for the Bureau to still "catch".

    Defensive guard added 2026-09-05 (stress-test pass): don't file a
    second "hoarding_of_strategic_supply" charge against the same
    administrator while an earlier one is still "serving" its Toil Legion
    term. This was harmless in isolation before today's colony-stall fix
    (a colony that could never recover would just accumulate duplicate
    charges forever -- one stress run hit 194 against two colonies), and
    stays good hygiene afterward: an administrator already serving time
    for exactly this offense doesn't need a second, redundant sentence
    stacked on top before the first one has even run its course. The
    streak/concealment still reset either way -- the delinquency episode
    is handled either by the new charge or by the one already in
    progress, not left open.
    """
    name = f"the colonial administrator of {colony['name']}"
    already_serving = any(
        r["name"] == name and r["article_id"] == "hoarding_of_strategic_supply" and r["status"] == "serving"
        for r in world["penal_records"]
    )
    if not already_serving:
        _file_charge(name, "hoarding_of_strategic_supply")
    colony["tithe_shortfall_streak"] = 0
    world["audit_system"]["active_concealments"] = [
        c for c in world["audit_system"]["active_concealments"]
        if not (c["kind"] == "tithe_shortfall" and c["colony_id"] == colony_id)
    ]
    log_event(f"Chancellery escalation: '{colony['name']}''s persistent shortfall referred for formal charges.")


def update_tithes():
    """Run one Chancellery tithe assessment, every TITHE_CYCLE_STEPS steps.

    Every established mining_world/forge_world colony owes a flat quota
    (by Tithe Grade). Paid in full: dispatched as a tithe convoy with
    real travel time to Mars (see update_tithe_convoys()). Paid short:
    the shortfall becomes an auditable Chancellery discrepancy; if it
    persists too many cycles uncaught, it escalates into a formal
    Penal Code charge. See docs/systems/tithe-system.md.
    """
    if world["time"] % TITHE_CYCLE_STEPS != 0:
        return

    for colony_id, colony in world["colonies"].items():
        if colony["status"] != "established":
            continue
        grade = _tithe_grade_level(colony)
        colony["tithe_grade"] = grade
        if grade is None:
            continue

        owed = TITHE_GRADE_QUOTA[grade]
        available = colony["refined_metal"] + colony["raw_metal"]
        paid = min(owed, available)

        from_refined = min(paid, colony["refined_metal"])
        from_raw = paid - from_refined
        colony["refined_metal"] -= from_refined
        colony["raw_metal"] -= from_raw

        if paid > 0:
            world["tithe_convoys"].append({
                "colony_id": colony_id,
                "colony_name": colony["name"],
                "refined_metal": from_refined,
                "raw_metal": from_raw,
                "steps_remaining": colony["distance_steps"],
            })

        shortfall = owed - paid
        if shortfall <= 0:
            colony["tithe_shortfall_streak"] = 0
            # A colony that's caught back up is no longer concealing
            # anything -- clear any stale open shortfall from an earlier
            # cycle rather than leaving it sitting on the Bureau's list
            # forever waiting for an audit that no longer has anything
            # live to find.
            world["audit_system"]["active_concealments"] = [
                c for c in world["audit_system"]["active_concealments"]
                if not (c["kind"] == "tithe_shortfall" and c["colony_id"] == colony_id)
            ]
            world["tithe_system"]["log"].append({
                "cycle": world["time"], "colony_id": colony_id, "colony_name": colony["name"],
                "grade": TITHE_GRADE_NAMES[grade], "owed": owed, "paid": paid,
            })
            print(f"Tithe assessment: '{colony['name']}' ({TITHE_GRADE_NAMES[grade]}) remits {paid:.1f} in full.")
        else:
            colony["tithe_shortfall_streak"] += 1
            _open_or_refresh_tithe_shortfall(colony_id, colony, shortfall)
            if colony["tithe_shortfall_streak"] >= TITHE_SHORTFALL_CHARGE_THRESHOLD:
                _escalate_tithe_shortfall(colony_id, colony)


def update_tithe_convoys():
    """Advance every in-transit tithe convoy by one step; deliver those
    that arrive into Mars's stockpile. Runs every `advance` step, not
    just on tithe-cycle steps -- a convoy already en route keeps moving
    regardless of when the next assessment happens.
    """
    mars = world["locations"]["mars"]
    still_in_transit = []
    for convoy in world["tithe_convoys"]:
        convoy["steps_remaining"] -= 1
        if convoy["steps_remaining"] <= 0:
            deposit(mars, "refined_metal", convoy["refined_metal"])
            deposit(mars, "raw_metal", convoy["raw_metal"])
            print(
                f"Tithe convoy from '{convoy['colony_name']}' arrives at Mars: "
                f"{convoy['refined_metal']:.1f} refined metal, {convoy['raw_metal']:.1f} raw metal delivered."
            )
        else:
            still_in_transit.append(convoy)
    world["tithe_convoys"] = still_in_transit


def show_colonies():
    """Print every colony's status, specialization, current stockpiles,
    distance from Mars, and Tithe Grade/standing.
    """
    print("\n=== COLONIES ===")
    if not world["colonies"]:
        print("No colonies surveyed yet. Use 'survey <name>' to begin.")
        return
    for colony_id, colony in world["colonies"].items():
        spec = colony["specialization"] or "none"
        print(
            f"\n  {colony_id}: {colony['name']} [{colony['status']}] -- specialization: {spec} "
            f"-- {colony['distance_steps']} step(s) from Mars"
        )
        if colony["status"] != "surveyed":
            print(
                f"    Support {colony['support_supplies']:.1f} | Raw metal {colony['raw_metal']:.1f} | "
                f"Refined metal {colony['refined_metal']:.1f} | Population {colony['population']}"
            )
            if colony.get("continuance_hall"):
                print("    Continuance Hall: established")
            if colony.get("garrison_rating", 0.0) > 0:
                print(f"    Garrison rating: {colony['garrison_rating']:.0f}")
            if colony.get("fuel_reserve", 0.0) > 0:
                print(f"    Fuel reserve: {colony['fuel_reserve']:.0f}")
            if colony.get("trade_throughput", 0.0) > 0:
                print(f"    Trade throughput: {colony['trade_throughput']:.0f}")
        if colony["status"] == "established":
            grade = colony.get("tithe_grade")
            if grade is None:
                print("    Tithe: exempt (no material tithe for this specialization yet)")
            else:
                streak = colony["tithe_shortfall_streak"]
                standing = "in good standing" if streak == 0 else f"{streak} cycle(s) short, running"
                print(
                    f"    Tithe: {TITHE_GRADE_NAMES[grade]} -- {TITHE_GRADE_QUOTA[grade]:.0f} "
                    f"owed every {TITHE_CYCLE_STEPS} steps -- {standing}"
                )

    if world["tithe_convoys"]:
        print("\n  Tithe convoys en route to Mars:")
        for convoy in world["tithe_convoys"]:
            print(
                f"    {convoy['colony_name']}: {convoy['refined_metal']:.1f} refined metal, "
                f"{convoy['raw_metal']:.1f} raw metal -- {convoy['steps_remaining']} step(s) out"
            )


def advance_world():
    """Advance the entire simulation by one discrete step.

    Later this same kind of update will run automatically in a pausable
    real-time loop. Manual steps are easier to inspect while learning.
    """
    world["time"] += 1
    print(f"\n--- Advancing simulation to step {world['time']} ---")

    update_earth()
    update_mars()
    update_penal_labor()
    update_colonies()
    update_audit()
    # Bug found and fixed 2026-09-04: this order used to be
    # update_tithes() then update_tithe_convoys(), meaning a convoy
    # dispatched THIS step by update_tithes() was immediately decremented
    # once by update_tithe_convoys() in the same advance_world() call --
    # so every convoy actually delivered one step earlier than its
    # colony's real distance_steps, contradicting the documented "travel
    # time is real" design (docs/systems/tithe-system.md) and the
    # steps_remaining the `colonies` command shows the player right after
    # dispatch. Advancing convoys already in transit BEFORE this step's
    # assessment means a freshly-dispatched convoy's first decrement
    # happens on the *next* advance, giving it the full distance_steps.
    update_tithe_convoys()
    update_tithes()
    update_freighters()
    update_research()
    update_lab_specialization()
    update_shipyard()
    update_standing_orders()


def show_help():
    """Show every command accepted by the simulation."""
    print("\nCommands:")
    print("  status                        - Show Earth, Mars, every freighter, research, shipyard, and lab summaries")
    print("  advance                       - Advance the simulation by one step")
    print("  research                      - Show full Collegium research status (RP, pool, completed)")
    print("  invest <lane> <pos>           - Spend a lane's banked RP into its pool position <pos>")
    print("  pilot <lane> <pos>            - Gamble banked RP on an early breakthrough at pool position <pos>")
    print("  shipyard                      - Show Mars Shipyard slots, guarantees, and build queue")
    print("  fleet                         - Show ship classes, current MK, stats, and in-service roster")
    print("  labs                          - Show Collegium laboratories, their roles, and current multipliers")
    print("  build_lab                     - Construct the Collegium's next laboratory")
    print("  docket                        - Show the Directorate Penal Code and filed records")
    print("  code                          - Show the five-article Directorate Code")
    print("  audit <seat_id>              - Bureau attempts to uncover concealment under that seat")
    print("                                  (costs support supplies + a per-target cooldown -- see 'audit' log)")
    print("  audit                         - Show the Bureau audit log and doctrine")
    print("  council                       - Show the Directorate Council, Branches A-K, and the Vigil")
    print("  orders                        - Show Standing Orders and current equipment status")
    print("  events [count]                - Show the last [count] (default 10) logged events")
    print("  study_fragments               - Spend 3 xenos fragments on a Collegium analysis pass")
    print("  survey <name>                 - Survey a new colony target")
    print("  outpost <colony_id>           - Establish an outpost at a surveyed colony")
    print("  specialize <colony_id> <type> - Commit an outpost to a specialization")
    print("  colonies                      - Show all surveyed/outpost/established colonies")
    print("  tithes                        - Show the Chancellery's tithe ledger (fully remitted tithes)")
    print("  save                          - Save full world state to state.json")
    print("  load                          - Load full world state from state.json")
    print("  charge <name> <article_id>    - Sentence <name> under a Penal Code article")
    print("  confirm_servitor <name> <y/n> <y/n> - Confirm (Vigil, Grand Director) a pending Servitor Conversion")
    print("  help                          - Show available commands")
    print("  quit                          - Exit the simulation")


def main():
    """Start the terminal command loop.

    `while True` means keep asking for a command until the player uses `quit`.
    `.strip()` removes accidental spaces, and `.lower()` makes commands
    case-insensitive: STATUS, Status, and status all work. `.split()`
    breaks the typed line into words, so commands like `invest` can take
    arguments after the command name itself.
    """
    print("ASTERION FOUNDRY // SOL DIRECTORATE")
    print("Lessons 01-04: Forge Production, Freight Logistics, Collegium Research,")
    print("Shipyard Slots, Ship Design, Lab Specialization, and the Penal Code")
    show_help()

    while True:
        typed_line = input("\nCommand > ").strip().lower()
        parts = typed_line.split()
        command = parts[0] if parts else ""
        args = parts[1:]

        if command == "status":
            show_status()
        elif command == "advance":
            advance_world()
        elif command == "research":
            show_research()
        elif command == "invest":
            handle_invest(args)
        elif command == "pilot":
            handle_pilot(args)
        elif command == "shipyard":
            show_shipyard()
        elif command == "fleet":
            show_fleet()
        elif command == "labs":
            show_labs()
        elif command == "build_lab":
            handle_build_lab()
        elif command == "docket":
            show_docket()
        elif command == "code":
            show_directorate_code()
        elif command == "audit":
            if args:
                handle_audit(args)
            else:
                show_audit()
        elif command == "council":
            show_council()
        elif command == "orders":
            show_standing_orders()
        elif command == "events":
            show_events(args)
        elif command == "study_fragments":
            handle_study_fragments()
        elif command == "survey":
            handle_survey(args)
        elif command == "outpost":
            handle_outpost(args)
        elif command == "specialize":
            handle_specialize(args)
        elif command == "colonies":
            show_colonies()
        elif command == "tithes":
            show_tithes()
        elif command == "save":
            save_game()
        elif command == "load":
            load_game()
        elif command == "charge":
            handle_charge(args)
        elif command == "confirm_servitor":
            handle_confirm_servitor(args)
        elif command == "help":
            show_help()
        elif command == "quit":
            print("Simulation terminated.")
            break
        else:
            print("Unknown command. Type 'help' for available commands.")


# Research, ship classes, the shipyard, labs, and the Penal Code are all
# built here, after every function above exists, and before the command
# loop starts.
world["research"] = build_research_state()
build_ship_and_facility_state()
seed_completed_research()
# This guard runs `main` only when Python starts this file directly (e.g.
# `python src/main.py`), not when a test file imports it as a module —
# that is exactly what lets tests/test_main_integration.py import `world`
# and every function above without blocking on `input()`.
if __name__ == "__main__":
    load_game()
    main()
