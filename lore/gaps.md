# Gaps — narrative ↔ code mismatches

The working list of places where the story and the code don't line up
yet. This is the persistent version of a rule the project already
follows: when lore and code disagree, or one has something the other
doesn't, it gets written down and flagged — never silently forced into
matching, and never silently ignored.

Each entry: what the mismatch is, which side is ahead, and what (if
anything) is blocking it from closing.

## 🔴 Active blocker: narrative log only synced through Cycle 3

Perplexity's own log confirms the campaign's canonical state is Cycle
29 (last updated 2026-09-01). The recap synced into `canon.md` so far
only covers Cycles 0–3 — Perplexity's own extraction was truncated
partway through Cycle 20. **Ryan needs to paste Cycles 20–29 (or the
full current log) to Perplexity** to get a complete recap, then sync
that in. Everything below that references "Cycles 4–29" content is
working from Perplexity's own terse summary of those cycles, not a full
recap — treat those notes as provisional until the real sync happens.

## 🔴 Unresolved: cycle length retcon (month vs. day)

Perplexity's log states a cycle was originally one month, then a later
revision changed it to one Earth day — and that the underlying
production/consumption numbers were **not** rescaled to match. Perplexity's
own record "flags that inconsistency rather than silently correcting
it." This is a real open question, not something to guess at:

- Does the game code's `advance` command (one "cycle" per call) currently
  correspond to a month or a day, conceptually?
- If the narrative's cycle length changes, does anything in the code
  actually depend on real-world time scale, or is "cycle" already just
  an abstract turn unit with no hard tie to calendar time?

Needs Ryan's call once the fuller Cycles 4–29 recap clarifies when and
why this changed. Don't silently pick one.

## 🔴 Unresolved: First Flamekeeper vs. First Steward of Continuance sequencing

Two source chats give conflicting states for the Branch H Council seat:

- The Council-roster chat (Cycle 29 naming) lists the seat but doesn't
  name a holder — implying it may still read as "First Flamekeeper" or
  simply vacant at the moment that chat was written.
- The religion-removal retcon chat retires "First Flamekeeper" entirely
  in favor of "First Steward of Continuance," and its own bottom-line
  note says this matches the pre-existing project brief, which only ever
  uses "First Steward of Continuance."

**Working assumption for this sync:** treated "First Steward of
Continuance" as the current/correct name throughout `canon.md` and
`glossary.md`, since it's the only name the pre-existing project brief
ever uses and the retcon chat is explicit that it supersedes the old
title. **This is inferred, not explicitly confirmed by Ryan** — he
confirmed the Council names generally ("the names add") but this specific
sequencing question wasn't asked directly. Worth a direct confirm next
time it comes up, especially if new Perplexity content refers to a
"First Flamekeeper" as still active.

## Needs confirmation: Directorate Command Net's mechanical status

Ryan confirmed the DCN's *purpose* — automation/coordination so Council
members "actually do their jobs and not be just names/titles," to reduce
his own micromanaging — but not:

- Whether the DCN is meant to be integrated into Perplexity's actual
  story state/save right now, or is a design idea sitting alongside the
  story for now.
- Whether it should eventually become an actual game mechanic (e.g. an
  extension of the existing Standing Orders system) or stays narrative-
  only indefinitely.

Don't build anything code-side for the DCN without asking first — this
is exactly the "design idea, not to build now" flag already noted inline
in `canon.md`.

## Needs confirmation: Cycle 29 numeric baseline vs. actual save state

`canon.md`'s Cycle 29 section records a resource baseline from the
Council-roster chat (Earth support 13,165; Mars support 113; Mars raw
metal 225; Mars refined metal 362; consumption 10.2/cycle; production
500/cycle; resupply 20/cycle; warning threshold 62). This has **not**
been checked against the actual game's current save file — it's lore-
side numbers, not verified against `world` state in `src/main.py`. Worth
a direct comparison before treating these as the game's authoritative
current numbers, since the whole point of the Cycle 29 sync was to keep
the two in step.

## Needs a decision: Command & Rank Structure v4 is design-draft-only

`lore/design/command-and-rank-structure-v4.md` is a full archived design
doc (Branches A–K rank ladders, ten-seat Council table, Director's Own,
outside-the-Directorate entities) — but it's a **draft that was never
committed to the actual game code**. The code currently only has 5 of
10 Council seats wired to live data (see the original project brief).
Treat the full rank ladders as narrative reference material, not as
something already implemented — don't assume a rank mentioned there
exists in-game without checking `src/main.py` first. Also note: this
archive's own Branch H content (Ember Faith / First Flamekeeper /
Sisters of the Ember) is superseded by the religion-removal retcon —
annotated inline in the archive file itself, but easy to miss if someone
reads only part of it.

