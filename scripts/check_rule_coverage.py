#!/usr/bin/env python3
"""Every hard assertion in the generation prompt — and what, if anything, enforces it.

WHY THIS EXISTS, AND WHAT IT COST NOT TO HAVE IT. The generation prompt has said
"EXACTLY 4 suspects" since it was written. casefiles.py's entire constraint arithmetic
is derived from four. Nothing checked it, and `snow_on_the_engawa` came back with
three — which is not a smaller version of the same game but a different one, since
two required exonerations means any finding carrying both solves outright. That
cost a paid generation to discover, by accident.

It is a shape, not an incident. Three kinds of broken rule exist here, and one
session produced all three:

  INERT            declared somewhere, reachable from nothing.
                   Mechanically findable. Currently: none in the rule system.
  UNENFORCED       the prompt asserts it; no rule checks it.
                   THIS FILE. The "EXACTLY 4 suspects" shape.
  WRONGLY MEASURED a rule exists, runs, passes, and measures the wrong thing.
                   Not findable from here — a narrowing rule counted list entries
                   instead of suspects, and a prose check compared full names
                   while the model wrote first names. Both were GREEN. Both cost
                   a generation. Only reading finds these.

WHAT THIS CHECKS, all free and offline:

  1. Every assertion in the inventory below still appears in the prompt. If a
     line is reworded or deleted, its entry is stale and must be re-triaged
     rather than silently kept.
  2. Every rule id the inventory names really exists in a live registry. A
     renamed rule leaves a claim of coverage that no longer holds.
  3. Every imperative line in the prompt is accounted for by some entry. Adding
     a MUST to the prompt without saying what enforces it fails this check --
     which is the whole point: you cannot quietly add an unenforced rule.

The output's standing value is the UNENFORCED list. It is not a bug list; some
of those are deliberate (a witness statement's truthfulness cannot be checked by
any structural rule) and are marked so. What matters is that the list is
explicit, reviewed, and cannot grow by accident.
"""

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

from check_narrative import RULES as NARRATIVE_RULES        # noqa: E402
from casefiles import FEASIBILITY_RULES                          # noqa: E402

PROMPT_FILE = _ROOT / "server" / "main.py"
PROMPT_START = "QUALITY REQUIREMENTS"
PROMPT_END = '"culprit": "string'

