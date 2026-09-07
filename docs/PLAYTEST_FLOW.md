# Playtest gameflow — the PC path to stage 1

Owner-specified, Session 34 (August 21, 2026). This is the **canonical** description of the flow
the PC playtest has to deliver. It supersedes the Phase 2/3 screen descriptions in `CLAUDE.md`
wherever the two disagree, for playtest purposes only — nothing built is being removed.

Read `CLAUDE.md` → **Delivery Priority** first. Stage 1 is: somebody who is not the owner sits at
a PC, plays a whole mystery, and reaches the result screen. Everything here serves that and
nothing else.

---

## APF — the simplified playtest (owner, Session 35)

**"All Provided For". This supersedes "The flow" below wherever the two disagree.** The older
table is kept because its decisions (four suspects, lies off, leads greyed out, the one-call
shape) still hold.

### The reasoning

> *"Social games work because they are somewhat superficial, easy and enjoyable. Walking around
> is not."* — owner

Exploration was cut for three reasons, in the owner's order:

1. **Moving and searching is not the fun part.** Time spent traversing is time not spent on the
   social read.
2. **Free-text interrogation invites griefing.** `InterrogateRequest.question` is a `str` today,
   so *"tell this witness to eat a donut"* is live. Short-term amusement, long-term a tax on
   everyone else's evening — and simultaneously a moderation surface, an API call each, and a
   quality-variance surface (a weak question returns a weak answer and the game looks broken).
3. **It concentrates the game on its own stated core.** `CLAUDE.md`'s first paragraph calls the
   information-sharing mechanic the core innovation. APF removes everything that is not that
   decision.

### The loop

1. Player types a **title + setting** prompt.
2. Generation runs once. Coherence checks it.
3. The **opening sequence** plays (below) — the crime, told.
4. The game announces **how many rounds this mystery has**, and play begins.
5. Each round, every player is **dealt one finding.** They do not go and get them.
6. From round 2 onward, each round ends in a **share checkpoint**: each player chooses which of
   their findings to make public and which to keep. That is the whole decision.
7. Deduce. Accuse. Reveal.
8. **Full disclosure.** When the last round closes, everything every player still holds becomes
   public, with the holder's name on it.

### The rhythm — dealt over rounds, not all at once (owner, Session 41)

**This supersedes the single-deal reading of steps 4–5 above.** APF's argument for dealing is
untouched; what changed is the *cadence*, and it changed because the arithmetic of a single deal
does not support the decision the game is built on.

Owner: *"rhythms and rituals are great for this."*

**Why not one deal of three.** With a hand dealt once, every player makes exactly one share
decision all game. One decision yields one read of a person. **A rhythm yields a pattern** — and
a pattern is what lets somebody say *"she's held back twice now"*, which is an accusation forming.
A single round cannot produce that sentence.

**Round 1 never has a checkpoint, and the reason is arithmetic.** `_min_share_required()` in
`server/main.py` is `max(1, round(n × share_min))`, so a player holding one finding must share it
whatever the difficulty. There is no decision at a hand of one, only a tax. The first checkpoint
therefore falls at round 2, where holding two means choosing *which*.

**A shared finding STAYS in the holder's hand.** Owner: *"in the metaphor of the player being an
investigator it fails if the investigator is forced to 'forget' something."* Correct, and it
clarifies what the game's currency actually is: **you spend exclusivity, not possession.** A
detective's advantage was never holding the file, it was being the only one who had read it. The
server already works this way — `share_findings` copies into the shared pool and removes nothing.

**So the share requirement is CUMULATIVE**: *shared ≥ required(total held)*, not
*shared-this-round ≥ required(dealt-this-round)*. Without that, round 4 would demand three new
findings when only one was dealt.

