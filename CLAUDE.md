# Choose Your Mystery — Claude Code Instructions

## How to read this file

**This file says what is true now.** It is loaded into every session, so it holds only what a
session needs before it starts working: what the product is, how it is built, what the current
stage is, and what is open.

| Where | Holds |
|---|---|
| **`CLAUDE.md`** (here) | What is true now, and what is open. |
| **`docs/DECISIONS.md`** | Every numbered work item, 1–25, with its full reasoning. *Why is it like that? Has this been tried?* |
| **`SESSIONS.md`** | What was decided when, session by session. Append-only; never edited to match a later truth. |

**Item numbers are stable.** "Item 17" means the same thing in this file, in `docs/DECISIONS.md`,
in six files under `docs/`, and in source comments. Never renumber one.

**When a statement here needs a "superseded" marker, it has become history** — move it to
`docs/DECISIONS.md` and state the current truth here instead. Session 38 rewrote this file because
that rule had not been followed: it had reached 1,003 lines, 60% of it archive, and its own opening
paragraph contradicted its item 11.

**The vocabulary is investigation, not card game.** No decks, no cards, no hands, no deals, and
nothing is *played*. Findings are **assigned**, into a player's **casefile**. Owner's instruction,
three times — the first two were obeyed only for the noun, and the metaphor rebuilt itself from the
verbs and containers left standing. Where it came from and what was deliberately left alone:
`docs/DECISIONS.md` item 34. **The test: if a word would be at home on a box reading "2–6 players,
ages 10+", it is the wrong word.**

**Backtick-quoting a string here or in `docs/` is a CLAIM that the product contains it**, enforced
by `scripts/check_doc_claims.py`. To mention a string without asserting it exists — a retired
label, an illustrative pattern — use italics, or add it to that script's `ALLOWED_LITERALS` with a
reason.

---

## Project Overview

AI-powered social murder mystery party game. Players join a room, receive findings about a
generated crime, decide which findings to share and which to keep, and compete to accuse the
culprit first.

**Target:** multiplayer standalone, Steam release.
**Stack:** Godot 4.x desktop client + Python FastAPI backend. All Claude calls are server-side.
**HuggingFace:** retired. The `hf-deploy` orphan branch is stale.

### The core mechanic — and what it actually is

The design intent is **selective information sharing**: what you give away helps the room and
costs you your edge. Everything else in the product exists to set up that one decision.

**It is NOT a "75% mechanic", and no code has ever implemented one.** This file asserted for
many sessions that a shared clue "reaches exactly 75% of other players (randomly)". Session 21
found no such code and item 11 recorded it; the opening paragraph was never corrected, so the
false version stayed in the first thing every session read. What `server/main.py` really has is a
**player-chosen share level against a per-difficulty minimum**, with no randomness at all:

| Difficulty | `share_min` |
|---|---|
| EASY | 0.70 |
| MEDIUM | 0.60 |
| HARD | 0.50 |

**At APF's three-finding casefile that ladder is inert** — all three difficulties resolve to "share 2,
keep 1", because a percentage has no resolution over three items (Session 38). Session 39 moved
difficulty to assignment redundancy instead: `REDUNDANCY_BY_DIFFICULTY` in `casefiles.py` puts each
exoneration in two casefiles on EASY and one on HARD, which has real resolution at that casefile size.

**That buys two rungs, not three, and the ceiling is arithmetic.** Redundancy fights constraint 2:
push each exoneration into enough casefiles and some casefile holds them all and solves alone. At APF's
shape — 4 players, exactly 4 suspects, so 3 required exonerations — the ceiling is 2, so MEDIUM and
HARD are both 1. A third rung needs a second dial: suspect count or red-herring density.

If a random-broadcast mechanic is wanted, it is unbuilt design work, not a regression.

**[Session 41] The decision is a RHYTHM, not a single moment.** Findings are assigned one per player
per round, with a share checkpoint at every round from the second (a single held finding forces a share, so
round 1 assigns only). A shared finding **stays in its holder's casefile** — an investigator cannot be
made to forget, so what a player spends is *exclusivity*, not possession — which makes the share
requirement cumulative. Rounds = findings ÷ players, announced before play. This revives the
difficulty ladder that was inert at a fixed casefile: what differs between EASY and HARD is how much a
player may sit on. Full spec and the arithmetic: `docs/PLAYTEST_FLOW.md` → "The rhythm".

**[Session 42] Built, in `apf.py`.** Measured over the accepted mystery at four rounds: the private
stash is **1 at EASY, 2 at MEDIUM and HARD** — the ladder separating without a second dial, which is
what Sessions 38 and 39 both concluded could not happen. One consequence worth knowing before
touching the assignment: the stash size **is** the right `hoard_allowance`, so it is derived from the
ladder rather than taken from `casefiles.py`'s constant.

