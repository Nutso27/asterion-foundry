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
- No tie-in yet to the labor economy (Toil/Penal Legion assignees are not
  wired into `src/main.py`'s production numbers — a filed record does not
  yet remove anyone from, or add anyone to, a workforce pool).

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

## Success condition

- `charge()` returns the correct tier for each of the five founding articles.
- Attempting to finalize a Servitor Conversion sentence without both the
  Vigil referral and Grand Director confirmation raises an error instead of
  silently succeeding.
- A fully confirmed Servitor Conversion sentence succeeds and is reported as
  irreversible.

## Dependencies

None yet beyond the game loop itself. Future integration point: a labor
assignment system that actually consumes Toil/Penal Legion sentences as a
workforce pool.

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
