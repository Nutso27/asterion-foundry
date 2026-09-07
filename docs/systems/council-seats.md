# Council-Seat Wiring — First Minister, Marshal-General, First Steward of Continuance

**Status:** Implemented and wired into `src/main.py`'s `council`/`colonies`/`advance` command loop.
**Code:** `src/main.py` (`SPECIALIZATION_EFFECTS`, `handle_survey`, `update_colonies`, `show_council`, `show_colonies`, `_apply_loaded_save`)
**Tests:** `tests/test_main_integration.py::CouncilSeatWiringIntegrationTests`, `ColonySupportSustainabilityIntegrationTests`

## Bug found and fixed 2026-09-05 (stress-test pass): every non-agri_world colony permanently stalled at cycle 10, making garrison_rating and Continuance Hall unreachable

A full-game stress-test pass (2000-step runs, every specialization, requested explicitly to find bugs before building further) found that `update_colonies()` charged `COLONY_SUPPORT_CONSUMPTION` (5.0/cycle) against an **established** colony's support supplies forever, with only `agri_world`'s `support_supplies_per_cycle` effect ever offsetting it -- no colony-resupply mechanic exists anywhere in the game (unlike Earth->Mars, which has freighters, or colony->Mars, which has tithe convoys). With the shipped constants, `OUTPOST_SUPPORT_SEED` (50.0) lasts exactly 10 cycles at that consumption rate. The result: **every one of the 7 non-agri_world specializations permanently stalled at cycle 10**, printing "Growth and output stalled" forever after -- the default outcome of ordinary play, not an edge case.

This directly broke both mechanics documented above in this file: a stalled `fortress_world`'s `garrison_rating` froze permanently at 4 cycles' worth (well short of being a genuine "accumulating stat"), and a stalled `civilian_world`'s population growth froze at 140 -- one growth-step short of `CONTINUANCE_HALL_POPULATION_THRESHOLD` (150) -- making the Continuance Hall milestone **completely unreachable** under default tuning. It also cascaded into the Tithe System: a permanently-stalled `mining_world`/`forge_world` colony can never again pay a tithe, so `_escalate_tithe_shortfall()` kept re-filing charges against it forever (194 duplicate "hoarding_of_strategic_supply" charges against two colonies in one 2000-step stress run).

Fixed by treating support supplies as funding only the fragile pre-established "outpost" phase -- consistent with `OUTPOST_SUPPORT_SEED`'s own existing comment ("the expedition's starting stock") -- rather than an indefinite external dependency an established colony has no way to ever resolve on its own. Once "established," a colony's specialization effects (raw metal, refined metal, population, RP, garrison rating) are its self-sufficiency; nothing else in this codebase bills an established colony for anything ongoing. See `update_colonies()`'s docstring in `src/main.py` for the full before/after reasoning. A defensive dedup guard was also added to `_escalate_tithe_shortfall()` (see `docs/systems/tithe-system.md`) so a persistently-delinquent administrator can't accumulate duplicate active charges regardless.

## Purpose

Before this pass, `world["council"]`'s ten seats had six wired to live data
in `show_council()`'s `live_status` dict (`grand_admiral`,
`quartermaster_general`, `forge_marshal`, `high_savant`, `provost_general`,
`chancellor_general`), plus a seventh — Colonial Warden — wired a different
way, through the dedicated `colonies` command rather than a `live_status`
line. Three seats had neither: **First Minister**, **Marshal-General**, and
**First Steward of Continuance** — tracked in `lore/gaps.md`'s "Lore ahead
of code" section as the three still-open seats. This pass closes all
three, the same way Chancellor-General was closed by the Tithe System: by
finding (or, where none existed, adding) real mechanical data each seat's
own domain already implies, and reporting it live.

## Why these three, and why now

