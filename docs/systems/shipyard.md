# Shipyard Slot Expansion and No-Idle Rotation

**Status:** Documented, implemented, and wired into the game loop — `src/shipyard.py` (data module) plus `src/main.py` (integration).

## Purpose

The original build queue treated the shipyard as a single serial line: one
project at a time, first-in-first-out. That does not scale to an empire
that needs a standing fleet-production capacity. This system turns the
shipyard into a slotted facility that:

1. Grows toward a **target minimum tied to `FLEET_TARGET`**
   (`SHIPYARD_TARGET_MINIMUM = sum(FLEET_TARGET.values())`, currently 16),
   funded gradually from refined-metal surplus rather than built all at
   once. (Bug found and fixed 2026-09-04: this used to be a flat 100,
   chosen before `FLEET_TARGET` existed and never reconciled with it --
   see "Bug: shipyard target_minimum vs. FLEET_TARGET" below.)
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

## Bug: shipyard target_minimum vs. FLEET_TARGET (found and fixed 2026-09-04)

`Shipyard.target_minimum` defaulted to 100 in `src/shipyard.py`, a number
picked when this system was built -- before `FLEET_TARGET` (the 16-hull
fleet cap) existed. Nothing ever reconciled the two. Since this game has no
combat/hull-loss mechanic yet, `in_service` counts only ever grow toward
`FLEET_TARGET` and then sit there permanently, which means every slot
above what's needed to reach `FLEET_TARGET` was mathematically guaranteed
to sit idle forever the moment the cap was hit -- while `update_shipyard()`
kept spending Mars's refined metal expanding toward 100 regardless.

Fixed by introducing `SHIPYARD_TARGET_MINIMUM = sum(FLEET_TARGET.values())`
in `src/main.py` and passing it explicitly to `Shipyard(...)` in
`build_ship_and_facility_state()`, instead of relying on the dataclass's
generic default. `src/shipyard.py` itself is unchanged -- it's a reusable
data module with no knowledge of this game's fleet caps, so the reconciled
value is main.py's responsibility, the same way `warship_minimum`/
`logistics_minimum` already are. If a hull-loss/combat-attrition mechanic
is added later (DESIGN_SPINE.md dev order item 13), this value is worth
revisiting -- standing replacement capacity beyond the initial 16 would
become genuinely useful again.

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

