# Choose Your Mystery — Decision record

**What this file is.** Every numbered work item this project has had, items 1–25, in numeric
order, with the reasoning that produced each. It was carved out of `CLAUDE.md` in Session 38,
where it had grown to 60% of a file that gets loaded into every session's context whether or not
any of it is relevant.

**What it is for.** Answering *"why is it like that?"* and *"has this been tried?"* — not for
planning. `CLAUDE.md` holds what is true now and what is being worked on. If the two disagree,
`CLAUDE.md` wins and the entry here is stale.

**Item numbers are stable and load-bearing.** They are cited from `CLAUDE.md`, from six files
under `docs/`, and from source comments in `background_field.py`,
`godot/scripts/autoloads/Style.gd` and `scripts/preview_background_field.py` — "item 17" alone
appears fifteen times. **Never renumber an item.** A superseded item keeps its number and gains a
note naming what replaced it.

**Status labels**

| Label | Means |
|---|---|
| `[DONE]` | Built and verified. |
| `[CLOSED BY APF]` | Not fixed — the mechanic that needed it was deleted. The diagnosis is kept because it is usually the argument *for* APF. |
| `[OPEN]` | Still a live question. `CLAUDE.md` carries the one-paragraph version; the full reasoning is here. |
| `[DEFERRED]` / `[FUTURE]` | Real, scheduled behind the current delivery stage. |
| `[SUPERSEDED]` | Replaced by a later item or a document, which the entry names. |

**The rule that keeps this file from rotting the way its parent did.** A design document states
what is true *now*; `SESSIONS.md` states what was decided *when*; this file states why a numbered
item exists and where it ended up. A "superseded" marker appearing in `CLAUDE.md` is the signal
that the superseded text has become history and belongs here instead.

---

## Index

| # | Item | Status |
|---|---|---|
| 1 | Phase 1 — FastAPI server + Godot scaffold | `DONE` |
| 2 | Phase 2 — single-player Godot prototype, all five screens | `DONE` |
| 3 | Phase 3 — multiplayer investigation phases + clue sharing (3a–3d) | `DONE` |
| 4 | Phase 3e — avatar pool + player profiles; design locked, nothing built | `DEFERRED — stage 3` |
| 5 | PR #1 branch reconciliation merged to `main` | `DONE` |
| 6 | Five superseded branches confirmed deleted | `DONE` |
| 7 | Corpus growth — anthologies over novels, and why | `ONGOING` |
| 8 | Phase 4 — Steam / GodotSteam integration | `FUTURE` |
| 9 | Repo-wide branch cleanup; `dev/cryptic-challenge` is not a third project | `ONGOING` |
| 10 | Craft-grounding RAG layer wired into all five generation call-sites | `DONE` |
| 11 | Multiplayer lockstep redesign — the 75% mechanic does not exist in code | `IN PROGRESS` |
| 12 | Extraction-pipeline efficiency: fields extracted but never sampled | `PARTIALLY FIXED` |
| 13 | Silent extraction failures saved a null placeholder | `DONE` |
| 14 | `evidence_type`/`alibi` axis mislabel + registry staleness fingerprint | `DONE` |
| 15 | Room-first lobby, resolution reveal, prompt voting, same-room replay | `DONE` |
| 16 | Coherence engine unification — CYM and MYF share one `RuleSet` | `DONE` |
| 17 | BACKGROUND — the mystery's title as page texture; two owner questions open | `PARTLY BUILT` |
| 18 | A BLOCKING coherence report does not stop a mystery being served | `OPEN` |
| 19 | Corpus P1→P1P2P3 upgrade — runnable, blocked on API credits | `READY TO RUN` |
| 20 | CLOUD — manipulable top-down crime scene | `SUPERSEDED IN PART` |
| 21 | The investigation-phase deadlock | `CLOSED BY APF` |
| 22 | The first Godot F5 ran — two defects no checker could see | `DONE` |
| 23 | Build APF — the current work | `START HERE` |
| 24 | One palette, three surfaces | `DONE` |
| 25 | The design becomes visible in the editor; two engine-side checks | `DONE` |
| 26 | Generation writes backwards; clues declare what they serve | `DONE` |

---

1. **[DONE]** Phase 1 — FastAPI server + Godot project scaffold

2. **[DONE]** Phase 2 — Single-player Godot prototype (all 5 screens functional)

3. **[DONE]** Phase 3 — Multiplayer investigation phases + clue sharing
   - **[DONE]** 3a: Mystery gen updated (investigation_areas + leads in JSON)
   - **[DONE]** 3b: Game session store + 8 server endpoints
   - **[DONE]** 3c: WebSocket upgrade + mobile.html phone client + .tscn wiring
   - **[DONE]** 3d: Lobby flow, room codes, host-screen display (Session 14)

4. **[DEFERRED — stage 3]** Phase 3e — Avatar pool system + player history tracking. Design is locked and
   merged (PR #4, Session 17) — full spec in `docs/WIRING.md` under "Avatar system + player
   profiles (Phase 3e)" (two-layer model: shared era-keyed base looks + persistent per-player
   signature accessory from a fixed catalog). Nothing is built yet; see that section's
   "What still needs building" list. Sign off on the proposed 16-item accessory catalog first.

5. **[DONE]** PR #1 (branch reconciliation) merged into `main` — merge commit `faf52e0`, July 9 2026.
   `main` is now the source of truth: full Godot migration, `deprecated/` Streamlit archive, and
   the PDF-ingestion corpus work are all present.

6. **[DONE]** The five superseded branches were confirmed deleted (owner, July 9 2026):
   `claude/review-godot-migration-GiLDz`, `claude/fix-godot-performance-QyXLQ`,
   `claude/start-godot-migration-mNrWD`, `claude/setup-api-and-mysteries-LRLQK`,
   `claude/mystery-versioning-system-TPblK`

7. **[ONGOING]** Corpus growth — the anthology (`The_Best_of_Mystery_1980_Anthology`) is **[DONE]**:
   run for real, all 63/63 stories extracted (Session 21), source_id collision fix confirmed
   working on the real output. Corpus is larger than this list previously implied — besides the
   12 PDF-sourced entries via `scripts/extract_from_pdfs.py` (now 12 novels + 63 anthology
   stories = 75), there are **283 additional `ebook_*` entries** from an earlier bulk-pipeline run
   (bookrix.com sources, P1+P2 depth) already sitting in `mystery_database/extractions/` —
   confirmed present, not previously tracked in this file (Session 21).
   **Sourcing-ratio guideline (Session 21; second justification measured Session 35):** favor
   short-story anthology PDFs heavily over individual novels for new clearance decisions —
   roughly 3–5 anthologies cleared per 1 novel.

   **[Session 35] The original argument was cost-per-legal-clearance. There is now a measured
   QUALITY argument, and it is the stronger one.** After the P1P2P3 upgrade ran on 70 sources,
   P3 field confidence splits sharply by source type:

   | | high | medium | low | null | P3 fields |
   |---|---|---|---|---|---|
   | anthology story | **81%** | 16% | 0% | 3% | 441 |
   | novel | **48%** | 44% | 4% | 4% | 77 |

   Nearly half of every novel's P3 content is hedged. The cause is sampling, not the model: a
   short story under 25,000 chars is fed **whole**, while a novel is capped at
   `--max-text-chars` (24,000 in this run — about 7% of a 350,000-char book, as three
   disconnected chunks). P3 fields describe whole-book structure, so they are exactly what
   sampling destroys.

   **Do not measure this with part counts — they saturate and hide it.** Both types land at
   ~19.5 parts of a possible ~20 mapped keys, so by that metric novels look *better* than
   stories (4.2x vs 3.5x gain, an artifact of a lower starting point). Confidence is the honest
   signal. Anything that scores extraction quality should use it.

   **The fix for novels, when there is appetite:** raise `--max-text-chars`. Opus 5's context is
   1M tokens, so the 24,000-char cap is arbitrary rather than technical — a whole novel is
   ~87K tokens. Input is the cheap half of a call: ~$0.45/novel at 120K chars, ~$1.30/novel fed
   whole, against ~$0.09 today. Roughly **$15 buys all 12 novels the quality the stories already
   have**, as a re-run of the same idempotent command with no new code. Explicitly NOT urgent —
   it buys corpus quality, not anything a playtester sees (see Delivery Priority).

   The old wording, kept because it is still true of the cost side: an anthology yields 15–63x
   the source_ids per single legal-clearance decision at currently-identical extraction depth (both the 12 curated novels and the 63 stories are P1-only;
   novels only earn a depth advantage once `--protocol P1P2`, or P3/P4, actually gets used on them).
   `mystery_database/new_sources/` still holds: three full novels (Stevenson ×2, Tana French)
   queued for later one-at-a-time ingestion; one `.html` file (`extract_from_pdfs.py` only reads
   PDFs — unsupported as-is); and **`The_Devotion_of_Suspect_X` (Higashino) — found untriaged in
   Session 21**, not one of Session 20's original 9 categorized files, confirmed NOT a duplicate of
   the existing Higashino extraction (different novel: *Miracles of the Namiya General Store*).
   Owner ruled out deleting it; still needs an actual triage call (queue / skip / other).
   **[IN PROGRESS, Session 27]** The 22+-anthology ingestion is underway, not finished. Session 27
   was almost entirely git housekeeping (see `SESSIONS.md`) plus a duplicate-source triage: cross-
   referenced the owner's ~26 staged local files against the real corpus and caught two real
   near-misses — renamed duplicate PDFs of already-extracted books (*Leavenworth Case*, *Red House
   Mystery*), and, more seriously, the already-fully-extracted 63-story Hitchcock 1980 anthology
   itself still sitting in `new_sources/` (would have re-spent real API cost re-extracting 63
   already-owned stories). Owner removed both categories. Confirmed the extraction pipeline still
   has zero content-based dedup (`_slug()` keys purely off the input PDF's filename) — worth a
   pre-flight duplicate check on every future batch, not just this one; a standalone checker script
   was written for this (scratchpad-only, not committed to the repo).

   Remaining 21 anthology PDFs were `--dry-run`'d: **10 came back clean** (full-book page ranges,
   real per-story detection — the *Best American Mystery Stories* years 2005–2017/215/"4" plus
   *Years Best Mystery & Suspense 1993*, ~207 stories) and were moved to
   `mystery_database/new_sources/_anthologies/_ready/` with the real extraction command handed to
   the owner — **not yet run as of session close.** The other **11 have real detection problems**
   and are intentionally being held back, uncosted: 5 where the detector only caught back-matter and
   missed the entire body of stories, 3 where the whole book got detected as a single oversized
   "story" (459K–533K characters — a full anthology misattributed to one author, not a short story),
   and 3 broken/wrong-fit (one detected 0 stories; one nonfiction true-crime collection flagged for
   a separate taxonomy-fit decision). Full per-file breakdown in `SESSIONS.md` Session 27 — don't
   re-litigate it from scratch, the analysis is already done, just needs someone to act on the
   11 held-back files whenever there's appetite.

   Also unrun this session: the 4-file `_novels/` batch (*39 Steps*, *Behold Here's Poison*,
   *Mystery of the Chinese Ring*, *Whose Body?*) — never got even a `--dry-run` yet.

   **[CHECKED, Session 33 — August 20 2026]** That "next session should check" list is now
   answered, by measurement rather than by asking:
   - **The extraction runs happened.** `mystery_database/extractions/` holds **570 files**, of
     which **281 are `pdf_*`** — up from 75. So the `_ready/` anthology batch (and more) was run.
   - **The registry WAS regenerated — and still lost 13 sources.** Checked-in
     `part_registry.json` was **4,807 parts / 556 sources** against a fresh build's **4,952 /
     569**, so 13 sources and 145 parts were extracted, on disk, and never sampled.
     **Do not read this as "nobody remembered to regenerate" — an earlier draft of this note said
     that and it was wrong.** `20c3ee3` (owner, August 10) is titled "anthology extractions +
     regenerated part_registry" and did exactly that. The 20 extraction files missing from the
     index it produced were added *in that same commit*, and they cluster: ten stories from
     *Best American 2016 (Elizabeth George)* and three from *2007 (Hiaasen)* — the 13 that yield
     parts — plus 7 that yield none (see below). That is the signature of a regeneration run while
     those two books were still extracting, with everything committed together afterwards. Git
     cannot show the ordering (one commit, no intermediate timestamps), but nothing else explains
     the clustering.
     **Why this matters for the fix:** the failure was not neglect, it was a race between a long
     extraction run and a manual regeneration step. Doing the conscientious thing still silently
     lost 13 sources, which is precisely what an automatic check fixes and a reminder does not.
   - **[FIXED, Session 33]** Both halves done, no API calls: the registry is regenerated
     (4,952 / 569 committed), and `load_registry()` now has a real staleness check — see item 14.
   - **[OPEN, found in the same pass] 7 anthology extractions are all-null and contribute nothing.**
     `pdf_the_best_american_mystery_stor__story19_a_quiet_place_to_hide`,
     `__story21_remembering_the_rain`, `__story21_trip_to_reno_...`, `__story22_doggy_style`,
     `__story22_the_heroism_of_lieutenant_wills_...`, `__story22_the_women_s_room`,
     `__story22_these_two_guys_thuglit_november`. Every P1 field is `null` with `confidence: "low"`
     and **no `_meta.extraction_warnings`**, so by item 13's logic they read as a genuine "nothing
     found" rather than a caught parse failure — which is implausible for seven mystery short
     stories. They occupy filenames, so the dedup-by-filename rule means a re-run will skip them
     unless they are deleted first. Worth a look before the next batch; not diagnosed here.

