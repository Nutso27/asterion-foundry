# Ship Design — MK Progression and Retirement

**Status:** Documented and implemented (first version) — `src/ship_design.py`.

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

- No stat blocks (weapon values, armor values, cargo numbers) — MK
  improvements are represented as a generation label and an `effect`
  description string, not simulated numbers yet.
- No automatic refit of existing hulls to a new MK.
- No shipyard build-time integration — `docs/systems/shipyard.md`'s
  `next_build_assignment()` decides *that* a slot should build a given
  class; this module decides *which MK* that class currently means.

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
