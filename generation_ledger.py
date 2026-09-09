"""The generation ledger — what each attempt cost, what happened to it, and why.

WHY THIS EXISTS. Until Session 41 the pipeline threw away every token count it
was handed. There is exactly one Claude call site in the server (`llm()` in
server/main.py) and nothing read `response.usage`, so the only cost figure the
project had was a hand measurement of one August generation, recorded in
docs/AI_COST_PLAYBOOK.md. Four mysteries were generated and rejected after that
measurement and **what they cost is unrecoverable** — the money was spent and
the number was not written down.

That matters more than bookkeeping, for two reasons the owner named:

  COST PER ACCEPTED MYSTERY (CPAM) is the number that decides whether moving off
  a frontier model is worth it. Cost per *call* is the tempting metric and it is
  the wrong one: a model at a third the price with a third the pass rate is a
  wash. CPAM cannot be computed retroactively, so it has to start being recorded
  before the question is asked, not when it is.

  THE REJECTED ROWS ARE A DATASET. Every rejection so far taught the prompt a
  rule (a finding clears at most one suspect; every innocent needs two routes; a
  narrowing must exclude somebody; a narrowing's prose must not name who it
  leaves possible). That loop currently runs on a human reading checker output.
  Recording the failure class, the rule IDs and the offending evidence IDs is
  what turns an archive into something a future pass could learn from.

DELIBERATELY NOT A DATABASE. One append-only JSONL file: it diffs cleanly in
git, greps without tooling, survives a merge, and is already the format a
fine-tune would want. Rows are never edited or deleted — a re-verdict appends a
new row referencing the old attempt_id.

ON UNPRICED CALLS. Prices below cover only models this repo actually calls and
whose pricing is recorded in docs/AI_COST_PLAYBOOK.md. An unknown model records
its token counts with `cost_usd: null` rather than a guess, and `scripts/cpam.py`
reports how many rows are unpriced. A guessed number in a ledger that may end up
in front of an investor is worse than an honest gap.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = _ROOT / "mystery_database" / "ledger.jsonl"

# USD per million tokens, (input, output). Source: docs/AI_COST_PLAYBOOK.md,
# measured 21 August 2026. A model absent from this table is recorded with
# cost_usd null rather than estimated -- see the module docstring.
PRICES: Dict[str, tuple] = {
    "claude-sonnet-4-6": (3.00, 15.00),
}

# Ordered worst-first. When an attempt trips rules in several classes the worst
# one names it, because that is the one a person triaging the queue must read.
FAILURE_CLASSES = ("incoherent", "unplayable", "spoiled_prose", "below_standard")


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Dollar cost of one call, or None when the model's price is not known."""
    price = PRICES.get(model)
    if price is None:
        return None
    per_in, per_out = price
    return round((input_tokens * per_in + output_tokens * per_out) / 1_000_000, 6)


class Attempt:
    """One generation attempt, accumulating calls until it is written.

    An attempt spans every call the pipeline makes for a single mystery --
    generation, localization, narration -- because CPAM is per mystery, not per
    call. Localization is skipped for modern settings and narration is optional,
    so the call list is genuinely variable and has to be recorded rather than
    assumed.
    """

    def __init__(self, prompt: str, attempt_id: Optional[str] = None):
        self.attempt_id = attempt_id or uuid.uuid4().hex[:12]
        self.prompt = prompt
        self.started = time.time()
        self.calls: List[dict] = []

    def record_call(self, purpose: str, model: str,
                    input_tokens: int, output_tokens: int) -> None:
        self.calls.append({
            "purpose": purpose,
            "model": model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": cost_usd(model, input_tokens, output_tokens),
        })

    @property
    def total_cost(self) -> Optional[float]:
        """None if ANY call is unpriced -- a partial total would read as a full one."""
        if not self.calls:
            return 0.0
        if any(c["cost_usd"] is None for c in self.calls):
            return None
        return round(sum(c["cost_usd"] for c in self.calls), 6)

    def row(self, *, slug: str, verdict: str, failure_class: Optional[str],
            violations: Sequence[dict], coherence: Optional[dict],
            destination: str) -> dict:
        return {
            "attempt_id": self.attempt_id,
            "timestamp": int(self.started),
            "elapsed_s": round(time.time() - self.started, 1),
            "prompt": self.prompt,
            "slug": slug,
            "calls": list(self.calls),
            "cost_usd": self.total_cost,
            "coherence": coherence,
            "verdict": verdict,
            "failure_class": failure_class,
            "violations": [dict(v) for v in violations],
            "destination": destination,
        }


