"""
Choose Your Mystery — FastAPI Backend
======================================
Thin server that wraps the existing Python generation/interrogation/coherence
logic and exposes it over HTTP for the Godot client.

All Claude API calls happen here. The Godot client never touches the API key.

Endpoints:
  POST /generate          — generate a new mystery from a prompt
  POST /interrogate       — ask a character a question (in-character reply)
  POST /rate              — save a viability rating for a mystery
  GET  /mysteries         — list saved mysteries
  GET  /mysteries/{slug}  — load a saved mystery by slug

Run locally:
  cd /path/to/SocialGaming
  python3 -m uvicorn server.main:app --reload --port 8000

SESSION ANNOTATION — Phase 1 complete when:
  curl -X POST localhost:8000/generate \
       -H "Content-Type: application/json" \
       -d '{"prompt":"a murder on a train","opening_narration":true}'
  returns a valid mystery JSON with _provenance and _coherence fields.
"""

import asyncio
import contextlib
import json
import os
import random
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Path setup — when running as `uvicorn server.main:app` from project root,
# the repo root is already on sys.path. When running from inside server/,
# we add the parent directory so the backend modules are importable.
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from part_registry import load_registry, PART_TYPE_NAMES  # noqa: E402
from coherence_validator import check_mystery               # noqa: E402
from localization import (                                  # noqa: E402
    localize_mystery as _localize_mystery,
    _is_modern,
    _era_key,
    _load_era_rules,
)
import craft_grounding                                       # noqa: E402
import gate                                                  # noqa: E402
import generation_ledger                                     # noqa: E402
import apf                                                   # noqa: E402
import casefiles                                                  # noqa: E402

# The table size the saved-mystery picker judges assignability at. APF is
# specified for four (docs/PLAYTEST_FLOW.md), and a mystery's readiness has to
# be reported before anybody has joined, so it is measured at the specified
# shape rather than at whoever happens to be in the room.
APF_PICKER_PLAYERS = 4

# ---------------------------------------------------------------------------
# API client — auth priority: env var → session ingress token
# ---------------------------------------------------------------------------
def _get_credentials() -> dict:
    """Kwargs for Anthropic(), by auth source.

    The two sources are NOT interchangeable, which is what this function exists
    to express. ANTHROPIC_API_KEY is an API key and goes on the x-api-key
    header (`api_key=`). The session ingress token is a bearer token and goes on
    Authorization (`auth_token=`) -- passing it as api_key returns
    401 "API key is invalid", which is exactly what it used to do. CLAUDE.md has
    always described this one as a Bearer token; the code did not.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return {"api_key": key}
    token_path = Path("/home/claude/.claude/remote/.session_ingress_token")
    if token_path.exists():
        return {"auth_token": token_path.read_text().strip()}
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set and no session ingress token found. "
        "Set the environment variable before starting the server."
    )

_client: Optional[Anthropic] = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(**_get_credentials())
    return _client

# ---------------------------------------------------------------------------
# Part registry — loaded once at startup
# ---------------------------------------------------------------------------
_DB_PATH = _repo_root / "mystery_database"
_registry = None

def get_registry():
    global _registry
    if _registry is None:
        _registry = load_registry(str(_DB_PATH))
    return _registry

# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------
# 8192 was too low for the mystery schema and is the most likely cause of the
# "Unterminated string" / "Expecting property name" parse failures in the old
# batch summary in mystery_database/generated/ (13 of 14 generations). A capped
# response is truncated mid-JSON, which is exactly what those errors look like.
# The playtest fields (per-area discovery/analysis, witness statements) made the
# response longer again. 16000 is the documented ceiling for a non-streaming
# request -- above that the SDK wants streaming to avoid HTTP timeouts.
_MAX_TOKENS = 16000


# The attempt currently being generated, per thread. THREAD-LOCAL because
# /generate/async runs generation in a background thread (see _run_generation_job)
# and a module-level global would let two concurrent jobs bill each other's
# tokens to the wrong mystery.
_current_attempt = threading.local()


def _record_usage(purpose: str, model: str, response) -> None:
    """Bank one call's tokens against the attempt in flight, if there is one.

    Silent no-op outside a generation -- play-time calls (interrogation, area
    investigation) are real spend but they are not part of any mystery's
    creation cost, and folding them into CPAM would make the metric answer a
    different question than the one it is for.
    """
    attempt = getattr(_current_attempt, "attempt", None)
    if attempt is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    attempt.record_call(purpose, model,
                        getattr(usage, "input_tokens", 0) or 0,
                        getattr(usage, "output_tokens", 0) or 0)


def llm(prompt: str, system: str = "You are a creative mystery game engine.",
        purpose: str = "other") -> str:
    model = "claude-sonnet-4-6"
    response = get_client().messages.create(
        model=model,
        max_tokens=_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    # Recorded HERE because this is the only call site in the server, so there
    # is exactly one place a token count can go missing. Until Session 41 it
    # went missing here: response.usage was handed to us on every call and read
    # by nothing, which is why the four rejected mysteries have no recoverable
    # cost. See generation_ledger.py.
    _record_usage(purpose, model, response)
    # Not content[0]: a model running adaptive thinking puts a ThinkingBlock
    # first. Sonnet 4.6 does not think unless asked, so this is safe today and
    # would break the day the model line changes -- which is exactly the kind of
    # switch nobody expects to be a code change.
    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise RuntimeError(
        f"no text block in response (stop_reason={response.stop_reason})")

def _parse_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)

# ---------------------------------------------------------------------------
# Mystery generation (ported from app.py)
# ---------------------------------------------------------------------------
def _craft_guidance_for_parts(parts) -> list:
    """Map the part_types actually sampled for this mystery onto their
    taxonomy codes (see craft_grounding.PART_TYPE_TO_TAXONOMY) and retrieve
    matching craft guidance — so a mystery only gets guidance relevant to
    the axes it actually drew from, not a generic dump."""
    taxonomy_tags: set[str] = set()
    for p in parts:
        taxonomy_tags.update(craft_grounding.PART_TYPE_TO_TAXONOMY.get(p.part_type, []))
    return craft_grounding.get_craft_guidance(taxonomy_tags=sorted(taxonomy_tags), max_items=5)


def _generate_mystery_dict(user_prompt: str) -> tuple[dict, object]:
    """Sample registry parts, call Claude, return (mystery_dict, recipe)."""
    registry = get_registry()
    parts, recipe = registry.sample_for_generation(target_setting=user_prompt)

    parts_block = "\n".join(
        f"  [{p.label()} — {p.part_type}]: {p.content}"
        for p in parts
    )

    guidance_entries = _craft_guidance_for_parts(parts)
    guidance_block = craft_grounding.format_guidance_block(guidance_entries)

    prompt = f"""\
You are generating a mystery scenario for a social deduction game with 4 players.

SETTING: {user_prompt}

The following atomized parts have been selected from existing mystery literature
(recipe: {recipe.format()}). Adapt them to the target setting — do not copy verbatim.

SELECTED PARTS:
{parts_block}

{guidance_block}

WRITE IT BACKWARDS. This is the order the JSON below is in, and it is not cosmetic.

Decide the SOLUTION first — culprit, motive, method, and the numbered chain of reasoning that
gets a player there. Only then write the cast, and only then the clues, each one planted to serve
a step of that chain. This is how mysteries are written for novels and screen, and it matters more
here than it does on paper: you are composing left to right, so whatever you write first is what
everything after it is conditioned on. Write the solution last and you are improvising an
explanation for clues you already committed to — and when the cast does not support the chain you
need, the cheapest thing to do is invent a person who is not in it. That has happened: a generated
mystery scored a clean coherence pass while its reasoning turned on four people who appear nowhere
in its own character list.

So the rule that follows from it, and it is absolute:

  EVERY PERSON, PLACE OR OBJECT NAMED IN THE SOLUTION MUST EXIST IN THE MYSTERY.
  Every person named in solution.method, solution.motive, solution.chain or how_to_deduce must
  appear by that exact name in "characters". Every place must be an investigation_areas name or
  the setting itself. If the chain needs somebody, put them in the cast — never name someone the
  player cannot meet, question or accuse.

DECLARE THE LINKS. Do not leave the connection between a clue and the solution implicit in prose:
state it in fields, so it can be checked without re-reading the story. Each evidence item says
which step of the chain it supports, who it clears, and who it points at.

  ELIMINATION DATA LIVES ONLY ON EVIDENCE. A witness statement, a lead and an investigation area
  do NOT repeat exonerates/implicates -- they carry "reveals", the list of evidence ids they
  surface. Everything a player learns is therefore traceable to an evidence item, and one
  exoneration can never be stated two ways that disagree.

QUALITY REQUIREMENTS — every generated mystery MUST satisfy these:

SETTING:
  - description must explicitly explain why suspects cannot simply leave (isolation mechanic).

CHARACTERS (include 1 victim, EXACTLY 4 suspects, and 3–4 witnesses):
  - FOUR SUSPECTS, COUNTED. Not three, not five. The whole assignment is sized for it: four suspects
    means three people to clear, and with only two the single finding that clears both IS the
    answer, so no assignment can be fair however well the mystery is written. A three-suspect mystery
    is refused outright -- count the list before writing anything else.
  - alibi: SPECIFIC — state where the person was, with whom or doing what. Never "—" or vague.
  - secret: CONCRETE FACT (≥ 2 sentences) anchoring interrogation questions.
  - motive (suspects): specific stake — financial, relational, reputational, or political. Never "—".
  - occupation: always present; must logically place the character in the closed world.
  - bio: 2–3 sentences on WHO THIS PERSON IS, shown to players. Not their function in the puzzle —
    their history, temperament, what they are like to be in a room with, how they came to be here.
    Motive, alibi and secret already carry the mechanics; this is the part that makes a name into a
    person somebody can suspect and feel bad about suspecting. No spoilers: never hint at guilt,
    never restate the secret.
  - statement (WITNESSES ONLY): what this witness tells an investigator who questions them.
    2–4 sentences. It must be ACTIONABLE — it names a person, a place, a time or an object the
    player can do something with. Never atmosphere alone, never "I didn't see anything".
    Witness statements in this build are TRUE. A witness may be mistaken about what something
    MEANT, but must not invent, deny or conceal what they saw. Deception is deliberately switched
    off: a player cannot otherwise tell "this mystery is incoherent" from "this witness lied".
    Across the witnesses as a group, at least one statement must point toward the culprit, and at
    least one must point at something that turns out to be innocent.

    ASSIGN EACH WITNESS A SUSPECT BEFORE WRITING THEIR STATEMENT, and cover every one of the
    four. Write the assignment first -- "this witness is the one who speaks to <suspect>" --
    then write the statement about that person. If there are three witnesses and four suspects,
    one witness covers two; nobody may be left with no one who mentions them.
    THIS IS THE RULE THE LAST THREE GENERATIONS BROKE, and it broke the same way each time: three
    suspects got a witness and a location, and the fourth got a document nobody talks about. That
    fourth suspect then had exactly one route to being cleared -- Adachi, Luz Fontaine, Nadege
    Fontenot -- while the others had four to ten, and each mystery was refused for it. The one
    generation where every suspect had a witness passed this rule outright.
    A suspect nobody mentions is not a lighter workload. It is the defect.

    AND NO SINGLE WITNESS, LEAD OR AREA MAY CARRY A WHOLE PROOF. One finding is assigned to one
    player, so if its "reveals" list adds up to the answer, that player wins without speaking to
    anyone and the sharing decision -- the point of the game -- never happens. Concretely: do not
    let one witness reveal BOTH a narrowing item and the exoneration that completes it. A
    narrowing that leaves two suspects, plus the clue clearing one of them, IS the answer.
    That is how the last generation failed, and it failed while everything else was right:
    one witness revealed the six-foot-shelf narrowing and the barometric log clearing the shorter
    man, and so solved the case single-handed. Split the two halves across different witnesses,
    or put one of them on a lead or an area instead.

    A NARROWING MUST BE A CLASS OF PERSON, NEVER SOMEBODY'S BELONGINGS. Three generations have
    now leaked the answer in a narrowing clue's own prose, and the last one shows why: the clue
    was a vial "in Aoyama's cramped script, found in his entomology kit". Once the object BELONGS
    to one of the people it leaves possible, naming him is unavoidable and the clue has become an
    accusation. Anchor the fact to a physical class instead -- a reach, a handedness, a shoe size,
    a strength, a language read -- so it describes a KIND of person and the player looks at the
    cast and draws the line themselves. A six-foot shelf is a narrowing. A vial in Aoyama's own
    kit is not: it is his name with extra steps.
  - reveals (WITNESSES ONLY): the ids of the evidence items this statement surfaces, e.g. ["E3"].
    EVERY witness must reveal at least one. The statement must actually be about that evidence --
    if a witness saw the bolted door, they reveal the evidence item about the bolted door.
    A witness who reveals nothing is assigned to a player as a finding that cannot be reasoned from.

