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
| Directorate Penal Code | Implemented (standalone module, not yet wired into `main.py`) | `src/penal_code.py`, see `penal-code.md` |
| Lab specialization (fixed vs. flexible labs) | Implemented (standalone module, not yet wired into `main.py`) | `src/research/lab_specialization.py`, see `lab-specialization.md` |
| Shipyard slot expansion and no-idle rotation | Implemented (standalone module, not yet wired into `main.py`) | `src/shipyard.py`, see `shipyard.md` |
| Ship design (MK progression and retirement) | Implemented (standalone module, not yet wired into `main.py`) | `src/ship_design.py`, see `ship-design.md` |

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