---

## Where the project is now

**Stage 1 of the delivery priority: get one human through one whole mystery on one PC.**

The current build is item 23 — **APF ("All Provided For")**, specified in `docs/PLAYTEST_FLOW.md`.
Findings are **assigned, not gathered**: no traversal, no exploration, no investigation budget, no
phase gates. That is a deliberate reduction to the sharing decision, and it deletes several
problems rather than fixing them — see `docs/INVESTIGATION_DESIGN.md` §5–§7.

**The stage-1 test is blunt:** can somebody who is not the owner sit at a PC, start the game, play
a whole mystery, and reach the result screen without a Godot error? Anything that fails that is
urgent; anything that does not, is not.

---

## Delivery Priority (owner, Session 34)

**PC playtest → funding → phone + robust gen-AI.** Owner's caveat: *"obviously it can change."*
Treat it as the current sequence, not a contract — but check work against it before starting,
because it decides what counts as a blocker.

| # | Stage | What it means here |
|---|---|---|
| 1 | **PC playtest** | The Godot desktop client is the **only** surface that has to work. |
| 2 | **Funding** | The playtest is evidence for the pitch. The studio-engine pillars (coherence engine, corpus) need to be real, which they now are. |
| 3 | **Phone + robust gen AI** | `server/static/mobile.html`, the room-first prompt flow, moderation that survives Steam, and item 17's BACKGROUND work. |

**Read this before calling something a gap:**

- **Phone-client gaps are not blockers.** `mobile.html` has no prompt entry box, no mystery list
  and no lobby suggestion UI. All true, all fine until stage 3.
- **Saved-mystery reuse reached a UI in Session 42, and stage 1 is why.** The browse list still
  loads a mystery straight into `CaseDisplay.tscn` for solo reading — that part was never an
  oversight. What changed is that `MysteryGeneration`'s multiplayer section can now open a **room**
  from a saved mystery, because until it could, every look at the round screen cost a generation and
  one generation in eight passes the gate. `GET /mysteries` reports `apf_ready` per mystery so the
  picker can disable what cannot be assigned; 1 of 17 on disk qualifies, and the other 16 say why.
- **Moderation stays as decided** — none, with the visible *Not moderated for play testing*
  disclaimer. A stage-1 answer by construction; the Steam answer is stage 3.
- **Nothing already built gets removed.** The multiplayer server work stays exactly as it is. It is
  not being extended *yet*.
- **New API cost needs a reason that serves stage 1.**

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Godot 4.x desktop client (godot/)  — the host / TV screen    │
│  GDScript 2.0. Five autoloads: GameState, ApiClient,          │
│  NetworkManager, Style, Chrome.  Nine .tscn screens.           │
└───────────────┬──────────────────────────────────────────────┘
                │ HTTP JSON  (ApiClient.gd)
┌───────────────▼──────────────────────────────────────────────┐
│  Python FastAPI server (server/)                              │
│  37 routes. Generation, interrogation, game sessions,         │
│  APF's rhythm, lockstep rounds, prompt voting, results.       │
│  Wraps part_registry, coherence_validator, localization,      │
│  craft_grounding.                                             │
└───────────────┬──────────────────────────────────────────────┘
                │ WebSocket  /ws/{game_id}
