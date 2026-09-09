"""
casefiles.py — APF's constrained assignment (root CLAUDE.md item 23, build-order step 2).

Findings are ASSIGNED, NOT GATHERED. This module takes a generated mystery and
casefiles each player a small set of findings, subject to constraints that make the
game winnable without making it a lottery. It is pure computation: no API call,
deterministic from a seed, and a failed assignment is simply re-run at zero cost
(docs/PLAYTEST_FLOW.md, "The assignment is a separate step from generation").

WHY A POINTER AND NOT DUPLICATED FIELDS. Only evidence[] carries elimination
data -- `exonerates` / `implicates`, added in Session 38. A witness statement
and a lead result carry none, so two of APF's three finding kinds were inert:
they could not participate in the set arithmetic all three assignment constraints
are defined over. The fix is a `reveals` pointer on witnesses, leads and areas
naming the evidence they surface. Elimination data therefore lives in exactly
ONE place and a witness's exoneration cannot drift out of agreement with the
evidence item's -- a defect no structural check could have caught, which is
why the alternative (copying all three link fields onto every kind) was
rejected. See docs/INVESTIGATION_DESIGN.md §4.

THE ARITHMETIC. A finding set eliminates the suspects exonerated by the evidence
it reveals. The set SOLVES when exactly one suspect is left standing and that
suspect is the culprit. Everything below is that one predicate applied to
different subsets: all casefiles together, each casefile alone, and each casefile's
contribution to a single exoneration.

IT IS A RACE TO PROOF, NOT A RACE TO THE BEST BET. Owner's decision, Session
39: "the core of mystery solving is solving not guessing." So a fourth
constraint asks whether somebody can still PROVE the case after every player
withholds their best finding -- enumerated over every legal hoarding pattern,
free, no API call. What makes that survivable is CARRIERS, not redundancy: two
independent routes to each exoneration puts survival at 81/81, one route puts
it at 75/81. The rule therefore lives in the generation prompt, and this
constraint is what stops a mystery that ignores it from reaching a table.

THE VOCABULARY IS INVESTIGATION, NOT CARD GAME. Owner's instruction, three
times -- and the third time was needed because the first two only fixed the
NOUN. "Finding" replaced "clue"/"card", and every verb and container around it
survived: things were dealt, into hands, by deal.py, under a DEFAULT_HAND_SPEC.
A metaphor rebuilds itself from whatever parts you leave standing.

So: findings are ASSIGNED, to a player's CASEFILE, by this module. There are no
decks, no hands, no deals and nothing is played. This is a social deduction
game about what people choose to say, and describing it in the language of a
card table makes it read as one. If a client one day draws a finding as a
rectangle, that is that client's business and its word to choose.

Where the old vocabulary came from is recorded in docs/DECISIONS.md item 34 --
it entered as a note about reusing another project's UI components, not as a
design decision, which is exactly why nobody defended it and it still spread.

WHAT THIS DOES NOT DO. It does not judge whether a clue's prose actually
supports the link it declares. A model can emit reveals: ["E3"] on a statement
that says nothing about E3, and nothing structural can tell -- the same
limitation Session 38 recorded for `supports`. The pointer changes what drift
looks like, not whether drift is possible.
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Set

# APF's casefile: one witness statement, one crime-scene clue, one lead result
# (docs/PLAYTEST_FLOW.md step 4). "Ideally" is load-bearing in that sentence --
# a mystery has 3-4 witnesses and 4 leads against 4 players, so the pools run
# dry and the assignment substitutes. See _FALLBACK_KIND.
DEFAULT_CASEFILE_SPEC = ("witness", "clue", "lead")

# Which pool a slot falls back to when its own is exhausted. evidence[] is the
# largest pool in every mystery on disk (6-10 items against 3-4 witnesses and
# 4 leads), so it is the only sensible donor.
_FALLBACK_KIND = "clue"

# How many DISTINCT casefiles each required exoneration must land in.
#
# This is the replacement for PLAYTEST_FLOW's third assignment constraint, which
# Session 38 measured as not well-formed: "becomes solvable once the minimum
# share threshold is met" cannot hold, because share_min is a fraction of a
# player's OWN findings and the player chooses which to share -- so meeting the
# threshold does not determine what reaches the pool, and a finding that MUST
# reach it is a finding nobody may keep, which deletes the hoarding decision.
#
# Redundancy is the option that survives that argument, and it does double duty:
# Session 38 also found the difficulty ladder is inert at a three-finding casefile
# (EASY/MEDIUM/HARD all resolve to "share 2, keep 1" -- a percentage has no
# resolution over three items), and named redundancy as difficulty's natural
# home. EASY puts each exoneration in two casefiles so somebody will share it; HARD
# puts it in exactly one so withholding really bites.
#
# MEDIUM AND HARD ARE THE SAME VALUE, AND THAT IS FORCED, NOT LAZY. The
# redundancy ceiling is set by constraint 2 (see feasibility()): at APF's shape
# -- 4 players, EXACTLY 4 suspects, so 3 required exonerations -- redundancy 3
# would force some casefile to hold all three and solve alone. The ceiling is 2, so
# only two rungs exist. Difficulty gets a third only from a second dial:
# suspect count or red-herring density, both named by Session 38. Moving the
# ladder here fixed EASY-vs-the-rest and did NOT fix MEDIUM-vs-HARD.
#
# OWNER'S CALL, NOT SETTLED HERE. docs/INVESTIGATION_DESIGN.md §4 lists three
# options and this implements two of them: redundancy=1 IS the "accept it"
# option (constraints 1 and 2 only, universal hoarding can end a game with no
# winner). "Pigeonhole it" is a genuinely different constraint and is NOT
# implemented -- see module docs rather than assuming it is in here.
# MEDIUM is a legacy alias, not a third setting. Owner's decision (Session 39):
# two difficulties are fine for the playtest, which is the honest answer given
# the ceiling above -- three labels where two behave identically is the exact
# defect Session 38 found in the share ladder. The 17 mysteries on disk carry
# MEDIUM, so it keeps working rather than breaking the corpus.
REDUNDANCY_BY_DIFFICULTY = {"EASY": 2, "HARD": 1, "MEDIUM": 1}

# How many findings a player may withhold. PASSED IN, NEVER COMPUTED HERE:
# _min_share_required() in server/main.py is THE definition of the share rule
# (Session 38 removed a second copy that had drifted), and casefiles.py recomputing
# it from share_min would put the duplication straight back. 1 is what that rule
# yields at APF's three-finding casefile for every difficulty.
DEFAULT_HOARD_ALLOWANCE = 1

# APF's specified cast (docs/PLAYTEST_FLOW.md, and the generation prompt's
# "EXACTLY 4 suspects"). Named here because the constraint arithmetic throughout
# this file is derived from it -- three required exonerations, a redundancy
# ceiling of 2 -- and a mystery that arrives with a different number is not a
# harder or easier version of the same game, it is a different one.
APF_SUSPECT_COUNT = 4

# Re-running the assignment is free, so the ceiling is generous. It exists to bound a mystery
# that cannot be assigned at all, and when it is hit the feasibility report -- not
# the attempt count -- is what says why.
MAX_ATTEMPTS = 400


@dataclass
class Finding:
    """One assigned finding. `reveals` is the join key to evidence[]."""
    id: str
    kind: str          # "witness" | "clue" | "lead"
    title: str
    body: str
    reveals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssignmentResult:
    casefiles: List[List[Finding]]
    ok: bool
    issues: List[str] = field(default_factory=list)
    attempts: int = 0
    seed: int = 0
    redundancy: int = 1
    # Quality of the assignment, not of the mystery -- see best_assignment().
    monopoly: int = 0            # hoarding patterns where exactly one player can prove it
    patterns: int = 0            # hoarding patterns examined
    seeds_tried: int = 1

    def to_dict(self) -> dict:
        return {
            "casefiles": [[c.to_dict() for c in h] for h in self.casefiles],
            "ok": self.ok,
            "issues": list(self.issues),
            "attempts": self.attempts,
            "seed": self.seed,
            "redundancy": self.redundancy,
            "monopoly": self.monopoly,
            "patterns": self.patterns,
            "seeds_tried": self.seeds_tried,
        }


# --------------------------------------------------------------------------
# Reading the mystery
# --------------------------------------------------------------------------

def _name(character: dict) -> str:
    return (character.get("name") or "").strip()


def suspects(mystery: dict) -> List[str]:
    return [
        _name(c) for c in mystery.get("characters", []) or []
        if (c.get("role") or "").strip().lower() == "suspect" and _name(c)
    ]


def culprit(mystery: dict) -> str:
    return ((mystery.get("solution") or {}).get("culprit") or "").strip()


def required_exonerations(mystery: dict) -> Set[str]:
    """Every suspect EXCEPT the culprit.

    Eliminating exactly these leaves one person standing, which is the schema's
    own stated contract for evidence[].exonerates.
    """
    return {s for s in suspects(mystery) if s != culprit(mystery)}


def evidence_by_id(mystery: dict) -> Dict[str, dict]:
    return {
        (e.get("id") or "").strip(): e
        for e in mystery.get("evidence", []) or []
        if (e.get("id") or "").strip()
    }


def build_pool(mystery: dict) -> List[Finding]:
    """Every finding that could be assigned, in three kinds.

    A clue finding reveals ITSELF -- an evidence item is its own join key, which
    is why assignment from evidence[] alone would need no pointer at all. The
    pointer exists for the other two kinds.

    INVESTIGATION AREAS ARE DELIBERATELY NOT ASSIGNED. APF has no traversal, so
    "you searched the library" is a sentence about a move nobody makes. They
    still carry `reveals` in the schema because the map is deferred, not
    cancelled (CLAUDE.md item 23), and a second schema change would cost a
    second paid generation round.
    """
    pool: List[Finding] = []

    for c in mystery.get("characters", []) or []:
        if (c.get("role") or "").strip().lower() != "witness":
            continue
        statement = (c.get("statement") or "").strip()
        if not statement:
            continue
        pool.append(Finding(
            id=f"W:{_name(c)}",
            kind="witness",
            title=_name(c),
            body=statement,
            reveals=[str(r).strip() for r in (c.get("reveals") or []) if str(r).strip()],
        ))

    for e in mystery.get("evidence", []) or []:
        eid = (e.get("id") or "").strip()
        if not eid:
            continue
        pool.append(Finding(
            id=f"E:{eid}",
            kind="clue",
            title=(e.get("name") or eid).strip(),
            body=(e.get("description") or "").strip(),
            reveals=[eid],
        ))

    for l in mystery.get("leads", []) or []:
        lid = (l.get("id") or "").strip()
        if not lid:
            continue
        pool.append(Finding(
            id=f"L:{lid}",
            kind="lead",
            title=(l.get("title") or lid).strip(),
            body=(l.get("brief") or "").strip(),
            reveals=[str(r).strip() for r in (l.get("reveals") or []) if str(r).strip()],
        ))

    return pool


# --------------------------------------------------------------------------
# The arithmetic
# --------------------------------------------------------------------------

def exonerated_by(findings: Sequence[Finding], ev_by_id: Dict[str, dict]) -> Set[str]:
    """Which suspects this finding set clears, read through the reveals pointer."""
    cleared: Set[str] = set()
    for finding in findings:
        for eid in finding.reveals:
            item = ev_by_id.get(eid)
            if not item:
                continue  # dangling; reported by feasibility(), not silently fatal here
            cleared.update(str(n).strip() for n in (item.get("exonerates") or []) if str(n).strip())
    return cleared


def narrowed_by(findings: Sequence[Finding], mystery: dict,
                ev_by_id: Dict[str, dict]) -> Set[str]:
    """Who is still possible after every NARROWING finding in this set (item 27).

    THE GLOVE. A finding whose evidence carries a non-empty `narrows` says "only
    these could have done it" -- the owner's bloody men's glove, which clears
    nobody on its own and rules out the women. Several such findings INTERSECT:
    a glove narrowing to the men and a boot-print narrowing to the tall people
    leave whoever is both.

    WHY A NEW FIELD RATHER THAN REUSING `implicates`. The two mean different
    things and overloading one broke 22 tests before this comment existed.
    `implicates` is SUSPICION -- "this points at Brandt" -- and the prompt
    requires the culprit be implicated by something so the answer does not read
    as arbitrary, which makes single-name lists normal and correct. Read as a
    narrowing constraint, a single-name list says "only Brandt could have done
    it", i.e. one finding that is the whole answer: whoever is assigned it wins
    alone without anyone sharing anything, which is the exact failure the
    lighthouse mystery was rejected for. `narrows` is a CONSTRAINT over a set and must name
    at least two people; `implicates` keeps its old meaning untouched.

    Findings that implicate nobody narrow nothing and are skipped, so a set with
    no narrowing findings returns the full suspect list and this function has no
    effect -- which is what keeps every pre-item-27 mystery behaving exactly as
    it did.

    NOT A LABEL THE PLAYER EVER SEES. `implicates` is hidden bookkeeping so the
    engine can guarantee the case is solvable; the prose says "man's size large"
    and the player looks at the cast and draws the line. The precedent is
    `investigation_prompt`, already private context. Item 27 is explicit that
    this must never surface as "the culprit is one of these two".
    """
    possible = set(suspects(mystery))
    for finding in findings:
        for eid in finding.reveals:
            item = ev_by_id.get(eid)
            if not item:
                continue
            named = {str(n).strip() for n in (item.get("narrows") or []) if str(n).strip()}
            if named:
                possible &= named
    return possible


def solves(findings: Sequence[Finding], mystery: dict,
           ev_by_id: Optional[Dict[str, dict]] = None) -> bool:
    """True when this finding set leaves exactly the culprit standing.

    Two routes, and a set may use either or both:

      SUBTRACTION   clear everybody else -- the original mechanic (`exonerates`).
      NARROWING     rule out everybody a narrowing finding excludes (`narrows`).

    They compose, which is the whole point of the glove: narrowing to two and
    then clearing one of those two reaches the answer in TWO findings where
    subtraction alone needs one per innocent. Two findings that individually
    prove nothing combine into a proof.

    ELIMINATION REMAINS THE GUARANTEED FLOOR AND NARROWING IS A FASTER ROUTE
    ON TOP -- a deliberate choice, not an accident of implementation. If
    narrowing were load-bearing, withholding the one glove could make a case
    unprovable, which is exactly what the owner's "it has to be a race to
    proof" rules out. Keeping subtraction sufficient on its own means the
    glove rewards insight with SPEED, and speed is what a race should reward.

    Note it is not enough to leave one name: the ONE left standing must be the
    culprit. A set that exonerates the culprit and leaves an innocent standing
    has the right cardinality and the wrong answer.
    """
    ev_by_id = evidence_by_id(mystery) if ev_by_id is None else ev_by_id
    standing = narrowed_by(findings, mystery, ev_by_id) - exonerated_by(findings, ev_by_id)
    return standing == {culprit(mystery)}


# --------------------------------------------------------------------------
# Feasibility — why an assignment cannot be made, before trying 400 times
# --------------------------------------------------------------------------

# Every reason feasibility() can refuse a mystery, and what kind of broken each
# one is. Added Session 41 so gate.py and the ledger can count rules rather than
# match prose. Classes are the same four used everywhere: incoherent, unplayable,
# spoiled_prose, below_standard (see check_narrative.RULES).
#
# SEVERAL IDS ARE DELIBERATELY SHARED WITH check_narrative.RULES. The two files
# independently implement the same fair-play rules -- narrowing to one suspect,
# narrowing to everybody, a narrowing that excludes the culprit, load-bearing
# narrowing, an exonerated culprit. That duplication is real and predates this
# change; naming them identically means the gate deduplicates them instead of
# counting one defect twice.
FEASIBILITY_RULES = {
    "CASE.NO_SUSPECTS":              "incoherent",
    "CASE.SUSPECT_COUNT":            "unplayable",
    "CASE.NO_CULPRIT":               "incoherent",
    "CASE.CULPRIT_NOT_SUSPECT":      "incoherent",
    "REVEAL.DANGLING":               "incoherent",
    "CASE.EXONERATES_STRANGER":      "below_standard",
    "NARR.CULPRIT_EXONERATED":       "unplayable",
    "NARR.NARROWS_SINGLE":           "spoiled_prose",
    "NARR.NARROWS_ALL":              "below_standard",
    "NARR.NARROWS_STRANGER":         "below_standard",
    "NARR.NARROWS_EXCLUDES_CULPRIT": "unplayable",
    "NARR.NARROWING_LOAD_BEARING":   "unplayable",
    "CASE.POOL_UNSOLVABLE":          "unplayable",
    "CASE.REDUNDANCY_CEILING":       "unplayable",
    "CASE.REDUNDANCY_UNREACHABLE":   "unplayable",
    "CASE.SOLO_SOLVE":               "unplayable",
    "CASE.POOL_TOO_SMALL":           "unplayable",
}


def _add(issues: List[dict], rule_id: str, message: str, subjects=()) -> None:
    """Record one refusal. `subjects` names the evidence item, finding or person
    the rule fired on -- it is what lets gate.py deduplicate this against the
    same rule reported by check_narrative.py, and what a later pass would need
    in order to know WHAT to repair rather than only that something is wrong."""
    issues.append({
        "rule_id": rule_id,
        "failure_class": FEASIBILITY_RULES.get(rule_id, "unplayable"),
        "subject_ids": [str(x) for x in subjects],
        "message": message,
    })


def feasibility(mystery: dict, player_count: int,
                redundancy: int = 1,
                casefile_spec: Sequence[str] = DEFAULT_CASEFILE_SPEC) -> List[str]:
    """The reasons, as prose. Unchanged public behaviour — every existing caller
    and scripts/test_casefiles.py read this list of strings."""
    return [i["message"] for i in
            feasibility_issues(mystery, player_count, redundancy, casefile_spec)]


def feasibility_issues(mystery: dict, player_count: int,
                       redundancy: int = 1,
                       casefile_spec: Sequence[str] = DEFAULT_CASEFILE_SPEC) -> List[dict]:
    """Cheap structural reasons this mystery can never be assigned.

    WHY THIS EXISTS. Without it, an unassignable mystery looks exactly like an
    unlucky one: 400 failed attempts and no explanation. Every check below
    turns "the assignment failed" into a sentence naming the mystery's defect, which
    is the difference between re-running the assignment and regenerating.
    """
    issues: List[dict] = []
    ev_by_id = evidence_by_id(mystery)
    pool = build_pool(mystery)
    sus = suspects(mystery)
    cul = culprit(mystery)
    required = required_exonerations(mystery)

    if not sus:
        _add(issues, "CASE.NO_SUSPECTS", "no suspects: characters[] has nobody with role 'suspect'")
    elif len(sus) != APF_SUSPECT_COUNT:
        # APF'S ARITHMETIC IS SIZED FOR FOUR, and asserting it in the prompt was
        # not enough -- `snow_on_the_engawa` came back with three and nothing
        # caught it. THREE IS NOT MERELY SMALLER, IT IS A DIFFERENT GAME: two
        # required exonerations instead of three means any single finding
        # carrying both clears everybody and solves outright, so the assignment cannot
        # be fair no matter how well the mystery is written. The redundancy
        # ceiling reasoning below assumes 4 as well.
        _add(issues, "CASE.SUSPECT_COUNT",
             f"{len(sus)} suspects, not {APF_SUSPECT_COUNT}: at {len(sus)} there are only "
             f"{max(0, len(sus) - 1)} required exoneration(s), so one finding carrying them all "
             f"solves the case and no assignment can be fair",
             sorted(sus))
    if not cul:
        _add(issues, "CASE.NO_CULPRIT", "no culprit: solution.culprit is empty")
    elif cul not in sus:
        _add(issues, "CASE.CULPRIT_NOT_SUSPECT", f"culprit {cul!r} is not among the suspects {sorted(sus)}", [cul])

    # Dangling pointers. A reveals id naming no evidence item is silently
    # inert in exonerated_by(), so it must be loud here.
    for finding in pool:
        for eid in finding.reveals:
            if eid not in ev_by_id:
                _add(issues, "REVEAL.DANGLING", f"finding {finding.id} reveals {eid!r}, which is not in evidence[]", [finding.id, eid])

    # An exonerates name matching no suspect eliminates nobody. Reported rather
    # than normalised away: "Dr. Tanaka" against a suspect named "Tanaka" is a
    # real generation defect, and quietly fuzzy-matching it would hide it.
    known = set(sus)
    for eid, item in ev_by_id.items():
        for n in (item.get("exonerates") or []):
            if str(n).strip() and str(n).strip() not in known:
                _add(issues, "CASE.EXONERATES_STRANGER", f"evidence {eid} exonerates {str(n).strip()!r}, who is not a suspect", [eid])
    if cul and cul in exonerated_by(pool, ev_by_id):
        _add(issues, "NARR.CULPRIT_EXONERATED", f"the culprit {cul!r} is exonerated by the evidence; nobody can be accused", [cul])

    # FAIR PLAY, item 27. A narrowing clue is a strong claim and generation has
    # to mean it. "A bloody man's glove" invites the player to rule out the
    # women; if the culprit is a woman who wore her husband's glove, the player
    # who reasoned exactly as the game taught them LOSES. That is the worst
    # outcome a mystery can produce, and it is the one thing the corpus already
    # forbids -- RESEARCH_FINDINGS.md M3 Clue Fairness, P.D. James and Knox 8.
    #
    # Structurally it is simple: the culprit must survive every narrowing, so
    # the culprit must appear in EVERY `narrows` list. A list that excludes them
    # is the mystery contradicting its own solution.
    for eid, item in ev_by_id.items():
        named = [str(n).strip() for n in (item.get("narrows") or []) if str(n).strip()]
        if not named:
            continue
        # COUNTED OVER SUSPECTS, NOT LIST ENTRIES (Session 41). E9 of
        # `the_last_night_of_delacroix_&_sons` narrowed to [the culprit, THE
        # VICTIM]: two entries, one living possibility. A dead man does not
        # widen a narrowing, and the finding solved the case outright.
        live = [n for n in named if n in known]
        if len(live) < 2:
            _add(issues, "NARR.NARROWS_SINGLE",
                f"evidence {eid} narrows to {named}, which is {len(live)} actual suspect(s) -- "
                f"that is the whole answer in one finding, and whoever is assigned it wins "
                f"without sharing", [eid])
        # A narrowing naming EVERY suspect rules nobody out. The first real
        # generation to write a narrowing clue produced exactly this -- a rifle
        # casing "consistent with" all four suspects -- and it passed, because
        # the only rule was "at least two names". The clue reads like evidence
        # and does nothing, which is worse than no clue: a player who works out
        # what it implies has been sent down a corridor with no door.
        elif len(live) >= len(sus) and sus:
            _add(issues, "NARR.NARROWS_ALL", 
                f"evidence {eid} narrows to all {len(named)} suspects, so it rules nobody out; "
                f"a narrowing must exclude at least one person to be worth reading", [eid])
        unknown = [n for n in named if n not in known]
        if unknown:
            _add(issues, "NARR.NARROWS_STRANGER", f"evidence {eid} narrows to {unknown}, who are not suspects", [eid])
        if cul and cul not in named:
            _add(issues, "NARR.NARROWS_EXCLUDES_CULPRIT", 
                f"evidence {eid} narrows to {named}, which excludes the culprit {cul!r} -- "
                f"the mystery contradicts its own solution and punishes correct reasoning", [eid])

    # ELIMINATION MUST STAY SUFFICIENT ON ITS OWN. Narrowing is a faster route,
    # never the only one (see solves()). If the case can only be cracked with a
    # glove, withholding that one glove makes it unprovable -- which is what the
    # owner's "it has to be a race to proof" rules out. Checked by asking
    # whether subtraction alone still reaches the culprit.
    if sus and cul:
        standing_by_subtraction = set(sus) - exonerated_by(pool, ev_by_id)
        if standing_by_subtraction != {cul}:
            _add(issues, "NARR.NARROWING_LOAD_BEARING", 
                "elimination alone does not reach the culprit -- narrowing has become "
                f"load-bearing, so withholding one narrowing finding could make the case "
                f"unprovable. Standing after exonerations: {sorted(standing_by_subtraction)}")

    # Constraint 1 must be reachable at all: if the WHOLE pool cannot solve,
    # no subset of it can.
    if sus and cul and not solves(pool, mystery, ev_by_id):
        standing = sorted(set(sus) - exonerated_by(pool, ev_by_id))
        _add(issues, "CASE.POOL_UNSOLVABLE", 
            "the full finding pool does not solve the mystery -- "
            f"suspects left standing: {standing or ['(none)']}, expected exactly [{cul!r}]"
        )

    # Constraints 2 and 3 pull AGAINST each other, and the ceiling is where
    # they meet. Each of the R required exonerations sits in >= k casefiles, so
    # there are >= R*k (exoneration, casefile) incidences over P casefiles, and by
    # pigeonhole some casefile holds >= ceil(R*k/P) of them. When that reaches R,
    # that casefile holds EVERY exoneration -- and a casefile holding every exoneration
    # solves alone, which is constraint 2. So the assignment is not unlucky at that
    # point, it is impossible, and burning 400 attempts to discover it would
    # report "no valid assignment" for something arithmetic settles up front.
    #
    # THIS IS WHY THERE IS NO THREE-RUNG REDUNDANCY LADDER. At APF's specified
    # shape -- 4 players, EXACTLY 4 suspects, so R = 3 -- the ceiling is 2.
    # EASY takes it; MEDIUM and HARD both sit at 1. Difficulty needs a second
    # dial (suspect count or red-herring density, per Session 38) to get a
    # third rung; redundancy alone cannot provide one.
    if required and player_count and redundancy > 1:
        worst_casefile = math.ceil(len(required) * redundancy / player_count)
        if worst_casefile >= len(required):
            _add(issues, "CASE.REDUNDANCY_CEILING", 
                f"redundancy {redundancy} is impossible at {player_count} players with "
                f"{len(required)} required exoneration(s): some casefile must then hold all "
                f"{len(required)} and would solve alone (constraint 2). "
                f"Ceiling here is {max(1, (player_count * (len(required) - 1)) // len(required))}."
            )

    # Constraint 3 must be reachable: an exoneration carried by fewer distinct
    # findings than the redundancy level can never reach that many casefiles.
    if redundancy > 1:
        for r in sorted(required):
            carriers = [c for c in pool if r in exonerated_by([c], ev_by_id)]
            if len(carriers) < redundancy:
                _add(issues, "CASE.REDUNDANCY_UNREACHABLE", 
                    f"exoneration of {r!r} is carried by {len(carriers)} finding(s) "
                    f"but redundancy {redundancy} needs {redundancy} distinct casefiles"
                , [r])

    # Constraint 2 must be reachable: if one finding solves outright, whoever gets
    # it wins alone and the assignment is a lottery by construction.
    for finding in pool:
        if sus and cul and solves([finding], mystery, ev_by_id):
            _add(issues, "CASE.SOLO_SOLVE", f"finding {finding.id} solves the mystery by itself; no assignment can be fair", [finding.id])

    casefile_size = len(casefile_spec)
    if len(pool) < player_count * casefile_size:
        _add(issues, "CASE.POOL_TOO_SMALL", 
            f"pool has {len(pool)} findings, short of {player_count} players x {casefile_size} = "
            f"{player_count * casefile_size}"
        )

    return issues


# --------------------------------------------------------------------------
# The assignment
# --------------------------------------------------------------------------

def _violations(casefiles: List[List[Finding]], mystery: dict,
                ev_by_id: Dict[str, dict], redundancy: int,
                require_proof_under_hoarding: bool = True,
                hoard_allowance: int = DEFAULT_HOARD_ALLOWANCE,
                forbid_prover_monopoly: bool = False) -> List[str]:
    """The constraints, checked against one candidate assignment."""
    out: List[str] = []
    all_findings = [f for h in casefiles for f in h]

    # 1. the union of all assigned findings eliminates all but one suspect
    if not solves(all_findings, mystery, ev_by_id):
        standing = sorted(set(suspects(mystery)) - exonerated_by(all_findings, ev_by_id))
        out.append(f"union does not solve; standing: {standing or ['(none)']}")

    # 2. no single player's casefile does that alone
    for i, casefile in enumerate(casefiles):
        if solves(casefile, mystery, ev_by_id):
            out.append(f"casefile {i} solves alone")

    # 3. each required exoneration reaches at least `redundancy` distinct casefiles
    if redundancy > 1:
        for r in sorted(required_exonerations(mystery)):
            holders = sum(1 for h in casefiles if r in exonerated_by(h, ev_by_id))
            if holders < redundancy:
                out.append(f"exoneration of {r!r} reaches {holders} casefile(s), needs {redundancy}")

    # SHORT-CIRCUIT. Constraints 4 and 5 each enumerate every hoarding pattern
    # -- 81 at APF's shape, each running solves() once per player -- so they are
    # roughly three orders of magnitude more expensive than the three above. A
    # assignment that already fails a cheap constraint is going to be rejected either
    # way, so spending that on it is pure waste: with a 400-attempt ceiling it
    # was ~130,000 needless set operations per refused assignment.
    if out:
        return out

    # 4. proof survives hoarding -- the owner's "race to proof", enumerated
    if require_proof_under_hoarding:
        ok, total, _ = proof_survives_hoarding(casefiles, mystery, ev_by_id, hoard_allowance)
        if ok < total:
            out.append(
                f"proof dies under hoarding in {total - ok} of {total} patterns; "
                f"solving must not depend on nobody withholding")

    # 5. a race needs at least two runners -- no single player may hold a
    #    monopoly on reaching proof. OFF BY DEFAULT: it is a stricter reading of
    #    the owner's "race to proof" than the words strictly require, it costs
    #    assigns, and it is theirs to turn on.
    if forbid_prover_monopoly:
        counts = prover_counts(casefiles, mystery, ev_by_id, hoard_allowance)
        mono = counts.get(1, 0)
        if mono:
            total = sum(counts.values())
            out.append(
                f"one player has a monopoly on proof in {mono} of {total} patterns; "
                f"a race needs at least two who can get there")

    return out


def proof_survives_hoarding(casefiles: List[List[Finding]], mystery: dict,
                           ev_by_id: Optional[Dict[str, dict]] = None,
                           hoard_allowance: int = DEFAULT_HOARD_ALLOWANCE) -> tuple:
    """Can somebody still PROVE it after every player withholds their best finding?

    OWNER'S DECISION, SESSION 39, AND THIS IS ITS MECHANICAL FORM: "the core of
    mystery solving is solving not guessing -- thus it has to be a race to
    proof." That is a claim about what must remain true after players hoard, so
    it is checked by enumeration rather than argued about.

    A player knows everything shared PLUS their own casefile -- you always know what
    you kept -- so proof is reachable when ANY player's shared-pool-plus-own-casefile
    solves. At APF's shape that is 4 players x 3 choices = 81 patterns, the same
    81 docs/PLAYTEST_FLOW.md already cites for the pick-list, and set operations
    at zero API cost.

    Returns (reachable_count, total_patterns, sample_failing_patterns).

    MEASURED (Session 39): what makes this survive is NOT redundancy but
    CARRIERS -- how many separate findings in the mystery can clear a given
    suspect. At one carrier per suspect proof dies in 6 of 81 patterns; at two
    it survives all 81, at redundancy 1 and 2 alike. That is why the fix landed
    in the generation prompt as "two independent routes" rather than as an assignment
    setting.
    """
    ev_by_id = evidence_by_id(mystery) if ev_by_id is None else ev_by_id
    # Each player independently chooses which `hoard_allowance` findings to keep.
    per_player = [list(itertools.combinations(range(len(h)), hoard_allowance))
                  for h in casefiles]
    reachable = 0
    failing: List[tuple] = []
    patterns = list(itertools.product(*per_player))
    for pattern in patterns:
        shared = [f for i, casefile in enumerate(casefiles)
                  for j, f in enumerate(casefile) if j not in pattern[i]]
        provers = sum(1 for i in range(len(casefiles))
                      if solves(shared + list(casefiles[i]), mystery, ev_by_id))
        if provers:
            reachable += 1
        elif len(failing) < 3:
            failing.append(pattern)
    return reachable, len(patterns), failing


def prover_counts(casefiles: List[List[Finding]], mystery: dict,
                  ev_by_id: Optional[Dict[str, dict]] = None,
                  hoard_allowance: int = DEFAULT_HOARD_ALLOWANCE) -> Dict[int, int]:
    """{how many players could prove it: in how many hoarding patterns}.

    WHY THIS IS SEPARATE FROM proof_survives_hoarding. Proof EXISTING and the
    game being FAIR are different properties, and the second real generation
    showed the gap: on a mystery where two suspects had only one route each,
    proof was reachable in 81 of 81 patterns and in 54 of them exactly ONE
    player could reach it -- always the same player, the one holding the
    single-route finding, because a hoarder still knows what they kept. That
    passes "race to proof" and is not a race. Two routes cuts the monopoly to
    27 of 81, and a monopoly-free assignment exists at other seeds, so it is a
    property the assignment can search for rather than one the writing must
    guarantee.
    """
    ev_by_id = evidence_by_id(mystery) if ev_by_id is None else ev_by_id
    per_player = [list(itertools.combinations(range(len(h)), hoard_allowance))
                  for h in casefiles]
    counts: Dict[int, int] = {}
    for pattern in itertools.product(*per_player):
        shared = [f for i, casefile in enumerate(casefiles)
                  for j, f in enumerate(casefile) if j not in pattern[i]]
        n = sum(1 for i in range(len(casefiles))
                if solves(shared + list(casefiles[i]), mystery, ev_by_id))
        counts[n] = counts.get(n, 0) + 1
    return counts


def assign(mystery: dict, player_count: int, seed: int = 0,
         redundancy: Optional[int] = None,
         casefile_spec: Sequence[str] = DEFAULT_CASEFILE_SPEC,
         max_attempts: int = MAX_ATTEMPTS,
         require_proof_under_hoarding: bool = True,
         hoard_allowance: int = DEFAULT_HOARD_ALLOWANCE,
         forbid_prover_monopoly: bool = False) -> AssignmentResult:
    """Assignment `player_count` casefiles under the three constraints.

    Deterministic in `seed`: the same (mystery, players, seed) always gives the
    same casefiles, so a reconnecting player gets back the casefile they left rather
    than a reshuffled one -- the same property background_field.py needs for
    the same reason.

    Returns an AssignmentResult rather than raising. An assignment that cannot be made is
    diagnostic data about the MYSTERY -- the caller decides between re-running the assignment
    with a new seed and regenerating -- and an exception would throw that away.
    """
    if redundancy is None:
        difficulty = ((mystery.get("gameplay_notes") or {}).get("difficulty") or "MEDIUM").strip().upper()
        redundancy = REDUNDANCY_BY_DIFFICULTY.get(difficulty, 1)

    ev_by_id = evidence_by_id(mystery)
    pool = build_pool(mystery)

    blocking = feasibility(mystery, player_count, redundancy, casefile_spec)
    if blocking:
        return AssignmentResult(casefiles=[], ok=False, issues=blocking, attempts=0,
                          seed=seed, redundancy=redundancy)

    rng = random.Random(seed)
    last: List[str] = []

    casefile_size = len(casefile_spec)
    required = sorted(required_exonerations(mystery))

    for attempt in range(1, max_attempts + 1):
        by_kind: Dict[str, List[Finding]] = {}
        for finding in pool:
            by_kind.setdefault(finding.kind, []).append(finding)
        for bucket in by_kind.values():
            rng.shuffle(bucket)

        casefiles: List[List[Finding]] = [[] for _ in range(player_count)]
        used: Set[str] = set()
        # Kinds each casefile still wants, so the seeding pass below can consume a
        # slot and the fill pass knows what is left.
        wanted: List[List[str]] = [list(casefile_spec) for _ in range(player_count)]

        # SEEDING PASS -- place the findings that DECIDE the case first.
        #
        # WHY THIS EXISTS. The first version assigned purely by kind and let the
        # constraints reject bad assigns. That works while the pool is small, and
        # stops working the moment it is not: the second real generation
        # returned 21 findings of which only 4 carried any exoneration, so a
        # 12-of-21 assignment chosen by KIND had to catch all three eliminations by
        # luck, and 400 attempts did not. Raising the evidence floor to 9 made
        # the pool bigger and the luck worse. Constraint 1 is a COVERING
        # requirement, and a covering requirement should be constructed, not
        # sampled for.
        short = False
        for r in required:
            carriers = [f for f in pool
                        if f.id not in used and r in exonerated_by([f], ev_by_id)]
            rng.shuffle(carriers)
            # Spread across distinct casefiles, which is also what redundancy wants;
            # prefer casefiles with room, in a rotated order so casefile 0 is not always
            # the one that gets the decisive finding.
            order = list(range(player_count))
            rng.shuffle(order)
            placed = 0
            for casefile_idx in order:
                if placed >= max(1, redundancy) or not carriers:
                    break
                if len(casefiles[casefile_idx]) >= casefile_size:
                    continue
                finding = carriers.pop()
                casefiles[casefile_idx].append(finding)
                used.add(finding.id)
                if finding.kind in wanted[casefile_idx]:
                    wanted[casefile_idx].remove(finding.kind)
                elif wanted[casefile_idx]:
                    wanted[casefile_idx].pop()
                placed += 1

        # FILL PASS -- slot-major over what each casefile still wants.
        # Slot-major, not player-major. MEASURED, NOT ASSUMED: with one slot per
        # kind and a single shared fallback pool, the two orders produce the
        # SAME distribution -- an earlier version of this comment claimed
        # player-major would "give player 0 the full spec and player 3 three
        # fallbacks", and a negative test proved that false. It is kept because
        # it stays correct if casefile_spec ever takes two slots of one kind, where
        # player-major would let an early casefile take both copies of a scarce kind
        # before any later casefile takes one.
        for _ in range(casefile_size):
            for casefile_idx, casefile in enumerate(casefiles):
                if len(casefile) >= casefile_size:
                    continue
                slot = wanted[casefile_idx].pop(0) if wanted[casefile_idx] else _FALLBACK_KIND
                src = [f for f in by_kind.get(slot, []) if f.id not in used]
                if not src:
                    src = [f for f in by_kind.get(_FALLBACK_KIND, []) if f.id not in used]
                if not src:
                    src = [f for f in pool if f.id not in used]
                if not src:
                    short = True
                    break
                finding = src[0]
                casefile.append(finding)
                used.add(finding.id)
            if short:
                break
        if short or any(len(h) < casefile_size for h in casefiles):
            last = ["ran out of findings while assignment"]
            continue

        last = _violations(casefiles, mystery, ev_by_id, redundancy,
                           require_proof_under_hoarding, hoard_allowance,
                           forbid_prover_monopoly)
        if not last:
            return AssignmentResult(casefiles=casefiles, ok=True, issues=[], attempts=attempt,
                              seed=seed, redundancy=redundancy)

    return AssignmentResult(
        casefiles=[], ok=False,
        issues=[f"no valid assignment in {max_attempts} attempts; last: " + "; ".join(last)],
        attempts=max_attempts, seed=seed, redundancy=redundancy,
    )


# --------------------------------------------------------------------------
# Choosing an assignment, not just finding a legal one
# --------------------------------------------------------------------------

DEFAULT_SEED_SEARCH = 20


def best_assignment(mystery: dict, player_count: int,
              seeds: int = DEFAULT_SEED_SEARCH,
              **kwargs) -> AssignmentResult:
    """Assignment several times and keep the fairest assignment. Free — pure computation.

    WHY THIS IS NOT assign() WITH A BETTER DEFAULT. `assign()` stops at the first
    assignment that is LEGAL. It never asks whether it is GOOD, and those are
    different questions with different answers: on the first accepted mystery,
    `the_neriin_in_the_pilchard_barrel`, seed 7 left exactly one player able to
    prove the case in 27 of 81 hoarding patterns -- the very figure `totality`
    was rejected for -- while 13 of 20 seeds gave ZERO, and proof survived 81/81
    on every seed tried. Same mystery, same rules, same constraints satisfied.
    The difference was entirely which findings landed in which casefiles.

    So monopoly on proof is a property of the ASSIGNMENT, not of the story, and it
    is worth choosing rather than accepting. Re-running the assignment costs nothing (this
    module's whole premise), which makes taking the first legal distribution a
    strange thing to have been doing.

    SELECTION, NOT PROHIBITION, and that distinction is the design. assign() takes
    `forbid_prover_monopoly` and makes it a hard constraint -- which means a
    mystery where NO assignment avoids a monopoly returns no casefiles at all, and a
    table gets nothing. Selecting instead always returns an assignment, the least
    bad one available, and reports how good it managed to be. Degrading is
    better than refusing when the alternative is an empty table.

    DETERMINISM SURVIVES. assign() promises the same (mystery, players, seed)
    always gives the same casefiles, because a reconnecting player must get their
    own casefile back. That still holds: this searches seeds and returns the
    winner with `seed` set to it, so the chosen assignment is reproducible by
    calling assign() with that seed directly.

    Stops early on a perfect assignment, so the common case costs one or two
    assigns rather than `seeds` of them.
    """
    ev_by_id = evidence_by_id(mystery)
    best: Optional[AssignmentResult] = None

    for n, seed in enumerate(range(seeds), start=1):
        result = assign(mystery, player_count, seed=seed, **kwargs)
        if not result.ok:
            # A feasibility refusal is about the mystery and will repeat for
            # every seed, so there is nothing to search. An unlucky assignment might
            # not repeat, so keep going.
            if result.attempts == 0:
                result.seeds_tried = n
                return result
            best = best or result
            continue

        # FORWARD THE ALLOWANCE. This used to call prover_counts() with its
        # default of 1 while assign() was constraining at whatever the caller
        # passed -- so a session with a two-finding stash checked
        # proof-survives-hoarding at two and then chose its seed by a monopoly
        # measured at one. Two different hoarding models, one of which the rules
        # do not permit. apf.py derives the allowance from the difficulty ladder
        # (see apf.stash_allowance), which is what made the mismatch reachable.
        counts = prover_counts(result.casefiles, mystery, ev_by_id,
                               kwargs.get("hoard_allowance", DEFAULT_HOARD_ALLOWANCE))
        result.monopoly = counts.get(1, 0)
        result.patterns = sum(counts.values())
        result.seeds_tried = n

        if best is None or not best.ok or result.monopoly < best.monopoly:
            best = result
        if best.monopoly == 0:
            break

    if best is not None:
        best.seeds_tried = n
    return best if best is not None else AssignmentResult(casefiles=[], ok=False,
                                                    issues=["no seeds tried"])
