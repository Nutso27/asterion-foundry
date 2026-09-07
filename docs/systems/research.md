# Research System — The Asterion Collegium

**Status:** Implemented and wired into `src/main.py`'s command loop (`research`, `invest`, `pilot` commands)
**Code:** `src/research/`
**Data:** `src/research/data/technologies.json`
**Tests:** `tests/test_research.py`

This is the project's canonical research system. It replaces the earlier
placeholder research bullets in `DESIGN_SPINE.md` and the "Add one
progress track and one small completed technology" line in this
directory's `README.md` — any future work that touches research should
build on this module rather than starting a second one.

## Purpose

Model the Asterion Collegium's research as a real institution: labs that
need staff, staff with real skill differences, a rotating set of live
research options instead of one fixed tree, and the option to gamble
resources on an early breakthrough instead of only waiting.

## Design brief this fulfills

Three mechanics, combined:

1. **Lab & specialist layer.** Research points (RP) are generated per
   cycle from labs staffed with scientists, not from an abstract global
   pool. `engine.generate_rp` sums each lab's assigned scientists (by
   lane, with diminishing returns on stacking more of them), scales by
   lab quality and lane-match, and credits the corresponding lane's RP
   stockpile.
2. **Weighted discovery layer.** Players don't see or choose from the
   entire tech tree at once. `engine.refresh_draw_pool` rolls a small
   (2-4 node), weighted-random selection of currently eligible nodes per
   lane — eligible meaning prerequisites are met, the node isn't
   completed, and no mutually-exclusive alternative has already been
   taken. Nodes with RP already invested always stay visible, and so does
   anything passed via the `guaranteed_ids` parameter (added 2026-09-04
   as a bug fix — see `docs/systems/ship-design.md`'s "Bugs found and
   fixed 2026-09-04" section: a node registered into a lane at runtime
   with 0 RP invested could otherwise be silently dropped by the very
   next refresh, the instant the player was told it was available).
3. **R&D pipeline / risk layer.** `engine.attempt_pilot_project` lets a
   staffed, `pilot_project_enabled` node be gambled on: commit a chunk of
   banked RP now, roll against `calculate_pilot_success_chance`, and
   either finish the node immediately or lose most (not all) of what was
   committed. Failure banks `pilot_partial_progress_pct` of the funding
   as permanent progress — a failed gamble still moves the node forward,
   it just costs more than steady accumulation would have.

## Success-probability formula

`calculate_pilot_success_chance` combines four factors, each mapped
through the same diminishing-returns curve (`1 - e^-(rate * value)`) so
no single factor can be maxed out to guarantee success:

```
chance = base_chance
       + 0.30 * diminishing(avg_assigned_scientist_skill)
       + 0.20 * diminishing(lab_quality)
       + 0.25 * diminishing(funding_committed / node.rp_cost)
       - 0.07 * (node.tier - 1)
clamped to [0.05, 0.85]
```

A pilot project is never a sure thing (0.85 ceiling) and never truly
hopeless (0.05 floor). Deeper-tier nodes are harder to shortcut, so
pilot projects matter most for early- and mid-tier breakthroughs.

## Data schema (`technologies.json`)

- **Lane** — `id`, `name`, `description`. Four lanes ship in the starter
  set: `physics_and_materials`, `logistics_and_industry`,
  `biology_and_colonization`, `military_doctrine`.
- **TechNode** — `id`, `name`, `lane`, `tier` (prerequisite depth, *not*
  an equipment quality tier), `prerequisites`, `rp_cost`, `draw_weight`,
  `effect` (must be non-empty — see "No dead ends" below),
  `flavor_text`, optional `mutually_exclusive_with` (for non-deterministic
  branches), and optional `pilot_project_enabled` /
  `pilot_base_success_chance` / `pilot_partial_progress_pct` /
  `pilot_funding_rp` for nodes that support the risk layer.

The starter set ships 16 nodes across all four lanes (well past the
minimum of 10), including two explicit non-deterministic branches:

- **Propulsion doctrine** — `li_star_lane_transit_doctrine` (efficient,
  corridor-bound) vs. `li_open_space_drive_doctrine` (flexible,
  fuel-hungry, better for scouting/interception) — mirrors the hybrid
  travel model in `DESIGN_SPINE.md`.
- **Primary weapon doctrine** — `pm_focused_energy_emitters` (accurate
  beam weapons, energy lane, pilot-project eligible) vs.
  `md_kinetic_mass_drivers` (cheaper, reliable mass drivers, military
  lane) — a cross-lane mutual exclusion, so committing to one closes off
  the other regardless of which lane you researched it through.

## No dead ends

Every node's `effect` names a concrete, measurable change: a resource
multiplier, an unlocked weapon/hull/defense/world specialization, or a
production/travel efficiency change. `tests/test_research.py`'s
`test_no_dead_end_nodes` enforces this at the data level — a node with an
empty effect fails the test suite.

## Smallest possible first version (already implemented)

