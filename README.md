# Asterion Foundry

> A learning-first, pausable real-time space-empire simulation about manufacturing humanity's first stellar civilization.

## What this project is

**Asterion Foundry** is a private learning project. You command a severe industrial government centered on Earth and Mars. Mars is humanity's first forge world: it transforms resources, knowledge, labor, and time into ships, infrastructure, and the foundations of new colonies.

This is not a story about recovering forgotten human colonies. The player builds the colonies, routes, fleets, worlds, and megastructures that become the empire.

The initial prototype is a small Python terminal simulation. It is intentionally simple so every major part can be read, changed, tested, and understood. Later versions may add a pausable real-time loop, a 2D strategic interface, tactical combat, and deeper systems.

## Core design pillars

- **Mars is the first forge world.** Earth provides command, population support, and essential supplies; Mars is the main heavy-industrial and research center.
- **Industry enables war.** Ships and military power come from mines, refineries, factories, shipyards, fuel, workers, and logistics.
- **Important goods move physically.** Freighters, tankers, convoys, and later nomadic fleets transport strategic cargo.
- **Individual ships matter operationally.** They have names, roles, locations, fuel, cargo, condition, and orders.
- **Time is continuous but controllable.** Development starts with manual simulation steps, then becomes pausable real time.
- **The player chooses command depth.** Direct orders and readable automation can coexist.
- **Scale is earned.** Hive worlds, nomadic fleets, Dyson swarms, and Dyson spheres require immense, long-term industrial effort.
- **Loss still creates opportunity.** Wrecks can be salvaged for material, components, data, and research leads.

## Current playable lesson

`src/main.py` now contains Lessons 01 through 03: a two-world industrial simulation, freight logistics, and Collegium research.

- Earth begins with essential support supplies.
- Mars consumes support supplies to operate its forge complexes, and produces raw metal and refines a portion into refined metal.
- The freighter **CSV Meridian** automatically ferries support supplies from Earth to Mars, and refined metal back from Mars to Earth, so Mars no longer stalls on its own.
- The **Asterion Collegium** runs a small research lab on Mars. Research points accumulate automatically each step; spending them on a technology, or gambling on an early breakthrough with a pilot project, is a deliberate player choice (see `docs/systems/research.md`).
- The player types commands such as `status`, `advance`, `research`, `invest <lane> <pos>`, `pilot <lane> <pos>`, `help`, and `quit`.

## Run the project

### Requirements

- Python 3 installed on Windows
- VS Code with the Microsoft Python extension recommended

### Commands

Open the project folder in VS Code. Then open **Terminal → New Terminal** and run:

```text
python src/main.py
```

If Windows does not recognize `python`, try:

```text
py src/main.py
```

Inside the program, try:

```text
help
status
advance
status
quit
```

## Read it in this order

1. Read `docs/START_HERE.md`.
2. Run `src/main.py` without changing anything.
3. Read the code from top to bottom and connect each function to what you saw in the terminal.
4. Change one number, run it again, and observe the result.
5. Write what you learned in `LEARNING_NOTES.md`.
6. Commit your own working experiment.

## Project map

```text
asterion-foundry/
├── README.md                 # Start here for the project overview
├── DESIGN_SPINE.md           # Long-term design decisions and boundaries
├── LEARNING_NOTES.md         # Your personal explanations and discoveries
├── docs/
│   ├── START_HERE.md         # First-session guide
│   └── systems/              # Design notes for game systems
├── src/
│   ├── main.py               # Lessons 01-03 runnable simulation (forge, freight, research)
│   └── research/             # Asterion Collegium research engine, data, and demo
└── .gitignore                # Files Git should not track
```

## Safe development workflow

`main` should always be the last stable, runnable version.

Build one small feature per branch:

```text
feature/csv-meridian-freighter
feature/mars-forge-production
feature/red-archive-research
feature/wreck-field-salvage
feature/first-colony
feature/nomadic-fleet
feature/hive-city
feature/dyson-swarm
```

For each feature:

1. Write or update a short design note.
2. State one testable goal.
3. Create a branch.
4. Change the smallest amount of code that can meet that goal.
5. Run the game and test deliberate failure cases.
6. Commit with a clear message.
7. Merge only when the branch works and you can explain it.

## Immediate milestones

1. Run the manual Sol–Mars industrial simulation. — done
2. Understand dictionaries, functions, conditions, and the command loop. — done
3. Add the **CSV Meridian** freighter. — done
4. Make it load support supplies on Earth, travel, and unload them at Mars. — done
5. Return Martian industrial output to Earth orbit. — done
6. Add basic research from the Mars-based technical institution. — done
7. Convert manual steps into pausable real time. — next

## Long-term systems

The project deliberately documents large ambitions before implementing them:

- Colony creation and world specialization
- Forge worlds, hive cities, and hive worlds
- Research, prototypes, and technology recovery
- Individual fleets, logistics, and supply depots
- Salvage operations and wreck fields
- Nomadic industrial and expedition fleets
- Abstract strategic combat, followed later by tactical battle command
- Dyson swarms and eventual Dyson-scale megastructures

An idea belongs in documentation or a GitHub issue until its required smaller systems exist.

## Naming and release note

Asterion Foundry is a working title. The setting may be inspired by dark military-industrial space opera, but it must remain original for any public release: do not use Warhammer names, factions, lore, quotations, artwork, or assets.
