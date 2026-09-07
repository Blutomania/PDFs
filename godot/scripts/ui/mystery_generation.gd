## MysteryGeneration — the "Set Your Mystery" screen.
## User types a prompt, presses Generate, waits for backend response,
## then is taken to CaseDisplay.
##
## Uses the async job system so Godot never blocks on a 60-90s HTTP call.
## Flow:
##   1. POST /generate/async  → job_id (returns in < 1s)
##   2. Poll GET /jobs/{job_id} every POLL_INTERVAL seconds
##   3. Show live "stage" text from the server (Generating… / Localizing… / etc.)
##   4. On status == "done" → load CaseDisplay
##   5. On status == "error" → show error, re-enable form
##
## SESSION ANNOTATION — Phase 2:
## This is the first scene that makes a real backend call. Test it by:
##   1. Running the FastAPI server: cd server && uvicorn main:app --port 8000
##   2. Press F5 in Godot, click "New Game", type any prompt, click "Generate".
##   3. Verify CaseDisplay loads with a populated mystery.

extends Control

const POLL_INTERVAL: float = 2.0   ## seconds between job status polls

# ---------------------------------------------------------------------------
# Node references (wire these in the .tscn)
# ---------------------------------------------------------------------------
@onready var prompt_input: LineEdit = $VBox/PromptInput
@onready var narration_checkbox: CheckBox = $VBox/NarrationCheckbox
@onready var generate_button: Button = $VBox/GenerateButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner
@onready var multiplayer_section: VBoxContainer = $VBox/MultiplayerSection
@onready var saved_label: Label = $VBox/MultiplayerSection/SavedLabel
@onready var saved_option: OptionButton = $VBox/MultiplayerSection/SavedOption
@onready var host_saved_button: Button = $VBox/MultiplayerSection/HostSavedButton
@onready var host_name_input: LineEdit = $VBox/MultiplayerSection/HostNameInput
@onready var difficulty_option: OptionButton = $VBox/MultiplayerSection/DifficultyOption

var _job_id: String = ""
var _poll_timer: float = 0.0
var _polling: bool = false

## The saved-mystery list, parallel to saved_option's items.
var _saved: Array = []
## The slug being loaded into a room, held because /mysteries/{slug} is fetched
## before /games/create and only the first of those two calls knows it.
var _pending_slug: String = ""

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	generate_button.pressed.connect(_on_generate)
	back_button.pressed.connect(_on_back)
	prompt_input.text_submitted.connect(func(_t): _on_generate())
	multiplayer_section.visible = GameState.is_multiplayer
	if GameState.is_multiplayer:
		difficulty_option.add_item("Easy")
		difficulty_option.add_item("Medium")
		difficulty_option.add_item("Hard")
		difficulty_option.selected = 1   ## Medium default
		if GameState.player_name != "Detective":
			host_name_input.text = GameState.player_name
		host_saved_button.pressed.connect(_on_host_saved)
		_load_saved_mysteries()
	_set_loading(false)

func _process(delta: float) -> void:
	if not _polling:
		return
	_poll_timer -= delta
	if _poll_timer <= 0.0:
		_poll_timer = POLL_INTERVAL
		ApiClient.poll_job(_job_id, _on_poll_result)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_generate() -> void:
	var prompt := prompt_input.text.strip_edges()
	if prompt.is_empty():
		status_label.text = "Please describe your mystery scenario."
		return

	_set_loading(true)
	status_label.text = "Contacting server…"
	ApiClient.generate_mystery_async(
		prompt,
		narration_checkbox.button_pressed,
		_on_job_created
	)

func _on_job_created(error: String, data: Dictionary) -> void:
	if error:
		_set_loading(false)
		status_label.text = "Error: " + error
		return
	_job_id = data.get("job_id", "")
	if _job_id.is_empty():
		_set_loading(false)
		status_label.text = "Error: server did not return a job ID."
		return
	_poll_timer = 0.0   ## poll immediately on next _process tick
	_polling = true

func _on_poll_result(error: String, data: Dictionary) -> void:
	if error:
		_polling = false
		_set_loading(false)
		status_label.text = "Error polling job: " + error
		return

	var stage: String = data.get("stage", "Working…")
	status_label.text = stage

	match data.get("status", ""):
		"done":
			_polling = false
			var result: Dictionary = data.get("result", {})
			if result.is_empty():
				_set_loading(false)
				status_label.text = "Error: server returned an empty result."
				return
			_set_loading(false)
			GameState.current_mystery = result
			if GameState.is_multiplayer:
				_create_multiplayer_game(result.get("_slug", ""))
			else:
				GameState.game_phase = GameState.Phase.CASE_DISPLAY
				get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
		"error":
			_polling = false
			_set_loading(false)
			status_label.text = "Generation failed: " + data.get("error", "unknown error")
		_:
			pass   ## queued / running — keep polling

