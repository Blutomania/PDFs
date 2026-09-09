# The investigation model — locations, rounds, and provable solvability

**Status: design, agreed in conversation (owner + Claude, Session 35, August 25 2026). Nothing
here is built.** It supersedes item 20's "CLOUD" sketch in `CLAUDE.md` wherever the two differ,
and it exists because a UX question about drawing a map turned up three live defects in the
game underneath it.

Read `docs/PLAYTEST_FLOW.md` first for the screens as they stand today.

> **[Session 38 — August 28, 2026] Reconciled with APF.** This document was written alongside APF
> and parts of it pre-date the deletions APF makes, so it contradicted itself in three places about
> the map, the deadlock and the build order. §5, §6 and §7 now say which of their contents APF
> closed and which survive. **Only one open question remains** (§6.5, titles that spoil); the other
> four were closed by APF rather than answered. Nothing was deleted — a closed question keeps its
> reasoning, because the reasoning is what makes it re-openable if APF ever is.

---

## 1. The crime scene is not a floor plan

`crime_scene_map.py` draws a **building**. `_grid_shape()` makes a near-square grid and
`_row_rects()` fills each row edge to edge — its own docstring says a gap "reads as a missing
room rather than as the shape of the building."

Run a Black Forest mystery through it and you get:

```
A1  Woodcutter's Hut       x= 24.0  y= 24.0  w=308.0  h=289.0
A2  The Ravine             x=346.0  y= 24.0  w=308.0  h=289.0
A3  Charcoal Kiln          x=668.0  y= 24.0  w=308.0  h=289.0
A4  Forest Track           x= 24.0  y=327.0  w=469.0  h=289.0
A5  Hunting Lodge Cellar   x=507.0  y=327.0  w=469.0  h=289.0
```

A forty-metre ravine as a 308×289 box, fourteen pixels from a hut.

**Where the assumption lives matters.** Generation is already setting-agnostic — the field is
`investigation_areas`, "named physical locations… plausible for the setting," and the word
"room" appears nowhere. The coherence engine has no spatial rule at all (all 26 codes are causal
chain, evidence variety, alibi anchoring). **Only the renderer assumes walls.**

### The decision: a connection map

Locations as nodes, connections as lines. Setting-agnostic by construction, because a line
claims only "these two relate" — true of a hallway, a footpath, and a companionway alike, while
a box always claims walls.

**The owner's argument is the strongest one and belongs on the record:** a Dick Francis mystery
spans a racetrack, training stables, a country estate and a lawyer's office. Rendering those
top-down is absurdist. Proximity is not the constraint; *access* is.

It also matches what the corpus actually holds. P3.F4 "setting as constraint" on *The Red House
Mystery* reads: *"an office reachable only through a passage of spring-hinged doors… door
movements are legible only as shadows on the passage wall."* That is a relation, not a floor
plan — and a relation is exactly what an edge is.

### Open: what does a line mean?

Three candidates, in ascending cost:

| Reading | Line means | Note |
|---|---|---|
| **Relationship** | "part of the same case" | Movement free. The map is a picture, not a mechanic. |
| **Provenance** | "this revealed that" | Falls out of §3's unlocking for free. Map becomes case history. |
| **Narrative access** | "reachable only once X is known" | A real mechanic. Most to build. |

**Owner is stewing on this.** Provenance looks like the natural fit given §3, and it costs
nothing extra.

> **[RESOLVED, Session 38 — August 28, 2026.] Not decided; closed by APF.** Two of the three
> readings lost the mechanic they described. *Narrative access* is traversal, and APF deletes
> traversal. *Provenance* is generated entirely by §3's growing pool — a hotel key opening a hotel
> room — and APF assigns findings rather than letting players gather them, so nothing reveals
> anything and there is no provenance to draw. Only *relationship* survives, and *relationship* is
> defined here as "the map is a picture, not a mechanic" — the same conclusion the correction
> below reaches independently.
>
> **The owner's actual decision (Session 38) went further: no map at all for the playtest.** See
> §6.

### Correction (owner, later the same session): top-down is NOT rejected — rectangle-packing is

The first draft of this section generalised the defect from "packs rectangles" to "top-down."
**That was too broad, and the owner was right to push back.**

`_row_rects` fills each row edge to edge because its docstring reasons about *"the shape of the
building"* — it is drawing **interior architecture**. That is what breaks on a forest. The
overhead view is not the problem; the tiling is.

