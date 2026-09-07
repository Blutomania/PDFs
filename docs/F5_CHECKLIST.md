# F5 checklist — running the Godot client by hand

The complete procedure for running the desktop client on your own machine, from a terminal prompt
to the result screen. **Every command you need is in here**; nothing is left as "set up the
backend".

**Steps 1–8 and 9–19 cost nothing.** Only steps 20 and 21 spend API credits.

**Why this exists.** Godot reports a bad node path only at runtime, and a control that was never
connected not at all — it just does nothing when clicked. The Python checkers catch what they can
by reading the files, but *reading a scene is not the same as loading it*, and Session 36 proved
that gap twice. This checklist is the part no script can do.

---

## Status — what has actually been walked

**Session 36 (owner, August 26 2026): the free route passed.** Three defects were found and fixed
during that walk, none of which any checker could see:

| Screen | Defect |
|---|---|
| Case screen | `case_display.gd` inferred `Variant` from `Dictionary.get()` — fatal at parse time, so the scene never loaded |
| Interrogation | `#` comment lines in the `.tscn` dropped five panels and every child under them |
| Result screen | GDScript has no implicit string concatenation, so the script never loaded and only static nodes rendered |

**Still unverified:** steps 20 and 21 (the two paid ones), step 17's negative case, and — added
Session 42 — **the entire APF path**. `ApfRound.tscn`, the new buttons on `CaseDisplay.tscn` and the
full-disclosure section of `ResultScreen.tscn` pass `scripts/check_godot_wiring.py` and have never
been loaded by the engine. That checker reads scene files rather than loading them, and all three
defects in the table above are exactly the kind it cannot see.

> **Renumbering note (Session 38).** This document used to open at "sync the repo" and keep its
> setup instructions in an appendix — including a section headed *Step 0, do this first*, which sat
> **after** step 17. It is now one linear sequence. **Session 36 walked what were then steps 1–15;
> those are steps 9–19 here.** Nothing was dropped.

---

## What you need

| | |
|---|---|
| **Godot** | 4.x. `godot/project.godot` declares 4.6; 4.7.2 opens it fine (see *Expected noise*). Download from godotengine.org — the standard build, **not** .NET/Mono. It is a single executable; there is no installer to run |
| **Python** | 3.8+, invoked as `python3` |
| **A terminal** | Two windows, or two tabs. One runs the server and stays running |
| **API key** | **Not needed** for steps 1–19. The Anthropic client is built lazily, so the server boots and serves the whole saved-mystery route with no key set |
| **Time** | ~10 minutes for setup, ~15 for the free route |

---

# Part 1 — Terminal: get the code and prove it is sound

## 1. Get the repo

If you have not cloned it:

```bash
git clone https://github.com/Blutomania/SocialGaming.git
cd SocialGaming
```

If you have:

```bash
cd /path/to/SocialGaming
git checkout main
git pull origin main
```

Run every command from the **repo root** unless a step says otherwise — several git subcommands
resolve paths relative to your working directory.

Confirm you are where you think you are:

```bash
pwd
git log --oneline -3
```

## 2. Set up Python

A virtual environment is optional on most systems and mandatory on Homebrew Python, which refuses
to install into the system interpreter. Do it anyway — it costs one command and avoids the whole
problem:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python3 -m pip install --upgrade pip
python3 -m pip install -r server/requirements.txt
```

That installs FastAPI, Uvicorn, the Anthropic SDK and python-dotenv.

**The venv is per-terminal.** Every new window needs `source .venv/bin/activate` again. If a later
command reports a missing module, that is almost always why.

## 3. Run the checkers — free, and seconds

Do this **before** opening Godot. It is the cheapest pre-flight there is, and each of these has
already caught a real bug:

```bash
python3 scripts/check_godot_wiring.py
python3 scripts/check_mystery_playable.py
python3 scripts/build_palette.py --check
python3 scripts/build_icons.py --check
python3 scripts/test_palette.py
python3 scripts/check_doc_claims.py
python3 scripts/check_decisions.py
```

Or all of them at once, plus the rest of the free suite:

```bash
for s in check_godot_wiring check_mystery_playable check_doc_claims check_decisions \
         check_solvability check_narrative test_narrative_checks test_palette test_icons \
         test_background_field test_share_rule test_deal test_apf \
         test_crime_scene_map test_registry_staleness; do
  printf '%-30s ' "$s"; python3 "scripts/$s.py" >/dev/null 2>&1 && echo PASS || echo FAIL