┌───────────────▼──────────────────────────────────────────────┐
│  Phone client — server/static/mobile.html, served at /play    │
└──────────────────────────────────────────────────────────────┘
```

**Route groups in `server/main.py`** (37 total — do not assume this list is short; check the file):
generation (`/generate`, `/generate/async`, `/jobs/{job_id}`), saved mysteries (`/mysteries`),
game lifecycle (`/games/create`, `/join`, `/start`), **APF's rhythm** (`/apf/open`,
`/apf/round/next`, `/apf/state`, `/apf/share`, `/apf/disclose`, `/apf/disclosure`) — the playtest
path, and the only group that costs nothing to call — the pre-APF gather loop
(`/interrogate-witness`, `/investigate-area`, `/follow-lead`, `/share-phase`, `/accuse`), lockstep
rounds (`/round/open`, `/round/submit`, `/round/resolve`, `/round/status`), replay
(`/prompts/submit`, `/prompts/tiebreak`, `/next-mystery/start`), plus `/health`, `/rate`, `/play`
and the WebSocket.

**Two transports exist, and only one is live.**

| | Status |
|---|---|
| **FastAPI WebSocket** (`/ws/{game_id}`) | **Live.** `mobile.html` connects to it. This is the multiplayer path. |
| **Godot ENet** (`NetworkManager.gd`) | **Registered as an autoload and called by nothing.** No `.gd` or `.tscn` outside the file itself references it. Desktop-only by nature — browsers block UDP, so a Godot web export would need `WebSocketMultiplayerPeer` instead. |

**Steam:** Phase 4, GodotSteam plugin. Deferred until the prototype is stable.

---

## Key Files

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI backend — every route and every Claude call site |
| `server/static/mobile.html` | The phone client, served at `/play` |
| `server/requirements.txt` | Server Python deps |
| `server/Dockerfile` | Container for deployment |
| `godot/project.godot` | Godot project root; autoload registry; ground clear colour |
| `godot/scripts/autoloads/GameState.gd` | Current mystery, phase, history |
| `godot/scripts/autoloads/ApiClient.gd` | HTTP + WebSocket wrapper for the backend |
| `godot/scripts/autoloads/NetworkManager.gd` | ENet singleton — present, unwired (see Architecture) |
| `godot/scripts/autoloads/Style.gd` | Builds the global Theme from `Palette.gd` and puts it on the scene-tree root, so all nine screens restyle with no `.tscn` edited. Hand-written; palette regeneration never touches it |
| `godot/scripts/autoloads/Chrome.gd` | The brand mark, upper-left, on every screen — added to `get_tree().root` in `_ready()` for the same "no `.tscn` edited" reason as `Style.gd`. Loads the **generated** copy at `godot/assets/brand/negative_mark.svg`; source is `brand/NEWnegative_CYM.svg`, mirrored by `scripts/build_brand.py` |
| `godot/scripts/theme/Palette.gd` | **Generated** from `palette.py` — do not hand-edit |
| `godot/scripts/data/MysteryData.gd` | Typed wrapper for mystery JSON |
| `godot/scenes/ui/` | The nine screens: MainMenu, MysteryGeneration, Lobby, CaseDisplay, **ApfRound**, Interrogation, ShareSelection, Accusation, ResultScreen |
| `godot/scripts/ui/apf_round.gd` | **The APF play screen, and the only screen the mechanic needs** — casefile, suspect board, shared pool and the share decision on one screen, because the board is what makes withholding legible |
| `godot/scripts/tools/` | `EditorScript`s — run inside the engine, File → Run. See the checker tables below |
| `palette.py` | **The one place a colour is decided.** Ground, surface ramp, ink, brass, semantics, type/space/radius scales, and a 28-pair WCAG contrast contract. Read before changing any colour anywhere |
| `part_registry.py` | The corpus index — **5,990 parts across 573 sources** as committed. `load_registry()` rebuilds when a corpus fingerprint changes; see item 14 |
| `coherence_validator.py` | P1 causal-chain, witness and evidence checks. Free — no API call |
| `coherence/` | The shared engine (`Issue`, `CoherenceReport`, `RuleSet`). Used by both CYM and Mind Your Friends — item 16 |
| `craft_grounding.py` | Retrieval layer over the craft-grounding docs; feeds guidance into all five generation call sites. Zero added API calls |
| `localization.py` | Era-appropriate name/occupation localization, 3-tier disk cache |
| `apf.py` | **APF's rhythm** (item 23 step 3). Round count, the cumulative share checkpoint, the suspect board and full disclosure. Owns the *cadence*; `casefiles.py` owns the *assignment*. The share rule is injected, never recomputed. Pure computation, wired to `server/main.py`'s six `/apf/` routes and to `ApfRound.tscn` |
| `casefiles.py` | APF's constrained assignment (item 23). `best_assignment()` picks the fairest of several assignments. Assigns findings under set arithmetic over `evidence[]`, reached through the `reveals` pointer. Pure computation, deterministic from a seed, re-runnable free. Computed, tested, **wired to no client** |
| `gate.py` | Decides whether a generated mystery may be served, and routes it to `generated/` or `rejected/`. Runs coherence, `check_narrative` and `casefiles.feasibility`; free, no API call. Item 18 |
| `arrangement.py` | The pointer-wiring pass: finds exonerations no witness, lead or area reveals, and wires the ones a finding can honestly carry. Free, deterministic. Repairs the arrangement, never the evidence — see item 29 |
| `generation_ledger.py` | One append-only JSONL row per generation attempt — cost, verdict, failure class, rule ids. The only record of what generation costs; see item 28 |
| `background_field.py` | The BACKGROUND layout (item 17). Computed, tested, **wired to no client** |
| `extraction_protocols.py` | P1–P4 taxonomy definitions. Live dependency of the extractor |
| `scripts/extract_from_pdfs.py` | The sanctioned way to add **one** new source. `--anthology` for a collection; always `--dry-run` an anthology first |
| `icons/` | Source artwork for the clue and witness icon sets, one folder per set. `godot/scripts/theme/Icons.gd` decides which icon a thing gets, and its header explains why that must carry no information |
| **Documents** | |
| `docs/PLAYTEST_FLOW.md` | **APF and the playtest screens.** Read before touching any playtest-path screen |
| `docs/INVESTIGATION_DESIGN.md` | The investigation model, solvability as set arithmetic, and the one remaining open design question |
| `docs/WIRING.md` | Canonical generation architecture — read before touching generation |
| `docs/F5_CHECKLIST.md` | The hand-walk procedure for the Godot client, and which steps have actually been walked |
| `docs/AI_COST_PLAYBOOK.md` | Measured economics. Read before adding a schema field, a play-time call, or a re-extraction |
| `docs/EXTRACTION_TROUBLESHOOTING.md` | Every extraction failure mode and its fix |
| `docs/COHERENCE_PRIMER.md` | Plain-language explanation of the two kinds of coherence, backwards generation, and what is still unchecked. Written for re-reading, not for detail |
| `docs/DECISIONS.md` | Items 1–26 with full reasoning |
| `RESEARCH_FINDINGS.md`, `SCREEN_CRAFT_FINDINGS.md`, `PARTY_CRAFT_FINDINGS.md` | Craft grounding — prose, screen, and party-game taxonomies |
| `SOURCING_METHODOLOGY.md` | Confidence tiers and the corroboration rule for the three above |

**`deprecated/` — do not touch.** The pre-Godot Streamlit/HuggingFace creator tool, kept for
provenance only: `app.py`, `cli.py`, `corpus_loader.py`, `run_corpus_pipeline.py`,
`mystery_generator.py`, `gameplay_validator.py`, `test_mysteries.py`, `extract_test_mysteries.py`,
`browse_mysteries.py`, `demo_acquisition.py`, `mystery_data_acquisition.py`,
`mystery_database_plan.md`, `GETTING_STARTED.md`, `end_of_session.sh`, `requirements.txt`.

**The list matters because several of those names look live.** `deprecated/requirements.txt` is not
`server/requirements.txt`, and `mystery_generator.py` is exactly what someone would open to change
generation — which lives in `server/main.py`.

**One exception:** `extraction_protocols.py` was briefly moved there and has been restored to root —
it is a live dependency of `scripts/extract_from_pdfs.py`. Everything else there really is inert.

> **DO NOT re-run the frozen bulk corpus pipeline** (`deprecated/run_corpus_pipeline.py`). Expand
> the corpus only via `scripts/extract_from_pdfs.py`, one quality source at a time.

---

## Session protocol — MANDATORY

**At the start:**

1. `git fetch origin && git checkout main && git pull origin main`. Create a feature branch off
   `main` for anything more than a trivial change.
2. Read the most recent block in `SESSIONS.md` — exact next step, blockers, decisions.
3. State your starting point: branch, latest commit hash, what you will do.
4. Read `docs/WIRING.md` if touching generation, localization or coherence logic.

**At the end:**

1. Update `SESSIONS.md` with a new session block.
2. Update this file's **Open work** section, and `docs/DECISIONS.md` if an item's status changed.
3. Commit and push on the feature branch.
4. Tell the owner to sync locally.
5. The remote rejects `git push origin main` (HTTP 403). Open a PR with the GitHub tools and merge
   it once clean — letting them accumulate is what caused the July 2026 branch-reconciliation mess
   (item 5).

**Never end a session without updating `SESSIONS.md`.**

**Active branch: `main`.** If a session is auto-assigned a stale branch, compare it against `main`
before trusting it — this has happened before and cost a reconciliation (items 5, 6, 9).

---

## Godot development notes

- **Godot 4.x, GDScript 2.0** — typed, `class_name` declarations. `project.godot` declares 4.6.
- **Five autoloads**, in order: `GameState`, `ApiClient`, `NetworkManager`, `Style`, `Chrome`.
  `Style` is second-to-last because it reads `Palette.gd`; `Chrome` is last because it adds the
  brand mark on top of whatever theme Style already set. If you add one, register it in
  `project.godot` **and** confirm it appears in Project → Project Settings → **Globals** (the tab
  is called *Autoload* on Godot 4.6
  and earlier; 4.7 renamed it).
- **No Godot binary in the repo, and none reachable from a session environment** — outbound is
  allowlist-only and the engine's hosts are not on it (tested, Session 38). Rendering can only be
  verified on the owner's machine.
- **Backend URL** is `ApiClient.SERVER_URL`, default `http://localhost:8000`.
- **Testing single-player:** run the server (`python3 -m uvicorn server.main:app --port 8000` from
  the repo root), then F5. **`python3 -m uvicorn`, not bare `uvicorn`** — the launcher script is
  absent from `PATH` on Homebrew Python, on `pip install --user`, and in any terminal where the venv
  is not active, and `zsh: command not found: uvicorn` reads like a missing dependency when the
  package is installed and importable. The `-m` form works whenever it is.