**Scale is what absorbs the Dick Francis case:**

| Story | Scale |
|---|---|
| Country house | floor plan |
| Antarctic station | site plan |
| Black Forest | terrain |
| Racetrack, stables, estate, lawyer's office | regional |

Same renderer, different zoom. *"Things placed in 2D space"* is true of all four; *"rooms tiled
into a rectangle"* is true of one.

It also removes the cost this document raised against the connection map — that a node graph
*"looks like a diagram, not a place."* A map at the right scale reads as somewhere.

**In APF the map is presentation, not mechanic** (`docs/PLAYTEST_FLOW.md`). With no traversal it
cannot deadlock, cannot gate anything, cannot lie about movement. It orients, and it gives the
game a place — which is exactly the "not just text" problem APF creates.

**The change is small.** Seven functions in `crime_scene_map.py`; only `_grid_shape` and
`_row_rects` are the offenders. `_seed_fraction` (determinism), `_point_in` (placing something
inside a region), `_best_area_for_crime` and `build_map`'s shape all survive. Most of the 193
assertions stay valid too — they test invariants a scattered layout must also satisfy (nothing
off-canvas, no overlaps, witnesses inside their area, identical run to run). Effectively only the
row-filling test goes.

**Simplest version that works:** labelled markers at seeded positions on a plain ground. No
terrain art, no walls, nothing to scale. Stable across reloads because the seed is the title.

Two things that do not change at any scale:

- **Do not claim precision you do not have.** A labelled marker is honest; a to-scale plan invites
  "but the hut overlooks the ravine" objections the data cannot back.
- **The witness fabrication is still a bug.** `area = placed[i % len(placed)]` is round-robin
  whether you draw rooms or a region. It still wants a real `area_id` from generation.

### Explicitly rejected

Teaching the floor plan about forests — i.e. per-setting rendering branches. Every new setting
would need new code, and the prompt box accepts anything. Scale generalises; special cases do
not.

---

## 2. A location is a container, not a single action

Today an area holds **exactly one** action: investigate it once, receive `discovery` +
`analysis` together, budget drops by one, and once anyone shares it the area is blocked for
everyone.

Worse, of the four content types only one is genuinely located:

| Content | Count | Located? | Actionable there? |
|---|---|---|---|
| Area discovery + analysis | 5 | yes, by definition | yes |
| Evidence items | 8 | **no field at all** | no |
| Witnesses | 3–4 | **fabricated by the renderer** | no |
| Leads | 4 | no | no |

**The witness placement is fiction.** `crime_scene_map.py` assigns witnesses into areas
round-robin: `area = placed[i % len(placed)]`. Nothing in the mystery says where anyone is. So a
witness whose statement is "I was in the kitchen all evening" can be drawn standing in the
ravine — and there is no action attached either way, because interrogation is a separate phase
that picks from a list.

### The decision

- **Witnesses get a real `area_id`.** Generation already knows — it writes locations into alibis.
- **Evidence gets `area_id`.** Same reasoning.
- **Leads stay off the map**, in a panel beside it. An anonymous letter has no honest location.
- A location then shows what it holds, and multiple players can visit it for **different**
  business. The backend already supports this: `block_pool` is three pools with three
  granularities (`witness` per person-per-question, `investigation` per area, `lead` per lead),
  so "player 1 questions the witness at the Track, player 2 searches the Track" already blocks
  independently.

**Density becomes emergent, not allocated.** ~5 locations × ~3 affordance types is a *ceiling*
of ~15 actions, not a target. A thin mystery draws a thin map — a quality signal, and checkable
for free ("no location has any affordance" is a warning).

This removes the pressure to raise the area count, which was the previous plan. Do not spend
tokens on more rooms until this is settled.

---

## 3. The narrative casefiles out the options, and the pool grows

**Owner's design.** Round 1's options are not discovered — they are *stated*, in prose, by the
opening narration:

> "To start your investigation Hansel and the Gingerbread Man should be questioned. The
> gingerbread house should be investigated for clues, so should the front yard where Gretel
> died. Finally, that wolf in grandmother's clothing seems out of place, doesn't he?"

Round 2 = whatever nobody took, **plus** what round 1 unlocked. A hotel key found at the scene
opens the hotel room as a location and the receptionist as a witness. Car tracks in the mud.
Name tags in the wolf's clothing.

### What this fixes