done
python3 scripts/build_palette.py --check && python3 scripts/build_icons.py --check
```

**Expect every line to say PASS.** A FAIL here is a bug on disk — fix it before spending time in
the engine, because the engine will only show you the symptom.

**Do not glob `scripts/check_*.py`.** That sweeps in `check_brand_contrast.py`, which measures the
`brand/` artwork rather than the client, needs Pillow (`pip install pillow`), and exits non-zero
without it. It has nothing to do with running the game, and a red line you are meant to ignore is
worse than no line at all. `build_palette.py` and `build_icons.py` are listed separately because
they need `--check` — without it they *rewrite* their generated files.

**Necessary, not sufficient.** These read the project files; they do not load them. Steps 7 and 8
are the checks that use Godot's own loader.

## 4. Start the backend

Its own terminal window, left running for the whole session. It runs in the foreground and dies
with its terminal.

```bash
source .venv/bin/activate          # if this is a new window
cd server
python3 -m uvicorn main:app --port 8000
```

**Expect** Uvicorn to print that it is running on `http://127.0.0.1:8000`. Leave it alone.

> **`zsh: command not found: uvicorn`** — the most common first stumble, and it usually does NOT
> mean the dependency is missing. `python3 -c "import uvicorn"` tells you which it is: an error
> means the packages really are absent (go back to step 2); a silent success means only the
> launcher *script* is off your `PATH`, which happens on Homebrew Python, on `pip install --user`,
> and in any terminal where the venv is not active. That is why every command in this document says
> **`python3 -m uvicorn`** rather than bare `uvicorn` — the `-m` form works whenever the package is
> importable, so it never depends on `PATH` at all.

Now, in your **second** terminal:

```bash
curl -s http://localhost:8000/health
```

**Expect exactly:** `{"ok":true}`

If the port is already taken, Uvicorn says so. Find what is holding it:

```bash
lsof -i :8000                      # macOS / Linux
```

Either stop that process, or run on another port (`--port 8001`) and change `SERVER_URL` in
`godot/scripts/autoloads/ApiClient.gd` to match.

**To stop the server later:** Ctrl-C in its window.

---

# Part 2 — Godot: open it, verify it, make the design visible

### 4b. Play a whole APF game over HTTP, before opening Godot at all

With the server up, this plays the accepted mystery end to end — create, join, assignment, four rounds,
full disclosure, accusation, result:

```bash
python3 scripts/walk_apf_game.py
```

**No API key needed**: nothing here generates, it plays the mystery already on disk. Every line
should say PASS.

**Why this is worth 20 seconds.** It exercises the entire playtest path with the client removed, so
a failure here is the server's and a failure later is the screen's. Session 42 found two defects
with it that every in-process test passed through — one of them was that *winning the game* fired a
live Claude call and 500'd without one.

## 5. Launch Godot and add the project

Open the Godot executable. In the Project Manager, click **Import**, navigate to
`SocialGaming/godot/`, select `project.godot`, and confirm.

## 6. Click **Edit**, not **Run**

A fresh clone has no `godot/.godot/` directory — that is the generated import cache and is never
committed. **Run** fails on it with *"Can't run project: Assets need to be imported first."*

Click **Edit** and let the initial import finish. The fonts and eight SVG icons are imported here.

Then check **Project → Project Settings → Globals**. **Expect four entries**, in this order:

