# Start Here

Welcome to **Asterion Foundry**. This project is deliberately built as a learning tool, not as a pile of code you are expected to understand all at once.

## First-session goal

Run the program, observe the simulation, and understand one complete loop:

```text
Player command → Python function → world data changes → terminal report
```

You are not trying to make a full game today. You are proving that you can run and modify a small simulation.

## Setup

1. Install Python 3 if `python --version` or `py --version` does not work in a terminal.
2. Open this repository folder in VS Code.
3. Install the Microsoft Python extension in VS Code if it is not installed.
4. Open **Terminal → New Terminal**.
5. Run one command:

```text
python src/main.py
```

On some Windows setups, use:

```text
py src/main.py
```

## Commands inside the simulation

```text
help       Show available commands
status     Show Earth and Mars resources
advance    Advance the universe by one simulation step
quit       Exit the program
```

## Read the code in this order

Open `src/main.py` and read these sections from top to bottom:

1. `world` — all currently tracked game information
2. `show_status()` — how the game reports state
3. `update_mars()` — Mars consumes supplies and produces industrial material
4. `advance_world()` — one simulation step
5. `main()` — the command loop that keeps the program running

Do not skip the comments. They are written for the version of you who will come back later.

## First experiments

Perform one experiment, run the program, then observe the result.

1. Change Mars's starting `support_supplies` from `100` to `30`.
2. Change raw-metal output from `15` to `25`.
3. Change refined-metal output from `8` to `12`.
4. Change one alert message to fit the setting tone.
5. Add a new empty location only after you understand the two existing ones.

After each experiment, write a one-sentence result in `LEARNING_NOTES.md`.

## Safe Git habit

Before changing code, make a branch. For a small experiment:

```text
git switch -c experiment/mars-output
```

When it works:

```text
git add src/main.py LEARNING_NOTES.md
git commit -m "Experiment with Mars forge output"
```

If you dislike the experiment, you can return to `main` and delete the branch without harming the stable project.

## What comes next

Lesson 02 adds the **CSV Meridian**, a named freighter. It will load support supplies on Earth, travel to Mars, unload them, then return with Martian industrial output. That turns the current dependency into the first real logistics loop.