- **Blind exploration is gone.** The owner's objection was that toiling while friends find things
  is neither fun nor social. It is also *structurally* the deadlock (§5): no findings means
  nothing to share, which means excluded from the social loop and unable to advance.
- **The deadlock cannot occur.** The pool grows faster than it is consumed. No player arrives at
  an exhausted board. That is a structural fix, not a patch.
- ~~**It answers "what is a line"** — provenance.~~ **[Superseded, Session 38.]** True only
  while the growing pool exists. APF deletes it, which takes provenance with it — see the
  resolution note in §1 and §6.

The generation prompt already agrees with the no-toil principle: *"Every area must yield
something; an area that yields nothing wastes the only move a player gets there."* The interface
simply never surfaced it.

### Scope: this works as a list first

Round 1 shows five named options; you pick. **No map required.** The connection map earns its
place only once there are enough options that history matters. Build the growing pool, ship the
playtest as a list, add the map after — nothing is thrown away.

### What it requires

1. **The whole tree is generated up front**, round 2's car tracks included, each node tagged with
   what reveals it. Not invented mid-game: that is a new API call per unlock, and it can
   contradict a solution already written.
2. **The briefing may only name things that exist as data.** If the prose says "question the
   gingerbread man" and no such character exists, the game breaks on the first click. Free
   coherence rule.
3. **Playtime becomes variable.** More unlocks, more rounds, against a 30–75 minute target.
   Something must cap it — a round limit, or a budget that does not grow with the pool.

---

## 4. Solvability as arithmetic — the central idea

> *"How do we ensure the clues are actual clues that come together for the solution?"* — owner

**What cannot be checked cheaply:** that a serrated bolt-driver *implicates* Dr. Hale. That is
meaning, and meaning costs an API call.

**What can:** that the clues **eliminate**.

### Today the link does not exist

From the one real generation on disk (*Whiteout at Shackleton Base*):

```
suspects      : Hale, Tanaka, Larssen, Caron
culprit       : Dr. Marcus Hale
key_evidence  : [E1, E2, E3, E4, E6]

E1  critical     Dr. Solberg's USB Audit Drive
E2  critical     Serrated Bolt-Driver
E3  critical     Cold Storage Motion-Sensor Log
```

`relevance: critical` is a **label, not a relationship**. Nothing says E3 rules out Tanaka. The
claim that these five items prove Hale did it lives only in a paragraph of prose.

And `P1.C5.dangling_key_evidence` — the rule that is supposed to guarantee solvability — has the
message *"Resolution refers to evidence players can never find"* while checking only that the ID
appears in the evidence array. **Same failure family as Session 34's culprit bug: a rule whose
message states the real requirement and whose check is a weaker proxy.**

### The decision: make elimination a field

```jsonc
{ "id": "E3", "name": "Cold Storage Motion-Sensor Log", "exonerates": ["Tanaka"] }
{ "id": "E6", "name": "Keycard Access Log",             "exonerates": ["Larssen", "Caron"] }
{ "id": "E2", "name": "Serrated Bolt-Driver",           "implicates": ["Hale"] }
```

Then solvability is a set operation, free and deterministic:

> Take every suspect. Remove everyone exonerated by the key evidence.
> **Exactly one must remain, and it must be the stated culprit.**

Three BLOCKING conditions fall out, none of them detectable today, all of them producing a game
a player cannot win:

| Condition | Meaning |
|---|---|
| two or more survivors | no unique answer |
| zero survivors | the evidence contradicts itself |
| survivor ≠ stated culprit | prose and structure disagree |

### Paired with reachability

Elimination only matters if the evidence is obtainable. So: **every key evidence item must be
surfaceable by at least one player action** — which needs §2's `area_id`. Together the two rules
are a real proof: *the clues that eliminate all but one suspect are all obtainable.*

### A free interim check, available now

`how_to_deduce` already cites evidence IDs *and areas* inline —
*"the Cold Storage motion log **(E3, Area A1)** shows two separate entries…"*. Generation knows
all of this and writes it into prose instead of fields.

So before any schema change: **parse the evidence IDs out of `how_to_deduce` and confirm they
cover `key_evidence`.** If the solution's own reasoning never mentions E1, E1 is not load-bearing
and should not be listed as key. Zero cost, catches sloppy generations today.

#### [Session 38] It was built, run on all 17 mysteries, and the check above finds nothing