> **The tab is called Autoload in Godot 4.6 and earlier, and Globals from 4.7.** Same panel, same
> contents; 4.7 renamed it. Verified on 4.7.2 (Session 40) after the owner went looking for an
> Autoload tab that no longer exists. If you cannot find either, type `autoload` into the
> **Filter Settings** box at the top of the dialog.

| | |
|---|---|
| `GameState` | current mystery, phase, history |
| `ApiClient` | HTTP and WebSocket calls to the backend |
| `NetworkManager` | ENet singleton — present but wired to nothing |
| `Style` | builds the theme. **Must be last** — it reads `Palette.gd` |

If `Style` is missing or not last, that alone explains a completely unstyled game.

## 7. Run `VerifyScenes.gd` — before anything else

In the Script editor, open `godot/scripts/tools/VerifyScenes.gd` and press
**File → Run** (`Ctrl+Shift+X`). It takes no arguments, costs nothing, and needs no backend.

It loads all nine screens through Godot's own loader and compares the nodes each `.tscn`
*declares* against the nodes that actually exist once loaded. That is the comparison
`check_godot_wiring.py` cannot make — it reads scene files, and Session 36 proved reading is not
loading when `Interrogation.tscn` passed the checker with five panels missing at runtime.

**Expect eight `ok` lines.** Anything else names the file and the node. Fix it before F5.

## 8. Run `ApplyTheme.gd` — this is what makes the design visible

Same procedure: open `godot/scripts/tools/ApplyTheme.gd`, **File → Run**.

`Style.gd` puts the theme on the scene-tree root, and there is no root at *design* time, so the
editor canvas shows engine grey however much styling exists. This script calls the same
`Style.build_theme()` the game calls, saves the result to `res://assets/theme/cym_theme.tres`, and
points the project's default theme at it.

**It also writes `godot/apply_theme_report.txt`** — the same output, in a file, because the Output
panel scrolls and cannot be copied out of easily. Read it from the terminal:

```bash
cat godot/apply_theme_report.txt
```

**Read three things, in the panel or the file:**

> **[Session 40] RUN, AND IT CAME BACK CLEAN.** On Godot 4.7.2, a real machine, the first time
> this script has ever executed: `fonts Nunito Sans loaded (default_font_size 16)`,
> `items 168 checked across 36 theme types`, and **`MISSES none — every theme item name is one the
> engine has`**. That closes the caveat Session 37 left open on ten control types and the 13 theme
> variations, which could not be checked any other way: a wrong name is a silent no-op, so the
> failure has no symptom except one control looking unthemed. `VerifyScenes.gd` reported eight
> `ok` lines in the same sitting.

| Line | What it means |
|---|---|
| `fonts` | Whether Nunito Sans actually resolved. On a fresh checkout, if it says the fonts are missing, let the import finish and run it again |
| `MISSES` | Every theme item name the engine does not have. Each is a line of `Style.gd` silently doing nothing. **`none` is the good answer** |
| `wrote` / `set` | The `.tres` was written and the project setting points at it |

Then look at a scene on the canvas. **Two moves, and the first is easy to miss:**

1. **Click the `2D` tab** in the top bar. Running an `EditorScript` leaves you in `Script`, where
   there is no canvas to judge — the instruction below is meaningless until you switch.
2. **Scene → Reload Saved Scene.** An already-open scene keeps rendering with the theme it loaded,
   so it will not pick up the `.tres` this script just wrote until it is reloaded. Closing the
   scene tab and double-clicking the `.tscn` in FileSystem does the same job.

**The canvas should now be slate (`#2F4459`), not Godot grey**, with the title at 44px brass.

Afterwards, in the terminal:

```bash
git status --short
git add godot/assets/theme/cym_theme.tres
git add godot/scripts/**/*.uid          # if Godot generated any; they belong in git
git commit -m "Generated editor theme preview"
```

> **Do NOT `git add godot/project.godot` here, however tempting.** By this point Godot has rewritten
> it, and on 4.7 that means **21 comment lines deleted** and `config/features` bumped. This exact
> instruction used to say to add it, and the owner followed it — the comment loss went into a
> commit (Session 40, salvaged by hand).
>
> The engine writes one useful line, `theme/custom=` under `[gui]`, and it is **already committed**;
> ApplyTheme setting it again is a no-op you can discard along with everything else:
>
> ```bash
> git checkout -- godot/project.godot
> ```