def append(row: dict, path: Path = LEDGER_PATH) -> None:
    """Append one row. Never rewrites; the file is the record, not a cache."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True)
    # Opened per append rather than held: generation runs in a background thread
    # (server/main.py's async job path) and a long-lived handle would outlive it.
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def load(path: Path = LEDGER_PATH) -> List[dict]:
    """Every row, oldest first. A malformed line is skipped, not fatal --
    a half-written row from a killed process must not blind the whole report."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def collapse(rows: Sequence[dict]) -> List[dict]:
    """One row per mystery for counting, newest verdict wins, cost carried forward.

    WHY THIS EXISTS. Rules in this project are earned one rejected mystery at a
    time, so re-running the gate over disk after a rule lands is routine. Each
    re-verdict appends a row (the file is append-only and the original stays
    exactly as written) -- but a re-verdict is NOT a second attempt, and counting
    it as one would inflate the pass-rate denominator with the same mystery
    twice, which is precisely the kind of quiet double-count this data exists to
    avoid.

    So: group by slug, take the LATEST verdict and violations (the current rules
    are the ones worth counting), and carry the cost from whichever row in the
    group actually has one -- the original attempt, since a re-verdict spends
    nothing. Rows with no slug stand alone.
    """
    by_slug: Dict[str, dict] = {}
    out: List[dict] = []
    for r in rows:
        slug = r.get("slug")
        if not slug:
            out.append(r)
            continue
        prior = by_slug.get(slug)
        if prior is None:
            by_slug[slug] = dict(r)
            continue
        merged = dict(r)
        if merged.get("cost_usd") is None and prior.get("cost_usd") is not None:
            merged["cost_usd"] = prior["cost_usd"]
            merged["calls"] = prior.get("calls") or []
        by_slug[slug] = merged
    return out + list(by_slug.values())


# Rule ids that have been renamed, old -> new. Rows already on disk carry the
# OLD id and are never rewritten -- the ledger is an append-only record of what
# actually happened, and editing history to match today's vocabulary is exactly
# what SESSIONS.md forbids for the same reason. So the ids are folded at READ
# time instead, which keeps a rule's whole history under one heading.
#
# Session 42 renamed DEAL.* to CASE.* when the card-game vocabulary came out of
# the codebase (the owner's third time asking). 45 rows across five rules were
# already written; without this they would have split into two columns naming
# the same defect.
LEGACY_RULE_IDS = {
    "DEAL.NO_SUSPECTS":            "CASE.NO_SUSPECTS",
    "DEAL.SUSPECT_COUNT":          "CASE.SUSPECT_COUNT",
    "DEAL.NO_CULPRIT":             "CASE.NO_CULPRIT",
    "DEAL.CULPRIT_NOT_SUSPECT":    "CASE.CULPRIT_NOT_SUSPECT",
    "DEAL.EXONERATES_STRANGER":    "CASE.EXONERATES_STRANGER",
    "DEAL.POOL_UNSOLVABLE":        "CASE.POOL_UNSOLVABLE",
    "DEAL.REDUNDANCY_CEILING":     "CASE.REDUNDANCY_CEILING",
    "DEAL.REDUNDANCY_UNREACHABLE": "CASE.REDUNDANCY_UNREACHABLE",
    "DEAL.SOLO_SOLVE":             "CASE.SOLO_SOLVE",
    "DEAL.POOL_TOO_SMALL":         "CASE.POOL_TOO_SMALL",
}


def _current_rule_id(rule_id: str) -> str:
    """Fold a historical rule id onto the id that rule has today."""
    return LEGACY_RULE_IDS.get(rule_id, rule_id)


def summarise(rows: Sequence[dict]) -> dict:
    """CPAM and the numbers around it.

    CPAM is total spend divided by ACCEPTED mysteries, not by attempts. That is
    the whole point: rejected generations are a real cost of every accepted one,
    and a metric that hides them makes a cheap unreliable model look good.
    """
    rows = collapse(rows)
    accepted = [r for r in rows if r.get("verdict") == "accepted"]
    rejected = [r for r in rows if r.get("verdict") == "rejected"]
    unjudged = [r for r in rows if r.get("verdict") == "unjudged"]
    priced = [r for r in rows if r.get("cost_usd") is not None]
    unpriced = len(rows) - len(priced)

    total = round(sum(r["cost_usd"] for r in priced), 6) if priced else 0.0
    cpam = round(total / len(accepted), 4) if accepted else None

    # OVER JUDGED ROWS ONLY. The 16 legacy mysteries were never put to the gate
    # -- they predate the rules -- so counting them as failures would report a
    # 0% pass rate for a pipeline that has simply not been measured yet. A
    # denominator that quietly includes unmeasured rows is how a metric starts
    # lying before anyone has read it twice.
    judged = len(accepted) + len(rejected)

    by_class: Dict[str, int] = {}
    by_rule: Dict[str, int] = {}
    for r in rejected:
        cls = r.get("failure_class") or "unclassified"
        by_class[cls] = by_class.get(cls, 0) + 1
        for v in r.get("violations") or []:
            rid = _current_rule_id(v.get("rule_id", "?"))
            by_rule[rid] = by_rule.get(rid, 0) + 1

    return {
        "attempts": len(rows),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "unjudged": len(unjudged),
        "pass_rate": round(len(accepted) / judged, 3) if judged else None,
        "total_cost_usd": total,
        "unpriced_rows": unpriced,
        "cpam_usd": cpam,
        "by_failure_class": by_class,
        "by_rule": by_rule,
    }
