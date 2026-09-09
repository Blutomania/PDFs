## Interrogation — Phase 3 phase-aware investigation screen.
##
## Hosts all three investigation sub-phases:
##   WITNESS      — ask AI suspects/witnesses (budget-limited, hard-block on duplicates)
##   INVESTIGATION — examine named crime scene locations (budget-limited)
##   LEAD         — follow pre-generated leads (max 2)
##
## When a phase budget hits 0, the screen transitions to ShareSelection.
## Received clues from other players are shown in a collapsible panel.
##
## For Phase 2 single-player (no game_id): falls back to direct /interrogate endpoint.
##
## SESSION ANNOTATION — Phase 3:
## Poll block_pool every POLL_INTERVAL to keep hard-block UI up to date.
## Poll shared_clues every POLL_INTERVAL to surface other players' shares.

extends Control

# ---------------------------------------------------------------------------
# Node references (wire in Interrogation.tscn)
# ---------------------------------------------------------------------------
@onready var phase_label: Label = $VBox/PhaseLabel
@onready var budget_label: Label = $VBox/BudgetLabel

## Witness sub-panel
@onready var witness_panel: VBoxContainer = $VBox/WitnessPanel
@onready var suspect_grid: GridContainer = $VBox/WitnessPanel/SuspectGrid
@onready var question_row: HBoxContainer = $VBox/WitnessPanel/QuestionRow
@onready var question_input: LineEdit = $VBox/WitnessPanel/QuestionRow/QuestionInput
@onready var ask_button: Button = $VBox/WitnessPanel/QuestionRow/AskButton
@onready var witness_history: VBoxContainer = $VBox/WitnessPanel/ScrollContainer/HistoryContainer

## Godot's own mutual-exclusion for the grid -- toggling one cell on
## automatically toggles the previously-selected one off, so there is no
## manual "clear the old selection" bookkeeping to get wrong.
var _suspect_button_group: ButtonGroup = ButtonGroup.new()
var _selected_character: String = ""

## Investigation sub-panel
@onready var investigation_panel: VBoxContainer = $VBox/InvestigationPanel
@onready var areas_container: VBoxContainer = $VBox/InvestigationPanel/AreasContainer

## Lead sub-panel
@onready var lead_panel: VBoxContainer = $VBox/LeadPanel
@onready var leads_container: VBoxContainer = $VBox/LeadPanel/LeadsContainer

## Shared intel (received from other players)
@onready var shared_panel: VBoxContainer = $VBox/SharedPanel
@onready var shared_container: VBoxContainer = $VBox/SharedPanel/SharedContainer

@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner
@onready var accuse_button: Button = $VBox/AccuseButton
@onready var back_button: Button = $VBox/BackButton

var _mystery: MysteryData
var _poll_timer: float = 0.0
var _is_multiplayer: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	_mystery = MysteryData.from_dict(GameState.current_mystery)
	_is_multiplayer = not GameState.game_id.is_empty()

	# Populate suspect grid
	_build_suspect_grid()

	# Populate investigation areas
	_build_area_buttons()

	# Populate leads
	_build_lead_buttons()

	ask_button.pressed.connect(_on_ask)
	question_input.text_submitted.connect(func(_t): _on_ask())
	back_button.pressed.connect(_go_case)
	accuse_button.pressed.connect(_go_accuse)

	_set_loading(false)
	_refresh_phase_ui()
	_rebuild_history()

	if _is_multiplayer:
		# Connect WebSocket (idempotent if already open from a previous scene)
		ApiClient.connect_ws(GameState.game_id, GameState.player_id)
		ApiClient.ws_event.connect(_on_ws_event)

func _exit_tree() -> void:
	if ApiClient.ws_event.is_connected(_on_ws_event):
		ApiClient.ws_event.disconnect(_on_ws_event)