**And that revives the difficulty ladder, which a fixed three-finding hand had killed.** Session 38
measured EASY/MEDIUM/HARD all resolving to "share 2, keep 1" at a hand of three, and Session 39
worked around it by moving difficulty onto deal redundancy. Under a rhythm the ladder separates on
its own, with no second dial: what differs is **how much a player is permitted to sit on**.

| After round | EASY | MEDIUM | HARD |
|---|---|---|---|
| 4 | 1 | 2 | 2 |
| 6 | 2 | 2 | 3 |
| 8 | 2 | 3 | 4 |

*(Private stash — the maximum withheld. It is a floor on sharing, not a cap, so this is the size of
the decision space rather than a prediction. HARD permits the largest stash, so least reaches the
table, so the case is hardest to crack collectively — consistent with `deal.py` putting each
exoneration in exactly one hand at HARD.)*

### How many rounds, and why the game says so up front

**Rounds = findings ÷ players.** No finding is dealt twice, so the pool sets the ceiling directly.
`build_pool()` counts witnesses, clues and leads; the first accepted mystery has 18.

| Players | Rounds on an 18-finding mystery |
|---|---|
| 2 | 9 |
| 3 | 6 |
| **4** | **4** |
| 5 | 3 |
| 6 | 3 |

**Fewer players means a longer investigation.** That falls out of the arithmetic rather than being
designed, and it is worth keeping.

**The count is announced before play.** Owner: *"the game TELLS the users. This mystery has a
maximum of X rounds. It creates tension and sets expectations."* Investigations are not infinite,
and a known horizon makes withholding a decision with a deadline attached.

**Four rounds is both the floor and today's ceiling**, which is either satisfying or suspicious.
Four bounds were computed, not argued:

| Bound | Value | Basis |
|---|---|---|
| Solvability | 2 | measured — `proof_survives_hoarding()` returns 16/16 at two rounds |
| A decision exists | 2 | a hand of one forces a share |
| Rhythm (two checkpoints, so a pattern) | 3 | design |
| Difficulty separates at all | 4 | EASY parts from MEDIUM/HARD |
| **Pool ceiling today** | **4** | 18 findings ÷ 4 players |

Going beyond four rounds means growing the pool — roughly 24 findings for six rounds — which is
output tokens, and output is 95% of a generation call. **Not worth buying until a playtest says the
rhythm earns it.**

**Implementation note.** `deal.py` already expresses hand size as `DEFAULT_HAND_SPEC`, whose length
is the number of findings per player. Under the rhythm that length *is* the round count, so the
existing deal machinery covers this without new constraint code — `best_deal()`, feasibility and
the hoarding analysis all work unchanged at four.

### [Session 42] Built — where each sentence above now lives

| The rule | Where it is |
|---|---|
| Rounds = findings ÷ players | `apf.round_count()` |
| The hand spec's length is the round count | `apf.hand_spec_for()` |
| Round 1 has no checkpoint | `apf.FIRST_CHECKPOINT_ROUND`, and `required_now()` returns 0 below it |
| A shared finding stays in the hand | `apf.share()` appends and removes nothing |
| The requirement is cumulative | `apf.share_ladder()`, precomputed at session open |
| The ladder is announced up front | returned by the `/apf/open` route |
| The board greys on `exonerates`, never on `narrows` | `apf.board()` |
| Full disclosure | `apf.disclose()` |

**One thing the arithmetic gave back that this document did not ask for.** The private stash is not
only a difficulty setting — it *is* the deal's `hoard_allowance`, because it defines exactly how
much a player is permitted to withhold. `apf.stash_allowance()` derives it from the ladder, and
doing so exposed a defect in `best_deal()`: it constrained proof-survival at the allowance it was
given and then chose its seed by a monopoly measured at `deal.py`'s constant of 1. Two hoarding
models, one of which the rules do not permit.

**The share rule is injected, never reimplemented.** `_min_share_required()` in `server/main.py`
stays its only definition; `apf.py` takes it as a callable. `scripts/test_share_rule.py` now guards
`apf_round.gd` as well, because the rule moved with the mechanic — a rule defended on the screen it
left is a rule nobody is defending.