- **A fresh clone must be opened with Edit, not Run** — `.godot/` is a generated import cache and is
  not committed. `.uid` files *are* committed; Godot 4.4+ expects them.
- **`project.godot` cannot hold documentation.** Opening the project in Godot 4.7 rewrites the file
  from the engine's own config and **deletes all 21 `;` comment lines**, bumps `config/features` to
  `"4.7"`, and drops `[rendering]`. Discard that diff rather than committing it — see
  `docs/F5_CHECKLIST.md`. Every fact those comments carry has a durable home elsewhere.

### Three failure modes Godot will not tell you about

Every one of these has cost a screen in this project. They are why the checkers below exist.

| Failure | What it looks like |
|---|---|
| A GDScript parse error | The scene's static nodes render and nothing responds. No runtime error. |
| A `#` comment line in a `.tscn` | The node declared after it is silently dropped at load. |
| A theme item name the engine does not have | A silent no-op — the control keeps its engine default. |

---

## Coding conventions

- Python 3.8+ server-side; GDScript 2.0 with type annotations client-side.
- **State the type.** Session 36 lost a whole screen to a `Variant` inferred from
  `Dictionary.get()`; `:=` on a constructor call is the shape that goes wrong.
- **Models, by job:** gameplay generation uses `claude-sonnet-4-6` (`server/main.py`); extraction
  defaults to `claude-haiku-4-5-20251001` with a Sonnet fallback; the corpus upgrade defaults to
  `claude-opus-5`.