## Resolved / not a gap: two transcript files aren't Directorate canon

Two of the four large saved transcript files were checked this sync and
found **not** to be Directorate narrative content:

- `I'm feeling inspired...md` — game-engineering planning history, not
  story content.
- `im bored at work.md` — an unrelated Space-Engineers/nomadic-fleet
  creative session (LOGOS-17). This IS the confirmed source of the
  "Sovereign of the Forge" project title/name — Ryan confirmed it's
  name-origin trivia only, not connected to the Directorate story.

Future syncs don't need to re-examine either file for canon content.

## Resolved 2026-09-04: Tithe System implemented, Chancellor-General wired

Built directly from `Downloads\The Directorate\Asterion Foundry — Command
& Rank Structure.md`'s Branch I section and its "gameplay hooks" list
(design-draft-only, not previously in the repo), cross-checked against
`Do i have a counsil_.md`'s Chancellery notes. What the code now does and
how it lines up with that source material:

- **"Tithe convoys are a natural extension of the CSV Meridian's
  supply-run pattern... mechanically identical... just with a different
  reason for the trip."** Implemented per-colony, with real travel time
  (`distance_steps`, randomized at survey) instead of a flat constant —
  the mechanical pattern matches; **simplification flagged**: a tithe
  convoy is a lightweight transit record in `world["tithe_convoys"]`, not
  a full named `Ship` object the way CSV Meridian is. Upgrading that is a
  reasonable future step if named tithe vessels ever matter narratively.
- **"The tithe as a pressure valve. A world that can't meet its tithe is
  a Chancellery problem before it's a rebellion."** Implemented as a
  shortfall → Bureau audit → Penal Code escalation chain (see
  `docs/systems/tithe-system.md`) — matches the spirit; there's no
  rebellion mechanic to escalate to yet (none exists in the game), so a
  persistent shortfall currently tops out at a formal charge, not
  unrest.
- **"Flag any discrepancy exceeding 2 percent automatically to both the
  Provost-General and the Grand Director."** The Bureau/Provost-General
  half is implemented (`audit <colony_id>`); nothing currently notifies
  "the Grand Director" specifically, since the player *is* effectively
  that seat — the escalation message doubles as that notification today.
- Tithe destination: the source material says "a Chancellery depot,"
  which doesn't exist as its own location yet. **Assumption, not
  confirmed:** tithes deliver to Mars, the Directorate's only real
  industrial/logistics hub right now. Revisit if a dedicated Chancellery
  depot location is ever added.
- Only `mining_world`/`forge_world` colonies owe a tithe (the only
  specializations that produce a real tithe-able resource) — not
  addressed one way or the other in the source material, so this is a
  code-side scoping call, not a lore gap.

**Chancellor-General is now wired to live data** in `show_council()`
(tithes remitted, colonies currently short) — the same pattern the other
five wired seats use.

## Resolved 2026-09-05: First Minister, Marshal-General, First Steward of Continuance wired

The last three of the ten Council seats with no backing system (see the
"Lore ahead of code" entry this replaces) are now wired, closing out this
doc's own open item. Full writeup in `docs/systems/council-seats.md`;
short version:

- **First Minister** (civil government/population/food & life support) —
  a pure read-only aggregate: total population across established
  colonies plus Earth's support-supplies reserve. No new mechanic, no
  lore ambiguity.
- **Marshal-General** (the Legions/ground forces) — `fortress_world` was
  one of the flavor-only specializations noted just above; per
  `Downloads\The Directorate\Asterion Foundry — Command & Rank
  Structure.md`, Marshal-General's mandate is ground-defense bookkeeping
  ("stress-testing... the perimeter defense grid," a "Legion Readiness
  Report" tracking "garrison, and defense-grid readiness"), not combat
  resolution — so a new `garrison_rating` stat was a legitimate,
  narrow read of the source material, not an invented mechanic. Explicitly
  flagged in the doc as fleet/combat groundwork, not a combat system.
- **First Steward of Continuance** (Office of Human Continuance) — used
  the "First Steward of Continuance" resolution from the sequencing entry
  above directly: `Downloads\The Directorate\lets remove the religious
  aspect of this. instead.md` describes each colony eventually raising a
  "Continuance Hall" once it has grown enough. That's now a real,
  population-gated, one-way milestone per colony
  (`CONTINUANCE_HALL_POPULATION_THRESHOLD`), which is what let
  `civilian_world`'s population growth stop being a dead end (see the
  "Code ahead of lore" note this doesn't fully resolve — Legion/Bureau
  ranks below Marshal-General/Provost-General still have no code
  representation, only the Council-seat level does).