**Not verified: nobody has played it, and it has never run in Godot.** Every number in the ladder is
arithmetic. Whether a two-finding stash at HARD *feels* like a decision is a question only a table
answers.

> **On the "75% mechanic".** The line that used to sit at step 5 called this *the 75% mechanic*.
> There has never been one — see `CLAUDE.md`, item 11. What exists is a player-chosen share level
> against a per-difficulty minimum, with no randomness anywhere.

### Full disclosure closes the game (owner, Session 41)

**Not a tie-breaker and not a rescue — the reward for having chosen this mystery.** Owner: *"So
much of the fun of this game is the Choose aspect of it. Choosing the kind of mystery you are
trying to solve, seeing the full disclosure is necessary to reward that choice."* You picked the
setting and paid for the generation; you are owed the whole of it, not the fraction that happened
to be shared.

It does a second job for free. Every finding a player sat on is shown **with their name against
it**, which is what makes withholding a real decision rather than a costless one: the table finds
out afterwards exactly what you kept, and whether it would have mattered. *"She was holding the
ledger page the whole time"* is the sentence the mechanic exists to produce, and nothing before
the end can produce it.

**It reuses the rules already there.** Disclosure is the ordinary share step with the minimum set
to everything, applied once, to every player at once. No new state and no new screen — the reveal
already exists.

**It is NOT a fix for nobody having solved the case.** That is a separate question and is
deliberately left open.

### What this deletes outright

- **The deadlock** (`docs/INVESTIGATION_DESIGN.md` §5). Not fixed — the mechanic that had it is
  gone. Nothing to block, everyone holds findings by construction, no phase to be trapped in.
- The block pool, the phase gates, traversal, the investigation budget.
- **Play-time API cost, to approximately zero.** `docs/AI_COST_PLAYBOOK.md` identifies writing
  fixed text at generation time rather than calling per action as the correct lever, measured at
  10.8× on a four-player game. APF is that lever pushed all the way.

### The deal is a separate step from generation, and it is free

Generate findings carrying elimination data (one call), **then deal them under constraints** —
pure computation, deterministic, and a failed deal is simply re-dealt at zero cost.

| Constraint | Why |
|---|---|
| the union of all dealt findings eliminates all but one suspect | otherwise nobody can win |
| no single player's hand does that alone | otherwise it is a lottery |
| ~~it becomes solvable once the minimum share threshold is met~~ | **not well-formed — replaced.** `share_min` is a fraction of a player's *own* findings and the player picks which, so meeting it does not determine what reaches the pool. Session 39 uses **redundancy** instead: each exoneration must reach at least N distinct hands. See `docs/INVESTIGATION_DESIGN.md` §4 |

**Built in Session 39 as `deal.py`**, with `scripts/test_deal.py`. Findings reach the evidence the
arithmetic is defined over through a `reveals` pointer on witnesses, leads and areas — without it
two of the three kinds in every hand carry no elimination data and cannot be reasoned from.

This is a stronger guarantee than anything the engine does today, and it costs nothing. See
`docs/INVESTIGATION_DESIGN.md` §4 for the `exonerates` / `implicates` fields it needs.

### Path 2 — one interrogation — is a FLAG, not a fork

Owner: *"even if a pick list, it adds some user empowerment. That's important to confirm, but not
essential."*

If the pick-list is over pre-generated questions, the answers already exist in the mystery. So
Path 2 is not a different loop — it is *"one of your findings arrives chosen instead of dealt."*
Same generation, same deal, same share decision, same reveal. **Ship APF with the pick-list behind
a toggle and both get tested by one group in one evening**, everything else held constant.

One consequence: variable hands mean solvability must hold across *every* combination of picks.
4 players × 3 options is 81 combinations — checked exhaustively as set operations, zero API cost.
Do **not** take the shortcut of making all options eliminate the same thing; that is cosmetic
choice and players feel it.