The user's own answer when this "improve all systems" pass started named
colonies/specializations directly ("I want to eventually add more to the
planets and specializations etc") and flagged Council/Penal Code politics
as a priority alongside it. Two of this codebase's three flavor-only
specializations — `fortress_world` and (partially) `civilian_world` — sit
exactly at the intersection of those two things: they exist as options but
produce nothing, and their natural mechanical home is a Council seat that
was sitting empty. Wiring the seat and giving the specialization a real
effect turned out to be the same piece of work for both.

## First Minister (Branch E — civil government, population, food & life support, policy)

Lowest-risk of the three: no new mechanic, just a real aggregate over data
`world["colonies"]` and `world["locations"]["earth"]` already track.

`show_council()`'s `first_minister` entry reports total population across
every **established** colony (a colony still `"surveyed"` or `"outpost"`
doesn't count — it isn't part of the civil population yet) and Earth's
current support-supplies reserve, which is the closest thing this codebase
has to "food & life support" data. No new state, no new constant.

## Marshal-General (Branch G — the Legions, ground forces) and `fortress_world`

`fortress_world` was pure flavor — `SPECIALIZATION_EFFECTS["fortress_world"]
== {}` — because no combat/defense mechanic existed to give it a number.
Real combat is still out of scope (`DESIGN_SPINE.md` dev order item 13),
but per `Downloads\The Directorate\Asterion Foundry — Command & Rank
Structure.md`, Marshal-General's actual mandate is ground-defense
*bookkeeping*, not combat resolution: "stress-testing Mars's untested
perimeter defense grid," a "Legion Readiness Report" tracking "guard,
drill, garrison, and defense-grid readiness." That's a real stat this
codebase can track without inventing combat.

- `FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE` (currently 4, tunable) is a
  new per-cycle effect for `fortress_world` colonies, applied in
  `update_colonies()` the same way every other specialization's effect is
  — added into the colony's new `garrison_rating` field.
- `show_council()`'s `marshal_general` entry reports how many
  `fortress_world` colonies exist and their combined `garrison_rating`.
- `show_colonies()` prints a colony's `garrison_rating` whenever it's above
  zero.

This is explicitly **fleet/combat groundwork**, not a combat system: it
gives a real number to the exact kind of stat `docs/systems/shipyard.md`'s
`SHIPYARD_TARGET_MINIMUM` note already anticipated becoming useful again
once hull-loss/combat-attrition exists ("standing replacement capacity...
would become genuinely useful again"). `garrison_rating` is the ground-side
equivalent, ready for a future combat pass to actually read.

## First Steward of Continuance (Branch H — Office of Human Continuance) and Continuance Halls

`civilian_world`'s `population_growth_per_cycle` effect was real, but fed
nothing beyond the colony's own display number and (indirectly) Tithe
Grade math — `docs/systems/tithe-system.md`'s "Who owes a tithe" section
calls this out by name as a dead end. Per
`Downloads\The Directorate\lets remove the religious aspect of this.
instead.md` (the chat that replaced the Ember Faith/First Flamekeeper with
the secular Office of Human Continuance in this project's actual canon —
see `lore/gaps.md`'s "First Flamekeeper vs. First Steward of Continuance"
entry for why that name, not Ember Faith, is correct here), each colony is
meant to eventually raise a **Continuance Hall**: "part archive, school,
museum, assembly space, emergency coordination center, and memorial... one
of the first permanent civic buildings after life support and industry."
That's framed as a milestone a colony *grows into*, not an instant flag —
which is exactly what population growth was missing a use for.

- `CONTINUANCE_HALL_POPULATION_THRESHOLD` (currently 150, tunable) is the
  population a colony needs before it raises one.
- `update_colonies()` checks every outpost/established colony's population
  against the threshold and flips a new `continuance_hall` field to `True`
  the first time it's crossed. This check is deliberately **not** scoped to
  `civilian_world` — the lore frames it as something any colony eventually
  grows into, not a `civilian_world`-only perk — so it stays correct even
  if a future change lets other specializations grow population too. In
  practice, only `civilian_world` colonies actually gain population right
  now, so only they can cross it today.
- `continuance_hall` is one-way: once `True`, it's never re-checked or
  reset, even if population later dropped (there's no mechanic that drops
  population today, but the flag is written to be correct if one existed).
- `show_council()`'s `first_steward_of_continuance` entry reports how many
  established colonies have raised a Continuance Hall out of how many
  exist. `show_colonies()` prints "Continuance Hall: established" on any
  colony that has one.

## Save/load

Both new colony fields (`garrison_rating`, `continuance_hall`) are plain
entries in each colony's dict, so they save and load automatically as part
of `world["colonies"]` — no new save-format work needed. A save made
*before* this pass won't have either key; `_apply_loaded_save()` backfills
both with `colony.setdefault("garrison_rating", 0.0)` and
`colony.setdefault("continuance_hall", False)`, in the same backfill block
that already covers the Tithe System's `distance_steps`/`tithe_grade`/
`tithe_shortfall_streak` fields — see that block's comment in
`src/main.py` for the established pattern this follows.

## Colonial Warden (Branch D) and Quartermaster-General (Branch F) — 2026-09-05, "Colonial Warden / remaining specializations" pass

Two more gaps this same "improve all systems" effort left open, closed in
a follow-up pass once the stress-test fixes above were committed:

- **Colonial Warden** was the only wired-in-spirit seat with no
  `live_status` line in `show_council()` at all — its "wiring" worked
  entirely through the separate `colonies` command instead (see the old
  bullet this replaces). That's still true and still useful, but every
  other nine seats now report something under "Current:" and Colonial
  Warden reporting nothing read as an omission rather than a deliberate
  choice. Fixed the same low-risk way First Minister was: a pure read-only
  aggregate over `world["colonies"]` (counts by status — surveyed,
  outpost, established), zero new state, matching the seat's actual domain
  ("Survey, colonization, colony specialization") exactly.
- **`fuel_world`** and **`depot_trade_world`** were this codebase's last
  two flavor-only specializations. Both are explicitly logistics-flavored
  (a fuel depot, a trade depot), and Quartermaster-General's domain
  ("Freight, convoys, supply routes, logistics doctrine") was sitting
  almost as thin as Marshal-General's was before that seat's fix — a bare
  freighter count, nothing behind "supply routes" or "logistics doctrine"
  at all. Following the exact `FORTRESS_WORLD_GARRISON_RATING_PER_CYCLE`
  precedent: `FUEL_WORLD_RESERVE_PER_CYCLE` (6) and
  `DEPOT_TRADE_WORLD_THROUGHPUT_PER_CYCLE` (6) give each specialization a
  real, accumulating, per-colony stat (`fuel_reserve`, `trade_throughput`),
  applied in `update_colonies()` the same way every other specialization's
  effect is, and summed into Quartermaster-General's `live_status` entry
  alongside the freighter count. `show_colonies()` prints either stat
  whenever it's above zero, the same way `garrison_rating` already does.

**Deliberately not a fuel-consumption or multi-colony trade system.**
Building either of those for real — ships that actually burn fuel to
travel, or trade routes that move goods between two named colonies —
would mean introducing a new resource dependency that something can run
out of, immediately after a pass whose entire point was eliminating
exactly that failure shape (see the colony-support-stall bug above). Both
stats are explicitly logistics groundwork a future pass can read (e.g.
fuel reducing freighter travel time, or trade throughput feeding a real
colony-to-colony route), the same status `garrison_rating` already has
relative to a future combat pass — not a claim that fuel or trade is a
complete system today.

## What this explicitly does not include

- No combat resolution of any kind — `garrison_rating` is a bookkeeping
  number a future combat pass can read, not a mechanic that does anything
  on its own yet.
- No Continuance Hall building cost, construction time, or player command
  — it's an automatic milestone, the same way Tithe Grade is automatically
  recomputed rather than something the player builds directly. A dedicated
  `continuance` command or an explicit build cost is a reasonable future
  step if the milestone needs more player-facing weight.
- `fuel_reserve` and `trade_throughput` are bookkeeping numbers only, the
  same way `garrison_rating` is — no fuel-consumption mechanic for travel,
  no multi-colony trade routes. See the section just above for why that's
  deliberate, not an oversight.
- Colonial Warden's original "wiring" (the `colonies` command itself)
  predates this doc and is unchanged — the new `live_status` line
  supplements it, it doesn't replace it.

## Success condition

`tests/test_main_integration.py::CouncilSeatWiringIntegrationTests` covers:
First Minister's population/reserve aggregate excludes non-established
colonies; Marshal-General's garrison-rating aggregate actually accumulates
via `update_colonies()` and stays at zero for non-`fortress_world`
colonies; First Steward of Continuance's Continuance Hall milestone fires
exactly at the configured threshold, is a true one-way flag, and its
council count matches; a pre-Council-seat-wiring save (missing all of
`garrison_rating`/`continuance_hall`/`fuel_reserve`/`trade_throughput`)
loads without a `KeyError` and backfills correctly; Colonial Warden's
status-count aggregate matches an actual mix of surveyed/outpost/
established colonies; and Quartermaster-General's fuel/trade totals
actually accumulate via `update_colonies()` and stay at zero for every
other specialization.