# ---------------------------------------------------------------------------
# Phase UI
# ---------------------------------------------------------------------------
func _refresh_phase_ui() -> void:
	var ip := GameState.invest_phase

	witness_panel.visible = (ip == GameState.InvestPhase.WITNESS)
	investigation_panel.visible = (ip == GameState.InvestPhase.INVESTIGATION)
	lead_panel.visible = (ip == GameState.InvestPhase.LEAD)

	match ip:
		GameState.InvestPhase.WITNESS:
			phase_label.text = "Phase 1 — Witness Interrogation"
			# Budgets are handed out by the server on game create/join, so in
			# single-player they are all 0 -- which rendered as "0 questions
			# remaining" on a screen that in fact allows unlimited questions
			# (_on_legacy_reply deliberately never calls _check_phase_complete).
			if _is_multiplayer:
				budget_label.text = "%d questions remaining" % GameState.witness_budget
			else:
				budget_label.text = "Ask as many questions as you like."
		GameState.InvestPhase.INVESTIGATION:
			phase_label.text = "Phase 2 — Crime Scene Investigation"
			budget_label.text = "%d investigations remaining" % GameState.investigation_budget
		GameState.InvestPhase.LEAD:
			phase_label.text = "Phase 3 — Follow Leads"
			budget_label.text = "%d leads remaining" % GameState.leads_remaining
		GameState.InvestPhase.DONE:
			phase_label.text = "Investigation complete"
			budget_label.text = "Make your accusation when ready."

## Transition to ShareSelection when the current phase budget is exhausted.
func _check_phase_complete() -> void:
	var advance := false
	match GameState.invest_phase:
		GameState.InvestPhase.WITNESS:
			advance = (GameState.witness_budget <= 0)
		GameState.InvestPhase.INVESTIGATION:
			advance = (GameState.investigation_budget <= 0)
		GameState.InvestPhase.LEAD:
			advance = (GameState.leads_remaining <= 0)

	if advance:
		# Set invest_phase to SHARE_* so ShareSelection knows which findings to show.
		match GameState.invest_phase:
			GameState.InvestPhase.WITNESS:
				GameState.invest_phase = GameState.InvestPhase.SHARE_WITNESS
			GameState.InvestPhase.INVESTIGATION:
				GameState.invest_phase = GameState.InvestPhase.SHARE_INVESTIGATION
			GameState.InvestPhase.LEAD:
				GameState.invest_phase = GameState.InvestPhase.SHARE_LEAD
		get_tree().change_scene_to_file("res://scenes/ui/ShareSelection.tscn")

# ---------------------------------------------------------------------------
# Witness phase
# ---------------------------------------------------------------------------
## One card per interrogatable character: portrait over name, either half
## clickable, radio-button selection via a shared ButtonGroup (playtest
## InterrogationSept8 -- replaces the old suspect dropdown). Icon set follows
## CaseDisplay's own convention: Icons.suspect() for the suspect role,
## Icons.witness() otherwise -- both degrade to no image at all when their
## set is still empty, same as everywhere else Icons.gd is used.
func _build_suspect_grid() -> void:
	for child in suspect_grid.get_children():
		child.queue_free()
	for ch in _mystery.get_interrogatable():
		var card := Button.new()
		card.theme_type_variation = &"SuspectCardButton"
		card.toggle_mode = true
		card.button_group = _suspect_button_group
		card.text = ""
		card.custom_minimum_size = Vector2(100, 120)

		var box := VBoxContainer.new()
		box.mouse_filter = Control.MOUSE_FILTER_IGNORE
		box.alignment = BoxContainer.ALIGNMENT_CENTER
		card.add_child(box)

		var icon_path: String = (
			Icons.suspect(ch.name, GameState.game_id) if ch.role == "suspect"
			else Icons.witness(ch.name, GameState.game_id)
		)
		var icon_tex: Texture2D = Icons.texture(icon_path)
		if icon_tex:
			var icon_rect := TextureRect.new()
			icon_rect.texture = icon_tex
			icon_rect.custom_minimum_size = Vector2(64, 64)
			icon_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			icon_rect.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			icon_rect.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			icon_rect.modulate = Icons.tint()
			icon_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
			box.add_child(icon_rect)

		var name_label := Label.new()
		name_label.text = ch.name
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		name_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		box.add_child(name_label)

		card.toggled.connect(_on_suspect_selected.bind(ch.name))
		suspect_grid.add_child(card)