**The `.tres` is a generated preview, never a source.** `palette.py` is still the one place a
colour is decided. Re-run this after changing `palette.py` or `Style.gd`. Runtime never reads it —
a Control resolves its theme from its ancestors before the project default, so `Style.gd` still
wins when the game runs.

---

# Part 3 — The free route · no API spend

## 9. Press F5

F5 is an editor shortcut, so the **editor window must have focus**. The play button in the
top-right toolbar does the same thing, and is the way round a laptop F-key bound to brightness.
Either launches `res://scenes/ui/MainMenu.tscn` in a **new window**, separate from the editor.
F8, or the stop button, ends it.

**Expect:** the title Choose Your Mystery in 44px brass, a muted subtitle, four buttons — New Game
(Solo), Multiplayer, Browse Saved Mysteries, Quit — one of them brass and the rest outlined, a
faint status line at the bottom, and a slate background.

Red *"Backend unreachable"* means step 4's server died, not that the client is broken. Check that
terminal.

**If the whole thing is plain Godot grey**, the theme is not applying at all. Check that `Style` is
the last autoload (step 6).

## 10. Browse Saved Mysteries

**Expect:** a centred window listing **17** rows, each formatted title, difficulty, star rating.

*Not a bug:* "The Murder at Tokyo" and "The Great Cookie Caper of Sesame Street" each appear
twice. Two files on disk resolve to the same slug. Cosmetic and pre-existing.

## 11. Dismiss the popup two ways

Click Close. Reopen. Then dismiss with the window's own close gesture. Both must work — a Godot
`Window` does not hide itself on `close_requested`, the handler has to, and that handler was
unconnected until Session 34.

## 12. Select "Whiteout at Shackleton Base"

The richest case on disk: 8 characters, 4 suspects, 5 investigation areas, coherence passed. It is
also the only mystery whose `key_evidence` matches the evidence its own solution reasons from.

**Expect:** the popup closes and `CaseDisplay.tscn` loads.

If clicking a row does *nothing*, the `item_selected` signal is unconnected again and
`_on_browse_item_selected` is dead code.

## 13. Read the case screen

**Expect:** title, setting, crime, characters and evidence all populated — no empty panels, no raw
null. Two buttons: Interrogate Suspects and Make Accusation. A rating row.

## 14. Open Make Accusation

**Expect** exactly four names, and no orange warning line:

| Suspect | Culprit? |
|---|---|
| Dr. Marcus Hale | **yes** |
| Dr. Yuki Tanaka | no |
| Bjorn Larssen | no |
| Dr. Felix Caron | no |

The dropdown is built from `characters` filtered to the suspect role, so victims and witnesses must
not appear — 8 characters in, 4 names out.

**Open the dropdown and look at the list itself.** A `PopupMenu` is a separate theme type from the
control that opens it, so a dark control opening a light-grey list is the classic half-themed look.

## 15. Accuse the wrong person — Dr. Yuki Tanaka

Submit, then confirm at the dialog.

**Expect** the result screen: a red verdict naming who you accused and who the culprit was, a full
solution breakdown (culprit, method, motive, key evidence, how to deduce), a rating row, and the
buttons Play Again and Review Case.

A blank screen, or an error naming a node path under `ScrollContainer`, means the Session 34 fix to
`result_screen.gd` regressed. That commit was the entire end-of-game screen.

## 16. Rate the mystery

Click a rating button. This posts to the rate endpoint — a disk write, no Claude call. Expect no
error, and the request visible in the server terminal.

## 17. The culprit-matching regression — "The Stolen Star of Smurf Village"

Browse to it and accuse **Smurfwick the Craftsmurf**.

This mystery's culprit field is a prose sentence naming two culprits, so exact matching marked
*every* accusation wrong, including both right ones.