`scripts/check_solvability.py`. **0 of 17 mysteries list a key item the reasoning ignores**, so the
direction proposed above is already clean and is a regression guard rather than a discovery tool.

**The gap is the other way round, and it is in 16 of 17.** The reasoning cites evidence that
`key_evidence` does not contain — **55 items in total, up to 6 in a single mystery.** Only
*Whiteout at Shackleton Base*, the newest, has none.

That matters more than the direction originally proposed, because **APF's constrained assignment is
specified over "the evidence that proves the case"** (`docs/PLAYTEST_FLOW.md`). Read that set from
`key_evidence` and the assignment can casefile a player every key item while omitting three the solution's own
reasoning depends on. The assignment would satisfy all three of its stated constraints and the player
still could not get there. So before the assignment is built, one of these has to happen:

- redefine `key_evidence` as *exactly* the evidence the reasoning uses, and check it; or
- run the assignment over the cited set rather than the key set.

**Two more measurements that bound what `exonerates` can do:**

- **86% of non-culprit suspects are already named in the reasoning** (26 of 30). Elimination is
  mostly being written as prose already, so `exonerates` formalises something generation does
  rather than asking for something new — a much cheaper schema change than it looked.
- **16 of 17 mysteries have 2 or 3 suspects**, against the four `docs/PLAYTEST_FLOW.md` specifies —
  **but that is a corpus-age artefact, not a generation fault.** The prompt rule *EXACTLY 4
  suspects* was added on 2026-08-21 (`145877d`); sixteen of the seventeen were generated in March
  under the older prompt. **The single mystery generated under the current prompt has exactly
  four.** Re-measure after the next few generations before concluding anything.

  The arithmetic matters regardless of which way that lands. Eliminating down to one needs **S−1**
  exonerations, so the suspect count is a hard ceiling on how many findings can be *provably*
  load-bearing, and therefore on how many players can hold one. **At 3 suspects exactly 2 findings
  are load-bearing, so in a 4-player game at most half the room holds anything the proof needs; at
  4 suspects it is 3, which is why the spec says four.**

### [Session 38] The third assignment constraint is not achievable as written

`docs/PLAYTEST_FLOW.md` requires that an assignment *"becomes solvable once the minimum share threshold is
met."* Measured against the code, that constraint is not well-formed. `share_min` is a **minimum
fraction of a player's own findings** (`_min_share_required()` in `server/main.py`), and **the
player chooses which ones**. Meeting the threshold therefore does not determine what reaches the
pool: a player holding three findings at MEDIUM shares two and withholds one, and which one they
keep is the whole point of the mechanic.

**How well can they choose? Value is never labelled on a finding, but it is legible.** A finding
carries an id, where it came from, and generated prose — no `relevance`, no score, and (see below)
no evidence ID either. So a player cannot look up which of their three matters. But the prose is
generated *from* the evidence, so a decisive finding usually reads as decisive: *"I found whose
blood was on the knife"* needs no label. **That is uncertainty, not ignorance** — which makes the
adversarial worst case unlikely rather than impossible, and means a probabilistic guarantee (the
assignment is solvable under *most* share patterns, enumerated) is a legitimate fourth option beside the
three below.

> **Note the inconsistency.** `case_display.gd` renders a **★ for critical** and an **✗ for red
> herring** beside every evidence item on the solo case screen. So the single-player route labels
> exactly what the multiplayer route hides. That looks like a debug affordance that shipped, and it
> should be a decision either way.

So "solvable once the threshold is met" is only true if it holds for **every** legal choice of what
to share — including the case where every player withholds their most load-bearing finding. And it
cannot be guaranteed in general without deleting the hoarding decision, because a finding that must
reach the pool is a finding nobody may keep.

**That makes it a design choice rather than a bug, and it is the owner's:**

| Option | Consequence |
|---|---|
| **Accept it** — universal hoarding can end a game with no winner | Honest, and arguably the tension the game is *for*. Needs to be a designed outcome with a screen, not a silent dead end. |
| **Assignment for redundancy** — no exoneration exists in only one casefile | Pure set arithmetic, free, enforceable by re-running the assignment. Weakens hoarding without deleting it: withholding costs the room less because someone else may share it. |
| **Pigeonhole it** — give one player more critical findings than they can withhold | Guarantees at least one exoneration reaches the pool, since a player must share `h − withhold_allowance` items and will shed the least critical first. Also free. |

