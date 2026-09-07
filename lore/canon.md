# Canon Log

The chronological narrative record, as it comes in from the Perplexity
CYOA thread. Append new entries at the bottom under a dated/cycle
heading — don't rewrite earlier entries; if something here turns out to
be wrong or superseded, add a note at the point it changed rather than
editing history away.

State through roughly cycle 29 is already reflected directly in the game
code (`src/main.py`'s cycle sync, Command Structure, Standing Orders,
Directorate Code, colony system — see the project brief for the full
list). This file starts capturing narrative material from cycle 29
onward, as it's synced in.

---

## ⚠ Sync status: Cycles 0–3 only — Cycles 4–29 not yet synced (2026-09-03)

Perplexity's own narrative log confirms the campaign's canonical state is
**Cycle 29** (last updated 2026-09-01). What's synced below is only the
founding era, Cycles 0–3 — Perplexity's own extraction of the fuller log
was truncated partway through Cycle 20, so a complete Cycle 0–29 recap
isn't available yet. Ryan needs to paste Cycles 20–29 (or the full
current log) to Perplexity to get the rest; once that comes back, sync
it in the same way and this notice can come down.

**One retcon flagged by Perplexity itself, not yet reconciled:** a later
revision changes the definition of a cycle from one month to one Earth
day, and — per Perplexity's own account — the underlying production/
consumption numbers were **not** rescaled to match. That means the
"Cycle = one month" scope note directly below is the *original* framing,
already superseded narrative-side, but not resolved. See `gaps.md` for
the full note — this needs a decision, not a silent pick.

Known headline events from Cycles 4–29, mentioned in passing but not yet
logged in full detail here:
- Mars's salvage operation recovered three non-human hull fragments from
  the Cycle-2 wreck; research expanded into strip-mining and
  robotic/servitor labor.
- Mars gained a perimeter defense grid, an operational shipyard, a
  second freighter (**CSV Concord**), and a first dedicated combat
  vessel (**LWS Vigilant**).
- The "Cycle 16 Forge Stall" exhausted Mars's support reserves and
  halted production; the Grand Director responded by assigning both
  Meridian and Concord permanently to a continuous Earth–Mars supply
  circuit (20 units/cycle).
- The Directorate later formalized the Penal Code under the Directorate
  Code (doctrine "Innocence Proves Nothing," Toil/Penal Legion
  sentencing) — this part is already independently confirmed against
  the code in `docs/systems/penal-code.md`.

---

## Founding Era / Setup

*(Source: Perplexity CYOA `log.md`, pasted 2026-09-03. A cycle equals
one month per this original framing — see the sync-status note above for
the later, unreconciled revision.)*

Humanity has been unified under the Directorate, with the Grand Director
holding its supreme seat. The founding-era state centers on Earth and
Mars: Earth possesses a separate terrestrial economy supporting its 9.1
billion inhabitants, while the tracked "support supply" stockpile is an
off-world logistics reserve. Mars begins as a fragile industrial colony
dependent on imported support supplies, producing raw and refined metal
but lacking mature defenses and shipbuilding capacity. Earth-to-Mars
one-way travel is fixed at three cycles.

**Named entities and terms established here:**
- **Directorate** — humanity's unified sovereign authority.
- **Grand Director** — supreme seat of the ten-seat Directorate.
- **Earth** — Directorate core world and source of the off-world
  logistics reserve.
- **Mars** — industrial colony and developing shipbuilding center.
- **Cycle** — one month of in-world time (see sync-status note above).
- **Support supply unit** — ~40 tonnes of standardized rations,
  life-support media, medical stock, fuel cells, and spares; sufficient
  for ~125 personnel for one cycle.
- **Asterion Foundry** — the game/playthrough setting and the
  Directorate's founding-era campaign context.

**Revision noted in the source itself:** the meaning/scale of "support
supply" was only clarified in Cycle 3 — it's not Earth's total food
supply, but a dedicated off-world reserve.

## Cycle 0 — The Founding

The Directorate is chartered on Earth and the Grand Director is
installed. Forge-Marshal-designate Halvorsen warns that Mars has only
about six cycles of support remaining under the official ledger. The CSV
Meridian, humanity's first freighter, is prepared in Earth orbit. Rather
than commit a full shipment, the Grand Director orders a partial load of
75 support units and sends Quartermaster inspector Okoye aboard to audit
Mars's actual inventories, consumption, and industrial output. Earth's
tracked reserve falls from 500 to 425 units. Okoye is ordered to send her
findings back by courier drone before the Meridian returns.