EVIDENCE (include at least 9 items total — planted to serve the chain, written AFTER it):
  - At least 2 items with type "physical".
  - At least 1 item with relevance "red_herring" and type "physical" or "documentary".
  - At least 2 items with relevance "critical".
  - description: ≥ 2 sentences; state what the item is, where found, and what it suggests.
  - supports: the chain step ids this item is evidence FOR, e.g. ["S2"]. A red herring supports
    nothing and must use [] — it is the only kind of item that may.
  - exonerates: names of suspects this item clears. Use the exact character name.
    AT MOST ONE NAME. One piece of evidence rules out one person, never several at once. An
    item clearing two or three suspects is a solved case in a single object — whoever is assigned it
    wins without anyone sharing anything, which deletes the game. Write the alibi evidence one
    person at a time: each alibi is its own document, witness or trace.
  - implicates: names of suspects this item points AT — SUSPICION, not proof. The culprit must be
    implicated by at least one item; a culprit arrived at only by elimination, with nothing
    positively pointing at them, reads as arbitrary. This is flavour and does not constrain the
    deduction. Do NOT confuse it with "narrows" below.
  - narrows: OPTIONAL, and the most interesting field here. A physical fact that rules people OUT
    without clearing anyone in particular — a bloody MAN'S glove, a boot print in a size only two
    people take, a keycard only the night staff carry. List every suspect who could still be
    responsible given that fact. AT LEAST TWO NAMES, and ALWAYS FEWER THAN THE FULL SUSPECT LIST,
    always including the culprit. With 4 suspects that means 2 or 3 names — never 4. A fact
    consistent with everybody rules nobody out and is not a narrowing clue at all: it reads like
    evidence and does nothing, which is worse than no clue, because a player who works out what it
    implies has been sent down a corridor with no door. If the fact you have written could apply to
    every suspect, sharpen it until it cannot — a rifle is not a narrowing; a LEFT-HANDED shooter
    is — or drop "narrows" from that item.
      * Two or three items should carry it. Most items should not.
      * WRITE THE FACT. NAME NOBODY IT POINTS TO. The description gives the physical detail and
        stops. It must never say "so it was one of the men", never hint a list exists, and — this
        is the one that actually goes wrong — never say that the fact MATCHES a particular person.
        The player looks at the cast and draws the line; that is the whole pleasure, and one name
        destroys it.

        THIS IS THE REAL FAILURE, TAKEN FROM A GENERATION THAT MADE IT. A boot print narrowing to
        two people was written as:

            WRONG: "A partial print, herringbone sole, size 5-6. Morag Gillies wears size 5.5
                    walking boots with a herringbone sole."
            RIGHT: "A partial print in the gear oil, narrower than a work boot — a herringbone
                    walking sole, no bigger than a size 6."

        The wrong one is not a narrowing clue at all. It is an accusation, and whoever is assigned it
        wins without speaking to anyone. Same failure, second example:

            WRONG: "...a woman's voice, low and steady, consistent with how Morag Gillies speaks."
            RIGHT: "...a woman's voice, low and steady, too quiet to place."

        You MAY name a suspect the fact rules OUT — "the print does not match the heavy work boots
        Niall Urquhart wears" is good writing and good play. What you may never do is name anyone
        the fact still leaves possible.
      * IT MUST BE TRUE. If the glove is a man's, the culprit is a man, and no woman wore it. A
        player who reasons exactly as the clue invites must not lose for it — that is the worst
        outcome a mystery can produce, and this rule is M3 Clue Fairness in the craft corpus
        (P.D. James: "the detective can know nothing which the reader isn't also told").
      * The fact must be checkable against the cast: gender, height, build, profession, access,
        handedness — something the character list already tells the player. A narrowing on a fact
        players cannot see is not a clue, it is a coin flip.
      * These are IN ADDITION to the alibi evidence, not instead of it. The case must still be
        solvable by alibis alone, so that withholding a narrowing finding can never make it
        unprovable.
  - Across all items, the suspects exonerated must be every suspect EXCEPT the culprit, so that
    eliminating them leaves exactly one person. Never exonerate the culprit.
  - TWO INDEPENDENT ROUTES, AND WRITE THEM FIRST. Every non-culprit suspect must be cleared by
    AT LEAST TWO separate evidence items, each a genuinely different kind of proof — a witness who
    saw them elsewhere AND a physical trace, not the same fact written twice. A suspect clearable
    only one way becomes unclearable the moment that one item is withheld, and players withhold.

    BUILD THE ARRAY IN THIS ORDER, and do not start the red herrings until the alibi pairs are
    written. With 3 innocents that is six items, and they are the first six:

        E1, E2   both clear <first non-culprit>, by two different kinds of proof
        E3, E4   both clear <second non-culprit>, by two different kinds of proof
        E5, E6   both clear <third non-culprit>, by two different kinds of proof
        E7 …     everything else — red herrings, narrowing facts, items implicating the culprit

    Name the suspect in each of the first six items' "exonerates" before writing its description,
    so the pairing is decided rather than discovered. This ordering is not presentational: it is
    the same reason "solution" is written before the clues. Whatever is emitted first conditions
    everything after, and an alibi structure improvised alongside atmosphere is an alibi structure
    with a gap in it — the last two generations each left exactly one suspect with a single route.
  - Every chain step must appear in at least one item's "supports".
  - REACHABLE: every evidence item that exonerates somebody must be named in the "reveals" of at
    least one witness, lead or investigation area. Not "or found as a clue" -- a clue is always
    available, so that escape clause would make this rule ask for nothing. If every exoneration
    sits on clues alone, witness statements and lead results are decorative and the game has one
    kind of finding wearing three costumes.

SOLUTION (write this FIRST — everything below is derived from it):
  - key_evidence must list at least 2 evidence IDs.
  - chain: the deduction as numbered steps, 3+, each with an id "S1", "S2", … and a one-sentence
    claim. Each step must be a claim a player could actually reach from evidence, not a summary.
    Every step must be supported by at least one evidence item (see EVIDENCE below).
  - how_to_deduce: the same reasoning as readable prose, for the result screen. It must not
    introduce any person, place or fact that is not already in the chain and the cast.
  - The culprit named here must appear in "characters" with role "suspect".

GAMEPLAY NOTES:
  - difficulty: EASY or HARD. There is no MEDIUM — it existed as a third label with no third
    behaviour behind it, which is worse than two honest settings.
  - estimated_playtime: must reflect difficulty — EASY: 30–45 min, HARD: 60–75 min.
    Do not exceed 75 minutes. This is a digital party game, not a dinner-event experience.

INVESTIGATION AREAS (exactly 5):
  - Named physical locations within the setting where players can search for clues.
  - Each area must be atmospherically distinct and plausible for the setting.
  - investigation_prompt: 1–2 sentences of private context Claude will use when a player investigates
    this area (what could be found there — may include red herrings). NOT shown to players.
  - discovery: what a player who searches this area FINDS. 1–2 sentences, concrete and physical —
    an object, a mark, a document, an absence. This is shown to the player verbatim as
    "You searched the <AREA> and found <DISCOVERY>." Every area must yield something; an area
    that yields nothing wastes the only move a player gets there.
  - analysis: what testing, forensics or research on that discovery then reveals. 1–2 sentences,
    shown verbatim as "Testing and research reveal <ANALYSIS>." Make it the kind of thing a lab or
    a records search returns: fingerprints on a weapon match a named person; a bank receipt traces
    to a named account; a hard drive shows what was deleted and when; a ledger entry contradicts a
    stated alibi. It must reference a NAMED character, time or place — not "someone was here".
  - At least 2 areas must yield a discovery+analysis pair that genuinely narrows the suspect list,
    and at least 1 must be a red herring that looks incriminating and is innocently explained.
  - reveals: the ids of the evidence items found here, e.g. ["E1","E7"]. EVERY area must reveal at
    least one, and its discovery/analysis must describe that evidence rather than something else.

LEADS (exactly 4):
  - Pre-existing tips, rumours, or documents that can be followed up on.
  - Each lead must be specific and actionable (not generic like "investigate the crime").
  - investigation_prompt: 1–2 sentences of private context Claude will use to resolve the lead.
    NOT shown to players. At least 1 lead should point toward the culprit; at least 1 is a red herring.
  - reveals: the ids of the evidence items following this lead turns up, e.g. ["E5"]. EVERY lead
    must reveal at least one. The red-herring lead reveals the red-herring evidence item -- that is
    how a dud finding is represented, not by revealing nothing.