None of these needs an API call; all three are constraints on the assignment, which is already specified
as pure computation and re-runnable at zero cost.

#### [Session 39] Two of the three are implemented; redundancy is the default

`casefiles.py` takes `redundancy` — the number of **distinct casefiles** each required exoneration must
reach. That single parameter covers two of the three rows above: **redundancy 1 is "accept it"**
(constraints 1 and 2 only, universal hoarding can end a game with no winner) and **redundancy 2 is
"assignment for redundancy"**. **"Pigeonhole it" is a genuinely different constraint and is NOT
implemented** — it is not reachable by setting the parameter, and the module says so rather than
letting a reader assume otherwise.

**[Session 39, second pass] Redundancy buys two rungs, not three, and the ceiling is provable.**
It fights constraint 2 directly: each of the R required exonerations sits in at least k casefiles, so
some casefile holds at least ceil(R·k/P) of them, and when that reaches R that casefile holds every
exoneration and solves alone. At APF's specified shape — 4 players, exactly 4 suspects, R = 3 —
**the ceiling is 2**, so EASY takes it and MEDIUM and HARD are both 1. `feasibility()` reports this
up front rather than failing 400 attempts. **Moving difficulty here fixed EASY-vs-the-rest and did
not fix MEDIUM-vs-HARD**; a third rung needs a second dial, and Session 38 already named the two
candidates — suspect count and red-herring density.

Redundancy is the default because it does double duty. The difficulty ladder is inert at a
three-finding casefile, and this is the home with real resolution at that size:
`REDUNDANCY_BY_DIFFICULTY` puts each exoneration in two casefiles on EASY so somebody will share it,
and one on HARD so withholding really bites. **Still the owner's call** — the parameter is where
it is decided, not a value baked into the algorithm.

#### [Session 38] A prerequisite nobody has listed: findings carry no evidence ID

The three finding constructors in `server/main.py` produce `{id, where it came from, prose}` and
nothing else. **There is no reference to the `evidence[]` array**, so the solvability arithmetic —
`exonerates` / `implicates` on evidence items — and what a player actually holds are two data
models with no join key. **The constrained assignment cannot be built until a finding carries the
evidence ID it came from**, because otherwise the assignment is distributing opaque prose and cannot
reason about which exoneration landed in which casefile. This is not on §7's build order and should be.

##### [Session 39] Closed — and the blocker as written pointed at the wrong code

The three constructors it names are the **gather** routes (`/investigate-area`, `/follow-lead`,
`/interrogate-witness`). APF's premise is that findings are assigned, not gathered, so a join key
bolted onto them would have fixed the path being replaced. Under APF a assigned clue **is** an
evidence item and carries its own id — there is nothing to join.

**The gap that actually blocks the assignment is larger.** APF's casefile is one witness statement, one
crime-scene clue, one lead result, and `exonerates` / `implicates` live **only** on `evidence[]`.
Witness statements sit on `characters[].statement`, lead results on `leads[]`, area findings on
`investigation_areas[].discovery`. None carried elimination data, so **two of the three kinds in
every casefile were structurally inert** — they could not participate in the set arithmetic all three
assignment constraints are defined over.

**Fixed with a pointer, not by duplicating the fields.** Witnesses, leads and areas carry
`reveals` — the evidence ids they surface. Elimination data therefore lives in exactly one place,
and a witness's exoneration cannot drift out of agreement with the evidence item's, which is a
defect no structural check could have caught. Copying `supports` / `exonerates` / `implicates`
onto every kind was the considered alternative and was rejected for exactly that reason.

`casefiles.py` reads a casefile's eliminating power through the pointer; `scripts/check_narrative.py` gained
a REVEALS branch for dangling pointers, findings that reveal nothing, and exonerations reachable
only as a clue. Both are fixture-tested, because no mystery on disk carries the field.

#### [Session 38] And at APF's casefile size the difficulty ladder does not exist

APF assigns **three** findings — one witness statement, one crime-scene clue, one lead result. Put
that casefile through the rule at each difficulty:

| Casefile | EASY 0.70 | MEDIUM 0.60 | HARD 0.50 |
|---|---|---|---|
| 3 findings | share 2, **keep 1** | share 2, **keep 1** | share 2, **keep 1** |

**All three difficulties are identical.** The ladder is inert at three held findings, because a
percentage has no resolution over three items. Only three outcomes are reachable — keep 0 deletes
the mechanic, keep 2 means sharing a single finding — so **keep 1 is effectively forced, and
difficulty cannot live in the share rule at all.**

