#!/usr/bin/env python3
"""Fixture tests for gate.py and generation_ledger.py (Session 41, item 18).

WHAT THESE ARE GUARDING. The gate decides whether a generated mystery reaches a
player, and the ledger is the only record of what generation costs. Both are the
kind of code that fails silently: a gate that accepts everything looks exactly
like a gate over a run of good mysteries, and a ledger that drops rows looks
exactly like a quiet week. So the tests below assert the REFUSALS and the
ARITHMETIC, not the happy path alone.

Fixtures are reused from test_casefiles.py rather than rewritten -- they already
encode APF's shape (4 players, 4 suspects, 3 required exonerations) and a second
set drifting from the first is how two checkers come to disagree.
"""

import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import gate                                            # noqa: E402
import generation_ledger as GL                         # noqa: E402
from test_casefiles import mystery, solvable_fixture        # noqa: E402

_failures = []


def coherent(m):
    """Add the fields the COHERENCE engine needs, which the assignment fixtures omit.

    test_casefiles.py's fixtures deliberately carry only what casefiles.py reads -- no
    crime, no victim, no motive -- because the assignment never looks at those. The
    gate runs all three checkers, so an un-enriched fixture fails on eight
    blocking coherence rules and every gate assertion then passes or fails for
    a reason that has nothing to do with what it is testing. (It did: the first
    run of this suite had a legacy test passing because the fixture was broken
    in an unrelated way, which is the failure mode these tests exist to catch.)

    Mutates and returns, so it composes: coherent(solvable_fixture()).
    """
    m.setdefault("crime", {})["what_happened"] = "The keeper was found dead at first light."
    m["characters"] = list(m["characters"]) + [
        {"name": "The Keeper", "role": "victim",
         "secret": "He had been quietly reading other people's letters."}]
    for c in m["characters"]:
        if c.get("role") == "suspect":
            c.setdefault("motive", f"{c['name']} stood to lose everything.")
    m["solution"].setdefault("motive", "A debt nobody was meant to see.")
    m["solution"].setdefault("how_to_deduce", "Rule out the three who could not have been there.")
    m["solution"].setdefault("key_evidence", ["E1", "E2"])
    # Two physical items and one critical: the scene-family minimums.
    for i, e in enumerate(m.get("evidence", [])):
        e.setdefault("type", "physical")
        e.setdefault("relevance", "critical" if i == 0 else "supporting")

    # A CHAIN, AND ONE ITEM THAT SUPPORTS IT. Without this the fixture is not a
    # current-schema mystery, and check_narrative.py skips its entire LINKS
    # branch -- has_links is false, so the narrowing and multi-clear rules never
    # run. Two tests here passed their "is it refused" assertion only because
    # casefiles.py happened to catch the same defect from the other side, which is
    # precisely the blind spot a fixture is supposed to expose rather than share.
    m["solution"].setdefault("chain", [{"id": "S1", "step": "The keeper was killed indoors."}])
    if m.get("evidence"):
        m["evidence"][0].setdefault("supports", ["S1"])
    return m


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)


# ---------------------------------------------------------------------------
# Cost arithmetic
# ---------------------------------------------------------------------------
def test_cost():
    print("\ncost arithmetic")
    # 2,457 in / 8,667 out on claude-sonnet-4-6 is the measurement in
    # docs/AI_COST_PLAYBOOK.md; it must still come out at the documented $0.1374.
    c = GL.cost_usd("claude-sonnet-4-6", 2457, 8667)
    check("the playbook's measured generation still prices at $0.1374",
          c is not None and abs(c - 0.137376) < 1e-6, f"got {c}")
    check("an unknown model prices as None, never as zero",
          GL.cost_usd("some-future-model", 1000, 1000) is None)

    a = GL.Attempt("a prompt")
    a.record_call("generation", "claude-sonnet-4-6", 1000, 1000)
    check("a priced attempt totals its calls",
          a.total_cost is not None and abs(a.total_cost - 0.018) < 1e-9,
          f"got {a.total_cost}")

    a.record_call("localization", "some-future-model", 10, 10)
    check("ONE unpriced call makes the whole attempt unpriced, not partial",
          a.total_cost is None, f"got {a.total_cost}")


# ---------------------------------------------------------------------------
# Ledger I/O
# ---------------------------------------------------------------------------
def test_ledger_io():
    print("\nledger i/o")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "ledger.jsonl"
        GL.append({"attempt_id": "one", "verdict": "accepted", "cost_usd": 0.5}, p)
        GL.append({"attempt_id": "two", "verdict": "rejected", "cost_usd": 0.25}, p)
        rows = GL.load(p)
        check("rows round-trip, oldest first",
              [r["attempt_id"] for r in rows] == ["one", "two"], str(rows))

        # A process killed mid-write leaves a partial line. It must not blind
        # the whole report -- the other rows are still true.
        with open(p, "a", encoding="utf-8") as f:
            f.write('{"attempt_id": "trunc"\n')
        check("a truncated line is skipped, not fatal", len(GL.load(p)) == 2)

    check("a ledger that does not exist yet reads as empty",
          GL.load(Path(d) / "gone.jsonl") == [])