8. **[FUTURE]** Phase 4 — Steam integration (GodotSteam plugin)

9. **[ONGOING]** Repo-wide branch cleanup (Session 18) — 9 fully-merged branches identified as
   safe to delete, plus a further 21 stale unmerged branches the owner is triaging on their own
   schedule (see `SESSIONS.md` Session 18). **`dev/mind-your-friends` is a separate, real second
   project sharing this repo — do not touch it in any cleanup pass.**

   **`dev/cryptic-challenge` is NOT a third project (verified Session 29, August 17 2026).**
   The name has repeatedly been read — including by a Claude session, which cited it as evidence
   of a third studio title — as though it were a sibling of CYM and MYF. It is not. Verified
   against the actual refs, not the name:
   - It points at commit `ea5af2f`, and **`dev/choose-your-mystery` points at the exact same
     commit.** Two names, one ref.
   - That commit is a March 31, 2026 snapshot of the **pre-Godot Streamlit CYM tree** (`app.py`,
     `cli.py`, `corpus_loader.py`, `run_corpus_pipeline.py` — what now lives in `deprecated/`).
   - Zero unique commits vs `main`. Everything on it is already here.
   - Searched every branch's full history: **no file with "cryptic" in its name has ever
     existed**, and no commit message mentions it.

   So it is a stale duplicate pointer with a misleading name — nothing to archive, nothing to
   preserve. Owner cleared it for deletion; it needs the GitHub UI, since `git push --delete`
   hits the same 403 that blocks pushes to `main` and no branch-delete tool is exposed via the
   GitHub MCP server (a Session 29 attempt was also blocked by the permission classifier).
   Recreatable with `git branch dev/cryptic-challenge ea5af2f` if ever wanted.

   **Caveat that outlives the branch:** if a real "Cryptic Challenge" project exists, its work is
   **not in this repo** and deleting this pointer archives nothing. Don't treat the branch as
   that project's record.

10. **[DONE, Session 22; extended Session 26]** RAG (retrieval-augmented generation) for mystery
    best-practices — **wired into generation.** `craft_grounding.py` parses `RESEARCH_FINDINGS.md`,
    `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md` into a retrievable, confidence-tiered
    index and injects relevant guidance into all five generation call-sites in `server/main.py`
    (`_generate_mystery_dict`, `_generate_witness_scene`, `_investigate_area_with_ai`,
    `_follow_lead_with_ai`, and — added Session 26 — `_generate_resolution_narrative`) — full design, rationale table, and extension guide in `docs/WIRING.md`
    → "Craft-grounding retrieval (RAG layer)". Read that section before touching any of it. Zero
    added API calls — retrieval is a local index lookup. Auditable by design: every call records
    which citations it used (routing differs by broadcast scope — see that doc section).
    Remaining open items, not part of this build:
    - Finish verifying `PARTY_CRAFT_FINDINGS.md` against full source text (Session 21's partial
      pass — Jackbox + 3 of 4 Medway posts pasted, findings sorted but not yet written into the
      doc itself) — the retrieval layer works fine on the doc as it stands today, but the
      verification pass is still worth finishing for citation accuracy.
    - True-crime podcast sourcing — the one media type not yet covered; becomes retrievable
      automatically the moment the doc exists, per `SOURCING_METHODOLOGY.md`'s process.
    - Human decision on the accumulated "new concepts flagged" candidates across all three docs
      (e.g. howcatchem structural mode, production-security-as-craft-practice) — whether any
      warrant a new `extraction_protocols.py` code. Explicitly kept separate from "wiring the
      retrieval mechanism" as its own decision (see Session 22's chat log) — not required for the
      RAG layer to work, only for the taxonomy itself to grow.

