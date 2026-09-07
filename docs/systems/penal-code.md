# Directorate Penal Code — Law and Sentencing

**Status:** Documented, implemented, and wired into the game loop — `src/penal_code.py` (data module) plus `src/main.py` (integration).

## Purpose

The Directorate is not a friendly government. A colony-founding empire that
runs on ruthless logistics and total command authority needs a legal system
that reflects that: absolute, procedural, and unforgiving. The Penal Code
gives every violation a named article and a typical sentence so that
"justice" in this setting is fast, cold, and institutional rather than
adversarial or sympathetic.

Doctrine: **"Innocence Proves Nothing."** The Code exists to protect the
Directorate's function, not to establish a defendant's guilt or innocence
in the way a real-world court would. A hearing determines whether the
Directorate acts, not whether the accused "did it."

## Smallest possible first version (already implemented)

- Four sentencing tiers, from least to most severe:
  1. **Reprimand and Restitution** — official record mark plus repayment of any measurable loss.
  2. **Toil Legions** — forced labor assignment, fixed term.
  3. **Penal Legions** — forced military/hazard-duty assignment, fixed term, more dangerous than Toil Legions.
  4. **Servitor Conversion** — capital and irreversible. The convicted is stripped of legal personhood and converted into servitor labor.
- Five founding articles, each with a `typical_sentence` tier (see `PenalCode.default_code()` in code):
  - Desertion of Post
  - Sabotage of Directorate Property
  - Insubordination Under Command
  - Hoarding of Strategic Supply
  - Treason Against the Directorate
- `charge()` looks up an article and returns its typical sentence tier — a starting recommendation, not an automatic outcome.
- `confirm_capital_sentence()` is a hard gate: a Servitor Conversion sentence cannot be marked carried out unless **both** `referred_by_vigil` and `confirmed_by_grand_director` are `True`. This mirrors the CYOA narrative rule that no capital sentence executes without that two-step sign-off chain.

## What this version explicitly does not include yet

- No random trial/verdict resolution — `charge()` returns the article's typical sentence, it does not simulate a contested hearing.
- No appeals process.

## Labor-economy wiring (2026-09-05, "improve all systems" pass)

