# Glossary

Named entities from the narrative, kept in sync with what actually exists
in the code. Updated in place (not append-only) — when something changes,
edit its entry rather than adding a new one.

**Wired** = live game data reflects this entity. **Named only** = exists
in the narrative but has no backing system or live data yet. Cross-
reference `gaps.md` for the fuller story on anything not wired.

## Core setting terms

| Term | Definition | Status |
|---|---|---|
| Cycle | Originally defined as one month of in-world time (Founding Era). **A later narrative revision changes this to one Earth day, and the production/consumption numbers were not rescaled to match — flagged as an open inconsistency, see `gaps.md`.** | Ambiguous — needs a decision |
| Support supply unit | ~40 tonnes of rations/life-support media/medical stock/fuel cells/spares; supports ~125 personnel for one cycle. An off-world logistics reserve, not Earth's total food supply. | Named only — unclear if the code tracks a distinct "support supply" resource by this name; needs checking against `src/main.py`'s resource model |
| Asterion Foundry | The game/playthrough setting and the Directorate's founding-era campaign context | — |
| Earth–Mars corridor | The three-cycle transit route between the two settled worlds | Wired (patrol-cutter escort, freighter transit already modeled) |

## Worlds

| Entity | What it is | Status |
|---|---|---|
| Earth | Directorate core world; 9.1 billion inhabitants; separate terrestrial economy plus the off-world logistics reserve; home of the Logistics Corps (500 support units/cycle from Cycle 4) | Wired |
| Mars | Industrial colony and developing shipbuilding center; started fragile, dependent on imports | Wired |

## Ships

| Entity | What it is | Status |
|---|---|---|
| CSV Meridian | Humanity's first freighter; delivered the Cycle-0 relief shipment, fought the Cycle-2 xenos contact, later assigned to a permanent Earth–Mars supply circuit after the Cycle-16 Forge Stall | Wired — already referenced in code (`FREIGHTER_METAL_PICKUP_RESERVE` fix targets Meridian's Mars pickup behavior) |
| CSV Concord | Mars's second freighter, built sometime in Cycles 4–29 (not yet detailed here — pending fuller sync) | Named only |
| LWS Vigilant | Mars's first dedicated combat vessel, built sometime in Cycles 4–29 (not yet detailed here) | Named only |
| PC Ward | Patrol cutter escorting the Earth–Mars corridor | Named only |
| PC Sentinel | Patrol cutter on alert at Earth | Named only |
| PC Bastion | Patrol cutter on alert at Earth | Named only |
| The Cycle-2 wreck / crippled cutter | The disabled non-human vessel left in the transit corridor after "Weapons Live"; subject of a later salvage operation that recovered three hull fragments | Named only — the salvage operation's outcome (hull fragments) likely feeds the xenology research lane's `xenos_fragments` evidence, but this mapping hasn't been confirmed, see `gaps.md` |

## Founding-era figures

| Entity | What it is | Status |
|---|---|---|
| Grand Director | Supreme seat of the ten-seat Directorate; not yet named in any synced material | Named only |
| Forge-Marshal-designate Halvorsen | Mars's senior industrial authority; reported (and briefly concealed part of) the colony's support crisis. By Cycle 29, in an ongoing friction thread with Provost-General Thale (Bureau) — the audit-and-concealment dynamic from Cycle 3 appears to be a running relationship, not a one-off incident. Not himself a Council seat as far as confirmed. | Named only |
| Bertrand Okoye | Quartermaster inspector who audited Mars in Cycles 0–3; by Cycle 29 holds the Council seat of **Quartermaster-General**. Same person — the Cycle 3 audit reads as an early appearance of the officer who later formalizes into the seat. | Named only |

## Directorate Council (Cycle 29 roster)

Named and activated as of Cycle 29. Seats below are cross-referenced with
the pre-existing Council-seat rows in "Command Structure" — same seats,
now with the officers who hold them. This roster comes from a side-chat
that generated a paste-able directive rather than writing directly into
Perplexity's story state; Ryan has confirmed the names are canon, but see
`gaps.md` for what's still unconfirmed about live integration.

| Officer | Seat | Notes | Status |
|---|---|---|---|
| Ines Halvard | First Minister | Civil government / Earth policy | Named only, no live data |
| Dr. Yuen Osei | High Savant | Heads the Research Collegium | Named only, no live data |
| Reyes Ferrant | Grand Admiral | Fleet command | Named only, no live data |
| Bertrand Okoye | Quartermaster-General | Same Okoye as the Cycle 3 Mars audit | Named only, no live data |
| Priya Solanke | Colonial Warden | Survey/colonization | Seat wired to the colony system (`show_council()`); officer name not yet reflected in code |
| Dietrik Voss | Marshal-General | Legions/ground forces | Named only, no live data |
| Mireille Dubois | Chancellor-General | Chancellery/census/tithes | Named only, no live data |
| Casimir Thale | Provost-General | Heads the Bureau; in friction with Forge-Marshal-designate Halvorsen over Mars's reporting | Named only, no live data |
| First Steward of Continuance | Council seat — civic culture/education/memory | **Seat holder not confirmed named** — see `gaps.md` for the First Flamekeeper-vacant vs. current-seat-name sequencing question | Named only, no live data |