- Mystery parts use `SOURCE(INDEX)` notation — `C(4)`, `F(2)`, `A(6)`.
- Extraction protocols: P1 Skeleton (C1–C6), P2 Architecture (M1–M8), P3 Craft (F1–F8),
  P4 Texture (F9–F12).
- Every generated mystery carries a `_provenance` field.
- API auth is server-side only: (1) the `ANTHROPIC_API_KEY` env var, (2) a Bearer token from
  `/home/claude/.claude/remote/.session_ingress_token`.
- Invoke Python as `python3` — this environment has no `python` alias.

### Phase annotations (commit tags)

| Tag | Meaning |
|---|---|
| `phase1-backend-done` | FastAPI server + Godot scaffold complete |
| `phase2-single-player-prototype` | Full single-player loop works in Godot |
| `phase3-multiplayer` | Lobby + clue sharing working |
| `phase4-steam` | GodotSteam integrated |

---

## Design principles

Every new feature should answer at least one:

**1. Does it close a feedback loop?** Creator signal is the 1–10 viability rating; player signal is
accusations, interrogation patterns and time-to-solve; part signal (future) is weighting the
registry by which parts appear in high-rated mysteries.

**2. Does it preserve coherence?** The P1 causal chain must be unbroken: crime → victim → closed
world → culprit/motive → resolution. Run `check_parts()` before the generation call and
`check_mystery()` after, attaching the result as `_coherence`. Both are free.

**3. Does it drive down cost?** API calls are the primary cost driver, and **output tokens are ~95%
of a generation call** — so prompt caching saves ~5% and is the wrong lever. The right one is
writing fixed text at generation time instead of calling per action, measured at 10.8× on a
four-player game. Details in `docs/AI_COST_PLAYBOOK.md`.

| Rule | Detail |
|---|---|
| Cache localization rulesets | `mystery_database/localization_cache/` keyed by era |
| Skip modern-era localization | `_is_modern(setting)` → no API call |
| Compact mapping over full rewrite | Claude returns `[{old,new}]` only |
| Cache extractions | Never re-extract a source already in JSON |
| Coherence is free | `coherence_validator.check_parts()` / `check_mystery()` — zero API calls |
| Adding one new source | `scripts/extract_from_pdfs.py <file-or-dir> --protocol P1`, not the frozen bulk pipeline |

**Active caching inventory:**

| Cache | Location | Key | Stores |
|---|---|---|---|
| Localization rulesets | `mystery_database/localization_cache/<era_key>.json` | location + time-period slug | Name conventions, occupation map, forbidden titles |
| Part extractions | `mystery_database/extractions/*.json` | source filename | P1–P4 parts from source texts |
| Generated mysteries | `mystery_database/generated/*.json` | slug + timestamp | Full mystery dicts with `_coherence` |

---

## Checkers — run these before handing anyone a build

Zero API cost, no Godot binary needed. Each has already caught a real bug.