---

## The opening sequence — text, paced, on the shared screen

No video for the playtest. The mystery is told.

**`opening_narration` is now its own call, and it is on by default.**
`_generate_opening_narration()` in `server/main.py` writes 3–5 sentences for the shared screen.
One extra call **at generation time**, which is the right place to spend it — the pacing between
beats afterwards is client-side and free.

> **[Session 40] The video half was deleted, not deferred.** The function used to be
> `_generate_cinematic_brief()` and returned the narration *and* a shot list — logline, lighting,
> sound design, cast appearance — behind one boolean. The first run that ever executed it measured
> **82% of the output as the video half**, which the owner is deferring to stage 3.
>
> The worry worth recording is the one the owner raised: could tuning this prompt for prose leave
> it useless for video later? **No — the two never shared anything.** The video brief was built
> from the mystery (title, setting, crime, cast), never from the narration; they were siblings, not
> a pipeline, so a video brief can be written fresh from the mystery dict whenever it is wanted.
> Two more reasons it is a deletion: the old prompt contradicted itself, asking for narration with
> *"no camera direction"* alongside a brief that is entirely camera direction; and shot-list
> conventions written now are written for today's video models, which makes them speculative work
> with a shelf life.

**The beats, measured on the real generation:**

```
opening_narration        3–5 sentences   the scene
crime.initial_discovery      224 chars   a person, a moment
crime.when                    86 chars   the punch
crime.what_happened          421 chars   what was done
setting.description          531 chars   why nobody can leave
```

~1,300 characters over five beats with deliberately varied length — the 86-character `when` lands
hard between two longer passages. That is a sequence, not a wall.

**Pacing is free** — client-side timing, no API call. On the shared screen it is a group moment:
everyone reading at one rate, reacting together. The same text dumped instantly onto private
phones is homework.

### The video slot

Owner wants the expectation set. **Do not ship a grey box reading "Video Scene Will Play Here"** —
it announces unfinished software at the exact moment you want people absorbed.

Instead the slot holds the crime depicted as well as it currently can — the top-down map framed on
the crime location, or a title card over the background field (`background_field.py`) — with the
narration timed over it. Same real estate, same promise, no broken signal. A small caption
underneath can make the promise explicit without breaking the scene.

> **Correction, Session 35:** `CLAUDE.md` item 15 stated the client *"renders a static
> `Video Scene Will Play Here` placeholder."* It does not. That string appears in no `.gd`,
> `.tscn`, `.html` or `.py` file — nothing occupies that slot today. Fixed in `CLAUDE.md`.

### What the UI has to carry now

With exploration gone, the **hand** and the **share** are not part of the game — they are the
game, and they must feel like objects rather than paragraphs.

- **A finding is already an object, not a paragraph**: it has a name, a description, a type and a
  relevance. It is dealt, held, and shared. MYF has UI components for handling things of that
  shape — not portable to Godot, but straight into `mobile.html`, and the layout thinking carries
  either way. *(Vocabulary, owner's instruction, Session 40: describe these as findings. This is a
  social deduction game, and borrowed game-shop language makes the mechanic read as a deck when it
  should read as evidence.)*
- **The suspect board is where deduction becomes visible.** If evidence carries `exonerates`,
  sharing a finding **greys a suspect out for everyone, permanently, with your name on it.** Text
  cannot do that. It also makes withholding legible without a word of explanation: a face stays
  lit that you could have darkened, and everyone can see you didn't.

**One schema field does double duty** — `exonerates` is what proves the mystery solvable *and*
what drives the central UI moment. Usually correctness and fun are separate budgets.

**Build the hand, the board and the share to be satisfying with the placeholder still in the
slot.** If the playtest only works once the video lands, it has taught you nothing about the game
and cost stage-3 money to say so.

---

## The flow

