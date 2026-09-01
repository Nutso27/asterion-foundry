# Shipyard Slot Expansion and No-Idle Rotation

**Status:** Documented, implemented, and wired into the game loop — `src/shipyard.py` (data module) plus `src/main.py` (integration).

## Purpose

The original build queue treated the shipyard as a single serial line: one
project at a time, first-in-first-out. That does not scale to an empire
that needs a standing fleet-production capacity. This system turns the
shipyard into a slotted facility that:

1. Grows toward a **target minimum of 100 slots**, funded gradually from
   refined-metal surplus rather than built all at once.
2. Permanently guarantees a floor of **5 warship slots** and **5 logistics
   slots** at all times, once that many slots exist.
3. Keeps every slot working. No slot should ever sit idle — this system's
   rotation policy is the "no slot left behind" rule.

## Smallest possible first version (already implemented)

- `Shipyard` holds `slots_total`, `target_minimum`, `warship_minimum`,
  `warship_locked`, `logistics_minimum`, `logistics_locked`, and
  `flexible` (slots not locked to either category).
- `expand()` adds slots in fixed batches (default batch size 3, matching
  the CYOA order), spending refined metal per slot. New slots fill the
  warship guarantee first, then the logistics guarantee, and only then
  add to the flexible pool. Expansion stops once `target_minimum` is
  reached — it never overshoots.
- `next_build_assignment()` implements the no-idle rotation rule for one
  free slot: given how many of each type are already in production versus
  in the fleet, it picks whichever category (within the slot's allowed
  categories) currently has the smallest fleet count relative to demand.
  If one type is already in clear surplus, the function actively steers
  away from it toward the type that is falling behind.

## What this version explicitly does not include yet

- No shipyard damage, sabotage, or capacity-loss events.
- Slot expansion is triggered on the *no-idle* rule, which happens to run
  every `advance` step — there is no separate expansion cadence yet.

## Integration into the game loop

`update_shipyard()` in `src/main.py` runs every `advance` step, in three
parts, in this order:

1. **Expand.** If Mars's `refined_metal` is above `SHIPYARD_METAL_RESERVE`
   and the yard hasn't hit `target_minimum`, it calls the exact tested
   `expand()` function from `src/shipyard.py`, spends the metal it
   reports, and appends one new dict to `world["shipyard_slots"]` per
   slot added — with `locked_category` set to match whichever guarantee
   (`warship_locked`/`logistics_locked`/`flexible`) `expand()` just grew.
2. **Advance builds.** Every slot with a build in progress
   (`building_class_id` set) has its `steps_remaining` counter decremented.
   Hitting zero calls `_complete_ship_build()`, which creates a real new
   entry in `world["ships"]` and appends its name to the matching
   `world["ship_classes"][class_id].in_service` list, then frees the slot.
3. **No-idle assignment.** Every slot with no build in progress (just
   freed, or new from step 1) is immediately assigned a build by calling
   the exact tested `next_build_assignment()` from `src/shipyard.py`,
   using current in-service counts as `fleet_counts` and the *other*
   category's count as a simple 1:1 `demand_counts` heuristic. Build time
   comes from `BASE_BUILD_TIME_STEPS`, scaled by the lab-specialization
   `construction_time_multiplier` (see `docs/systems/lab-specialization.md`).

Newly built ships are delivered **idle at Mars**, not automatically
routed anywhere — see `update_csv_meridian()`'s docstring in `src/main.py`
for the customization point that would change that.

## Where this lives in the code

| What | Where |
|---|---|
| The `Shipyard` object (slot counts, guarantees) | `world["shipyard"]` in `src/main.py` |
| Per-slot build state (`locked_category`, `building_class_id`, `steps_remaining`) | `world["shipyard_slots"]` (a list of dicts, one per physical slot) |
| The per-step expand/advance/assign logic | `update_shipyard()` in `src/main.py`, called from `advance_world()` |
| Spawning a completed hull into the fleet | `_complete_ship_build()` in `src/main.py` |
| Viewing slots, guarantees, and the build queue | `shipyard` command → `show_shipyard()` in `src/main.py` |

## Success condition

- Calling `expand()` repeatedly never produces more than `target_minimum`
  total slots.
- The warship and logistics guarantees are always filled before any slot
  becomes flexible.
- `next_build_assignment()` never recommends building more of a type that
  is already flagged as surplus while a needed type is starving.

## Dependencies

Feeds from the Directorate's general refined-metal economy (`main.py`
`world["locations"]["mars"]["refined_metal"]`) and produces work items for
`docs/systems/ship-design.md`'s MK/class registry — a slot needs to know
current ship classes and their MKs to decide what "build the freighter"
actually means today.

## How to customize

- **Grow the shipyard faster or slower:** lower/raise `SLOT_EXPAND_COST`
  (metal per slot) or raise/lower `SHIPYARD_EXPAND_BATCH_SIZE` (slots per
  expansion) in `src/main.py`. Raise `SHIPYARD_METAL_RESERVE` to make the
  Directorate hoard more metal before spending any on new slots.
- **Change how long a hull takes to build:** edit
  `BASE_BUILD_TIME_STEPS = {"freighter": 4, "light_warship": 6}` in
  `src/main.py`. This is in `advance` steps, before the construction-time
  multiplier is applied.
- **Change the warship/logistics guarantee floors or the 100-slot
  target:** these are `Shipyard` dataclass fields
  (`warship_minimum`, `logistics_minimum`, `target_minimum`) — pass
  different values when `Shipyard(...)` is constructed in
  `build_ship_and_facility_state()` in `src/main.py`.
- **Change the demand heuristic that drives which category a free slot
  builds:** `update_shipyard()` currently uses a simple 1:1 balance (each
  category's demand is set to the *other* category's current fleet
  count). Replace that calculation with something more detailed (e.g.
  factoring in combat losses or a player-set target ratio) without
  touching `next_build_assignment()` itself, which only ever reads
  whatever `fleet_counts`/`demand_counts` it's given.
- **Wire built freighters into the automatic supply loop:** see the
  customization note in `update_csv_meridian()`'s docstring in
  `src/main.py`.
