## ApiClient -- Global singleton.
## Wraps all HTTP calls to the FastAPI backend, plus the WebSocket connection
## for real-time push events during multiplayer games.
##
## HTTP callbacks receive (error: String, data: Dictionary).
## error is "" on success, or an error message on failure.
##
## WebSocket:
##   Call connect_ws(game_id, player_id) once per game session.
##   Emits signal ws_event(event_name: String, data: Dictionary) on each
##   push from the server.  Scenes connect to this signal instead of polling.
##
## SESSION ANNOTATION -- Phase 2:
## SERVER_URL is localhost for dev. Change to deployed URL before shipping.

extends Node

signal ws_event(event_name: String, data: Dictionary)

const SERVER_URL_DEFAULT: String = "http://localhost:8000"
const REQUEST_TIMEOUT: float = 120.0   ## seconds; generation can take 60-90s
var server_url: String = SERVER_URL_DEFAULT

## Active WebSocket peer (null when not in a game session)
var _ws: WebSocketPeer = null
var _ws_game_id: String = ""

func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load("user://server_config.cfg") == OK:
		server_url = cfg.get_value("server", "url", SERVER_URL_DEFAULT)

func _process(_delta: float) -> void:
	if _ws == null:
		return
	_ws.poll()
	var state := _ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		while _ws.get_available_packet_count() > 0:
			var raw := _ws.get_packet().get_string_from_utf8()
			var json := JSON.new()
			if json.parse(raw) == OK and json.data is Dictionary:
				var msg: Dictionary = json.data
				ws_event.emit(msg.get("event", ""), msg.get("data", {}))
	elif state == WebSocketPeer.STATE_CLOSED:
		_ws = null

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Synchronous generation (kept for reference; prefer generate_mystery_async).
func generate_mystery(prompt: String, opening_narration: bool, callback: Callable) -> void:
	var body := JSON.stringify({"prompt": prompt, "opening_narration": opening_narration})
	_post("/generate", body, callback)

## Async generation: returns {job_id} immediately; poll with poll_job().
func generate_mystery_async(prompt: String, opening_narration: bool, callback: Callable) -> void:
	var body := JSON.stringify({"prompt": prompt, "opening_narration": opening_narration})
	_post("/generate/async", body, callback)

## Poll a running job. callback receives (error, {status, stage, result, error}).
func poll_job(job_id: String, callback: Callable) -> void:
	_do_request("/jobs/" + job_id, HTTPClient.METHOD_GET, "", callback)

## --- Phase 3: WebSocket connection ---

## Open a persistent WebSocket to /ws/{game_id}. Call once after joining a game.
func connect_ws(game_id: String, player_id: String) -> void:
	if _ws != null:
		_ws.close()
	_ws_game_id = game_id
	_ws = WebSocketPeer.new()
	var ws_url := server_url.replace("http://", "ws://").replace("https://", "wss://")
	ws_url += "/ws/" + game_id + "?player_id=" + player_id
	_ws.connect_to_url(ws_url)

## Close the active WebSocket (call on scene cleanup or game exit).
func disconnect_ws() -> void:
	if _ws != null:
		_ws.close()
		_ws = null
		_ws_game_id = ""

## --- Phase 3: game session API ---

func create_game(mystery_slug: String, host_name: String, difficulty: String, callback: Callable) -> void:
	var body := JSON.stringify({"mystery_slug": mystery_slug, "host_name": host_name, "difficulty": difficulty})
	_post("/games/create", body, callback)

func join_game(game_id: String, player_name: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_name": player_name})
	_post("/games/" + game_id + "/join", body, callback)

func get_lobby(game_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/lobby", HTTPClient.METHOD_GET, "", callback)

func start_game(game_id: String, player_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id})
	_post("/games/" + game_id + "/start", body, callback)

func get_block_pool(game_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/block-pool", HTTPClient.METHOD_GET, "", callback)

func get_shared_clues(game_id: String, player_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/shared-clues?player_id=" + player_id, HTTPClient.METHOD_GET, "", callback)

func game_interrogate_witness(game_id: String, player_id: String, character_name: String, question: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "character_name": character_name, "question": question})
	_post("/games/" + game_id + "/interrogate-witness", body, callback)

func investigate_area(game_id: String, player_id: String, area_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "area_id": area_id})
	_post("/games/" + game_id + "/investigate-area", body, callback)

func follow_lead(game_id: String, player_id: String, lead_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "lead_id": lead_id})
	_post("/games/" + game_id + "/follow-lead", body, callback)

func share_phase(game_id: String, player_id: String, phase: String, selected_ids: Array, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "phase": phase, "selected_ids": selected_ids})
	_post("/games/" + game_id + "/share-phase", body, callback)