11. **[IN PROGRESS, Session 21]** Multiplayer lockstep redesign — a live "Murder on Mars" use-case
    walkthrough against the actual running code (not this file's aspirational description) found
    real gaps: the "75%-random-share" mechanic described above doesn't exist in the code (real
    mechanic: player-choice minimum-share threshold, 50/60/70% by difficulty); interrogation was
    free text, not a pick-list; and **there is no backend endpoint anywhere for resolving a
    multiplayer accusation** — the only accusation code (`accusation.gd`) is single-player-era,
    client-local. Full design in `docs/WIRING.md` → "Multiplayer lockstep round system". Built and
    verified so far: the lockstep round state machine (`stage`/`round`, additive alongside the
    legacy per-player `phase` — nothing existing broken), and the witness interrogation redesign
    (batched, deduped, shared-scene generation replacing N isolated per-question calls). Still
    open, in dependency order: accusation-resolution backend (independent, also unblocks the
    end-game resolution/summation scene); crime-scene investigation redesign and the "what I know
    vs. what's shared" comparison screen (both depend on the lockstep mechanism, now in place);
    lead-claim reservation + scaling lead count to max players (8, per item 4's Phase 3e decision).

12. **[PARTIALLY FIXED, Session 22 audit / Session 23 fix]** Extraction-pipeline efficiency gap,
    found while auditing whether extraction actually supports the coherence engine's dialogue
    generation — two concrete, code-verified issues:
    - **[DONE, Session 23]** Even fully P1+P2-depth sources had craft-relevant fields
      (`clue_fairness`, `media_and_audience`, `investigator_wound`, `victim`, `resolution`,
      `investigator`) that the registry extracted and then never read, for any source, at any
      depth — confirmed against a real `ebook_*` extraction (14 populated fields, only 8 ever
      read). Fixed by extending `part_registry.py`'s `KEY_TO_IDX`; see item 14 below for the full
      fix (also resolved the pre-existing `evidence_type`/`alibi` axis mislabeling in the same
      pass). `media_and_audience` remains deliberately unmapped — no honest fit among the 8 axes.
    - **[FIXED, Session 34]** `_atomize_extraction()` now maps 7 of P3's 8 keys
      (`setting_as_constraint`→2, `victims_enemies`→3, `suspect_wounds`→4, `false_suspect`→5,
      `unreliable_frame`/`technical_detail`→6, `moral_ambiguity`→7). `evidence_type` stays
      unmapped for the same reason as `media_and_audience` — axis 8 was *named* evidence_type
      until Session 23 renamed it to `alibi` precisely because it held alibi content, and
      mapping F5 there would recreate that mislabeling. `REGISTRY_SCHEMA_VERSION` bumped to 3.
      The re-extraction now runs **P1P2P3**, not P1P2: P3 costs ~$2 more in the same pass and
      ~$8 more as a later one, and P3.F4 "setting as constraint" is the spatial-device field
      (measured on *The Red House Mystery*: *"an office reachable only through a passage of
      spring-hinged doors, plus a secret passage… door movements are legible only as shadows
      on the passage wall"*). Real end-to-end result on that source: **4 parts → 19**.
    - **[SUPERSEDED]** The old note here said `_atomize_extraction()` has no P3/P4-tier keys
      to read, so a P1-only source (all 12 novels + all 63 anthology stories) went from populating
      3 of the registry's 8 sampling axes to 5 of 8 after the Session 23 fix (gained `motive` via
      `victim`, `reveal_mechanic` via `resolution`, `social_dynamic` via `investigator`) — but
      `suspect_archetype`, `red_herring`, and `alibi` still require P2-tier fields
      (`suspect_architecture`, `red_herring`/`clue_fairness`, `alibi`) that a P1-only extraction
      never produces. Only fix: re-extract the 75 P1-only sources at `--protocol P1P2` (new API
      cost, backfills the remaining 3 axes specifically). Full detail in `SESSIONS.md` Session 22.

13. **[DONE, Session 23]** Fixed a silent extraction-failure bug found while reviewing anthology
    output quality: `extract_pdf()`/`extract_pdf_anthology()` used to catch a malformed Claude
    response and silently save the same null-placeholder shape used for a genuine "nothing found"
    result — confirmed on `pdf_the_best_of_mystery_1980_antho__story05_pseudo_identity.json`
    (Lawrence Block's "Pseudo Identity"), which came back all-null with no trace of the failure.
    Fixed via a shared `_call_claude_for_protocol()` helper (retry once, then save-with-warning in
    `_meta.extraction_warnings` on parse failure; raise `ExtractionAPIError` and skip-without-saving
    on a pure API/network failure, preserving the dedup-by-filename retry on next run). Verified
    against the real failing case, not just stubs — owner re-ran extraction locally, the retry
    fired and fixed it, and the resulting file now has real high-confidence data across all 6
    fields. Full detail in `SESSIONS.md` Session 23.

14. **[DONE, Session 23]** Fixed the `evidence_type`/`alibi` axis mislabeling flagged as a known
    caveat in `craft_grounding.py`'s docstring (axis 8 was named `"evidence_type"` but actually
    held alibi content, since the extraction key `"alibi"` mapped there) — renamed the axis itself
    to `"alibi"` in `part_registry.py`, updated `craft_grounding.py`'s `PART_TYPE_TO_TAXONOMY` and
    `coherence_validator.py`'s hardcoded `"evidence_type"` string checks (4 call sites) to match.
    Done together with the item 12 field-mapping fix above, in the same commit, per the caveat's
    own instruction not to do one without the other. Also found and fixed a second, unrelated
    staleness bug while regenerating the registry to verify: `mystery_database/part_registry.json`
    is a checked-in cache with no staleness check (`load_registry()` only rebuilds if the file is
    *missing*, never if it's stale) — it had been silently frozen since March 11, missing ~75
    sources' worth of corpus growth (294 → 369 sources after regeneration; 1,469 → 2,833 parts).
    Regenerated and committed this time, but the root cause is **not** fixed — `load_registry()`
    still has no staleness check, so the next extraction run will silently go stale again until
    someone manually deletes `part_registry.json`. Worth a real fix (e.g. mtime comparison against
    `extractions/`, matching the pattern `craft_grounding.py`'s index cache already uses) as a
    follow-up, not done this session. Full detail in `SESSIONS.md` Session 23.
    **[RECURRED AND NOW FIXED, Session 33 — August 20 2026]** It went stale again exactly as
    predicted — 4,807 parts / 556 sources checked in versus 4,952 / 569 on a fresh build, i.e. 13
    sources extracted at real API cost and then never sampled. Regenerated, and the root cause is
    now closed:
    - **The check is a corpus fingerprint**, written to a sidecar `part_registry.meta.json`: the
      hashed set of extraction filenames plus a schema version. Filenames are the right unit
      because `load_extractions()` derives every `source_id` from the filename stem, so a change
      to that set is exactly a change to the sources covered.
    - **Not mtime-based, on purpose** — unlike `craft_grounding.py`'s index cache, which this item
      originally proposed copying. A fresh `git clone` stamps every file with the checkout time,
      so mtimes here carry no information about what was built when; comparing them would either
      miss real staleness or rebuild on every clone.
    - **[Session 35] The fingerprint now hashes file CONTENTS too, not just the name set.** The
      original filename-only version documented its own blind spot — "an extraction file edited in
      place under the same name is not detected, pass `force=True`" — and that turned out to be
      the exact shape of the P1→P1P2P3 upgrade, which rewrites an extraction under its own name
      and takes it from ~6 parts to ~20. The first 7 upgraded stories landed with
      `load_registry()` reporting itself fresh and **98 parts unsampled**. The written warning did
      not save it, which is the argument for checking over reminding. Hashing all 571 files costs
      ~11 ms and is clone-stable, so there was never a reason to approximate it.
    - **`REGISTRY_SCHEMA_VERSION` covers the other staleness mode**, which no amount of looking at
      the corpus can catch: Session 23 changed `KEY_TO_IDX`, so identical files produced different
      parts and the cache had no way to know. Bump it whenever `_atomize_extraction` / `KEY_TO_IDX`
      / `PART_TYPES` changes what a given extraction yields.
    - **`scripts/test_registry_staleness.py`** (new, zero API cost) asserts both halves — a
      moved-on corpus rebuilds, and an unchanged one does *not*, since the cheap way to pass the
      first is to rebuild unconditionally. The second is proved by corrupting the cached file and
      confirming the corruption survives.

15. **[DONE, Session 26]** Room-first lobby + prompt suggestions, end-of-game resolution reveal,
    and post-game voting + same-room replay — three-piece feature set, built and verified
    incrementally per explicit owner request. `POST /games/create` now opens an empty room;
    players suggest prompts while waiting; the host's own submission drives generation on
    `POST /games/{id}/start`. On a win, `GET /games/{id}/result`/`game_won` return `plot_reveal`
    (the mystery's own solution reformatted) + `winner_findings` (the winner's own findings,
    shown to the whole room) + `resolution_narrative` (one Claude call, craft-guidance-informed —
    the RAG layer's fifth call-site, tagged `C5`/`M6`/`"Accusation/Reveal Phase"` — generated once
    and cached, never regenerated on a later fetch). New `round_type: "prompt_vote"` lets the
    group pick what to play next from the leftover suggestions; ties go to the game's winner
    unless they also won the mystery immediately before this one, in which case it's random
    instead (`game["win_history"]` tracks this). `POST /games/{id}/next-mystery/start` resets the
    same room in place — same `game_id`, same players, nobody rejoins — which is the actual point:
    subtly encouraging the same group to keep playing together. Video generation stays explicitly
    tabled. **[CORRECTED, Session 35] This item used to claim the client "renders a static
    `Video Scene Will Play Here` placeholder." It does not — that string appears in no `.gd`,
    `.tscn`, `.html` or `.py` file, and nothing occupies that slot today.** What DOES exist,
    unused, is `_generate_cinematic_brief()` (`server/main.py:335`), which returns both a
    player-facing `opening_narration` ("3–5 sentences of atmospheric prose… displayed or read
    aloud to players") and a hidden `cinematic_brief` shot list for a future video generator. It
    is gated behind `cinematic_brief: bool = False` and has never run — the one real generated
    mystery on disk carries neither key. The playtest opening should turn that flag on; see
    `docs/PLAYTEST_FLOW.md` → "The opening sequence". Full detail,
    including a real `_craft_guidance` leak this work found and fixed in `winner_findings` (private
    per-player audit citations were about to broadcast to the whole room), in `SESSIONS.md`
    Session 26 and `docs/WIRING.md`'s three new sections.

16. **[DONE, Session 28]** Coherence engine unification — CYM side, first of eventually every
    title. Owner priority: the "Coherence Engine" pillar in the studio funding pitch needs to be
    real, not aspirational, and CYM was the safe place to start (same language, same repo, no
    cross-language bridge — unlike MYF, which is JS today). Brought the `coherence/` package
    (`Issue`/`CoherenceReport`/`RuleSet` base classes) over to `main` — it previously existed
    **only** on the stranded `dev/mind-your-friends` branch, despite `docs/WIRING.md`'s prior
    phrasing implying it was already shared. Refactored `coherence_validator.py`'s two entry
    points into real `RuleSet` subclasses (`MysteryPartsRuleSet`, `MysteryRuleSet`); `CoherenceReport`
    here now extends the engine's base class, keeping the inherited `issues` field in sync as the
    union of CYM's categorized `p1_issues`/`scene_issues`/`part_issues`. `check_parts()`/
    `check_mystery()` kept as thin wrapper functions with unchanged signatures — zero call-site
    changes needed in `server/main.py` or `deprecated/cli.py`. Verified both the pass and fail
    paths against realistic mystery dicts, and confirmed `MysteryRuleSet().run(mystery)` called
    directly produces identical results to `check_mystery(mystery)`. Full detail in
    `docs/WIRING.md` → "Coherence validator — what it checks". **MYF's side is deferred until its
    own Python port lands** (see MYF's `CLAUDE.md` item 31/32) — its `lib/coherence.js` is
    JavaScript and can't subclass a Python `RuleSet` without a bridge, which is exactly the
    premature-integration mistake this sequencing avoids. Branch: `claude/coherence-engine-unification`.
    **[COMPLETED, Session 33 — August 20 2026] MYF's Python side is now wired, so the pillar has
    two real consumers.** `mind-your-friends/server_py/coherence_rules.py` (renamed from
    `coherence.py`, which it had to be — a top-level module named `coherence` and the `coherence`
    package cannot both sit on `sys.path`, and `server_py/` always wins, so the import resolved to
    MYF's own file) defines `QuestionRuleSet`, a real `coherence.engine.RuleSet` subclass.
    `mind-your-friends/server_py/test_coherence_engine.py` asserts that both titles use the
    **identical** `RuleSet` / `CoherenceReport` / `Issue` classes rather than two copies that
    merely share field names — the check that would actually catch the framework forking. Full
    detail in MYF's `CLAUDE.md` item 51.

17. **[PARTLY BUILT — designed Session 33, layout written since, wired to nothing] CYM BACKGROUND
    — the mystery's own title as the page texture.** Owner-initiated: bring MYF's look and feel
    across to CYM. Two questions are still open (below) and both are the owner's.

    **The "nothing has been written" line this item used to carry is stale, and was already stale
    when written down.** `background_field.py` exists at root, is tested by
    `scripts/test_background_field.py`, and computes the whole seeded layout — 294 lines, with its
    reasoning recorded in place. What does NOT exist is any wiring: no server endpoint returns it,
    and neither client draws it. So the correct status is *layout built, unrendered*.
    - **[Session 37] It can now be looked at.** `scripts/preview_background_field.py` renders the
      field to SVG at the host viewport's own size with a real screen's text over it — prose on
      the ground (the hard case) and on a panel — which is what this item's own instruction
      (*"Test on a real screen; do not settle it by argument"*) asks for and what nothing
      previously made possible.
    - **[Session 37] The ground is now painted**, as `default_clear_color` in `project.godot`.
      That is this item's specified pre-prompt state — ground colour alone until a mystery is
      named — reached without deciding anything about the field itself.

    **Shared vocabulary (owner-defined — use these names).** MYF's `CLAUDE.md` glossary already
    defines two of the three; BACKGROUND is new and belongs in both files:
    | Term | MYF today | CYM equivalent |
    |---|---|---|
    | **BACKGROUND** | slate ground + strewn faded question marks | slate ground + the strewn mystery TITLE |
    | **LOGO** | the three-emoji mark, top centre | none yet — not part of this |
    | **TITLE TREATMENT** | the logotype, top left | none yet — not part of this |

    **What CYM gets, and what it does not.** CYM gets the *system* — a ground colour plus a faded,
    strewn, rotated, randomly-sized mark tile — **not the motif**. The question marks stay MYF's
    (owner, explicitly). CYM's marks are the mystery's own title, so the two titles read as
    siblings rather than as one game reskinned. This **reverses MYF item 39's** "scoped by owner to
    MYF only, do not generalise into a cross-title design layer" — knowingly, at the owner's
    direction. MYF item 39 needs that line rewritten when this is built.

    **The state machine.** Ground colour alone until a mystery is named; the field then builds in,
    and re-skins on same-room replay (`prompt_vote` → `next-mystery/start`), which is a free payoff
    of the same mechanism.

    **How the title arrives — the owner's answer, and it is the better one.** The first design
    routed around the fact that `title` does not exist until generation ends (112s–1992s, per the
    real batch summaries): stream the generation call, parse `title` out early since it is field #1
    in the schema, add a `short_title` beside it. That works and costs no extra API calls, but it
    changes the main generation path. **The owner's proposal supersedes it: prompt the player for a
    title alongside the setting, and use theirs.** No streaming, no schema change, nothing touching
    `llm()`, and the original spec ("plain until the prompt is entered, field after") becomes
    literally true. It is also closer to what players already do — `submit_prompt`'s own docstring
    examples are "Smurf murder mystery" and "Mystery on Mars", i.e. already title-shaped.
    Keep the streaming approach in the back pocket **only** as the fallback for a blank title.
    - "Encapsulated" = **as few words as possible** (owner). With a player-supplied title this is
      enforceable at the input (`maxlength` + placeholder) rather than hoped for from generation —
      which matters, because the 16 real titles on disk run 8 to 39 characters and a field of
      "Whiteout" behaves nothing like a field of "Daggers in the Forum: The Ides of March".
    - Free win: leftover suggestions already drive the post-game `prompt_vote`; if each carries a
      title, that screen becomes a list of *named* mysteries instead of raw setting text.
    - The change is small: one field on `SubmitPromptRequest` and on the stored
      `{name, prompt_text, ts}` dict in `submit_prompt` (`server/main.py`).

    **Architecture (decided): the server computes the layout, both clients render it.** CYM has
    **two** clients — the Godot host screen and `server/static/mobile.html`, the phone client every
    player actually looks at. The server emits a seeded layout (`{text, x, y, rotation, size,
    colour}`); Godot draws it in `_draw()`, the phone as inline SVG. One implementation, two
    surfaces, and the TV and every phone show the identical field. Shipping an image instead would
    mean rasterising for Godot and a data-URI for the phone — two renderers and two chances to
    drift.

    **Risks, in the order they will bite:**
    - **Moderation is the real one, and it is new.** A player-supplied string rendered large,
      repeated, on every screen, for a whole game, on a TV, in a Steam title. It is the
      highest-visibility user-generated content surface in the product. MYF already built
      `moderateHeckle()` for a far *smaller* surface. It cannot ride along on generation, because
      the background appears before any Claude call — so it needs handling at submit time, which is
      its own API call or a local filter.
      **[DECIDED, Session 34 — August 21 2026] None yet.** No filter and no moderation call: the
      room is people who chose to play together and can see who typed it. What ships instead is a
      **visible disclaimer under the prompt entry box — "Not moderated for play testing"** (live in
      `godot/scenes/ui/MysteryGeneration.tscn` as `VBox/ModerationNoticeLabel`). It does two jobs:
      it is cover during play testing, and it is a standing reminder that this is unresolved, so
      the decision cannot quietly become the status quo by being invisible. **It is not a Steam
      answer** — a TV-sized, whole-game, user-typed string still needs a real one before release.
      When the phone client finally grows a prompt-suggestion box (Session 26's room-first flow is
      server-only today — `server/static/mobile.html` has no prompt entry at all), the same line
      goes under it.
    - **Legibility.** MYF sits at 10% mark strength for an abstract glyph. Words are read
      involuntarily, and CYM's screens carry far more text (clues, transcripts, evidence). Expect
      to need *below* 10%, plus rotation and edge-cropping so most instances are partial. Test on a
      real screen; do not settle it by argument.
    - **Fonts:** OFL-licensed only (owner). One existing title is "Schatten am Checkpoint", so
      localisation means non-English titles and the set needs the glyph coverage. Note MYF draws
      its marks as **geometry, not font glyphs**, precisely because a background `<text>` renders
      in whatever font the machine has — that concern returns for the phone client, which needs the
      faces actually loaded or the two screens will not match.

    **The two open questions — question 1 is answered, question 2 is half-answered:**
    1. **Moderation** — **answered, Session 34: none yet, disclaimer instead.** See the risk entry
       above for what shipped and what it does not cover.
    2. **Does the player's title feed INTO generation, or only decorate?** Owner, Session 34:
       *"Title is just for generation, but should also be used in a drop down menu of reusable
       mysteries."* So the title **feeds generation** — it is not decoration-only — and it is the
       handle the saved-mystery list is browsed by. **Still to pin down before building:** whether
       "just for generation" also means the BACKGROUND field should be strewn with something other
       than the title, or with the title as well. Do not assume; ask.
       The slug wrinkle stands either way: the saved-mystery slug derives from
       `mystery_dict["title"]` (`server/main.py`), so decide whether the player's title *replaces*
       Claude's or sits beside it. Recommendation: replace, with Claude's as the blank-field
       fallback — the dropdown then lists what the player named, which is the point of question 2.

    **Reusable-mystery dropdown — it exists, and Session 34 fixed it.** Owner asked whether it was
    still in the build. It is, on the Godot host screen only: MainMenu's "Browse Saved Mysteries"
    → `GET /mysteries` → a popup `ItemList` labelled by each mystery's `title`. **It had been
    inert since it was written** — `main_menu.gd` connected its four buttons and none of the
    popup's own signals, so `_on_browse_item_selected` was dead code, clicking a row did nothing,
    and the window could not even be dismissed (a Godot `Window` does not hide itself on
    `close_requested`). Now wired. Two things it still is not:
    - **Single-player only — and that is deliberate, not a gap.** Selecting a saved mystery goes
      straight to `CaseDisplay.tscn`. The server has supported multiplayer reuse all along
      (`CreateGameRequest.mystery_slug`, "skip prompt-collection, attach an already-generated
      mystery immediately"), but no UI reaches it. This was raised as a next step and the owner
      pointed at the Delivery Priority section above: group replay is a stage-3 feature. The PC
      playtest needs one person at one machine replaying a saved case, which is exactly what the
      single-player route already does.
    - **Absent from the phone client.** `mobile.html` has no mystery list.

    **Brand artwork — where it stands (Session 33).** `brand/` holds four files and a README.
    `negative_logo.svg` / `organic_logo.svg` were the first pass: raster PNGs in an SVG wrapper,
    not vector, and `organic_logo.svg` carries an export artifact of 22,445 opaque pixels outside
    its viewBox. `NEWnegative_CYM.svg` / `NEWorganic_cym.svg` are the owner's re-cut and are
    **genuine vectors** — 66 and 126 `<path>` elements, zero base64. That was the stated goal and
    it is met.
    - **The contrast problem is unchanged, and that is expected** — the re-cut converted format,
      not values. Measured on the slate ground by `scripts/check_brand_contrast.py`: the negative
      mark went 49% → 53% of ink at or below 2.5:1, the organic monogram 49% → 73%. The monogram's
      *outright invisible* band did drop from 22.7% to 0.1%, but it moved into "barely" rather
      than up the scale.
    - **Being vector now makes the fix cheap and safe**, which is the real payoff. A value
      re-pitch is a fill-colour rewrite across the paths, not a pixel filter. Worth knowing why
      that matters: the pixel filter tried in this session produced rainbow speckle on the
      negative mark, because its near-black regions have near-zero saturation with tiny hue noise
      and raising lightness amplified that noise into visible colour. On vector paths there is no
      noise to amplify.
    - **Neither mark is wired to any client.** No CYM screen references either file. They are
      artwork plus a measurement, not implemented chrome.
    - **The structural question is still open and is the owner's:** these are specified as
      *different marks per device* — negative mark upper-left on desktop/TV, organic monogram top-
      centre on phones. Unlike MYF, CYM's Godot host screen and its phone clients are in the same
      room at the same time, so the room would display two identities simultaneously. That may be
      wanted (a TV poster and a phone icon); it should be decided rather than arrived at.
    - Also unresolved: the negative mark reintroduces a question-mark motif to CYM, which item 17
      otherwise scopes to MYF. A noir question mark is a different object from a strewn field, so
      this may well be fine — but deliberately, not by drift.

    **[DECIDED, playtest StartPageSept7] The desktop half.** Owner: put the logo upper-left on
    every screen. That is the negative mark, at the exact placement this item already specified
    for desktop/TV — so the "different marks per device" question above is now answered for the
    Godot client specifically, not for the room as a whole. The phone half (organic monogram,
    top-centre) is untouched and still open; `mobile.html` has no chrome pass of any kind yet, so
    there is nothing there to place it against. The question-mark-motif point directly above was
    NOT re-litigated when this was asked — flagged to the owner in the same turn the mark was
    wired in, not decided unilaterally either way.

    **Built as `godot/scripts/autoloads/Chrome.gd`**, a fifth autoload, for the same reason
    `Style.gd` is one: `change_scene_to_file()` discards and rebuilds the current-scene tree
    wholesale, so anything living inside a `.tscn` needs adding nine separate times today and
    again for every screen this project ever grows. Chrome adds its `CanvasLayer` straight to
    `get_tree().root` in `_ready()`, which survives every scene swap for free. Also built:
    `scripts/build_brand.py`, the same "generated, then checked" mirror `palette.py` and `icons/`
    already use, copying `brand/NEWnegative_CYM.svg` byte-exact into
    `godot/assets/brand/negative_mark.svg` — no recolouring, because a brand mark is a fixed
    identity rather than a retintable icon, which is exactly the distinction `build_icons.py`
    draws for the OTHER direction (why it recolours the clue/witness sets and this script does
    not).

    **The contrast measurement above is unchanged and was surfaced again before wiring anything
    in**, not silently inherited: 53% of the negative mark's ink still sits at or below 2.5:1
    against the slate ground. This is a property of the artwork, not of the wiring, and fixing it
    means re-pitching fill values on the source SVG — a decision for whoever owns the mark. Flagged
    to the owner in the same turn rather than left for a screenshot to surface on its own.

    **Unrelated, noticed while checking and worth one look before building on generation:** an old
    batch summary in `mystery_database/generated/` shows **13 of 14 generations failing** on JSON
    parse errors (`Unterminated string`, `Expecting property name`). It is from March and 16
    mysteries have generated cleanly since, so it is probably long fixed — but a background keyed
    to the title inherits whatever the current failure rate is. Worth one real generation run to
    confirm before building on top of it.

18. **[CLOSED, Session 41 — September 3 2026] A BLOCKING coherence report does not stop a
    mystery being saved, served, or played.** Not a coherence-engine failure — the opposite. The
    engine catches this exactly: `P1.C4.culprit_not_in_characters`, severity `BLOCKING`, message
    *"Chain is broken; players can never identify them."* `_run_coherence()` records the verdict
    into `_coherence` and the pipeline then saves and serves the mystery regardless.
    Live example on disk: `the_stolen_star_of_smurf_village_1775239921.json` recorded
    `{"passed": false, "blocking": 1}` and is fully playable — its two-culprit `solution.culprit`
    is prose, so under `accusation.gd`'s original exact-match every accusation was wrong,
    including both correct ones. **The game could not be won, and the player was told they were
    wrong.**
    Session 34 fixed the *symptom* at two altitudes (substring matching in `accusation.gd` with a
    short-name guard; an on-screen warning when no suspect can be the answer) and added
    `scripts/check_mystery_playable.py` to catch it before a playtest. The cause stayed open as a
    design call: refuse to save, retry, or serve with a louder warning? Retrying costs API calls,
    which is why it was not decided unilaterally.

    **[Session 41] The data reframed the item before it was answered.** Asked whether "poor" meant
    "fails coherence", the disk said no, and said it backwards: **all four mysteries in
    `rejected/` PASSED coherence with 0 blocking**, and the one file that FAILED it was sitting in
    `generated/`, servable. So the gap was never only "BLOCKING mysteries get served" — it was that
    **nothing routed anything**. Every one of those four rejections had been carried out by hand.

    Four kinds of bad generation, and coherence catches the rarest:

    | Class | Means | The case that named it |
    |---|---|---|
    | *incoherent* | the story does not hang together | `the_stolen_star_of_smurf_village` |
    | *unplayable* | the story is fine, the game cannot be assigned or won | `the_lantern_keeper's_last_light` |
    | *spoiled_prose* | every field correct, the text gives the answer away | `the_light_that_went_out` |
    | *below_standard* | playable, winnable, not good enough to serve | `totality` |

    **Owner's decision: option (c) — auto-route on ANY failing check**, coherence and structural
    alike, because the checks are free (no API call, so no cost argument against them) and because
    the sentence worth having is not *"our engine detects incoherence"* but *"nothing reaches a
    player that our checks cannot prove is solvable, and here are five we caught, with reasons."*
    Built as `gate.py`: `generated/` now means *no check we own can prove this is broken*.

    **A fourth option nobody had in August: quarantine.** `rejected/` did not exist when this item
    was written. It costs no API call — which is what killed *retry* — and it keeps the mystery,
    because each one is paid-for evidence that a rule was needed.

    **Auto-reject, never auto-repair.** A gate can only be conservative: it can wrongly refuse a
    good mystery (annoying, recoverable, nothing is deleted) but it cannot manufacture a bad one
    that looks good. A repair loop iterating a model against these checks until they go green would
    stop selecting for good mysteries and start selecting for mysteries *shaped like the checks* —
    Goodhart, and `the_light_that_went_out` is the standing proof, since it passed every structural
    rule and gave its answer away in prose.

    **Three judgement calls inside the build, each deliberate.** CAST/ORPHAN findings are recorded
    but never blocking, because `check_narrative.py`'s own header documents them as
    false-positive-prone and *"a list to triage, not a verdict"*. Legacy mysteries are `unjudged`
    rather than accepted or rejected — all 17 in `generated/` predate the Session 38 schema, so
    rules defined over `exonerates` / `narrows` / `reveals` fire trivially on every one, and gating
    them would have emptied the served library over rules that did not exist when they were
    written. Coherence is the exception, because it never depended on those fields — so exactly one
    file on disk moved, and it was this item's original case.

    **The other half: the ledger.** See item 28 — the same change records what each attempt cost,
    because the routing decision and the failure corpus are one write.

19. **[READY TO RUN — blocked on credits, not code, as of Session 35] The corpus P1→P1P2P3 upgrade.** 75 sources are P1-only (206 of
    281 `pdf_*` are already P1P2). `python3 scripts/upgrade_p1_to_p1p2.py` prints the plan and
    spends nothing; `--go` runs it on `claude-opus-5`, ~$0.147/source. Verified end to end on
    *The Red House Mystery*: **4 parts → 19**. Every failure mode and its fix is in
    `docs/EXTRACTION_TROUBLESHOOTING.md`; the run is idempotent and resumable, and replaced
    extractions are archived to `extractions/_superseded/`, never deleted.
    **Why P1P2P3 rather than P1P2:** P3 costs ~$2 more in the same pass and ~$8 more as a later
    one, and P3.F4 "setting as constraint" is the spatial-device field the CLOUD idea needs.
    **[Session 35] The run was attempted and hit an exhausted Anthropic credit balance partway
    through.** The failed calls cost nothing (400s are rejected before inference) and wrote nothing
    (the failure path saves no placeholder), but **7 stories of the Hitchcock 1980 anthology
    upgraded successfully first** — the queue is sorted by extraction count, so the 63-story
    anthology ran ahead of the novels. Those 7 are real paid-for work; check for them with the
    two-list pattern in `docs/EXTRACTION_TROUBLESHOOTING.md` and commit before re-running. Top up
    and re-run the same command for the rest. What Session 35 *did* fix is that the run did not stop on its own: it
    retried an unretryable billing error, and `upgrade_p1_to_p1p2.py` — which runs the extractor
    once per source **as a subprocess** — kept going through every remaining PDF because it read
    only `if rc != 0`. Related, found in the same pass: `extract_from_pdfs.py` exited 0 however
    many sources failed, so that wrapper's failure tally had never been reachable. Both fixed,
    with `scripts/test_extraction_fatal_errors.py` covering it end to end.

20. **[SUPERSEDED IN PART, Session 35 — see `docs/INVESTIGATION_DESIGN.md`] CLOUD — a
    manipulable top-down crime scene.** The design conversation that followed replaced the
    *top-down* part: a floor plan hard-codes a building (`crime_scene_map._row_rects` packs
    rectangles; a Black Forest renders as a ravine in a 308×289 box), and the owner's Dick
    Francis case — racetrack, stables, country estate, lawyer's office — settles it. **A
    connection map replaces it.** That conversation also turned up three live defects underneath
    the UI question: fabricated witness placement, a phase-gate deadlock (item 21), and a
    solvability rule that checks a weaker thing than its own error message claims. Read
    `docs/INVESTIGATION_DESIGN.md` before touching any of it — the assessment below is still
    accurate about the corpus and about schematic-vs-photoreal, and is kept for that.

    **Original Session 34 assessment:** After the
    inciting-incident video the interface becomes a top-down scene players traverse. Assessed
    against the data, not speculation:
    - **The corpus holds no spatial structure** — space appears incidentally at 2–14% across 564
      extractions, never as layout, adjacency or sightline. It does not need to: CLOUD's geometry
      comes from generation, which already *knows* the spatial facts as prose (evidence E2 is
      named "…(found in Generator Room)"; `solution.method` is the culprit's route in sentences).
      **Missing are fields, not knowledge:** `area_id` on evidence, adjacency between areas, and
      the culprit's path as a sequence — a schema change to a call already being paid for.
    - **The schematic and the photo-real reference are different kinds of thing.** The schematic
      is *data rendered* and is nearly buildable now (`crime_scene_map.py` already draws rooms and
      witnesses). The photo-real image is *presentation*, needs an image model, and is stage-3
      money. Do not conflate them.
    - **What transfers between a country house and a Mars dome is the spatial *device*, not the
      geometry** — and P3.F4 "Setting as Constraint" captures exactly that, as a relation rather
      than a floor plan. That is why the corpus run is now P1P2P3.

21. **[CLOSED BY APF — found Session 35; superseded by item 23. Kept because the diagnosis is
    the reason APF exists.] The investigation phase can DEADLOCK, and it is
    not an edge case.** Sharing is the only exit from a phase (`player["phase"]` advances in
    exactly one place, inside `share_findings`); you cannot share nothing
    (`if not all_findings: raise HTTPException(400, …)`); and every area can be blocked before you
    act. A player reaching the investigation phase with all 5 areas already shared gets 409 on
    every room, 400 on share, and **cannot advance, ever.** Every difficulty at every player count
    wants more investigations than there are areas — MEDIUM 4-player wants 8 against 5; HARD
    8-player wants 16. Root cause is the **phase gate** (lines 2076/2130/2363), not the block
    pool: a player locked into `investigation` cannot do the witness or lead work sitting right
    there. It **was** a stage-1 playtest-killer — it ends with someone staring at a screen that
    rejects every button.

    **Do not go and fix this.** APF assigns findings instead of letting players gather them, so
    there is no phase to be trapped in, nothing to block, and every player holds findings by
    construction. The mechanic that carries the bug is gone (`docs/INVESTIGATION_DESIGN.md` §5,
    fix 0). The diagnosis stays on the record because the phase gate returns with any future
    gathering mechanic, and because it is the clearest single argument for APF.

22. **[DONE, Session 36 — August 26, 2026] The Godot F5 ran.** The client has been launched in the
    engine, by the owner, on their machine. It reached the main menu with the backend connected,
    and a saved mystery loaded from the browse list into `CaseDisplay` and rendered. Owner's
    verdict: *"it ran, it's ugly, but it works."* Ugly is a stage-1 pass — the screens were built
    to be wired, not styled.

    **It found two defects in the first twenty minutes, and the checker had passed both files.**
    - `case_display.gd:140` — `var relevance_icon := {…}.get(…)` inferred `Variant` from
      `Dictionary.get()`, which the engine treats as an error. Fatal at *parse* time, so
      `CaseDisplay.tscn` never loaded at all. Fixed by stating `: String` (`e461ef5`).
    - `Interrogation.tscn` used `##` section headers. **A `.tscn` comments with `;`; a `#` line is
      garbage to the scene parser and the node declared immediately after one is dropped when the
      scene loads.** Five panels and all their children were null at runtime — the survivors were
      exactly the nodes with no `##` above them (`7cbacd1`).

    **The lasting finding is the checker's false pass.** `check_godot_wiring.py` reads
    `[node name=…]` with a regex, so it saw all 21 of that scene's nodes and confirmed every
    `$NodePath` resolves, while five panels were missing at runtime. **Reading a scene is not the
    same as loading it.** Both defects lived where the checker's model of the project diverges
    from the engine's — one in the type system, one in the file format. The checker now fails on
    `#` in a `.tscn`; there is no equivalent guard for the type system, and short of running Godot
    there cannot be. Treat "the checkers pass" as *necessary, not sufficient*, and say so when
    reporting status.

    **The free route is now complete.** The accusation dropdown, the result screen, rating
    persistence, both navigation exits, the Smurf substring regression (both correct answers come
    back correct) and the repaired interrogation screen have all been walked and pass. A third
    defect surfaced and was fixed on the way: `result_screen.gd` relied on implicit string
    concatenation, which GDScript does not have, so the script failed to parse and the screen
    rendered its static nodes only — no verdict, no solution, no rating buttons, and no runtime
    error to explain it. The same pattern was found and fixed on the multiplayer share path
    before it could be hit (`102e2be`).

    **Still unverified: only the two paid steps** — one interrogation call and one generation.
    Plus one gap inside a passing step: the Smurf negative case (accusing Smurfodex, which must
    read *wrong*) was not run. The procedure and its live Status line are `docs/F5_CHECKLIST.md`.

23. **[STEPS 1-4 BUILT, Session 42 — what is left is a table, not code] Build APF.** The playtest shape is agreed and written down:
    `docs/PLAYTEST_FLOW.md` → "APF (All Provided For)". Findings are **assigned, not gathered**; the
    only decision is which to share and which to keep, which is the mechanic this file's first
    paragraph calls the core innovation. It deletes exploration, the block pool, the phase gates
    and item 21's deadlock outright, and drops play-time API cost to roughly zero.
    Order (from `docs/INVESTIGATION_DESIGN.md` §7, reduced by APF):
    1. ~~`exonerates` / `implicates` on evidence + the set-arithmetic solvability check~~ —
       schema half landed Session 38 with the backwards-writing reorder (item 26).
    2. ~~the constrained assignment — pure computation, re-runnable at zero cost~~ — **[Session 39]
       built as `casefiles.py`.** See below.
    3. ~~the share decision, the suspect board, the reveal~~ — **[Session 42] built.** See below.
    4. ~~`cinematic_brief: bool = True` for the paced text opening~~ — **[Session 40]**
       `_generate_opening_narration()` writes it, on by default. Pacing the beats is client-side
       and free; that screen is unbuilt.

    **[Session 42] Step 3, and the shape it took.** `apf.py` owns the RHYTHM; `casefiles.py` still owns
    the CASE. That split is the whole design: which findings land in whose casefile is a solvability
    question with a proof attached, and when each is turned face up is a pacing question with none.
    Six `/apf/` routes serve it, all set arithmetic over an already-generated mystery, so a whole
    game costs exactly what its one generation call cost.

    **The share and the board are ONE screen, and that was a decision.** `ShareSelection.tscn` was
    already built as a separate screen for the gather loop and it is untouched. Under the rhythm the
    share belongs beside the board, because the board is what makes withholding legible without a
    word of explanation: a face stays lit that you could have darkened, and everyone can see you
    didn't. A separate screen hides the one thing that gives the decision weight.

    **The board greys on `exonerates` and NEVER on `narrows`, even though `casefiles.solves()` counts
    both.** Item 27 is explicit that a narrowing must never surface as "the culprit is one of these
    two" — the clue says *man's size large* and the player looks at the cast and draws the line. A
    board that greys a face on a narrowing does that reasoning for them and deletes the mechanic it
    was built to serve. Asserted by a fixture, not left to a comment.

    **Two defects found by RUNNING it, which no reading would have caught.** (a) `best_assignment()`
    forwarded `hoard_allowance` into `assignment()` but not into the `prover_counts()` call it *selects*
    the seed with — so a session whose rules permit a two-finding stash constrained proof-survival
    at two and then chose its assignment by a monopoly measured at one. Only reachable once something
    derived the allowance instead of taking the constant, which `apf.stash_allowance()` does.
    (b) **Winning the game fired a live Claude call.** `_generate_resolution_narrative` is the last
    play-time call site on the critical path, and a 401 took the whole win down with a 500. The
    stage-1 test is *reach the result screen without an error*, so the reveal now degrades to the
    mystery's own already-generated resolution prose. Build-order step 5 still has to remove the
    call; this stops it being fatal. `_winner_findings_summary` was also reading the gather loop's
    phase lists, which under APF are empty — it now reads the assigned casefile.

    **Verified two ways, both free.** `scripts/test_apf.py` proves the rules in-process (58
    assertions, fixtures plus one pass over the accepted mystery at all three difficulties);
    `scripts/walk_apf_game.py` plays a whole four-round game over real HTTP **with no API key at
    all**, which is how both defects above were found.

    **Not verified: it has never run in Godot, and nobody has played it.** The scene and scripts
    pass `scripts/check_godot_wiring.py`, which reads scene files rather than loading them —
    necessary, not sufficient. And every number in the difficulty ladder is arithmetic: whether a
    two-finding stash at HARD *feels* like a decision is a question only a table answers.

    **[Session 39] Step 2's blocker was real and pointed at the wrong code.** Session 38 recorded
    it as *"a finding carries no evidence ID"* in the three finding constructors — but those are
    the **gather** routes (`/investigate-area`, `/follow-lead`, `/interrogate-witness`), and APF
    deletes gathering. A assigned clue **is** an evidence item and carries its own id, so there is
    nothing to join.

    **The gap that actually blocked the assignment is larger and was not listed anywhere.** APF's casefile
    is one witness statement, one crime-scene clue, one lead result, and `exonerates` /
    `implicates` live **only** on `evidence[]`. Witness statements, leads and area discoveries
    carried no elimination data at all, so **two of the three kinds in every casefile were
    structurally inert** — they could not participate in the set arithmetic that all three assignment
    constraints are defined over. An assignment cannot guarantee "the union eliminates all but one
    suspect" when two thirds of what it assigns eliminates nobody by construction.

    **Closed with a `reveals` pointer**, on witnesses, leads and investigation areas, naming the
    evidence ids they surface. Elimination data therefore lives in exactly **one** place, and a
    witness's exoneration cannot drift out of agreement with the evidence item's. The considered
    alternative — copying `supports` / `exonerates` / `implicates` onto every kind — was rejected
    for precisely that reason: two authored copies of the same fact can disagree, and no
    structural check could catch it. Areas carry the field but are **not assigned**, because APF has
    no traversal; they have it so the deferred map does not cost a second paid generation round.

    **The third assignment constraint was replaced, not implemented.** `docs/PLAYTEST_FLOW.md` required
    that an assignment *"becomes solvable once the minimum share threshold is met"*, which Session 38
    measured as not well-formed. `casefiles.py` takes a `redundancy` parameter instead — how many
    distinct casefiles each required exoneration must reach. Redundancy 1 is §4's "accept it" option;
    redundancy 2 is its "assignment for redundancy" option; **"pigeonhole it" is not implemented** and
    the module says so. Redundancy is also where **difficulty now lives**, because the share-rule
    ladder is inert at a three-finding casefile (Session 38): `REDUNDANCY_BY_DIFFICULTY` puts each
    exoneration in two casefiles on EASY and one on HARD.

    **Untested against a real generation.** That costs credits and is the next paid step — one
    round now validates both Session 38's reorder and this pointer. `scripts/test_casefiles.py` and
    `scripts/test_narrative_checks.py` carry fixtures because no mystery on disk has either
    field, and both suites were negative-tested by injecting each defect. **That pass found two
    of the first-draft assignment tests vacuous** — one was refused by the feasibility pre-check so the
    enforcing branch could be deleted with the suite still green, and one asserted a property
    that held by construction — and corrected a code comment claiming an assignment-order benefit
    that measurement showed does not exist.
    **[Session 38] One design question remains open, not five** — `docs/INVESTIGATION_DESIGN.md`
    §6 has been reconciled with APF. Four of the five were closed by APF rather than answered
    (they assumed traversal, blind exploration, player positions and an investigation budget,
    all of which APF deletes); the survivor is **titles that spoil** — a player title like
    *"Why did Hansel Grimm kill Gretel Grimm"* names the culprit, and generation must treat
    that as premise or as misdirection by decision rather than by accident.
    Owner also decided the question that was really underneath question 1: **no crime-scene
    picture for the playtest** — a list of named findings, per §6's option (a). The map is
    deferred, not cancelled, and the round-robin witness placement stays a real bug regardless.

24. **[DONE, Session 37 — August 26, 2026] One palette, three surfaces.** The client had no
    styling at all; the phone had a palette it invented; the brand documented a third and was
    rendered by nothing. Two of those brasses were `#c8a96e` and `#C9A227` — near enough to read
    as a rounding difference, and in CYM guaranteed to be seen side by side, because the host
    screen and the phones are in the same room at the same time.

    `palette.py` is now the only place a colour is decided. `scripts/build_palette.py` generates
    `godot/scripts/theme/Palette.gd` and `mobile.html`'s CSS block from it and `--check` fails on
    drift; `scripts/test_palette.py` holds 28 ink/background pairs to their WCAG floors.
    `godot/scripts/autoloads/Style.gd` builds the Theme and puts it on `get_tree().root`, so all
    eight screens restyle **without one `.tscn` node tree being edited** — which is the point,
    given where Session 36's defects lived.

    **What this does not settle, and why the next report on it must say so.** There is no Godot
    binary in the session environment, so **none of the theme has been rendered.** The checkers
    establish that every `theme_type_variation` is declared and every path resolves; they cannot
    establish that a theme item name is one the engine recognises, and a wrong one is a silent
    no-op rather than an error. **[Session 38] That last gap is closed, but only from inside the
    engine** — `godot/scripts/tools/ApplyTheme.gd` looks every name up in
    `ThemeDB.get_default_theme()` and prints the misses.

    **[Session 40] IT WAS RUN, AND IT CAME BACK CLEAN.** Godot 4.7.2, the owner's machine, the
    first execution of either engine-side script: `168 items checked across 36 theme types`,
    **`MISSES none`**, and Nunito Sans resolved at default_font_size 16. `VerifyScenes.gd`
    reported eight `ok` lines in the same sitting. So the caveat below is now history rather than
    a live risk: every theme item name and all 13 variations are names the engine really has, and
    every one of the eight screens survives Godot's own loader. Neither could be established any
    other way — a wrong theme name is a silent no-op with no symptom but one control looking
    unthemed, and reading a `.tscn` is not loading it. The failure mode is bounded — a control keeps its engine default,
    nothing crashes — but it needs an F5 to close. Session 36's "necessary, not sufficient" rule
    applies to this work more than to most.

    Three things deliberately left alone, each because deciding them is the owner's:
    - ~~**Fonts.**~~ **[DECIDED, same session] Nunito Sans**, SIL OFL 1.1, three static
      instances (400/600/700) in `godot/assets/fonts/` with `OFL.txt` beside them, and the
      same release self-hosted as WOFF2 for the phone. One family across the whole
      hierarchy, so there is no fallback chain and no missing-glyph box; Latin-1 accents
      verified against *Schatten am Checkpoint*. Open at the F5: the room code, since the
      zero is unslashed.
    - **`config/icon`** points at `res://assets/ui/icon.png`, which does not exist (nor does
      `godot/assets/`). Choosing it means answering item 17's open question about which brand mark
      goes on which device.
    - **What the BACKGROUND field is strewn with** — item 17 question 2. Nothing here wires the
      field to a client, so nothing prejudges it.

25. **[DONE, Session 38 — August 28, 2026] The design is visible in the editor, and two checks
    moved inside the engine.** Session 37 built the theme and it was invisible while being worked
    on: `Style.gd` assigns it to `get_tree().root`, and there is no root at *design* time, so the
    editor canvas showed engine grey.

    Two `EditorScript`s, both one keystroke (File → Run) and both free:
    - **`godot/scripts/tools/ApplyTheme.gd`** calls the same `Style.build_theme()` the game calls,
      lets `ResourceSaver` serialise it to `res://assets/theme/cym_theme.tres`, and points
      `gui/theme/custom` at it. **The `.tres` is a generated preview, never a source** —
      `palette.py` is still the one place a colour is decided. Runtime never reads it: a Control
      resolves its theme from its ancestors before the project default, so `Style.gd` still wins
      when the game runs, and a stale preview can mislead the editor but cannot ship a wrong
      colour. It also prints every theme item name the engine does not have (see item 24).
    - **`godot/scripts/tools/VerifyScenes.gd`** loads all eight screens through Godot's own loader
      and compares the nodes each `.tscn` declares against the nodes that survive loading — the
      comparison `check_godot_wiring.py` structurally cannot make, and the one that would have
      caught Session 36's five missing `Interrogation.tscn` panels.

    **The Output panel was cleaned so a real warning stands out**, which matters because
    `docs/F5_CHECKLIST.md` tells the owner to read it for the font canary. Three Python-style
    triple-quoted docstrings were sitting in GDScript — two of them in `ApiClient.gd`, an autoload. They
    are *not* fatal (GDScript does have triple-quoted strings) but each is a standalone expression
    that logs a warning; converted to `##`. `config/icon` named a file that has never existed and
    logged a failed-load **error** on every open; now unset.

    `check_godot_wiring.py` gained a docstring check, and its parse-level checks now run over all
    18 `.gd` files rather than only the 8 a `.tscn` names — the four autoloads had never been
    checked, which is the worst place to miss a parse error. Its own docstring claimed
    "none exist in this project today" of triple-quoted blocks; that was false at three call sites.

    **Also now measured rather than assumed:** there is no route to a Godot binary from a session
    environment. Outbound is allowlist-only; `godotengine.org` does not resolve and the GitHub
    releases host returns 403 from the proxy's repo scoping. Previous sessions stated this; it has
    now been tried.

    **Still nothing rendered.** Both scripts are engine-side and unrun.

26. **[DONE, Session 38 — August 28, 2026] Generation writes the mystery BACKWARDS, and every
    clue declares what it serves.** Owner's observation, from the craft of the form: a mystery is
    written solution first — killer, motive, then the clues planted in reverse to lead a detective
    to a truth already fixed. The prompt was doing the opposite. Its JSON template emitted
    `solution` **last**, after the cast and the evidence, so the model invented a cast, committed
    to clues, and then improvised an explanation for what it had already written.

    **This is mechanical, not stylistic.** A language model composes left to right, so whatever it
    emits first is what everything after is conditioned on. Solution last means the solution is
    conditioned on the clues. The adage is, in effect, a statement about conditioning order — which
    is why it carries over from novels and screenplays unchanged.

    **The evidence it was hurting us:** `daggers_in_the_forum` scores `passed=True, blocking=0,
    warnings=0` — a clean sweep of all 26 coherence rules — and its deduction turns on Apolonios,
    Demetrios and Senator Manilius, none of whom appear in its own character list. Writing forwards,
    when the cast does not support the chain the model needs, inventing a person is cheaper than
    revising a cast already emitted. Measured across the corpus: **7 of 17 mysteries reason about
    at least one person absent from `characters[]`.**

    **What changed.** `solution` is emitted directly after `setting`; `crime.what_happened` is
    marked public and may not spoil; and everything downstream **declares its links** instead of
    leaving them implicit in prose — `solution.chain` numbers the deduction steps, and each
    evidence item names the steps it `supports`, the suspects it `exonerates`, and the suspects it
    `implicates`. Those last two are §4's solvability fields, bundled into the same schema change
    deliberately: testing generation costs money and one paid round is cheaper than two.

    **Why declaring links is the whole point.** It is the same move `exonerates` already made for
    the arithmetic — stop asking a checker to infer a relationship, make generation state one. With
    the links stated, narrative coherence becomes graph reachability and is checkable for **zero
    API cost**: every `supports` resolves to a real step, every step is supported by something,
    elimination leaves exactly the culprit, the culprit is never exonerated and is positively
    implicated by at least one item.

    **What it does NOT buy, stated plainly.** A model can emit `supports: ["S2"]` on a clue that
    does not support S2, and no structural check can tell. What the reorder buys is a change in the
    *direction* of drift: drifting from a fixed solution produces a clue that does not fit, which
    shows as an unresolved or unsupported link; drifting toward an improvised solution produces
    invented people, which nothing structural can see. **A visible failure mode replaces an
    invisible one.** That is the win, and it is worth having.

    `scripts/check_narrative.py` reports CAST (a person in the chain who is not in the cast), LINKS
    (the graph checks above) and ORPHAN (a name appearing only inside the solution). It fails only
    on mysteries generated under the current schema, so the legacy corpus does not hold the suite
    red. `scripts/test_narrative_checks.py` proves the LINKS branch fires, on fixtures, because no
    mystery on disk declares links yet and a branch with no input is a branch nobody has run.

    **Untested against a real generation** — that costs credits. The first generation run after
    this is the confirmation.


27. **[BUILT, Session 40 — untested against a real generation] Incrimination as well as exculpation: the glove
    mechanic.** Deduction today is pure subtraction. Every clue clears exactly one suspect, and
    you win when one name is left. That shape has a cost the owner named: it is arithmetic, not
    detection. Nothing asks the player to *decide* anything, and nothing gives two players a
    reason to talk to each other — you read your own list and subtract privately.

    **The owner's example, which is the whole design:** *"A bloody men's glove."* On its own it
    clears nobody. Give it to somebody holding *"the CCTV shows Adachi in the control room all
    night"* and the two together name the killer. **Two findings that individually prove nothing
    combine into a proof**, which makes sharing the engine of the deduction rather than an
    obligation, and makes *"has anyone got anything on Adachi?"* a sentence a real player says
    out loud.

    **It must NEVER be stated as "the culprit is one of these two."** The owner was explicit and
    was right: the clue says *man's size large*, the player looks at the cast and draws the line
    themselves. The structured field is hidden bookkeeping so the engine can guarantee the case
    is solvable; the prose is the game. `investigation_prompt` is the existing precedent — it is
    already private context the player never sees.

    **The rule that keeps it honest: an assumption the game INVITES must be one that holds.**
    A men's glove is fun when the culprit is a man. It is a cheat when Solberg wore her husband's
    — because the player who reasoned exactly as the game taught them then loses, which is the
    worst outcome a mystery can produce. This is not a new rule: `RESEARCH_FINDINGS.md` already
    carries it as **M3 Clue Fairness**, sourced to P.D. James (*"the detective can know nothing
    which the reader isn't also told"*) and Knox's eighth commandment. The corpus has it and
    generation does not use it.

    That is also how this squares with the owner's "race to proof" (item 23): **certainty in the
    engine, inference at the table.** The system guarantees a sound chain to exactly one culprit
    exists and that nobody can withhold it away — checked before anyone sits down. The player
    experiences a glove, an alibi that does not fit, and a decision.

    **What it needs.** The field already exists: `implicates` is on every evidence item and
    generation fills it in, but nothing reads it — `check_narrative.py` only asserts that the
    culprit is implicated by *something*, so the answer does not feel arbitrary, and `casefiles.py`'s
    `solves()` uses `exonerates` alone. The change is to give `implicates` the meaning *"only
    these could have done it"* and have `solves()` intersect those sets as well as subtracting
    the exonerated, solving when exactly one name survives both.

    **Build the fair-play check in the same change, not after.** A narrowing clue is a strong
    claim and generation has to mean it: the real culprit must appear in EVERY implicating set,
    or the mystery contradicts itself and punishes correct reasoning. That is free, structural,
    and exactly the kind of relationship item 26 established should be declared rather than
    inferred.

    **Two consequences worth knowing before starting.** It should reduce how many findings a
    mystery needs — clearing three people currently takes six findings under item 23's two-routes
    rule, and a glove narrowing to two plus one alibi does the same work with two. And it changes
    what generation must write, so it wants to land in the same paid round as any other schema
    change rather than its own.


28. **[BUILT, Session 41 — September 3 2026] The generation ledger, and cost per accepted mystery.**
    Asked to "start recording CPAM" and "start amassing failures with structured data", the honest
    answer was that these are one artifact, not two: a row per generation attempt saying **what it
    cost, what happened to it, and why**. CPAM falls out as `sum(cost) / count(accepted)`; the
    failure corpus is the rejected rows.

    **What was thrown away, and cannot be recovered.** There is exactly one Claude call site in the
    server — `llm()` in `server/main.py` — and nothing read `response.usage`. Every token count the
    API handed back was discarded, so the project's only cost figure was a hand measurement of one
    August generation in `docs/AI_COST_PLAYBOOK.md`. **What the four rejected mysteries cost is
    unrecoverable.** They are backfilled with `cost_usd: null`; an estimate there would silently
    become the denominator of a number that may end up in front of an investor.

    **Why CPAM and not cost per call.** Cost per call is the easy number and it answers the wrong
    question: a model at a third the price with a third the pass rate is a wash, and one with a
    worse pass rate is a loss disguised as a saving. This matters directly to the owner's Mistral
    question — the workload is output-heavy (8,667 output against 2,457 input, output is 95% of the
    call), which is the profile where self-hosting *can* win, but the hard thing this product asks
    of a model is satisfying six simultaneous global constraints across ~10k tokens, which is
    exactly where smaller models degrade. So the deciding number is cost per *accepted* mystery,
    and it cannot be computed retroactively. It starts being recorded now, not when the question
    is asked.

    **Stable rule ids, which is what makes it a dataset rather than an archive.**
    `check_narrative.py` and `casefiles.py` emitted prose only — good for a person triaging a queue,
    useless for counting. Both now name every rule they fire, the subject it fired on, and a
    failure class. Prose output is byte-identical; the structured form is additional. The two files
    independently implement five of the same fair-play rules, so their ids are shared deliberately
    and `gate.py` deduplicates on (rule, subject).

    **Pass rate is computed over judged rows only.** The 16 legacy mysteries were never put to the
    gate, so counting them as failures would report 0% for a pipeline that has simply not been
    measured — a denominator that quietly includes unmeasured rows is how a metric starts lying
    before anyone reads it twice.

    `python3 scripts/cpam.py` reads it; `scripts/backfill_ledger.py` seeded it from disk and is
    idempotent. Covered by `scripts/test_gate_and_ledger.py`.

29. **[BUILT, Session 41 — September 3 2026] The arrangement pass: wire the pointer, never rewrite
    the clue.** Owner, on the two-routes rule failing three generations running: *"I wonder if
    there's a RAG or RAG-adjacent solution… ways to augment clues to clear more than one suspect
    (changing from the specific to a more general noun)."*

    **The corrected diagnosis came first, and it was not a distribution problem.** Counting ROUTES
    rather than evidence items — a route being the clue itself plus any witness, lead or area whose
    `reveals` names it — the picture is not 3/2/1 but this:

    | Mystery | Routes per innocent |
    |---|---|
    | `the_last_night_of_delacroix_&_sons` | Nadège **1**, Rémy 10, Sylvain 5 |
    | `the_vanishing_at_altheim_peak` | Adachi **1**, Solberg 4, Novák 2 |
    | `totality` | Luz **1**, Fenwick 4, Sable 4 |

    Nobody is short of clues. **Exactly one person has exactly one, every time, and it is always the
    person whose exonerating clue nothing points at.** So `NARR.SINGLE_ROUTE` and
    `REVEAL.UNREACHED_EXONERATION` are one defect seen from two sides.

    **Two corrections to the owner's proposal, both worth keeping.** First, RAG is already here —
    `craft_grounding.py` retrieves into all five generation call sites at zero added cost — and it
    cannot fix this, because this is not a knowledge failure: the model writes six good alibi clues
    and then fails at bookkeeping. Retrieval adds knowledge, not arithmetic. Second, and more
    important: **a clue that clears more than one suspect is already forbidden.**
    `NARR.CLEARS_MULTIPLE` is the rule `the_lantern_keeper's_last_light` earned, where one clue
    cleared three innocents and whoever drew it won alone. Generalising a noun pushes toward
    solo-solve, trading a *below_standard* failure for an *unplayable* one. The wanted property is
    **redundancy** — two different findings clearing the same one person — not generality.

    **What was built is the tool the owner asked for, made deterministic rather than retrieval.**
    `arrangement.py` finds orphaned exonerations and wires a carrier that has earned it. The line
    it holds: **repair the arrangement, never the evidence.** Adding a pointer completes something
    the schema requires and the model forgot, and a person can read the statement and check it;
    rewriting prose until a leak detector stops firing is optimising against the checker, which is
    what `the_light_that_went_out` proves you cannot do.

    **It refuses far more than it acts, and its own first run is why.** Scoring on shared vocabulary
    proposed wiring Nadège's audience sign-in sheet to a witness discussing somebody else buying
    taffy (shared words: *else, entire, general, show*). Document-frequency rarity does not rescue
    that — in that mystery *"else"* is exactly as rare as *"corroboration"*, because rarity measures
    oddness, not aboutness. The test is domain-shaped instead: these pointers only ever attach to
    exonerating evidence and alibi testimony names its subject, so **the carrier must name the
    person the clue clears**, plus a distinctive shared term that is *not* the name. That second
    clause was also learned the hard way — letting the name corroborate itself proposed wiring the
    same alibi to the area holding her **marriage certificate**.

    **Every wiring is then re-verified against the full gate, on severity rather than count.** A
    carrier that gains one exoneration too many starts solving the case alone; the test caught a
    wiring that took a mystery from three violations to two while turning *below_standard* into
    *unplayable*.

    **Result on the five current-schema mysteries: 0 wirable, 4 gaps.** A negative result, and the
    right one — the tool declines to manufacture a lie and instead names the targeted ask, which is
    a few hundred output tokens against $0.20 for a regeneration.

    **The finding that matters more than the tool is `--coverage`.** The suspect with one route is
    the suspect nobody talks about:

    | Mystery | Suspect with no witness | Suspect with 1 route |
    |---|---|---|
    | `the_vanishing_at_altheim_peak` | Adachi (no witness, no area) | Adachi |
    | `totality` | Luz Fontaine (no witness, no area) | Luz Fontaine |
    | `the_last_night_of_delacroix_&_sons` | Nadège (no witness) | Nadège |
    | `the_light_that_went_out` | *none — all four have one* | *none* |

    Generation builds the world around the people it is thinking about, and one suspect ends up with
    less world than the others. **That is a prompt fix, not a tool fix**, and the prompt now says it
    where witnesses are actually written: assign each witness a suspect BEFORE writing the
    statement, and cover all four. The existing REACHABLE rule failed for the same reason the
    two-routes rule did — both were stated in the EVIDENCE section as properties of a section the
    model writes later. **Untested against a real generation.**

30. **[BUILT, Session 41 — September 3 2026] Two things the session kept finding by accident, made
    into checks.** Owner, after a run of *"a rule nobody was enforcing"* findings: *"Is it worth our
    while to do a top down code review predicated on rules to make sure we don't have a lot of
    superfluous or inactive ones?"*

    **The specific worry was tested first, and it was clean.** 55 rule ids are declared across
    `check_narrative.RULES`, `casefiles.FEASIBILITY_RULES` and `coherence_validator`. **Every one is
    reachable from a live code path — there are no dead rules.** 39 have never fired and are not
    named in a test, which sounds alarming and mostly is not: `P1.C2.no_victim` never firing means
    generation reliably writes a victim. That is cheap insurance working. What is new is that the
    ledger now records firing, so "never fired in N generations" is becoming evidence rather than a
    guess.

    **Three shapes of broken rule exist, and this session produced one of each:**

    | Shape | This session's example | Findable mechanically? |
    |---|---|---|
    | *inert* — declared, unreachable | none in the rule system | yes — checked, clean |
    | *unenforced* — the prompt asserts it, nothing checks | *"EXACTLY 4 suspects"*, which cost a paid generation | **yes** |
    | *wrongly measured* — runs, passes, measures the wrong thing | narrowing counted list entries not suspects; prose leak compared full names | no — only reading finds these |

    The third is the dangerous one, because a wrong rule sits there **green** and looks like
    coverage. Both instances cost a generation to expose.

    `scripts/check_rule_coverage.py` attacks the second. It inventories all 36 hard assertions in
    the generation prompt against the rule ids enforcing them, and fails on three conditions: an
    imperative the inventory does not cover, a claimed rule id that is not live, or an inventoried
    assertion deleted from the prompt. **You cannot quietly add an unenforced rule to the prompt.**
    It found one on its first run — *"At least 2 areas must yield a discovery+analysis pair that
    genuinely narrows the suspect list"*, which nothing counts. 11 assertions stand UNENFORCED and
    are listed deliberately; one is marked *unenforceable* (whether a witness statement is TRUE is
    not a structural question, which is why deception is switched off rather than checked).

31. **[BUILT, Session 41] The assignment step chooses a distribution instead of taking the first legal one.**
    `assignment()` stopped at the first shuffle satisfying the constraints. It asked *is this legal* and
    never *is this good*, and the first accepted mystery showed how much that costs: at seed 7,
    exactly one player could prove the case in **27 of 81** hoarding patterns — the same figure
    `totality` was rejected for — while **13 of 20 seeds gave zero**, and proof survived 81/81 on
    every seed tried. Same mystery, same rules, same constraints met. The only difference was which
    findings landed in which casefiles.

    **So monopoly on proof is a property of the ASSIGNMENT, not the story.** `best_assignment()` tries seeds,
    scores each by monopoly count and keeps the best, stopping early on a perfect one — usually one
    or two assigns rather than twenty.

    **Selection, not prohibition,** and that is the design choice. `assignment()` already had
    `forbid_prover_monopoly`, off by default because it costs assigns: as a hard constraint a mystery
    where no assignment avoids a monopoly returns no casefiles at all, and a table gets nothing. Selecting
    always returns a distribution — the least bad available — and reports how good it managed to be.
    Degrading beats refusing when the alternative is an empty table.

    Determinism survives, which matters because a reconnecting player must get their own casefile back:
    the winning seed is returned in the result and reproduces the same casefiles through plain `assignment()`.

32. **[DECIDED, Session 41 — owner] The game ends in full disclosure.** When the final round
    closes, every finding still held by every player becomes public, each shown with the name of
    whoever was holding it.

    **The reason is the product's own name.** Owner: *"So much of the fun of this game is the Choose
    aspect of it. Choosing the kind of mystery you are trying to solve, seeing the full disclosure
    is necessary to reward that choice."* A player picked the setting and the generation was paid
    for; showing them only the fraction that happened to get shared sells them a part of what they
    bought.

    **It also makes withholding accountable, which nothing before the end can do.** During play,
    keeping a finding costs you nothing visible — the whole point is that others cannot see what
    you hold. Disclosure settles that at the table's own pace: everyone finds out precisely what
    each player sat on, and whether it would have changed anything. The sentence the mechanic
    exists to produce — *"she was holding that the whole time"* — is only sayable afterwards.

    **Cheap, because it is not new machinery.** Disclosure is the ordinary share step with the
    minimum set to everything, applied once to every player simultaneously. The reveal screen
    already exists. No new state, no new route shape, no new screen.

    **Explicitly NOT a remedy for an unsolved case.** Whether a mystery that nobody cracked should
    end unsolved, or be resolved some other way, is a separate design question and is left open on
    purpose. Full disclosure happens either way — after a correct accusation or after none.

33. **[OPEN — deferred by the pool, owner wants to revisit] Five suspects would unlock the third
    difficulty rung.** Recorded because it is the first thing found that would fix a problem two
    earlier sessions could not, and because the only reason to wait is a constraint that will lift
    on its own.

    **The problem it solves.** Session 38 measured the share ladder as inert at APF's casefile size —
    EASY, MEDIUM and HARD all resolve to the same requirement — and Session 39 moved difficulty
    onto assignment redundancy instead, only to find that ladder has **two rungs, not three**:
    `REDUNDANCY_BY_DIFFICULTY` puts MEDIUM and HARD at the same value because the ceiling forbids
    a third. That ceiling is arithmetic, from `feasibility()`: with R required exonerations over P
    players, redundancy r forces some casefile to hold `ceil(R × r / P)`, and when that reaches R the
    casefile solves alone. At four suspects (R = 3) over four players the ceiling is **2**.

    **Add one suspect and the ceiling rises.** R = 4 gives a ceiling of 3 — a genuine third rung,
    with no new mechanism:

    | Suspects | Required exonerations | Alibi findings needed | Pool left over | Redundancy ceiling |
    |---|---|---|---|---|
    | 4 | 3 | 6 | 12 | 2 |
    | **5** | **4** | **8** | **10** | **3** |
    | 6 | 5 | 10 | 8 | 3 |

    **Why not now: the pool cannot feed it.** Every innocent needs clearing and every clearing
    needs two independent routes, so a fifth suspect locks two more findings as alibis out of a
    pool that does not grow — 18 findings on the first accepted mystery. It also competes directly
    with the round count, which is findings ÷ players, so buying a difficulty rung would cost
    investigation length. Both wants are answered by the same thing: **more findings per mystery**,
    which is output tokens, which is 95% of a generation call.

    **Also weighed and rejected: making four a MINIMUM rather than fixed.** More suspects is more
    constrained, not less — each one adds required exonerations, routes and witness coverage. And
    coherence barely scales with cast size (a six-suspect story hangs together as readily as a
    four-suspect one); what scales is game structure, which is exactly where every recent failure
    has been. A minimum also hands the model a structural parameter to choose, which is precisely
    what produced `snow_on_the_engawa`'s three-suspect cast and the unfair assignment that followed.

    **The trigger for revisiting is therefore not a decision, it is a number:** once a mystery
    reliably carries enough findings to support both a longer rhythm and a fifth suspect's alibi
    load, this becomes free. Until then `APF_SUSPECT_COUNT` stays at 4 and is enforced.

34. **[SETTLED, Session 42 — owner's third telling] The vocabulary is investigation, not card
    game.** No decks, no cards, no hands, no deals, and nothing is *played*. Findings are
    **assigned**, into a player's **casefile**, by `casefiles.py`. This is a social deduction game
    about what people choose to say, and describing it in the language of a card table makes it
    read as one.

    **Where it came from, because "we keep drifting back" is a symptom and this is the cause.**
    Commit `0db3d9b`, 25 August 2026 — the commit that first specified APF. Under a heading about
    what the UI now has to carry:

    > **The data is already card-shaped**: a finding has a name, a description, a type, a
    > relevance. Dealt, held, played. MYF has `GameCard.jsx` (155 lines), `CardHand.jsx` (67),
    > `CardPicker.jsx` (104) — not portable to Godot, but straight into `mobile.html`, and the
    > visual language carries either way.

    **It entered as a UI-REUSE argument, never as a design one.** Mind Your Friends genuinely is a
    card game and genuinely has those components. Somebody noticed they had the right *shape* for
    "a discrete object given to a player and held", and wrote *"the data is already card-shaped"*
    as shorthand for *"MYF's components would fit here"*. Nobody ever argued that CYM should feel
    like a card game — so nobody ever defended the claim, and it spread precisely because it was
    never a claim.

    Then the shorthand became the vocabulary, in four sessions: *card-shaped* → *dealt, held,
    played* → *the deal* → *the hand* → *deal.py* → *DEFAULT_HAND_SPEC* → a *.card* CSS class on
    the phone client every player looks at.

    **The first two corrections failed because they only fixed the NOUN.** *deal.py*'s docstring
    recorded *"THE WORD IS 'FINDING', EVERYWHERE. Owner's instruction, twice."* — and it was
    obeyed: no clue was called a card anywhere. Every verb and container around it survived
    untouched. **A metaphor rebuilds itself from whatever parts you leave standing**, which is why
    a third telling was needed and why this one moved the module name, the rule ids, the function
    names, the CSS class and the prose together.

    **What was deliberately NOT rewritten**, because rewriting it would be a different kind of
    error:
    - **`SESSIONS.md`** — append-only. Editing history so it agrees with today is the exact thing
      that file exists to prevent, and Session 38 already had to rebuild `CLAUDE.md` because that
      rule was ignored.
    - **The ledger's stored rule ids.** 45 rows carry `DEAL.*`. They are folded onto the new
      `CASE.*` names at READ time by `generation_ledger.LEGACY_RULE_IDS`, so a rule's cost history
      stays under one heading without a single stored row being altered.
    - **Mystery JSON, `part_registry.json`, and the corpus findings documents.** Those contain
      prose from published fiction and from party-game research that legitimately discusses card
      games. That is content, not vocabulary we chose.
    - **"handedness"** in the generation prompt, which is a forensic property of a person, and
      ordinary English like *hand-written* or *handing someone a build*.

    **The standing rule for future sessions:** if a word would be at home on a box that says
    "2–6 players, ages 10+", it is the wrong word. Reach for the investigation instead — findings,
    casefiles, statements, the record, what reached the table.
