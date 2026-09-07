# The Tithe System

## Purpose

Wire the Chancellor-General Council seat (Branch I, "The Chancellery —
tithes, census, records, cross-branch reporting", with a Tithe Clerk rank
already in its ladder) to real mechanics, and give colonies' material
output somewhere to go instead of sitting in a colony-local stockpile
nothing else ever read.

Deliberately **not** a shared resource pool. Earth, Mars, and every colony
keep producing and stockpiling their own resources exactly as before. The
tithe is the only thing that ever crosses between a colony and the wider
Directorate economy, and it moves the way CSV Meridian's cargo does: taken
from one location's stockpile now, delivered into another's after real
travel time.

## Who owes a tithe

Only **mining_world** and **forge_world** colonies — the two
specializations that produce `raw_metal`/`refined_metal`
(`SPECIALIZATION_EFFECTS` in `main.py`). Every other specialization is
tithe-exempt right now, for the same reason several of them are already
"flavor only" for production: there's no tithe-able resource type for them
yet. A `research_world`'s research points, a `civilian_world`'s
population, and an `agri_world`'s support-supply output aren't tithed —
extending the system to those would need its own design pass once those
are genuinely spendable resources rather than a display number.

(Update 2026-09-05: `civilian_world`'s population stopped being *purely* a
display number the same day this note's "dead end" framing was written —
see `docs/systems/council-seats.md`'s Continuance Hall milestone. It's
still not a *spendable* resource, so it's still correctly tithe-exempt;
this is just a pointer so this note doesn't read as stale.)

## Tithe Grade

A colony's obligation level (0–4, "Grade I — Nominal" through "Grade V —
Crushing"), recalculated live every tithe cycle rather than cached, so it
can climb as the colony grows:

- **Base level** by specialization: `forge_world` starts at 2, `mining_world`
  at 1 — forge worlds are squeezed harder, matching the Chancellery's
  doctrine that industrial output is taxed heaviest.
- **+1 grade** for every population threshold crossed
  (`TITHE_GRADE_POPULATION_THRESHOLDS`: 200 / 500 / 900), capped at Grade V.

Each grade maps to a **flat quota** (`TITHE_GRADE_QUOTA`), owed every
`TITHE_CYCLE_STEPS` steps. It's a fixed amount, not a percentage of current
stock — a percentage-of-stock levy can never actually exceed what a colony
has, which would make the shortfall/audit/Penal-Code chain below
unreachable. A fixed quota is what creates real risk of falling short.

## Assessment and payment

Every `TITHE_CYCLE_STEPS` steps (`update_tithes()`), every established
eligible colony is assessed:

- Refined metal is spent first, then raw metal for any remainder.
- **Paid in full**: the amount is dispatched as a **tithe convoy** with
  `steps_remaining` set to that colony's `distance_steps` (see below), the
  colony's shortfall streak resets to 0, and any stale open shortfall from
  an earlier cycle is cleared — a colony that's caught back up isn't still
  concealing anything.
- **Paid short**: the colony pays everything it currently has, and the
  unpaid remainder becomes a Chancellery discrepancy the Bureau can audit
  (see below).

## Travel time — why distance is real now

Every colony gets a `distance_steps` value at `survey` time
(`SURVEY_DISTANCE_RANGE_STEPS`, randomized 3–12 steps) — you don't know how
far into space a target actually is until you've surveyed it. This is what
a tithe convoy's travel uses instead of a flat constant: a far colony's
tithe leaves on schedule but takes many more steps to actually arrive at
Mars than a near one's does. `update_tithe_convoys()` advances every
in-transit convoy by one step on every `advance` (not just on tithe-cycle
steps), and delivers into Mars's stockpile on arrival.

CSV Meridian's Earth–Mars run deliberately keeps its own fixed
`TRAVEL_TIME_STEPS` rather than being folded into this system — it's an
established, already-named corridor ("the Earth-Mars corridor", per the
Vigilant's own status line), not a newly discovered, unknown-distance
target. If a second fixed route (a second freighter, a colony-to-colony
lane) is ever added, it should get its own named distance the same way,
not a random one.

### Bug: convoys used to deliver one step early (found and fixed 2026-09-04)

`advance_world()` used to call `update_tithes()` — which can dispatch a
brand-new convoy with `steps_remaining` set to the colony's
`distance_steps` — immediately followed by `update_tithe_convoys()` —
which decrements EVERY in-transit convoy by one, in the SAME `advance`
call. A freshly-dispatched convoy was therefore decremented once before
the player ever saw its real travel time: a colony 3 steps out actually
delivered its tithe after only 2 real `advance` steps, contradicting this
section's own "distance is real" design and the `steps_remaining` the
`colonies` command shows right after dispatch. This was deterministic and
affected every tithe, every game — not an edge case — and disproportionately
shrank the effective distance of near colonies (a distance-3 colony lost
a third of its travel time; a distance-12 colony lost under a tenth).

Fixed by swapping the call order in `advance_world()`:
`update_tithe_convoys()` now runs BEFORE `update_tithes()`. A convoy
already in transit advances first; a convoy freshly dispatched THIS step
by the assessment that follows isn't touched until the NEXT `advance`,
giving it the full `distance_steps` worth of real travel. Regression
tests in `tests/test_main_integration.py` pin both the contract between
the two functions and the actual call order inside `advance_world()`
itself, so a future edit can't silently swap it back unnoticed.

## Shortfall → Bureau audit → Penal Code (Lesson 12's system-linking)

A colony's unpaid tithe doesn't get its own punishment system — it feeds
directly into two systems that already existed:

1. **Bureau audit** (`world["audit_system"]`, generalized from a single
   `active_concealment` slot to a list of `active_concealments` so
   forge_marshal's existing silent-metal-drain mechanic and any number of
   colonies' tithe shortfalls can be open at once). `audit <colony_id>`
   rolls the same `AUDIT_SUCCESS_CHANCE` used for forge_marshal; a
   successful audit clears the shortfall and resets the streak, same
   "reward correction over concealment" doctrine (the Halvorsen
   precedent) as the original mechanic.
2. **Penal Code**. If a colony's shortfall streak reaches
   `TITHE_SHORTFALL_CHARGE_THRESHOLD` (2) consecutive cycles with no
   successful audit correcting one in between, the Chancellery escalates:
   a `hoarding_of_strategic_supply` charge is filed against "the colonial
   administrator of `<colony name>`" — that article already existed for
   exactly this ("Withholding rationed or strategic material from the
   Quartermaster Corps"). This reuses `handle_charge()`'s own logic
   (factored out into `_file_charge()`) so an automatic escalation behaves
   identically to a manually typed `charge` command.

## Commands

- `tithes` — the Chancellery's ledger of fully-remitted tithes.
- `colonies` — each established colony's current Tithe Grade, standing
  (in good standing / N cycles short), distance from Mars, and any
  convoys currently en route.
- `audit <seat_id or colony_id>` — attempt to catch forge_marshal's silent
  drain, or a specific colony's open tithe shortfall. Costs
  `AUDIT_COST_SUPPORT_SUPPLIES` from Mars and starts an
  `AUDIT_COOLDOWN_STEPS`-step cooldown on that target, win or lose (added
  2026-09-04 — see "Design decision" below).
- `council` — the Chancellor-General's seat now reports live data: tithes
  remitted in full, and how many colonies are currently short.

## Defensive fix: escalation no longer stacks duplicate charges (2026-09-05)

A stress-test pass found that `_escalate_tithe_shortfall()` used to file a
brand-new "hoarding_of_strategic_supply" charge every time a colony hit
`TITHE_SHORTFALL_CHARGE_THRESHOLD` consecutive shortfalls, with no check
for whether that exact administrator was already serving one for the same
offense. Combined with the colony-support-stall bug fixed the same day
(see `docs/systems/council-seats.md`'s bug note -- a colony that could
never again pay its tithe re-triggered this every
`TITHE_SHORTFALL_CHARGE_THRESHOLD` cycles forever), one 2000-step stress
run produced 194 duplicate charges against two colonies. The underlying
stall is fixed, but the escalation logic now also refuses to stack a
second charge on an administrator already `"serving"` one for the exact
same article as cheap defense in depth -- a real second offense, filed
*after* the first sentence has run its course (`"term_served"`), still
files normally.

## Design decision: audit cost and cooldown (2026-09-04)

When this system was first built, `audit` had no cost and no cooldown —
flagged at the time as a balance question for Ryan to decide, not
something to change unilaterally. Under later explicit authorization
("patch everything"), it's now closed: a real audit attempt (one that
actually matches an open concealment) spends
`AUDIT_COST_SUPPORT_SUPPLIES` from Mars and starts a per-target
`AUDIT_COOLDOWN_STEPS`-step cooldown, whether it succeeds or fails.
Auditing a target with nothing to find stays free and instant.

Why this was a real bug in disguise, not just polish: with
`AUDIT_SUCCESS_CHANCE` at 0.7 and audits previously free and
repeatable without limit, the odds of *not* catching a real concealment
within 3 attempts were already under 3% — meaning a shortfall or a
silent drain was never a genuine risk, just a one-time inconvenience
undone by spamming `audit` a few times in a row. That undercuts both
forge_marshal's mechanic and the entire shortfall → audit → Penal Code
chain this system builds on.

This is still a tunable balance call, not a fixed rule — the two
constants live in `src/main.py` right next to `AUDIT_SUCCESS_CHANCE` and
are meant to be adjusted.

## What this explicitly does not include yet

- No tithe on population, research points, or food — see "Who owes a
  tithe" above.
- No player control over a colony's Tithe Grade or payment priority (e.g.
  choosing to pay late on purpose, or petitioning for a lower grade).
- No interdiction: nothing can currently stop a tithe convoy in transit.
  Once combat has strategic roots (DESIGN_SPINE.md dev order item 13),
  a convoy in transit is a natural target.
- Distances are colony-to-Mars only. There's no colony-to-colony or
  colony-to-Earth distance yet — not needed until routes other than "tithe
  to Mars" exist.

## Lore reconciliation (2026-09-04)

Built before this system's design was checked against
`Downloads\The Directorate\Asterion Foundry — Command & Rank Structure.md`
(a design-draft doc, not previously committed to the repo). Checked
against it afterward — see `lore/gaps.md`'s "Resolved 2026-09-04" entry
for the full comparison. Short version: the mechanical shape matches that
source closely (tithe convoys as CSV-Meridian-style freight runs, the
"pressure valve before a rebellion" framing for shortfalls). Two places
are simplified relative to it and flagged there: convoys are lightweight
transit records rather than named `Ship` objects, and tithes deliver to
Mars rather than a distinct "Chancellery depot" (no such location exists
yet).

## Success condition

`tests/test_main_integration.py::TitheSystemIntegrationTests` covers: grade
computed correctly from specialization + population; exempt specializations
never assessed; full payment deducts stock and dispatches a convoy with the
colony's own distance; underpayment opens an auditable shortfall; a
successful audit clears it and resets the streak; catching up on a later
cycle also clears a stale shortfall; persistent shortfall escalates to a
real Penal Code charge; convoy travel time matches the colony's
`distance_steps` and delivers into Mars on arrival; `survey` assigns a
distance inside the configured band.
