# Shipyard Slot Expansion and No-Idle Rotation

**Status:** Documented and implemented (first version) — `src/shipyard.py`.

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

- No real refined-metal economy hookup — `expand()` takes an
  `available_refined_metal` number as a plain argument rather than reading
  live `world` state from `main.py`.
- No per-slot build-time simulation (a slot "building" a ship over several
  `advance` steps) — this version only decides *what* a slot should build
  next, not how long that build takes.
- No shipyard damage, sabotage, or capacity-loss events.

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
