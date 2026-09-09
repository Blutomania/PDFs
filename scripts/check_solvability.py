#!/usr/bin/env python3
"""Audit the structural link between a mystery's evidence and its solution.

docs/INVESTIGATION_DESIGN.md section 4 proposes a free interim check: parse the
evidence IDs out of `how_to_deduce` and confirm they COVER `key_evidence` -- on
the reasoning that an item the solution never mentions is not load-bearing and
should not be listed as key.

Run against all 17 generated mysteries on disk, that check passes everywhere.
Zero mysteries list a key item the reasoning ignores. The interesting failure is
the OTHER direction, and it is present in 16 of 17:

    the reasoning cites evidence that key_evidence does not contain.

Up to six items per mystery, a mean of about three. That matters more than the
direction section 4 proposed, because APF's constrained assignment is specified over
"the evidence that proves the case". If that set is read from `key_evidence`,
the assignment can casefile a player every key item and still not give them what the
solution's own reasoning uses. The assignment would satisfy its constraints and the
player still could not get there.

So this script reports both directions and treats the second as the real one.

It also reports two things needed before section 4's `exonerates` field can be
added, because both bound what that field can do:

  * How many suspects there are. Eliminating down to one needs S-1 exonerations,
    so S sets how many findings can be provably load-bearing -- and therefore
    how many players can hold one. Generation currently produces 2-3 suspects
    while docs/PLAYTEST_FLOW.md specifies four.
  * Whether the reasoning names the non-culprit suspects at all. `exonerates` asks
    generation to state elimination as data; that is cheap if the prose already
    reasons that way and expensive if it does not.

Zero API cost -- it reads what is already on disk.

Usage:  python3 scripts/check_solvability.py [--verbose]
Exit:   0 always. This is a report, not a gate: nothing here is a defect in a
        mystery, it is a measurement of what generation currently produces.
"""

import argparse
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "mystery_database" / "generated"

EVIDENCE_ID = re.compile(r"\bE\d+\b")
ELIMINATION = re.compile(
    r"rules? out|ruled out|eliminat|exonerat|could not have|cannot have|"
    r"accounted for|alibi", re.I)


def _name_parts(name: str) -> list:
    """Words worth matching on. Titles and initials are too short to be evidence
    that a particular person was named."""
    return [p.strip(".,") for p in re.split(r"\s+", name or "")
            if len(p.strip(".,")) > 2 and p not in ("Dr.", "Mr.", "Mrs.", "Ms.")]


def _mentions(name: str, text: str) -> bool:
    return any(part in text for part in _name_parts(name))


def audit(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    solution = data.get("solution") or {}
    reasoning = solution.get("how_to_deduce") or ""
    culprit = solution.get("culprit") or ""

    evidence_ids = {e["id"] for e in (data.get("evidence") or [])
                    if isinstance(e, dict) and "id" in e}
    key = set(solution.get("key_evidence") or [])
    cited = set(EVIDENCE_ID.findall(reasoning))

    suspects = [c.get("name", "") for c in (data.get("characters") or [])
                if isinstance(c, dict) and c.get("role") == "suspect"]
    # Elimination is about everyone who is NOT the answer.
    others = [s for s in suspects if not _mentions(s, culprit)]

    return {
        "file": path.name,
        "suspects": len(suspects),
        "others": len(others),
        "others_named": [s for s in others if _mentions(s, reasoning)],
        "key_not_cited": sorted(key - cited),
        "cited_not_key": sorted(cited - key),
        "dangling": sorted(cited - evidence_ids),
        "key_missing": sorted(key - evidence_ids),
        "elimination_phrases": len(ELIMINATION.findall(reasoning)),
        "reasoning_chars": len(reasoning),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verbose", action="store_true",
                    help="list the individual evidence IDs behind each count")
    args = ap.parse_args()

    files = [Path(f) for f in sorted(glob.glob(str(GENERATED / "*.json")))
             if "batch_summary" not in Path(f).name]
    if not files:
        print(f"No generated mysteries found in {GENERATED}.")
        return 0

    reports = [audit(f) for f in files]

    print(f"{'mystery':38s} {'sus':>3s} {'key¬cit':>7s} {'cit¬key':>7s} "
          f"{'dangl':>5s} {'named':>7s} {'elim':>4s}")
    print("-" * 78)
    for r in reports:
        named = f"{len(r['others_named'])}/{r['others']}"
        print(f"{r['file'][:38]:38s} {r['suspects']:3d} "
              f"{len(r['key_not_cited']):7d} {len(r['cited_not_key']):7d} "
              f"{len(r['dangling']):5d} {named:>7s} {r['elimination_phrases']:4d}")
        if args.verbose:
            for label, ids in (("key not cited", r["key_not_cited"]),
                               ("cited not key", r["cited_not_key"]),
                               ("dangling", r["dangling"]),
                               ("key not in evidence[]", r["key_missing"])):
                if ids:
                    print(f"{'':38s}   {label}: {', '.join(ids)}")

    n = len(reports)
    print("-" * 78)
    print("\nColumns")
    print("  key¬cit  key_evidence the reasoning never mentions "
          "(section 4's proposed check)")
    print("  cit¬key  evidence the reasoning USES that key_evidence omits "
          "(the real gap)")
    print("  dangl    evidence IDs cited that do not exist in evidence[]")
    print("  named    non-culprit suspects the reasoning names, of how many exist")
    print("  elim     count of elimination phrases in the reasoning\n")

    key_gap = sum(1 for r in reports if r["key_not_cited"])
    cite_gap = [r for r in reports if r["cited_not_key"]]
    dangling = sum(1 for r in reports if r["dangling"])
    missing = sum(1 for r in reports if r["key_missing"])
    named_tot = sum(len(r["others_named"]) for r in reports)
    others_tot = sum(r["others"] for r in reports)
    thin = [r for r in reports if r["suspects"] < 4]

    print(f"  {key_gap}/{n} list a key item the reasoning never mentions.")
    if cite_gap:
        extra = sum(len(r["cited_not_key"]) for r in cite_gap)
        print(f"  {len(cite_gap)}/{n} cite evidence the key list omits "
              f"-- {extra} items, up to "
              f"{max(len(r['cited_not_key']) for r in cite_gap)} in one mystery.")
        print("     APF's assignment is specified over the evidence that proves the "
              "case. Read that\n     from key_evidence and it is short by these.")
    print(f"  {dangling}/{n} cite an evidence ID that does not exist.")
    print(f"  {missing}/{n} list key evidence absent from evidence[] "
          f"(what P1.C5 really means).")
    if others_tot:
        print(f"  {named_tot}/{others_tot} non-culprit suspects "
              f"({100 * named_tot // others_tot}%) are named in the reasoning "
              f"-- so elimination\n     is mostly already being written as prose, "
              f"and `exonerates` would formalise it\n     rather than ask for "
              f"something new.")
    print(f"  {len(thin)}/{n} have fewer than the four suspects "
          f"docs/PLAYTEST_FLOW.md specifies.")
    print("     READ THAT CAREFULLY BEFORE CONCLUDING ANYTHING. The prompt rule")
    print("     'EXACTLY 4 suspects' was added 2026-08-21; almost every mystery on")
    print("     disk was generated in March under the older prompt and predates it.")
    print("     The one generation made under the current prompt has exactly 4. So")
    print("     this is a corpus-age artefact, not evidence that generation ignores")
    print("     the spec -- re-measure after the next few generations.")
    print("     The arithmetic still matters either way: eliminating to one needs")
    print("     S-1 exonerations, so S bounds how many findings can be provably")
    print("     load-bearing, and therefore how many players can hold one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
