# Ship Design — MK Progression and Retirement

**Status:** Documented, implemented, and wired into the game loop — `src/ship_design.py` (data module) plus `src/main.py` (integration).

## Purpose

Ships should not be permanently frozen at their launch specification. This
system gives every ship class a generation number (its "MK") that can be
improved through research, and a clean rule for what happens to
production — and to already-built hulls — when a better MK becomes
available.

## Smallest possible first version (already implemented)

- `ShipClass` tracks `id`, `category` (`"warship"` or `"logistics"` only —
  no other categories are allowed in this version), `current_mk`,
  `in_service` (ship names currently using this class), and
  `retired_from_production` (bool).
- `complete_mk_research()` takes a `ShipClass` and a completed MK research
  project: it immediately switches the class's `current_mk` to the new
  generation, marks the record of the *previous* generation's production
  line as `retired_from_production = True`, and — because this line of
  research is meant to be self-renewing — returns a stub for the *next*
  generation's research project so Lab #1's queue is never empty for a
  class that still has room to improve.
- Existing hulls are never touched by this function. `in_service` stays
  exactly as it was — retiring a MK from *production* is not the same as
  retiring or scrapping a *ship*, and this system never does the latter on
  its own.
- `propose_new_hull_class()` is a deliberately narrow gap-finder: given the
  current roster, it only ever proposes a new class inside the existing
  `"warship"` or `"logistics"` categories, and only when there is a real
  mechanical gap (e.g., no escort-sized warship exists yet). It will not
  invent a new category or a flavor-only ship.

## What this version explicitly does not include yet

- No automatic refit of existing hulls to a new MK — completing a MK
  research project only changes the stats used for *future* hulls the
  shipyard builds; `in_service` ships keep the stats and `mk` label they
  were built with.
- No stat blocks beyond a single number per class (`cargo_capacity` for
  freighters, `combat_rating` for light warships) — see "How to
  customize" below for where to add more.

## Integration into the game loop

As of this integration, two research nodes make ship design a real,
playable loop instead of a standalone module:

- `li_freighter_mk2_hull_design` (lane `logistics_and_industry`)
- `md_light_warship_mk2_hull_design` (lane `military_doctrine`)

Both live in `src/research/data/technologies.json`. Investing (`invest`)
or successfully piloting (`pilot`) either one calls
`_apply_ship_design_effect()` in `src/main.py`, which:

1. Builds a `MkResearchProject` from the node's `effect` dict
   (`ship_design_mk_upgrade`: which class, `to_mk`: the new generation).
2. Calls `complete_mk_research()` — the exact same tested function from
   `src/ship_design.py`, untouched by this integration.
3. Reads the returned *next* `MkResearchProject` stub and calls
   `_register_next_mk_node()`, which builds a brand-new `TechNode` and
   inserts it directly into `world["research"].nodes` and that lane's
   `active_pool` — this is what makes the chain self-renewing all the way
   to Mark V without ever touching the JSON data file again.
4. Applies the node's stat-multiplier key (see below) to
   `world["ship_class_stats"]`, which is what the shipyard (see
   `docs/systems/shipyard.md`) reads when it builds the *next* hull of
   that class.

## Where this lives in the code

| What | Where |
|---|---|
| Ship class objects (`ShipClass`, `current_mk`, `in_service`) | `world["ship_classes"]` in `src/main.py`, built by `build_ship_and_facility_state()` |
| Per-hull stats used for the *next* built ship of a class | `world["ship_class_stats"]` — e.g. `world["ship_class_stats"]["freighter"]["cargo_capacity"]` |
| MK2 research node definitions | `src/research/data/technologies.json` — `li_freighter_mk2_hull_design`, `md_light_warship_mk2_hull_design` |
| MK3+ node auto-generation | `_register_next_mk_node()` in `src/main.py` |
| Applying a completed node's effect | `_apply_ship_design_effect()` in `src/main.py` — called from both `handle_invest()` and `handle_pilot()` |
| Viewing current MK + stats + roster | `fleet` command → `show_fleet()` in `src/main.py` |

## How to customize

- **Change how much a MK bump improves stats:** edit the multiplier value
  in the node's `effect` dict in `technologies.json` (e.g. change
  `"freighter_cargo_capacity_multiplier": 1.25` to a different number).
  For MK3 and beyond, the multiplier is set in `_register_next_mk_node()`
  in `src/main.py` (currently a flat `1.15` for every successor node) —
  change that literal, or replace it with a lane/tier-based formula.
- **Add a new tracked stat** (e.g. `hull_rating`, `weapon_rating`): add
  the key to the class's dict in `world["ship_class_stats"]` inside
  `build_ship_and_facility_state()`, then add a matching `elif` branch in
  `_apply_ship_design_effect()` that recognizes a new effect key
  (e.g. `"{class_id}_hull_rating_multiplier"`) the same way the existing
  cargo/combat branches do.
- **Add a third ship class** (e.g. a dedicated escort or colony-hauler):
  add an entry to `world["ship_classes"]` and `world["ship_class_stats"]`
  in `build_ship_and_facility_state()`, add its base build time to
  `BASE_BUILD_TIME_STEPS` and its category mapping to `CATEGORY_TO_CLASS`
  (both in `src/main.py`), and write its own MK2 `TechNode` in
  `technologies.json` following the same `ship_design_mk_upgrade`/`to_mk`
  effect-key pattern.
- **Change the MK cap:** edit `MK_SEQUENCE` in `src/ship_design.py`
  itself (currently Mark I–V) — every downstream function (including
  `_register_next_mk_node()`) reads the cap from there, nothing else
  needs to change.
- **Make MK research require RP investment from a scientist**, not just
  whatever's banked: this already works exactly like every other
  research node — the gate is entirely in `src/research/engine.py`, not
  in this system.

## Success condition

- Completing a MK2 research project updates `current_mk` and flags the
  MK1 production line as retired, without altering `in_service`.
- The function returns a stub for the class's next research project
  automatically (the self-renewing property).
- `propose_new_hull_class()` never returns a suggestion outside
  `"warship"`/`"logistics"`.

## Dependencies

Consumes completed research from the Asterion Collegium (see
`docs/systems/research.md` and `docs/systems/lab-specialization.md` for
how Lab #1's ship-design queue gets staffed) and feeds
`docs/systems/shipyard.md`'s slot-rotation decisions.
