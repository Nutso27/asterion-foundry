# Asterion Foundry — Full Codebase & Design Audit

**Date:** 2026-09-04
**Scope:** `src/`, `tests/`, `docs/`, `DESIGN_SPINE.md`, `README.md`, plus the two prior Cowork session summaries in the project, checked directly against the live repo on your machine (`C:\Users\rrp27\Documents\asterion-foundry`).
**Method:** Read every source and test file, ran the full test suite four times (unittest, since pytest couldn't be installed — no network access in this sandbox), traced the resource flow of every system by hand, and cross-checked the two prior session summaries' claims against what's actually committed.

This is long because you asked for "every way" and said not to hold back. It's organized worst-first: things that will actually hurt you, then structural/architecture issues, then smaller code-quality notes, then a concrete plan for the "systems talking to each other" question you asked directly.

---

## 0. Before anything else: Session 2's claimed work isn't in your repo

This is the most important thing in this report, and it's not a code-quality issue — it's a trust issue with the process itself.

`asterion-foundry-session2-summary.md` (in this project) describes three things as built, verified, and committed on `main` in a prior Cowork session:

1. Colonial Warden Council seat wired to live colony data (commit `c4a24d0`)
2. A full xenology research lane with evidence-gating (commit `562a02e`)
3. A fix for the flaky `test_mk_progression_stops_at_mark_v` test (commit `89964bb`), verified "30/30" clean runs

**None of these three things exist in the repo on your laptop.** I checked directly:

- `show_council()`'s `live_status` dict has exactly the same 5 wired seats the original brief described (`grand_admiral`, `quartermaster_general`, `forge_marshal`, `high_savant`, `provost_general`) — no `colonial_warden` entry.
- There is no `xenology` lane anywhere in `technologies.json`, `engine.py`, or `models.py`. `main.py` still literally says, in `handle_study_fragments()`'s docstring: *"that system has no xenology lane or evidence-gating mechanism yet."* `tests/test_research.py::test_exactly_four_lanes` still asserts 4 lanes, and there's no `EvidenceGatingTests` class anywhere.
- `tests/test_main_integration.py`'s `ShipDesignIntegrationTests.setUp()` does **not** strip dynamically-registered MK-successor nodes, which is exactly the fix the summary describes. I ran the full suite four times in a row to check, and it failed on run 4 with the identical error described in your original brief (`'Mark II' != 'Mark V'`) — the bug is still live.

The session 2 summary itself says the work was "committed locally in this session's workspace. **Not pushed to origin**" — so my best guess is that session ran in a different, ephemeral sandbox (not this laptop) and whatever it committed never made it here. That's a real gap in how these sessions hand off work to each other, separate from anything about your game's design.

**I'm not going to guess further — I'd rather ask you directly, see the question at the end.** Practically, treat the "what's built so far" list in the original brief (5-of-10 Council seats, no xenology lane, the flaky test still flaky) as the accurate current state, not the session 2 summary.

---

## 1. The single biggest gameplay bug: Earth's economy has no faucet, only a drain

This is the most important finding in the actual code (as opposed to the process issue above).

`update_earth()` is a no-op:

```python
def update_earth():
    """Run one simple Earth update.
    Earth has no production rule yet. This function exists to show that
    every location can have its own update rules as the project grows.
    """
    earth = world["locations"]["earth"]
    _ = earth
    print("Earth command reports stable reserves. No new production this step.")
```

Meanwhile, every draw on `earth["support_supplies"]` — CSV Meridian's cargo loads (up to 200/trip) and outpost founding (50/outpost) — only ever subtracts. Nothing in the entire codebase ever adds to it. I checked every `+=`/`-=` site by hand.

Starting value is 13,165.0. CSV Meridian round-trips roughly every 4 `advance` steps and can move up to 200 support supplies per trip, so **Earth runs dry in roughly 260-300 `advance` calls** even with zero colonies founded — sooner if you found outposts. When it hits zero: Meridian departs with 0 cargo, Mars can't sustain its own consumption (`cost` in `update_mars()`), the forge complex goes idle ("ALERT: Mars lacks support supplies"), refined metal production stops, and that cascades into the shipyard, standing orders, and colony founding all stalling — permanently, with no recovery mechanic, because nothing regenerates Earth's supply.

There's no in-game warning about this (no "N cycles of Earth reserves remaining" anywhere in `show_status()`), and nothing in `DESIGN_SPINE.md` frames this as an intended fail-state — it reads like an acknowledged-but-unaddressed gap ("Earth has no production rule yet" is the actual comment in the code). You haven't hit this yet — there's no `state.json` on your machine, so no save exists — but if you've been advancing the terminal session a lot without saving, you may be closer to it than you think.

**This should be priority #1**, above any of the "systems talking to each other" work below, because it's a ticking clock on the whole simulation.

---

## 2. The shipyard and the fleet cap don't know about each other

`Shipyard.target_minimum` defaults to **100 slots**. `FLEET_TARGET` in `main.py` caps the fleet at **6 freighters + 10 warships = 16 hulls, total, ever**. Once fleet counts hit those caps, `update_shipyard()`'s own logic explicitly idles any slot whose only allowed categories are capped (`if not allowed: continue`).

But slot *expansion* (step 1 of `update_shipyard()`) never checks the fleet cap at all — it just keeps growing toward 100 slots as long as Mars has spare refined metal. So the shipyard will happily spend metal building up to 84 slots that can mathematically never build anything, forever, competing for the same refined-metal pool that funds equipment upgrades, colony founding, and Earth's metal deliveries. This is real, ongoing resource waste baked into the current numbers, and it'll get worse the longer you play.

**Fix is small**: either lower `Shipyard.target_minimum` to something that makes sense against `FLEET_TARGET` (e.g., `sum(FLEET_TARGET.values())` plus a small buffer), or make `expand()` aware of a fleet-derived cap instead of a flat 100. This is also a good first example of the "shared source of truth" pattern in section 6 below.

---

## 3. Only one of your two starting freighters (and none of the ones you build) actually do anything

`update_csv_meridian()` is hardcoded to `world["ships"]["csv_meridian"]`. **CSV Concord** — your second starting freighter, already sitting `idle_at_mars` in the initial world state — has never run a supply route, and never will, because nothing calls its update logic. Every freighter the shipyard subsequently builds (up to the fleet cap of 6) is spawned `idle_at_mars` and also never joins the loop. The function's own docstring already flags this as a known gap:

> "Freighters the shipyard builds later... do not join this loop automatically... Generalizing this function into a loop over every ship with `class_id == "freighter"` is the natural next step... intentionally left as a customization point."

Functionally, right now, **building more freighters does nothing for you.** You have a shipyard that will build up to 6 freighters and a fleet-status screen that'll proudly show them "in service," but 5 of those 6 just sit at Mars forever. This is the clearest concrete example of "systems not talking to each other" in the whole codebase, and it's also probably the single most satisfying gap to close, because closing it makes the shipyard → fleet → economy loop actually connect for the first time.

---

## 4. Colony output goes into a resource pool nobody reads

Established colonies with a mechanical specialization (`mining_world`, `forge_world`, `research_world`, `agri_world`, `civilian_world`) accumulate output into `colony["raw_metal"]`, `colony["refined_metal"]`, `colony["support_supplies"]`, `colony["population"]`. I grepped every read site in the codebase: the **only** place any of these fields is ever read back is `show_colonies()`, printing them to the screen.

Nothing moves colony output into Mars's stockpile, Earth's stockpile, or the freighter network. Nothing spends colony population on anything. The one exception is `research_world`, whose effect writes straight into `state.rp_stockpile[lane]` — bypassing the entire lab/scientist RP-generation pipeline in `research/engine.py` (i.e., there are now two unrelated code paths that add RP to the same field, one going through `generate_rp()`'s diminishing-returns math and one that doesn't).

So right now, colonies are a fully cosmetic side-system: you can survey, found, and specialize a world, watch its numbers tick up in `colonies`, and it changes literally nothing else in the game. This is your second concrete "systems don't talk to each other" example, and it's the natural next thing to wire up after freighters (section 3) since it needs the same kind of connective work: give colony output somewhere real to go (probably: colonies deliver into Mars's or Earth's stockpiles via a freighter-style logistics tick, or a colony gets picked up by the same freighter-generalization work).

---

## 5. The audit "gamble" isn't actually a gamble

`handle_audit(seat_id)` can be called as many times as you want, with no cost, no cooldown, and no requirement to `advance` between attempts. Each call rolls a flat 70% (`AUDIT_SUCCESS_CHANCE`) chance to catch an active concealment; on failure, nothing is lost or changed — `active_concealment` stays exactly as it was, so you can just call `audit forge_marshal` again immediately. With 70% odds and free retries, the actual chance of eventually catching a concealment before your next `advance` is effectively 100% minus a vanishingly small tail. The "risk" framing in the code and docs (this is explicitly built as "a real gamble," per `show_audit()`'s docstring) doesn't hold up against how the command loop actually lets you use it.

Small fix: either cost something per attempt (a scarce resource, or consumes the current `advance` step), or add a cooldown after a failed attempt. Either restores the intended tension cheaply.

---

## 6. Foundation: why the systems don't talk to each other, and how to fix it structurally

You specifically asked how to make the systems talk to each other and expand as the game grows. Here's the actual mechanical reason they mostly don't right now, and what I'd change.

**Current shape.** `src/main.py` is 1,834 lines, 42 top-level functions, and a single global `world` dict that's read or written directly at 162 call sites across the file. There's real credit due here — the "three-layer pattern" documented at the top of `main.py` (data module → world-state key → `update_*`/`show_*`/`handle_*` glue functions) is a genuinely good discipline, and `src/research/`, `ship_design.py`, `shipyard.py`, and `penal_code.py` all follow it cleanly as small, well-tested, dependency-free modules. That part of the foundation is solid — keep doing it for every new subsystem.

**Where it breaks down** is that the *glue* layer in `main.py` is where every cross-system connection has to live, and right now those connections are ad hoc: each `update_*()` function reaches directly into whatever other systems' `world[...]` keys it needs, in whatever order `advance_world()` happens to call them in. There's no shared interface for "system A hands system B some resource" — it's all direct dict mutation, which is exactly why freighters (§3) and colonies (§4) ended up producing output with nowhere defined to go: there was no *contract* for "here's how a producer connects to a consumer," so it was easy to build the producer half and stop.

**Concrete changes I'd make, roughly in order:**

1. **Give resources one shared home instead of duplicating fields per-owner.** Right now `earth`, `mars`, and every `colony` each have their own separate `support_supplies`/`raw_metal`/`refined_metal` fields, and every system that wants to move resources between locations (the freighter loop, colony founding) writes bespoke code to do it. A small `transfer_resource(from_location, to_location, resource, amount)` helper — or even just a `world["stockpiles"][location_id][resource]` structure instead of ad hoc dict shapes — would let any future system (a second freighter route, colony output, a trade mechanic) move resources through one audited path instead of everyone hand-rolling their own `+=`/`-=` pairs. This alone would have made §3 and §4 nearly free to wire up correctly the first time.

2. **Generalize the freighter loop now, not later.** This is called out as the deliberate next step in the code's own docstring — do it. A `for ship in world["ships"].values(): if ship["class_id"] == "freighter": update_freighter(ship)` loop (with each ship tracking its own route/cargo) fixes §3 directly and is also the foundation for anything DESIGN_SPINE.md's dev order calls for later (nomadic fleets, a second colony's supply route, multiple star systems).

3. **Add a light event/notification log instead of only `print()`.** Right now every `update_*()` function prints directly, in the middle of business logic, and that's the *only* record of what happened — if you're not watching the terminal scroll by when you `advance`, an alert (Mars stalling, a concealment discovered, a colony's supply running low) is gone. A simple `world["events"].append({"cycle": ..., "text": ...})` that `advance_world()` also prints from, plus an `events` command to review the last N, would (a) decouple simulation logic from presentation — useful the moment you want a different UI later — and (b) give you a persistent trail to actually notice things like "Earth is at 8% reserves" before it's too late.

4. **Turn `advance_world()`'s fixed call order into something coordinated, not accidental.** Right now cross-system ordering effects are implicit — e.g., `update_colonies()` runs before `update_csv_meridian()`, so a colony founded this exact step can't yet benefit from anything the freighter delivers this step. That's probably fine today, but it's exactly the kind of thing that becomes a silent bug once colonies and freighters are actually connected (§3+§4 done together). Once you wire those two up, write down (in the module docstring, where the "WHERE EVERYTHING LIVES" table already lives) *why* the order is what it is, the same way you already do for constants — you clearly already have the habit of documenting "why this number," extend it to "why this order."

5. **Move the constants that define cross-system relationships to one place.** `FLEET_TARGET` (main.py) and `Shipyard.target_minimum` (shipyard.py) are two numbers that *should* agree with each other and currently don't (§2) because they're defined in two different files with no link between them. As you add more of these relationships (colony specialization caps vs. resource capacity, lab count vs. RP lane demand), a small `config.py` or a "derived constants" section at the top of `main.py` that computes dependent numbers from their sources (`SHIPYARD_TARGET = sum(FLEET_TARGET.values()) + BUFFER` instead of a bare `100`) prevents this class of drift permanently, and it's a very cheap habit to start now while there are only a couple of these relationships to fix.

6. **Split `main.py` once it crosses ~2,500-3,000 lines, along the boundary that already exists in your docstring's system table.** You're not there yet (1,834 lines), and I would *not* refactor this preemptively — but the table at the top of the file describing "data module / world key / constants / commands" per system is already, in effect, a map of where the file wants to be split (`main_council.py`, `main_colonies.py`, `main_shipyard.py`, etc., each importing a shared `world` module). When you do split it, that table is your guide; you won't need to rediscover the boundaries.

None of this is "rewrite the game" — it's "the next 3-4 systems you build should go through one shared resource-transfer path and one shared event log instead of each getting its own bespoke wiring," which is a small, incremental change that pays for itself the moment you connect freighters and colonies to the shared economy.

---

## 7. Robustness: what happens when something goes wrong

- **`load_game()` only catches `FileNotFoundError`.** A truncated or hand-edited `state.json` (partial write from a disk-full save, a crash mid-`json.dump`, or you poking at it in a text editor) raises an uncaught `json.JSONDecodeError`, and since `load_game()` runs unconditionally at import time before `main()` even starts, **the game becomes unlaunchable** until you delete or fix the save file by hand. There's no backup save, and `save_game()` itself has no error handling either (no `try`/`except` around the `open()`/`json.dump()` — a full disk mid-save could leave a corrupt file that then breaks the next launch, compounding the first problem).
- **Single save slot, no confirmation on `load`.** Typing `load` at any point silently discards all unsaved progress with no "are you sure?" There's also no autosave and no versioned/rotating backups — one bad `save` (or one corrupted write) can erase real playtime with nothing to fall back on.
- **The command loop itself is robust** — I want to flag the good along with the bad. `handle_invest`, `handle_pilot`, `handle_survey`, `handle_outpost`, `handle_specialize`, and `handle_charge` all validate argument counts and reject bad input cleanly with a helpful usage message instead of crashing. That's genuinely solid defensive coding for a beginner project and better than a lot of code I see from people well past this point — the `save`/`load` path is the one place that doesn't match that standard yet.

**Fix, roughly:** wrap `load_game()`'s file read in a broader `except (FileNotFoundError, json.JSONDecodeError)`, print a clear "save file is corrupted, starting fresh" message instead of crashing, and have `save_game()` write to a temp file and rename over the old one (atomic write) so a failure mid-save can never leave a half-written, corrupt `state.json` behind. A rotating `state.json.bak` written before each overwrite would cover the "oops" case cheaply too.

---

## 8. Test coverage: solid where it exists, absent where it matters most

61 tests currently pass reliably (the 1-in-4-ish flaky one aside). Where they exist, they're good — they check real computed values (e.g. `test_cargo_effect_key_applies_exactly_once` checking `200 * 1.25 = 250` specifically to catch a double-apply regression), not just "did it run."

But coverage is very uneven. `tests/test_main_integration.py` — the only place `main.py`'s own wiring gets tested at all — has exactly 4 test classes: ship design/MK progression, shipyard slot assignment, lab specialization ticking, and penal code charges. **Zero automated tests exist for**: colonies (survey/outpost/specialize/`update_colonies`), the audit system, standing orders/equipment upgrades, the Council/Branches display, and save/load. That's roughly half of the systems listed in your own `main.py` docstring's system table, and it's exactly the code most likely to silently break as you keep building on it — nothing would catch a regression there today.

**Recommendation:** before adding new systems on top of colonies/audit/standing-orders (which §3/§4/§6 above suggest doing soon), add integration tests for the ones that exist now, the same style as the existing `ShipyardIntegrationTests`/`LabSpecializationIntegrationTests` classes. It's the same pattern you already have; it just hasn't been extended to every system yet.

---

## 9. Smaller findings

- **`attempt_pilot_project`'s failure path can leave a node in an odd display state.** On a failed pilot, `pilot_partial_progress_pct` of the committed RP is banked into `rp_invested[tech_id]` — but only `invest_rp()` ever checks whether `rp_invested >= rp_cost` to actually mark a node complete. If a pilot's partial banking happens to push a node's invested total at or past its cost, it'll display as fully funded but stay incomplete until you run `invest` again (which, if the lane's bank is 0 right after the pilot spent it, means waiting for more RP to accumulate first). Minor, but worth a `_complete_node` check added to the failure path in `attempt_pilot_project` for consistency.
- **Command dispatch and help text are two independently hand-maintained lists.** `main()`'s `if/elif` chain (24 branches) and `show_help()`'s hand-written print statements list the same commands separately — nothing enforces they stay in sync, so it's easy for a new command to get added to one and forgotten in the other. A small command registry (`{"invest": (handle_invest, "invest <lane> <pos> - ...")}`) would generate both the dispatch and the help text from one source.
- **`handle_audit`'s usage message hardcodes `'forge_marshal'`** as "currently the only seat that can have a concealment," duplicating the same assumption baked into `update_audit()`. If a second concealable seat is ever added, both places need to change in lockstep with nothing to catch a mismatch.
- **`docs/systems/shipyard.md`'s "100-slot target" and `FLEET_TARGET`'s 16-hull cap are documented separately** (this is the doc-level mirror of the code bug in §2) — worth a note in the doc once the numbers are reconciled, so future-you doesn't reintroduce the mismatch.
- **No way to `advance` more than one step at a time.** Every step requires a fresh `advance` command with no arguments. `advance 10` (looping the same body 10 times, still printing each step) would make it much less tedious to play through a long stretch without changing any underlying logic.

---

## 10. What I'd actually do next, in order

1. **Fix Earth's resource loop (§1).** This is the one that silently ends the game. Even a minimal production rule (e.g., Earth's population slowly regenerates a small trickle of support supplies each step, framed narratively however fits "Sovereign of the Forge") turns an accidental hard stop into an intentional economic pressure — which is closer to what `DESIGN_SPINE.md` actually describes ("Mars eventually needs resupply" implies a resupply *system*, not a one-time depletable stock).
2. **Generalize the freighter loop (§3)** and use the same resource-transfer path to **wire colony output into the shared economy (§4)**. These two together are the real answer to "how do the systems talk to each other" — they're the two places right now where a system produces something with no consumer.
3. **Reconcile the shipyard's 100-slot target with the fleet cap (§2)** — small, mechanical, easy to verify.
4. **Add error handling and an atomic write to save/load (§7)** before you're deep enough into a playthrough that losing it would actually hurt.
5. **Backfill integration tests for colonies, audit, standing orders, council, and save/load (§8)**, ideally alongside doing 2-4 above so the new wiring gets tests from day one instead of joining the untested pile.
6. Everything in §6 (shared resource-transfer helper, event log, command registry) is the connective tissue that makes 2 and 5 land better wherever you tackle them — worth doing as you touch each area rather than as one big refactor.

---

*This audit read every file in `src/`, `tests/`, and `docs/`, ran the test suite four times, and traced every read/write of every shared resource field by hand. I did not run the interactive game loop itself (it requires a live terminal with `input()`), so anything that only shows up in actual play rather than in the code's logic wouldn't have surfaced here — worth telling me about anything you've noticed in play that isn't on this list.*
