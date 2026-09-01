"""Asterion Foundry — Lessons 01-03: Forge Production, Freight Logistics,
and Collegium Research.

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
  is a deliberate player choice. See docs/systems/research.md for the
  full design.
"""

from research import Lab, ResearchState, Scientist
from research.engine import attempt_pilot_project, generate_rp, invest_rp, refresh_draw_pool

# How many `advance` steps CSV Meridian spends in transit, each direction.
TRAVEL_TIME_STEPS = 2

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
        },
    },
}


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


def show_status():
    """Print the resource stockpiles for every current location, the
    freighter's status, and a one-line research summary.
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


def update_mars():
    """Run one production step for the Mars forge world.

    Mars needs 10 support supplies to keep its workforce and forge complexes
    operating. When supplied, it extracts raw metal and refines part of it.
    """
    mars = world["locations"]["mars"]

    if mars["support_supplies"] >= 10:
        mars["support_supplies"] -= 10
        mars["raw_metal"] += 15

        # The forge complex uses part of newly available raw metal immediately.
        mars["raw_metal"] -= 10
        mars["refined_metal"] += 8

        print(
            "Mars forge complexes consumed 10 support supplies, "
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
    """
    generated = generate_rp(world["research"], dt=1.0)
    produced = {lane: amount for lane, amount in generated.items() if amount > 0}

    if produced:
        parts = ", ".join(f"{lane}: +{amount:.1f} RP" for lane, amount in produced.items())
        print(f"Asterion Collegium generated research points ({parts}).")
    else:
        print("Asterion Collegium labs are unstaffed or idle; no research points generated.")


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
    immediately and reopens a slot in that lane's discovery pool.
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
        refresh_draw_pool(state, lane_id)


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


def show_help():
    """Show every command accepted by the simulation."""
    print("\nCommands:")
    print("  status              - Show Earth, Mars, CSV Meridian, and research summary")
    print("  advance             - Advance the simulation by one step")
    print("  research            - Show full Collegium research status (RP, pool, completed)")
    print("  invest <lane> <pos> - Spend a lane's banked RP into its pool position <pos>")
    print("  pilot <lane> <pos>  - Gamble banked RP on an early breakthrough at pool position <pos>")
    print("  help                - Show available commands")
    print("  quit                - Exit the simulation")


def main():
    """Start the terminal command loop.

    `while True` means keep asking for a command until the player uses `quit`.
    `.strip()` removes accidental spaces, and `.lower()` makes commands
    case-insensitive: STATUS, Status, and status all work. `.split()`
    breaks the typed line into words, so commands like `invest` can take
    arguments after the command name itself.
    """
    print("ASTERION FOUNDRY // SOL DIRECTORATE")
    print("Lessons 01-03: Forge Production, Freight Logistics, and Collegium Research")
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
        elif command == "help":
            show_help()
        elif command == "quit":
            print("Simulation terminated.")
            break
        else:
            print("Unknown command. Type 'help' for available commands.")


# Research is built here, after every function above it exists, and
# before the command loop starts.
world["research"] = build_research_state()

# This line runs the `main` function when Python starts this file.
main()
