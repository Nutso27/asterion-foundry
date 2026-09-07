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

## Bugs found and fixed 2026-09-04 (stabilization pass)

Two real bugs in the self-renewing MK progression loop, both confirmed
with concrete repros, both closed with regression tests:

- **The freshly-registered successor node could be silently dropped the
  instant it appeared.** `_register_next_mk_node()` appends the new node
  (e.g. `freighter_mark_iii`) into its lane's `active_pool`, but
  `handle_invest()`/`handle_pilot()` immediately call
  `refresh_draw_pool()` right after (to see what else completing this
  node opened up) — and that function used to do a full weighted re-draw
  with no special treatment for a node that had just been added with 0 RP
  invested. It competed on equal footing with every other eligible
  candidate for a (usually 3-slot) pool and could lose, despite the
  player having just been told "New research now available." Confirmed
  at roughly 1 in 6 trials. Fixed by adding a `guaranteed_ids` parameter
  to `refresh_draw_pool()` (`src/research/engine.py`) — protected the
  same way an already-in-progress node already was — and having
  `_apply_ship_design_effect()` return the new node's id so
  `handle_invest()`/`handle_pilot()` can pass it through.
- **A dynamically-registered node didn't survive save/load, crashing
  `research`/`invest`/`pilot` on the very next launch.** `save_game()`
  only ever persisted the base technology set's mutable state
  (`active_pool`, `completed`, `rp_invested`) — never the node
  *definitions* themselves. A runtime-registered node like
  `freighter_mark_iii` exists only in `state.nodes` in memory; on
  `load_game()`, `state.nodes` gets rebuilt fresh from
  `technologies.json` alone (which never had it), while `active_pool`
  still names it — the next lookup on that id raised `KeyError`. This is
  an ordinary sequence (complete an MK node, save, reload), not an edge
  case. Fixed by saving every `state.nodes` entry not present in
  `technologies.json` under a new `dynamic_nodes` key and restoring them
  before `active_pool`/`completed` are applied on load; see
  `docs/systems/shipyard.md`'s save/load bug note for the sibling fix
  this shares its "reconstruct everything into locals before touching
  `world`" pattern with.

## Bug found and fixed 2026-09-05 (stress-test pass): a dynamic node's protection only covered its own registration, not later refreshes

The 2026-09-04 fix (above) added `guaranteed_ids` to `refresh_draw_pool()`,
but `handle_invest()`/`handle_pilot()` only ever passed the ID of the node
just registered **this call** -- protecting it against exactly one
refresh. Any *later*, unrelated completion in the same lane called
`refresh_draw_pool()` with no `guaranteed_ids` for it at all, so a
still-uninvested dynamic node from an earlier completion competed on equal
footing with every other eligible candidate and could be silently evicted.
Confirmed at ~16% (49/300 trials) for a completely ordinary sequence:
complete an MK node, then complete two unrelated same-lane techs before
ever touching the new one. The node wasn't lost forever (a later refresh
could re-draw it), but it vanished from `research`/`invest`/`pilot` for an
indeterminate stretch -- directly contradicting the "New research now
available" message printed at registration.

Fixed by `_guaranteed_dynamic_node_ids()` in `src/main.py`, which
recomputes the full set of live dynamic node ids in a lane (anything in
`active_pool` not present in the base `technologies.json` set) on **every**
`refresh_draw_pool()` call from `handle_invest()`/`handle_pilot()`, not
just the one right after registration -- so a dynamic node stays protected
for its entire uninvested lifetime. Regression test:
`tests/test_main_integration.py::DynamicNodePersistentGuaranteeIntegrationTests`.

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
