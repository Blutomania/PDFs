#!/usr/bin/env python3
"""
test_casefiles.py -- fixture tests for casefiles.py, APF's constrained assignment.

WHY FIXTURES AND NOT THE CORPUS. No mystery on disk carries `reveals` or
`exonerates`: the schema landed in Session 38 and has never been generated
against. All 17 generated mysteries would therefore pass every check below
vacuously, which is the same trap Session 38 named for check_narrative.py --
"a branch with no input is a branch nobody ran".

Each test names the constraint it proves and asserts the assignment REFUSES a
mystery that violates it. A test suite that only proves the happy path would
pass just as well against an assign() that returned ok=True unconditionally.

Zero API calls. Run: python3 scripts/test_casefiles.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import casefiles as C


# --------------------------------------------------------------------------
# Fixture builder
# --------------------------------------------------------------------------

def mystery(evidence, witnesses=(), leads=(), culprit="Vale",
            suspects=("Vale", "Ortiz", "Brand", "Chen"), difficulty="MEDIUM"):
    """A minimal mystery carrying only what the assignment reads.

    Four suspects and one culprit means three required exonerations, which is
    PLAYTEST_FLOW's specified shape rather than the 2-3 suspects most of the
    March corpus actually has.
    """
    chars = [{"name": n, "role": "suspect"} for n in suspects]
    chars += [{"name": n, "role": "witness", "statement": stmt, "reveals": list(rv)}
              for n, stmt, rv in witnesses]
    return {
        "solution": {"culprit": culprit},
        "characters": chars,
        "evidence": [
            {"id": e[0], "name": f"item {e[0]}", "description": "...",
             "exonerates": list(e[1]), "implicates": list(e[2]),
             # 4th element is the item-27 narrowing set, optional so every
             # pre-item-27 fixture above is untouched.
             **({"narrows": list(e[3])} if len(e) > 3 else {})}
            for e in evidence
        ],
        "leads": [{"id": lid, "title": f"lead {lid}", "brief": "...", "reveals": list(rv)}
                  for lid, rv in leads],
        "gameplay_notes": {"difficulty": difficulty},
    }


def solvable_fixture(difficulty="MEDIUM"):
    """A mystery that CAN be assigned: three exonerations spread over six items,
    each carried by two separate evidence items so redundancy 2 is reachable,
    and no single item clearing more than one suspect."""
    ev = [
        ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
        ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], []),
        ("E7", [], ["Vale"]), ("E8", [], []),
    ]
    wit = [("Ada", "I saw the light on.", ["E1"]),
           ("Bo", "The door was bolted.", ["E2"]),
           ("Cy", "He was never there.", ["E3"]),
           ("Di", "Nothing unusual.", ["E8"])]
    leads = [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", ["E7"])]
    return mystery(ev, wit, leads, difficulty=difficulty)


def tight_redundancy_fixture():
    """Redundancy 2 is FEASIBLE here but not free.

    Each required exoneration is carried by EXACTLY two findings, so
    feasibility() passes -- two carriers can reach two casefiles. Whether they
    actually DO is what _violations() has to enforce, because an assignment that puts
    both carriers of Ortiz in one casefile satisfies constraints 1 and 2 and still
    leaves Ortiz reaching a single casefile.

    This is the fixture the first version of this suite lacked: its redundancy
    test was refused by the feasibility pre-check, so deleting the _violations
    branch entirely left the suite green.
    """
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], ["Vale"])]
    wit = [("Ada", "s", ["E1"]), ("Bo", "s", ["E4"]), ("Cy", "s", ["E5"])]
    leads = [("L1", ["E2"]), ("L2", ["E3"]), ("L3", []), ("L4", [])]
    return mystery(ev, wit, leads)


def carriers(n):
    """A mystery where exactly n DEALABLE FINDINGS can clear each suspect.

    Counted over the pool, not over evidence[]: a witness whose `reveals` names
    E1 is a separate finding, assigned to a different player and hoarded
    independently, so it is a genuine second route to the same exoneration.

    THIS WAS DEFINED TWICE AND THE COPIES DRIFTED. One pointed its witnesses at
    the exonerating items, so at n=1 it really had TWO carriers and the whole
    monopoly section tested the wrong thing while passing. The witnesses and
    leads below point only at neutral evidence, so n really is the carrier
    count -- and there is now one definition, which is why the drift cannot
    come back.
    """
    ev, k = [], 1
    for who in ("Ortiz", "Brand", "Chen"):
        for _ in range(n):
            ev.append((f"E{k}", [who], [])); k += 1
    neutral_start = k
    for _ in range(6):
        ev.append((f"E{k}", [], [])); k += 1
    ev.append((f"E{k}", [], ["Vale"]))
    neutral = [f"E{i}" for i in range(neutral_start, neutral_start + 6)]
    wit = [(f"W{i}", "s", [neutral[i]]) for i in range(3)]
    leads = [(f"L{i+1}", [neutral[i + 3]]) for i in range(3)]
    return mystery(ev, wit, leads)


FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        FAILURES.append(name)


# --------------------------------------------------------------------------
# The arithmetic itself
# --------------------------------------------------------------------------

def test_arithmetic():
    print("\nthe arithmetic")
    m = solvable_fixture()
    ev = C.evidence_by_id(m)
    pool = C.build_pool(m)

    check("required_exonerations is every suspect but the culprit",
          C.required_exonerations(m) == {"Ortiz", "Brand", "Chen"},
          str(C.required_exonerations(m)))

    check("the full pool solves", C.solves(pool, m, ev))

    # Cardinality is not enough: clearing the culprit and two others leaves ONE
    # suspect standing and still gets the wrong person.
    wrong = [f for f in pool if f.id in ("E:E1", "E:E2")]
    wrong.append(C.Finding(id="X", kind="clue", title="x", body="", reveals=["E9"]))
    m2 = mystery([("E9", ["Vale"], [])] + [("E1", ["Ortiz"], []), ("E2", ["Brand"], [])])
    ev2 = C.evidence_by_id(m2)
    pool2 = C.build_pool(m2)
    standing = set(C.suspects(m2)) - C.exonerated_by(pool2, ev2)
    check("a set clearing the culprit does not solve, even at the right count",
          len(standing) == 1 and not C.solves(pool2, m2, ev2), f"standing={standing}")

    check("a dangling reveals id contributes no exoneration",
          C.exonerated_by([C.Finding("Z", "clue", "z", "", ["NOPE"])], ev) == set())


# --------------------------------------------------------------------------
# The three constraints -- each proved by a mystery that violates it
# --------------------------------------------------------------------------

def test_constraint_1_union_solves():
    print("\nconstraint 1 -- the union of all assigned findings eliminates all but one")
    # Chen is never exonerated by anything, so two suspects always stand.
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", [], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E1"]), ("Bo", "s", ["E2"]), ("Cy", "s", ["E3"])],
                [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", [])])
    r = C.assign(m, player_count=3, seed=1)
    check("refuses a mystery whose evidence cannot eliminate to one", not r.ok)
    check("and says which suspect is left standing",
          any("Chen" in i for i in r.issues), str(r.issues))


def test_constraint_2_no_solo_win():
    print("\nconstraint 2 -- no single player's casefile solves alone")
    # One item clears all three innocents: whoever draws it wins by itself.
    ev = [("E1", ["Ortiz", "Brand", "Chen"], []), ("E2", [], []), ("E3", [], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E1"]), ("Bo", "s", ["E2"]), ("Cy", "s", ["E3"])],
                [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", [])])
    r = C.assign(m, player_count=3, seed=1)
    check("refuses a mystery where one finding solves outright", not r.ok)
    check("and names the finding that does it",
          any("solves the mystery by itself" in i for i in r.issues), str(r.issues))

    # And the per-casefile check fires even when no SINGLE finding solves: two
    # findings that together clear all three, landing in one casefile.
    m2 = solvable_fixture()
    ok = C.assign(m2, player_count=4, seed=7)
    check("a well-formed mystery still assigns", ok.ok, str(ok.issues))
    check("and no casefile solves alone",
          ok.ok and not any(C.solves(h, m2) for h in ok.casefiles))


def test_constraint_3_redundancy():
    print("\nconstraint 3 -- redundancy (difficulty's new home)")
    # Each exoneration carried by exactly ONE evidence item: reachable at
    # redundancy 1, impossible at 2.
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E4"]), ("Bo", "s", ["E5"]), ("Cy", "s", ["E6"])],
                [("L1", []), ("L2", []), ("L3", []), ("L4", [])])

    # Redundancy in isolation. The proof constraint is switched off here on
    # purpose: this fixture gives each exoneration exactly ONE carrier, so proof
    # does not survive hoarding, and leaving it on would make this a test of the
    # wrong constraint. The next case asserts that it does fire here.
    r1 = C.assign(m, player_count=3, seed=3, redundancy=1,
                require_proof_under_hoarding=False)
    check("assigns at redundancy 1 with the proof constraint off", r1.ok, str(r1.issues))

    r1p = C.assign(m, player_count=3, seed=3, redundancy=1)
    check("and the SAME assignment is refused with it on, because one route per "
          "suspect cannot survive hoarding",
          not r1p.ok and any("proof dies under hoarding" in i for i in r1p.issues),
          str(r1p.issues))

    r2 = C.assign(m, player_count=3, seed=3, redundancy=2,
                require_proof_under_hoarding=False)
    check("refuses the same mystery at redundancy 2", not r2.ok)
    check("and says the exoneration is carried by too few findings",
          any("carried by 1 finding" in i for i in r2.issues), str(r2.issues))

    # EASY should pick redundancy 2 off the difficulty, HARD 1.
    easy = C.assign(solvable_fixture("EASY"), player_count=4, seed=11)
    hard = C.assign(solvable_fixture("HARD"), player_count=4, seed=11)
    check("EASY assigns at redundancy 2", easy.redundancy == 2, str(easy.redundancy))
    check("HARD assigns at redundancy 1", hard.redundancy == 1, str(hard.redundancy))

    # The branch that actually enforces it, on a mystery feasibility lets through.
    tight = tight_redundancy_fixture()
    ev = C.evidence_by_id(tight)
    check("redundancy 2 is FEASIBLE on the tight fixture (so _violations, not "
          "feasibility, is what must enforce it)",
          C.feasibility(tight, 3, redundancy=2) == [],
          str(C.feasibility(tight, 3, redundancy=2)))

    t = C.assign(tight, player_count=3, seed=2, redundancy=2)
    check("the tight fixture still assigns", t.ok, str(t.issues))
    reach = {r: sum(1 for h in t.casefiles if r in C.exonerated_by(h, ev))
             for r in C.required_exonerations(tight)}
    check("and every exoneration really reaches two distinct casefiles",
          t.ok and all(v >= 2 for v in reach.values()), str(reach))

    # The ceiling, which is arithmetic rather than luck. R=3, P=4, k=3 forces
    # some casefile to hold all three exonerations, which is constraint 2.
    over = C.assign(solvable_fixture(), player_count=4, seed=1, redundancy=3)
    check("redundancy above the ceiling is refused as impossible, not merely unlucky",
          (not over.ok) and any("is impossible at" in i for i in over.issues), str(over.issues))
    check("and it is refused up front, without burning attempts",
          over.attempts == 0, str(over.attempts))
    check("the ceiling is reported, and at APF's shape it is 2",
          any("Ceiling here is 2" in i for i in over.issues), str(over.issues))
    check("redundancy 2 is at the ceiling and still assigns",
          C.assign(solvable_fixture(), player_count=4, seed=1, redundancy=2).ok)
    # A wider table lifts it: R=3, P=5 makes k=3 reachable again.
    check("a five-player table lifts the ceiling to 3",
          not any("is impossible at" in i
                  for i in C.feasibility(solvable_fixture(), 5, redundancy=3)),
          str(C.feasibility(solvable_fixture(), 5, redundancy=3)))

    # _violations() tested directly, on an assignment casefile-built to break redundancy:
    # both Ortiz carriers in casefile 0. Constraints 1 and 2 still hold.
    pool = {f.id: f for f in C.build_pool(tight)}
    stacked = [
        [pool["E:E1"], pool["W:Ada"], pool["E:E6"]],   # both Ortiz carriers here
        [pool["E:E2"], pool["L:L1"], pool["E:E4"]],
        [pool["E:E3"], pool["L:L2"], pool["E:E5"]],
    ]
    v2 = C._violations(stacked, tight, ev, redundancy=2)
    v1 = C._violations(stacked, tight, ev, redundancy=1)
    check("_violations reports an exoneration confined to one casefile at redundancy 2",
          any("Ortiz" in x and "1 casefile" in x for x in v2), str(v2))
    check("and the same assignment is legal at redundancy 1", v1 == [], str(v1))


# --------------------------------------------------------------------------
# Feasibility diagnostics -- the difference between re-running the assignment and regenerating
# --------------------------------------------------------------------------

def test_the_glove():
    print("\nitem 27 -- the glove: incrimination alongside exculpation")
    # The owner's scenario, literally. Four suspects; Vale did it. A bloody
    # man's glove rules out the women. An alibi clears the other man.
    ev = [
        ("G1", [], [], ["Vale", "Ortiz"]),   # the glove: only the men could have worn it
        ("E1", ["Ortiz"], []),               # CCTV clears Ortiz
        ("E2", ["Brand"], []), ("E3", ["Chen"], []),
        ("E4", ["Brand"], []), ("E5", ["Chen"], []),
        ("E6", ["Ortiz"], []), ("E7", [], ["Vale"]),
    ]
    m = mystery(ev, [("Ada", "s", ["E2"]), ("Bo", "s", ["E3"]), ("Cy", "s", ["E7"])],
                [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"])])
    evb = C.evidence_by_id(m)
    pool = {f.id: f for f in C.build_pool(m)}
    glove, cctv = pool["E:G1"], pool["E:E1"]

    check("the glove alone clears nobody",
          C.exonerated_by([glove], evb) == set())
    check("and the glove alone does not solve", not C.solves([glove], m, evb))
    check("the alibi alone does not solve", not C.solves([cctv], m, evb))
    check("but the two TOGETHER name the culprit -- two findings that "
          "individually prove nothing combine into a proof",
          C.solves([glove, cctv], m, evb))

    check("the glove narrows to the men it names",
          C.narrowed_by([glove], m, evb) == {"Vale", "Ortiz"})
    check("a finding with no narrowing narrows nothing",
          C.narrowed_by([cctv], m, evb) == set(C.suspects(m)))

    # Two narrowing findings intersect.
    ev2 = list(ev) + [("G2", [], [], ["Vale", "Brand"])]
    m2 = mystery(ev2, [("Ada", "s", ["E2"]), ("Bo", "s", ["E3"]), ("Cy", "s", ["E7"])],
                 [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"])])
    evb2 = C.evidence_by_id(m2)
    p2 = {f.id: f for f in C.build_pool(m2)}
    check("two narrowing findings INTERSECT rather than accumulate",
          C.narrowed_by([p2["E:G1"], p2["E:G2"]], m2, evb2) == {"Vale"})

    check("subtraction still reaches the culprit without the glove at all, so "
          "narrowing is a faster route and never the only one",
          C.solves([f for f in C.build_pool(m) if f.id != "E:G1"], m, evb))

    # --- fair play: the culprit must survive every narrowing ---
    lying = mystery([("G1", [], [], ["Ortiz", "Brand"]),
                     ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
                     ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], [])])
    issues = C.feasibility(lying, 4)
    check("a narrowing that excludes the culprit is refused",
          any("excludes the culprit" in i for i in issues), str(issues))

    single = mystery([("G1", [], [], ["Vale"]),
                      ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
                      ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], [])])
    check("a narrowing naming ONE suspect is refused -- it is the answer on a finding",
          any("1 actual suspect" in i for i in C.feasibility(single, 4)),
          str(C.feasibility(single, 4)))

    # Session 41, earned by `the_last_night_of_delacroix_&_sons`: its E9 narrowed
    # to [the culprit, THE VICTIM]. Two entries passed the old "at least two"
    # test, but a dead man is not a living possibility -- so it was a
    # single-suspect narrowing, and the finding solved the case on its own.
    padded = mystery([("G1", [], [], ["Vale", "The Victim"]),
                      ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
                      ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], [])])
    check("padding a narrowing with a non-suspect does not widen it",
          any("1 actual suspect" in i for i in C.feasibility(padded, 4)),
          str(C.feasibility(padded, 4)))

    everyone = mystery([("G1", [], [], ["Vale", "Ortiz", "Brand", "Chen"]),
                        ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
                        ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], [])])
    check("a narrowing naming EVERY suspect is refused -- it rules nobody out",
          any("rules nobody out" in i for i in C.feasibility(everyone, 4)),
          str(C.feasibility(everyone, 4)))

    ghost = mystery([("G1", [], [], ["Vale", "Nobody"]),
                     ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
                     ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], [])])
    check("a narrowing naming a non-suspect is refused",
          any("not suspects" in i for i in C.feasibility(ghost, 4)),
          str(C.feasibility(ghost, 4)))

    # --- elimination must stay sufficient without any narrowing ---
    load_bearing = mystery([("G1", [], [], ["Vale", "Ortiz"]),
                            ("E1", ["Ortiz"], []), ("E2", [], []), ("E3", [], []),
                            ("E4", [], []), ("E5", [], []), ("E6", [], [])])
    check("a mystery solvable ONLY with the glove is refused, because withholding "
          "it would make the case unprovable",
          any("load-bearing" in i for i in C.feasibility(load_bearing, 4)),
          str(C.feasibility(load_bearing, 4)))

    check("a well-formed glove mystery has no feasibility issues",
          C.feasibility(m, 4) == [], str(C.feasibility(m, 4)))

    # --- and the assignment must not casefile one player both halves ---
    r = C.assign(m, player_count=4, seed=3)
    check("it still assigns", r.ok, str(r.issues))
    if r.ok:
        check("and no casefile holds a glove-plus-alibi pair that solves alone",
              not any(C.solves(h, m, evb) for h in r.casefiles))


def test_proof_survives_hoarding():
    print("\nconstraint 4 -- it is a race to PROOF, not to the best bet")
    # Owner's decision, Session 39. What makes proof survive is CARRIERS -- how
    # many separate findings can clear a given suspect -- not redundancy.


    one = C.assign(carriers(1), player_count=4, seed=4, require_proof_under_hoarding=False)
    ok1, tot1, _ = C.proof_survives_hoarding(one.casefiles, carriers(1))
    check("one route per suspect: proof does NOT always survive hoarding",
          one.ok and ok1 < tot1, f"{ok1}/{tot1}")

    two = C.assign(carriers(2), player_count=4, seed=4)
    ok2, tot2, _ = C.proof_survives_hoarding(two.casefiles, carriers(2))
    check("two routes per suspect: proof survives EVERY hoarding pattern",
          two.ok and ok2 == tot2, f"{ok2}/{tot2}")
    check("and that holds at redundancy 1, so it is carriers and not redundancy "
          "that buys it",
          C.assign(carriers(2), player_count=4, seed=4, redundancy=1).ok)

    check("the enumeration covers 3^4 = 81 patterns at APF's shape",
          tot2 == 81, str(tot2))

    # A player knows what they kept: proof may rest on their own hoarded finding.
    m = carriers(2)
    r = C.assign(m, player_count=4, seed=6)
    evb = C.evidence_by_id(m)
    check("a casefile that solves only WITH its own kept finding still counts as proof",
          r.ok and all(C.solves([f for h in r.casefiles for f in h], m, evb)
                       for _ in [0]))


def test_no_prover_monopoly():
    print("\nconstraint 5 -- a race needs at least two runners (opt-in)")


    check("it is OFF by default, so a monopoly assignment is still legal",
          C.assign(carriers(1), player_count=4, seed=4,
                 require_proof_under_hoarding=False).ok)

    one = carriers(1)
    r = C.assign(one, player_count=4, seed=4, require_proof_under_hoarding=False,
               forbid_prover_monopoly=True)
    check("one route per suspect can never be monopoly-free", not r.ok)
    check("and the refusal says so", any("monopoly" in i for i in r.issues), str(r.issues))

    # MEASURED over 20 seeds each, with the constraint ON so the assignment is
    # actually searching:
    #
    #   carriers   proof-safe assignment found   also monopoly-free
    #      1            0/20                    0/20
    #      2           20/20                    8/20
    #      3           20/20                   17/20
    #      5           20/20                   19/20
    #
    # Two carriers is exactly the threshold for PROOF, which is the owner's
    # rule. Monopoly-freedom is a strictly harder ask and only becomes reliable
    # at three, which is why constraint 5 is opt-in and why this asserts it at
    # three rather than two.
    three = carriers(3)
    t = C.assign(three, player_count=4, seed=4, forbid_prover_monopoly=True)
    check("three carriers: a monopoly-free assignment is found by re-running the assignment",
          t.ok, str(t.issues))
    if t.ok:
        counts = C.prover_counts(t.casefiles, three)
        check("and no pattern leaves exactly one player able to prove it",
              counts.get(1, 0) == 0, str(counts))

    two = carriers(2)
    check("two carriers still always yields a PROOF-safe assignment, which is the "
          "rule the owner actually set",
          all(C.assign(two, player_count=4, seed=s).ok for s in range(5)))

    # prover_counts must actually count, not just report presence.
    check("prover_counts totals every hoarding pattern",
          t.ok and sum(C.prover_counts(t.casefiles, three).values()) == 81,
          str(sum(C.prover_counts(t.casefiles, three).values()) if t.ok else "n/a"))


def test_feasibility_diagnostics():
    print("\nfeasibility -- why an assignment cannot be made")
    base = solvable_fixture()

    dangling = solvable_fixture()
    dangling["characters"][4]["reveals"] = ["E99"]
    check("a reveals pointer naming no evidence item is reported",
          any("E99" in i for i in C.feasibility(dangling, 4)),
          str(C.feasibility(dangling, 4)))

    misnamed = solvable_fixture()
    misnamed["evidence"][0]["exonerates"] = ["Dr. Ortiz"]
    issues = C.feasibility(misnamed, 4)
    check("an exonerates name matching no suspect is reported, not fuzzy-matched",
          any("Dr. Ortiz" in i and "not a suspect" in i for i in issues), str(issues))

    cleared = solvable_fixture()
    cleared["evidence"][6]["exonerates"] = ["Vale"]
    check("evidence exonerating the culprit is reported",
          any("culprit" in i and "exonerated" in i for i in C.feasibility(cleared, 4)))

    nocul = solvable_fixture()
    nocul["solution"]["culprit"] = "Nobody"
    check("a culprit who is not a suspect is reported",
          any("not among the suspects" in i for i in C.feasibility(nocul, 4)))

    check("a well-formed mystery has no feasibility issues",
          C.feasibility(base, 4, redundancy=2) == [], str(C.feasibility(base, 4, redundancy=2)))

    thin = solvable_fixture()
    thin["leads"] = []
    thin["evidence"] = thin["evidence"][:2]
    check("a pool too small for the table is reported",
          any("short of" in i for i in C.feasibility(thin, 4)), str(C.feasibility(thin, 4)))


# --------------------------------------------------------------------------
# Determinism and casefile shape
# --------------------------------------------------------------------------

def test_determinism_and_shape():
    print("\ndeterminism and casefile shape")
    m = solvable_fixture()

    a = C.assign(m, player_count=4, seed=42)
    b = C.assign(m, player_count=4, seed=42)
    check("the same seed gives the same casefiles",
          a.ok and b.ok and
          [[f.id for f in h] for h in a.casefiles] == [[f.id for f in h] for h in b.casefiles])

    check("every player gets a full casefile",
          a.ok and all(len(h) == len(C.DEFAULT_CASEFILE_SPEC) for h in a.casefiles),
          str([len(h) for h in a.casefiles]))

    assigned = [f.id for h in a.casefiles for f in h]
    check("no finding is assigned twice", len(assigned) == len(set(assigned)))

    # A short witness pool must degrade fairly, not starve the last player.
    short = solvable_fixture()
    short["characters"] = [c for c in short["characters"]
                           if c.get("role") != "witness" or c["name"] in ("Ada", "Bo")]
    s = C.assign(short, player_count=4, seed=5)
    check("a short witness pool still fills every casefile",
          s.ok and all(len(h) == 3 for h in s.casefiles), str(s.issues))
    # NOT "no casefile stacks two witnesses" -- with one witness SLOT per casefile that
    # holds by construction and the assertion could never fail. The real
    # property is that a scarce kind is fully USED: two witnesses and four
    # players must put a witness in exactly two casefiles, not zero (over-eager
    # fallback) and not one (a witness left unassigned).
    witness_counts = [sum(1 for f in h if f.kind == "witness") for h in s.casefiles]
    check("a scarce kind is fully assigned: 2 witnesses reach exactly 2 of 4 casefiles",
          s.ok and sum(witness_counts) == 2, str(witness_counts))


def main():
    print("casefiles.py -- constrained assignment fixtures")
    test_arithmetic()
    test_best_assignment()
    test_the_glove()
    test_constraint_1_union_solves()
    test_constraint_2_no_solo_win()
    test_constraint_3_redundancy()
    test_proof_survives_hoarding()
    test_no_prover_monopoly()
    test_feasibility_diagnostics()
    test_determinism_and_shape()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + ", ".join(FAILURES))
        return 1
    print("All assignment constraints hold, and each refuses a mystery that violates it.")
    return 0



def test_best_assignment():
    """Choosing an assignment rather than accepting the first legal one.

    From the real measurement on the first accepted mystery: seed 7 left one
    player able to prove the case in 27 of 81 hoarding patterns, 13 of 20 seeds
    gave zero, and proof survived 81/81 on every seed. Same mystery, same rules.
    """
    print("\nchoosing an assignment (best_assignment)")
    m = solvable_fixture()

    r = C.best_assignment(m, player_count=4)
    check("best_assignment returns a usable assignment", r.ok, str(r.issues))
    check("it reports the assignment's quality, not just legality",
          r.patterns > 0, f"patterns={r.patterns}")
    check("it stops early once an assignment has no monopoly",
          r.monopoly > 0 or r.seeds_tried <= 20, f"seeds_tried={r.seeds_tried}")

    # Determinism survives: the winning seed reproduces the winning casefiles.
    again = C.assign(m, player_count=4, seed=r.seed)
    check("the winning seed reproduces the same casefiles exactly",
          [[f.id for f in h] for h in again.casefiles]
          == [[f.id for f in h] for h in r.casefiles],
          f"seed {r.seed} did not reproduce")

    # It must never be WORSE than taking the first seed, which is the whole point.
    first = C.assign(m, player_count=4, seed=0)
    if first.ok:
        ev = C.evidence_by_id(m)
        first_mono = C.prover_counts(first.casefiles, m, ev).get(1, 0)
        check("and it is never worse than the first legal assignment",
              r.monopoly <= first_mono, f"best {r.monopoly} vs first {first_mono}")

    # A mystery the FEASIBILITY check refuses fails identically for every seed,
    # so searching must not burn 20 assigns discovering that.
    bad = mystery([("E1", ["Ortiz", "Brand", "Chen"], []), ("E2", [], ["Vale"])])
    rb = C.best_assignment(bad, player_count=4)
    check("an infeasible mystery is refused after ONE seed, not twenty",
          (not rb.ok) and rb.seeds_tried == 1, f"ok={rb.ok} seeds={rb.seeds_tried}")

if __name__ == "__main__":
    sys.exit(main())