# Every imperative in the generation prompt. `match` is a distinctive substring
# rather than a line hash: cosmetic rewording should not fail the check, but
# deleting or materially rewriting an assertion should.
#
#   enforced      a rule refuses a mystery that breaks it
#   advisory      a rule reports it but never blocks (see gate.ADVISORY_RULES)
#   unenforceable no structural rule could check it, with the reason
#   UNENFORCED    the gap. asserted to the model and nothing verifies it
ASSERTIONS = [
    ("header", "QUALITY REQUIREMENTS", "header", None),

    ("suspect-count", "EXACTLY 4 suspects", "enforced", ["CASE.SUSPECT_COUNT"]),
    ("witness-count", "3–4 witnesses", "UNENFORCED",
     "no rule counts witnesses. A mystery with one witness still assigns, but APF's "
     "casefile spec wants one witness statement per player"),

    ("alibi-specific", "alibi: SPECIFIC", "advisory", ["parts.alibi.testimonial_only",
                                                      "parts.alibi.no_physical_anchor"]),
    ("motive-specific", "motive (suspects): specific stake", "advisory", ["parts.motive.too_vague"]),
    ("statement-actionable", "It must be ACTIONABLE", "UNENFORCED",
     "no rule reads a statement for actionability"),
    ("statement-not-atmosphere", "Never atmosphere alone", "UNENFORCED",
     "same gap as statement-actionable"),
    ("witness-truthful", "must not invent, deny or conceal", "unenforceable",
     "whether a statement is TRUE cannot be decided structurally -- that is the "
     "reason deception is switched off in this build rather than checked"),
    ("witness-group-balance", "at least one statement must point toward the culprit",
     "UNENFORCED", "nothing checks the witness group's balance"),

    ("narrowing-is-a-class", "A NARROWING MUST BE A CLASS OF PERSON", "enforced",
     ["NARR.NARROWS_PROSE_NAMES"]),
    ("witness-reveals", "EVERY witness must reveal at least one", "enforced",
     ["REVEAL.NO_POINTER"]),

    ("evidence-count", "at least 9 items total", "advisory", ["scene.evidence.too_few_total"]),
    ("culprit-implicated", "implicates: names of suspects this item points AT", "enforced",
     ["NARR.NOBODY_IMPLICATED"]),

    ("narrowing-true", "IT MUST BE TRUE", "enforced", ["NARR.NARROWS_EXCLUDES_CULPRIT"]),
    ("narrowing-fair", "must not lose for it", "enforced", ["NARR.NARROWS_EXCLUDES_CULPRIT"]),
    ("narrowing-checkable", "must be checkable against the cast", "enforced",
     ["NARR.NARROWS_STRANGER"]),

    ("elimination-leaves-one", "the suspects exonerated must be every suspect EXCEPT", "enforced",
     ["NARR.ELIMINATION_NOT_ONE"]),
    ("never-exonerate-culprit", "Never exonerate the culprit", "enforced",
     ["NARR.CULPRIT_EXONERATED"]),
    ("two-routes", "TWO INDEPENDENT ROUTES", "enforced", ["NARR.SINGLE_ROUTE"]),
    ("chain-supported", "Every chain step must appear in at least one", "enforced",
     ["NARR.STEP_UNSUPPORTED"]),
    ("reachable", "REACHABLE: every evidence item that exonerates", "enforced",
     ["REVEAL.UNREACHED_EXONERATION"]),
    ("whole-proof", "MAY CARRY A WHOLE PROOF", "enforced", ["CASE.SOLO_SOLVE"]),
    ("witness-covers-suspect", "ASSIGN EACH WITNESS A SUSPECT", "UNENFORCED",
     "arrangement.world_coverage() reports it but nothing gates on it -- this is "
     "the rule that fixed the two-routes problem and it is enforced only by its "
     "downstream effect (NARR.SINGLE_ROUTE), not directly"),

    ("key-evidence-count", "key_evidence must list at least 2", "enforced",
     ["P1.C5.no_key_evidence", "P1.C5.dangling_key_evidence"]),
    ("chain-step-reachable", "Each step must be a claim a player could actually reach",
     "UNENFORCED", "no rule judges whether a step is reachable from its evidence"),
    ("step-supported", "Every step must be supported by at least one evidence item",
     "enforced", ["NARR.STEP_UNSUPPORTED"]),
    ("how-to-deduce", "how_to_deduce: the same reasoning as readable prose", "enforced",
     ["P1.C5.no_deduction_path"]),
    ("culprit-in-cast", 'The culprit named here must appear in "characters"', "enforced",
     ["P1.C4.culprit_not_in_characters", "CASE.CULPRIT_NOT_SUSPECT"]),

    ("areas-distinct", "Each area must be atmospherically distinct", "UNENFORCED",
     "no rule judges atmosphere"),
    ("areas-yield", "Every area must yield something", "UNENFORCED",
     "REVEAL.NO_POINTER covers an area with no reveals pointer, but not one whose "
     "discovery text is empty"),
    ("areas-narrow", "At least 2 areas must yield a discovery+analysis pair", "UNENFORCED",
     "FOUND BY THIS CHECKER ON ITS FIRST RUN, which is the point of it. Nothing "
     "counts how many areas genuinely narrow the suspect list; an area that "
     "yields atmosphere satisfies REVEAL.NO_POINTER as long as it points at "
     "some evidence item"),
    ("area-red-herring", "must be a red herring that looks incriminating", "advisory",
     ["scene.red_herring.missing", "scene.red_herring.testimonial_only"]),
    ("area-reveals", "EVERY area must reveal at", "enforced", ["REVEAL.NO_POINTER"]),

    ("leads-actionable", "Each lead must be specific and actionable", "UNENFORCED",
     "no rule judges a lead's specificity"),
    ("lead-balance", "At least 1 lead should point toward the culprit", "UNENFORCED",
     "nothing checks the lead group's balance"),
    ("lead-reveals", "the ids of the evidence items following this lead turns up", "enforced",
     ["REVEAL.NO_POINTER"]),
]