**Expect:** correct. Repeat with **Smurfadel, Master of Adornment** — also correct.

**Then the case nobody has run: Smurfodex, Keeper of the Great Smurf Tome must read *wrong*.**
The fix was substring matching with a short-name guard, and a fix like that can go too far. This is
the step that proves it did not.

*Cosmetic, expected:* the verdict prints the raw culprit field, so you will see the whole prose
string. Ugly, not a failure. The underlying cause is `docs/DECISIONS.md` item 18, still open.

## 18. Both exits from the result screen

Review Case returns to `CaseDisplay`; Play Again returns to `MainMenu`. Two different
destinations, neither throwing.

## 19. Interrogation screen — reachable without spending

From a loaded case, click Interrogate Suspects. **Do not ask a question yet** — the screen itself
is free, each question is not.

**Expect:** the header reading Phase 1, budget text reading "Ask as many questions as you like."
(not *0 questions remaining*), and a populated suspect dropdown.

This screen failed in Session 36 with *"Cannot call method 'add_item' on a null value"* because
`Interrogation.tscn` used `#` comment lines, which drop the node declared after them. That is
fixed; this step confirms it.

**Stop here and take stock.** If 1–19 pass, the free route is clear. Everything below spends money
and can wait.

---

# Part 4 — The paid route · costs API credits

