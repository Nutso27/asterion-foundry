# Lore Sync — how this folder works

This folder is the bridge between the Perplexity Choose-Your-Own-Adventure
thread (where Ryan develops Asterion Foundry's story/lore) and this repo
(where the game code lives). It exists so both AIs — Perplexity's CYOA
and whichever Claude is working on the code (Cowork or Claude Code) — are
reading from the same canonical narrative state, instead of the narrative
living only in a chat transcript no one re-reads.

## The four files

- **`canon.md`** — the narrative log itself. Append-only, chronological,
  tagged by cycle/date. This is the raw story content pulled from
  Perplexity, lightly organized but not rewritten.
- **`glossary.md`** — a standing reference of named entities (Council
  seats, Branches, factions, ships, key figures, institutions) with a
  one-line description and a note on whether each is wired to live game
  data yet. Updated in place, not append-only.
- **`gaps.md`** — the working list of mismatches between narrative and
  code: lore that has no code equivalent yet, code systems with no
  narrative behind them yet, and places where the two have diverged and
  a real decision was made about which one wins. This is the persistent
  version of the "flag it, don't silently reconcile it" practice from
  the project brief.
- **`README.md`** (this file) — also carries the sync log at the bottom:
  a running record of when a sync happened and what it touched.

## How a sync happens

This is on-demand, not automatic — there's no way to have Perplexity
push content out on its own, so it starts with you:

1. Copy the new material out of the Perplexity thread.
2. Paste it to Claude (either in a Cowork chat attached to this project,
   or in a Claude Code session in this repo) and say something like
   "sync this lore in."
3. Claude reads the existing `canon.md`/`glossary.md`/`gaps.md` plus the
   code-facing docs (`DESIGN_SPINE.md`, `docs/systems/*.md`, `src/`) to
   check the new material against what's already built, then:
   - appends the new narrative to `canon.md` under a dated/cycle heading
   - updates `glossary.md` for any new or changed named entities
   - adds or updates entries in `gaps.md` for anything that doesn't
     line up with the code yet — new content is never silently forced
     into matching existing code, and existing code is never silently
     changed to match new lore, without you being told first
   - adds a line to the sync log below
4. **In Claude Code**, that's the whole thing — it has real git access on
   your machine, so it commits (and can push) directly.
   **In Cowork**, Claude can write the updated files into this folder
   directly, but this bridge doesn't give it a terminal on your laptop,
   so you'll get a one-line `git add lore/ && git commit -m "..." && git
   push` to run yourself to finish it.

## Sync log

| Date | Cycle/range covered | Files touched | Notes |
|------|---------------------|----------------|-------|
| 2026-09-03 | — | README.md, canon.md, glossary.md, gaps.md created | Initial setup of the lore/ folder itself, seeded from the existing project brief and session summary. No new Perplexity content synced yet. |
| 2026-09-03 | Cycles 0–3 (Founding Era through the Cycle 3 continuing orders) | canon.md, glossary.md, gaps.md | First real sync. **Partial only** — Perplexity confirmed the canonical state is Cycle 29, but its own log extraction was truncated around Cycle 20, so Cycles 4–29 are still pending (Ryan needs to paste Cycles 20–29, or the full log, to Perplexity next). Also flagged: an unresolved cycle-length retcon (month → day) that Perplexity's own log admits wasn't reconciled against production numbers; the Bureau audit mechanic's in-universe justification is now confirmed (Directorate Code + Bureau/Provost-General institution); several research-lane and Directorate-Code/Penal-Code naming mappings noted as plausible but unconfirmed. |
| 2026-09-04 | Cycle 29 (Council roster + Command Net) plus a not-cycle-tagged doctrinal retcon | canon.md, glossary.md, gaps.md, design/command-and-rank-structure-v4.md (new), design/religion-removal-retcon.md (new) | Second sync, sourced from Ryan's saved Perplexity transcript files rather than a fresh paste. Added: the full named Cycle 29 Council roster (Halvard/First Minister, Osei/High Savant, Ferrant/Grand Admiral, Okoye/Quartermaster-General, Solanke/Colonial Warden, Voss/Marshal-General, Dubois/Chancellor-General, Thale/Provost-General), Director's Own (Captain-of-the-Guard Mara Voskuijlen), the Directorate Command Net doctrine (design intent confirmed by Ryan, mechanical build status still open), and the religion-removal retcon (Ember Faith → Office of Human Continuance, First Flamekeeper → First Steward of Continuance, Continuance Halls, the Human Spark, the Decree of Human Continuance). Two other saved transcripts were checked and confirmed **not** Directorate canon (checked off in `gaps.md` so future syncs can skip them); one of them is the confirmed origin of the "Sovereign of the Forge" project title (name-origin only, not story content). Still open: First Flamekeeper vs. First Steward of Continuance seat-holder sequencing (inferred, not explicitly confirmed), DCN's live-integration status, and the Cycle 29 numeric baseline hasn't been checked against the actual save file. The active Cycles 4–29 recap blocker and the month/day cycle-length retcon from the first sync are both still open. |
