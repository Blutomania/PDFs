"""
apf.py -- APF's rhythm: findings dealt over rounds, shared at a checkpoint.

THIS MODULE OWNS THE CADENCE, NOT THE DEAL. `deal.py` decides WHICH findings
land in whose hand and proves the result winnable; this decides WHEN each of
them is turned face up, how much a player must have put on the table by then,
and what the room can see as a result. Both are pure computation -- no API
call, deterministic from a seed, re-runnable free.

WHY A RHYTHM AT ALL (docs/PLAYTEST_FLOW.md, "The rhythm"; owner, Session 41).
Dealt once, every player makes exactly one share decision all game, and one
decision yields one read of a person. A rhythm yields a PATTERN, and a pattern
is what lets somebody say "she's held back twice now" -- which is an accusation
forming. A single round cannot produce that sentence, and producing it is the
entire point of the product.

THREE RULES THAT LOOK LIKE DETAILS AND ARE NOT:

1. ROUND 1 HAS NO CHECKPOINT, AND THE REASON IS ARITHMETIC. The share minimum
   has a floor of 1, so a player holding one finding must share it whatever the
   difficulty. That is a tax, not a decision. The first checkpoint therefore
   falls at round 2, where holding two means choosing WHICH.

2. A SHARED FINDING STAYS IN ITS HOLDER'S HAND. Owner: "in the metaphor of the
   player being an investigator it fails if the investigator is forced to
   'forget' something." So what a player spends is EXCLUSIVITY, not possession
   -- a detective's advantage was never holding the file, it was being the only
   one who had read it. `share()` below adds to a set and removes nothing, and
   sharing is monotone: there is no un-share, because the room cannot unlearn.

3. THE REQUIREMENT IS CUMULATIVE -- shared >= required(total held), not
   shared-this-round >= required(dealt-this-round). Without that, round 4 would
   demand three new findings when only one was dealt.

AND THAT REVIVES THE DIFFICULTY LADDER. Session 38 measured EASY/MEDIUM/HARD
all resolving to "share 2, keep 1" at a fixed three-finding hand -- a percentage
has no resolution over three items. Under a rhythm the ladder separates on its
own, with no second dial: what differs between difficulties is how much a player
is permitted to sit on, and that gap widens every round.

THE SHARE RULE IS INJECTED, NEVER COMPUTED HERE. `_min_share_required()` in
server/main.py is THE definition (Session 38 deleted a second copy that had
drifted to ceil() and was silently refusing legal moves). This module takes a
callable and precomputes the answer for every round at session open -- which is
also what lets the game ANNOUNCE the ladder up front, as the owner asked:
"the game TELLS the users."

WHAT THE BOARD SHOWS, AND THE ONE THING IT MUST NOT. A shared finding greys a
suspect out for everyone, permanently, with the sharer's name on it -- that is
the central UI moment, and `exonerates` is the field that drives it. Narrowing
(item 27, the glove) is DELIBERATELY ABSENT from the board even though
`deal.solves()` counts it: item 27 is explicit that a narrowing must never
surface as "the culprit is one of these two". The clue says "man's size large",
the player looks at the cast and draws the line themselves. Greying a face on a
narrowing would do that reasoning for them and delete the mechanic.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Sequence

import deal as _deal

# The first round at which a share checkpoint runs. See rule 1 above: at a hand
# of one the minimum's floor forces the share, so round 1 has nothing to decide.
FIRST_CHECKPOINT_ROUND = 2

# A session needs at least this many rounds to be worth opening: two, because
# that is where the first real decision lives. docs/PLAYTEST_FLOW.md computes
# the same floor from two directions (solvability measured at 2, "a decision
# exists" at 2) and today's pool ceiling at 4 players is 4.
MIN_ROUNDS = FIRST_CHECKPOINT_ROUND


def round_count(pool_size: int, player_count: int) -> int:
    """Rounds = findings / players, floored. No finding is dealt twice, so the
    pool sets the ceiling directly and there is nothing to tune.

    FEWER PLAYERS MEANS A LONGER INVESTIGATION. That falls out of the division
    rather than being designed, and it is worth keeping.
    """
    if player_count <= 0:
        return 0
    return pool_size // player_count


def hand_spec_for(rounds: int) -> tuple:
    """A hand spec whose LENGTH is the round count.

    `deal.py` already expresses a hand as one slot per kind, and under the
    rhythm that hand is dealt one slot per round -- so the round count needs no
    new constraint code, only a spec of the right length. Extra slots take
    `deal._FALLBACK_KIND` (evidence), which is the largest pool in every mystery
    on disk and already the donor when a kind runs dry.
    """
    spec = list(_deal.DEFAULT_HAND_SPEC[:max(0, rounds)])
    while len(spec) < rounds:
        spec.append(_deal._FALLBACK_KIND)
    return tuple(spec)


def share_ladder(rounds: int, share_rule: Callable[[int], int]) -> List[int]:
    """How many findings must be on the table after each round, 1-indexed by
    position: `ladder[r - 1]` is the requirement at the end of round r.

    Computed once, at session open, from the injected rule -- so the whole
    ladder can be shown before play starts, and no round has to ask the server
    what it will want later.
    """
    return [max(0, int(share_rule(r))) for r in range(1, rounds + 1)]


def stash_allowance(rounds: int, ladder: Sequence[int]) -> int:
    """The largest number of findings a player may still be sitting on at the
    end of the last round -- the private stash, which is what difficulty
    actually varies.

    IT IS ALSO THE RIGHT `hoard_allowance` FOR THE DEAL. deal.py's default of 1
    was correct for a fixed three-finding hand where every difficulty required
    two shares. Under the rhythm the stash is 1 at EASY and 2 at MEDIUM/HARD
    over four rounds, so passing the constant would check proof-survives-hoarding
    against a hoarding pattern the rules do not actually permit -- too strict at
    EASY, too lax at HARD. Derived, therefore, not assumed.
    """
    if rounds <= 0 or not ladder:
        return 0
    return max(0, rounds - int(ladder[rounds - 1]))


# --------------------------------------------------------------------------
# Opening a session
# --------------------------------------------------------------------------

class ApfError(Exception):
    """A session that cannot be opened. Carries the reasons as data, because
    'the deal failed' and 'this mystery cannot be dealt' need different
    responses from the caller -- the first is re-dealable, the second is not."""

    def __init__(self, message: str, issues: Optional[List[str]] = None):
        super().__init__(message)
        self.issues = list(issues or [])


def open_session(mystery: dict, players: Sequence[dict],
                 share_rule: Callable[[int], int],
                 seeds: int = _deal.DEFAULT_SEED_SEARCH) -> dict:
    """Deal a mystery into a rhythm. Returns a plain, JSON-serializable dict.

    `players` is [{"id": ..., "name": ...}, ...] in seating order. `share_rule`
    maps a held-finding count to the number that must have been shared -- see
    the module docstring on why it is injected.

    NOTHING IS FACE UP YET. The session opens at round 0 with every hand dealt
    but unrevealed; `deal_round()` turns one finding per player up. Dealing the
    whole thing at open and revealing progressively (rather than dealing one
    finding per round as the round arrives) is what keeps deal.py's guarantees
    -- solvability, no solo solve, proof surviving hoarding -- true of the
    session as a whole rather than only of its last round.
    """
    ids = [str(p["id"]) for p in players]
    if len(set(ids)) != len(ids):
        raise ApfError("duplicate player ids")
    player_count = len(ids)
    if player_count < 1:
        raise ApfError("no players")

    pool = _deal.build_pool(mystery)
    rounds = round_count(len(pool), player_count)
    if rounds < MIN_ROUNDS:
        raise ApfError(
            f"{len(pool)} findings over {player_count} players is {rounds} round(s); "
            f"at least {MIN_ROUNDS} are needed for a share decision to exist",
            [f"pool {len(pool)} too small for {player_count} players"],
        )

    ladder = share_ladder(rounds, share_rule)
    spec = hand_spec_for(rounds)
    allowance = stash_allowance(rounds, ladder)

    result = _deal.best_deal(mystery, player_count, seeds=seeds,
                             hand_spec=spec, hoard_allowance=allowance)
    if not result.ok:
        raise ApfError("no legal deal for this mystery", result.issues)

    return {
        "rounds": rounds,
        "round": 0,                       # nothing dealt yet
        "player_order": ids,
        "names": {str(p["id"]): p.get("name", "Player") for p in players},
        "hands": {pid: [f.to_dict() for f in hand]
                  for pid, hand in zip(ids, result.hands)},
        "shared": {pid: [] for pid in ids},   # finding ids, cumulative, monotone
        "share_ladder": ladder,
        "stash_allowance": allowance,
        "hand_spec": list(spec),
        "disclosed": False,
        # Who shared what, and when. This is what "she's held back twice now"
        # is read off, and what full disclosure attributes by name.
        "log": [],
        "deal": {
            "seed": result.seed,
            "redundancy": result.redundancy,
            "monopoly": result.monopoly,
            "patterns": result.patterns,
            "seeds_tried": result.seeds_tried,
            "attempts": result.attempts,
        },
    }


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------

def dealt(session: dict, player_id: str) -> List[dict]:
    """The findings this player has actually been handed so far: the first
    `round` slots of their hand. Everything past that is dealt but face down,
    and no client is ever sent it."""
    return list(session["hands"].get(player_id, []))[:session["round"]]


def held_count(session: dict, player_id: str) -> int:
    return len(dealt(session, player_id))


def required_now(session: dict, player_id: str) -> int:
    """How many findings this player must have shared IN TOTAL to pass the
    current checkpoint. Zero before the first checkpoint round, which is the
    machine-readable form of "round 1 has no decision in it"."""
    r = session["round"]
    if r < FIRST_CHECKPOINT_ROUND:
        return 0
    ladder = session["share_ladder"]
    return int(ladder[min(r, len(ladder)) - 1]) if ladder else 0


def outstanding(session: dict, player_id: str) -> int:
    """How many more this player still owes the table. Never negative: sharing
    beyond the minimum is a legal move and must not read as credit toward a
    later round -- the minimum is a floor on the total, and a player who gave
    away four in round 2 has simply already met round 4."""
    return max(0, required_now(session, player_id) - len(session["shared"].get(player_id, [])))


def checkpoint_open(session: dict) -> bool:
    """True when the current round ends in a share checkpoint at all."""
    return session["round"] >= FIRST_CHECKPOINT_ROUND and not session["disclosed"]


def checkpoint_met(session: dict) -> bool:
    """True when every player has met the current round's requirement, so the
    next round may be dealt. Also true at rounds with no checkpoint."""
    return all(outstanding(session, pid) == 0 for pid in session["player_order"])


def deal_round(session: dict) -> int:
    """Turn one more finding face up for every player. Returns the new round.

    Refuses while a checkpoint is outstanding -- the rhythm is the mechanic, and
    a round that arrives before the table has paid is just a faster deal.
    """
    if session["disclosed"]:
        raise ApfError("the case is closed; full disclosure has already run")
    if session["round"] >= session["rounds"]:
        raise ApfError(f"all {session['rounds']} rounds have been dealt")
    if not checkpoint_met(session):
        owing = [session["names"].get(pid, pid) for pid in session["player_order"]
                 if outstanding(session, pid) > 0]
        raise ApfError("the share checkpoint is still open for: " + ", ".join(owing))
    session["round"] += 1
    return session["round"]


def share(session: dict, player_id: str, finding_ids: Sequence[str]) -> dict:
    """Put findings on the table. Cumulative, monotone, idempotent.

    Validates against what the player has actually been DEALT, not their whole
    hand: a player cannot share round 4's finding during round 2, because they
    have not read it yet.
    """
    if player_id not in session["hands"]:
        raise ApfError(f"unknown player {player_id!r}")
    if session["disclosed"]:
        raise ApfError("the case is closed; full disclosure has already run")

    face_up = {f["id"] for f in dealt(session, player_id)}
    wanted = [str(fid) for fid in finding_ids]
    unknown = [fid for fid in wanted if fid not in face_up]
    if unknown:
        raise ApfError(f"not in this player's dealt findings: {unknown}")

    already = session["shared"][player_id]
    newly = [fid for fid in wanted if fid not in already]
    now = time.time()
    for fid in newly:
        already.append(fid)
        session["log"].append({
            "round": session["round"],
            "player_id": player_id,
            "player_name": session["names"].get(player_id, player_id),
            "finding_id": fid,
            "ts": now,
        })

    return {
        "shared_count": len(already),
        "newly_shared": newly,
        "required": required_now(session, player_id),
        "outstanding": outstanding(session, player_id),
    }


def disclose(session: dict) -> List[dict]:
    """Full disclosure: everything anyone still holds becomes public, with the
    holder's name against it. Returns the entries that were newly revealed.

    NOT A TIE-BREAKER AND NOT A RESCUE (owner, Session 41). It is the reward for
    having chosen this mystery: you picked the setting and paid for the
    generation, so you are owed the whole of it rather than the fraction that
    happened to be shared. It does a second job for free -- every finding a
    player sat on is shown with their name on it, which is what makes
    withholding a real decision rather than a costless one.

    IT REUSES THE RULES ALREADY HERE. Disclosure is the ordinary share step with
    the minimum set to everything, applied once, to every player at once. No new
    state, and the reveal is the same projection the board has been running all
    game.
    """
    revealed: List[dict] = []
    now = time.time()
    for pid in session["player_order"]:
        # Everything DEALT, not the whole hand: findings past the last round
        # were never in anybody's possession, so nobody withheld them.
        for finding in dealt(session, pid):
            if finding["id"] in session["shared"][pid]:
                continue
            session["shared"][pid].append(finding["id"])
            entry = {
                "round": session["round"],
                "player_id": pid,
                "player_name": session["names"].get(pid, pid),
                "finding_id": finding["id"],
                "ts": now,
                "disclosure": True,
            }
            session["log"].append(entry)
            revealed.append({**entry, "finding": finding})
    session["disclosed"] = True
    return revealed


# --------------------------------------------------------------------------
# What the room can see
# --------------------------------------------------------------------------

def _finding_index(session: dict) -> Dict[str, dict]:
    """finding id -> {**finding, holder_id, holder_name}. Every dealt finding
    has exactly one holder, which is what lets the pool and the board attribute
    without a second lookup."""
    index: Dict[str, dict] = {}
    for pid in session["player_order"]:
        for finding in session["hands"].get(pid, []):
            index[finding["id"]] = {
                **finding,
                "holder_id": pid,
                "holder_name": session["names"].get(pid, pid),
            }
    return index


def shared_pool(session: dict) -> List[dict]:
    """Everything on the table, oldest first, each with the name of whoever put
    it there and the round they did it in. Ordered by the log rather than by
    hand, because the ORDER is the social record."""
    index = _finding_index(session)
    pool: List[dict] = []
    for entry in session["log"]:
        finding = index.get(entry["finding_id"])
        if finding is None:
            continue
        pool.append({
            **finding,
            "shared_by": entry["player_name"],
            "shared_by_id": entry["player_id"],
            "shared_round": entry["round"],
            "disclosure": bool(entry.get("disclosure")),
        })
    return pool


def board(session: dict, mystery: dict) -> List[dict]:
    """The suspect board: one row per suspect, greyed out or not, attributed.

    ONLY `exonerates` GREYS A FACE. See the module docstring -- item 27's
    narrowing is deliberately not projected here, because a narrowing the game
    draws for you is a narrowing you did not deduce.

    The culprit is not marked and cannot be inferred from a row: a row says
    "cleared" or it says nothing, and the last face standing is a conclusion the
    table reaches, not a flag this function sets.
    """
    ev_by_id = _deal.evidence_by_id(mystery)
    rows = {name: {"name": name, "cleared": False, "cleared_by": []}
            for name in _deal.suspects(mystery)}

    for entry in shared_pool(session):
        finding = _deal.Finding(id=entry["id"], kind=entry["kind"],
                                title=entry["title"], body=entry["body"],
                                reveals=list(entry.get("reveals") or []))
        for name in sorted(_deal.exonerated_by([finding], ev_by_id)):
            row = rows.get(name)
            if row is None:
                continue  # exonerates a non-suspect; feasibility() reports it
            row["cleared"] = True
            row["cleared_by"].append({
                "player_name": entry["shared_by"],
                "finding_id": entry["id"],
                "finding_title": entry["title"],
                "round": entry["shared_round"],
                "disclosure": entry["disclosure"],
            })

    return [rows[name] for name in _deal.suspects(mystery)]


def can_prove(session: dict, player_id: str, mystery: dict) -> bool:
    """Whether this player could prove the case right now: the shared pool plus
    their own hand. YOU ALWAYS KNOW WHAT YOU KEPT -- the same premise
    deal.proof_survives_hoarding() enumerates over, applied to the live game.

    Server-side only. Telling a player they can prove it would hand them the
    deduction the game exists to make them do.
    """
    ev_by_id = _deal.evidence_by_id(mystery)
    known: Dict[str, dict] = {}
    for entry in shared_pool(session):
        known[entry["id"]] = entry
    for finding in dealt(session, player_id):
        known.setdefault(finding["id"], finding)
    findings = [_deal.Finding(id=f["id"], kind=f["kind"], title=f["title"],
                              body=f["body"], reveals=list(f.get("reveals") or []))
                for f in known.values()]
    return _deal.solves(findings, mystery, ev_by_id)


def state_for(session: dict, player_id: str, mystery: dict) -> dict:
    """Everything one client may see. THE PRIVATE HALF IS THIS PLAYER'S ONLY --
    other players' unshared findings never leave the server, and neither does
    any finding past the current round.
    """
    my_shared = set(session["shared"].get(player_id, []))
    hand = [{**f, "shared": f["id"] in my_shared} for f in dealt(session, player_id)]

    return {
        "round": session["round"],
        "rounds": session["rounds"],
        "checkpoint_open": checkpoint_open(session),
        "checkpoint_met": checkpoint_met(session),
        "disclosed": session["disclosed"],
        # The share rule's own answer, sent -- never derived by a client.
        "share_required": required_now(session, player_id),
        "share_outstanding": outstanding(session, player_id),
        "share_ladder": list(session["share_ladder"]),
        "held": len(hand),
        "hand": hand,
        "shared_pool": shared_pool(session),
        "board": board(session, mystery),
        "players": [
            {
                "player_id": pid,
                "name": session["names"].get(pid, pid),
                "held": held_count(session, pid),
                "shared": len(session["shared"].get(pid, [])),
                "outstanding": outstanding(session, pid),
            }
            for pid in session["player_order"]
        ],
    }