Not part of the ten-seat Council, but adjacent to it:

| Entity | What it is | Status |
|---|---|---|
| Director's Own | A body distinct from the Council, answering directly to the Grand Director | Named only |
| Mara Voskuijlen | Captain-of-the-Guard, Director's Own | Named only |

## Command Structure

| Entity | What it is | Status |
|---|---|---|
| The Council | Ten-seat governing body | Partially wired — see individual seats below |
| First Minister | Council seat — civil government / Earth policy. Held by Ines Halvard as of Cycle 29. | Named only, no live data |
| Colonial Warden | Council seat — survey/colonization. Held by Priya Solanke as of Cycle 29. | Wired to the colony system (`show_council()`'s `colonial_warden` entry); officer name not yet in code |
| Marshal-General | Council seat — Legions/ground forces; also the Founding-Era title for routine Discipline Corps authority. Held by Dietrik Voss as of Cycle 29. | Named only, no live data |
| First Steward of Continuance | Council seat — civic culture/education/memory. Seat holder not confirmed named as of Cycle 29 — see `gaps.md` for the sequencing question with the pre-retcon "First Flamekeeper" name. | Named only, no live data |
| Chancellor-General | Council seat — Chancellery/census/tithes. Held by Mireille Dubois as of Cycle 29. | Named only, no live data |
| High Savant | Council seat — heads the Research Collegium. Held by Dr. Yuen Osei as of Cycle 29. | Named only, no live data |
| Grand Admiral | Council seat — fleet command. Held by Reyes Ferrant as of Cycle 29. | Named only, no live data |
| Quartermaster-General | Council seat — logistics/requisition. Held by Bertrand Okoye as of Cycle 29 (same Okoye as the Cycle 3 Mars audit). | Named only, no live data |
| *(remaining Council seats, incl. Provost-General)* | See "Directorate Council (Cycle 29 roster)" above for the full named table | Wired — see `src/main.py` `show_council()` for the current code-side list |
| Branches A–K | Directorate organizational branches, each with its own rank ladder. Full ladders (Navy, Forge & Industry, Asterion Collegium/Research, Colonial Administration, Civil Government, Logistics & Supply, Legions, Branch H, Chancellery, Bureau, Vigil) archived verbatim in `lore/design/command-and-rank-structure-v4.md` — that file is a **design draft, not yet committed to code**, see `gaps.md`. Note: that archive's Branch H content (Ember Faith) is superseded, see the Branch H row below. | Wired (branch/rank concept); full ladders are design-only |
| Branch H — Office of Human Continuance | Formerly "the Ember Faith" (First Flamekeeper, Sisters of the Ember, Undying Flame) — retired by the Decree of Human Continuance retcon, see `lore/design/religion-removal-retcon.md`. Current ladder: First Steward of Continuance (Council) → Dominion Steward → Sector Steward → World Curator → Civic Advocate → Archivist-Aide → Candidate. | Named only, design-draft ladder |
| Continuance Halls | Combined archive/school/museum/assembly-space/emergency-coordination-center/memorial; one of the first permanent civic buildings on a new colony. Replaces shrines/cathedrals under the retcon. | Named only |
| The Human Spark | The state seal's flame motif, reinterpreted post-retcon: humanity's own capacity to understand, make, remember, choose, and continue — belonging to the species, protected by no god, not eternal on its own. Replaces "the divine flame / Undying Flame." | Named only |
| The Decree of Human Continuance | The Directorate's founding law (secular-humanist, replacing the old faith-centered foundation): full text archived in `lore/design/religion-removal-retcon.md`. Establishes "no citizen, office, bloodline, machine, or institution may be named the embodiment of Humanity." Not cycle-tagged — a doctrinal layer on the setting, not a dated event. | Named only |
| The Vigil | Extreme internal-security body answering privately to the Grand Director; receives escalated treason cases (from the Discipline Corps) and mandatory xenos-contact reports (Xenos Contact Protocol); deliberately excluded from the Council. Mandate reworked under the religion-removal retcon: now investigates religious revivalism/cult activity as an ongoing counter-insurgency concern (replacing the old "heresy against the Faith" framing), alongside corruption, xenos contact, and rogue technology. | Named only |
| Directorate Command Net (DCN) | Cycle 29 doctrine: an automation/coordination layer meant so Council members actually execute their standing duties rather than being decorative titles (Ryan's stated design intent). Covers data domains, authority tiers, and escalation triggers — see `canon.md` for the full doctrine. **Confirmed:** the design intent/purpose. **Not confirmed:** whether this is meant to be built as an actual game mechanic (e.g. tied into Standing Orders) or is narrative-only for now — flagged in `gaps.md`. | Named only, purpose confirmed — mechanical status open |
| Chartered Trading Houses | Entities outside the Directorate entirely | Named only |
| Wayfarers' Guild | Entity outside the Directorate entirely; its parent branch (Logistics vs. Collegium) is undecided | Named only — parent-branch question explicitly deferred, don't resolve it without Ryan asking |
| Discipline Corps | Embedded Legion discipline/loyalty officers with field authority over desertion, cowardice, and treason; treason cases escalate to the Vigil | Named only |
| Quartermaster Corps | Standing logistics bureau administering freighter networks and implementing Requisition Authority | Named only |
| Chancellery | Empire-wide census/records institution; reconciles reported figures to reality | Named only |
| Legions | Directorate ground-force formation | Named only |
| Research Collegium | The High Savant's research institution; five founding branches: Materials & Industry, Logistics & Propulsion, Habitat & Life Support, Military & Defense, Xenology | Partially wired — see "Research lanes" below for how these map to the code's actual tech lanes |
| High Savant | Directorate office associated with the Research Collegium | Named only |

## Directorate Code (constitutional articles)

Five articles, now named in full (previously this table only had the two
enforcement-gapped ones plus a placeholder):

| Article | What it establishes | Enforcement status |
|---|---|---|
| Sovereignty | No independent human authority exists anywhere in the empire | — |
| Honest Reporting | Concealment/falsification of figures is punishable | No dedicated Penal Code article; filled behaviorally by the Bureau audit mechanic |
| Requisition Authority | Resources and production are Directorate property | Likely enforced via the Penal Code's "Hoarding of Strategic Supply" article — mapping not yet confirmed, see `gaps.md` |
| Chain of Command | Ground forces report to the Grand Director through the Marshal-General | Likely enforced via "Insubordination Under Command" / "Desertion of Post" — mapping not yet confirmed |
| Xenos Contact Protocol | Non-human contacts/materials must be reported immediately to the Bureau and the Vigil | No enforcement yet |

## Institutions enforcing the Code

| Entity | What it is | Status |
|---|---|---|
| Bureau | Institution enforcing the Directorate Code, under the Provost-General. In-universe home of the audit mechanic that fills the Honest Reporting gap (catches concealment, corrects rather than charges) — this mechanic was built code-side as game balance *before* this institutional context existed; the two now line up, see `gaps.md` for the resolved note | Wired (the audit mechanic), the Bureau-as-institution framing is new from this sync |
| Provost-General | Authority overseeing the Bureau. Held by Casimir Thale as of Cycle 29 — see the Thale/Halvorsen friction note under "Founding-era figures." | Named only |

## Research lanes

| Collegium branch (narrative) | Code tech lane | Status |
|---|---|---|
| Materials & Industry | `physics_and_materials` (best guess — not confirmed) | Wired (code), mapping unconfirmed |
| Logistics & Propulsion | `logistics_and_industry` (best guess — not confirmed) | Wired (code), mapping unconfirmed |
| Habitat & Life Support | `biology_and_colonization` (best guess — not confirmed) | Wired (code), mapping unconfirmed |
| Military & Defense | `military_doctrine` (best guess — not confirmed) | Wired (code), mapping unconfirmed |
| Xenology | `xenology` — added as a real 5th lane in session 2 | Wired (code); narrative says this path is locked behind salvage completion, code gates it on banked `xenos_fragments` evidence instead — see `gaps.md` |

## Other

| Entity | What it is | Status |
|---|---|---|
| Xenology (research lane) | 5th `TechLane`, gated by banked (not spent) `xenos_fragments` evidence | Wired, but RP never actually accumulates in it under current staffing (single scientist, physics_and_materials only) |
| "Sovereign of the Forge" | The working title/name origin for this whole project — traced to a separate, unrelated Perplexity creative chat ("im bored at work.md", a nomadic-fleet/LOGOS-17 concept). Confirmed by Ryan: **name-origin trivia only**, not connected to Directorate canon. Nothing from that source chat should be treated as Directorate story content. | Not canon — name origin only |

---

*Seal/insignia/logo systems and faith/living-relic mechanics are under
active separate development per `build-instructions.md` — not tracked
here until Ryan says they're ready to fold in. (The faith/living-relic
line refers to whatever separate mechanic Ryan may build later, not the
Ember Faith institution — that one is retired per the religion-removal
retcon above, not "in development.")*
