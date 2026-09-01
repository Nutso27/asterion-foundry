# Lab Specialization — Fixed Programs vs. Flexible Research

**Status:** Documented, implemented, and wired into the game loop — `src/research/lab_specialization.py` (data module) plus `src/main.py` (integration).

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

- No scientist staffing model for the fixed-role labs — they are assumed to
  run with a caretaker crew, not the individually-tracked `Scientist`
  objects used for Lab #1's flexible pool.

## Integration into the game loop

- `build_lab` **command** → `handle_build_lab()` in `src/main.py`: spends
  `LAB_BUILD_COST` refined metal at Mars, creates a new `Lab` object,
  computes its role with `default_lab_role(lab_number)` (the exact tested
  function from `src/research/lab_specialization.py`), and registers it
  in both `world["research"].labs` and `world["lab_roles"]`.
- **Perpetual ticking**: `update_lab_specialization()` runs from
  `advance_world()` every `advance` step, but only actually ticks every
  `LAB_TICK_INTERVAL_STEPS` steps (`world["time"] % LAB_TICK_INTERVAL_STEPS == 0`).
  On a tick, every lab in `world["lab_roles"]` whose role is a fixed
  perpetual program calls `apply_perpetual_tick()` — the exact tested
  function — on the matching entry in `world["multipliers"]`.
- **What the multipliers actually do**, wired into the other systems:
  - `construction_time_multiplier` scales `BASE_BUILD_TIME_STEPS` inside
    `update_shipyard()` (see `docs/systems/shipyard.md`) — lower means
    faster hulls.
  - `research_time_multiplier` is used as the effective `dt` passed to
    `generate_rp()` inside `update_research()` — lower means faster RP
    accumulation.
  - `universal_efficiency_multiplier` scales the 10-support-supply cost
    inside `update_mars()` — lower means Mars's forge complex is cheaper
    to run (down to a floor of 5 supplies/step, since the multiplier's
    own floor is 0.5).

## Where this lives in the code

| What | Where |
|---|---|
| Each lab's permanent role | `world["lab_roles"]` in `src/main.py` (a dict of `lab_id -> role string`) |
| The three running multipliers | `world["multipliers"]` in `src/main.py` |
| Building a new lab | `build_lab` command → `handle_build_lab()` in `src/main.py` |
| The per-interval tick logic | `update_lab_specialization()` in `src/main.py`, called from `advance_world()` |
| Viewing labs, roles, and multipliers | `labs` command → `show_labs()` in `src/main.py` |

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
standing background-improvement systems — its `construction_time_multiplier`
feeds `docs/systems/shipyard.md` directly.

## How to customize

- **Change how much refined metal a new lab costs:** edit
  `LAB_BUILD_COST` in `src/main.py`.
- **Change how often perpetual programs tick, or by how much:** edit
  `LAB_TICK_INTERVAL_STEPS` (steps between ticks) and
  `LAB_TICK_MAGNITUDE` (how much a multiplier moves per tick) in
  `src/main.py`.
- **Change the hard floor every multiplier is capped at:** edit
  `LAB_TICK_FLOOR` in `src/main.py`. Note this floor applies to all three
  multipliers uniformly; give a system its own floor by adding a second
  constant and passing it explicitly in `update_lab_specialization()`.
- **Change which lab number gets which fixed role:** edit
  `_FIXED_ROLE_BY_LAB_NUMBER` in `src/research/lab_specialization.py`
  itself (the tested data module, not `main.py`).