## --- APF: the rhythm (docs/PLAYTEST_FLOW.md, "The rhythm") ---
##
## These six replace the gather loop above for the playtest path; they do not
## extend it. Findings are DEALT, so there is nothing here that spends a budget
## or goes and gets anything, and no call below costs the server an API call.

## Host only. Deals the mystery into rounds and returns the announcement the
## game opens with: how many rounds, and the whole share ladder.
func apf_open(game_id: String, player_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id})
	_post("/games/" + game_id + "/apf/open", body, callback)

## Host only. Turns one more finding face up for every player. The server
## refuses while a share checkpoint is still open — that is the mechanic.
func apf_next_round(game_id: String, player_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id})
	_post("/games/" + game_id + "/apf/round/next", body, callback)

## One player's whole view: their own hand, the public pool, the suspect board,
## and how many findings they still owe the table.
func apf_state(game_id: String, player_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/apf/state?player_id=" + player_id,
			HTTPClient.METHOD_GET, "", callback)

## Put findings on the table. Cumulative and monotone — a shared finding stays
## in the hand, and there is no un-share.
func apf_share(game_id: String, player_id: String, finding_ids: Array, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "finding_ids": finding_ids})
	_post("/games/" + game_id + "/apf/share", body, callback)

## Host only. Full disclosure: everything still held becomes public with the
## holder's name against it.
func apf_disclose(game_id: String, player_id: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id})
	_post("/games/" + game_id + "/apf/disclose", body, callback)

## Server-authoritative accusation. The solution is never sent to clients, so
## in a room this is the ONLY thing that can decide a winner -- and first
## correct accusation wins, which a local comparison cannot adjudicate.
func accuse(game_id: String, player_id: String, culprit_name: String, callback: Callable) -> void:
	var body := JSON.stringify({"player_id": player_id, "culprit_name": culprit_name})
	_post("/games/" + game_id + "/accuse", body, callback)

## The result snapshot, including the reveal, for a client that missed the
## game_won broadcast.
func get_result(game_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/result", HTTPClient.METHOD_GET, "", callback)

## The end-of-game record, for the reveal screen.
func apf_disclosure(game_id: String, callback: Callable) -> void:
	_do_request("/games/" + game_id + "/apf/disclosure", HTTPClient.METHOD_GET, "", callback)

## --- Single-player legacy API (Phase 2) ---

func interrogate(mystery: Dictionary, character_name: String, question: String, callback: Callable) -> void:
	var body := JSON.stringify({"mystery": mystery, "character_name": character_name, "question": question})
	_post("/interrogate", body, callback)

func rate_mystery(slug: String, rating: int, callback: Callable) -> void:
	var body := JSON.stringify({"mystery_slug": slug, "rating": rating})
	_post("/rate", body, callback)

func list_mysteries(callback: Callable) -> void:
	_do_request("/mysteries", HTTPClient.METHOD_GET, "", callback)

func get_mystery(slug: String, callback: Callable) -> void:
	_do_request("/mysteries/" + slug, HTTPClient.METHOD_GET, "", callback)

func health_check(callback: Callable) -> void:
	_do_request("/health", HTTPClient.METHOD_GET, "", callback)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

func _post(path: String, body: String, callback: Callable) -> void:
	_do_request(path, HTTPClient.METHOD_POST, body, callback)

func _do_request(path: String, method: int, body: String, callback: Callable) -> void:
	var req := HTTPRequest.new()
	req.timeout = REQUEST_TIMEOUT
	add_child(req)
	req.request_completed.connect(_on_done.bind(req, callback))
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err: int
	if method == HTTPClient.METHOD_POST:
		err = req.request(server_url + path, headers, HTTPClient.METHOD_POST, body)
	else:
		err = req.request(server_url + path)
	if err != OK:
		req.queue_free()
		callback.call("HTTP request failed (code %d)" % err, {})

func _on_done(result: int, code: int, _headers: PackedStringArray, body_bytes: PackedByteArray, req: HTTPRequest, callback: Callable) -> void:
	req.queue_free()
	if result == HTTPRequest.RESULT_TIMEOUT:
		callback.call("Request timed out after %ds — server may still be generating." % int(REQUEST_TIMEOUT), {})
		return
	if result != HTTPRequest.RESULT_SUCCESS:
		callback.call("Network error (result=%d)" % result, {})
		return
	if code < 200 or code >= 300:
		callback.call("Server error %d: %s" % [code, body_bytes.get_string_from_utf8()], {})
		return
	var json := JSON.new()
	if json.parse(body_bytes.get_string_from_utf8()) != OK:
		callback.call("JSON parse error: " + json.get_error_message(), {})
		return
	callback.call("", json.data)