Generate a complete mystery JSON with this exact structure:
{{
  "title": "string",
  "setting": {{
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentence atmospheric description including why suspects cannot leave"
  }},
  "solution": {{
    "culprit": "string — must appear in characters[] with role suspect",
    "motive": "string",
    "method": "string",
    "chain": [
      {{"id": "S1", "claim": "one sentence a player could reach from evidence"}}
    ],
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "the same chain as prose; introduces nothing new"
  }},
  "crime": {{
    "type": "string",
    "what_happened": "PUBLIC — what the room knows. Must NOT name the culprit or reveal the method",
    "when": "string",
    "initial_discovery": "string"
  }},
  "characters": [
    {{
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string",
      "motive": "string",
      "alibi": "string",
      "secret": "string",
      "bio": "2–3 sentences: who this person is. Shown to players. No spoilers",
      "statement": "witnesses only — what they tell an investigator; true, actionable",
      "reveals": ["witnesses only — evidence ids this statement surfaces, e.g. E3"]
    }}
  ],
  "evidence": [
    {{
      "id": "E1",
      "name": "string",
      "description": "string",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring",
      "supports": ["S2"],
      "exonerates": ["exact character name"],
      "implicates": ["exact character name"],
      "narrows": ["optional — 2+ suspects still possible given a physical fact; omit on most items"]
    }}
  ],
  "investigation_areas": [
    {{
      "id": "A1",
      "name": "string",
      "description": "1–2 sentence atmospheric description of the location visible to players",
      "investigation_prompt": "private context for AI — what is here, what could be found",
      "discovery": "what a player who searches here finds — concrete, physical",
      "analysis": "what testing or research on that discovery reveals — names a character, time or place",
      "reveals": ["E1"]
    }}
  ],
  "leads": [
    {{
      "id": "L1",
      "title": "string",
      "brief": "1 sentence visible to players describing the tip or document",
      "investigation_prompt": "private context for AI — what this lead reveals when followed",
      "reveals": ["E5"]
    }}
  ],
  "gameplay_notes": {{
    "difficulty": "EASY | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  }}
}}

Return only valid JSON. No commentary outside the JSON block."""

    raw = llm(prompt, system="You are a mystery game engine. Return only valid JSON.",
              purpose="generation")
    mystery_dict = _parse_json(raw)
    mystery_dict["_provenance"] = recipe.to_dict()
    mystery_dict["_provenance"]["craft_guidance"] = craft_grounding.guidance_provenance(guidance_entries)
    return mystery_dict, recipe


def _run_localization(mystery_dict: dict) -> dict:
    setting = mystery_dict.get("setting", {})
    if _is_modern(setting):
        return mystery_dict
    # Wrapped rather than passed bare so the ledger can tell a localization call
    # apart from the generation call. A modern setting skips this entirely, so
    # the call list genuinely varies per mystery and cannot be assumed.
    return _localize_mystery(
        mystery_dict,
        lambda prompt, **kw: llm(prompt, purpose="localization", **kw))


def _run_coherence(mystery_dict: dict) -> dict:
    report = check_mystery(mystery_dict)
    mystery_dict["_coherence"] = {
        "passed": report.passed,
        "blocking": report.blocking_count,
        "warnings": report.warning_count,
    }
    return mystery_dict


def _generate_opening_narration(mystery_dict: dict) -> dict:
    """The paced text opening (docs/PLAYTEST_FLOW.md, item 23 step 4).

    WAS _generate_cinematic_brief(), AND WROTE TWO THINGS. It returned the
    player-facing narration AND a video shot list -- logline, lighting, sound
    design, cast appearance -- in one response, behind one boolean. Measured on
    the first run that ever executed it, 82% of the output was the video half.
    The owner is deferring video and avatars to stage 3, so the playtest was
    paying for shot direction nobody will read for a year.

    THE VIDEO HALF IS DELETED, NOT PARKED, and the reasoning matters because the
    obvious worry was that tuning this prompt for prose would leave it useless
    for video later. It cannot, because the two never shared anything: the video
    brief was built from the mystery -- title, setting, crime, cast -- never
    from the narration. They were siblings, not a pipeline, so a video brief can
    be written fresh from the mystery dict whenever stage 3 arrives.

    Two more reasons it is a deletion. The old prompt contradicted itself,
    asking for narration with "no camera direction" and, in the same response, a
    brief that is entirely camera direction. And shot-list conventions written
    today are written for today's video models; by stage 3 they are stale, which
    makes writing them now speculative work with a shelf life.

    Returns {"opening_narration": str}. One call, at generation time, which is
    the right place to spend it -- pacing the beats afterwards is client-side
    and free.
    """
    m = mystery_dict
    s = m.get("setting", {})
    c = m.get("crime", {})
    chars = m.get("characters", [])
    suspects = [ch for ch in chars if ch.get("role") == "suspect"]
    cast_lines = "\n".join(
        f"  - {ch['name']} ({ch.get('occupation', '')})" for ch in suspects
    )
    prompt = f"""\
Write the opening narration for a mystery party game: the text shown on a shared screen and read
aloud to the room before play begins. This is the moment that sets the scene, and it is the only
thing the players have before they start suspecting each other.

MYSTERY TITLE: {m.get('title', '')}
SETTING: {s.get('location', '')} — {s.get('time_period', '')}
ATMOSPHERE: {s.get('description', '')}
CRIME: {c.get('what_happened', '')}
DISCOVERED BY: {c.get('initial_discovery', '')}
PRESENT THAT NIGHT (name them only if it serves the scene; never hint at guilt):
{cast_lines}

REQUIREMENTS:
  - 3–5 sentences. Written for the ear: it will be spoken out loud to a room.
  - Atmospheric and specific. One concrete physical detail beats three adjectives.
  - NO SPOILERS. Never name or hint at the culprit, the method, or the motive.
  - No camera, shot or lighting direction. This is prose, not a screenplay.
  - End on the situation, not a question. Do not ask the players anything; do not
    say "who did it?" or "can you solve it?" — the game asks that, not the narrator.

Return ONLY valid JSON:
{{"opening_narration": "the 3–5 sentences"}}"""
    raw = llm(prompt, system="You are a mystery game's opening-sequence writer. Return only valid JSON.",
              purpose="opening_narration")
    return _parse_json(raw)

def _save_mystery(mystery_dict: dict) -> str:
    """Persist mystery to disk, to the directory its verdict earns. Returns slug.

    ITEM 18, SETTLED (Session 41, owner's choice (c)). This used to write every
    generation to generated/ regardless of what the checks said -- which is how
    a mystery carrying {"passed": false, "blocking": 1} came to be servable, and
    why all four hand-rejected mysteries had to be carried out by hand.

    generated/ now means "no check we own can prove this is broken".
    rejected/  means one can, and mystery_database/ledger.jsonl says which.

    THE VERDICT IS RECORDED EITHER WAY. A rejected mystery is still written to
    disk, still costs what it cost, and is still the evidence that a rule was
    needed -- gate.py refuses it, it does not delete it.
    """
    title = mystery_dict.get("title", "mystery")
    slug = title.lower().replace(" ", "_")[:40]
    timestamp = int(time.time())
    filename = f"{slug}_{timestamp}.json"

    verdict = gate.evaluate(mystery_dict, filename)
    mystery_dict["_verdict"] = {
        "verdict": verdict.verdict,
        "failure_class": verdict.failure_class,
        "violations": verdict.violations,
        "advisory": verdict.advisory,
    }

    out_path = _DB_PATH / verdict.destination / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(mystery_dict, f, indent=2)

    # Stashed for the caller's ledger row rather than returned, because both
    # /generate and the async job path call this and neither's return type can
    # change without touching the client.
    mystery_dict["_verdict"]["destination"] = verdict.destination
    # THE LEDGER KEYS ON THE FILE STEM, NOT THE TITLE SLUG. Two mysteries can
    # share a title (there are two `the_great_cookie_caper_of_sesame_street` and
    # two `the_murder_at_tokyo` on disk already), and the timestamped stem is the
    # only identity that is actually unique. It also has to match what
    # scripts/backfill_ledger.py derives from the filename, or a re-verdict can
    # never find the attempt it supersedes -- which is exactly what happened the
    # first time this ran, and it double-counted the mystery.
    mystery_dict["_verdict"]["file_stem"] = out_path.stem
    return slug


@contextlib.contextmanager
def _ledger_attempt(prompt: str):
    """Bracket one generation so every call inside it bills to the same row.

    The attempt is written to the ledger on the way out WHATEVER HAPPENS --
    including when generation raises halfway through. A crashed generation still
    spent the tokens it spent, and a ledger that only records successes would
    make CPAM optimistic by exactly the amount that matters most.
    """
    attempt = generation_ledger.Attempt(prompt)
    _current_attempt.attempt = attempt
    state = {"slug": "", "mystery": None, "error": ""}
    try:
        yield attempt, state
    except Exception as exc:                                  # noqa: BLE001
        state["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        _current_attempt.attempt = None
        mystery = state.get("mystery") or {}
        recorded = mystery.get("_verdict") or {}
        row = attempt.row(
            # The file stem, so the ledger and the backfill agree on identity.
            slug=recorded.get("file_stem") or state.get("slug", ""),
            verdict=recorded.get("verdict") or ("error" if state["error"] else "unknown"),
            failure_class=recorded.get("failure_class"),
            violations=recorded.get("violations") or [],
            coherence=mystery.get("_coherence"),
            destination=recorded.get("destination", ""),
        )
        if state["error"]:
            row["error"] = state["error"]
        row["advisory"] = recorded.get("advisory") or []
        try:
            generation_ledger.append(row)
        except OSError:
            # A ledger write must never be the reason a generated mystery is
            # lost -- the mystery is already safely on disk by this point.
            pass

# ---------------------------------------------------------------------------
# Async job store
# ---------------------------------------------------------------------------
# Jobs are held in memory; they expire after 10 minutes.
# Structure: { job_id: { "status": str, "stage": str, "result": dict|None, "error": str, "ts": float } }
_jobs: dict = {}
_jobs_lock = threading.Lock()

JOB_TTL = 600  # seconds


def _job_create() -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "queued", "stage": "Queued", "result": None, "error": "", "ts": time.time()}
    return job_id


def _job_update(job_id: str, status: str, stage: str) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = status
            _jobs[job_id]["stage"] = stage


def _job_finish(job_id: str, result: dict) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["stage"] = "Done"
            _jobs[job_id]["result"] = result


def _job_fail(job_id: str, error: str) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["stage"] = "Error"
            _jobs[job_id]["error"] = error


def _job_get(job_id: str) -> Optional[dict]:
    with _jobs_lock:
        return _jobs.get(job_id)


def _evict_old_jobs() -> None:
    cutoff = time.time() - JOB_TTL
    with _jobs_lock:
        stale = [k for k, v in _jobs.items() if v["ts"] < cutoff]
        for k in stale:
            del _jobs[k]


def _run_generation_pipeline(job_id: str, prompt: str, opening_narration: bool) -> dict:
    """Runs generation + localization + coherence + optional opening narration +
    save, updating job progress as it goes. Returns the final mystery dict
    (with "_slug" set). Raises on failure -- callers own their own
    _job_fail/cleanup, since that differs between a plain /generate/async job
    and a game-attached one (the latter also needs to notify the room)."""
    # Wrapped here rather than in the two callers: /generate/async and the
    # room-first game flow both come through this function, and a ledger row
    # opened in only one of them would silently under-count the other's spend.
    with _ledger_attempt(prompt) as (_attempt, _state):
        _job_update(job_id, "running", "Generating mystery…")
        mystery_dict, recipe = _generate_mystery_dict(prompt)

        _job_update(job_id, "running", "Localizing characters…")
        mystery_dict = _run_localization(mystery_dict)

        _job_update(job_id, "running", "Checking coherence…")
        mystery_dict = _run_coherence(mystery_dict)

        if opening_narration:
            _job_update(job_id, "running", "Writing the opening…")
            mystery_dict["opening_narration"] = _generate_opening_narration(
                mystery_dict).get("opening_narration", "")

        _job_update(job_id, "running", "Saving…")
        slug = _save_mystery(mystery_dict)
        mystery_dict["_slug"] = slug
        _state["slug"] = slug
        _state["mystery"] = mystery_dict
        return mystery_dict


def _run_generation_job(job_id: str, prompt: str, opening_narration: bool) -> None:
    """Background thread: runs the full generation pipeline and updates job state."""
    try:
        mystery_dict = _run_generation_pipeline(job_id, prompt, opening_narration)
        _job_finish(job_id, mystery_dict)
        _evict_old_jobs()
    except Exception as exc:
        _job_fail(job_id, str(exc))


def _run_game_generation_job(game_id: str, job_id: str, prompt: str, opening_narration: bool) -> None:
    """Background thread: generates a mystery for a specific game room (the
    room-first lobby flow -- POST /games/create with no mystery_slug, then
    POST /games/{id}/start), attaches it to the session once done, and
    broadcasts so connected clients stop waiting on the lobby screen."""
    try:
        mystery_dict = _run_generation_pipeline(job_id, prompt, opening_narration)
        _job_finish(job_id, mystery_dict)
        _evict_old_jobs()
        game = _get_game(game_id)
        if game is not None:
            with _games_lock:
                game["mystery"] = mystery_dict
            _broadcast_sync(game_id, "mystery_ready", {"job_id": job_id})
    except Exception as exc:
        _job_fail(job_id, str(exc))
        _broadcast_sync(game_id, "mystery_generation_failed", {"error": str(exc)})


# ---------------------------------------------------------------------------
# Game session store
# ---------------------------------------------------------------------------
# In-memory; good for Phase 3. Replace with a DB if sessions need to survive restarts.
#
# Session structure:
# {
#   "game_id": str,
#   "mystery": dict | None,    # full mystery dict including investigation_areas + leads;
#                                # None from room creation until the host starts the game
#                                # (see "submitted_prompts" below) or a mystery_slug was
#                                # given directly to POST /games/create.
#   "difficulty": str,
#   "share_min": float,        # minimum fraction of findings player must share
#   "witness_budget": int,
#   "investigation_budget": int,
#   "players": {player_id: {"name": str, "phase": str, "witness_budget": int,
#                            "investigation_budget": int, "leads_used": [lead_id],
#                            "witness_findings": [{id, character, question, response}],
#                            "investigation_findings": [{id, area_id, findings}],
#                            "lead_findings": [{id, lead_id, findings}]}},
#   "submitted_prompts": {player_id: {"name": str, "prompt_text": str, "ts": float}},
#                                # collected while "mystery" is still None; whoever's entry
#                                # "used_prompt_player_id" names is what actually drove the
#                                # attached mystery. Everyone else's stay stored for the
#                                # "prompt_vote" round type (see below) once the game ends.
#   "used_prompt_player_id": str | None,  # whose submitted_prompts entry generated "mystery"
#   "win_history": [player_id, ...],  # one entry per mystery played in this room, oldest
#                                # first -- used only to check "did the current winner also
#                                # win the mystery right before this one" for prompt_vote's
#                                # tie-break rule (see _tally_prompt_vote).
#   "shared_pool": {
#       "witness": [{sender_name, id, character, question, response, ts}],
#       "investigation": [{sender_name, id, area_id, findings, ts}],
#       "lead": [{sender_name, id, lead_id, findings, ts}],
#   },
#   "block_pool": {
#       "witness": [{character, fingerprint}],
#       "investigation": [area_id],
#       "lead": [lead_id],
#   },
#   "stage": str | None,        # lockstep round state: None | "submitting" | "generating" | "revealed"
#   "round": dict | None,       # active lockstep round, see _open_round() — independent of the
#                                # legacy per-player "phase" above; phase-specific rework (witness/
#                                # investigation/lead content) plugs into this separately.
#   "winner": player_id | None, # set on the first correct accusation; game is over once set
#   "accusations": [{player_id, accused_name, correct, ts}],  # full public history
#   "resolution_narrative": str | None,  # generated once by _generate_resolution_narrative()
#                                # on the first game_won/GET-result call after a win, then cached
#                                # here -- never regenerated, so every viewer sees the same wording.
#   "_resolution_craft_guidance": list | None,  # citations for the above, server-side audit only
#   "ts": float,
# }

_games: dict = {}
_games_lock = threading.Lock()
_GAME_TTL = 3600  # 1 hour

_DIFFICULTY_CONFIG = {
    "EASY":   {"share_min": 0.70, "witness_budget": 8, "investigation_budget": 3, "questions_per_round": 3},
    "MEDIUM": {"share_min": 0.60, "witness_budget": 6, "investigation_budget": 2, "questions_per_round": 2},
    "HARD":   {"share_min": 0.50, "witness_budget": 4, "investigation_budget": 2, "questions_per_round": 1},
}


def _min_share_required(finding_count: int, share_min: float) -> int:
    """How many of a player's findings they must share. THE only definition.

    It used to be written twice -- here and again in the Godot client, which
    used ceil() where this uses round(). They disagreed in 6 of 18 realistic
    combinations and the client was always the stricter one, so it refused to
    submit shares the server would have accepted. With only two findings held it
    demanded both, which removes the choice the whole mechanic is about.

    Now the server computes it and sends it with every finding response; the
    client only displays what it is given. If a client ever has to guess it
    should guess 1 -- the floor below -- because erring permissive costs a
    rejected submit, while erring strict silently deletes a legal move.
    """
    return max(1, round(finding_count * share_min))

# Generic, role-aware conversation starters offered as pick-list options in a
# witness lockstep round (hybrid input: pick one of these, or type a custom
# question instead). Not mystery-specific — kept as a static bank rather than
# an extra generation call, since the value here is speed/low-typing-burden,
# not per-mystery flavor.
_CANDIDATE_QUESTIONS = {
    "suspect": [
        "Where were you when the crime happened?",
        "What was your relationship with the victim?",
        "Did you see or hear anything unusual?",
    ],
    "witness": [
        "What exactly did you see?",
        "Did you notice anyone acting strangely?",
        "Is there anything you haven't told anyone yet?",
    ],
    "default": [
        "Where were you when the crime happened?",
        "What did you see or hear?",
        "Do you know of anyone who might have wanted this to happen?",
    ],
}


def _candidate_questions_for(mystery: dict, character_name: str) -> list[str]:
    chars = mystery.get("characters", [])
    char_data = next((c for c in chars if c["name"] == character_name), None)
    role = char_data.get("role", "") if char_data else ""
    return _CANDIDATE_QUESTIONS.get(role, _CANDIDATE_QUESTIONS["default"])


def _format_plot_reveal(mystery: dict) -> dict:
    """Format the mystery's already-generated solution into the end-of-game
    plot reveal. Zero API cost -- pure formatting over content generated once
    at mystery creation (see GenerateRequest/_generate_mystery_dict), never
    regenerated here. Resolves solution.key_evidence (a list of evidence IDs)
    into the full evidence objects so the reveal can name what was found,
    not just cite an ID."""
    solution = mystery.get("solution", {})
    evidence_by_id = {e["id"]: e for e in mystery.get("evidence", [])}
    key_evidence = [
        {"id": eid, "name": evidence_by_id[eid]["name"], "description": evidence_by_id[eid]["description"]}
        for eid in solution.get("key_evidence", [])
        if eid in evidence_by_id
    ]
    return {
        "culprit": solution.get("culprit", ""),
        "method": solution.get("method", ""),
        "motive": solution.get("motive", ""),
        "how_to_deduce": solution.get("how_to_deduce", ""),
        "key_evidence": key_evidence,
    }


def _winner_findings_summary(game: dict, winner_id: str) -> dict:
    """The winning player's own uncovered findings -- witness answers, scene
    investigations, followed leads -- pulled from data already collected
    during play. Zero API cost, pure data shaping. Shown to the whole room at
    game end on purpose (not kept private to the winner): the point is the
    shared reveal of *how* they got there, not just *that* they won.

    Strips "_craft_guidance" from each finding: investigate-area/follow-lead
    findings carry it (internal audit-trail citations, safe to return
    per-player because those calls are private -- see docs/WIRING.md), but
    this summary is broadcast to the whole room, so it needs the same
    server-side-only treatment _resolve_round already gives witness rounds."""
    player = game["players"].get(winner_id, {})

    def _strip_craft_guidance(findings: list) -> list:
        return [{k: v for k, v in f.items() if k != "_craft_guidance"} for f in findings]

    # UNDER APF THE WINNER GATHERED NOTHING. There are no witness/investigation/
    # lead budgets and no per-phase finding lists to read -- findings were assigned.
    # Reading the old keys would return three empty arrays and the reveal would
    # say the winner found nothing, which is the opposite of true.
    session = game.get("apf")
    if session is not None:
        by_kind = {"witness": [], "clue": [], "lead": []}
        shared_ids = set(session["shared"].get(winner_id, []))
        for finding in apf.assigned(session, winner_id):
            by_kind.setdefault(finding["kind"], []).append({
                "id": finding["id"],
                "title": finding["title"],
                "body": finding["body"],
                # Whether they put it on the table is part of HOW they got
                # there, which is what this summary is for.
                "shared": finding["id"] in shared_ids,
            })
        return {
            "witness_findings": by_kind["witness"],
            "investigation_findings": by_kind["clue"],
            "lead_findings": by_kind["lead"],
        }

    return {
        "witness_findings": _strip_craft_guidance(player.get("witness_findings", [])),
        "investigation_findings": _strip_craft_guidance(player.get("investigation_findings", [])),
        "lead_findings": _strip_craft_guidance(player.get("lead_findings", [])),
    }


def _generate_resolution_narrative(game: dict, plot_reveal: dict, winner_findings: dict) -> tuple[str, list]:
    """
    One Claude call, craft-guidance-informed: turns the already-resolved
    plot_reveal + the winner's own findings into a satisfying, well-paced
    reveal narrative for the whole table -- not a restatement of the
    structured solution fields, an actual "moment." Guided by C5 (The
    Resolution) + M6 (The Reveal Mechanic) craft findings -- e.g. "a reveal
    must feel earned, not just correct" (Rian Johnson), "the controlled
    release of information... is really, really hard" (Moffat) -- plus
    PARTY_CRAFT_FINDINGS.md's Accusation/Reveal Phase guidance for the
    social, shared-table dimension screen craft alone doesn't cover.

    max_items=8 here (vs. the other three call-sites' default 5): this pool
    is unusually well-populated (19 matching entries) and this is the single
    highest-stakes narrative beat in the game, so it gets more room. Not a
    change to the shared ranking/confidence-tier logic itself -- just this
    call's own budget.

    No new facts are invented -- the prompt explicitly hands over the
    already-determined solution and forbids introducing anything not listed,
    same "adapt, don't invent" discipline _generate_mystery_dict already
    uses on sampled parts.
    """
    mystery = game["mystery"]
    s = mystery.get("setting", {})
    c = mystery.get("crime", {})
    winner_name = game["players"].get(game["winner"], {}).get("name", "the winner")

    all_findings = (
        [f'"{f.get("question", "")}" -> {f.get("response", "")}' for f in winner_findings.get("witness_findings", [])]
        + [f'investigated {f.get("area_name", "")}: {f.get("findings", "")}' for f in winner_findings.get("investigation_findings", [])]
        + [f'followed lead "{f.get("lead_title", "")}": {f.get("findings", "")}' for f in winner_findings.get("lead_findings", [])]
    )
    findings_block = "\n".join(f"  - {f}" for f in all_findings) if all_findings else "  (no recorded findings)"
    evidence_block = "\n".join(
        f"  - {e['name']}: {e['description']}" for e in plot_reveal.get("key_evidence", [])
    ) or "  (none)"

    guidance_entries = craft_grounding.get_craft_guidance(**craft_grounding.CALL_SITE_TAGS["resolution_reveal"], max_items=8)
    guidance_block = craft_grounding.format_guidance_block(guidance_entries)

    prompt = f"""\
You are writing the end-of-game reveal narrative for a social deduction mystery game.
{winner_name} just correctly named the culprit and won.

SETTING: {s.get('location', '')}, {s.get('time_period', '')}
CRIME: {c.get('what_happened', '')}

THE SOLUTION (already determined -- do not change or contradict any fact here):
  Culprit: {plot_reveal.get('culprit', '')}
  Method: {plot_reveal.get('method', '')}
  Motive: {plot_reveal.get('motive', '')}
  How it was deduced: {plot_reveal.get('how_to_deduce', '')}

KEY EVIDENCE:
{evidence_block}

WHAT {winner_name.upper()} PERSONALLY UNCOVERED DURING PLAY:
{findings_block}

{guidance_block}

Write a satisfying reveal narrative for the whole table to read together -- the kind of moment
that makes the mystery-solving worthwhile, not a dry restatement of the facts above. Weave in
specifically what {winner_name} found and how it connected to the solution. Do not introduce any
new facts, characters, or evidence not listed above -- narrate the reveal, don't invent one.
4-7 sentences.

Return ONLY the narrative text -- no JSON, no headers, no quotation marks around it."""

    narrative = llm(
        prompt,
        system="You are a mystery game narrator staging the final reveal. Be vivid, satisfying, "
               "and precise -- never contradict the given solution.",
    )
    return narrative.strip(), craft_grounding.guidance_provenance(guidance_entries)


def _fallback_resolution_narrative(game: dict, plot_reveal: dict) -> str:
    """The reveal when the narrative call cannot be made. Assembled from fields
    the mystery already carries -- zero API cost, and no invention: every
    sentence here was written by the generation call that produced the mystery.
    """
    culprit = (plot_reveal.get("culprit") or "").strip()
    method = (plot_reveal.get("method") or "").strip()
    motive = (plot_reveal.get("motive") or "").strip()
    deduce = (plot_reveal.get("how_to_deduce") or "").strip()

    # The four fields _format_plot_reveal already resolves, read in the order a
    # reveal is told: who, how, why, and how it could have been worked out.
    lines = []
    if culprit:
        lines.append(f"It was {culprit}.")
    if method:
        lines.append(method)
    if motive:
        lines.append(motive)
    if deduce:
        lines.append(deduce)
    if lines:
        return "\n\n".join(lines)

    # A mystery carrying none of them has bigger problems than its reveal; say
    # something true rather than nothing.
    return "The case is closed, but this mystery carries no written resolution."


def _build_resolution_reveal(game: dict, winner_id: str) -> dict:
    """
    Shared by the game_won broadcast and GET /result so a client that missed
    the broadcast (late join, reconnect) sees the identical reveal.

    resolution_narrative is generated once -- the first call after the win
    -- and cached on game["resolution_narrative"]. GET /result never
    regenerates it: a reconnecting client must see the exact same wording
    everyone else already saw, not a fresh (and differently-phrased) LLM
    roll each time it's fetched. Craft-guidance citations are stashed
    server-side only (game["_resolution_craft_guidance"]) for audit
    purposes -- same "never player-facing" treatment as every other
    craft-guidance call-site's provenance.
    """
    plot_reveal = _format_plot_reveal(game["mystery"])
    winner_findings = _winner_findings_summary(game, winner_id)

    if game.get("resolution_narrative") is None:
        # THE WIN MUST NOT DEPEND ON A NETWORK CALL. This is the last play-time
        # Claude call on the critical path, and until build-order step 5 removes
        # it, a 401 / rate limit / timeout here took the whole win down with a
        # 500 -- measured, Session 42, driving a full APF game over HTTP. The
        # stage-1 test is "reach the result screen without an error", so the
        # reveal degrades to the mystery's OWN already-generated resolution
        # prose rather than failing. That text was written and paid for at
        # generation time; it is a plainer reveal, not a missing one.
        try:
            narrative, craft_guidance = _generate_resolution_narrative(game, plot_reveal, winner_findings)
        except Exception as e:  # noqa: BLE001 -- any failure, not a taxonomy of them
            print(f"[resolution] narrative call failed ({type(e).__name__}); "
                  f"falling back to the mystery's own resolution text")
            narrative, craft_guidance = _fallback_resolution_narrative(game, plot_reveal), []
        with _games_lock:
            game["resolution_narrative"] = narrative
            game["_resolution_craft_guidance"] = craft_guidance

    return {
        "plot_reveal": plot_reveal,
        "winner_findings": winner_findings,
        "resolution_narrative": game["resolution_narrative"],
    }


def _new_game_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def _new_player_id() -> str:
    return str(uuid.uuid4())


def _get_game(game_id: str) -> Optional[dict]:
    with _games_lock:
        return _games.get(game_id)


def _fingerprint(question: str) -> str:
    """Normalised lowercase question key for duplicate detection."""
    return question.strip().lower()


def _investigate_area_with_ai(mystery: dict, area: dict, player_name: str) -> tuple[str, list]:
    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    guidance_entries = craft_grounding.get_craft_guidance(**craft_grounding.CALL_SITE_TAGS["investigate_area"], max_items=5)
    guidance_block = craft_grounding.format_guidance_block(guidance_entries)
    prompt = (
        f"You are an AI narrator for a mystery game. A detective named {player_name} "
        f"is investigating '{area['name']}' at {setting.get('location', 'the scene')} "
        f"({setting.get('time_period', '')}).\n\n"
        f"Crime overview: {crime.get('what_happened', '')}\n\n"
        f"Private context for this area: {area.get('investigation_prompt', '')}\n\n"
        f"{guidance_block}\n\n"
        "Describe in 2–4 sentences what the detective finds when searching this area. "
        "Be atmospheric and specific. May include clues, red herrings, or atmosphere. "
        "Do not reveal the culprit directly."
    )
    findings = llm(prompt, system="You are a mystery game narrator. Be vivid and specific.")
    return findings, craft_grounding.guidance_provenance(guidance_entries)


def _follow_lead_with_ai(mystery: dict, lead: dict, player_name: str) -> tuple[str, list]:
    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    guidance_entries = craft_grounding.get_craft_guidance(**craft_grounding.CALL_SITE_TAGS["follow_lead"], max_items=5)
    guidance_block = craft_grounding.format_guidance_block(guidance_entries)
    prompt = (
        f"You are an AI narrator for a mystery game. A detective named {player_name} "
        f"is following the lead: '{lead['title']}' at {setting.get('location', 'the scene')}.\n\n"
        f"Crime overview: {crime.get('what_happened', '')}\n\n"
        f"Private context for this lead: {lead.get('investigation_prompt', '')}\n\n"
        f"{guidance_block}\n\n"
        "Describe in 2–4 sentences what the detective discovers when following this lead. "
        "Be specific and atmospherically consistent with the mystery. "
        "Do not reveal the culprit directly."
    )
    findings = llm(prompt, system="You are a mystery game narrator. Be vivid and specific.")
    return findings, craft_grounding.guidance_provenance(guidance_entries)


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
# Maintains one set of open WebSocket connections per game_id (room).
# All server-side actions that change shared state call _ws_broadcast()
# so clients receive push events instead of polling.
#
# Push event envelope:
#   { "event": str, "data": dict }
#
# Events pushed today:
#   player_joined      — { name }
#   clues_shared       — { sender_name, phase, clues: [...] }
#   block_updated      — { witness: [...], investigation: [...], lead: [...] }
#   player_phase_done  — { player_name, phase }
#   round_opened       — { round_type, expected_players: [name, ...], timeout_seconds }
#   player_submitted   — { player_name, submitted_count, expected_count }
#   round_generating   — { round_type, timed_out: bool, missing_players: [name, ...] }
#   round_revealed     — { round_type, result }
#   accusation_made    — { player_name, accused_name, correct: bool } — every attempt, public
#   game_won            — { winner_player_id, winner_name, solution }

class ConnectionManager:
    def __init__(self) -> None:
        # game_id → list of open WebSocket connections
        self._rooms: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, game_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(game_id, []).append(ws)

    async def disconnect(self, game_id: str, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(game_id, [])
            if ws in room:
                room.remove(ws)

    async def broadcast(self, game_id: str, event: str, data: dict) -> None:
        payload = json.dumps({"event": event, "data": data})
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._rooms.get(game_id, []):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._rooms[game_id].remove(ws)


_ws_manager = ConnectionManager()


def _broadcast_sync(game_id: str, event: str, data: dict) -> None:
    """
    Fire-and-forget WebSocket broadcast from a synchronous context
    (e.g. inside a regular FastAPI endpoint or thread).
    Creates a new event loop task if the running loop allows it.
    Safe to call from non-async code.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _ws_manager.broadcast(game_id, event, data), loop
            )
        else:
            loop.run_until_complete(_ws_manager.broadcast(game_id, event, data))
    except RuntimeError:
        pass  # No event loop available — server is probably shutting down


# ---------------------------------------------------------------------------
# Lockstep round state machine
# ---------------------------------------------------------------------------
# Game-level synchronization, independent of the legacy per-player "phase" field
# above: every player must submit before anyone advances, rather than each player
# moving through witness/investigation/lead independently at their own pace.
#
# Stage sequence: "submitting" -> "generating" -> "revealed"
#
# This module owns the round mechanics only — opening a round, collecting
# submissions, detecting when everyone (or the timeout) says "go", and holding
# the eventual result once it's produced. It does not decide what a "witness"
# or "investigation" round's submission payload or generated result look like;
# that content is owned separately, per round_type, by the code that calls
# _open_round() and _resolve_round().
_DEFAULT_ROUND_TIMEOUT = 90  # seconds


def _open_round(game: dict, round_type: str, timeout_seconds: int = _DEFAULT_ROUND_TIMEOUT,
                 metadata: Optional[dict] = None) -> dict:
    """
    Start a new lockstep round. Snapshots the currently-joined players as the
    set required to submit — a player joining mid-round is not added to it and
    will be included starting with the next round.
    """
    metadata = metadata or {}
    prep_fn = _ROUND_PREP.get(round_type)
    extra_fields = prep_fn(game, metadata) if prep_fn else {}

    with _games_lock:
        expected = list(game["players"].keys())
        game["round"] = {
            "round_type": round_type,
            "expected_players": expected,
            "submissions": {},
            "opened_at": time.time(),
            "timeout_seconds": timeout_seconds,
            "metadata": metadata,
            "result": None,
            **extra_fields,
        }
        game["stage"] = "submitting"
        round_snapshot = dict(game["round"])

    _broadcast_sync(game["game_id"], "round_opened", {
        "round_type": round_type,
        "expected_players": [game["players"][pid]["name"] for pid in expected],
        "timeout_seconds": timeout_seconds,
        "metadata": metadata,
        **extra_fields,
    })
    return round_snapshot


def _maybe_advance_to_generating(game: dict) -> bool:
    """
    If every expected player has submitted, transition submitting -> generating.
    Returns True if this call caused the transition.
    """
    round_ = game["round"]
    if round_ is None or game["stage"] != "submitting":
        return False
    if not all(pid in round_["submissions"] for pid in round_["expected_players"]):
        return False

    with _games_lock:
        game["stage"] = "generating"

    _broadcast_sync(game["game_id"], "round_generating", {
        "round_type": round_["round_type"],
        "timed_out": False,
        "missing_players": [],
    })
    _dispatch_round_generation(game)
    return True


def _check_round_timeout(game: dict) -> bool:
    """
    Lazy timeout check — call at the top of any round endpoint. If the
    submission window has expired with players still missing, auto-advances to
    "generating" anyway (missing players are recorded, not silently dropped)
    so one absent player can't stall the game indefinitely.
    Returns True if this call caused a timeout transition.
    """
    round_ = game["round"]
    if round_ is None or game["stage"] != "submitting":
        return False
    if time.time() - round_["opened_at"] < round_["timeout_seconds"]:
        return False

    missing = [pid for pid in round_["expected_players"] if pid not in round_["submissions"]]
    with _games_lock:
        game["stage"] = "generating"

    _broadcast_sync(game["game_id"], "round_generating", {
        "round_type": round_["round_type"],
        "timed_out": True,
        "missing_players": [game["players"][pid]["name"] for pid in missing if pid in game["players"]],
    })
    _dispatch_round_generation(game)
    return True


def _resolve_round(game: dict, result: dict) -> None:
    """
    Attach the generated result (owned by round_type-specific code) and
    transition generating -> revealed.

    Round generators may include a "_craft_guidance" key (a citation list
    from craft_grounding.guidance_provenance) for audit purposes — useful
    during playtesting to trace which craft sources informed a given
    witness scene. That key is stored server-side only, on round_ itself,
    and popped off before result is broadcast — it goes to every player in
    the game over WebSocket, and craft-guidance citations are internal
    tooling, not player-facing content.
    """
    round_ = game["round"]
    with _games_lock:
        round_["_craft_guidance"] = result.pop("_craft_guidance", None)
        round_["result"] = result
        game["stage"] = "revealed"

    _broadcast_sync(game["game_id"], "round_revealed", {
        "round_type": round_["round_type"],
        "result": result,
    })


def _round_status_payload(game: dict) -> dict:
    """Waiting-room view: who's submitted, who hasn't, time left."""
    _check_round_timeout(game)
    round_ = game["round"]
    if round_ is None:
        return {"stage": None, "round_type": None}

    submitted_ids = set(round_["submissions"].keys())
    pending_names = [
        game["players"][pid]["name"]
        for pid in round_["expected_players"]
        if pid not in submitted_ids and pid in game["players"]
    ]
    seconds_remaining = max(0, round_["timeout_seconds"] - (time.time() - round_["opened_at"]))
    return {
        "stage": game["stage"],
        "round_type": round_["round_type"],
        "submitted_count": len(submitted_ids),
        "expected_count": len(round_["expected_players"]),
        "pending_players": pending_names,
        "seconds_remaining": round(seconds_remaining, 1) if game["stage"] == "submitting" else 0,
        "result": round_["result"],
    }


# ---------------------------------------------------------------------------
# Round-type implementations
# ---------------------------------------------------------------------------
# Each round_type registers an optional "prep" hook (extra fields to attach
# when the round opens, e.g. a candidate-question pick-list) and a "generate"
# hook (produces the eventual result once every player has submitted or the
# round timed out). Dispatched by round_type — see _dispatch_round_generation.

def _witness_prep(game: dict, metadata: dict) -> dict:
    """Prep for a 'witness' round: attach candidate pick-list questions for the target witness."""
    character_name = metadata.get("character_name", "")
    return {"candidate_questions": _candidate_questions_for(game["mystery"], character_name)}


def _generate_witness_scene(game: dict, round_: dict) -> dict:
    """
    Generate the result for a 'witness' round: one shared dramatized scene,
    bounded to 2-3 sentences regardless of how many questions were pooled,
    plus a private answer to every individual question each player submitted.
    No random distribution beyond that — a player always gets their own
    answers, and the scene is what's shared with everyone.
    """
    mystery = game["mystery"]
    character_name = round_["metadata"].get("character_name", "")
    chars = mystery.get("characters", [])
    char_data = next((c for c in chars if c["name"] == character_name), {})

    s = mystery.get("setting", {})
    c = mystery.get("crime", {})
    setting_summary = (
        f"Location: {s.get('location', '')}\n"
        f"Time period: {s.get('time_period', '')}\n"
        f"Crime: {c.get('what_happened', '')}"
    )
    char_context = (
        f"Role: {char_data.get('role', 'suspect')}\n"
        f"Occupation: {char_data.get('occupation', '')}\n"
        f"Alibi: {char_data.get('alibi', '')}\n"
        f"Secret: {char_data.get('secret', '')}\n"
        f"Motive: {char_data.get('motive', '')}"
    )

    # Pool questions across players, deduped by fingerprint so overlapping
    # questions surface once (with all their askers) instead of N near-duplicates.
    by_fingerprint: dict[str, dict] = {}
    for pid, payload in round_["submissions"].items():
        player_name = game["players"].get(pid, {}).get("name", "Unknown")
        for q in payload.get("questions", []):
            q = q.strip()
            if not q:
                continue
            fp = _fingerprint(q)
            entry = by_fingerprint.setdefault(fp, {"question": q, "askers": []})
            entry["askers"].append((pid, player_name))

    pooled = list(by_fingerprint.values())
    empty_answers = {pid: [] for pid in round_["submissions"].keys()}
    if not pooled:
        return {"scene": f"{character_name} waited, but nobody had a question this round.",
                "scene_covers": [], "answers": empty_answers}

    for i, entry in enumerate(pooled):
        entry["qid"] = f"Q{i + 1}"
    questions_block = "\n".join(
        f"  {p['qid']}: \"{p['question']}\" (asked by: {', '.join(name for _, name in p['askers'])})"
        for p in pooled
    )

    guidance_entries = craft_grounding.get_craft_guidance(**craft_grounding.CALL_SITE_TAGS["witness_scene"], max_items=5)
    guidance_block = craft_grounding.format_guidance_block(guidance_entries)

    prompt = f"""\
You are {character_name} in this mystery, being interrogated by a group of detectives at once.

SETTING:
{setting_summary}

YOUR PRIVATE CHARACTER DETAILS (do NOT reveal directly):
{char_context}

Be evasive if you are the culprit. Be defensive if you are innocent but suspicious.
Do NOT directly reveal the real culprit.

{guidance_block}

The detectives asked these questions this round (some were asked by more than one):
{questions_block}

Produce two things:

1. A SHARED SCENE: a short, watchable dramatization of this interrogation — 2 to 3
   sentences, no matter how many questions were pooled above. Prioritize whichever
   question(s) were asked by more than one detective, plus one character/atmosphere
   flourish moment. Keep this the same length regardless of how many questions were
   pooled — condense, don't list them all.
2. A private ANSWER to every individual question above, keyed by its id — these are
   NOT shown to the group, only to whichever detective(s) asked that question.

Return ONLY valid JSON:
{{
  "scene": "2-3 sentence dramatized scene, written to be watched/read by the whole group",
  "scene_covers": ["Q1", "Q3"],
  "answers": {{"Q1": "private in-character answer, 1-3 sentences", "Q2": "..."}}
}}"""

    raw = llm(prompt, system="You are a mystery game character. Stay in character. Return only valid JSON.")
    parsed = _parse_json(raw)

    answers_by_qid = parsed.get("answers", {})
    per_player_answers: dict[str, list] = {pid: [] for pid in round_["submissions"].keys()}
    for entry in pooled:
        answer = answers_by_qid.get(entry["qid"], "")
        for pid, _name in entry["askers"]:
            per_player_answers[pid].append({"question": entry["question"], "answer": answer})

    scene_covers_qids = set(parsed.get("scene_covers", []))
    scene_covers_text = [e["question"] for e in pooled if e["qid"] in scene_covers_qids]

    return {
        "scene": parsed.get("scene", ""),
        "scene_covers": scene_covers_text,
        "answers": per_player_answers,   # {player_id: [{question, answer}, ...]} — private per player
        # Popped off by _resolve_round before broadcast — see that function's
        # docstring for why this never reaches the WebSocket payload.
        "_craft_guidance": craft_grounding.guidance_provenance(guidance_entries),
    }


def _prompt_vote_prep(game: dict, metadata: dict) -> dict:
    """Prep for a 'prompt_vote' round: the candidate list is every submitted
    prompt except the one that generated the mystery just played (voting for
    what to play next shouldn't re-offer what the group just did)."""
    used_pid = game.get("used_prompt_player_id")
    candidates = [
        {"player_id": pid, "name": entry["name"], "prompt_text": entry["prompt_text"]}
        for pid, entry in game["submitted_prompts"].items()
        if pid != used_pid
    ]
    return {"candidates": candidates}


def _tally_prompt_vote(game: dict, round_: dict) -> dict:
    """
    Tally votes for 'prompt_vote' -- pure Python, zero API cost. Majority
    wins. On a tie, the game's winner breaks it themselves *unless* they also
    won the mystery immediately before this one -- in that case tie-break
    power passes to a random pick instead, so one dominant player can't also
    keep controlling what the group plays next. No tie-break needed at all
    if there's only one candidate or no votes were cast for more than one.
    """
    candidates = {c["player_id"]: c for c in round_.get("candidates", [])}
    tally: dict[str, int] = {pid: 0 for pid in candidates}
    for payload in round_["submissions"].values():
        voted_for = payload.get("vote_for_player_id")
        if voted_for in tally:
            tally[voted_for] += 1

    if not candidates:
        return {"tie": False, "chosen_player_id": None, "tally": {}, "note": "no candidates to vote on"}

    max_votes = max(tally.values(), default=0)
    leaders = [pid for pid, count in tally.items() if count == max_votes]

    if len(leaders) == 1:
        return {"tie": False, "chosen_player_id": leaders[0], "tally": tally}

    game_winner = game.get("winner")
    win_history = game.get("win_history", [])
    winner_is_repeat = bool(win_history) and win_history[-1] == game_winner

    if game_winner in leaders and not winner_is_repeat:
        return {
            "tie": True, "tied_player_ids": leaders, "tally": tally,
            "chosen_player_id": None, "awaiting_tiebreak_from": game_winner,
        }

    # Either the tie doesn't include the game winner's own candidate, or the
    # winner also won last time -- either way, break it randomly rather than
    # handing (or re-handing) tie-break power to them.
    chosen = random.choice(leaders)
    reason = (
        "same player won the mystery right before this one, so tie-break passed to a random pick"
        if winner_is_repeat else
        "tie didn't include the game winner's own candidate, resolved randomly"
    )
    return {
        "tie": True, "tied_player_ids": leaders, "tally": tally,
        "chosen_player_id": chosen, "auto_resolved": True, "reason": reason,
    }


_ROUND_PREP = {
    "witness": _witness_prep,
    "prompt_vote": _prompt_vote_prep,
}

_ROUND_GENERATORS = {
    "witness": _generate_witness_scene,
    "prompt_vote": _tally_prompt_vote,
}


def _reset_game_for_next_mystery(game: dict, chosen_prompt_text: str) -> str:
    """
    Reset an already-played room in place for a new mystery -- same
    game_id/room code, same player roster, nobody leaves or rejoins. This is
    the "same room persists across mysteries" mechanic: records the
    concluded game's winner into win_history (read by _tally_prompt_vote's
    tie-break rule), then clears everything scoped to a single mystery
    before kicking off generation from the chosen prompt. Returns a job_id.
    """
    cfg = _DIFFICULTY_CONFIG[game["difficulty"]]
    with _games_lock:
        game["win_history"].append(game["winner"])
        game["mystery"] = None
        game["used_prompt_player_id"] = None
        game["submitted_prompts"] = {}
        game["shared_pool"] = {"witness": [], "investigation": [], "lead": []}
        game["block_pool"] = {"witness": [], "investigation": [], "lead": []}
        game["stage"] = None
        game["round"] = None
        game["winner"] = None
        game["accusations"] = []
        game["resolution_narrative"] = None
        game["_resolution_craft_guidance"] = None
        for player in game["players"].values():
            player["phase"] = "witness"
            player["witness_budget"] = cfg["witness_budget"]
            player["investigation_budget"] = cfg["investigation_budget"]
            player["leads_used"] = []
            player["witness_findings"] = []
            player["investigation_findings"] = []
            player["lead_findings"] = []

    job_id = _job_create()
    thread = threading.Thread(
        target=_run_game_generation_job,
        args=(game["game_id"], job_id, chosen_prompt_text, True),
        daemon=True,
    )
    thread.start()
    return job_id


def _dispatch_round_generation(game: dict) -> None:
    """
    Kick off the round_type-specific generator in a background thread once a
    round has moved to "generating", then resolve the round with its result.
    Round types with no registered generator (future work not built yet)
    fall through safely rather than erroring.
    """
    round_ = game["round"]
    generator = _ROUND_GENERATORS.get(round_["round_type"])
    if generator is None:
        return

    def _run() -> None:
        try:
            result = generator(game, round_)
        except Exception as exc:
            result = {"error": str(exc)}
        _resolve_round(game, result)

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Choose Your Mystery — Backend", version="1.0.0")

# Allow the Godot client (and local dev tools) to call this server.
# In production, restrict origins to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve mobile.html and any other static phone-client assets from server/static/
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    opening_narration: bool = True

class InterrogateRequest(BaseModel):
    mystery: dict                  # full mystery dict (sent by client)
    character_name: str
    question: str

class RateRequest(BaseModel):
    mystery_slug: str
    rating: int                    # 1–10

class AsyncGenerateRequest(BaseModel):
    prompt: str
    opening_narration: bool = True

class CreateGameRequest(BaseModel):
    host_name: str
    difficulty: str = "MEDIUM"   # "EASY" | "MEDIUM" | "HARD"
    mystery_slug: Optional[str] = None  # skip prompt-collection, attach an already-generated mystery immediately

class JoinGameRequest(BaseModel):
    player_name: str

class SubmitPromptRequest(BaseModel):
    player_id: str
    prompt_text: str

class InvestigateAreaRequest(BaseModel):
    player_id: str
    area_id: str

class FollowLeadRequest(BaseModel):
    player_id: str
    lead_id: str

class SharePhaseRequest(BaseModel):
    player_id: str
    phase: str          # "witness" | "investigation" | "lead"
    selected_ids: list  # list of clue/finding IDs the player chose to share

class ApfOpenRequest(BaseModel):
    player_id: str

class ApfShareRequest(BaseModel):
    player_id: str
    finding_ids: list   # ids of ASSIGNED findings this player puts on the table

class StartGameRequest(BaseModel):
    player_id: str

class OpenRoundRequest(BaseModel):
    player_id: str       # must be the host
    round_type: str      # e.g. "witness" — meaning owned by round-type-specific code
    timeout_seconds: int = _DEFAULT_ROUND_TIMEOUT
    metadata: dict = {}  # round-type-specific, e.g. {"character_name": "..."} for a witness round

class SubmitRoundRequest(BaseModel):
    player_id: str
    payload: dict         # shape is round_type-specific, not validated here

class ResolveRoundRequest(BaseModel):
    result: dict           # shape is round_type-specific, not validated here

class AccuseRequest(BaseModel):
    player_id: str
    culprit_name: str

class TiebreakRequest(BaseModel):
    player_id: str
    chosen_player_id: str

class NextMysteryStartRequest(BaseModel):
    player_id: str

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Quick liveness check — no API calls."""
    return {"ok": True}


@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Generate a mystery from a freetext prompt.

    Flow:
      1. Sample registry parts (free)
      2. Claude call: generate mystery JSON
      3. Localization pass (Claude call, or free if modern era)
      4. Coherence check (free)
      5. Optional: opening narration (Claude call)
      6. Gate + save to generated/ or rejected/ (free)
      7. Append one ledger row (free)
      8. Return full mystery dict

    SESSION ANNOTATION: This is the core endpoint. If this works,
    Phase 1 is functionally complete.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")

    with _ledger_attempt(req.prompt) as (_attempt, _state):
        return _generate_inner(req, _state)


def _generate_inner(req: "GenerateRequest", _state: dict) -> dict:
    mystery_dict, recipe = _generate_mystery_dict(req.prompt)
    mystery_dict = _run_localization(mystery_dict)
    mystery_dict = _run_coherence(mystery_dict)

    if req.opening_narration:
        mystery_dict["opening_narration"] = _generate_opening_narration(
            mystery_dict).get("opening_narration", "")

    slug = _save_mystery(mystery_dict)
    mystery_dict["_slug"] = slug
    _state["slug"] = slug
    _state["mystery"] = mystery_dict
    return mystery_dict


@app.post("/generate/async")
def generate_async(req: AsyncGenerateRequest):
    """
    Kick off mystery generation in a background thread and return a job_id immediately.
    The client polls GET /jobs/{job_id} for progress and the final result.

    Stages returned in "stage":
      "Queued" → "Generating mystery…" → "Localizing characters…"
      → "Checking coherence…" → ["Writing the opening…"] → "Saving…" → "Done"

    Status values: "queued" | "running" | "done" | "error"
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")
    job_id = _job_create()
    thread = threading.Thread(
        target=_run_generation_job,
        args=(job_id, req.prompt, req.opening_narration),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """
    Poll for job status.

    Returns:
      { "status": "queued"|"running"|"done"|"error",
        "stage":  human-readable progress label,
        "result": <mystery dict> | null,
        "error":  "" | "error message" }
    """
    job = _job_get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found (may have expired)")
    return {
        "status": job["status"],
        "stage":  job["stage"],
        "result": job["result"],
        "error":  job["error"],
    }


@app.get("/play", response_class=HTMLResponse)
async def play_page():
    """Serve the mobile phone client."""
    mobile_html = _static_dir / "mobile.html"
    if mobile_html.exists():
        return HTMLResponse(mobile_html.read_text())
    return HTMLResponse("<h2>mobile.html not found — server/static/mobile.html is missing.</h2>", status_code=503)


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(ws: WebSocket, game_id: str, player_id: str = ""):
    """
    Persistent WebSocket connection for a game room.
    Clients connect here to receive real-time push events:
      - clues_shared      when another player's Share Selection is submitted
      - block_updated     when the block pool changes
      - player_joined     when a new player joins
      - player_phase_done when a player advances phase

    The client can also send messages, currently only used to confirm readiness:
      { "action": "ping" }  → ignored (keepalive)
    """
    game = _get_game(game_id)
    if game is None:
        await ws.close(code=4004, reason="game not found")
        return

    await _ws_manager.connect(game_id, ws)
    player_name = ""
    if player_id and player_id in game["players"]:
        player_name = game["players"][player_id]["name"]
        await _ws_manager.broadcast(game_id, "player_joined", {"name": player_name})

    try:
        while True:
            # Keep the connection alive; ignore any messages from client
            await ws.receive_text()
    except WebSocketDisconnect:
        await _ws_manager.disconnect(game_id, ws)


@app.post("/games/create")
def create_game(req: CreateGameRequest):
    """
    Create a new multiplayer game room. Returns the game_id (room code) and
    per-difficulty budgets.

    Two modes:
    - `mystery_slug` omitted (the normal path): the room opens empty — no
      mystery yet. Players join and submit prompt suggestions via
      POST /games/{id}/prompts/submit while waiting; the host's submission
      is what actually generates the mystery once they POST /games/{id}/start.
    - `mystery_slug` given: skips prompt collection and attaches an
      already-generated mystery immediately (quick-start / dev / testing path).
    """
    difficulty = req.difficulty.upper()
    if difficulty not in _DIFFICULTY_CONFIG:
        raise HTTPException(status_code=400, detail="difficulty must be EASY, MEDIUM, or HARD")

    mystery = None
    if req.mystery_slug:
        generated_dir = _DB_PATH / "generated"
        matches = list(generated_dir.glob(f"{req.mystery_slug}_*.json"))
        if not matches:
            raise HTTPException(status_code=404, detail="mystery not found")
        with open(sorted(matches)[-1]) as f:
            mystery = json.load(f)

    cfg = _DIFFICULTY_CONFIG[difficulty]
    game_id = _new_game_id()
    host_id = _new_player_id()

    session = {
        "game_id": game_id,
        "mystery": mystery,
        "difficulty": difficulty,
        "share_min": cfg["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
        "players": {
            host_id: {
                "name": req.host_name,
                "is_host": True,
                "phase": "witness",
                "witness_budget": cfg["witness_budget"],
                "investigation_budget": cfg["investigation_budget"],
                "leads_used": [],
                "witness_findings": [],
                "investigation_findings": [],
                "lead_findings": [],
            }
        },
        "submitted_prompts": {},  # player_id -> {"name": str, "prompt_text": str, "ts": float}
        "used_prompt_player_id": None,  # whose submission drove the mystery currently attached
        "win_history": [],  # [player_id, ...] one entry per mystery played in this room, oldest first
        "shared_pool": {"witness": [], "investigation": [], "lead": []},
        "block_pool": {"witness": [], "investigation": [], "lead": []},
        "stage": None,
        "round": None,
        "winner": None,
        "accusations": [],
        "resolution_narrative": None,  # cached once generated -- see _build_resolution_reveal
        "_resolution_craft_guidance": None,  # server-side audit trail only, never sent to clients
        "ts": time.time(),
    }
    with _games_lock:
        _games[game_id] = session

    return {
        "game_id": game_id,
        "player_id": host_id,
        "share_min": cfg["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
    }


@app.post("/games/{game_id}/join")
def join_game(game_id: str, req: JoinGameRequest):
    """Register a new player in the game session."""
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player_id = _new_player_id()
    cfg = _DIFFICULTY_CONFIG[game["difficulty"]]
    with _games_lock:
        game["players"][player_id] = {
            "name": req.player_name,
            "is_host": False,
            "phase": "witness",
            "witness_budget": cfg["witness_budget"],
            "investigation_budget": cfg["investigation_budget"],
            "leads_used": [],
            "witness_findings": [],
            "investigation_findings": [],
            "lead_findings": [],
        }
    _broadcast_sync(game_id, "player_joined", {"name": req.player_name})
    return {
        "player_id": player_id,
        "game_id": game_id,
        "share_min": game["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
    }


@app.post("/games/{game_id}/prompts/submit")
def submit_prompt(game_id: str, req: SubmitPromptRequest):
    """
    A player suggests a mystery prompt while the lobby is waiting to start
    (e.g. "Smurf murder mystery", "Mystery on Mars"). Only meaningful before
    the host starts the game — the host's own submission is what actually
    drives generation; everyone else's are kept for the post-game vote on
    what to play next. Submitting again overwrites this player's prior entry.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if game["mystery"] is not None:
        raise HTTPException(status_code=400, detail="mystery already generated for this game")
    player = game["players"].get(req.player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="player not in game")
    prompt_text = req.prompt_text.strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="prompt_text must not be empty")

    with _games_lock:
        game["submitted_prompts"][req.player_id] = {
            "name": player["name"],
            "prompt_text": prompt_text,
            "ts": time.time(),
        }
    _broadcast_sync(game_id, "prompt_submitted", {
        "player_name": player["name"],
        "is_host": player["is_host"],
    })
    return {"ok": True, "submitted_count": len(game["submitted_prompts"])}


@app.get("/games/{game_id}/mystery-brief")
def mystery_brief(game_id: str):
    """
    Returns the public-facing mystery data for phone clients.
    Strips private fields (investigation_prompt, solution) before sending.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    mystery = game["mystery"]
    if mystery is None:
        raise HTTPException(status_code=400, detail="mystery not yet generated — waiting on the host to start the game")
    # Strip server-only fields
    safe = {k: v for k, v in mystery.items()
            if k not in ("_provenance", "_coherence")}
    # Remove investigation_prompt from areas and leads (server-side only)
    # discovery/analysis are the pre-written search results. Single-player reads
    # them straight out of the mystery dict, which is fine -- that client already
    # holds the solution. Multiplayer resolves areas server-side through
    # /games/{id}/investigate, so shipping them here would casefile every clue to
    # every player the moment the game started.
    safe["investigation_areas"] = [
        {k: v for k, v in a.items()
         if k not in ("investigation_prompt", "discovery", "analysis")}
        for a in safe.get("investigation_areas", [])
    ]
    safe["characters"] = [
        {k: v for k, v in c.items() if k != "statement"}
        for c in safe.get("characters", [])
    ]
    safe["leads"] = [
        {k: v for k, v in l.items() if k != "investigation_prompt"}
        for l in safe.get("leads", [])
    ]
    # Never send the solution to clients
    safe.pop("solution", None)
    safe["witness_budget"] = _DIFFICULTY_CONFIG[game["difficulty"]]["witness_budget"]
    safe["investigation_budget"] = _DIFFICULTY_CONFIG[game["difficulty"]]["investigation_budget"]
    return safe


@app.get("/games/{game_id}/lobby")
def get_lobby(game_id: str):
    """Current lobby state: player list + mystery title/setting (once generated,
    otherwise null) + difficulty + how many prompt suggestions are in."""
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    mystery = game["mystery"]
    return {
        "game_id": game_id,
        "title": mystery.get("title", "Mystery") if mystery else None,
        "setting": mystery.get("setting", {}) if mystery else None,
        "difficulty": game["difficulty"],
        "submitted_prompt_count": len(game["submitted_prompts"]),
        "players": [
            {
                "id": pid,
                "name": p["name"],
                "is_host": p["is_host"],
                "has_submitted_prompt": pid in game["submitted_prompts"],
            }
            for pid, p in game["players"].items()
        ],
    }


@app.post("/games/{game_id}/start")
def start_game(game_id: str, req: StartGameRequest):
    """
    Host starts the game.

    Room-first flow (the normal case -- POST /games/create was called
    without a mystery_slug): kicks off generation in a background thread
    using the *host's own* submitted prompt (POST /games/{id}/prompts/submit
    -- everyone else's submissions stay stored for the post-game "vote for
    the next mystery" round). Returns a job_id pollable via GET /jobs/{id};
    connected clients also get a "mystery_ready" WebSocket broadcast once
    generation finishes, or "mystery_generation_failed" on error.

    Quick-start flow (mystery_slug was given to /games/create): mystery is
    already attached, so this just broadcasts game_started immediately, as
    before.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can start the game")

    if game["mystery"] is not None:
        _broadcast_sync(game_id, "game_started", {"game_id": game_id})
        return {"game_id": game_id, "status": "started"}

    host_prompt = game["submitted_prompts"].get(req.player_id)
    if host_prompt is None:
        raise HTTPException(
            status_code=400,
            detail="submit a prompt via POST /games/{game_id}/prompts/submit before starting",
        )

    with _games_lock:
        game["used_prompt_player_id"] = req.player_id

    job_id = _job_create()
    thread = threading.Thread(
        target=_run_game_generation_job,
        args=(game_id, job_id, host_prompt["prompt_text"], True),
        daemon=True,
    )
    thread.start()
    return {"game_id": game_id, "status": "generating", "job_id": job_id}


@app.post("/games/{game_id}/round/open")
def open_round(game_id: str, req: OpenRoundRequest):
    """
    Host opens a new lockstep round (e.g. "witness"). Snapshots current
    players as required submitters and starts the submission window.
    Content generation for the round is owned elsewhere — this just starts
    the synchronization mechanism.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can open a round")
    if game["stage"] == "submitting":
        raise HTTPException(status_code=400, detail="a round is already open")

    round_ = _open_round(game, req.round_type, req.timeout_seconds, req.metadata)
    return {"ok": True, "round_type": round_["round_type"],
            "expected_count": len(round_["expected_players"]),
            "timeout_seconds": round_["timeout_seconds"],
            "candidate_questions": round_.get("candidate_questions", [])}


@app.post("/games/{game_id}/round/submit")
def submit_round(game_id: str, req: SubmitRoundRequest):
    """
    Player submits their payload for the current round (e.g. their
    interrogation questions). Once every expected player has submitted (or
    the timeout fires), the round advances to "generating" automatically.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    _check_round_timeout(game)
    round_ = game["round"]
    if round_ is None or game["stage"] != "submitting":
        raise HTTPException(status_code=400, detail="no round is currently accepting submissions")
    if req.player_id not in round_["expected_players"]:
        raise HTTPException(status_code=403, detail="player joined after this round opened")
    if req.player_id in round_["submissions"]:
        raise HTTPException(status_code=409, detail="player has already submitted this round")

    # Round-type-specific submission validation. If a third round_type needs
    # this, generalize into a dispatch dict the way _ROUND_PREP /
    # _ROUND_GENERATORS already are.
    if round_["round_type"] == "witness":
        max_questions = _DIFFICULTY_CONFIG[game["difficulty"]]["questions_per_round"]
        questions = [q.strip() for q in req.payload.get("questions", []) if isinstance(q, str) and q.strip()]
        if len(questions) > max_questions:
            raise HTTPException(
                status_code=400,
                detail=f"at most {max_questions} questions allowed this round on {game['difficulty']} difficulty"
            )
        req.payload["questions"] = questions
    elif round_["round_type"] == "prompt_vote":
        candidate_ids = {c["player_id"] for c in round_.get("candidates", [])}
        voted_for = req.payload.get("vote_for_player_id")
        if voted_for not in candidate_ids:
            raise HTTPException(status_code=400, detail="vote_for_player_id must be one of this round's candidates")

    with _games_lock:
        round_["submissions"][req.player_id] = req.payload

    _broadcast_sync(game_id, "player_submitted", {
        "player_name": game["players"][req.player_id]["name"],
        "submitted_count": len(round_["submissions"]),
        "expected_count": len(round_["expected_players"]),
    })
    advanced = _maybe_advance_to_generating(game)
    return {"ok": True, "advanced_to_generating": advanced}


@app.get("/games/{game_id}/round/status")
def round_status(game_id: str):
    """Waiting-room view: current stage, who's submitted, time left."""
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    return _round_status_payload(game)


@app.post("/games/{game_id}/round/resolve")
def resolve_round(game_id: str, req: ResolveRoundRequest):
    """
    Attach a generated result and reveal it to all players. Called by
    round-type-specific generation code once it has produced the shared
    scene / outcome for the current round — not intended as a direct
    player-facing action.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if game["round"] is None or game["stage"] != "generating":
        raise HTTPException(status_code=400, detail="no round is currently generating")

    _resolve_round(game, req.result)
    return {"ok": True}


@app.post("/games/{game_id}/accuse")
def accuse(game_id: str, req: AccuseRequest):
    """
    Player accuses a character of being the culprit — server-authoritative,
    checked against the mystery's actual solution (which is never sent to
    clients, see /mystery-brief). First correct accusation wins the game.
    Every attempt, right or wrong, is broadcast to the whole room — accusing
    is meant to be a public, shared moment, not a private guess-and-check.
    No elimination on a wrong guess; a player can try again.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="player not in game")
    if game.get("winner"):
        raise HTTPException(status_code=400, detail="the case has already been solved")

    solution = game["mystery"].get("solution", {})
    correct = _fingerprint(req.culprit_name) == _fingerprint(solution.get("culprit", ""))

    won = False
    if correct:
        # Re-check inside the lock: guards the race between two players both
        # guessing correctly at nearly the same time — only the first to
        # actually claim the lock while game["winner"] is still None wins.
        with _games_lock:
            if game.get("winner") is None:
                game["winner"] = req.player_id
                won = True

    game.setdefault("accusations", []).append({
        "player_id": req.player_id,
        "accused_name": req.culprit_name,
        "correct": correct,
        "ts": time.time(),
    })

    _broadcast_sync(game_id, "accusation_made", {
        "player_name": player["name"],
        "accused_name": req.culprit_name,
        "correct": correct,
    })
    if won:
        _broadcast_sync(game_id, "game_won", {
            "winner_player_id": req.player_id,
            "winner_name": player["name"],
            "solution": solution,
            **_build_resolution_reveal(game, req.player_id),
        })

    return {"correct": correct, "won": won}


@app.get("/games/{game_id}/result")
def get_result(game_id: str):
    """
    Snapshot of the game's outcome and end-of-game resolution reveal — for a
    client that missed the game_won broadcast (e.g. joined late,
    reconnected), or for the resolution screen itself. Everything here is
    already-generated content (the mystery's own solution + the winner's own
    findings, both produced before this call) reformatted for display --
    zero new API calls. Only included once the game has actually been won.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    winner_id = game.get("winner")
    if winner_id is None:
        return {"solved": False}
    return {
        "solved": True,
        "winner_player_id": winner_id,
        "winner_name": game["players"].get(winner_id, {}).get("name", "Unknown"),
        "solution": game["mystery"].get("solution", {}),
        **_build_resolution_reveal(game, winner_id),
    }


@app.post("/games/{game_id}/prompts/tiebreak")
def prompt_tiebreak(game_id: str, req: TiebreakRequest):
    """
    Break a prompt_vote tie. Only usable when the round's result is an
    unresolved tie waiting on a human call (round result's
    "awaiting_tiebreak_from" is set) -- the auto-resolved-random case (the
    game winner also won the mystery right before this one, or the tie
    didn't include their own candidate at all) needs no human input and this
    endpoint will reject it. Restricted to whichever player
    _tally_prompt_vote named as the tie-break authority for this vote
    (normally the game's winner).
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    round_ = game["round"]
    if round_ is None or round_["round_type"] != "prompt_vote" or game["stage"] != "revealed":
        raise HTTPException(status_code=400, detail="no prompt_vote result is awaiting a tiebreak")
    result = round_["result"]
    authority = result.get("awaiting_tiebreak_from")
    if authority is None or result.get("chosen_player_id") is not None:
        raise HTTPException(status_code=400, detail="this vote isn't waiting on a manual tiebreak")
    if req.player_id != authority:
        raise HTTPException(status_code=403, detail="only the tie-break authority for this vote can resolve it")
    if req.chosen_player_id not in result.get("tied_player_ids", []):
        raise HTTPException(status_code=400, detail="chosen_player_id must be one of the tied candidates")

    with _games_lock:
        result["chosen_player_id"] = req.chosen_player_id
        result["tie_broken_by"] = req.player_id

    _broadcast_sync(game_id, "prompt_tiebreak_resolved", {
        "chosen_player_id": req.chosen_player_id,
        "chosen_name": game["players"].get(req.chosen_player_id, {}).get("name", "Unknown"),
    })
    return {"ok": True, "chosen_player_id": req.chosen_player_id}


@app.post("/games/{game_id}/next-mystery/start")
def next_mystery_start(game_id: str, req: NextMysteryStartRequest):
    """
    Host confirms the group's prompt_vote pick and resets this same room in
    place for the next mystery -- same room code, same players, nobody
    rejoins. Requires the vote to have actually landed on a chosen prompt:
    a clean majority, or a tie that's since been broken (manually via
    /prompts/tiebreak, or automatically).
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can start the next mystery")
    if game.get("winner") is None:
        raise HTTPException(status_code=400, detail="this game hasn't been won yet")
    round_ = game["round"]
    if round_ is None or round_["round_type"] != "prompt_vote" or game["stage"] != "revealed":
        raise HTTPException(status_code=400, detail="no completed prompt_vote to act on")
    chosen_player_id = round_["result"].get("chosen_player_id")
    if chosen_player_id is None:
        raise HTTPException(status_code=400, detail="the vote is still tied and awaiting a tiebreak")

    candidates = {c["player_id"]: c for c in round_.get("candidates", [])}
    chosen_prompt = candidates.get(chosen_player_id)
    if chosen_prompt is None:
        raise HTTPException(status_code=500, detail="chosen candidate no longer exists")

    job_id = _reset_game_for_next_mystery(game, chosen_prompt["prompt_text"])
    return {"game_id": game_id, "status": "generating", "job_id": job_id}


@app.get("/games/{game_id}/block-pool")
def get_block_pool(game_id: str):
    """
    Return the current block pool for this game so the client can grey out
    already-shared questions, areas, and leads before the player tries them.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    return game["block_pool"]


@app.get("/games/{game_id}/shared-clues")
def get_shared_clues(game_id: str, player_id: str):
    """
    Return all clues that have been shared into this game session.
    In a future WebSocket version this would be pushed; for now the client polls.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")
    # Return everything in shared_pool — all players receive all shared clues
    return game["shared_pool"]


@app.post("/games/{game_id}/investigate-area")
def investigate_area(game_id: str, req: InvestigateAreaRequest):
    """
    Player investigates a named crime scene area.
    - Checks hard block (area already in block pool)
    - Calls Claude to generate findings
    - Deducts 1 from the player's investigation budget
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "investigation":
        raise HTTPException(status_code=400, detail="player is not in the investigation phase")
    if player["investigation_budget"] <= 0:
        raise HTTPException(status_code=400, detail="investigation budget exhausted")

    # Hard block check
    if req.area_id in game["block_pool"]["investigation"]:
        raise HTTPException(
            status_code=409,
            detail={"blocked": True, "reason": "This area has already been shared with the group. Try a different location."}
        )

    # Find the area definition in the mystery
    areas = game["mystery"].get("investigation_areas", [])
    area = next((a for a in areas if a["id"] == req.area_id), None)
    if area is None:
        raise HTTPException(status_code=404, detail="area not found in mystery")

    findings, craft_guidance = _investigate_area_with_ai(game["mystery"], area, player["name"])
    finding_id = str(uuid.uuid4())[:8]

    with _games_lock:
        player["investigation_findings"].append({
            "id": finding_id,
            "area_id": req.area_id,
            "area_name": area["name"],
            "findings": findings,
            "_craft_guidance": craft_guidance,
        })
        player["investigation_budget"] -= 1

    # craft_guidance is included here (unlike the witness-round broadcast) because
    # this response goes only to the requesting player over a private HTTP call,
    # not broadcast to the room — useful for tracing narration quality during
    # playtesting without any spoiler/leak risk to other players.
    return {"finding_id": finding_id, "area_name": area["name"], "findings": findings,
            "budget_remaining": player["investigation_budget"],
            "share_required": _min_share_required(
                len(player["investigation_findings"]), game["share_min"]),
            "craft_guidance": craft_guidance}


@app.post("/games/{game_id}/follow-lead")
def follow_lead(game_id: str, req: FollowLeadRequest):
    """
    Player follows one of the pre-generated leads.
    - Checks hard block
    - Each player limited to 2 leads total
    - Calls Claude to generate findings
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "lead":
        raise HTTPException(status_code=400, detail="player is not in the lead phase")
    if len(player["leads_used"]) >= 2:
        raise HTTPException(status_code=400, detail="lead budget exhausted (max 2 per player)")
    if req.lead_id in player["leads_used"]:
        raise HTTPException(status_code=400, detail="you already followed this lead")

    # Hard block check
    if req.lead_id in game["block_pool"]["lead"]:
        raise HTTPException(
            status_code=409,
            detail={"blocked": True, "reason": "This lead has already been shared with the group. Pick a different one."}
        )

    leads = game["mystery"].get("leads", [])
    lead = next((l for l in leads if l["id"] == req.lead_id), None)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found in mystery")

    findings, craft_guidance = _follow_lead_with_ai(game["mystery"], lead, player["name"])
    finding_id = str(uuid.uuid4())[:8]

    with _games_lock:
        player["lead_findings"].append({
            "id": finding_id,
            "lead_id": req.lead_id,
            "lead_title": lead["title"],
            "findings": findings,
            "_craft_guidance": craft_guidance,
        })
        player["leads_used"].append(req.lead_id)

    # See the matching comment in investigate_area() re: why craft_guidance is
    # safe to include here (private per-player response, not a room broadcast).
    return {"finding_id": finding_id, "lead_title": lead["title"], "findings": findings,
            "leads_remaining": 2 - len(player["leads_used"]),
            "share_required": _min_share_required(
                len(player["lead_findings"]), game["share_min"]),
            "craft_guidance": craft_guidance}


@app.post("/games/{game_id}/share-phase")
def share_phase(game_id: str, req: SharePhaseRequest):
    """
    Player submits their Share Selection at the end of a phase.

    - Validates minimum share % (must share ≥ share_min of findings)
    - Checks selected IDs for duplicates against the shared pool
    - If duplicates found: returns duplicate_flags, player must resubmit
    - If clean: broadcasts selected findings to all players, updates block pool
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    phase = req.phase

    # Get the player's findings for this phase
    findings_key = f"{phase}_findings"
    all_findings = player.get(findings_key, [])
    if not all_findings:
        raise HTTPException(status_code=400, detail="no findings to share for this phase")

    # Validate minimum share %
    min_required = _min_share_required(len(all_findings), game["share_min"])
    if len(req.selected_ids) < min_required:
        raise HTTPException(
            status_code=400,
            detail=f"Must share at least {min_required} of {len(all_findings)} findings "
                   f"({int(game['share_min']*100)}% minimum)."
        )

    # Validate selected IDs exist in player's findings
    findings_by_id = {f["id"]: f for f in all_findings}
    invalid = [sid for sid in req.selected_ids if sid not in findings_by_id]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown finding IDs: {invalid}")

    # Duplicate check against shared pool
    duplicate_flags = []
    for sid in req.selected_ids:
        finding = findings_by_id[sid]
        if phase == "witness":
            fp = _fingerprint(finding["question"])
            if any(b["character"] == finding["character"] and b["fingerprint"] == fp
                   for b in game["block_pool"]["witness"]):
                duplicate_flags.append(sid)
        elif phase == "investigation":
            if finding["area_id"] in game["block_pool"]["investigation"]:
                duplicate_flags.append(sid)
        elif phase == "lead":
            if finding["lead_id"] in game["block_pool"]["lead"]:
                duplicate_flags.append(sid)

    if duplicate_flags:
        return {"ok": False, "shared_count": 0, "duplicate_flags": duplicate_flags}

    # Broadcast to all: add to shared_pool and update block_pool
    sender_name = player["name"]
    with _games_lock:
        for sid in req.selected_ids:
            finding = findings_by_id[sid]
            entry = {"sender_name": sender_name, "ts": time.time(), **finding}
            game["shared_pool"][phase].append(entry)

            if phase == "witness":
                game["block_pool"]["witness"].append({
                    "character": finding["character"],
                    "fingerprint": _fingerprint(finding["question"]),
                })
            elif phase == "investigation":
                game["block_pool"]["investigation"].append(finding["area_id"])
            elif phase == "lead":
                game["block_pool"]["lead"].append(finding["lead_id"])

        # Advance player to next phase
        phase_order = ["witness", "investigation", "lead", "done"]
        current_idx = phase_order.index(phase)
        player["phase"] = phase_order[min(current_idx + 1, len(phase_order) - 1)]

    # Push events to all connected WebSocket clients in this room
    shared_clues = [findings_by_id[sid] for sid in req.selected_ids]
    _broadcast_sync(game_id, "clues_shared", {
        "sender_name": player["name"],
        "phase": phase,
        "clues": shared_clues,
    })
    _broadcast_sync(game_id, "block_updated", game["block_pool"])
    _broadcast_sync(game_id, "player_phase_done", {
        "player_name": player["name"],
        "phase": phase,
    })

    return {"ok": True, "shared_count": len(req.selected_ids), "duplicate_flags": []}

# ---------------------------------------------------------------------------
# APF -- the rhythm (CLAUDE.md item 23 step 3, docs/PLAYTEST_FLOW.md)
#
# THESE ROUTES REPLACE THE GATHER LOOP, THEY DO NOT EXTEND IT. /interrogate,
# /investigate-area, /follow-lead and /share-phase above are the pre-APF
# mechanic: a player spends a budget going and getting findings, then shares by
# phase. APF assigns instead, so nothing below calls them and they are untouched
# (CLAUDE.md: "nothing already built gets removed").
#
# ZERO API COST. Every route here is set arithmetic over a mystery that was
# already generated. A whole game costs exactly what its one generation call
# cost -- which is docs/AI_COST_PLAYBOOK.md's lever pushed all the way.
#
# THE SHARE RULE IS INJECTED, NOT REIMPLEMENTED. _min_share_required() above is
# its only definition; apf.py takes it as a callable and precomputes the ladder
# once, at open, so the game can announce it before play starts.
# ---------------------------------------------------------------------------

def _apf_session(game: dict) -> dict:
    session = game.get("apf")
    if session is None:
        raise HTTPException(status_code=409,
                            detail="no APF session; POST /games/{game_id}/apf/open first")
    return session


def _apf_broadcast_state(game_id: str, game: dict) -> None:
    """Push what changed to the whole room. The BOARD and the POOL are public by
    construction -- a shared finding greys a suspect out for everyone, with the
    sharer's name on it, and that is the point of sharing. Casefiles are not, so
    they are never in this payload; each client re-reads its own via /apf/state.
    """
    session = game["apf"]
    _broadcast_sync(game_id, "apf_state", {
        "round": session["round"],
        "rounds": session["rounds"],
        "checkpoint_open": apf.checkpoint_open(session),
        "checkpoint_met": apf.checkpoint_met(session),
        "disclosed": session["disclosed"],
        "board": apf.board(session, game["mystery"]),
        "shared_pool": apf.shared_pool(session),
        "players": [
            {"player_id": pid,
             "name": session["names"].get(pid, pid),
             "held": apf.held_count(session, pid),
             "shared": len(session["shared"].get(pid, [])),
             "outstanding": apf.outstanding(session, pid)}
            for pid in session["player_order"]
        ],
    })


@app.post("/games/{game_id}/apf/open")
def apf_open(game_id: str, req: ApfOpenRequest):
    """Host assigns the mystery into a rhythm and the game announces its length.

    Owner, Session 41: "the game TELLS the users. This mystery has a maximum of
    X rounds. It creates tension and sets expectations." So the round count and
    the whole share ladder come back from this one call, before anybody has seen
    a finding.

    The assignment is free and deterministic, so a refusal here is a statement about
    the MYSTERY, not bad luck -- it comes back with casefiles.py's own diagnosis
    rather than a bare 400, because the two need different responses (re-run
    versus regenerate).
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can assignment")
    if game.get("mystery") is None:
        raise HTTPException(status_code=409, detail="no mystery attached to this game yet")
    if game.get("apf") is not None:
        raise HTTPException(status_code=409, detail="this game has already been assigned")

    players = [{"id": pid, "name": p["name"]} for pid, p in game["players"].items()]
    if len(players) < 2:
        # Constraint 2 -- no single casefile may solve alone -- is unsatisfiable at
        # one player, because that casefile IS the union. Said plainly here rather
        # than surfaced as an opaque assignment failure.
        raise HTTPException(
            status_code=400,
            detail="APF needs at least 2 players: at one, the only casefile is the whole assignment "
                   "and it solves the case alone.",
        )

    share_min = game["share_min"]
    try:
        session = apf.open_session(
            game["mystery"], players,
            share_rule=lambda held: _min_share_required(held, share_min),
        )
    except apf.ApfError as e:
        raise HTTPException(status_code=422,
                            detail={"error": str(e), "issues": e.issues})

    with _games_lock:
        game["apf"] = session
        game["stage"] = "apf"

    announcement = {
        "rounds": session["rounds"],
        "share_ladder": session["share_ladder"],
        "stash_allowance": session["stash_allowance"],
        "player_count": len(players),
        "difficulty": game["difficulty"],
    }
    _broadcast_sync(game_id, "apf_opened", announcement)
    return {**announcement, "assignment": session["assignment"]}


@app.post("/games/{game_id}/apf/round/next")
def apf_next_round(game_id: str, req: ApfOpenRequest):
    """Turn one more finding face up for every player.

    Refuses while a checkpoint is outstanding. That is the mechanic, not a
    safety rail: a round that arrives before the table has paid is just a
    faster assignment, and the rhythm is what produces "she's held back twice now".
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can assignment a round")
    session = _apf_session(game)

    try:
        with _games_lock:
            round_no = apf.open_round(session)
    except apf.ApfError as e:
        raise HTTPException(status_code=409, detail=str(e))

    _apf_broadcast_state(game_id, game)
    return {
        "round": round_no,
        "rounds": session["rounds"],
        "checkpoint_open": apf.checkpoint_open(session),
        "final_round": round_no >= session["rounds"],
    }


@app.get("/games/{game_id}/apf/state")
def apf_state(game_id: str, player_id: str):
    """One client's whole view: its own casefile, the public pool, the board, and
    the share requirement -- SENT, never derived. Other players' unshared
    findings and this player's own unassigned future are not in it."""
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    session = _apf_session(game)
    if player_id not in session["casefiles"]:
        raise HTTPException(status_code=404, detail="player not in this assignment")
    return apf.state_for(session, player_id, game["mystery"])


@app.post("/games/{game_id}/apf/share")
def apf_share(game_id: str, req: ApfShareRequest):
    """Put findings on the table. Cumulative, monotone, idempotent.

    THE FINDING STAYS IN THE PLAYER'S CASEFILE. Owner: an investigator cannot be
    made to forget. What is spent is exclusivity, not possession -- so this adds
    to the shared pool and removes nothing, and there is no un-share, because
    the room cannot unlearn.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    session = _apf_session(game)
    if req.player_id not in session["casefiles"]:
        raise HTTPException(status_code=404, detail="player not in this assignment")

    try:
        with _games_lock:
            result = apf.share(session, req.player_id, req.finding_ids)
    except apf.ApfError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _apf_broadcast_state(game_id, game)
    return {**result, "checkpoint_met": apf.checkpoint_met(session)}


@app.post("/games/{game_id}/apf/disclose")
def apf_disclose(game_id: str, req: ApfOpenRequest):
    """Full disclosure: everything still held becomes public, with the holder's
    name against it.

    NOT A TIE-BREAKER AND NOT A RESCUE (owner, Session 41) -- it is the reward
    for having chosen this mystery. You picked the setting and paid for the
    generation, so you are owed the whole of it rather than the fraction that
    happened to be shared. And it does a second job for free: "she was holding
    the ledger page the whole time" is the sentence the mechanic exists to
    produce, and nothing before the end can produce it.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player = game["players"].get(req.player_id)
    if not player or not player.get("is_host"):
        raise HTTPException(status_code=403, detail="only the host can close the case")
    session = _apf_session(game)
    if session["disclosed"]:
        return apf_disclosure(game_id)

    with _games_lock:
        apf.disclose(session)

    _apf_broadcast_state(game_id, game)
    payload = apf_disclosure(game_id)
    _broadcast_sync(game_id, "apf_disclosed", payload)
    return payload


@app.get("/games/{game_id}/apf/disclosure")
def apf_disclosure(game_id: str):
    """The end-of-game record: every assigned finding, who held it, whether they
    volunteered it or disclosure prised it out, and in which round.

    `withheld` is the list the reveal screen is actually for. Zero API calls --
    this is the session's own log, reformatted.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    session = _apf_session(game)
    pool = apf.shared_pool(session)
    return {
        "disclosed": session["disclosed"],
        "rounds": session["rounds"],
        "board": apf.board(session, game["mystery"]),
        "findings": pool,
        "withheld": [e for e in pool if e["disclosure"]],
        "by_player": [
            {
                "player_id": pid,
                "name": session["names"].get(pid, pid),
                "held": apf.held_count(session, pid),
                "volunteered": sum(1 for e in pool
                                   if e["shared_by_id"] == pid and not e["disclosure"]),
                "withheld": sum(1 for e in pool
                                if e["shared_by_id"] == pid and e["disclosure"]),
            }
            for pid in session["player_order"]
        ],
    }

@app.post("/interrogate")
def interrogate(req: InterrogateRequest):
    """
    Ask a named character a question. Returns an in-character reply.

    The full mystery dict is sent by the client so the server can build
    the character context without a database lookup on every call.
    This is acceptable because mysteries are small (<10 KB).
    """
    chars = req.mystery.get("characters", [])
    char_data = next((c for c in chars if c["name"] == req.character_name), None)
    if char_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{req.character_name}' not found in mystery"
        )

    # Build setting narrative for context
    s = req.mystery.get("setting", {})
    c = req.mystery.get("crime", {})
    setting_summary = (
        f"Location: {s.get('location', '')}\n"
        f"Time period: {s.get('time_period', '')}\n"
        f"Crime: {c.get('what_happened', '')}"
    )

    char_context = (
        f"Role: {char_data.get('role', 'suspect')}\n"
        f"Occupation: {char_data.get('occupation', '')}\n"
        f"Alibi: {char_data.get('alibi', '')}\n"
        f"Secret: {char_data.get('secret', '')}\n"
        f"Motive: {char_data.get('motive', '')}"
    )

    prompt = f"""You are {req.character_name} in this mystery.

SETTING:
{setting_summary}

YOUR PRIVATE CHARACTER DETAILS (do NOT reveal these directly):
{char_context}

Answer the detective's question in character.
Be evasive if you are the culprit. Be defensive if you are innocent but suspicious.
Do NOT directly reveal the real culprit.

Detective's question: {req.question}"""

    reply = llm(prompt, system="You are a mystery game character. Stay in character.")
    return {"response": reply}


@app.post("/games/{game_id}/interrogate")
def game_interrogate(game_id: str, req: InterrogateRequest):
    """
    Game-session-aware interrogation used during Phase 3 multiplayer.
    - Validates player is in the witness phase
    - Checks hard-block (duplicate question already shared)
    - Deducts from witness budget
    - Stores finding so the player can share at phase end
    The underlying AI call is identical to the solo /interrogate endpoint.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")

    # Look up player_id from the request body's mystery — we need it separately.
    # For game interrogation we expect a player_id field on the request.
    # We re-use InterrogateRequest but the player_id is passed as a query param.
    raise HTTPException(
        status_code=501,
        detail="Use POST /games/{game_id}/interrogate-witness instead."
    )


class GameInterrogateRequest(BaseModel):
    player_id: str
    character_name: str
    question: str


@app.post("/games/{game_id}/interrogate-witness")
def game_interrogate_witness(game_id: str, req: GameInterrogateRequest):
    """
    Multiplayer witness interrogation.
    - Player must be in 'witness' phase
    - Hard-block if (character, question_fingerprint) already in block pool
    - Calls Claude for in-character response
    - Deducts 1 from witness budget; stores in player's witness_findings
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "witness":
        raise HTTPException(status_code=400, detail="player is not in the witness phase")
    if player["witness_budget"] <= 0:
        raise HTTPException(status_code=400, detail="witness budget exhausted")

    # Hard block check
    fp = _fingerprint(req.question)
    if any(b["character"] == req.character_name and b["fingerprint"] == fp
           for b in game["block_pool"]["witness"]):
        raise HTTPException(
            status_code=409,
            detail={
                "blocked": True,
                "reason": f"This question to {req.character_name} has already been shared with the group. Ask something different."
            }
        )

    # Retrieve character data from mystery for richer context
    chars = game["mystery"].get("characters", [])
    char_data = next((c for c in chars if c["name"] == req.character_name), None)
    if char_data is None:
        raise HTTPException(status_code=404, detail=f"Character '{req.character_name}' not found")

    s = game["mystery"].get("setting", {})
    c = game["mystery"].get("crime", {})
    setting_summary = (
        f"Location: {s.get('location', '')}\n"
        f"Time period: {s.get('time_period', '')}\n"
        f"Crime: {c.get('what_happened', '')}"
    )
    char_context = (
        f"Role: {char_data.get('role', 'suspect')}\n"
        f"Occupation: {char_data.get('occupation', '')}\n"
        f"Alibi: {char_data.get('alibi', '')}\n"
        f"Secret: {char_data.get('secret', '')}\n"
        f"Motive: {char_data.get('motive', '')}"
    )
    prompt = (
        f"You are {req.character_name} in this mystery.\n\n"
        f"SETTING:\n{setting_summary}\n\n"
        f"YOUR PRIVATE CHARACTER DETAILS (do NOT reveal directly):\n{char_context}\n\n"
        f"Detective's question: {req.question}"
    )
    response = llm(prompt, system="You are a mystery game character. Stay in character.")

    finding_id = str(uuid.uuid4())[:8]
    with _games_lock:
        player["witness_findings"].append({
            "id": finding_id,
            "character": req.character_name,
            "question": req.question,
            "response": response,
        })
        player["witness_budget"] -= 1

    return {
        "finding_id": finding_id,
        "response": response,
        "budget_remaining": player["witness_budget"],
        "share_required": _min_share_required(
            len(player["witness_findings"]), game["share_min"]),
    }


@app.post("/rate")
def rate(req: RateRequest):
    """
    Persist a viability rating (1–10) back into the saved mystery JSON.
    Updates the `_meta.viability_rating` field.
    """
    if not (1 <= req.rating <= 10):
        raise HTTPException(status_code=400, detail="rating must be 1–10")

    generated_dir = _DB_PATH / "generated"
    matches = list(generated_dir.glob(f"{req.mystery_slug}_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="mystery not found")

    # Use the most recent file if multiple matches (shouldn't happen in practice)
    mystery_file = sorted(matches)[-1]
    with open(mystery_file) as f:
        data = json.load(f)

    if "_meta" not in data:
        data["_meta"] = {}
    data["_meta"]["viability_rating"] = req.rating

    with open(mystery_file, "w") as f:
        json.dump(data, f, indent=2)

    return {"ok": True}


def _apf_readiness(mystery: dict) -> dict:
    """Can this saved mystery actually be ASSIGNED? Free -- pure set arithmetic.

    WHY A PICKER NEEDS THIS AND A PLAYER NEEDS IT MORE. `generated/` means "no
    check we own can prove this is broken", which is a statement about the
    checks that existed when the file was written. Seventeen of the eighteen
    mysteries on disk predate the APF schema entirely: they carry no `reveals`
    pointers and mostly three suspects, so `casefiles.feasibility()` refuses them.
    Offering all eighteen as equals means a picker where one in eighteen works
    and the other seventeen fail AFTER you have chosen, named a room and waited
    -- which reads as a broken game rather than an old library.

    Measured at APF's specified shape: 4 players over 4 rounds. A mystery that
    cannot be assigned there is reported with the FIRST reason, because the first
    reason is almost always the real one and a wall of them tells a picker
    nothing it can render.
    """
    try:
        rounds = apf.round_count(len(casefiles.build_pool(mystery)), APF_PICKER_PLAYERS)
        if rounds < apf.MIN_ROUNDS:
            return {"apf_ready": False,
                    "apf_blocker": f"only {rounds} round(s) at {APF_PICKER_PLAYERS} players"}
        issues = casefiles.feasibility(mystery, APF_PICKER_PLAYERS,
                                  casefile_spec=apf.casefile_spec_for(rounds))
        if issues:
            return {"apf_ready": False, "apf_blocker": issues[0]}
        return {"apf_ready": True, "apf_blocker": ""}
    except Exception as exc:  # noqa: BLE001 -- a malformed file is "not ready", not a 500
        return {"apf_ready": False, "apf_blocker": f"unreadable: {type(exc).__name__}"}


@app.get("/mysteries")
def list_mysteries():
    """
    List all saved mysteries (slug, title, created_at timestamp).
    Sorted newest-first.
    """
    generated_dir = _DB_PATH / "generated"
    results = []
    for path in sorted(generated_dir.glob("*.json"), reverse=True):
        try:
            with open(path) as f:
                data = json.load(f)
            stem = path.stem  # e.g. "the_murder_on_the_train_1700000000"
            parts = stem.rsplit("_", 1)
            slug = parts[0] if len(parts) == 2 else stem
            ts = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
            results.append({
                "slug": slug,
                "title": data.get("title", slug),
                "difficulty": data.get("gameplay_notes", {}).get("difficulty", "?"),
                "coherence_passed": data.get("_coherence", {}).get("passed", None),
                "viability_rating": data.get("_meta", {}).get("viability_rating", None),
                "created_at": ts,
                **_apf_readiness(data),
            })
        except Exception:
            continue
    return results


@app.get("/mysteries/{slug}")
def get_mystery(slug: str):
    """Load the most recently saved mystery matching this slug."""
    generated_dir = _DB_PATH / "generated"
    matches = list(generated_dir.glob(f"{slug}_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="mystery not found")
    mystery_file = sorted(matches)[-1]
    with open(mystery_file) as f:
        data = json.load(f)
    # _slug is assigned *after* _save_mystery() in the generation pipeline, so
    # it is never written to disk -- every file on disk lacks it. The client
    # reads mystery["_slug"] to save a viability rating, so a mystery loaded
    # from here used to rate into the void: the request was skipped entirely
    # on an empty slug. Derive it from the filename, exactly as /mysteries does.
    data.setdefault("_slug", slug)
    return data