IMPERATIVE = re.compile(
    r'\b(MUST|EXACTLY|NEVER|Never|must not|must be|must appear|must reveal|must list'
    r'|must yield|at least|no more than|EVERY|Every)\b')


def live_rule_ids():
    ids = set(NARRATIVE_RULES) | set(FEASIBILITY_RULES)
    ids |= set(re.findall(r'code="([A-Za-z0-9_.]+)"',
                          (_ROOT / "coherence_validator.py").read_text(encoding="utf-8")))
    return ids


def prompt_lines():
    """The prompt's assertions, one per BULLET rather than one per source line.

    A long assertion wraps across several lines, and checking lines
    independently makes every continuation look like an assertion nobody has
    inventoried -- the first run of this checker reported four such phantoms.
    A new assertion starts at a bullet, a numbered item, or a shouted heading;
    anything else continues the one above it.
    """
    src = PROMPT_FILE.read_text(encoding="utf-8")
    i = src.index(PROMPT_START)
    j = src.index(PROMPT_END, i)
    raw = [ln.strip() for ln in src[i:j].splitlines() if ln.strip()]

    starts_new = re.compile(r'^([-*•]|\d+[.)]|[A-Z][A-Z0-9 ,\'"()/-]{6,}[:.]?$|[A-Z]{2,}[ (])')
    grouped = []
    for ln in raw:
        if grouped and not starts_new.match(ln):
            grouped[-1] += " " + ln
        else:
            grouped.append(ln)
    return grouped


def main():
    lines = prompt_lines()
    blob = "\n".join(lines)
    known = live_rule_ids()
    failures = []

    # --- 1. every inventory entry still present in the prompt ---
    stale = [slug for slug, match, _, _ in ASSERTIONS if match not in blob]
    for slug in stale:
        failures.append(f"STALE     '{slug}' is in the inventory but no longer in the prompt")

    # --- 2. every named rule id exists ---
    for slug, _, status, detail in ASSERTIONS:
        if status in ("enforced", "advisory"):
            for rid in detail or []:
                if rid not in known:
                    failures.append(f"MISSING   '{slug}' claims {rid}, which is not a live rule id")

    # --- 3. every imperative line is accounted for ---
    matches = [m for _, m, _, _ in ASSERTIONS]
    unaccounted = [ln for ln in lines
                   if IMPERATIVE.search(ln) and not any(m in ln for m in matches)]
    for ln in unaccounted:
        failures.append(f"NEW       an assertion nothing in the inventory covers:\n"
                        f"            {ln[:96]}")

    # --- report ---
    by_status = {}
    for slug, _, status, detail in ASSERTIONS:
        by_status.setdefault(status, []).append((slug, detail))

    print(f"  {len(ASSERTIONS)} assertions inventoried against {len(known)} live rule ids\n")
    for status in ("enforced", "advisory", "unenforceable", "UNENFORCED"):
        items = by_status.get(status, [])
        if not items:
            continue
        print(f"  {status.upper()}  ({len(items)})")
        for slug, detail in items:
            if status in ("enforced", "advisory"):
                print(f"     {slug:<26} {', '.join(detail)}")
            else:
                print(f"     {slug:<26} {detail}")
        print()

    if failures:
        print("-" * 78)
        for f in failures:
            print(f"  {f}")
        print(f"\n=== {len(failures)} COVERAGE PROBLEM(S) ===")
        return 1

    gaps = len(by_status.get("UNENFORCED", []))
    print("-" * 78)
    print(f"=== inventory is current: every assertion accounted for, every rule id live ===")
    print(f"    {gaps} assertion(s) stand UNENFORCED and are listed above, deliberately.")
    print("    This check fails if the prompt gains an assertion nobody has triaged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
