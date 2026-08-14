# Game Systems Index

This directory contains short design notes. Documentation is where large ideas live safely before they become code.

## Current implementation

| System | Status | Main code |
|---|---|---|
| Manual time steps | Implemented | `src/main.py` |
| Earth and Mars stockpiles | Implemented | `src/main.py` |
| Mars forge-world production | Implemented, minimal | `src/main.py` |
| Command loop | Implemented | `src/main.py` |

## Planned next

| System | First small goal |
|---|---|
| Freight logistics | Add CSV Meridian and a single cargo order |
| Alerts | Report low supplies and stalled production clearly |
| Research | Add one progress track and one small completed technology |
| Pauseable real time | Replace manual-only advancement after manual steps are stable |

## Future design notes

| System | Document |
|---|---|
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
