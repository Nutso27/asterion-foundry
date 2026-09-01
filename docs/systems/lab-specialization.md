# Lab Specialization — Fixed Programs vs. Flexible Research

**Status:** Documented and implemented (first version) — `src/research/lab_specialization.py`.

## Purpose

As the Asterion Collegium grows past its first lab, not every new lab
should behave the same way. Lab specialization gives each lab a
permanent role assigned at construction time, so growth has a clear rule
instead of every lab quietly doing the same generic thing:

- **Lab #1 stays flexible.** It auto-restaffs from whatever is in
  `research.topics` and is the only lab that ever joins the game's
  general flexible research pool (see `docs/systems/research.md`).
- **Every lab from #2 onward is fixed to one perpetual program for its
  entire existence.** It never joins the flexible pool. It just quietly
  ticks its one program, forever, in the background.

## Smallest possible first version (already implemented)

Fixed role assignment by construction order, matching the CYOA precedent:

| Lab # | Role |
|---|---|
| 1 | `flexible_auto_research` — pulls from `research.topics`, priority: military & defense > materials/industry/logistics > habitat/life support/other > xenology (only with evidence) |
| 2 | `perpetual_construction_optimization` |
| 3 | `perpetual_research_methodology` |
| 4+ | `perpetual_universal_improvement` (the default role for every lab beyond #3) |

`default_lab_role(lab_number)` returns the correct role for any lab number
using this table, so lab #8, #20, etc. all resolve to
`perpetual_universal_improvement` without new code.

`apply_perpetual_tick(multiplier, magnitude_per_tick, floor)` advances one
of the three running multipliers (`construction_time_multiplier`,
`research_time_multiplier`, `universal_efficiency_multiplier`) by one tick,
never crossing the given floor — so "perpetual improvement forever" still
has a hard, sane limit rather than approaching zero or infinity.

## What this version explicitly does not include yet

- No lab construction cost/queue integration with `src/shipyard.py` or a
  matching "build a lab" flow in `main.py`.
- No scientist staffing model for the fixed-role labs — they are assumed to
  run with a caretaker crew, not the individually-tracked `Scientist`
  objects used for Lab #1's flexible pool.
- No UI/report line yet showing all seven-plus labs and their roles at once.

## Success condition

- `default_lab_role(1)` returns `flexible_auto_research`.
- `default_lab_role(2)` and `default_lab_role(3)` return their distinct
  fixed programs.
- `default_lab_role(n)` for any `n >= 4` returns
  `perpetual_universal_improvement`.
- `apply_perpetual_tick()` moves a multiplier toward its target and stops
  exactly at the floor instead of overshooting it.

## Dependencies

Builds on the existing research system (`src/research/`, see
`docs/systems/research.md`). Does not require the shipyard or ship-design
systems, but conceptually sits alongside them as one of the Directorate's
standing background-improvement systems.