Newly built ships are delivered **idle at Mars**. A new light warship
stays idle there (no automatic patrol/escort assignment exists yet). A new
freighter joins the automatic Earth–Mars supply loop on the very next
`advance` step — `update_freighters()` in `src/main.py` runs every ship
with `class_id == "freighter"`, not just CSV Meridian (bug found and
fixed 2026-09-04; see that function's docstring and the "Bug: freighters
built after CSV Meridian never ran their supply route" note below).

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
- **Change the warship/logistics guarantee floors or the slot target:**
  these are `Shipyard` dataclass fields (`warship_minimum`,
  `logistics_minimum`, `target_minimum`) — pass different values when
  `Shipyard(...)` is constructed in `build_ship_and_facility_state()` in
  `src/main.py`. The slot target is `SHIPYARD_TARGET_MINIMUM` there,
  derived from `FLEET_TARGET` — raise `FLEET_TARGET` (or override
  `SHIPYARD_TARGET_MINIMUM` directly) rather than hardcoding a new number,
  so the two stay reconciled.
- **Change the demand heuristic that drives which category a free slot
  builds:** `update_shipyard()` currently uses a simple 1:1 balance (each
  category's demand is set to the *other* category's current fleet
  count). Replace that calculation with something more detailed (e.g.
  factoring in combat losses or a player-set target ratio) without
  touching `next_build_assignment()` itself, which only ever reads
  whatever `fleet_counts`/`demand_counts` it's given.
- **Change how a new light warship is used:** it's delivered idle at
  Mars and stays that way — no automatic patrol/escort assignment exists
  yet. That's the next customization point in this area, now that
  freighters are handled (see the bug note below).

## Bug: freighters built after CSV Meridian never ran their supply route (found and fixed 2026-09-04)

`update_csv_meridian()` (now `update_freighters()`) was hardcoded to
`world["ships"]["csv_meridian"]` alone. CSV Concord — a second freighter
present since the very start of the game, sitting right next to CSV
Meridian in the starting `world["ships"]` dict — was never touched by it,
and neither was any freighter the shipyard later built: `_complete_ship_build()`
delivers a new freighter "idle_at_mars" with the same
`status`/`cargo_*`/`travel_remaining` shape CSV Meridian and CSV Concord
already use, but nothing ever advanced it out of that idle state. Both
sat there for the life of the game, contributing nothing to the
Earth-Mars supply loop despite being fully-built, in-service hulls.

Fixed by generalizing `update_csv_meridian()` into `update_freighters()`,
which loops over every ship in `world["ships"]` with
`class_id == "freighter"` and runs the same load/travel/unload state
machine for each. `show_status()` had the identical bug (only ever
printed CSV Meridian's line) and is fixed the same way. Regression tests
in `tests/test_main_integration.py` cover CSV Concord and a
freshly-shipyard-built freighter both actually advancing through the
loop.

## Bug: the shipyard could overshoot FLEET_TARGET (found and fixed 2026-09-04)

`update_shipyard()`'s no-idle assignment step seeded `fleet_counts` from
`in_service` counts alone. A build already in flight from a PRIOR step (a
slot with `building_class_id` still set, not yet complete) was invisible
to the `FLEET_TARGET` check — so while one hull of a class was
mid-construction, every OTHER free slot that came open during those same
steps could each start an additional build of that same class, none of
them able to see the others' pending work. Once they all completed, the
fleet ended up over `FLEET_TARGET`, directly contradicting the promise at
that constant's own definition ("the shipyard stops building more of that
class"). Confirmed with a 400-step `advance_world()` run from a fresh,
untouched game: `light_warship` reached 11 in_service against a target of
10.

Fixed by also counting slots already mid-build toward the same cap when
deciding whether a newly-free slot should start another one — a category
at or above `FLEET_TARGET` once existing hulls AND pending construction
are both counted now stops attracting new builds, the same way it already
did for `in_service` alone. Regression tests in
`tests/test_main_integration.py` cover both the direct mechanism (one
slot mid-build, three more free, only one of the three should start a new
build) and the end-to-end symptom (a 400-step run never exceeds
`FLEET_TARGET` for either class).

## Bug: hull numbering reset on every process restart (found and fixed 2026-09-04)

`_hull_counters` (`src/main.py`, near `build_ship_and_facility_state()`)
is a plain module-level global — not part of `world` — so it was silently
excluded from every save and reset to `{"freighter": 1, "light_warship":
0}` on the next process start regardless of what the save file said. The
very next hull the shipyard completed after a save/load/relaunch cycle
would then reuse an already-taken hull id (e.g. `csv_hull_02` again),
silently overwriting that ship's entire entry in `world["ships"]` —
destroying any cargo or travel state it was carrying — and adding a
duplicate name to `ship_classes[...].in_service`, which also threw off
`update_shipyard()`'s fleet-count bookkeeping. This triggers on the
ordinary "save, quit, relaunch, keep playing" cycle as soon as the
shipyard has produced even one hull, not an edge case.

Fixed by adding `hull_counters` to `save_game()`'s `saveable` dict and
restoring it in `load_game()`. A save made before this fix (no
`hull_counters` key at all) is backfilled by scanning `world["ships"]`
for the highest `csv_hull_NN`/`lws_hull_NN` already present, so numbering
still can't collide even on an old save. Regression tests in
`tests/test_main_integration.py::HullCounterSaveLoadIntegrationTests`
cover both the normal round-trip and the pre-fix-save backfill.

## Bug found and fixed 2026-09-05 (stress-test pass): a save missing an entire ship-class category crashed the next `advance`/`council`

Unlike every other historical field `_apply_loaded_save()` restores
(colonies, hull counters, `audit_system`, penal records...), the
`ship_classes` reconstruction never backfilled a missing category. A save
whose `ship_classes` object was missing `"light_warship"` or `"freighter"`
entirely (a hand edit, a truncated write, a future class rename) loaded
with a silent "full state restored" message, then crashed the very next
`advance` or `council` command with an uncaught `KeyError` --
`update_shipyard()` and `show_council()` both do a hardcoded
`world["ship_classes"]["light_warship"/"freighter"]` lookup with no
`.get()` guard. Fixed by backfilling any missing category with a fresh,
empty-roster `ShipClass` (no invented phantom ships -- it can't
retroactively recover ships that may have genuinely been lost, but it also
can't make things worse than the crash it replaces). Regression test:
`tests/test_main_integration.py::ShipClassBackfillIntegrationTests`.

## Known, accepted limitation (flagged 2026-09-05, not fixed): a corrupted save's slot/fleet mismatch isn't re-validated on load

The stress-test pass that found the bug just above also surfaced a related,
lower-severity gap: `_apply_loaded_save()` restores `world["shipyard_slots"]`
and `world["ship_classes"]` independently, with no cross-check between them.
A save that's already internally inconsistent -- for example,
`shipyard_slots` containing more in-flight `building_class_id` entries for a
category than `FLEET_TARGET` allows, because it was hand-edited or written
by some future buggy version -- loads without complaint, and
`update_shipyard()`'s no-idle assignment step (see "Bug: the shipyard could
overshoot FLEET_TARGET" above) only ever stops a category from **starting**
a *new* build once it's at cap; it doesn't retroactively cancel or repair
slots that were already over cap when the save was loaded. This does not
crash anything -- every field involved is still present and correctly
typed, so no `KeyError`/`AttributeError` follows the way the missing-category
bug above did -- it just means an already-corrupted save can stay
mechanically over `FLEET_TARGET` indefinitely instead of self-correcting.

Deliberately left unfixed for now: reaching this state requires a save
that's already inconsistent by construction (not producible by normal
play, and not producible by anything else this stress-test pass found), so
it's a smaller, harder-to-justify chunk of new validation logic than the
crash-on-load bugs this pass prioritized fixing. Worth a real look if
save-file corruption/hand-editing becomes a more central concern later, or
naturally as part of any future combat/hull-loss pass that will need to
touch this same fleet-counting logic anyway.
