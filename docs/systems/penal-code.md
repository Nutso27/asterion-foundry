# Directorate Penal Code — Law and Sentencing

**Status:** Documented and implemented (first version) — `src/penal_code.py`.

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
- No persistent case/prisoner records tied into `world` state in `main.py`.
- No appeals process.
- No tie-in yet to the labor economy (Toil/Penal Legion assignees are not
  wired into `src/main.py`'s production numbers).

## Success condition

- `charge()` returns the correct tier for each of the five founding articles.
- Attempting to finalize a Servitor Conversion sentence without both the
  Vigil referral and Grand Director confirmation raises an error instead of
  silently succeeding.
- A fully confirmed Servitor Conversion sentence succeeds and is reported as
  irreversible.

## Dependencies

None yet — this is a standalone module. Future integration point: a labor
assignment system that actually consumes Toil/Penal Legion sentences as a
workforce pool.
