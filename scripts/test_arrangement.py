#!/usr/bin/env python3
"""Fixture tests for arrangement.py — the pointer-wiring pass.

WHAT THESE ARE REALLY GUARDING. This tool's only dangerous failure is a FALSE
POSITIVE: wiring a witness to evidence their statement is not about. That
manufactures exactly the drift casefiles.py's docstring warns of ("a model can emit
reveals: ["E3"] on a statement that says nothing about E3, and nothing
structural can tell") -- and every checker would then go green over a lie.

Both false positives below are real ones this tool made during its own first
run, on real generated mysteries. They are the tests because they are the
mistakes:

  1. Scoring on shared vocabulary alone proposed wiring Nadege Fontenot's
     audience sign-in sheet to a witness whose statement is about somebody else
     buying taffy. Shared words: "else", "entire", "general", "show".
  2. Letting the person's name be its own corroboration proposed wiring that
     same alibi to the area holding her MARRIAGE CERTIFICATE. Both mention her;
     one is her alibi and the other is her motive.

A tool that refuses too often costs a cheap targeted call. A tool that wires too
eagerly costs the credibility of every check downstream of it.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import arrangement as A                                # noqa: E402
import gate                                            # noqa: E402
from test_casefiles import mystery                          # noqa: E402
from test_gate_and_ledger import coherent              # noqa: E402

_failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f"\n          {detail}" if detail else ""))
        _failures.append(name)


# Four leads carrying no elimination data. They exist so the pool reaches
# 4 players x 3 findings: without them CASE.POOL_TOO_SMALL fires on every fixture
# here, which is "unplayable" and therefore masks any severity change the wiring
# itself causes. The first version of the severity test passed for exactly that
# reason -- the baseline was already as bad as the outcome.
_FILLER_LEADS = [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", ["E4"])]


def base(witnesses=(), leads=None):
    """Four suspects, three exonerations, one of them (E3/Chen) orphaned."""
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], ["Vale"])]
    m = coherent(mystery(ev, witnesses, _FILLER_LEADS if leads is None else leads))
    for e, text in zip(m["evidence"], [
            "Ferry Manifest. Ortiz boarded the last ferry at nine.",
            "Boiler Room Log. Brand signed the boiler room log at nine.",
            "Lighthouse Duty Roster. Chen kept the lighthouse lamp from eight until midnight.",
            "Torn Receipt. A receipt from the mainland chandlery.",
            "Broken Lantern. A lantern with a cracked mantle.",
            "Ledger Page. A page torn from the harbour ledger."]):
        e["name"], e["description"] = text.split(". ", 1)[0], text
    return m


def test_finds_orphans():
    print("\nfinding the gap")
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry, I sold him the ticket.", ["E1"]),
                        ("Bo", "Brand signed the boiler room log in front of me.", ["E2"])])
    orphans = A.orphaned(m)
    check("an exoneration nothing reveals is found",
          [o[0] for o in orphans] == ["E3"], str(orphans))
    check("an exoneration something DOES reveal is not reported",
          "E1" not in [o[0] for o in orphans])
    check("evidence that exonerates nobody is never an orphan",
          "E4" not in [o[0] for o in orphans])


def test_refuses_when_nobody_names_the_person():
    print("\nrefusing (the important half)")
    # Nobody mentions Chen. This is the delacroix / totality / altheim case, and
    # the honest answer is a targeted ask, not a wiring.
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry, I sold him the ticket.", ["E1"]),
                        ("Bo", "Brand signed the boiler room log in front of me.", ["E2"])])
    p = A.propose(m)[0]
    check("with nobody talking about the suspect, no carrier is proposed",
          not p.actionable, str(p.carrier))
    check("and the reason names the evidence a call would have to write for",
          "E3" in p.reason and "Chen" in p.reason, p.reason)


def test_false_positive_shared_words():
    print("\nthe two false positives it made on real mysteries")
    # A witness about somebody ELSE, sharing only generic vocabulary with E3.
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry from the harbour at nine, "
                                "the lamp was lit and everything else was quiet.", ["E1"]),
                        ("Bo", "Brand signed the boiler room log in front of me.", ["E2"])])
    p = A.propose(m)[0]
    check("shared generic words are NOT enough to wire a pointer",
          not p.actionable,
          f"proposed {p.carrier.label if p.carrier else None} on {p.shared}")

    # Names Chen, but about her MOTIVE, sharing nothing about the duty roster.
    m2 = base(witnesses=[("Ada", "Ortiz boarded the last ferry, I sold him the ticket.", ["E1"]),
                         ("Bo", "Chen stood to inherit the whole chandlery, everyone knew it.",
                          ["E2"])])
    p2 = A.propose(m2)[0]
    check("naming the person is NOT its own corroboration -- motive is not alibi",
          not p2.actionable,
          f"proposed {p2.carrier.label if p2.carrier else None} on {p2.shared}")


def test_wires_a_genuine_carrier():
    print("\nwiring one that earns it")
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry, I sold him the ticket.", ["E1"]),
                        ("Bo", "Brand signed the boiler room log in front of me.", ["E2"]),
                        ("Cy", "Chen kept the lighthouse roster all evening; I read the "
                               "roster myself when I relieved the watch.", [])])
    p = A.propose(m)[0]
    check("a witness who names the person AND is about the object is proposed",
          p.actionable and "Cy" in p.carrier.label,
          f"{p.carrier.label if p.carrier else None} {p.shared}")
    check("and the corroborating word is about the OBJECT, not the person",
          "chen" not in [w.lower() for w in p.shared], str(p.shared))

    applied, withheld = A.apply(m, A.propose(m), "wire.json")
    check("applying it adds the pointer", len(applied) == 1 and not withheld, str(withheld))
    cy = [c for c in m["characters"] if c.get("name") == "Cy"][0]
    check("the pointer is really on the witness", "E3" in (cy.get("reveals") or []),
          str(cy.get("reveals")))
    check("and no generated prose was touched",
          cy["statement"].startswith("Chen kept the lighthouse roster"))


def test_never_makes_the_verdict_worse():
    print("\nthe gate has the last word")
    # One witness who already reveals both other exonerations. Handing them the
    # third makes that single finding clear every innocent -- casefiles.py's
    # constraint 2, and a strictly worse mystery than the one we started with.
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry and Brand signed the boiler "
                                "room log; Chen kept the lighthouse roster, I read the "
                                "roster myself.", ["E1", "E2"]),
                        ("Bo", "Nothing unusual that evening.", ["E4"])])
    proposals = A.propose(m)
    check("the eager carrier IS proposed on lexical grounds",
          proposals and proposals[0].actionable, str(proposals))
    before = len(gate.evaluate(m, "x.json").violations)
    applied, withheld = A.apply(m, proposals, "x.json")
    after = len(gate.evaluate(m, "x.json").violations)
    check("but the gate withholds it, because it would add a violation",
          not applied and withheld, f"applied={len(applied)}")
    check("and the mystery is left exactly as it was", after <= before, f"{before} -> {after}")


def test_world_coverage():
    print("\nworld coverage (the diagnosis, not a gate)")
    m = base(witnesses=[("Ada", "Ortiz boarded the last ferry, I sold him the ticket.", ["E1"]),
                        ("Bo", "Brand signed the boiler room log in front of me.", ["E2"])])
    cov = A.world_coverage(m)
    check("a suspect with a witness is seen to have one",
          len(cov["Ortiz"]["witnesses"]) == 1, str(cov["Ortiz"]))
    check("the suspect nobody mentions shows up bare",
          cov["Chen"]["witnesses"] == [] and cov["Chen"]["areas"] == [], str(cov["Chen"]))
    # The culprit is covered too: this is a diagnosis of the whole cast, and a
    # culprit nobody mentions is its own problem.
    check("the culprit is reported like any other suspect", "Vale" in cov)


if __name__ == "__main__":
    test_finds_orphans()
    test_refuses_when_nobody_names_the_person()
    test_false_positive_shared_words()
    test_wires_a_genuine_carrier()
    test_never_makes_the_verdict_worse()
    test_world_coverage()

    print()
    if _failures:
        print(f"=== {len(_failures)} FAILED ===")
        for f in _failures:
            print(f"    {f}")
        raise SystemExit(1)
    print("=== ALL PASSED ===")