Nothing here decides the still-open sequencing question above (whether
"First Flamekeeper" ever briefly applied in the actual Perplexity save) —
this just uses "First Steward of Continuance" per that entry's own working
assumption, same as `canon.md`/`glossary.md` already do.

## Resolved 2026-09-05: Penal Code labor-economy gap (Toil/Penal Legion)

Same session as the Council-seat wiring above, same underlying pattern:
`docs/systems/penal-code.md` already flagged, in its own words, that Toil
Legion and Penal Legion sentences had "no tie-in yet to the labor
economy... a filed record does not yet remove anyone from, or add anyone
to, a workforce pool." Not sourced from new lore this time — the two
tiers' own existing descriptions ("forced labor assignment" / "forced
military/hazard-duty assignment") were enough to wire a real, fixed-term
effect: Toil Legion now feeds Mars's refined metal, Penal Legion now feeds
the same `legion_penal_garrison_rating` number Marshal-General's Council
entry reports. Full writeup in `docs/systems/penal-code.md`'s "Labor-
economy wiring" section. Explicitly **not** a full labor-pool system (no
mechanic moves a specific named person out of a specific job to serve) —
that's still open, noted in that doc's "Dependencies" section.

## Resolved 2026-09-05: last two flavor-only colony specializations wired (Colonial Warden pass)

`fuel_world` and `depot_trade_world` were the last two colony
specializations left with `SPECIALIZATION_EFFECTS[...] == {}` (the same
position `fortress_world`/`civilian_world` were in before the entry
above). Both are logistics-flavored, and Quartermaster-General's Council
domain ("Freight, convoys, supply routes, logistics doctrine") had
essentially no data behind it yet — a bare freighter count. Gave each a
real, accumulating per-colony stat (`fuel_reserve`, `trade_throughput`)
reported on that seat, the same "find the seat whose domain already
implies this" approach used for Marshal-General/`garrison_rating`. Not
sourced from new lore — same as the Penal Code entry above, the
specializations' own existing names/flavor text were enough to place
them. Deliberately **not** a fuel-consumption-for-travel mechanic or a
real multi-colony trade network — building either right after the
2026-09-05 stress-test pass (which spent its whole effort closing down a
forever-stalling resource dependency) would have reintroduced the exact
failure shape that pass just fixed. Full writeup:
`docs/systems/council-seats.md`'s "Colonial Warden and Quartermaster-
General" section. Same pass also gave Colonial Warden's own Council entry
a `live_status` line for the first time (a pure read-only aggregate,
zero new state) — it was the only wired seat with none at all.

## Lore ahead of code (narrative exists, no system yet)

- **Xenos Contact Protocol** (Directorate Code article) — no enforcement
  mechanism yet. Honest Reporting's gap was filled behaviorally via the
  Bureau audit mechanic instead of a new Penal Code article; Xenos
  Contact Protocol hasn't gotten an equivalent treatment.
- **Wayfarers' Guild's parent branch** (Logistics vs. Collegium) — 
  explicitly undecided per `build-instructions.md`. Don't resolve this
  without Ryan raising it.
- **Seal/insignia/logo systems, faith/living-relic mechanics** —
  explicitly out of scope for now per `build-instructions.md`, under
  active separate development elsewhere.
- **Founding-era figures and named ships** (Halvorsen, Okoye, the Grand
  Director, patrol cutters Ward/Sentinel/Bastion, CSV Concord, LWS
  Vigilant) — rich narrative color from the Cycle 0–3 sync, none of it
  currently represented as named entities in the code (the game tracks
  aggregate fleet counts and generic titles, not individuals or named
  hulls, as far as confirmed). Not necessarily something to build —
  just flagged so it's not assumed to exist in-game.
- **Institutions named in Cycle 3** (Discipline Corps, Quartermaster
  Corps, Chancellery, Provost-General as an office) — established
  narratively, no confirmed code representation yet beyond what the
  Council-seat and Branch system already covers.

## Code ahead of lore / needs narrative

- **Freighter metal-pickup reserve** (`FREIGHTER_METAL_PICKUP_RESERVE`)
  and **fleet caps** (`FLEET_TARGET`) — real mechanical/economic
  consequences (CSV Meridian no longer strips Mars's refined metal to
  zero; new-hull construction stops at class caps) that could use a
  narrative reason if Perplexity wants to give them one. Note: Meridian
  itself is now confirmed as a real named ship in the narrative (first
  freighter, Cycle-0 relief run, Cycle-2 combat) — the code-side
  behavior fix and the narrative ship are the same vessel, just not
  cross-referenced before this sync.