Toil Legion and Penal Legion sentences used to be a filed record with no
further consequence — flagged in this doc, before this pass, as a known
gap ("no tie-in yet to the labor economy... a filed record does not yet
remove anyone from, or add anyone to, a workforce pool"). Both tiers'
own descriptions already say what kind of work they mean, so this wiring
takes them at face value instead of inventing new meaning:

- **Toil Legion** ("forced labor assignment") is assigned to Mars's forge
  complex for a fixed term (`TOIL_LEGION_TERM_STEPS`, 10 steps): a steady
  `TOIL_LEGION_REFINED_METAL_PER_CYCLE` (3.0) trickle into Mars's refined
  metal every `advance` step while the sentence is being served.
- **Penal Legion** ("forced military/hazard-duty assignment") is assigned
  to garrison/defense duty for a shorter fixed term
  (`PENAL_LEGION_TERM_STEPS`, 6 steps — more dangerous duty, shorter
  term): `PENAL_LEGION_GARRISON_PER_CYCLE` (2.0) added every step to
  `world["legion_penal_garrison_rating"]`, a Directorate-wide (not
  per-colony) number reported by Marshal-General's Council entry
  alongside `fortress_world`'s colony-level `garrison_rating` — see
  `docs/systems/council-seats.md` for why that stat exists at all.
  Directorate-wide rather than per-colony because a sentenced individual
  isn't tied to any one colony the way a fortress world is.

`_file_charge()` now files a Toil/Penal Legion sentence with
`status: "serving"` and a `term_remaining` counter instead of the generic
`"sentenced"` every other non-capital tier still gets. `update_penal_labor()`
(called every step from `advance_world()`, right after `update_mars()`)
applies the effect and decrements the term for every `"serving"` record,
flipping it to `"term_served"` — a real end state, not a silent stop —
the step its term reaches zero. `docket` shows the remaining term on any
sentence still serving.

### Hardening added 2026-09-05 (stress-test pass)

`update_penal_labor()` used to do a bare `record["term_remaining"] -= 1`.
Normal play can't produce a `"serving"` record without `term_remaining`
(`_file_charge()` always sets both in the same assignment), but a
hand-edited or partially-written save file could -- and that raised an
uncaught `KeyError` on the very next `advance`, crashing the program right
after `load_game()` had reported "full state restored." Fixed with
`.get("term_remaining", 0)` (treats a malformed record as already served
rather than crashing) plus a matching load-time backfill in
`_apply_loaded_save()`, the same defensive pattern this codebase already
applies to every other historical save-compatibility gap.

This still isn't a "workforce pool": there's no mechanic today that
removes the sentenced person from anywhere else (a colony's population,
a lab's staff) to begin serving, since the game doesn't track named
individuals as assignable labor anywhere. It gives the sentence a real
economic/military effect for its term, which is what was actually
missing; a full labor-pool system (drafting a specific person away from
a specific job) is a larger, separate feature this doesn't attempt.

## Integration into the game loop

- `charge <name> <article_id>` **command** → `handle_charge()` in
  `src/main.py`: looks up the article, calls the exact tested `charge()`
  function from `src/penal_code.py`, and appends a record dict
  (`name`, `article_id`, `tier`, `status`) to `world["penal_records"]`.
  A capital (Servitor Conversion) sentence is filed with
  `status: "awaiting_confirmation"` instead of being carried out
  immediately.
- `confirm_servitor <name> <vigil y/n> <grand_director y/n>` **command** →
  `handle_confirm_servitor()`: finds that name's pending record and calls
  the exact tested `confirm_capital_sentence()` function. On success the
  record's `status` becomes `"carried_out"`; a missing sign-off raises
  the same `ValueError` the standalone module always raised, reported to
  the player instead of silently failing.

## Where this lives in the code

| What | Where |
|---|---|
| The standing Penal Code (doctrine + articles) | `world["penal_code"]` in `src/main.py`, built by `PenalCode.default_code()` |
| Every charge ever filed | `world["penal_records"]` — a list of dicts, oldest first |
| Filing a charge | `charge` command → `handle_charge()` in `src/main.py` |
| Confirming/carrying out a capital sentence | `confirm_servitor` command → `handle_confirm_servitor()` in `src/main.py` |
| Viewing articles + filed records | `docket` command → `show_docket()` in `src/main.py` |
| Applying one step of Toil/Penal Legion labor, per serving record | `update_penal_labor()` in `src/main.py`, called from `advance_world()` |
| Directorate-wide Penal Legion garrison contribution | `world["legion_penal_garrison_rating"]`, reported by `marshal_general` in `show_council()` |

## Success condition

- `charge()` returns the correct tier for each of the five founding articles.
- Attempting to finalize a Servitor Conversion sentence without both the
  Vigil referral and Grand Director confirmation raises an error instead of
  silently succeeding.
- A fully confirmed Servitor Conversion sentence succeeds and is reported as
  irreversible.
- A Toil/Penal Legion sentence applies its effect every step for exactly
  its fixed term, then stops for good — see "Labor-economy wiring" above.

## Dependencies

Feeds Mars's refined-metal stockpile (Toil Legion) and
`world["legion_penal_garrison_rating"]` (Penal Legion), which
Marshal-General's Council entry reads (`docs/systems/council-seats.md`).
Future integration point, still open: a full labor-pool system that
actually moves a specific named person out of a specific job (a colony's
population, a lab's staff) to begin serving, rather than a sentence
existing independently of wherever that person previously was.

## How to customize

- **Add, remove, or rename an article, or change its typical sentence:**
  edit `PenalCode.default_code()` in `src/penal_code.py` itself — this is
  the single source of truth `world["penal_code"]` is built from at game
  start.
- **Add a new sentencing tier:** add a member to the `SentencingTier`
  enum in `src/penal_code.py`; if it should be capital/irreversible like
  Servitor Conversion, also add its own confirmation gate alongside
  `confirm_capital_sentence()` rather than overloading that function.
- **Change who names count as valid targets, or add a lookup by ship/
  crew roster instead of free-typed names:** that validation would live
  in `handle_charge()` in `src/main.py`; the data module itself has no
  opinion on what a valid "name" is.
