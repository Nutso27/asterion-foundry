# Game Systems Index

This directory contains short design notes. Documentation is where large ideas live safely before they become code.

## Current implementation

| System | Status | Main code |
|---|---|---|
| Manual time steps | Implemented | `src/main.py` |
| Earth and Mars stockpiles | Implemented | `src/main.py` |
| Mars forge-world production | Implemented, minimal | `src/main.py` |
| Command loop | Implemented | `src/main.py` |
| Freight logistics (CSV Meridian) | Implemented — automatic Earth↔Mars cargo loop | `src/main.py` |
| Research (Asterion Collegium) | Implemented and wired into the command loop (`research`/`invest`/`pilot`) | `src/research/`, `src/main.py`, see `research.md` |
| Directorate Penal Code | Implemented and wired into the command loop (`charge`/`confirm_servitor`/`docket`) | `src/penal_code.py`, `src/main.py`, see `penal-code.md` |
| Lab specialization (fixed vs. flexible labs) | Implemented and wired into the command loop (`build_lab`/`labs`) | `src/research/lab_specialization.py`, `src/main.py`, see `lab-specialization.md` |
| Shipyard slot expansion and no-idle rotation | Implemented and wired into the command loop (`shipyard`) | `src/shipyard.py`, `src/main.py`, see `shipyard.md` |
| Ship design (MK progression and retirement) | Implemented and wired into the command loop (`fleet`; advances via `invest`/`pilot`) | `src/ship_design.py`, `src/main.py`, see `ship-design.md` |

## Customization quick reference

Every system's tunable constants live in `src/main.py`, near the top of
the file, grouped by system with a comment on what raising/lowering each
one does. Each system's own doc page has a fuller "How to customize"
section — this table is just the fast lookup.

| System | `world` state key(s) | Key functions in `src/main.py` | Constants to tweak (also in `src/main.py`) |
|---|---|---|---|
| Ship design / MK | `world["ship_classes"]`, `world["ship_class_stats"]` | `_apply_ship_design_effect()`, `_register_next_mk_node()`, `show_fleet()` | MK effect multipliers live in `src/research/data/technologies.json`; successor-node multiplier is the `1.15` literal in `_register_next_mk_node()` |
| Shipyard slots | `world["shipyard"]`, `world["shipyard_slots"]` | `update_shipyard()`, `_complete_ship_build()`, `show_shipyard()` | `SHIPYARD_METAL_RESERVE`, `SLOT_EXPAND_COST`, `SHIPYARD_EXPAND_BATCH_SIZE`, `BASE_BUILD_TIME_STEPS` |
| Lab specialization | `world["lab_roles"]`, `world["multipliers"]` | `update_lab_specialization()`, `handle_build_lab()`, `show_labs()` | `LAB_BUILD_COST`, `LAB_TICK_INTERVAL_STEPS`, `LAB_TICK_MAGNITUDE`, `LAB_TICK_FLOOR` |
| Directorate Penal Code | `world["penal_code"]`, `world["penal_records"]` | `handle_charge()`, `handle_confirm_servitor()`, `show_docket()` | Articles/tiers are edited in `PenalCode.default_code()` in `src/penal_code.py`, not `main.py` |

## Planned next

| System | First small goal |
|---|---|
| Alerts | Report low supplies and stalled production clearly |
| Pauseable real time | Replace manual-only advancement after manual steps are stable |
| Research economy | Let the player build a second lab or hire/train scientists |

## Future design notes

| System | Document |
|---|---|
| Research | `research.md` |
| Directorate Penal Code | `penal-code.md` |
| Lab specialization | `lab-specialization.md` |
| Shipyard slot expansion | `shipyard.md` |
| Ship design (MK progression) | `ship-design.md` |
| Salvage | `salvage.md` |
| Hive cities, nomadic fleets, Dyson projects | `megastructures.md` |

## Rule for adding a system

Before coding a new system, write:

1. Its purpose
2. Its smallest possible first version
3. What it explicitly does not include yet
4. A success condition you can test
5. Which existing systems it depends on

If the smallest version still feels huge, reduce it again.
