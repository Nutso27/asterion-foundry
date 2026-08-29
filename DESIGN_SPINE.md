# Asterion Foundry — Design Spine

**Status:** Private learning prototype

## One-sentence pitch

A pausable real-time space-empire simulation where an industrial command state manufactures humanity's first interstellar civilization: building forge worlds, supply networks, named fleets, colonies, and eventually civilization-scale structures.

## Founding premise

Humanity does not inherit a lost galaxy-spanning empire. It begins in Sol and constructs one.

Earth is the political center, primary population reserve, and source of essential support goods. Mars is the first forge world: a purpose-built industrial, research, and shipbuilding center. Mars transforms local minerals and imported necessities into the ships, construction modules, tools, and knowledge required to create new colonies.

The player is the supreme government and military command authority. The tone is dark, gothic, industrial, and unforgiving. The player commands a vast system rather than serving as a heroic individual; people and ships are valuable assets with roles in a growing machine.

## Design pillars

1. **Continuous time, controlled by pause.** The game ultimately runs continuously. The player can pause to inspect reports and give orders. Development begins with manual simulation steps because they are easier to build and understand.
2. **Mars is the first forge world.** It is the main industrial and research heart, not a simple dependent mine.
3. **Industry enables expansion and war.** Resources, power, workers, factories, shipyards, construction fleets, and secure transport create capability.
4. **Logistics is physical.** Strategic resources travel by freight, tanker, convoy, transport, and later nomadic fleet.
5. **Ships are individual operational assets.** Each ship has a name, class, location, status, fuel, cargo, condition, and strategic role. Deep individual crew simulation is not required for the early game.
6. **Command depth is adjustable.** Direct player orders coexist with transparent automation policies.
7. **Colonies are constructed.** The player surveys, supplies, builds, protects, and specializes new worlds rather than reclaiming old human colonies.
8. **Combat has strategic roots.** Supply, repairs, fuel, ammunition, industry, and battlefield control matter. Start abstract; add tactical command later.
9. **Loss creates stories and opportunity.** Destroyed ships leave wrecks that may yield materials, components, data, survivors, hazards, and research leads.
10. **Scale is earned.** Hive worlds and Dyson-scale structures are late-game results of massive industrial throughput and sustained logistics, not menu purchases.
11. **Systems explain themselves.** Alerts must state what happened, why it happened, and what the player can do.

## Starting setting

### Earth

- Political and command capital
- Main population center
- Source of initial support supplies
- Early administrative and strategic reserve
- Future role: civilian core, recruitment, food/life-support base, policy center

### Mars

- Humanity's first forge world
- Heavy industry, refining, fabrication, and early shipbuilding foundation
- Research complex operated by the provisional technical institution, **The Asterion Collegium**
- Needs strategic support goods in the first prototype, creating the first logistics problem

### The Asterion Collegium

A Mars-based research-industrial institution that maintains technical archives, laboratories, prototype facilities, and fabrication doctrine. It is a working original name and can be changed later. Internal politics are a later system; initially it exists to make research and advanced industry meaningful.

## Hybrid travel model

- Civilian freight primarily uses established transit corridors or star-lanes: efficient, predictable, and protectable.
- Military ships can use those corridors or conduct direct open-space travel.
- Open-space travel uses more fuel, takes longer, and supports scouting, interception, flanking, or access to undeveloped targets.
- The first prototype uses a simple Earth–Mars route with travel time and no graphics.

## Initial economy

### First prototype resources

| Resource | Initial producer | Initial user | Purpose |
|---|---|---|---|
| Support supplies | Earth | Mars forge complexes | Keeps the Martian workforce and industrial systems functioning |
| Raw metal | Mars | Mars forge complexes | Input for refining and construction |
| Refined metal | Mars | Future shipyards and construction | First strategic industrial output |

### First loop

1. Earth holds support supplies.
2. Mars consumes support supplies to run its forge complexes.
3. Mars extracts raw metal and refines a portion into refined metal.
4. Mars eventually needs resupply.
5. Lesson 02 adds the freighter CSV Meridian.
6. CSV Meridian will carry supplies from Earth to Mars and return industrial output to Earth orbit.
7. That output will enable the first colony expedition and later ship construction.

## Individual ships

### First named ship: CSV Meridian

