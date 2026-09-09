"""The arrangement pass — find exonerations nothing reveals, and wire them if honest.

THE DEFECT THIS EXISTS FOR, MEASURED RATHER THAN GUESSED. Three generations in a
row failed the two-routes rule, and in all three the short suspect's exoneration
was *exactly* the one no witness, lead or area pointed at:

    the_last_night_of_delacroix_&_sons   Nadège 1, Rémy 10, Sylvain 5   E6 orphaned
    the_vanishing_at_altheim_peak        Adachi 1, Solberg 4, Novák 2   E11 orphaned
    totality                             Luz    1, Fenwick 4, Sable 4   E10 orphaned

Nobody is short of CLUES -- everyone else has four to ten routes. Exactly one
person has exactly one, every time, and it is always the person whose clue is
unwired. So `NARR.SINGLE_ROUTE` and `REVEAL.UNREACHED_EXONERATION` are not two
failures; they are one defect seen from two sides.

INVENTION VERSUS ARRANGEMENT (Session 40's axis, applied). Writing the clue is
invention and only a model can do it. Deciding that a witness should point at it
is arrangement, and arrangement is set arithmetic: free, deterministic, and
re-runnable. This module does the arrangement half only.

REPAIR THE ARRANGEMENT, NEVER THE EVIDENCE. That is the line, and it is narrower
than it sounds. Wiring an existing witness to an existing clue completes
something the schema requires and the model forgot, and a person can read the
statement and check it. Rewriting a clue's prose until a leak detector stops
firing is optimising against the checker -- Goodhart, and `the_light_that_went_out`
is the standing proof that the checks are not the same as quality. This module
adds pointers. It never touches a word of generated text.

WHY IT REFUSES MORE OFTEN THAN IT ACTS, AND WHY THAT IS THE POINT. casefiles.py's own
docstring names the risk: "a model can emit reveals: ["E3"] on a statement that
says nothing about E3, and nothing structural can tell." A tool that wires
anything to anything would manufacture exactly that lie and every checker would
go green over it. So a candidate must earn the pointer lexically -- it has to
already be about that evidence -- and the wiring is then re-verified against the
full gate, because adding a pointer can CREATE a violation: a witness who
already reveals two exonerations and gains a third may now solve the case alone
(casefiles.py constraint 2). Proposals that make the verdict worse are dropped.

WHAT IT FOUND ON THE FIRST MYSTERY IT WAS POINTED AT, which is the reason the
conservatism is not theoretical. In `the_last_night_of_delacroix_&_sons` no
witness mentions Nadège, no lead concerns her performance, and the Big Top --
the one place her alibi lives -- is not an investigable area at all. The other
three suspects each have a location AND a person; she has a piece of paper.
There was no honest carrier to wire, so the tool reports the gap instead of
inventing one, and names the targeted ask that would close it.

That is the deeper finding, and it is a PROMPT fix rather than a tool one:
generation builds the world around the people it is thinking about, and one
suspect ends up with less world than the others.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

import gate  # noqa: E402
from generation_ledger import FAILURE_CLASSES  # noqa: E402


def _severity(verdict) -> Tuple[int, int]:
    """How bad a verdict is, lower being better: (worst class, how many).

    COUNTING VIOLATIONS IS NOT ENOUGH, and the test that proved it is in
    scripts/test_arrangement.py. Wiring a third exoneration onto a witness who
    already carried two took a mystery from three violations to two -- and the
    two were a CASE.SOLO_SOLVE, because that witness now cleared every innocent
    single-handed. Fewer findings, strictly worse mystery: it traded two
    below_standard complaints for an unplayable one. Severity has to lead.
    """
    # HIGHER IS WORSE, and getting that backwards is easy: FAILURE_CLASSES is
    # ordered worst-FIRST, so a raw index reads inverted -- the first version
    # scored a clean mystery as worse than a below_standard one and withheld
    # every genuine wiring. Flipped here so 0 is clean and 4 is incoherent.
    if not verdict.violations:
        return (0, 0)
    worst = max(len(FAILURE_CLASSES) - FAILURE_CLASSES.index(v["failure_class"])
                if v["failure_class"] in FAILURE_CLASSES else 1
                for v in verdict.violations)
    return (worst, len(verdict.violations))

# Words that carry no evidence of aboutness. Deliberately short: the real filter
# is the within-mystery document frequency below, which adapts to each mystery's
# own vocabulary far better than a fixed list can ("circus" is a stopword in a
# circus mystery and a strong signal anywhere else).
_STOP = {
    "about", "after", "against", "around", "because", "been", "before", "being",
    "between", "both", "cannot", "could", "does", "doing", "down", "during",
    "each", "from", "further", "have", "having", "here", "into", "just", "more",
    "most", "much", "must", "only", "other", "over", "same", "should", "some",
    "such", "than", "that", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "until", "very", "were", "what", "when",
    "where", "which", "while", "with", "would", "your", "night", "would",
}

# A term shared by more than this fraction of a mystery's findings is that
# mystery's furniture, not a link to any one clue.
_COMMON_FRACTION = 0.34

# NAMING THE PERSON IS REQUIRED, NOT A BONUS -- and the first run is why.
#
# The first version scored on shared vocabulary alone and immediately proposed
# wiring Nadège Fontenot's audience sign-in sheet to a witness whose statement is
# about Celestine buying taffy. Their shared words were "else", "entire",
# "general", "show". Rarity does not rescue that: in this mystery "else" has the
# same document frequency as "corroboration", because document frequency
# measures how ODD a word is, not whether it is ABOUT anything.
#
# So the test is domain-shaped instead of statistical. These pointers only ever
# attach to EXONERATING evidence, and alibi testimony names its subject -- every
# witness in that mystery does ("Miss Celestine", "Dr. Beaumont", "Monsieur
# Rémy"), and the one suspect nobody names is precisely the one whose clue was
# orphaned. Requiring the name is strict, explainable to whoever reads the
# statement afterwards, and refuses exactly when there is genuinely nobody
# talking about that person.
#
# The distinctive-term test stays as corroboration: naming the person is not
# enough on its own, since a witness can mention someone while discussing
# something else entirely.
_MIN_SHARED = 1

# A supporting term must be genuinely specific to the pair, not merely uncommon.
_MAX_DOC_FREQUENCY = 3


def _terms(text: str) -> set:
    return {w for w in re.findall(r"[a-zà-ÿ']+", (text or "").lower())
            if len(w) > 3 and w not in _STOP}


@dataclass
class Carrier:
    """A witness, lead or area that could hold a pointer."""
    label: str
    kind: str
    obj: dict
    text: str


@dataclass
class Proposal:
    evidence_id: str
    clears: List[str]
    carrier: Optional[Carrier] = None
    shared: List[str] = field(default_factory=list)
    named_person: bool = False
    reason: str = ""

    @property
    def actionable(self) -> bool:
        return self.carrier is not None


def carriers(mystery: dict) -> List[Carrier]:
    out = []
    for c in mystery.get("characters") or []:
        if isinstance(c, dict) and (c.get("role") or "").lower() == "witness":
            out.append(Carrier(f"witness {c.get('name', '?')}", "witness", c,
                               " ".join(str(c.get(k, "")) for k in
                                        ("name", "statement", "alibi", "occupation", "bio"))))
    for l in mystery.get("leads") or []:
        if isinstance(l, dict):
            out.append(Carrier(f"lead {l.get('id', '?')}", "lead", l,
                               " ".join(str(l.get(k, "")) for k in
                                        ("title", "brief", "investigation_prompt"))))
    for a in mystery.get("investigation_areas") or []:
        if isinstance(a, dict):
            out.append(Carrier(f"area {a.get('id', '?')}", "area", a,
                               " ".join(str(a.get(k, "")) for k in
                                        ("name", "description", "discovery", "analysis"))))
    return out


def orphaned(mystery: dict) -> List[Tuple[str, List[str]]]:
    """Exonerating evidence that no witness, lead or area reveals."""
    pointed = set()
    for c in carriers(mystery):
        pointed |= {str(e) for e in (c.obj.get("reveals") or [])}
    out = []
    for e in mystery.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        names = [str(n).strip() for n in (e.get("exonerates") or []) if str(n).strip()]
        if names and str(e.get("id")) not in pointed:
            out.append((str(e.get("id")), names))
    return out


def _doc_frequency(mystery: dict, cs: Sequence[Carrier]) -> Dict[str, int]:
    """How many findings each term appears in, for the corroboration test."""
    docs = [_terms(c.text) for c in cs]
    docs += [_terms(f"{e.get('name','')} {e.get('description','')}")
             for e in (mystery.get("evidence") or []) if isinstance(e, dict)]
    counts: Dict[str, int] = {}
    for d in docs:
        for w in d:
            counts[w] = counts.get(w, 0) + 1
    return counts


def _common_terms(mystery: dict, cs: Sequence[Carrier]) -> set:
    """Vocabulary this mystery repeats everywhere, which proves nothing."""
    docs = [_terms(c.text) for c in cs]
    docs += [_terms(f"{e.get('name','')} {e.get('description','')}")
             for e in (mystery.get("evidence") or []) if isinstance(e, dict)]
    if not docs:
        return set()
    counts: Dict[str, int] = {}
    for d in docs:
        for w in d:
            counts[w] = counts.get(w, 0) + 1
    ceiling = max(2, int(len(docs) * _COMMON_FRACTION))
    return {w for w, n in counts.items() if n > ceiling}


def propose(mystery: dict) -> List[Proposal]:
    """One proposal per orphaned exoneration. A carrier only if it earns it."""
    cs = carriers(mystery)
    common = _common_terms(mystery, cs)
    freq = _doc_frequency(mystery, cs)
    ev_by_id = {str(e.get("id")): e for e in (mystery.get("evidence") or [])
                if isinstance(e, dict)}

    out = []
    for eid, clears in orphaned(mystery):
        e = ev_by_id[eid]
        ev_terms = _terms(f"{e.get('name','')} {e.get('description','')}") - common
        person_terms = set()
        for n in clears:
            person_terms |= _terms(n)

        best: Optional[Tuple[int, bool, Carrier, List[str]]] = None
        for c in cs:
            raw = _terms(c.text)
            c_terms = raw - common
            # MATCHED AGAINST THE UNFILTERED TEXT. A suspect's name is repeated
            # all over their own mystery, so the common-vocabulary filter strips
            # it -- which silently turned "does this witness name Celestine?"
            # into "no" for the two witnesses who do nothing but talk about her.
            # The common filter exists to stop furniture counting as
            # corroboration; it has no business deciding who was mentioned.
            names_person = bool(person_terms & raw)
            if not names_person:
                continue                       # hard requirement -- see above
            # THE NAME CANNOT BE ITS OWN CORROBORATION. The first version let it
            # be, which is circular -- require the name, then accept the name as
            # proof of aboutness -- and it proposed wiring Nadège Fontenot's
            # audience sign-in sheet to the area holding her MARRIAGE
            # CERTIFICATE. Both mention her; one is her alibi and the other is
            # her motive. So the supporting term must be something other than
            # the person: evidence that the carrier is about this OBJECT, not
            # merely about this person.
            shared = sorted(w for w in (ev_terms & c_terms - person_terms)
                            if freq.get(w, 99) <= _MAX_DOC_FREQUENCY)
            if len(shared) < _MIN_SHARED:
                continue
            rank = (len(shared), names_person)
            if best is None or rank > (best[0], best[1]):
                best = (len(shared), names_person, c, shared)

        if best is None:
            out.append(Proposal(
                eid, clears, reason=(
                    f"nothing names {clears} while also being about {eid}. Nothing here can honestly "
                    f"reveal it, and inventing a pointer would be the drift casefiles.py warns "
                    f"about. Targeted ask: write one finding that surfaces {eid} "
                    f"({e.get('name', '')!r}) and so clears {clears}")))
        else:
            out.append(Proposal(eid, clears, carrier=best[2], shared=best[3],
                                named_person=best[1]))
    return out


def apply(mystery: dict, proposals: Sequence[Proposal],
          name: str = "<memory>") -> Tuple[List[Proposal], List[Proposal]]:
    """Wire what survives the gate. Returns (applied, withheld).

    EACH WIRING IS VERIFIED, ONE AT A TIME, AGAINST THE FULL GATE. Adding a
    pointer is not automatically an improvement: a carrier already revealing two
    exonerations that gains a third may now solve the case alone, which is
    casefiles.py's constraint 2 and a strictly worse mystery than the one we started
    with. Applied in sequence so each is judged against the state the previous
    one left, rather than against the original.
    """
    before = gate.evaluate(mystery, name)
    before_sev = _severity(before)
    applied: List[Proposal] = []
    withheld: List[Proposal] = []

    for p in proposals:
        if not p.actionable:
            withheld.append(p)
            continue
        pointers = list(p.carrier.obj.get("reveals") or [])
        p.carrier.obj["reveals"] = pointers + [p.evidence_id]
        after = gate.evaluate(mystery, name)
        after_sev = _severity(after)
        if after_sev > before_sev:
            p.carrier.obj["reveals"] = pointers          # roll back
            worse = ", ".join(sorted({v["rule_id"] for v in after.violations}
                                     - {v["rule_id"] for v in before.violations})) or "more of the same"
            p.reason = (f"wiring {p.evidence_id} to {p.carrier.label} makes the mystery WORSE "
                        f"({before.failure_class or 'clean'} -> {after.failure_class}: {worse}); "
                        f"withheld")
            p.carrier = None
            withheld.append(p)
        else:
            before, before_sev = after, after_sev
            applied.append(p)
    return applied, withheld


def world_coverage(mystery: dict) -> Dict[str, dict]:
    """Which suspects have a person and a place, and which have only paper.

    NOT A GATE, A DIAGNOSIS. This is what the first real run turned up and it is
    the finding worth acting on: the suspect who ends up with one route is the
    suspect generation gave no witness and no investigable location. That is a
    prompt fix, not something a pointer can repair -- a missing witness cannot
    be wired, only written.
    """
    cs = carriers(mystery)
    out = {}
    for c in mystery.get("characters") or []:
        if not isinstance(c, dict) or c.get("role") != "suspect":
            continue
        who = c.get("name", "")
        # Deliberately NOT common-filtered: the question here is who gets talked
        # about at all, and a name is common precisely when they do.
        terms = _terms(who)
        out[who] = {
            "witnesses": [x.label for x in cs
                          if x.kind == "witness" and (terms & _terms(x.text))],
            "areas": [x.label for x in cs
                      if x.kind == "area" and (terms & _terms(x.text))],
            "leads": [x.label for x in cs
                      if x.kind == "lead" and (terms & _terms(x.text))],
        }
    return out