func _on_suspect_selected(pressed: bool, character_name: String) -> void:
	## ButtonGroup fires toggled(false) on the card that just lost the
	## selection too -- only react to the one that gained it.
	if not pressed:
		return
	_selected_character = character_name
	question_row.visible = true
	question_input.grab_focus()

func _on_ask() -> void:
	var question := question_input.text.strip_edges()
	if question.is_empty():
		status_label.text = "Type a question first."
		return
	if _selected_character.is_empty():
		status_label.text = "Select a suspect first."
		return
	var character_name: String = _selected_character

	if _is_multiplayer and GameState.is_witness_blocked(character_name, question):
		status_label.text = "This question has already been shared with the group. Ask something different."
		return

	_set_loading(true)
	status_label.text = "Interrogating %s…" % character_name

	if _is_multiplayer:
		ApiClient.game_interrogate_witness(
			GameState.game_id, GameState.player_id,
			character_name, question,
			_on_witness_reply.bind(character_name, question)
		)
	else:
		ApiClient.interrogate(GameState.current_mystery, character_name, question,
			_on_legacy_reply.bind(character_name, question))

func _on_witness_reply(error: String, data: Dictionary, character_name: String, question: String) -> void:
	_set_loading(false)
	if error:
		status_label.text = _parse_block_error(error, "question")
		return
	var response: String = data.get("response", "(no response)")
	status_label.text = ""
	question_input.clear()
	GameState.record_witness_finding(data)
	GameState.record_interrogation(character_name, question, response)
	_add_history_entry(character_name, question, response)
	_refresh_phase_ui()
	_check_phase_complete()

func _on_legacy_reply(error: String, data: Dictionary, character_name: String, question: String) -> void:
	_set_loading(false)
	if error:
		status_label.text = "Error: " + error
		return
	var response: String = data.get("response", "(no response)")
	status_label.text = ""
	question_input.clear()
	GameState.record_interrogation(character_name, question, response)
	_add_history_entry(character_name, question, response)

# ---------------------------------------------------------------------------
# Investigation phase
# ---------------------------------------------------------------------------
func _build_area_buttons() -> void:
	for child in areas_container.get_children():
		child.queue_free()
	for area in _mystery.investigation_areas:
		var btn := Button.new()
		btn.text = area.name
		btn.tooltip_text = area.description
		if GameState.is_area_blocked(area.id):
			btn.disabled = true
			btn.text += " (shared)"
		btn.pressed.connect(_on_investigate_area.bind(area.id, area.name, btn))
		areas_container.add_child(btn)

func _on_investigate_area(area_id: String, area_name: String, btn: Button) -> void:
	if GameState.is_area_blocked(area_id):
		status_label.text = "This area has already been shared with the group."
		return
	_set_loading(true)
	status_label.text = "Searching %s…" % area_name
	ApiClient.investigate_area(GameState.game_id, GameState.player_id, area_id,
		_on_area_result.bind(btn))

func _on_area_result(error: String, data: Dictionary, btn: Button) -> void:
	_set_loading(false)
	if error:
		status_label.text = _parse_block_error(error, "area")
		return
	status_label.text = ""
	GameState.record_investigation_finding(data)
	# Show findings inline below the button
	var label := Label.new()
	label.text = data.get("findings", "")
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	btn.get_parent().add_child(label)
	_refresh_phase_ui()
	_check_phase_complete()

# ---------------------------------------------------------------------------
# Lead phase
# ---------------------------------------------------------------------------
func _build_lead_buttons() -> void:
	for child in leads_container.get_children():
		child.queue_free()
	for lead in _mystery.leads:
		var btn := Button.new()
		btn.text = lead.title
		btn.tooltip_text = lead.brief
		if GameState.is_lead_blocked(lead.id):
			btn.disabled = true
			btn.text += " (shared)"
		btn.pressed.connect(_on_follow_lead.bind(lead.id, lead.title, btn))
		leads_container.add_child(btn)

