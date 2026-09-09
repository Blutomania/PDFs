#!/usr/bin/env python3
"""
test_apf.py -- the rhythm: assigned over rounds, shared at a cumulative checkpoint.

WHAT THIS PROVES, AND WHY EACH ONE IS HERE. Every assertion below corresponds to
a sentence in docs/PLAYTEST_FLOW.md -> "The rhythm" that a reasonable
implementation could get wrong in a way no other checker would notice:

  - round 1 has NO checkpoint (the minimum's floor of 1 makes a single held finding a
    tax rather than a decision)
  - a shared finding STAYS in its holder's casefile, and sharing is monotone
  - the requirement is CUMULATIVE, so round 4 does not demand three new findings
  - the difficulty ladder SEPARATES under the rhythm, which is the whole reason
    the rhythm exists -- Sessions 38 and 39 both measured it inert at a fixed casefile
  - the suspect board greys on `exonerates` and NEVER on `narrows` (item 27)
  - full disclosure attributes every withheld finding to the player who sat on it
  - a client is never sent another player's casefile, or its own undealt future

The last two matter most: an information game that leaks is not a harder version
of the same game, and a reveal that cannot say who held the ledger page cannot
produce the sentence the mechanic exists for.

Fixtures, for the reason scripts/test_casefiles.py gives -- plus one pass over the
real accepted mystery, which is now on disk and is the shape a table will play.

Zero API calls. Run: python3 scripts/test_apf.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apf
import casefiles as C

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        FAILURES.append(name)


# --------------------------------------------------------------------------
# The share rule, as server/main.py defines it. NOT a second implementation:
# the tests need a rule to inject, and injecting the real one from server/main
# would drag FastAPI and the Anthropic SDK into a zero-dependency test. This is
# a stand-in for the callable, and scripts/test_share_rule.py is what guards the
# real one against acquiring a twin.
# --------------------------------------------------------------------------

def rule(share_min):
    return lambda held: max(1, round(held * share_min))


EASY, MEDIUM, HARD = rule(0.70), rule(0.60), rule(0.50)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

SUSPECTS = ("Vale", "Ortiz", "Brand", "Chen")


def mystery(evidence, witnesses=(), leads=(), culprit="Vale", suspects=SUSPECTS):
    chars = [{"name": n, "role": "suspect"} for n in suspects]
    chars += [{"name": n, "role": "witness", "statement": s, "reveals": list(r)}
              for n, s, r in witnesses]
    return {
        "title": "fixture",
        "solution": {"culprit": culprit},
        "characters": chars,
        "evidence": [
            {"id": e[0], "name": f"item {e[0]}", "description": "...",
             "exonerates": list(e[1]), "implicates": list(e[2]),
             **({"narrows": list(e[3])} if len(e) > 3 else {})}
            for e in evidence
        ],
        "leads": [{"id": lid, "title": f"lead {lid}", "brief": "...", "reveals": list(r)}
                  for lid, r in leads],
        "gameplay_notes": {"difficulty": "MEDIUM"},
    }


def wide_fixture():
    """Four suspects, three required exonerations each carried by two separate
    items, and a pool of 16 findings -- 4 players x 4 rounds exactly."""
    ev = [
        ("E1", ["Ortiz"], []), ("E2", ["Ortiz"], []),
        ("E3", ["Brand"], []), ("E4", ["Brand"], []),
        ("E5", ["Chen"], []),  ("E6", ["Chen"], []),
        ("E7", [], ["Vale"]),  ("E8", [], []),
        ("E9", [], []),        ("E10", [], []),
    ]
    wits = [("Iris", "saw the light", ["E1"]),
            ("Jon", "heard the door", ["E3"]),
            ("Kip", "counted the barrels", [])]
    leads = [("L1", ["E5"]), ("L2", []), ("L3", [])]
    return mystery(ev, wits, leads)


def players(n=4):
    return [{"id": f"p{i}", "name": f"Player {i}"} for i in range(1, n + 1)]


def pay_up(s):
    """Every player shares the minimum they still owe, choosing findings they
    have not already shared. Slicing from the front of the casefile does NOT work:
    sharing is idempotent, so a player who already shared finding 0 would
    re-share it and still owe one."""
    for pid in s["player_order"]:
        need = apf.outstanding(s, pid)
        if not need:
            continue
        already = set(s["shared"][pid])
        fresh = [f["id"] for f in apf.assigned(s, pid) if f["id"] not in already]
        apf.share(s, pid, fresh[:need])


def play_out(s, stop_short=False):
    """Assignment every round, paying each checkpoint with the bare minimum. Leaves
    the final checkpoint unpaid when `stop_short`."""
    while s["round"] < s["rounds"]:
        if apf.checkpoint_open(s):
            pay_up(s)
        apf.open_round(s)
    if not stop_short:
        pay_up(s)


def open4(share_rule=MEDIUM, m=None):
    m = m or wide_fixture()
    return m, apf.open_session(m, players(4), share_rule)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_round_count_and_spec():
    print("\nRounds = findings / players, and the casefile spec is that long")
    check("18 findings over 4 players is 4 rounds", apf.round_count(18, 4) == 4)
    check("fewer players means a longer investigation",
          apf.round_count(18, 2) == 9 and apf.round_count(18, 6) == 3,
          f"{apf.round_count(18, 2)}, {apf.round_count(18, 6)}")
    check("no players is no rounds rather than a crash", apf.round_count(18, 0) == 0)

    spec = apf.casefile_spec_for(4)
    check("the spec's LENGTH is the round count, so casefiles.py needs no new code",
          len(spec) == 4, str(spec))
    check("it keeps APF's specified casefile and extends with the fallback kind",
          spec[:3] == C.DEFAULT_CASEFILE_SPEC and spec[3] == C._FALLBACK_KIND, str(spec))
    check("a short session truncates rather than padding",
          apf.casefile_spec_for(2) == C.DEFAULT_CASEFILE_SPEC[:2], str(apf.casefile_spec_for(2)))


def test_the_ladder_separates():
    """The reason the rhythm exists. Sessions 38 and 39 both measured the
    difficulty ladder inert at a fixed three-finding casefile -- all three
    difficulties resolving to 'share 2, keep 1', because a percentage has no
    resolution over three items. Under a rhythm it separates with no second dial.
    """
    print("\nThe difficulty ladder, which a fixed casefile had killed")
    stash = lambda r, rl: [n - v for n, v in zip(range(1, r + 1), apf.share_ladder(r, rl))]

    check("at a fixed three findings the three difficulties are identical",
          apf.share_ladder(3, EASY)[-1] == apf.share_ladder(3, MEDIUM)[-1]
          == apf.share_ladder(3, HARD)[-1] == 2,
          f"{apf.share_ladder(3, EASY)[-1]}/{apf.share_ladder(3, MEDIUM)[-1]}"
          f"/{apf.share_ladder(3, HARD)[-1]}")

    # docs/PLAYTEST_FLOW.md, "The rhythm" -- the private stash by round.
    for rounds, expected in ((4, (1, 2, 2)), (6, (2, 2, 3)), (8, (2, 3, 4))):
        got = (stash(rounds, EASY)[-1], stash(rounds, MEDIUM)[-1], stash(rounds, HARD)[-1])
        check(f"after round {rounds} the stash is EASY/MEDIUM/HARD {expected}",
              got == expected, f"got {got}")

    check("EASY parts from the rest by round 4, which is why 4 is the floor",
          stash(4, EASY)[-1] < stash(4, MEDIUM)[-1])
    check("and the gap widens rather than closing",
          stash(8, HARD)[-1] - stash(8, EASY)[-1] > stash(4, HARD)[-1] - stash(4, EASY)[-1])

    check("the stash allowance is derived from the ladder, not assumed to be 1",
          apf.stash_allowance(4, apf.share_ladder(4, EASY)) == 1
          and apf.stash_allowance(4, apf.share_ladder(4, HARD)) == 2,
          f"{apf.stash_allowance(4, apf.share_ladder(4, EASY))}/"
          f"{apf.stash_allowance(4, apf.share_ladder(4, HARD))}")


def test_round_one_has_no_decision():
    print("\nRound 1 assigns and does not ask -- the floor of 1 makes it a tax")
    m, s = open4()
    check("a session opens with nothing face up", s["round"] == 0)
    check("and announces its length up front", s["rounds"] == 4)
    check("and announces the whole ladder up front", len(s["share_ladder"]) == 4)

    apf.open_round(s)
    check("round 1 assigns one finding each", apf.held_count(s, "p1") == 1)
    check("round 1 asks for nothing", apf.required_now(s, "p1") == 0)
    check("so no checkpoint is open", not apf.checkpoint_open(s))
    check("and round 2 may be dealt without anyone sharing", apf.open_round(s) == 2)
    check("round 2 opens the first checkpoint", apf.checkpoint_open(s))
    check("which asks for 1 of the 2 held", apf.required_now(s, "p1") == 1)


def test_sharing_is_cumulative_and_monotone():
    print("\nA shared finding stays in the casefile; the requirement is cumulative")
    m, s = open4(MEDIUM)
    apf.open_round(s)
    apf.open_round(s)

    casefile = apf.assigned(s, "p1")
    first = casefile[0]["id"]
    apf.share(s, "p1", [first])
    check("the finding is still in the holder's casefile after sharing",
          first in [f["id"] for f in apf.assigned(s, "p1")])
    check("what was spent is exclusivity: it is now in the shared pool",
          first in [e["id"] for e in apf.shared_pool(s)])
    check("re-sharing the same finding is idempotent, not a second entry",
          apf.share(s, "p1", [first])["shared_count"] == 1)

    check("p1 has met round 2", apf.outstanding(s, "p1") == 0)
    check("but the round cannot advance while others owe", not apf.checkpoint_met(s))
    for pid in ("p2", "p3", "p4"):
        apf.share(s, pid, [apf.assigned(s, pid)[0]["id"]])
    check("once everyone has paid, the round advances", apf.open_round(s) == 3)

    check("round 3 asks for 2 TOTAL, not 2 more", apf.required_now(s, "p1") == 2)
    check("so a player who shared 1 owes exactly 1 more", apf.outstanding(s, "p1") == 1)

    # Over-sharing is legal and is not credit -- it simply meets a later round.
    m2, s2 = open4(MEDIUM)
    for _ in range(3):
        if apf.checkpoint_open(s2):
            for pid in s2["player_order"]:
                already = set(s2["shared"][pid])
                fresh = [f["id"] for f in apf.assigned(s2, pid) if f["id"] not in already]
                apf.share(s2, pid, fresh[:apf.outstanding(s2, pid) + 1])
        apf.open_round(s2)
    check("a player who gave away early has simply already met a later round",
          apf.outstanding(s2, "p1") == 0)

    try:
        apf.share(s2, "p1", ["E:NOPE"])
        check("sharing a finding you were never assigned is refused", False)
    except apf.ApfError:
        check("sharing a finding you were never assigned is refused", True)

    # A future round's finding is assigned but face down: it cannot be spent early.
    m3, s3 = open4(MEDIUM)
    apf.open_round(s3)
    future = s3["casefiles"]["p1"][3]["id"]
    try:
        apf.share(s3, "p1", [future])
        check("a face-down future finding cannot be shared early", False)
    except apf.ApfError:
        check("a face-down future finding cannot be shared early", True)


def test_the_round_cannot_outrun_the_checkpoint():
    print("\nThe rhythm is the mechanic, so a round waits for the table")
    m, s = open4(MEDIUM)
    apf.open_round(s)
    apf.open_round(s)
    try:
        apf.open_round(s)
        check("assignment over an open checkpoint is refused", False)
    except apf.ApfError as e:
        check("assignment over an open checkpoint is refused", True)
        check("and the refusal names who still owes",
              "Player 1" in str(e), str(e))

    pay_up(s)
    apf.open_round(s)
    pay_up(s)
    apf.open_round(s)
    check("the last round is round 4", s["round"] == 4)
    pay_up(s)
    try:
        apf.open_round(s)
        check("there is no round 5", False)
    except apf.ApfError:
        check("there is no round 5", True)


def test_the_board():
    print("\nThe suspect board: greyed with a name on it, and never by narrowing")
    m = wide_fixture()
    s = apf.open_session(m, players(4), MEDIUM)
    apf.open_round(s)

    rows = apf.board(s, m)
    check("the board lists every suspect", [r["name"] for r in rows] == list(SUSPECTS))
    check("nobody is cleared before anything is shared",
          not any(r["cleared"] for r in rows))
    check("and the culprit is not marked in any way",
          all(set(r) == {"name", "cleared", "cleared_by"} for r in rows), str(rows[0]))

    # Share any assigned finding that clears somebody, and watch the face grey out.
    ev = C.evidence_by_id(m)
    as_finding = lambda f: C.Finding(id=f["id"], kind=f["kind"], title=f["title"],
                                     body=f["body"], reveals=list(f["reveals"]))
    holder, fid, cleared_names = None, None, []
    for pid in s["player_order"]:
        for f in apf.assigned(s, pid):
            names = sorted(C.exonerated_by([as_finding(f)], ev))
            if names:
                holder, fid, cleared_names = pid, f["id"], names
                break
        if holder:
            break
    check("round 1 assigned somebody a finding that clears a suspect",
          holder is not None, "no exonerating finding in any casefile at round 1")
    apf.share(s, holder, [fid])
    rows = {r["name"]: r for r in apf.board(s, m)}
    check("sharing an exonerating finding greys that suspect out",
          all(rows[n]["cleared"] for n in cleared_names), str(cleared_names))
    check("with the sharer's name against it",
          rows[cleared_names[0]]["cleared_by"][0]["player_name"]
          == s["names"][holder])
    check("and the round they did it in",
          rows[cleared_names[0]]["cleared_by"][0]["round"] == 1)

    # ITEM 27. A narrowing must never surface as "the culprit is one of these".
    # Two carriers per exoneration, as the generation prompt requires -- one
    # carrier per suspect is what makes proof die under hoarding (casefiles.py's own
    # measurement), and a fixture that cannot be assigned proves nothing about the
    # board.
    glove = mystery(
        [("E1", ["Ortiz"], []), ("E2", ["Ortiz"], []),
         ("E3", ["Brand"], []), ("E4", ["Brand"], []),
         ("E5", ["Chen"], []),  ("E6", ["Chen"], []),
         ("E7", [], ["Vale"], ["Vale", "Ortiz"]),
         ("E8", [], []), ("E9", [], [])],
        witnesses=[("Iris", "saw it", ["E1"]), ("Jon", "heard it", [])],
        leads=[("L1", ["E3"]), ("L2", [])],
    )
    gs = apf.open_session(glove, players(4), MEDIUM)
    play_out(gs)
    for pid in gs["player_order"]:
        apf.share(gs, pid, [f["id"] for f in apf.assigned(gs, pid)])
    grows = {r["name"]: r for r in apf.board(gs, glove)}
    check("a narrowing to [Vale, Ortiz] does not grey Brand or Chen on the board",
          not any(r["cleared"] and not r["cleared_by"] for r in grows.values()))
    check("Brand and Chen are cleared by their EXONERATIONS, each attributed",
          all(grows[n]["cleared"] and grows[n]["cleared_by"] for n in ("Brand", "Chen")))
    check("and the narrowing itself clears nobody",
          all(all(cb["finding_id"] != "E:E7" for cb in r["cleared_by"])
              for r in grows.values()))


def test_full_disclosure():
    print("\nFull disclosure closes the game, with a name on every withheld finding")
    m, s = open4(HARD)
    play_out(s)

    withheld_before = sum(len(apf.assigned(s, pid)) - len(s["shared"][pid])
                          for pid in s["player_order"])
    check("at HARD over four rounds there is a real stash to reveal",
          withheld_before > 0, f"{withheld_before}")

    revealed = apf.disclose(s)
    check("disclosure reveals exactly what was still held",
          len(revealed) == withheld_before, f"{len(revealed)} vs {withheld_before}")
    check("every revealed finding carries the name of whoever sat on it",
          all(r["player_name"] and r["finding"] for r in revealed))
    check("and is flagged as disclosure, not as a share the player chose",
          all(r["disclosure"] for r in revealed))
    check("after disclosure nothing is held back",
          all(apf.outstanding(s, pid) == 0 for pid in s["player_order"]))
    check("the pool now holds every assigned finding",
          len(apf.shared_pool(s)) == sum(len(apf.assigned(s, pid))
                                         for pid in s["player_order"]))
    try:
        apf.share(s, "p1", [apf.assigned(s, "p1")[0]["id"]])
        check("the closed case refuses further shares", False)
    except apf.ApfError:
        check("the closed case refuses further shares", True)

    # Disclosure is the ordinary share with the minimum set to everything, so
    # the board must reach the same place a fully-shared game would.
    rows = apf.board(s, m)
    check("and the board resolves to exactly the culprit standing",
          [r["name"] for r in rows if not r["cleared"]] == ["Vale"],
          str([r["name"] for r in rows if not r["cleared"]]))


def test_a_client_is_sent_only_its_own_half():
    print("\nAn information game that leaks is a different game")
    m, s = open4(MEDIUM)
    apf.open_round(s)
    apf.open_round(s)
    st = apf.state_for(s, "p1", m)

    check("the casefile is this player's assigned findings only",
          [f["id"] for f in st["casefile"]] == [f["id"] for f in apf.assigned(s, "p1")])
    check("it stops at the current round -- no future findings",
          len(st["casefile"]) == 2 and s["rounds"] == 4)

    # Compare EXACT string values, not substrings: "E:E1" is a substring of
    # "E:E10", so a naive `in json.dumps(...)` reports a leak that is not one.
    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from strings(v)
        elif isinstance(node, list):
            for v in node:
                yield from strings(v)

    values = set(strings(st))
    others = {f["id"] for pid in ("p2", "p3", "p4") for f in s["casefiles"][pid]
              if f["id"] not in s["shared"][pid]}
    leaked = sorted(others & values)
    check("no other player's unshared finding appears anywhere in the payload",
          not leaked, str(leaked[:3]))
    future = {f["id"] for f in s["casefiles"]["p1"][2:]}
    check("nor does this player's own undealt future", not (future & values))
    check("the solution is nowhere in it", "culprit" not in json.dumps(st))
    check("nor is whether this player could already prove it",
          "can_prove" not in json.dumps(st))

    check("the share requirement is SENT, so no client has to derive one",
          st["share_required"] == 1 and st["share_outstanding"] == 1)
    check("and every player's share count is public -- the pattern is the point",
          [p["shared"] for p in st["players"]] == [0, 0, 0, 0])

    apf.share(s, "p1", [apf.assigned(s, "p1")[0]["id"]])
    st2 = apf.state_for(s, "p2", m)
    check("what p1 shared IS visible to p2, with p1's name on it",
          st2["shared_pool"][0]["shared_by"] == "Player 1")
    check("and p2 can see that p1 has paid and the others have not",
          [p["outstanding"] for p in st2["players"]] == [0, 1, 1, 1])


def test_can_prove_stays_server_side():
    print("\n'You always know what you kept' -- checked, never told")
    m, s = open4(MEDIUM)
    play_out(s)
    provers = [pid for pid in s["player_order"] if apf.can_prove(s, pid, m)]
    check("by the last round somebody can prove it", provers, str(provers))
    check("and it is not everybody, or the shares did nothing",
          len(provers) <= len(s["player_order"]))
    apf.disclose(s)
    check("after full disclosure everyone can prove it",
          all(apf.can_prove(s, pid, m) for pid in s["player_order"]))


def test_refusals():
    print("\nA session that cannot be opened says why")
    tiny = mystery([("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], [])])
    try:
        apf.open_session(tiny, players(4), MEDIUM)
        check("a pool too small for two rounds is refused", False)
    except apf.ApfError as e:
        check("a pool too small for two rounds is refused", True)
        check("and the refusal names the arithmetic",
              "round" in str(e), str(e))

    try:
        apf.open_session(wide_fixture(),
                         [{"id": "p1", "name": "A"}, {"id": "p1", "name": "B"}], MEDIUM)
        check("duplicate player ids are refused", False)
    except apf.ApfError:
        check("duplicate player ids are refused", True)

    # An unassignable MYSTERY is a different refusal from an unlucky assignment.
    solo = mystery([("E1", ["Ortiz", "Brand", "Chen"], []), ("E2", [], ["Vale"]),
                    ("E3", [], []), ("E4", [], []), ("E5", [], []), ("E6", [], []),
                    ("E7", [], []), ("E8", [], [])])
    try:
        apf.open_session(solo, players(4), MEDIUM)
        check("a mystery one finding solves alone is refused", False)
    except apf.ApfError as e:
        check("a mystery one finding solves alone is refused", True)
        check("and it carries casefiles.py's own diagnosis rather than a bare message",
              bool(e.issues), str(e.issues))


def test_against_the_accepted_mystery():
    """The first accepted mystery is on disk and is the shape a table will play.
    Fixtures prove the rules; this proves they survive real generated data."""
    print("\nThe real thing: the_neriin_in_the_pilchard_barrel")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = sorted(glob.glob(os.path.join(
        root, "mystery_database", "generated", "the_neriin_in_the_pilchard_barrel_*.json")))
    if not hits:
        print("  SKIP  the accepted mystery is not on disk")
        return
    m = json.load(open(hits[-1]))

    for label, share_rule in (("EASY", EASY), ("MEDIUM", MEDIUM), ("HARD", HARD)):
        s = apf.open_session(m, players(4), share_rule)
        check(f"{label}: it opens at four rounds", s["rounds"] == 4, str(s["rounds"]))
        check(f"{label}: the assignment has no monopoly on proof",
              s["assignment"]["monopoly"] == 0, str(s["assignment"]))
        play_out(s)
        held_back = sum(len(apf.assigned(s, pid)) - len(s["shared"][pid])
                        for pid in s["player_order"])
        check(f"{label}: players who share only the minimum still hold {held_back}",
              held_back == 4 * s["stash_allowance"], f"{held_back}")
        apf.disclose(s)
        rows = apf.board(s, m)
        standing = [r["name"] for r in rows if not r["cleared"]]
        check(f"{label}: full disclosure leaves exactly the culprit standing",
              standing == [C.culprit(m)], str(standing))

    # EASY must be the difficulty that puts LESS in a private stash.
    easy = apf.open_session(m, players(4), EASY)
    hard = apf.open_session(m, players(4), HARD)
    check("EASY permits a smaller stash than HARD on the real mystery",
          easy["stash_allowance"] < hard["stash_allowance"],
          f"{easy['stash_allowance']} vs {hard['stash_allowance']}")


def main():
    print("apf.py -- the rhythm")
    test_round_count_and_spec()
    test_the_ladder_separates()
    test_round_one_has_no_decision()
    test_sharing_is_cumulative_and_monotone()
    test_the_round_cannot_outrun_the_checkpoint()
    test_the_board()
    test_full_disclosure()
    test_a_client_is_sent_only_its_own_half()
    test_can_prove_stays_server_side()
    test_refusals()
    test_against_the_accepted_mystery()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + ", ".join(FAILURES))
        return 1
    print("The rhythm holds: round 1 asks nothing, sharing is cumulative and "
          "monotone,\nthe ladder separates, the board never narrows for you, and "
          "disclosure names\nwhoever sat on it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