Both steps need a key. In the **server's** terminal, before starting it:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."      # Windows: set ANTHROPIC_API_KEY=...
```

Then restart the server (Ctrl-C, then the step 4 command again). The client needs no key — it never
sees one.

## 20. One interrogation · ~1 call

Ask a single question. Expect an in-character reply in the history.

## 21. One generation · 1 large call

New Game (Solo) → a scenario → Generate Mystery. Real generations on record have taken **112 to
1,992 seconds**, so give it room.

**Expect:** the prompt box, the moderation disclaimer visible beneath it, the cinematic-brief
checkbox, and on success a brand-new case on `CaseDisplay`.

Watch for JSON parse errors. An old batch summary shows 13 of 14 generations failing that way; it
is from March and 16 have generated cleanly since, but this run is the confirmation nobody has done.

---

# Reference

## Expected noise — none of these are failures

- **Godot 4.7 modifying files.** Opening a 4.6 project in 4.7 re-saves `godot/project.godot` and
  `godot/scenes/ui/MainMenu.tscn`, which then show as modified in `git status`.

  > **It also DELETES every `;` comment in `project.godot` — 21 lines of them.** Verified on a real
  > 4.7 open, Session 40. The engine rewrites the file from its own in-memory config and comments
  > are not part of that, so they do not survive. It also bumps `config/features` to `"4.7"` and
  > drops the `[rendering]` section.
  >
  > **Discard that diff; do not commit it.** `git checkout -- godot/project.godot`. Committing it
  > deletes the notes explaining why `config/icon` is unset, why `Style` must be the last autoload,
  > and why the ground colour is set there rather than painted by a node — and it restores an
  > `config/icon` pointing at a file that has never existed, which puts a load error back into the
  > Output panel on every open.
  >
  > **Those comments are a convenience, not the only copy.** The icon decision is `CLAUDE.md`
  > item 17, the autoload ordering rule is in `CLAUDE.md`'s Godot notes, and the ground colour is
  > decided in `palette.py`. Treat `project.godot` as a file that cannot hold documentation.
- **Untracked `.uid` files.** Godot generates these sidecars for scripts and assets that lack them.
  **They are meant to be committed** — Godot 4.4+ expects it — so `git add` them rather than
  leaving them sitting in `git status`. Without them Godot regenerates fresh ones on every clone
  and the references churn.
- **`.import` files are ignored**, and the difference from `.uid` matters because they look alike:
  a `.uid` is a stable identity that belongs in version control, a `.import` is per-machine import
  settings pointing into the ignored `.godot/` cache.
- **A default window and taskbar icon.** `config/icon` is deliberately unset. It used to name a
  file that has never existed, which put a failed-load error in the Output panel on every open.

## Things that will look broken and are correct

| What you will see | Why it is right |
|---|---|
| **No icons anywhere** | `Icons.gd` and `IconSet.gd` exist and are tested, but **no screen calls them yet** |
| **No strewn title in the background** | The BACKGROUND field is layout-only and wired to no client. Flat slate *is* the specified pre-prompt state |
| **Panels look sunken, not raised** | Deliberate. The surface ramp goes *deeper* than the ground so the field stays behind everything |
| **Semantic colours look pale** | Forced, not chosen. A saturated red cannot clear 4.5:1 on a mid-slate ground |
| **An unslashed zero in the room code** | Nunito Sans has one. Generate a code and look at it across the room; if `0`/`O` is ambiguous the fix is a mono face for that one label, not a different UI font |

## Failures that are completely silent

**A theme item name the engine does not have is a no-op** — no error, no warning, the control keeps
its engine default. So the symptom is not a crash; it is one control type looking unthemed while
everything around it looks right. Step 8's `MISSES` block is the guard.

The 13 theme type variations (`DisplayLabel`, `TitleLabel`, `MysteryTitleLabel`, `HeadingLabel`,
`MutedLabel`, `FaintLabel`, `CautionLabel`, `ErrorLabel`, `PositiveLabel`, `PrimaryButton`,
`QuietButton`, `DangerButton`, `WellPanel`) fail the same way — an unrecognised variation falls back
to the base type. Quick tell: if the main menu title is not 44px brass, variations are not applying
at all.

**Scrollbars are the loudest tell.** Unthemed they are bright grey, which on this ground would make
them the brightest thing on the case screen.

## Fonts

The `.ttf` files become `FontFile` resources on first import. If a face did not load, `Style.gd`
pushes a warning naming the missing path and keeps the engine default — assigning a null
`default_font` would strip every label in the product with no error at all. Step 8's `fonts` line
reports the same thing off the built theme.

## Icons

The generated SVGs carry `width`/`height` as well as `viewBox`. A viewBox-only SVG has no intrinsic
size and Godot's importer has to invent one, possibly at a scale that makes the icon a few pixels
across, with no error. If icons import tiny, the fix is the **Scale** field in the Import dock, then
Reimport.

They are **white on purpose** — the generated files are a coverage mask, so an unmodulated icon on
the slate ground looks stark white. Anything drawing one should set `modulate`.

## What this checklist does not test

- **Two defensive branches on the accusation screen.** All 17 saved mysteries have suspects, and
  every culprit resolves to at least one — so neither the no-suspects message nor the unsolvable
  warning can fire from saved data. They have no test case on disk.
- **Multiplayer entirely** — lobby, room codes, the share mechanic, the WebSocket path, and
  `server/static/mobile.html`. Stage 3.
- **APF's round screen** — `ApfRound.tscn` was built in Session 42 and **has never been loaded by
  the engine.** It is the one screen on this list that is finished code with zero engine hours on
  it, so walk it deliberately: assignment, watch a face grey out when somebody shares, confirm the round
  refuses to advance while the checkpoint is open, close the case, and check the result screen names
  who held what back. Needs at least two players — constraint 2 is unsatisfiable at one, so a solo
  walk has to add a seat (join from a phone at `/play`, or `POST /games/{id}/join`).
- **Anything visual.** Whether the screens read well is a judgement only a human at the screen can
  make. Note it as you go.

## If something breaks

Capture three things:

1. The **step number**.
2. The **Output panel** text, verbatim.
3. The **Debugger** tab's stack trace if it froze rather than misbehaved.

Two diagnostic habits that paid off in Session 36:

- **The error line is often the symptom, not the cause.** A null-method error names the first line
  that touched a null, not the reason it was null. The running scene's **remote inspector** shows
  which node references resolved and which are empty, which is what actually located the bug.
- **A parse error appears only when its scene first loads.** Godot parses a script when the scene
  needs it, so a broken screen stays silent until you click through to it.