- One lane, one lab, one scientist, one node with no prerequisites,
  completed purely through `generate_rp` + `invest_rp` (no discovery
  pool, no pilot projects). This is exactly what `demo.py` exercises
  before adding the other layers.

## Command-loop integration (Lesson 03)

`src/main.py` builds one starting `ResearchState` (`build_research_state`):
one lab on Mars ("Mars Collegium Laboratory") staffed by one scientist
("Savant Voss", specialized in Physics & Materials), with every lane's
discovery pool rolled once at startup. Each `advance` step calls
`update_research`, which runs `generate_rp` automatically — the same way
Mars's forge complex runs automatically. Spending RP is always a
deliberate player choice:

- `research` — prints banked RP per lane, each lane's active pool with
  progress and effects, and completed technologies.
- `invest <lane_id> <pool position>` — spends everything currently
  banked in that lane into the chosen pool entry; completing a node
  applies its effect and reopens a pool slot.
- `pilot <lane_id> <pool position>` — attempts a pilot-project trial on
  that pool entry via the Mars Collegium Laboratory (only works on
  `pilot_project_enabled` nodes).

## What this version explicitly does not include

- No scientist hiring/training economy (scientists are created directly
  for now; a recruitment/training system is a natural follow-up).
- No UI beyond the terminal `research`/`invest`/`pilot` commands and
  `demo.py`'s printed walkthrough.
- No balancing pass — `base_output_per_cycle` in `engine.generate_rp` and
  the RP costs in `technologies.json` are placeholder numbers, tunable
  once real playtesting against the freight loop happens.
- Only one lab and one scientist exist at game start; building/hiring
  more is future work, not part of this integration.

## Xenology lane and evidence-gating (added 2026-09-07)

A fifth lane, `xenology`, exists alongside the original four. It is
gated differently from every other lane: its first node,
`xn_fragment_baseline_analysis`, requires `TechNode.evidence_required`
evidence banked in `ResearchState.evidence_banked`, on top of a normal
`prerequisites` entry — neither gate alone is sufficient.

**Why two gates.** `lore/gaps.md`'s "Xenology's unlock gate" entry
flagged that the narrative describes the lane as "explicitly locked
behind completion of the salvage operation," without confirming whether
that meant the existing `xenos_fragments` evidence mechanic, a real
salvage-related tech node, or both. This implementation applies both:
`xn_fragment_baseline_analysis` requires `md_salvage_field_recovery`
(military_doctrine) already completed, **and** at least 1 evidence
banked. `md_salvage_field_recovery`'s own flavor text — "what looked
like scrap starts yielding intact components and data cores" — reads as
a strong match for "the salvage operation" described narratively, and
requiring both doesn't contradict either reading. **This is an
assumption, not a confirmed design decision** — worth checking directly
against Perplexity's fuller Cycle 4-29 recap once that syncs in.

**How evidence gets banked.** `handle_study_fragments()` in `main.py` is
the only place `ResearchState.evidence_banked` ever increases —
one call banks 1 evidence and spends 3 `xenos_fragments`. Since
`xenos_fragments` was seeded once at the cycle-29 sync with nothing that
replenishes it, at most one analysis (and so at most 1 evidence) is ever
obtainable in the current game. This is exactly why only the lane's
first node is evidence-gated at all: every other xenology node
(`xn_comparative_hull_metallurgy`, `xn_countermeasure_doctrine`) chains
off a normal `prerequisites` entry instead of requiring further
evidence that could never be banked — consistent with this module's own
"no node in the data file is a dead end" rule.

**Mechanically**, `xn_fragment_baseline_analysis` stacks a
`salvage_yield_multiplier` on top of `md_salvage_field_recovery`'s own
(both apply via `_completed_effect_multiplier` in `main.py`, which
multiplies every completed node's matching effect key together);
`xn_comparative_hull_metallurgy` stacks `hull_integrity_multiplier` the
same way `pm_stress_lattice_theory` does; `xn_countermeasure_doctrine`
uses the same `unlocks_defense`/`incoming_fire_reduction` effect shape
`md_point_defense_grids` already established. None of the three are a
new mechanical category — they extend existing multiplier chains rather
than introducing bespoke, one-off logic.

**Not addressed by this work:** the Directorate Code's `Xenos Contact
Protocol` article (still has no Penal Code enforcement, per
`lore/gaps.md`'s "lore ahead of code" section) and any deeper first-
contact/diplomacy mechanic — both explicitly out of `DESIGN_SPINE.md`'s
scope for now.

## Success condition

`python -m unittest tests/test_research.py -v` passes, `python src/research/demo.py`
runs end to end, and `python src/main.py` lets a player run `advance` to
accumulate RP, `research` to see the discovery pool, `invest` to complete
a node through steady accumulation, and `pilot` to gamble on one.

## Dependencies

Standard library only (`dataclasses`, `json`, `math`, `random`,
`pathlib`) — no new project dependency was introduced.