- **State it as a count, not a percentage.** At these casefile sizes `share_min` cannot express what it
  is for, which is why two reasonable roundings of it disagreed and neither produced a ladder.
- **Difficulty needs another home**, and the redundancy option above is the natural one: EASY assigns
  each exoneration into two casefiles so someone will share it; HARD assigns each into exactly one so
  withholding really bites. That has real resolution at a three-card casefile. Suspect count and
  red-herring density are the other candidates.

**A duplicate of the rule was found and removed while measuring this.** The client computed the
minimum with `ceili()` where the server used `round()`; they disagreed in 6 of 18 realistic
combinations, always with the client stricter, so it refused shares the server would have accepted
— and at a two-finding casefile demanded both, deleting the choice entirely. The server now computes it
once and sends it with every finding response; `scripts/test_share_rule.py` asserts the client has
no rule of its own.

### What is deliberately left to the playtest

Whether a clue is **fair** — whether a human could reasonably make the leap — is craft judgment,
not arithmetic. That answer comes from the feedback loop already designed: the viability rating,
plus accusation data (how many got it right, how long it took).

**Structure is provable for free. Fairness is empirical. Meaning is the expensive middle you
mostly do not need to buy.**

> For the funding pitch this is the strongest form of the coherence pillar: not "we check the
> story hangs together" — table stakes — but **"we prove the mystery has exactly one obtainable
> solution before anyone plays it."**

---

## 5. The deadlock (superseded by APF — kept because the analysis is still the record)

> **[Session 38] Not a live blocker.** Fix 0 below is the decision: APF deletes the mechanic that
> carries the bug. The diagnosis is kept because it is the reason APF exists and because the phase
> gate would return with any future gathering mechanic.

Three facts in `server/main.py`:

1. **Sharing is the only exit from a phase.** `player["phase"]` advances in exactly one place,
   inside `share_findings`.
2. **You cannot share nothing.** `if not all_findings: raise HTTPException(400, …)`.
3. **Every area can be blocked before you act.** Sharing an investigation finding adds its
   `area_id` to `block_pool`; investigating a blocked area returns 409.

A player reaching the investigation phase with all five areas shared gets 409 on every room, 400
on share, and **cannot advance, ever.**

It is not an edge case:

```
EASY    4 players × 3 = 12 investigations wanted, 5 areas exist
MEDIUM  4 players × 2 =  8 investigations wanted, 5 areas exist
HARD    8 players × 2 = 16 investigations wanted, 5 areas exist
```

Every difficulty at every player count wants more investigations than there are rooms.

**The root cause is the phase gate**, not the block pool — lines 2076 / 2130 / 2363 lock a player
into one action type at a time. A player stuck in `investigation` cannot do the witness or lead
work sitting right there.

### Fixes, in order of preference

0. **[Session 35, owner] APF deletes the mechanic that has the bug.** With findings assigned rather
   than gathered there is nothing to block, every player holds findings by construction, and there
   is no phase to be trapped in. See `docs/PLAYTEST_FLOW.md` → "APF". This is the current plan for
   the playtest, and it is the cheapest correct outcome: the bug stops existing.
1. **§3's growing pool** — the deadlock stops being possible.
2. **Change the exit condition** to *"you are done acting,"* not *"you found something."*
   Spending a budget on three red herrings is a legitimate way to play a mystery badly; it should
   end a phase, not trap a player. Today, "found nothing useful" and "found nothing at all" are
   the same state to the code, and only one of them should be.
3. **The minimum patch**: advance when the player has no findings *and* no unblocked targets.

Owner's framing that made this clear: not every action needs to be vital — red herrings and
innocent bystanders are the point — so the fix is never "add just enough content."

---

## 6. Open questions

**[Reconciled, Session 38 — August 28, 2026.] Four of the five questions below were written in
Session 35 and were CLOSED BY APF, not answered.** They are kept, struck through, with what closed
each — deleting them would lose the reason, and the reason is the useful part.

**Why this drifted:** `CLAUDE.md` item 23 already reduced §7's build order for APF ("Order … reduced
by APF"). Nobody did the same pass on this section. The build order knew about APF; the open
questions did not, so a reader arriving here worked through four decisions that no longer have a
mechanic attached. That is a documentation failure, not a design one.