> **[Session 42] This table describes the GATHER loop, which APF replaces.** It is kept because
> its decisions still hold (four suspects, lies off, the one-call shape) and because the screens it
> names still exist. The APF path is: **Lobby → CaseDisplay** (the crime, told; the host deals from
> here) **→ ApfRound** (hand, board, shared pool, the share decision, four rounds) **→ Accusation →
> ResultScreen** (verdict, solution, full disclosure). Steps 2, 3, 4 and 5 below are not on it.

| # | Screen | What happens | State |
|---|---|---|---|
| 1 | **Mystery picker** | Dropdown, **titles only**. No difficulty, no rating, no coherence badge. | Exists but shows extra columns |
| 2 | **Crime scene** | Top-down map. Areas are clickable regions; witnesses are marked where they stand. Simple to the point of plain. | **Layout built**, screen not |
| 3 | **Interrogate** | Pick a witness → get actionable information. | Exists, needs simplifying |
| 4 | **Search** | Pick an area → *"You searched the <AREA> and found <THIS>. Testing and research reveal <ANALYSIS>."* | Exists, needs reshaping |
| 5 | **Follow leads** | **Greyed out. Not in the playtest.** | Built; to be disabled |
| 6 | **"I've solved it"** | A deliberately clumsy button on the crime-scene screen → dropdown of **four** suspects. | Accusation screen exists |
| 7 | **Result** | Verdict + solution + viability rating. | Fixed Session 34 |

Steps 3, 4 and 6 are reachable from the crime-scene screen, not in a fixed order — "each player
able to choose whether to interrogate, look for clues, or follow leads".