| Script | Catches |
|---|---|
| `scripts/check_godot_wiring.py` | Broken `$NodePath`s, `@onready` type mismatches, unreferenced interactive controls, autoload calls with the wrong arity, `#` lines in a `.tscn`, an undeclared `theme_type_variation`, Python-style docstrings, and implicit string concatenation. Runs over all scenes, autoloads and scripts. **Necessary, not sufficient** — it reads scene files rather than loading them |
| `scripts/check_narrative.py` | A person the solution reasons about who is not in the cast; a declared link that does not resolve; a chain step nothing supports; elimination that does not leave exactly the culprit. `scripts/test_narrative_checks.py` proves those fire |
| `scripts/check_solvability.py` | Not a gate — a report on the structural link between evidence and solution across every generated mystery: key evidence the reasoning ignores, evidence the reasoning uses that the key list omits, dangling IDs, suspect counts, and whether elimination is being written as prose |
| `scripts/check_mystery_playable.py` | A `solution.culprit` naming no listed suspect, an empty suspect list, or a blocking coherence failure served anyway |
| `scripts/check_decisions.py` | An item labelled open that another item says is finished (the item-21 shape), a duplicate or missing item number, and a cited item number that resolves to nothing. Cross-project references that name MYF are left alone |
| `scripts/check_doc_claims.py` | Documentation that has drifted from the code — a referenced file that does not exist, a *path:line* outside its file, a backticked string absent from every code file |
| `scripts/build_palette.py --check` | The palette having drifted between `palette.py`, `Palette.gd`, `mobile.html` and the ground clear colour |
| `scripts/test_palette.py` | Every ink/background pair against its WCAG floor |
| `scripts/build_icons.py --check` | Generated icon copies drifting from `icons/`. `--report` describes the sources. Refuses a raster embedded in an SVG wrapper, which cannot be recoloured |
| `scripts/build_brand.py --check` | The Godot copies of the brand marks (`godot/assets/brand/`) drifting from `brand/NEWnegative_CYM.svg` / `NEWorganic_cym.svg`. Byte-exact mirror, no recolouring — a brand mark is a fixed identity, not a retintable icon |
| `scripts/split_icon_sheet.py` | Cuts a sheet of icons into one file each — vector by subpath geometry, raster by column occupancy, dispatching on what the file contains rather than its extension. Reports detached specks; never removes them |
| `scripts/test_icons.py` | That the icon flatten survives all three export shapes, and that icon assignment is genuinely random |
| `scripts/test_apf.py` | The rhythm: that round 1 asks nothing, that sharing is cumulative and monotone, that the difficulty ladder separates, that the board never greys a face on a narrowing, that disclosure names whoever sat on it, and that a client is sent only its own half. Fixtures plus one pass over the accepted mystery |
| `scripts/test_share_rule.py` | The share minimum being defined twice. It was — server `round()` against client `ceili()`, disagreeing in 6 of 18 realistic cases with the client always stricter, so it refused shares the server would accept |
| `scripts/test_registry_staleness.py` | That a moved-on corpus rebuilds the registry and an unchanged one does not |
| `scripts/test_crime_scene_map.py` | Overlapping rooms, off-canvas rooms, a witness outside its stated room, a non-deterministic layout |
| `scripts/test_casefiles.py` | The three assignment constraints, and that each refuses a mystery violating it. Fixtures, because no mystery on disk carries `reveals` yet |
| `scripts/test_gate_and_ledger.py` | The gate's refusals and the ledger's arithmetic: that a clean mystery is accepted, that each failure class is refused and correctly named, that CAST findings stay advisory, that a legacy mystery is `unjudged` rather than rejected, and that CPAM divides by accepted rather than by attempts |
| `scripts/test_arrangement.py` | That the wiring pass refuses a false positive — both of the two it actually made on real mysteries — that a genuine carrier is wired, and that a wiring making the mystery worse is withheld even when it lowers the violation count |
| `scripts/check_rule_coverage.py` | Every hard assertion in the generation prompt against the rule that enforces it. Fails if the prompt gains an assertion nobody has triaged, if an inventory entry names a rule id that no longer exists, or if an inventoried assertion has been deleted. The standing UNENFORCED list is its real output |
| `scripts/test_rule_coverage.py` | That the coverage checker actually fails — an untriaged assertion, a dead rule id, a stale entry. A coverage checker that cannot fail is worse than none |
| `scripts/test_background_field.py` | The BACKGROUND layout |
| `scripts/test_extraction_fatal_errors.py` | That a batch stops on an account-level API failure and continues past a per-source one |

**Two more run INSIDE the engine** — `EditorScript`s, File → Run, free. They are the only checks
that use Godot's own loader, which is where the undetectable defects live:

| Script | Catches |
|---|---|
| `godot/scripts/tools/VerifyScenes.gd` | A node a `.tscn` declares that does not survive loading, a node whose runtime class is not what the scene declares, and a scene root that lost its script. **Run on 4.7.2 in Session 40: eight `ok` lines** |
| `godot/scripts/tools/ApplyTheme.gd` | A theme item name the engine does not have. Also generates the editor's theme preview, so the design is visible while scenes are edited, and reports whether the fonts resolved. **Run on 4.7.2 in Session 40: 168 items across 36 types, `MISSES none`, fonts resolved** |