## Resolved by this sync

- ~~**Bureau audit mechanic** — real game-balance mechanic invented
  code-side because the compendium never gave exact odds for Honest
  Reporting enforcement. No in-universe explanation yet.~~ **Resolved:**
  the Cycle 3 lore establishes the Bureau as the actual institution
  enforcing the Directorate Code under the Provost-General, with Honest
  Reporting as one of five constitutional articles. The audit mechanic
  now has a clean in-universe home — no code change needed, just the
  narrative catching up to what was already built.

## 🔴 Flagged 2026-09-04: this doc assumes a xenology tech lane that isn't in the actual repo

A full codebase audit run this session found **no `xenology` lane
anywhere** in `src/research/data/technologies.json`, `engine.py`, or
`models.py` — `tests/test_research.py::test_exactly_four_lanes` still
asserts 4 lanes, not 5. A prior Cowork session's summary claimed a
xenology lane with evidence-gating was built and committed; that work is
not present on Ryan's machine (separately flagged to Ryan, still under
investigation as of this writing). The "Research lane naming" and
"Xenology's unlock gate" entries just below were written assuming that
lane exists — **treat both as describing planned/claimed code, not
actual code**, until the missing-work question resolves one way or the
other.

## Needs confirmation, not urgent

- **Research lane naming** — the narrative's five Collegium branches
  (Materials & Industry, Logistics & Propulsion, Habitat & Life Support,
  Military & Defense, Xenology) plausibly map one-to-one onto the code's
  five tech lanes (`physics_and_materials`, `logistics_and_industry`,
  `biology_and_colonization`, `military_doctrine`, `xenology`) — but
  this hasn't been explicitly confirmed lane-by-lane, and the wording
  isn't identical (e.g. "Habitat & Life Support" vs.
  `biology_and_colonization`). Worth a deliberate check before treating
  them as interchangeable in future writing.
- **Xenology's unlock gate** — narrative says the Xenology research path
  is "explicitly locked behind completion of the salvage operation";
  code gates the xenology lane on banked `xenos_fragments` evidence
  instead. These could be the same gate described two ways (salvage
  recovers fragments, fragments unlock the lane) or two different gates
  — not confirmed.
- **Directorate Code ↔ Penal Code enforcement mapping** — Requisition
  Authority and Chain of Command (constitutional articles) plausibly
  correspond to "Hoarding of Strategic Supply" and "Insubordination
  Under Command"/"Desertion of Post" (Penal Code articles) respectively,
  based on their descriptions, but this hasn't been explicitly stated
  anywhere and shouldn't be assumed canonical without confirming.
- **"Support supply" as a tracked resource** — the narrative defines a
  specific unit (~40 tonnes / ~125 personnel / cycle) for an off-world
  logistics reserve distinct from raw/refined metal. Whether the code
  tracks a resource under this name, or whether this maps onto something
  else entirely (or nothing yet), hasn't been checked against
  `src/main.py`'s resource model.

## Known, deliberate, not a gap to "fix" silently

- **`world["research"].trial_log`** doesn't persist across save/load.
  Deliberate scope call (treated as disposable history), not an
  oversight — don't change this without asking first.
- **Narrative tech IDs vs. code tech IDs** (e.g. `improved_extraction_1`,
  `servitor_automation_1`) don't exist in `technologies.json` — the
  code's tech tree (`physics_and_materials`, `logistics_and_industry`,
  `biology_and_colonization`, `military_doctrine`, `xenology`) is
  canonical going forward. Two narrative techs were seeded as their
  closest code equivalents; others have no mapping and were left
  uncompleted rather than forced.
- **Structural scope guardrails** — 3D graphics, multiplayer, tactical
  battles, ship interiors, individual crew simulation, aliens/rival
  empires/diplomacy, internal politics, procedural galaxy generation,
  multiple star systems, full salvage system, hive worlds, Dyson
  structures are explicitly out of scope per `DESIGN_SPINE.md`. If new
  lore heads in one of these directions, that's worth flagging to Ryan,
  not building toward.

## Needs a system, not just data-wiring

- **Scientist hiring/reassignment** — would unblock the RP-starved
  research lanes (`biology_and_colonization`, `military_doctrine`,
  `xenology`) that currently can't accumulate research points under
  single-scientist staffing. Surfaced as a real gap while building the
  xenology lane; not itself sourced from lore.
