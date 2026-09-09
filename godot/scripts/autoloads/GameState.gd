## GameState — Global singleton.
## Tracks the current mystery, game phase, interrogation history,
## and player identity. Persists across scene changes.
##
## Access from any scene: GameState.current_mystery

extends Node

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
enum Phase {
	MAIN_MENU,
	GENERATING,
	CASE_DISPLAY,
	INTERROGATION,
	ACCUSATION,
	RESULT,
}

## Investigation sub-phases (used within INTERROGATION phase for Phase 3)
enum InvestPhase {
	WITNESS,
	SHARE_WITNESS,       ## Share Selection screen after witness budget exhausted
	INVESTIGATION,
	SHARE_INVESTIGATION,
	LEAD,
	SHARE_LEAD,
	DONE,
}

# ---------------------------------------------------------------------------
# Core state (single-player + multiplayer)
# ---------------------------------------------------------------------------
var current_mystery: Dictionary = {}        ## Full mystery dict from server
var interrogation_history: Array = []       ## [{character, question, response}, ...]
var player_name: String = "Detective"
var game_phase: Phase = Phase.MAIN_MENU
var accusation_result: Dictionary = {}      ## {correct: bool, culprit: str, verdict: str}

# ---------------------------------------------------------------------------
# Phase 3 — multiplayer + structured investigation
# ---------------------------------------------------------------------------
var game_id: String = ""
var player_id: String = ""
var player_list: Array = []                 ## [{id, name, is_host}, ...]
var is_multiplayer: bool = false            ## set true when host picks "Multiplayer" in MainMenu

## Current investigation sub-phase
var invest_phase: InvestPhase = InvestPhase.WITNESS

## Budgets (populated on game create/join)
var witness_budget: int = 0
var investigation_budget: int = 0
var leads_remaining: int = 2
var share_min: float = 0.6                  ## Informational only — see share_required below

## How many findings the SERVER requires to be shared, per phase. The client
## does NOT compute this. It used to, from share_min, with ceil() where the
## server uses round() — the two disagreed in 6 of 18 realistic combinations and
## the client was always stricter, so it refused shares the server would have
## accepted. With only two findings held it demanded both, deleting the choice the
## mechanic exists for. The server now sends the number with every finding
## response and these just hold it.
var witness_share_required: int = 0
var investigation_share_required: int = 0
var lead_share_required: int = 0

## Findings accumulated this phase (cleared after sharing)
var witness_findings: Array = []            ## [{id, character, question, response}, ...]
var investigation_findings: Array = []      ## [{id, area_id, area_name, findings}, ...]
var lead_findings: Array = []              ## [{id, lead_id, lead_title, findings}, ...]

## Clues received from other players (all phases, appended as shares arrive)
var shared_clues: Dictionary = {
	"witness": [],
	"investigation": [],
	"lead": [],
}

## Block pool — cached from server, used to grey out UI options
var block_pool: Dictionary = {
	"witness": [],         ## [{character, fingerprint}, ...]
	"investigation": [],   ## [area_id, ...]
	"lead": [],            ## [lead_id, ...]
}

# ---------------------------------------------------------------------------
# APF — the rhythm (docs/PLAYTEST_FLOW.md). Findings are ASSIGNED, one per player
# per round, with a cumulative share checkpoint from round 2.
#
# NOTHING HERE IS DERIVED. The server sends the round, the requirement and the
# board; this caches the last payload so a scene change does not cost a refetch.
# The one number a client must never compute for itself is the share minimum —
# see current_share_required() below and scripts/test_share_rule.py.
# ---------------------------------------------------------------------------

## True when this player created the room. Only the host may open a round or
## close the case, so the round screen hides those controls for everyone else.
var is_host: bool = false

## How many rounds this mystery has, announced before play begins. Owner:
## "the game TELLS the users… it creates tension and sets expectations."
var apf_rounds: int = 0

## The whole share ladder, also announced up front: apf_share_ladder[r - 1] is
## how many findings must be on the table by the end of round r.
var apf_share_ladder: Array = []

## The last /apf/state payload. Empty until the first fetch.
var apf_state: Dictionary = {}

## Cache the announcement from POST /apf/open.
func record_apf_open(data: Dictionary) -> void:
	apf_rounds = int(data.get("rounds", 0))
	apf_share_ladder = data.get("share_ladder", [])

## Cache one /apf/state payload.
func record_apf_state(data: Dictionary) -> void:
	apf_state = data
	if apf_rounds == 0:
		apf_rounds = int(data.get("rounds", 0))
	if apf_share_ladder.is_empty():
		apf_share_ladder = data.get("share_ladder", [])