**One fills the other seats so a person can walk it alone:** `scripts/seat_players.py <ROOM>` joins
three players to a room and pays each share checkpoint with the bare minimum. It is **not** a bot
player — it never accuses, never opens a round and never closes the case. It exists because APF needs
at least two players (constraint 2 is unsatisfiable at one) and `mobile.html` cannot yet share under
the rhythm, so without it a solo walk stalls at the round-2 checkpoint. Run it while the host is in
the lobby, before they deal — `open_session()` snapshots who is in the room.

**One needs a running server, and finds what no in-process test can:**
`scripts/walk_apf_game.py` plays a whole four-round APF game over real HTTP — create, join, assignment,
four rounds, full disclosure, accusation, result. Zero API cost and **no API key needed**; it plays
the mystery already on disk. Session 42 found two defects with it that every unit test passed
through. Run the server first, then `python3 scripts/walk_apf_game.py`.

**Not checkers, but run locally:** `scripts/wire_pointers.py` reports exonerations nothing reveals and which suspects have no witness at all (`--coverage`), wiring only what a finding can honestly carry; `scripts/cpam.py` reports cost per accepted mystery, pass rate and rejections by rule from `mystery_database/ledger.jsonl`; `scripts/backfill_ledger.py` seeds that ledger from the mysteries already on disk (idempotent, `--go` to write); `scripts/preview_background_field.py` renders the BACKGROUND
field to SVG over real screen text (`--sheet` covers the shortest and longest real titles);
`scripts/compare_extraction_models.py` scores extraction models by parts yielded and axes filled.

---

## Open work

Everything else is closed — see `docs/DECISIONS.md`.

### 23. Build APF — **steps 1–4 built. What is left is a table, not code**

The playtest shape is agreed and written down: `docs/PLAYTEST_FLOW.md` → "APF (All Provided For)".
Findings are **assigned, not gathered**; the only decision is which to share and which to keep, which
is the mechanic this file's overview calls the point of the product. All four build-order steps
(schema, constrained assignment, the rhythm/board/reveal, the paced opening) are built. Full build
history — the five rejected approaches, the accepted mystery and its CPAM, the seed-search/monopoly
fix, the two-routes-problem resolution and its interaction with item 27 — is in `docs/DECISIONS.md`
item 23; Session 44's screen-by-screen playtest is in `SESSIONS.md`. Neither is repeated here.

**What is actually left is a table.** The accepted mystery, `the_neriin_in_the_pilchard_barrel`, has
been played end to end, four rounds, at all three difficulties. Nothing on the critical path is
unbuilt. What has never happened is a person other than the owner sitting down to it cold — see
**Not verified** below, and `docs/F5_CHECKLIST.md`.

**Not verified, and the list is shorter than it was.**
(a) Nothing here has been confirmed run through `VerifyScenes.gd` / `ApplyTheme.gd` — those need the
owner's machine, and whether they ran during the Session 43 walkthrough is unconfirmed.
(b) **[Session 43] Closed — no longer open.** Ezra Greene played two mysteries through to the result
screen, rating them 9 (`the_neriin_in_the_pilchard_barrel`) and, initially, 10
(`whiteout_at_shackleton_base`) — revised to 8 the next day (`fix/whiteout-rating`). Which path each
took is still unconfirmed — `whiteout_at_shackleton_base` was not `apf_ready` last checked, so that
rating may reflect the pre-APF gather loop, not the rhythm this item is about.
(c) APF needs at least two players — a solo walk-through needs `scripts/seat_players.py`.

**The one play-time Claude call left on the critical path is the resolution narrative.** A failed
call now falls back to the mystery's own resolution prose, but build-order step 5 still has to
remove the call outright.

### 27. Incrimination as well as exculpation — the glove mechanic — **BUILT, Session 40**

Deduction today is pure subtraction: every clue clears one suspect, you win when one name is left.
The owner's example is the design — *"a bloody men's glove"* clears nobody alone, but combined with
*"the CCTV shows Adachi in the control room all night"* it names the killer. **Two findings that
individually prove nothing combine into a proof**, which turns sharing into the engine of the
deduction rather than an obligation.

**Never stated as "the culprit is one of these two."** The clue says *man's size large*; the player
looks at the cast and draws the line. Hidden field, oblique prose — `investigation_prompt` is the
existing precedent. The rule that keeps it honest is already in the corpus as **M3 Clue Fairness**
(`RESEARCH_FINDINGS.md`): an assumption the game invites must be one that holds, or a player who
reasons correctly loses.

