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
- The freighter CSV Meridian automatically ferries support supplies from
  Earth to Mars, and refined metal back from Mars to Earth, so Mars no
  longer stalls on its own the way it did in Lesson 01.
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
| Shipyard slots      | `src/shipyard.py`                     | `world["shipyard"]`, `world["shipyard_slots"]`   | `SHIPYARD_METAL_RESERVE`, `SLOT_EXPAND_COST`, `SHIPYARD_EXPAND_BATCH_SIZE`, `BASE_BUILD_TIME_STEPS` | shipyard |
| Lab specialization  | `src/research/lab_specialization.py`  | `world["lab_roles"]`, `world["multipliers"]`     | `LAB_BUILD_COST`, `LAB_TICK_INTERVAL_STEPS`, `LAB_TICK_MAGNITUDE`, `LAB_TICK_FLOOR` | labs, build_lab |
| Directorate Penal Code | `src/penal_code.py`                | `world["penal_code"]`, `world["penal_records"]`  | edit `PenalCode.default_code()` in `penal_code.py` to add/change articles | docket, charge, confirm_servitor |

Every one of these constants is defined once, near the top of its
section below, with a comment explaining what raising or lowering it
does. Change the constant, not the function body, when you just want to
retune a number.
"""

from research import Lab, ResearchState, Scientist
from research.engine import attempt_pilot_project, generate_rp, invest_rp, refresh_draw_pool
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
from penal_code import CAPITAL_TIER, PenalCode, charge, confirm_capital_sentence

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
# How many `advance` steps a slot needs to finish one hull of each class,
# before the lab-specialization construction-time multiplier is applied.
BASE_BUILD_TIME_STEPS = {"freighter": 4, "light_warship": 6}
CATEGORY_TO_CLASS = {LOGISTICS: "freighter", WARSHIP: "light_warship"}

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
    "time": 0,
    "locations": {
        "earth": {
            "name": "Earth",
            "support_supplies": 500,
            "raw_metal": 0,
            "refined_metal": 0,
        },
        "mars": {
            "name": "Mars",
            "support_supplies": 100,
            "raw_metal": 0,
            "refined_metal": 0,
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
    },
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
            id="freighter", category="logistics", current_mk="Mark I", in_service=["CSV Meridian"]
        ),
        "light_warship": ShipClass(
            id="light_warship", category="warship", current_mk="Mark I", in_service=[]
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
    world["shipyard"] = Shipyard(location="mars", slots_total=1, flexible=1)
    world["shipyard_slots"] = [
        {"locked_category": None, "building_class_id": None, "steps_remaining": 0}
    ]

    # Lab #1 is always the flexible auto-research lab (see build_research_state).
    world["lab_roles"] = {"mars_collegium_lab": FLEXIBLE_AUTO_RESEARCH}
    world["multipliers"] = {
        "construction_time_multiplier": 1.0,
        "research_time_multiplier": 1.0,
        "universal_efficiency_multiplier": 1.0,
    }

    world["penal_code"] = PenalCode.default_code()
    world["penal_records"] = []


def show_status():
    """Print the resource stockpiles for every current location, the
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

    ship = world["ships"]["csv_meridian"]
    status_labels = {
        "idle_at_earth": "docked at Earth, loading",
        "transit_to_mars": f"in transit to Mars ({ship['travel_remaining']} step(s) remaining)",
        "idle_at_mars": "docked at Mars, loading",
        "transit_to_earth": f"in transit to Earth ({ship['travel_remaining']} step(s) remaining)",
    }
    print(
        f"{ship['name']}: {status_labels[ship['status']]} | "
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


def update_mars():
    """Run one production step for the Mars forge world.

    Mars needs support supplies to keep its workforce and forge complexes
    operating. The base cost is 10 per step; the Collegium's universal
    efficiency multiplier (see docs/systems/lab-specialization.md) can
    lower this over time, down to a floor of half price. When supplied,
    Mars extracts raw metal and refines part of it.
    """
    mars = world["locations"]["mars"]
    cost = max(1, round(10 * world["multipliers"]["universal_efficiency_multiplier"]))

    if mars["support_supplies"] >= cost:
        mars["support_supplies"] -= cost
        mars["raw_metal"] += 15

        # The forge complex uses part of newly available raw metal immediately.
        mars["raw_metal"] -= 10
        mars["refined_metal"] += 8

        print(
            f"Mars forge complexes consumed {cost} support supplies, "
            "extracted 15 raw metal, and refined 10 raw metal into 8 refined metal."
        )
    else:
        print(
            "ALERT: Mars lacks support supplies. "
            "Forge complexes are idle; extraction and refining have stopped."
        )


def update_earth():
    """Run one simple Earth update.

    Earth has no production rule yet. This function exists to show that
    every location can have its own update rules as the project grows.
    """
    earth = world["locations"]["earth"]
    _ = earth
    print("Earth command reports stable reserves. No new production this step.")


def update_csv_meridian():
    """Run one logistics step for the freighter CSV Meridian.

    The freighter cycles automatically: load support supplies at Earth,
    travel to Mars, unload, load refined metal at Mars, travel back to
    Earth, unload, and repeat. See DESIGN_SPINE.md's "First loop" for the
    design this implements. There is no player command for this yet —
    like Mars's forge complex, it simply runs every time the simulation
    advances.

    Freighters the shipyard builds later (see update_shipyard()) do not
    join this loop automatically — they are delivered idle at Mars.
    Generalizing this function into a loop over every ship with
    `class_id == "freighter"` is the natural next step if you want every
    freighter automatically running supply routes; it is intentionally
    left as a customization point rather than assumed.
    """
    ship = world["ships"]["csv_meridian"]

    if ship["status"] == "idle_at_earth":
        earth = world["locations"]["earth"]
        load_amount = min(ship["cargo_capacity"], earth["support_supplies"])
        earth["support_supplies"] -= load_amount
        ship["cargo_support_supplies"] = load_amount
        ship["status"] = "transit_to_mars"
        ship["travel_remaining"] = TRAVEL_TIME_STEPS
        print(f"CSV Meridian loaded {load_amount} support supplies at Earth and departed for Mars.")

    elif ship["status"] == "transit_to_mars":
        ship["travel_remaining"] -= 1
        if ship["travel_remaining"] <= 0:
            mars = world["locations"]["mars"]
            delivered = ship["cargo_support_supplies"]
            mars["support_supplies"] += delivered
            ship["cargo_support_supplies"] = 0
            ship["status"] = "idle_at_mars"
            print(f"CSV Meridian arrived at Mars and unloaded {delivered} support supplies.")
        else:
            print(f"CSV Meridian is in transit to Mars ({ship['travel_remaining']} step(s) remaining).")

    elif ship["status"] == "idle_at_mars":
        mars = world["locations"]["mars"]
        load_amount = min(ship["cargo_capacity"], mars["refined_metal"])
        mars["refined_metal"] -= load_amount
        ship["cargo_refined_metal"] = load_amount
        ship["status"] = "transit_to_earth"
        ship["travel_remaining"] = TRAVEL_TIME_STEPS
        print(f"CSV Meridian loaded {load_amount} refined metal at Mars and departed for Earth.")

    elif ship["status"] == "transit_to_earth":
        ship["travel_remaining"] -= 1
        if ship["travel_remaining"] <= 0:
            earth = world["locations"]["earth"]
            delivered = ship["cargo_refined_metal"]
            earth["refined_metal"] += delivered
            ship["cargo_refined_metal"] = 0
            ship["status"] = "idle_at_earth"
            print(f"CSV Meridian arrived at Earth and delivered {delivered} refined metal.")
        else:
            print(f"CSV Meridian is in transit to Earth ({ship['travel_remaining']} step(s) remaining).")


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
    """
    effect = node.effect

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
        else:
            print(f"{class_id} has reached its final researchable generation ({effect['to_mk']}).")


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
        _apply_ship_design_effect(tech_id, node)
        refresh_draw_pool(state, lane_id)
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
    if result.success:
        _apply_ship_design_effect(tech_id, state.nodes[tech_id])
        refresh_draw_pool(state, lane_id)


def _complete_ship_build(class_id):
    """Spawn a newly built hull of `class_id` and add it to the fleet.

    New ships appear idle at Mars — they are not automatically wired into
    a supply loop the way CSV Meridian is. See update_csv_meridian()'s
    docstring for the customization point that would change that.
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

    # 2. Advance slots already building; completions free the slot.
    for slot in slots:
        if slot["building_class_id"] is not None:
            slot["steps_remaining"] -= 1
            if slot["steps_remaining"] <= 0:
                _complete_ship_build(slot["building_class_id"])
                slot["building_class_id"] = None

    # 3. No idle slots: assign every free slot a build immediately,
    # steering away from whichever category is already in surplus.
    fleet_counts = {
        WARSHIP: len(world["ship_classes"]["light_warship"].in_service),
        LOGISTICS: len(world["ship_classes"]["freighter"].in_service),
    }
    demand_counts = {WARSHIP: fleet_counts[LOGISTICS], LOGISTICS: fleet_counts[WARSHIP]}
    build_time_multiplier = world["multipliers"]["construction_time_multiplier"]

    for slot in slots:
        if slot["building_class_id"] is None:
            allowed = [slot["locked_category"]] if slot["locked_category"] else [WARSHIP, LOGISTICS]
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


def handle_charge(args):
    """Handle the `charge <name> <article_id>` command: sentence a named
    individual under the Directorate Penal Code. See docs/systems/penal-code.md.
    """
    if len(args) != 2:
        print("Usage: charge <name> <article_id>. Type 'docket' to see valid article ids.")
        return

    name, article_id = args
    code = world["penal_code"]
    try:
        tier = charge(code, article_id)
    except KeyError:
        print(f"Unknown article '{article_id}'. Type 'docket' to see valid article ids.")
        return

    record = {"name": name, "article_id": article_id, "tier": tier, "status": "sentenced"}

    if tier == CAPITAL_TIER:
        record["status"] = "awaiting_confirmation"
        print(
            f"{name} charged under '{code.articles[article_id].name}': "
            "typical sentence is SERVITOR CONVERSION (capital, irreversible)."
        )
        print("This cannot be carried out without both a Vigil referral and Grand Director confirmation.")
        print(f"Use: confirm_servitor {name} <yes/no> <yes/no>   (vigil referral, then grand director confirmation)")
    else:
        print(f"{name} charged under '{code.articles[article_id].name}': sentenced to {tier.value.replace('_', ' ').upper()}.")

    world["penal_records"].append(record)


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
            print(f"  {record['name']} — {record['article_id']} — {record['tier'].value} — {record['status']}")

    print("\nUse 'charge <name> <article_id>' to sentence someone. Capital sentences additionally need 'confirm_servitor'.")


def advance_world():
    """Advance the entire simulation by one discrete step.

    Later this same kind of update will run automatically in a pausable
    real-time loop. Manual steps are easier to inspect while learning.
    """
    world["time"] += 1
    print(f"\n--- Advancing simulation to step {world['time']} ---")

    update_earth()
    update_mars()
    update_csv_meridian()
    update_research()
    update_lab_specialization()
    update_shipyard()


def show_help():
    """Show every command accepted by the simulation."""
    print("\nCommands:")
    print("  status                        - Show Earth, Mars, CSV Meridian, research, shipyard, and lab summaries")
    print("  advance                       - Advance the simulation by one step")
    print("  research                      - Show full Collegium research status (RP, pool, completed)")
    print("  invest <lane> <pos>           - Spend a lane's banked RP into its pool position <pos>")
    print("  pilot <lane> <pos>            - Gamble banked RP on an early breakthrough at pool position <pos>")
    print("  shipyard                      - Show Mars Shipyard slots, guarantees, and build queue")
    print("  fleet                         - Show ship classes, current MK, stats, and in-service roster")
    print("  labs                          - Show Collegium laboratories, their roles, and current multipliers")
    print("  build_lab                     - Construct the Collegium's next laboratory")
    print("  docket                        - Show the Directorate Penal Code and filed records")
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

# This guard runs `main` only when Python starts this file directly (e.g.
# `python src/main.py`), not when a test file imports it as a module —
# that is exactly what lets tests/test_main_integration.py import `world`
# and every function above without blocking on `input()`.
if __name__ == "__main__":
    main()
