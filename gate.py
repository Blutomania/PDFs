"""The gate — does this mystery reach a player, and if not, why not.

WHAT CHANGED (Session 41, item 18). Until now the pipeline's behaviour on a bad
generation was identical to its behaviour on a good one: save to
mystery_database/generated/, which `/mysteries` globs directly, and serve it. A
BLOCKING coherence verdict was recorded into `_coherence` and then ignored --
`the_stolen_star_of_smurf_village` sits in generated/ with
`{"passed": false, "blocking": 1}` and is servable today. Meanwhile all four
mysteries in rejected/ PASSED coherence and were carried there by hand.

So the gap was never only "BLOCKING mysteries get served". It was that nothing
routed anything. This module is the routing.

  generated/  now means: no check we own can prove this is broken.
  rejected/   now means: a check we own says it is, and the ledger says which.

WHY THE CHECKS ARE THE RIGHT PLACE AND AUTO-REPAIR IS NOT. A gate can only be
conservative -- it can wrongly refuse a good mystery (annoying, recoverable,
nothing is deleted) but it cannot manufacture a bad one that looks good. A
REPAIR loop can, and would: iterate a model against these checks until they go
green and you stop selecting for good mysteries and start selecting for
mysteries shaped like the checks. the_light_that_went_out is the standing proof
that the checks are not the same as quality -- it passed every structural rule
in this file, assigned cleanly, survived 81/81 hoarding patterns, and gave its
answer away in the prose. Repair-to-green would have shipped it, confidently.

CAST AND ORPHAN ARE ADVISORY, DELIBERATELY. check_narrative.py's own header says
so: extracting people from prose is a heuristic, a mystery may legitimately name
a courier nobody questions, and CAST findings are "a list to triage, not a
verdict". Auto-rejecting on a rule its author documented as false-positive-prone
would quarantine good mysteries and teach everyone to distrust the gate. They
are recorded in the ledger -- so the data is not lost and the rate is visible --
and they do not block. If the false-positive rate turns out to be low once there
are rows to measure, promoting them is a one-line change.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_ROOT = Path(__file__).resolve().parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

import casefiles  # noqa: E402
from check_narrative import RULES, audit_data  # noqa: E402
from coherence_validator import check_mystery  # noqa: E402
from generation_ledger import FAILURE_CLASSES  # noqa: E402

# Recorded, never blocking. See the module docstring.
ADVISORY_RULES = {"CAST.UNKNOWN_PERSON", "CAST.ORPHAN"}

# APF's shape (docs/PLAYTEST_FLOW.md): four players, one witness statement, one
# crime-scene clue and one lead result each. Feasibility is the cheap half of
# casefiles.py -- pure set arithmetic, no assignment attempts, no API call -- so the gate
# can afford to ask it on every generation.
GATE_PLAYER_COUNT = 4


@dataclass
class Verdict:
    verdict: str                                   # accepted | rejected | unjudged
    failure_class: Optional[str]
    violations: List[dict] = field(default_factory=list)
    advisory: List[dict] = field(default_factory=list)
    coherence: Optional[dict] = None

    @property
    def accepted(self) -> bool:
        return self.verdict == "accepted"

    @property
    def destination(self) -> str:
        # "unjudged" stays where it is. Moving a mystery on rules that postdate
        # it would be a retroactive verdict, and there are 17 of them.
        return "rejected" if self.verdict == "rejected" else "generated"

    def summary(self) -> str:
        if self.verdict == "unjudged":
            return f"unjudged (legacy; {len(self.advisory)} advisory finding(s))"
        if self.accepted:
            extra = f" ({len(self.advisory)} advisory)" if self.advisory else ""
            return f"accepted{extra}"
        rules = ", ".join(sorted({v["rule_id"] for v in self.violations}))
        return f"rejected [{self.failure_class}] {rules}"


def _worst(classes) -> Optional[str]:
    """The most serious class present, by FAILURE_CLASSES order.

    An attempt usually trips several rules at once and they are rarely all the
    same kind. The worst one names the row, because that is what somebody
    triaging the queue needs to read first -- and because sorting rejections by
    "incoherent" vs "below_standard" is the difference between "regenerate" and
    "this was nearly good".
    """
    present = set(classes)
    for cls in FAILURE_CLASSES:
        if cls in present:
            return cls
    return None


def _dedupe(violations: List[dict]) -> List[dict]:
    """One row per (rule, subject), keeping first-seen order.

    check_narrative.py and casefiles.py independently implement five of the same
    fair-play rules, so a mystery that narrows to every suspect trips
    NARR.NARROWS_ALL twice -- once from each. Both are correct; counting the
    defect twice would quietly inflate every by_rule figure the ledger produces,
    which is the one thing this data exists to get right.

    NOT keyed on the message: the two files word the same rule differently, so
    matching prose would never collapse anything. It is keyed on rule plus
    subject, which is exactly why casefiles.py's issues carry subject ids at all --
    without them "E1 narrows to everybody" from one file and the same finding
    from the other look like two separate defects.
    """
    seen = set()
    out = []
    for v in violations:
        key = (v["rule_id"], tuple(v.get("subject_ids") or ()))
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def evaluate(mystery: dict, name: str = "<memory>", legacy: bool = False) -> Verdict:
    """Decide whether this mystery may be served. Free — no API call.

    LEGACY MYSTERIES ARE JUDGED ON COHERENCE ONLY, and the reason is not
    politeness. All 17 mysteries in generated/ predate Session 38's schema: none
    carries `exonerates`, `narrows` or `reveals`, so every rule defined over
    those fields fires trivially on all of them -- run the full gate over disk
    and it rejects the entire served library, emptying the browse list to prove
    a point about rules that did not exist when those files were written.

    Coherence is the exception because it never depended on the new fields: it
    has run on every mystery ever generated, and its verdicts on these files
    were recorded at the time. So a legacy mystery with a BLOCKING coherence
    report IS refused -- which is item 18's actual case,
    the_stolen_star_of_smurf_village, and it is the only file on disk that moves.

    check_narrative and assignment still run on legacy mysteries and their findings are
    still recorded, as advisory. The data is worth having; the retroactive
    verdict is not.
    """
    violations: List[dict] = []
    advisory: List[dict] = []

    # --- 1. Coherence: the engine already emits structured IDs, so they are
    # carried through unchanged rather than re-labelled. Only BLOCKING issues
    # gate; warnings are recorded by the caller in the row's coherence field.
    report = check_mystery(mystery)
    coherence = {
        "passed": report.passed,
        "blocking": report.blocking_count,
        "warnings": report.warning_count,
    }
    for issue in getattr(report, "issues", []) or []:
        if not issue.is_blocking:
            continue
        violations.append({
            "rule_id": issue.code or "COH.UNKNOWN",
            "failure_class": "incoherent",
            "subject_ids": [],
            "message": issue.message,
            # The engine already writes the fix; carrying it into the ledger is
            # free and is exactly the field a future repair pass would read.
            "repair_hint": issue.repair_hint or "",
        })

    # --- 2. Narrative: the story hangs together and the game can be won.
    # On a legacy mystery these are recorded but never blocking (see docstring).
    narrative = audit_data(mystery, name)
    for v in narrative["violations"]:
        blocking = not legacy and v["rule_id"] not in ADVISORY_RULES
        (violations if blocking else advisory).append(v)

    # --- 3. Assignment feasibility: reasons this can never be assigned at APF's shape.
    # feasibility_issues() is the cheap structural half -- pure set arithmetic,
    # no assignment attempts -- and since Session 41 it names its rules, so the
    # overlap with the narrative checker deduplicates below instead of counting
    # one defect twice.
    try:
        (advisory if legacy else violations).extend(
            casefiles.feasibility_issues(mystery, GATE_PLAYER_COUNT))
    except Exception as exc:                       # noqa: BLE001
        # A raise here is itself a refusal to assignment, and the reason belongs in
        # the ledger rather than in a traceback that kills the generation.
        (advisory if legacy else violations).append({
            "rule_id": "CASE.ERROR",
            "failure_class": "unplayable",
            "subject_ids": [],
            "message": f"{type(exc).__name__}: {exc}",
        })

    violations = _dedupe(violations)
    if violations:
        verdict = "rejected"
    elif legacy:
        verdict = "unjudged"
    else:
        verdict = "accepted"
    return Verdict(
        verdict=verdict,
        failure_class=_worst(v["failure_class"] for v in violations) if violations else None,
        violations=violations,
        advisory=_dedupe(advisory),
        coherence=coherence,
    )