## How many findings this player still owes the table. THE SERVER'S OWN ANSWER,
## never a guess: erring permissive costs a rejected submit, erring strict
## silently deletes a legal move. 0 when the server has said nothing, because
## round 1 legitimately asks for nothing.
func apf_outstanding() -> int:
	return int(apf_state.get("share_outstanding", 0))

## This player's assigned findings, each flagged with whether it has been shared.
func apf_casefile() -> Array:
	return apf_state.get("casefile", [])

## The suspect board: [{name, cleared, cleared_by}, ...]. A row is greyed out
## only by an EXONERATION somebody shared — never by a narrowing, which item 27
## requires the player to draw for themselves.
func apf_board() -> Array:
	return apf_state.get("board", [])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func get_interrogatable_characters() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") in ["suspect", "witness"])

func get_suspect_names() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") == "suspect") \
			.map(func(c): return c.get("name", ""))

## Single-player interrogation history (Phase 2 compatibility).
func record_interrogation(character_name: String, question: String, response: String) -> void:
	interrogation_history.append({
		"character": character_name,
		"question": question,
		"response": response,
	})

## Phase 3: record a witness finding returned by /games/{id}/interrogate-witness.
func record_witness_finding(finding: Dictionary) -> void:
	witness_findings.append(finding)
	witness_budget = finding.get("budget_remaining", witness_budget)
	witness_share_required = finding.get("share_required", witness_share_required)

## Phase 3: record an investigation finding.
func record_investigation_finding(finding: Dictionary) -> void:
	investigation_findings.append(finding)
	investigation_budget = finding.get("budget_remaining", investigation_budget)
	investigation_share_required = finding.get("share_required", investigation_share_required)

## Phase 3: record a lead finding.
func record_lead_finding(finding: Dictionary) -> void:
	lead_findings.append(finding)
	leads_remaining = finding.get("leads_remaining", leads_remaining)
	lead_share_required = finding.get("share_required", lead_share_required)

## Phase 3: cache the server's block pool response.
func update_block_pool(pool: Dictionary) -> void:
	block_pool = pool

## Phase 3: append incoming shared clues from server poll.
func merge_shared_clues(pool: Dictionary) -> void:
	for phase_key in ["witness", "investigation", "lead"]:
		var incoming: Array = pool.get(phase_key, [])
		var existing_ids: Array = shared_clues[phase_key].map(func(c): return c.get("id", ""))
		for clue in incoming:
			if clue.get("id", "") not in existing_ids:
				shared_clues[phase_key].append(clue)

## Returns true if the given (character, question) is in the witness block pool.
func is_witness_blocked(character: String, question: String) -> bool:
	var fp := question.strip_edges().to_lower()
	for b in block_pool.get("witness", []):
		if b.get("character") == character and b.get("fingerprint") == fp:
			return true
	return false

func is_area_blocked(area_id: String) -> bool:
	return area_id in block_pool.get("investigation", [])

func is_lead_blocked(lead_id: String) -> bool:
	return lead_id in block_pool.get("lead", [])

## Returns the findings array for the current invest_phase.
func current_phase_findings() -> Array:
	match invest_phase:
		InvestPhase.SHARE_WITNESS:
			return witness_findings
		InvestPhase.SHARE_INVESTIGATION:
			return investigation_findings
		InvestPhase.SHARE_LEAD:
			return lead_findings
	return []

## The server's own answer for how many of them must be shared. 0 means the
## server never told us, which the Share screen treats as "1", never as a
## stricter guess of its own.
func current_share_required() -> int:
	match invest_phase:
		InvestPhase.SHARE_WITNESS:
			return witness_share_required
		InvestPhase.SHARE_INVESTIGATION:
			return investigation_share_required
		InvestPhase.SHARE_LEAD:
			return lead_share_required
	return 0

## Resets all game state (call before starting a new mystery).
func reset() -> void:
	current_mystery = {}
	interrogation_history = []
	accusation_result = {}
	game_phase = Phase.MAIN_MENU
	game_id = ""
	player_id = ""
	player_list = []
	invest_phase = InvestPhase.WITNESS
	witness_budget = 0
	investigation_budget = 0
	leads_remaining = 2
	witness_findings = []
	investigation_findings = []
	lead_findings = []
	witness_share_required = 0
	investigation_share_required = 0
	lead_share_required = 0
	shared_clues = {"witness": [], "investigation": [], "lead": []}
	block_pool = {"witness": [], "investigation": [], "lead": []}
	is_multiplayer = false
	is_host = false
	apf_rounds = 0
	apf_share_ladder = []
	apf_state = {}
	# Note: player_name is intentionally NOT reset between games