| # | Question | Closed by |
|---|---|---|
| 1 | ~~What a line means — relationship, provenance, or narrative access~~ | *Narrative access* is traversal; *provenance* comes only from §3's growing pool. APF deletes both. Only "the map is a picture, not a mechanic" survives — and the owner then removed the map from the playtest entirely (below). |
| 2 | ~~Affordance display — counts, or only presence~~ | Its own justification was *"turns blind exploration into informed allocation."* APF deletes blind exploration. |
| 3 | ~~Player position visibility~~ | Presumes players are *at* locations. Nobody has a position under APF; there is no movement to reveal. |
| 4 | ~~Budget model — one pool of N, or three separate allowances~~ | The investigation budget is on APF's deletion list (`docs/PLAYTEST_FLOW.md` → "What this deletes outright"). |

### The question that was actually underneath question 1 — DECIDED

APF removes exploration, which creates the problem §1 names in passing: *"the 'not just text'
problem APF creates."* So the live question was never what a line means; it was whether there is a
picture at all.

> **Does the APF playtest show a picture of the crime scene, and may it mean anything?**
>
> **(a) No picture** — a list of named findings. §3 already sanctions it: *"Round 1 shows five
> named options; you pick. No map required."*
> **(b) Orientation art only** — labelled markers at seeded positions on a plain ground. No lines,
> no claims, no mechanic. Costs dev time, not API spend: `crime_scene_map.py` renders locally.
> **(c) A map that carries information** — requires reinstating a mechanic APF deleted. Stage 3.

**Decision (owner, Session 38): (a), for now.** Owner's reasoning: anything beyond it adds cost for
minimal play-testing benefit. Nothing is thrown away — §3's *"ship the playtest as a list, add the
map after"* still holds, and (b) remains the cheap upgrade if a real player finds the screen bare.

**One thing this decision does NOT dispose of.** The witness-placement bug is orthogonal to whether
a map is drawn: `area = placed[i % len(placed)]` is round-robin whether you render rooms, a region,
or nothing at all. It fabricates a fact about where a witness was. Drawing no map hides it; it does
not fix it, and it still wants a real `area_id` from generation before any map returns.

### 5. Titles that spoil — THE ONE STILL OPEN

Player titles now feed generation, and *"Why did Hansel Grimm kill Gretel Grimm"* names the culprit.
That is a whydunit — a legitimate form, a different game. Generation should treat such a title as
premise or as misdirection **by decision, not by accident.**

Untouched by APF: it is a property of the title→generation path, which APF does not change. This is
the only question in this section that is still a question.

---

## 7. Build order

**[Reduced by APF, Session 35; written down here Session 38.]** This now matches `CLAUDE.md`
item 23, which was the only place the reduced order existed. The Session 35 table it replaces is
below it, with what happened to each row.

| # | Step | Why here |
|---|---|---|
| 1 | `exonerates` / `implicates` on evidence + the set-arithmetic solvability check (§4) | The solvability proof, and the funding pillar's strongest form. Everything else assumes it. |
| 2 | The constrained assignment | Pure computation, deterministic, re-runnable at zero cost. Needs step 1's fields to check its own constraints. |
| 3 | The share decision, the suspect board, the reveal | The 75% mechanic with nothing in front of it — the thing the playtest exists to test. |
| 4 | `cinematic_brief: bool = True` for the paced text opening | Presentation. Last because a bare opening still plays. |

Steps 1–4 are the whole of stage 1. There is no stage-1 map.

### What dropped out of the Session 35 order, and why

| Was | Now |
|---|---|
| 1 — Deadlock fix | **Gone.** APF deletes the mechanic that has the bug (§5, fix 0). |
| 2 — `how_to_deduce` ID-coverage check | **Still free and still worth running**, but off the critical path: it catches sloppy generations, it does not build the loop. Do it whenever. |
| 3 — `area_id` on witnesses + evidence | **Deferred with the map.** Under APF the constrained assignment guarantees reachability directly — a finding is in somebody's casefile or it is not assigned — so §4's reachability rule no longer needs area data. It returns when a map does, and the round-robin witness placement is still wrong until then (§6). |
| 5 — Growing option pool | **Gone.** APF assigns findings instead of unlocking them. |
| 6 — Connection map | **Deferred.** §6 decision (a): no picture for the playtest. |

**Token cost of the schema additions is not a constraint.** A full generation measures ~7,200
tokens against a 16,000 ceiling; the fields above add a few hundred.