func _on_follow_lead(lead_id: String, lead_title: String, btn: Button) -> void:
	if GameState.is_lead_blocked(lead_id):
		status_label.text = "This lead has already been shared with the group."
		return
	if GameState.leads_remaining <= 0:
		status_label.text = "You have already used both your leads."
		return
	_set_loading(true)
	status_label.text = "Following lead: %s…" % lead_title
	ApiClient.follow_lead(GameState.game_id, GameState.player_id, lead_id,
		_on_lead_result.bind(btn))

func _on_lead_result(error: String, data: Dictionary, btn: Button) -> void:
	_set_loading(false)
	if error:
		status_label.text = _parse_block_error(error, "lead")
		return
	status_label.text = ""
	GameState.record_lead_finding(data)
	var label := Label.new()
	label.text = data.get("findings", "")
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	btn.get_parent().add_child(label)
	_refresh_phase_ui()
	_check_phase_complete()

# ---------------------------------------------------------------------------
# WebSocket push events (replace HTTP polling)
# ---------------------------------------------------------------------------
func _on_ws_event(event_name: String, data: Dictionary) -> void:
	match event_name:
		"block_updated":
			GameState.update_block_pool(data)
			_build_area_buttons()
			_build_lead_buttons()
		"clues_shared":
			GameState.merge_shared_clues({
				data.get("phase", "witness"): data.get("clues", [])
			})
			_rebuild_shared_panel()
		"player_joined":
			status_label.text = "%s joined the game." % data.get("name", "A player")

func _rebuild_shared_panel() -> void:
	for child in shared_container.get_children():
		child.queue_free()
	var all_shared: Array = []
	for phase_key in ["witness", "investigation", "lead"]:
		all_shared.append_array(GameState.shared_clues[phase_key])
	if all_shared.is_empty():
		return
	for clue in all_shared:
		var lbl := Label.new()
		var sender: String = clue.get("sender_name", "Unknown")
		if clue.has("question"):
			lbl.text = "[%s → %s] %s" % [sender, clue.get("character", "?"), clue.get("response", "")]
		elif clue.has("area_name"):
			lbl.text = "[%s @ %s] %s" % [sender, clue.get("area_name", "?"), clue.get("findings", "")]
		else:
			lbl.text = "[%s lead] %s" % [sender, clue.get("findings", "")]
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		shared_container.add_child(lbl)

# ---------------------------------------------------------------------------
# Witness history (single-player + Phase 2 compatibility)
# ---------------------------------------------------------------------------
func _rebuild_history() -> void:
	for child in witness_history.get_children():
		child.queue_free()
	for entry in GameState.interrogation_history:
		_add_history_entry(entry["character"], entry["question"], entry["response"])

func _add_history_entry(character: String, question: String, response: String) -> void:
	var panel := PanelContainer.new()
	var vbox := VBoxContainer.new()
	var q_label := Label.new()
	q_label.text = "[%s] %s" % [character, question]
	q_label.add_theme_color_override("font_color", Palette.BRASS)
	var r_label := Label.new()
	r_label.text = response
	r_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(q_label)
	vbox.add_child(r_label)
	panel.add_child(vbox)
	witness_history.add_child(panel)

# ---------------------------------------------------------------------------
# Error parsing
# ---------------------------------------------------------------------------
func _parse_block_error(error: String, _type: String) -> String:
	## Server 409 block errors come back as JSON strings; extract the reason.
	if "blocked" in error.to_lower():
		return error
	return "Error: " + error

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")

func _go_accuse() -> void:
	GameState.game_phase = GameState.Phase.ACCUSATION
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
func _set_loading(loading: bool) -> void:
	ask_button.disabled = loading
	question_input.editable = not loading
	for card: Node in suspect_grid.get_children():
		if card is Button:
			card.disabled = loading
	spinner.visible = loading