**Named entities:** Forge-Marshal-designate Halvorsen (Mars's senior
industrial authority), CSV Meridian (humanity's first, and at this
point only, freighter), Okoye (Quartermaster inspector), Quartermaster
(the logistical authority Okoye is assigned from), Forge-Marshal (title
associated with Mars's industrial command).

## Cycle 1 — Transit Begins

The Meridian begins its three-cycle burn to Mars with its partial relief
cargo and Okoye aboard. Mars consumes another ten support units (100 to
90), while its official extraction and refining process continues.

**Named entities:** Earth–Mars corridor (the established three-cycle
transit route), Mars industrial ledger (Halvorsen's reported account of
support consumption and metal production).

## Cycle 2 — The Anomaly

Mars's support reserve falls to 80. Midway through the Earth–Mars
transit corridor, the Meridian detects an irregular heat-and-power
signature that doesn't correspond to known debris or wreckage. The
captain escalates the contact to the Grand Director rather than acting
independently.

**Named entities:** the anomaly/contact (an unidentified powered object
at the Cycle-2 waypoint), Cycle-2 waypoint, the Meridian's captain
(unnamed).

## Cycle 2 — Weapons Live

The Grand Director orders the Meridian armed and directs it to treat the
contact as hostile. The crew reroutes power to two point-defense
autocannons and transmits a single demand for identification. The
contact doesn't answer, reveals weapon ports, and is fired upon first.
The Meridian disables it by striking its engine section: the drive core
overloads, the hull ruptures, and the vessel is left dead and venting in
the corridor. One escape pod breaks away into deep space before it can
be intercepted. The wreck remains at the waypoint for later salvage.

**Named entities:** point-defense autocannons (the Meridian's two
improvised weapons), the crippled cutter / Cycle-2 wreck, escape pod,
standing salvage doctrine (Directorate practice of recovering material,
components, and intelligence from wrecks).

**Retcon (flagged in the source itself):** this event was initially
described as an encounter with an unaffiliated human holdout crew. That
premise was explicitly retconned in Cycle 3 — because humanity is fully
unified under the Directorate, the vessel is now established as being of
confirmed **non-human** origin. Its species, polity, purpose, and
destination remain unknown.

## Cycle 3 — Arrival and Audit

The Meridian completes its transit and delivers its 75-unit cargo to
Mars. After the cycle's normal burn and production tick, Mars's support
stock rises to 145. Okoye's advance audit confirms Halvorsen's warning
was broadly accurate, but exposes an unreported problem: 180 unlogged
colonists have been folded into Mars's work gangs, raising real
life-support consumption ~15% above the official model. Mars's apparent
buffer is materially shorter than the ledger indicates.

**Named entities:** the 180 unlogged colonists, Mars work gangs (later
formalized into official records), courier drone.

## Cycle 3 — The Reprimand and Ledger

Rather than stage a public punishment, the Grand Director confronts
Halvorsen directly: truthful reporting is required because logistics
failures cost lives. Halvorsen gets a final warning and is made
responsible for correcting what she concealed. The Grand Director
demands a full Directorate asset ledger, formally inducts the 180 hidden
workers, orders Mars's industrial capacity expanded, accelerates the
incomplete shipyard, secures the Earth–Mars route with patrol cutters,
and dispatches a salvage team to the Cycle-2 wreck.

**Named entities:** full Directorate asset ledger, PC Ward / PC Sentinel
/ PC Bastion (patrol cutters — Ward escorts the corridor, Sentinel and
Bastion held on alert at Earth), Mars extraction rigs (expanding by
three), second refinery module, Mars shipyard (fast-tracked toward a
second freighter, later light warships), salvage team.

**Established targets:** production ramp from 15→22 raw metal/cycle and
8→14 refined metal/cycle, projected complete Cycle 6; shipyard
acceleration projected complete Cycle 10; salvage assessment projected
Cycle 5. Fleet at this point: Meridian + three inherited patrol cutters;
Mars has no ground defenses yet.

## Cycle 3 — Scale and Sovereignty Revision

The Grand Director corrects several early assumptions. Support supplies
get a fixed physical scale (see the Founding Era entry above); Earth
begins continuously manufacturing off-world support stock; all legacy
national garrisons are placed directly under the Grand Director's
command. The Navy remains at four ships despite Earth's population,
because shipyard/drydock capacity — not population — is the real
bottleneck. The human-holdout explanation for the Cycle-2 engagement is
formally replaced with the Directorate's first confirmed hostile xenos
contact; salvage and study are the only path to understanding it — no
immediate alien tech, answers, or upgrades are gained.

**Named entities:** Logistics Corps (Earth-based, 500 support units/cycle
from Cycle 4 on), legacy national garrisons (now subordinated to the
Grand Director), Navy (established here at exactly four ships), First
Xenos Contact (corrected designation for the Cycle-2 encounter),
Xenology (the research field that will study non-human materials and
contact).

**Revisions noted in the source itself:**
- Support-scale fixed at ~40 tonnes / ~125 personnel / one cycle.
- Earth's reserve is no longer static-and-depleting-only — the
  Logistics Corps produces 500 units/cycle from Cycle 4 onward.
- No independent human authority exists anywhere in the empire (closes
  off the earlier holdout-crew possibility).
- The Cycle-2 cutter is confirmed non-human (see the retcon note above).

## Cycle 3 — Research Charter and Directorate Code

The Grand Director formalizes both a state research program and the
Directorate's legal-operational code. Current economic rates are kept as
deliberately generous founding-era values — a possible future reduction
toward more sustainable rates is discussed but not scheduled or
numerically defined. The Research Collegium is chartered with five
fields of study, but has no active laboratory, no research points, and
no per-cycle generation yet. The Xenology path is explicitly locked
behind completion of the salvage operation.

**Named entities:** Research Collegium (the High Savant's institution),
High Savant, Materials & Industry / Logistics & Propulsion / Habitat &
Life Support / Military & Defense / Xenology (the five Collegium
branches), Directorate Code (five-article governing code), Bureau
(enforces the Code, under the Provost-General), Provost-General, Vigil
(extreme internal-security body answering privately to the Grand
Director).

**Directorate Code articles:**
1. **Sovereignty** — no independent human authority exists anywhere in
   the empire.
2. **Honest Reporting** — concealment or falsification of figures is
   punishable.
3. **Requisition Authority** — resources and production are Directorate
   property.
4. **Chain of Command** — ground forces report to the Grand Director
   through the Marshal-General.
5. **Xenos Contact Protocol** — non-human contacts or materials must be
   reported immediately to the Bureau and the Vigil.

**Note:** these five article names weren't previously recorded in
`glossary.md` — see the update there. `docs/systems/penal-code.md`
already documents the Penal Code's five *criminal* articles (Desertion
of Post, Sabotage of Directorate Property, Insubordination Under
Command, Hoarding of Strategic Supply, Treason Against the Directorate),
which is a distinct, already-implemented layer that enforces some of
these five constitutional principles — see `gaps.md` for how they line
up.

## Cycle 3 — Institutional Expansion

The Grand Director orders the first Mars Research Lab (projected
complete Cycle 5). A standing infrastructure policy is enacted: surplus
resources get used, not stored — first to correct known bottlenecks,
then defenses, then broad expansion — capped at one new small project
per cycle, and only project types already established in the record.
Three institutions are formally established: discipline, logistics
administration, and empire-wide reporting accuracy.

**Named entities:** Mars Research Lab (Cycle 5 ETA), Discipline Corps
(embedded Legion discipline/loyalty officers, field authority over
desertion/cowardice/treason, escalates treason to the Vigil), Quartermaster
Corps (standing logistics bureau administering freighter networks and
Requisition Authority), Chancellery (empire-wide census/records,
reconciles reported figures to reality), Legions (Directorate ground-force
formation), Marshal-General (routine Discipline Corps authority).

**Established infrastructure priorities:** 1) correct bottlenecks
(currently Mars shipyard/drydock capacity, lack of Mars ground defenses),
2) defensive construction, 3) general expansion (rigs, refineries,
labs, habitat).