**Built as a separate `narrows` field, not by overloading `implicates`** — that field means
suspicion, and a single-name list read as a constraint is the whole answer in one finding.
`solves()` intersects narrowings and subtracts exonerations; elimination stays the guaranteed floor
so a withheld glove can never make a case unprovable. Fair play is enforced: the culprit must
appear in every `narrows` list, a narrowing must name at least two suspects and fewer than all of
them, and its prose may not name the people it narrows to. Untested against a real generation.
Full reasoning: `docs/DECISIONS.md` item 27.

### 18, 28. The gate and the ledger — **CLOSED, Session 41**

Item 18 is settled (owner's choice: route on **any** failing check, not only coherence) and item 28
is the other half of the same write. `gate.py` decides where a generation is saved; every attempt
appends a row to `mystery_database/ledger.jsonl`.

**`generated/` now means: no check we own can prove this is broken.** `/mysteries` globs that
directory, so what sits there is what a real table can play.

The data is worth carrying forward, because it inverts the obvious assumption: **all four mysteries
in `rejected/` PASSED coherence with 0 blocking**, and the one file that FAILED it was in
`generated/`, servable. Coherence is not the thing that catches bad generations — it caught 1 of 21.
The game-structure checks caught the rest.

**Auto-reject, never auto-repair.** A gate can only be conservative. A repair loop iterating a model
against these checks until they go green selects for mysteries *shaped like the checks*;
`the_light_that_went_out` passed every structural rule and gave its answer away in prose.

Run `python3 scripts/cpam.py` for cost per accepted mystery, pass rate and rejections by rule.
Full reasoning: `docs/DECISIONS.md` items 18 and 28.

### 33. Five suspects would unlock the third difficulty rung — **deferred, owner wants to revisit**

The redundancy ladder has two rungs, not three, and the ceiling is arithmetic: at four suspects
(three required exonerations) over four players it is **2**, so MEDIUM and HARD are forced to the
same value. **A fifth suspect raises it to 3** — a real third rung with no new mechanism.

Blocked only by pool size. A fifth suspect locks two more findings as alibis out of the 18 a
mystery currently carries, and it competes with round count (findings ÷ players) for the same
findings. Both wants are answered by more findings per mystery, which is output tokens.

**The trigger is a number, not a decision:** revisit once a mystery reliably carries enough
findings to feed both. Until then `APF_SUSPECT_COUNT` stays 4 and is enforced by
`CASE.SUSPECT_COUNT`. Full reasoning, including why "minimum 4" was rejected: `docs/DECISIONS.md`
item 33.

### 17. BACKGROUND — one owner decision outstanding — **stage 3**

The layout is built and tested (`background_field.py`) and wired to nothing, which is the specified
pre-prompt state. Outstanding: whether the field is strewn with the mystery's title, with something
else, or both — do not assume.

**Resolved for the Godot client (Session 42/43).** The negative mark sits upper-left on every
screen via `Chrome.gd`. The organic monogram's placement on `Lobby.tscn` was tried and then swapped
for a temp placeholder (`logo_temp.svg`, not wired into `build_brand.py`) pending an artist — not
contrast-checked either, and measured anyway: 66% of its ink is at or below 2.5:1 against
`Palette.GROUND`. Whatever the artist delivers should go through `scripts/check_brand_contrast.py`
before it's wired in for real. Full history: `docs/DECISIONS.md` item 17.

**Still open, both stage 3:** the phone half (organic monogram, top-centre — `mobile.html` has no
chrome pass at all), and the window icon (`project.godot`'s `config/icon`, deliberately unset until
someone actually asks for it).

### 19. Corpus P1→P1P2P3 upgrade — **ready, blocked on API credits**

`python3 scripts/upgrade_p1_to_p1p2.py` prints the plan and spends nothing; `--go` runs it.
Idempotent and resumable; replaced extractions are archived, never deleted. `--check-sources`,
`--find-missing` and `--source-dir` handle PDFs that moved, were renamed, or are gone; `--model`
overrides the default. Seven stories upgraded
before credits ran out — check for them before re-running. Buys corpus quality, not anything a
playtester sees, so it is explicitly not stage 1. Full history: `docs/DECISIONS.md` item 19.

### 7. Corpus growth — **ongoing**

Favour anthologies over novels roughly 3–5 to 1: an anthology yields far more sources per legal
clearance, and P3 field confidence is 81% high for anthology stories against 48% for novels,
because a novel is sampled and a short story is fed whole. Outstanding: 11 held-back anthology PDFs
with detection problems, 7 all-null extractions that occupy filenames, and one untriaged Higashino
novel. Full detail: `docs/DECISIONS.md` item 7.

### 4, 8. Deferred by stage

Avatar pool + player profiles (item 4, design locked, nothing built) and Steam integration
(item 8) are both behind stage 3.