The CSV Meridian is a civilian cargo freighter added in the next lesson. Its initial job is to establish the Earth–Mars supply chain.

### Ship data, gradually introduced

- Name
- Class
- Location and destination
- Current order
- Fuel and fuel capacity
- Cargo and cargo capacity
- Hull condition
- Travel progress or speed
- Operational status: idle, loading, traveling, unloading, repairing, disabled, destroyed

### Future military ship

A first escort, provisional name **ISV Indomitable**, can protect logistics routes later. Its purpose is operational: defense, escort, patrol, and force projection.

## Research

Research is a strategic investment, not an instant unlock. The Asterion Collegium generates research progress over time from staffed labs, offers a rotating weighted selection of live research options rather than one fixed tree, and allows gambling banked research points on an early breakthrough at real risk.

This is now fully designed, implemented, and wired into `src/main.py`'s command loop as the project's canonical research system — see `docs/systems/research.md` for the full design, `src/research/` for the code, and `src/research/data/technologies.json` for the starter set of 16 technologies across four lanes (Physics & Materials, Logistics & Industry, Biology & Colonization, Military Doctrine). Players use `research`, `invest`, and `pilot` in the terminal loop to view and spend Collegium research points.

## Salvage

Destroyed ships should create a persistent wreck field instead of disappearing completely.

### Future salvage sequence

```text
Ship destroyed
→ wreck field remains at location
→ player evaluates safety, ownership, and urgency
→ salvage ship is dispatched
→ recovery occurs over time
→ resources, components, data, survivors, or hazards are resolved
```

### Potential outcomes

- Hull scrap
- Reusable components
- Fuel and ammunition
- Data cores and intelligence
- Prototype technology fragments
- Survivors
- Dangerous reactor, munitions, or contamination events

Recovering unfamiliar technology creates a research lead, not an automatic unlock. A research project may need enough recovered fragments, research points, facilities, and time before it yields a technology or partial bonus.

See `docs/systems/salvage.md`.

## Colony creation and specialization

A colony is made through a chain, not created instantly:

```text
Survey target
→ establish outpost
→ supply workers, machines, power, and habitats
→ sustain the settlement
→ develop local extraction and industry
→ specialize the world
→ connect it to the wider imperial economy
```

Possible future specializations:

- Mining world
- Fuel world
- Forge world
- Research world
- Fortress world
- Depot/trade world
- Agri-world
- Civilian world
- Hive city or hive world

A world may change specialization as infrastructure and strategic priorities evolve.

## Scale systems

### Nomadic fleets

Mobile strategic groups that can serve as construction expeditions, mobile industry, naval logistics, evacuations, or frontier settlements. Treat a first-version nomadic fleet as a colony with engines: fuel, cargo, habitat integrity, repair capacity, industrial capacity, and mission.

### Hive cities and hive worlds

Cities and worlds transformed into extremely dense urban-industrial machines. They provide enormous population, recruitment, manufacturing, and research capacity, but require continuous massive inputs of food, water, power, maintenance, security, and transport.

### Dyson swarm and sphere

Start with modular orbital collector/factory segments around a star. Each segment requires materials, construction capacity, transport, protection, and upkeep. A Dyson sphere or near-complete stellar enclosure is a far-future completion project built from the same logistics and construction mechanics at immense scale.

See `docs/systems/megastructures.md`.

## Development order

1. Manual `advance` time step
2. Earth and Mars stockpiles
3. Mars production and consumption
4. CSV Meridian freight movement
5. First shortage and alert
6. Basic research progress
7. Pauseable real-time loop
8. Basic automation policy
9. Colony expedition and first outpost
10. World specialization
11. Wreck fields and self-salvage
12. Research leads from salvage
13. External threats and abstract fleet combat
14. Nomadic fleets
15. Hive cities/worlds
16. Dyson swarm, then Dyson-scale completion project

## Scope guardrails

Do not implement these in the first prototype:

- 3D graphics
- Multiplayer
- Tactical battles
- Ship interiors
- Individual crew simulation
- Aliens, rival empires, or diplomacy
- Internal politics
- Procedural galaxy generation
- Multiple star systems
- Full salvage system
- Hive worlds or Dyson structures

Every later feature should be the larger form of an earlier mechanic the player already understands.