## Cycle 3 — Equipment and Asset Upgrade Doctrine

A second standing order: once refined metal and research points allow,
the Directorate will upgrade existing equipment and assets empire-wide —
ship weapons, Legion gear, industrial tools, personal administrative
equipment. Nothing is funded yet — available refined metal is committed
to the Research Lab and industrial ramp, and research generation hasn't
started.

**Named entities:** equipment standard tier (empire-wide quality
tracking), Tier 1: Standard Issue (current tier).

**Standing upgrade priorities:** 1) frontline/combat equipment, 2)
industrial equipment, 3) administrative/personal equipment. Standards
only increase when an upgrade is actually funded — none has been yet.

---

## Doctrine — The Decree of Human Continuance (not cycle-tagged)

*(Source: Perplexity design chat "lets remove the religious aspect of
this. instead.md", pasted/synced 2026-09-04. Archived in full at
`lore/design/religion-removal-retcon.md`. Not cycle-tagged in the
source — treat as a foundational doctrine layered onto the setting
rather than a dated in-story event.)*

An earlier design draft (`lore/design/command-and-rank-structure-v4.md`)
had built the Directorate around a state faith — the Ember Faith, headed
by a First Flamekeeper Council seat, with the Sisters of the Ember as
its militant order, and an optional path for the Grand Director to
ascend as the divine "Undying Flame." **This was fully retconned out.**

