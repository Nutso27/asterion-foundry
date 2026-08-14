"""Asterion Foundry — Lesson 01: Two-world industrial simulation.

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
- There is no freighter yet, so Mars eventually stalls.
- Lesson 02 will add the CSV Meridian and cargo movement.
"""

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
}


def show_status():
    """Print the resource stockpiles for every current location."""
    print(f"\n=== ASTERION FOUNDRY // SIMULATION STEP {world['time']} ===")

    # `.values()` gives us each location dictionary stored in `locations`.
    for location in world["locations"].values():
        print(
            f"{location['name']}: "
            f"Support supplies {location['support_supplies']} | "
            f"Raw metal {location['raw_metal']} | "
            f"Refined metal {location['refined_metal']}"
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

    Earth has no production rule in Lesson 01. This function exists to show
    that every location can have its own update rules as the project grows.
    """
    earth = world["locations"]["earth"]
    _ = earth
    print("Earth command reports stable reserves. No new production this step.")


def advance_world():
    """Advance the entire simulation by one discrete step.

    Later this same kind of update will run automatically in a pausable
    real-time loop. Manual steps are easier to inspect while learning.
    """
    world["time"] += 1
    print(f"\n--- Advancing simulation to step {world['time']} ---")

    update_earth()
    update_mars()


def show_help():
    """Show every command accepted by the first lesson."""
    print("\nCommands:")
    print("  status  - Show Earth and Mars resource stockpiles")
    print("  advance - Advance the simulation by one step")
    print("  help    - Show available commands")
    print("  quit    - Exit the simulation")


def main():
    """Start the terminal command loop.

    `while True` means keep asking for a command until the player uses `quit`.
    `.strip()` removes accidental spaces, and `.lower()` makes commands
    case-insensitive: STATUS, Status, and status all work.
    """
    print("ASTERION FOUNDRY // SOL DIRECTORATE")
    print("Lesson 01: Earth Support and Mars Forge Production")
    show_help()

    while True:
        command = input("\nCommand > ").strip().lower()

        if command == "status":
            show_status()
        elif command == "advance":
            advance_world()
        elif command == "help":
            show_help()
        elif command == "quit":
            print("Simulation terminated.")
            break
        else:
            print("Unknown command. Type 'help' for available commands.")


# This line runs the `main` function when Python starts this file.
main()