# ---------------------------------------------------------------------------
# Hosting a mystery that already exists — the free path
#
# WHY THIS EXISTS. Until Session 42 the ONLY way to open a room was to generate
# a new mystery first, because _create_multiplayer_game() was reachable solely
# from the end of a successful generation. So every look at the round screen
# cost a generation, and historically one generation in eight passes the gate.
# That is a coin flip with real money on it, to look at a screen.
#
# The server has accepted `mystery_slug` on /games/create since Session 26;
# nothing in this client ever asked it to. This is that one call, wired.
#
# It also happens to be docs/PLAYTEST_FLOW.md's step 1 — "Mystery picker,
# dropdown, TITLES ONLY". No difficulty column, no rating, no coherence badge.
# ---------------------------------------------------------------------------
func _load_saved_mysteries() -> void:
	saved_option.clear()
	host_saved_button.disabled = true
	saved_label.text = "Loading saved mysteries…"
	ApiClient.list_mysteries(_on_saved_listed)

## A MYSTERY THAT CANNOT BE ASSIGNED IS SHOWN AND DISABLED, NOT HIDDEN.
## Seventeen of the eighteen on disk predate the APF schema, so hiding them
## would leave a dropdown with one entry and no explanation of where the
## library went. Disabling them says "these exist, they are too old", which is
## the true statement. The server does the judging (GET /mysteries returns
## apf_ready) because dealability is set arithmetic over the mystery, and a
## client that guessed at it would be a second implementation of the rule.
func _on_saved_listed(error: String, data) -> void:
	if error:
		saved_label.text = "Could not list saved mysteries: " + error
		return
	_saved = data if data is Array else []
	saved_option.clear()

	var first_ready: int = -1
	for i in range(_saved.size()):
		var m: Dictionary = _saved[i]
		var ready: bool = bool(m.get("apf_ready", false))
		var title: String = str(m.get("title", m.get("slug", "?")))
		saved_option.add_item(title if ready else title + "  —  cannot be assigned")
		saved_option.set_item_disabled(i, not ready)
		if ready and first_ready < 0:
			first_ready = i

	if first_ready < 0:
		saved_label.text = (
			"None of the %d saved mysteries can be assigned — they predate the APF schema. "
			% _saved.size()
			+ "Generate one above."
		)
		host_saved_button.disabled = true
		return

	saved_option.selected = first_ready
	saved_label.text = "Or host one you already have — free, no generation:"
	host_saved_button.disabled = false

func _on_host_saved() -> void:
	var idx: int = saved_option.selected
	if idx < 0 or idx >= _saved.size():
		return
	var m: Dictionary = _saved[idx]
	if not bool(m.get("apf_ready", false)):
		## Reachable if the list changed under us. The server's own reason is
		## shown rather than a generic refusal -- "3 suspects, not 4" tells you
		## what to do next and "cannot be used" does not.
		status_label.text = "That mystery cannot be assigned: " + str(m.get("apf_blocker", ""))
		return
	_pending_slug = str(m.get("slug", ""))
	if _pending_slug.is_empty():
		status_label.text = "That mystery has no slug — cannot open a room with it."
		return
	_set_loading(true)
	status_label.text = "Loading the mystery…"
	ApiClient.get_mystery(_pending_slug, _on_saved_loaded)

func _on_saved_loaded(error: String, data: Dictionary) -> void:
	if error:
		_set_loading(false)
		status_label.text = "Could not load that mystery: " + error
		return
	## Same two steps the generation path takes, in the same order: the client
	## needs the mystery itself for the case screen, and the server needs only
	## the slug to attach it to the room.
	GameState.current_mystery = data
	_create_multiplayer_game(_pending_slug)

func _create_multiplayer_game(slug: String) -> void:
	if slug.is_empty():
		status_label.text = "Error: mystery has no slug — cannot create game."
		return
	var host_name := host_name_input.text.strip_edges()
	if host_name.is_empty():
		host_name = "Host"
	GameState.player_name = host_name
	var difficulty := difficulty_option.get_item_text(difficulty_option.selected).to_upper()
	status_label.text = "Creating game session…"
	_set_loading(true)
	ApiClient.create_game(slug, host_name, difficulty, _on_game_created)

func _on_game_created(error: String, data: Dictionary) -> void:
	_set_loading(false)
	if error:
		status_label.text = "Error creating game: " + error
		return
	GameState.game_id = data.get("game_id", "")
	GameState.player_id = data.get("player_id", "")
	## Whoever created the room is its host. Only the host may open a round or
	## close the case, so the round screen needs to know which one this is.
	GameState.is_host = true
	GameState.witness_budget = data.get("witness_budget", 0)
	GameState.investigation_budget = data.get("investigation_budget", 0)
	GameState.share_min = data.get("share_min", 0.6)
	get_tree().change_scene_to_file("res://scenes/ui/Lobby.tscn")

func _on_back() -> void:
	_polling = false
	_job_id = ""
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
func _set_loading(loading: bool) -> void:
	generate_button.disabled = loading
	back_button.disabled = loading
	prompt_input.editable = not loading
	spinner.visible = loading
	## Guarded: this screen is also used single-player, where the multiplayer
	## section and its button do not exist as far as the player is concerned.
	if GameState.is_multiplayer:
		host_saved_button.disabled = loading or saved_option.item_count == 0