Ryan's own framing for the change: the Directorate isn't anti-spiritual
for its own sake — the point is that "humanity put our faith into
something tangible and real. Put it into us as a species and what we
can become, then through that belief we will make it possible."

The Directorate's founding law is now **the Decree of Human
Continuance**: no faith, priesthood, oracle, cult, or claimed divinity
stands above human conscience, evidence, or law made for human
continuance. The underlying civic ideology is called **Human Ascendancy**.
State mottos: "No salvation is coming. Build it." / "What humanity
requires, humanity must make."

**What replaced the Ember Faith:**
- Council seat: **First Steward of Continuance** (replaces The First
  Flamekeeper) — this matches the seat name already used throughout the
  existing project brief and code-facing docs.
- Branch H: **The Office of Human Continuance** (replaces The Ember
  Faith) — a civic institution for education, historical memory,
  citizenship, memorial practice, and cultural continuity, not a church.
- **Continuance Halls** replace shrines/cathedrals as each colony's
  civic building (archive + school + museum + assembly space + memorial
  + emergency-coordination site).
- The seal's flame motif survives as **the Human Spark** — humanity's
  own capacity to understand, build, remember, and continue, belonging
  to the species, protected by no god, not eternal on its own.
- New constitutional rule: no citizen, office, bloodline, machine, or
  institution may be named the embodiment of Humanity — forecloses the
  Grand Director sliding into a personality cult even without a state
  faith.
- The Vigil's mandate reworked: "heresy against the Faith" becomes
  investigating religious revivalism/cult activity as an ongoing
  counter-insurgency concern, alongside its existing remit.

**Deliberately not closed off:** religion can still emerge later in the
story — on isolated colonies, after catastrophe, around something
genuinely unexplained — and the Directorate's response to it is meant
to be contested (the Collegium wants to test it, the Chancellery wants
to regulate it, the Bureau treats it as a security risk, the Vigil
judges it against the decree), not a simple villain/hero read either
way. A **"Continuance Test"** (7 questions) is proposed for judging any
future such movement — see the full archive for the questions.

## Cycle 29 — Directorate Council Named and Activated

