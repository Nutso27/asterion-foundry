# Salvage System — Future Design

**Status:** Documented only. Do not implement until basic ships, locations, cargo, and logistics work.

## Purpose

A destroyed ship should not vanish into nothing. It creates a wreck field that can become a source of materials, replacement components, intelligence, hazards, survivors, or research opportunities.

Salvage makes defeat costly without making every loss meaningless. It also makes holding a battlefield strategically important.

## Smallest possible version

```text
A ship is destroyed.
A wreck record appears at that location.
A salvage-capable ship spends time recovering refined metal.
The wreck's recoverable material decreases.
```

### Success condition

- Destroying a test ship creates one wreck.
- A salvage ship can recover a known amount of refined metal.
- The recovered material appears in a location stockpile.
- The wreck is removed when empty.

## Not in version one

- Enemy technology
- Tactical wreck fields
- Survivors
- Exploding reactors
- Traps or ambushes
- Multiple salvage teams
- Wreck ownership law
- Partial ship reconstruction

## Later outcomes

| Recovery type | Gameplay result |
|---|---|
| Hull scrap | Raw or refined material |
| Intact module | Repair part or reusable component |
| Fuel/ammunition | Recovered strategic supply, perhaps with risk |
| Data core | Research points or intelligence |
| Prototype fragment | Research lead, not instant technology |
| Survivors | Personnel recovery and later narrative/political effects |
| Hazard | Accident, contamination, explosion, or delay |

## Technology recovery

Salvaging unfamiliar equipment creates a research lead rather than an automatic unlock.

Example:

```text
Recovered item: Unknown beam-emitter fragments
Requirement: 15 fragments + 200 research points + advanced laboratory
Result: Experimental beam-array research becomes available
```

## Dependencies

- Named ships
- Ship destruction
- Locations or map coordinates
- Cargo and stockpiles
- Travel orders
- Basic research

## Possible branches

```text
feature/wreck-field-data
feature/salvage-ship-order
feature/salvage-material-recovery
feature/salvage-research-leads
feature/prototype-reverse-engineering
```