def test_collapse():
    print("\nre-verdicts")
    # Rules here are earned one rejected mystery at a time, so re-running the
    # gate over disk after a rule lands is routine. The re-verdict appends a row
    # and must NOT read as a second attempt -- that would count one mystery
    # twice in the pass rate, and it did on the first run of this session.
    rows = [
        {"slug": "m1", "verdict": "rejected", "cost_usd": 0.20,
         "failure_class": "below_standard", "violations": [{"rule_id": "NARR.SINGLE_ROUTE"}]},
        {"slug": "m1", "verdict": "rejected", "cost_usd": None,
         "failure_class": "unplayable", "violations": [{"rule_id": "CASE.SOLO_SOLVE"}],
         "supersedes": "m1-original"},
    ]
    c = GL.collapse(rows)
    check("two rows for one mystery collapse to one attempt", len(c) == 1, str(c))
    check("the cost survives the collapse, though the re-verdict spent nothing",
          c[0]["cost_usd"] == 0.20, str(c[0].get("cost_usd")))
    check("the NEWEST verdict wins, because the current rules are the real ones",
          c[0]["failure_class"] == "unplayable", str(c[0].get("failure_class")))

    s = GL.summarise(rows)
    check("so the pass-rate denominator counts the mystery once, not twice",
          s["attempts"] == 1 and s["rejected"] == 1, str(s))
    check("and its cost is not counted twice either",
          abs(s["total_cost_usd"] - 0.20) < 1e-9, str(s["total_cost_usd"]))

    check("a row with no slug is never merged into another",
          len(GL.collapse([{"verdict": "accepted"}, {"verdict": "rejected"}])) == 2)


def test_summarise():
    print("\nCPAM arithmetic")
    rows = [
        {"verdict": "accepted", "cost_usd": 0.10, "violations": []},
        {"verdict": "rejected", "cost_usd": 0.30, "failure_class": "unplayable",
         "violations": [{"rule_id": "CASE.SOLO_SOLVE"}]},
        {"verdict": "unjudged", "cost_usd": None, "violations": []},
    ]
    s = GL.summarise(rows)
    check("CPAM divides TOTAL spend by ACCEPTED, so rejects are carried",
          s["cpam_usd"] == 0.4, f"got {s['cpam_usd']}")
    check("pass rate excludes unjudged rows from its denominator",
          s["pass_rate"] == 0.5, f"got {s['pass_rate']}")
    check("unpriced rows are counted and excluded from spend",
          s["unpriced_rows"] == 1 and abs(s["total_cost_usd"] - 0.4) < 1e-9)
    check("rejections are tallied by class and by rule",
          s["by_failure_class"] == {"unplayable": 1}
          and s["by_rule"] == {"CASE.SOLO_SOLVE": 1})
    check("no accepted mysteries leaves CPAM undefined, never zero",
          GL.summarise([rows[1]])["cpam_usd"] is None)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------
def test_gate_accepts_clean():
    print("\nthe gate")
    v = gate.evaluate(coherent(solvable_fixture()), "clean.json")
    check("a mystery that breaks no rule is accepted",
          v.accepted and v.verdict == "accepted", v.summary())
    check("an accepted mystery is destined for generated/",
          v.destination == "generated")


def test_gate_refuses():
    # One finding clearing three innocents: whoever draws it wins alone. This
    # is the_lantern_keeper's_last_light, and the rule it produced.
    ev = [("E1", ["Ortiz", "Brand", "Chen"], []), ("E2", [], ["Vale"])]
    v = gate.evaluate(coherent(mystery(ev)), "solo.json")
    check("a finding that clears every innocent is refused",
          not v.accepted and "NARR.CLEARS_MULTIPLE" in {x["rule_id"] for x in v.violations},
          v.summary())
    check("and it is classed unplayable, not merely below standard",
          v.failure_class == "unplayable", str(v.failure_class))
    check("a rejected mystery is destined for rejected/", v.destination == "rejected")

    # A narrowing clue whose own prose names somebody it leaves possible. This
    # is the_light_that_went_out: every field correct, the answer given away.
    m = coherent(solvable_fixture())
    m["evidence"][7]["narrows"] = ["Vale", "Ortiz"]
    m["evidence"][7]["description"] = "A boot print. Vale wears exactly this size."
    v = gate.evaluate(m, "spoiled.json")
    check("a narrowing clue that names who it leaves possible is refused",
          "NARR.NARROWS_PROSE_NAMES" in {x["rule_id"] for x in v.violations}, v.summary())
    check("and it is classed spoiled_prose",
          v.failure_class == "spoiled_prose", str(v.failure_class))