*(Source: Perplexity design chat "Do i have a counsil_.md", synced
2026-09-04. Confirmed added to the real canonical state per Ryan — "the
names add.")*

The full ten-seat Council was given named officers and standing
mandates as of Cycle 29:

| Seat | Officer | Standing mandate (summary) |
|---|---|---|
| First Minister | **Ines Halvard** | Earth civil mobilization, census coordination, recruitment, emergency continuity |
| Forge-Marshal | **Halvorsen** | Mars output, verified ledgers, shipyard/industrial expansion (still under standing reprimand from the Cycle-3 concealment incident) |
| High Savant | **Dr. Yuen Osei** | Collegium programs, automation research, xenos-material containment and analysis |
| Grand Admiral | **Reyes Ferrant** | Fleet doctrine ("Operation Iron Lifeline" — corridor defense), convoy protection, patrol readiness |
| Quartermaster-General | **Bertrand Okoye** — the same Okoye who audited Mars back in Cycle 0, now promoted after exposing Halvorsen's concealment | Supply-route audits, Mars strategic reserve doctrine, cargo-control |
| Colonial Warden | **Priya Solanke** | First-colony survey program; no second colony founded yet, currently prep-only |
| Marshal-General | **Dietrik Voss** | Legion formation (1st Directorate Legion), Mars garrison, Discipline Corps |
| First Steward of Continuance | *(not named in this source — the source chat still calls this seat "The First Flamekeeper," vacant. See the open question in `gaps.md`.)* | — |
| Chancellor-General | **Mireille Dubois** | Reconciliation audit, Directorate Status Ledger, anti-fraud reporting |
| Provost-General | **Casimir Thale** | Directorate Code enforcement, counter-sabotage, restricted-material vetting |

**Two bodies outside the Council table:** the **Director's Own**,
informally led by **Captain-of-the-Guard Mara Voskuijlen**, stays fixed
at the Grand Director's side with no active tasking beyond standing
watch. The **Vigil**, headed by unnamed First Seekers, has its first
live mandate: quietly shadowing the Collegium's xenos-hull analysis and
the escaped Cycle-2 pod's last known heading, per the Xenos Contact
Protocol.

**Concrete Cycle-29 baseline given in this source** (useful for
cross-checking against the actual game code's saved state, not yet
done): Earth support supply 13,165; Mars support supply 113; Mars raw
metal 225; Mars refined metal 362; Mars support consumption 10.2/cycle;
Earth production 500 support/cycle; Earth-to-Mars standing resupply
20/cycle; Mars strategic-reserve warning threshold set at 62 units (six
cycles of consumption). Mars industrial base: 7 extraction rigs, 2
refinery modules, 26 raw metal/cycle, 14 refined metal/cycle, shipyard
upgrade ETA Cycle 25. Fleet: CSV Meridian, CSV Concord (second
freighter), PC Ward, PC Sentinel, PC Bastion, LWS Vigilant (first
dedicated light warship) — Meridian and Concord run the standing
Earth–Mars supply route, Ward and Vigilant escort it.

**Open thread noted in the source itself:** Provost Thale investigating
Halvorsen retroactively over the Cycle-3 concealment incident was
flagged as a possible first real Bureau/Marshal-General friction point —
a live fork, not a resolved outcome.

## Cycle 29 (continued) — Directorate Command Net

*(Source: same chat as above. Status per Ryan: the named roster is
confirmed added to canon; the Command Net's *purpose* is confirmed —
Ryan's own words: "the Command Net was/is the system that I have to
have less micro-managing, I intended it to be where the council members
would actually do their jobs and not be just names/titles" — but
whether this specific design was itself ever pasted into and saved by
the actual story-running Perplexity session is unconfirmed. Treat the
doctrine/intent as settled, the exact mechanical spec below as a strong
draft rather than verified-integrated narrative fact.)*

The Grand Director activates the **Directorate Command Net (DCN)** — not
an independent AI, not a new authority above the Council, but a
hardened network of ledgers, sensor feeds, scheduling tools, and
human-supervised expert systems that lets each Council seat's standing
mandate actually run day-to-day instead of sitting as a name on a chart.
Founding doctrine: **"Routine by System, Exception by Command."**

Data domains: Forge Control, Fleet Control, the Quartermaster Ledger,
the Chancellery Ledger, Security Control, and the Research Archive.

The DCN may automatically: schedule routine maintenance, verify cargo
manifests/seals/deliveries, rotate defensive escorts and patrols inside
the Earth–Mars security envelope, run drills/guard rotations/training,
staff research under existing rules, reconcile ledgers and flag
variances, and apply routine access-control/containment lockdowns. It
may **not**: spend strategic reserves, start or alter construction,
send ships beyond the Earth–Mars envelope, launch exploration/
diplomacy/war, activate a state faith, deploy xenos technology, or
impose senior sentencing — all of that stays the Grand Director's
exclusive call.

**Automatic escalation triggers set up:** Mars support reserve
approaching/below the 62-unit warning threshold; industrial output
shortfalls; escort-readiness gaps; unidentified sensor contacts;
restricted-lab/xenos-containment anomalies; Chancellery-detected ledger
variances; completed research awaiting a deployment decision. Each
routes to the relevant Council officer, then to the Grand Director if it
crosses into a reserved decision.

**Design idea worth flagging, not building yet:** this "Routine by
System, Exception by Command" framing could be a genuinely good model
for the actual game code's Standing Orders system too — right now
standing orders are simple threshold-based automations; this gives them
an in-universe institutional shape (which department "owns" which
automation, what escalates to a report vs. a real decision) without
requiring new mechanics. Purely a note for whenever Ryan wants to build
toward it, not a suggestion to implement now.