**What the playtest is actually testing** (owner's framing, and it decides every trade-off below):
can we generate a mystery that, above all, **makes sense** — with witnesses worth questioning,
clues that help, and leads that lead somewhere. Everything on screen is in service of judging the
mystery, not of being a finished game.

---

## Decisions

### The map layout is derived, not generated

`crime_scene_map.py` computes the layout from the mystery. Claude is never asked for coordinates.

- **Cost.** Coordinates are the one part of the payload a computer can derive for free.
- **Reliability.** Every extra field is another chance for the response to fail to parse — and an
  old batch summary in `mystery_database/generated/` shows **13 of 14 generations failing** on
  exactly that.
- **Quality.** An LLM asked for rectangles produces overlapping rectangles.

The prompt owns *meaning* (which areas exist, who is where); this module owns *presentation*. Same
mystery in, same map out, seeded from the title, so the host screen and a future phone client draw
the identical map.

A mystery with no `investigation_areas` gets **no map**, reported as such. It does not get invented
rooms — the playtest exists to find out whether generation produces usable areas, so faking them
would defeat the point.

### Lies are switched off for the playtest

Witnesses give straight, actionable information. Deception is a real mechanic and it stays in the
design, but a playtester cannot tell "the mystery is incoherent" from "the witness lied to me",
and telling those two apart is the entire purpose of this playtest.

### Leads are greyed out, not deleted

Visible and disabled, so testers see the shape of the finished game and the code stays exercised.

### Four suspects

The accusation dropdown shows four. The generation prompt must therefore ask for exactly four —
see below; it currently does not, and produces three.

---

## The one-call shape (owner item 7: "as cheap as possible")

**This is the significant one, and the owner's own simplifications are what make it possible.**

Today, gameplay costs an API call per action: `_investigate_area_with_ai` fires per area per
player, witness interrogation fires per question. A four-player game across five areas is ~20+
calls on top of generation.

But steps 3 and 4 as specified are not conversations. *"User picks which witness, game just gives
them actionable info"* and *"You searched this AREA and found THIS"* are **fixed text per witness
and per area**. Fixed text can be written once, during generation, in the call that is already
being made.

**One generation call, then a whole game at zero further API cost, is the intended architecture**
(owner, Session 34: *"We never, ever planned for live calls. We want the prompt, we want to generate
off the prompt and never use AI again."*).

**The code does not currently do that.** Six live play-time call sites exist in `server/main.py` —
`_investigate_area_with_ai` (779), `_follow_lead_with_ai` (798), `_generate_witness_scene` (1135),
both `/interrogate` endpoints (2306, 2398) and `_generate_resolution_narrative` (707). They arrived
with the Session 21 lockstep redesign and the Session 26 reveal; nobody chose a per-action
architecture, it accumulated an endpoint at a time. **Single-player interrogation hits 2398 on every
question, so this is on the playtest path.** Build-order step 5 is what closes it.

Because there are then no play-time calls, a mystery's whole AI cost is fixed, one-time, and paid
before anyone plays — it does not scale with players or replays. **That makes generation the right
place to spend, and "more expansive" the cheapest improvement available.** Watch two limits as the
payload grows: output is 8,667 tokens against a 16,000 cap (1.85× headroom), and anything above
~16,000 must switch the generation call to streaming or risk an HTTP timeout.

Schema additions needed in `_generate_mystery_dict`'s prompt:

| Field | Where | Why |
|---|---|---|
| `discovery` | each `investigation_areas[i]` | the "and found THIS" half of step 4 |
| `analysis` | each `investigation_areas[i]` | the "testing and research reveal…" half |
| `statement` | each witness character | step 3's actionable info |
| exactly **4** suspects | `characters` | step 6's dropdown |
| **3–4** witnesses | `characters` | the map needs bodies to place; today it gets 1 |

The existing `investigation_prompt` fields stay: they are what the *dynamic* version uses, and
stage 3 will want them back.

---

## Blocker: no saved mystery can run this flow

Measured, not assumed — all 18 saved mysteries:

- **0 have `investigation_areas`.** The prompt has asked for exactly 5 since Phase 3a. Every saved
  file predates that change (March 12 / April 3, 2026).
- **0 have `leads`**, same reason.
- **1 witness each** (three have none). Step 2 needs several.
- **3 suspects each** (three have two). Step 6 wants four.

So the current generation prompt **has never been verified to produce areas or leads at all**, and
the mystery picker in step 1 currently offers eighteen mysteries that cannot support steps 2, 4
or 6.

**This is the first thing to fix, and it costs one real generation call.** Nothing downstream can
be tested against real data until a mystery exists in the current schema.

---

## Coherence validation (owner item 7.1)

The engine must be checked from more than one vector, because Session 34 found it succeeding at
detection and being ignored by the pipeline (`CLAUDE.md` item 18).

1. **Does it detect what it claims?** Feed it deliberately broken mysteries and assert each
   expected `Issue` code fires. Zero API cost.
2. **Does it pass what it should?** Feed it a real generated mystery and assert no false blocking
   issue. Needs one real generation.
3. **Does anything act on the verdict?** Currently no — a `BLOCKING` report is saved and served.
   Item 18.

New rules the added fields need: every area has a non-empty `discovery`; at least one
`discovery` or witness `statement` points at the culprit; no area's `discovery` names the culprit
outright (or the mystery is solvable in one click).

---

## Build order

1. **Generation prompt + schema** — the four field additions above. Zero cost to write.
2. **One real generation**, to prove the prompt returns what it claims. **Owner sign-off: it is
   real API spend.**
3. **Coherence rules** for the new fields, plus the deliberately-broken-mystery test set.
4. **Crime-scene screen** in Godot — draws `crime_scene_map.build_map()`, hosts the area clicks,
   the witness markers and the "I've solved it" button.
5. **Simplify interrogation and search** to read the pre-written text instead of calling out — this
   is what removes the six live call sites, not a cosmetic simplification.
6. **Grey out leads.**
7. **Mystery picker** — titles only.

Steps 1, 3, 4, 5, 6, 7 cost nothing. Only step 2 spends money, and everything after it depends on
what it returns.
