# Coherence, in plain terms

*A re-readable explanation of how Choose Your Mystery decides whether a generated mystery is any
good — written to be understood, not to be complete. Session 38, August 2026.*

For the full reasoning see `docs/INVESTIGATION_DESIGN.md` §4 and `docs/DECISIONS.md` item 26.

---

## The one-sentence version

A mystery has to add up in two completely different ways, we could only check one of them, and the
fix was to change the order in which the mystery gets written.

---

## Two ways a mystery can add up

**The first is arithmetic.** Four suspects. The evidence rules out three. One is left, and that one
is the culprit. This is countable. A computer can verify it with no judgement and no cost — it is
set subtraction, the same operation as crossing names off a list.

**The second is narrative.** The story hangs together. The motive explains why *this* person did
*this* thing. The method is physically possible given where everyone says they were. The people in
the explanation are people you actually met. This is not countable. It is meaning.

**These are independent.** A mystery can be perfect at the first and broken at the second. That is
not hypothetical — we have one on disk.

---

## What we found

`daggers_in_the_forum` is a generated mystery about a murder in ancient Rome. It **passes every one
of our 26 coherence rules**. Clean sweep: zero blocking problems, zero warnings.

Its solution explains who did it by reasoning about four people — Apolonios, Demetrios, Senator
Manilius and one other — **none of whom exist in the mystery.** They are not in the cast. A player
cannot meet them, question them, or accuse them. The explanation for the crime turns on people who
are not in the game.

Across all 17 mysteries we have generated, **7 do some version of this.**

### Why every check missed it

I sorted our 26 rules by what they actually test:

| What the rule does | How many |
|---|---|
| Checks a field is present and not empty | ~15 |
| Counts things — "at least 2 physical clues" | ~9 |
| Checks a name actually resolves to something | **2** |
| Checks the story makes sense | **0** |

And the two useful ones only look at *structured fields* — the `culprit` field, the `key_evidence`
list. **Nothing ever looked at the prose**, which is where the story lives.

So the engine was checking that the boxes were filled in, not that what was in them cohered.

---

## Why it was happening

This is the part worth understanding, because it explains the fix.

**We were asking for the mystery in the wrong order.** The instructions to the AI listed the parts
like this:

> the crime → the characters → the clues → **the solution**

The solution came **last**. So the AI invented a cast of characters, then invented a pile of clues,
and only then had to work out an explanation that fitted everything it had already written.

That is writing a mystery *forwards*, and every writer of the form will tell you it does not work.
You write a mystery **backwards**: decide who did it and why, then plant the clues that lead there.

**Here that is not a matter of taste, it is mechanical.** An AI writes one word at a time, left to
right, and everything it writes is influenced by what it has already written. Put the solution last
and the solution is shaped by the clues. Put it first and the clues are shaped by the solution.

The adage from novels and screenwriting turns out to be a statement about *order of composition*,
which is exactly what an AI is doing. So it applies unchanged.

**And it explains the Apolonios bug precisely.** Writing forwards, the AI reaches the end and needs
a chain of reasoning that its cast cannot support. It has two options: go back and rewrite the cast
it already committed to, or invent someone new. Inventing someone is easier. So it invents someone.

---

## What we changed

**One: the solution is now written first.** The order is now

> the setting → **the solution** → the crime → the characters → the clues

The cast is written *after* the culprit is decided, so the cast has to contain them. That one escape
route is closed.

**Two: every clue now says what job it does.** Previously the connection between a clue and the
answer existed only in the prose, where no program could see it. Now each clue carries three
labels:

| Label | Means |
|---|---|
| `supports` | which step of the reasoning this clue is evidence for |
| `exonerates` | which suspects this clue clears |
| `implicates` | which suspects this clue points at |

And the solution now carries a numbered chain — step 1, step 2, step 3 — instead of one paragraph
of prose.

**Why this matters more than it sounds.** Once the connections are written down as labels rather
than buried in sentences, checking the story becomes checking a diagram. Is every step of the
reasoning supported by at least one clue? Does every clue point at a step that exists? Does crossing
off the cleared suspects leave exactly one person, and is it the right one? Is there anything that
positively points *at* the culprit, rather than us arriving at them only by elimination?

All of those are now checked, **for free, with no AI call.** We stopped asking a program to work out
the relationships and made the AI state them.

---

## What this does NOT fix

**Read this part twice, because it is the easiest thing to over-claim.**

The AI can write `supports: step 2` on a clue that does not actually support step 2. Nothing in the
system can tell. Labels can lie.

So what did we actually buy?

**We changed the direction things go wrong in.**

- Writing forwards, when the story drifted, the AI *invented people*. That is invisible — everything
  is filled in, all the boxes are ticked, and the mystery passes.
- Writing backwards, when the story drifts, it produces *a clue that doesn't fit the plan*. That
  shows up as a broken link in the diagram, and we catch it.

**We swapped an invisible kind of failure for a visible one.** That is a real and worthwhile win. It
is not the same as "the story is now guaranteed to make sense."

The things still not checked by anything:

- **Does the motive really explain the crime?** Money is a motive. Is it enough of a motive for
  *this* murder by *this* person? That is judgement.
- **Is the method actually possible?** Given where everyone says they were, could he have done it in
  the time available?
- **Did we make the mystery the player asked for?** Somebody types "1920s Harlem jazz club". Did
  they get one? Nothing checks this at all, and it is the very first thing a real player judges.

Those three need an AI to read the finished mystery and give an opinion. That is the open decision
below.

---

## What now demands your attention

**1. Generate one mystery.** Everything above is untested against a real generation, because running
one costs money. If the AI ignores the new labels, the entire checking layer is inert and you want
to know that before anything is built on top of it. Run `python3 scripts/check_narrative.py`
straight afterwards.

**2. Decide about the "critic".** A *critic* is one extra AI call that reads the finished mystery
and reports faults — it does not rewrite anything, it just tells you what is wrong. It would cover
motive, method and "did we deliver the prompt", the three things nothing else can check.

The cost is the surprising part. A normal generation costs about **$0.14**, and almost all of that
is the AI *writing* a long mystery. A critic does the opposite — it reads a lot and writes a little
— so it costs about **$0.04**, roughly a quarter more per mystery, paid once and shared across every
replay.

Two honest warnings. An AI checking its own work tends to approve it, so a critic must be forced to
*list and cite* — "name every person in the explanation and say whether they are in the cast" —
never asked "is this good?". And a critic that only reports is cheap; one that triggers a full
regeneration costs another $0.14 every time it fires, and we do not yet know how often that would
be.

**3. Two loose ends found on the way.**

- **A finding does not know which clue it came from.** What a player receives is a paragraph of text
  with an ID of its own. It carries no link back to the evidence list. So the elimination arithmetic
  and the things players actually hold are two systems with no connection between them — and the
  planned "assignment each player a fair casefile" step cannot be built until they are joined.
- **The solo case screen prints the answer key.** It shows a ★ beside critical evidence and an ✗
  beside red herrings. The multiplayer path hides this completely. One of the two is wrong.

---

## The five words that matter

| Word | Means |
|---|---|
| **Validator** | Ordinary code checking structure. Free, certain, no opinions. This is our 26 rules |
| **Critic** | One AI call that reads a finished mystery and reports faults. ~$0.04. Does not rewrite |
| **Chain** | The solution's reasoning, as numbered steps rather than a paragraph |
| **Exonerates** | The label on a clue naming who it clears. Crossing all of them off must leave exactly one person |
| **Backwards** | Writing the solution first and the clues afterwards, so the clues serve the answer instead of the answer excusing the clues |