def test_suspect_count():
    # snow_on_the_engawa came back with THREE suspects against a prompt that says
    # exactly four, and nothing caught it. Three is not a smaller version of the
    # same game: two required exonerations means one finding carrying both solves
    # outright, which is why that mystery could not be assigned.
    m = coherent(mystery([("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", [], ["Vale"])],
                         suspects=("Vale", "Ortiz", "Brand")))
    v = gate.evaluate(m, "three.json")
    check("a three-suspect mystery is refused",
          "CASE.SUSPECT_COUNT" in {x["rule_id"] for x in v.violations}, v.summary())
    check("and four suspects do not trip it",
          "CASE.SUSPECT_COUNT" not in
          {x["rule_id"] for x in gate.evaluate(coherent(solvable_fixture()), "four.json").violations})


def test_gate_worst_class_wins():
    # Trips both an incoherent rule and a below_standard one. The row must be
    # named by the worse of the two, or triage reads it as nearly-good.
    m = coherent(solvable_fixture())
    m["characters"].append({"name": "Zed", "role": "witness",
                            "statement": "s", "reveals": ["E99"]})
    m["evidence"][0]["exonerates"] = ["Ortiz"]
    v = gate.evaluate(m, "mixed.json")
    classes = {x["failure_class"] for x in v.violations}
    check("when several classes fire, the worst one names the row",
          v.failure_class == gate._worst(classes), f"{v.failure_class} from {classes}")


def test_cast_is_advisory():
    # check_narrative.py's own header documents CAST as false-positive-prone and
    # "a list to triage, not a verdict". Gating on it would quarantine good
    # mysteries; dropping it would lose the data. It is recorded, not blocking.
    m = coherent(solvable_fixture())
    m["solution"]["how_to_deduce"] = "Inspector Gullible saw that Vale lied."
    v = gate.evaluate(m, "cast.json")
    advisory_rules = {x["rule_id"] for x in v.advisory}
    check("a person named only in the solution is recorded as advisory",
          "CAST.UNKNOWN_PERSON" in advisory_rules, str(advisory_rules))
    check("and does NOT reject the mystery", v.accepted, v.summary())


def test_legacy_is_unjudged():
    # All 17 mysteries in generated/ predate the exonerates/narrows/reveals
    # schema, so every rule defined over those fields fires on all of them.
    # Judging them would empty the served library on rules that did not exist.
    # Coherent, but carrying none of the Session 38 link fields -- which is
    # exactly the shape of all 17 mysteries in generated/.
    legacy = coherent(mystery([("E1", [], []), ("E2", [], [])]))
    for e in legacy["evidence"]:
        e.pop("exonerates", None)
        e.pop("implicates", None)
    v = gate.evaluate(legacy, "legacy.json", legacy=True)
    check("a legacy mystery is unjudged, not rejected",
          v.verdict == "unjudged", v.summary())
    check("an unjudged mystery stays in generated/", v.destination == "generated")
    check("its findings are still recorded as advisory, so the data survives",
          len(v.advisory) > 0)

    # The one rule that DOES apply retroactively: coherence never depended on
    # the new fields. This is item 18's actual case.
    broken = dict(legacy, solution={"culprit": "Somebody Not In The Cast"})
    v2 = gate.evaluate(broken, "legacy_blocking.json", legacy=True)
    check("but a legacy mystery with a BLOCKING coherence report IS refused",
          v2.verdict == "rejected" and v2.failure_class == "incoherent", v2.summary())


def test_dedupe():
    # casefiles.py and check_narrative.py both implement the narrowing rules. Both
    # are right; counting one defect twice would inflate every by_rule figure.
    m = coherent(solvable_fixture())
    m["evidence"][0]["narrows"] = ["Vale", "Ortiz", "Brand", "Chen"]
    v = gate.evaluate(m, "dupe.json")
    hits = [x for x in v.violations
            if x["rule_id"] == "NARR.NARROWS_ALL" and x["subject_ids"] == ["E1"]]
    check("the same rule on the same subject is recorded once, not twice",
          len(hits) == 1, f"{len(hits)} hits")


def test_verdict_is_json_safe():
    # The verdict is embedded in the saved mystery and written to the ledger,
    # so a dataclass or a set leaking into it would break both writes at once.
    v = gate.evaluate(coherent(solvable_fixture()), "json.json")
    payload = {"verdict": v.verdict, "failure_class": v.failure_class,
               "violations": v.violations, "advisory": v.advisory}
    try:
        json.dumps(payload)
        ok = True
    except TypeError as exc:
        ok, payload = False, str(exc)
    check("every field of a verdict serialises to JSON", ok, str(payload))


if __name__ == "__main__":
    test_cost()
    test_ledger_io()
    test_collapse()
    test_summarise()
    test_gate_accepts_clean()
    test_gate_refuses()
    test_suspect_count()
    test_gate_worst_class_wins()
    test_cast_is_advisory()
    test_legacy_is_unjudged()
    test_dedupe()
    test_verdict_is_json_safe()

    print()
    if _failures:
        print(f"=== {len(_failures)} FAILED ===")
        for f in _failures:
            print(f"    {f}")
        raise SystemExit(1)
    print("=== ALL PASSED ===")
