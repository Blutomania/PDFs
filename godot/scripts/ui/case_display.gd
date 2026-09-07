## CaseDisplay — shows the generated mystery:
## title, setting, crime, victim, suspects, coherence badge, evidence,
## investigation areas, leads, and shared intel from other players.
##
## The viability rating widget lives on this screen (bottom).
## In Phase 3 multiplayer, the Shared Intel panel shows clues received
## from other players (polled every 3s).

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var title_label: Label = $ScrollContainer/MainVBox/TitleLabel
@onready var setting_label: RichTextLabel = $ScrollContainer/MainVBox/SettingLabel
@onready var crime_label: RichTextLabel = $ScrollContainer/MainVBox/CrimeLabel
@onready var cast_container: VBoxContainer = $ScrollContainer/MainVBox/CastContainer
@onready var coherence_label: Label = $ScrollContainer/MainVBox/CoherenceBadge
@onready var evidence_container: VBoxContainer = $ScrollContainer/MainVBox/EvidenceContainer
@onready var gameplay_label: Label = $ScrollContainer/MainVBox/GameplayLabel
@onready var interrogate_button: Button = $ScrollContainer/MainVBox/Buttons/InterrogateButton
@onready var accuse_button: Button = $ScrollContainer/MainVBox/Buttons/AccuseButton
@onready var begin_rounds_button: Button = $ScrollContainer/MainVBox/Buttons/BeginRoundsButton
@onready var viability_hbox: HBoxContainer = $ScrollContainer/MainVBox/ViabilityRow
@onready var viability_label: Label = $ScrollContainer/MainVBox/ViabilityRow/ViabilityLabel
@onready var areas_container: VBoxContainer = $ScrollContainer/MainVBox/AreasContainer
@onready var leads_container: VBoxContainer = $ScrollContainer/MainVBox/LeadsContainer
@onready var shared_intel_container: VBoxContainer = $ScrollContainer/MainVBox/SharedIntelContainer

var _mystery: MysteryData
var _current_rating: int = 0

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	_mystery = MysteryData.from_dict(GameState.current_mystery)
	_populate()
	interrogate_button.pressed.connect(_go_interrogate)
	accuse_button.pressed.connect(_go_accuse)
	begin_rounds_button.pressed.connect(_on_begin_rounds)
	## THIS SCREEN IS APF'S OPENING: the crime, told, before any finding is
	## assigned. Only the host can assignment, and only in a room -- a saved mystery
	## opened from the browse list is one person reading, with nobody to share
	## with, so the button stays hidden there.
	begin_rounds_button.visible = GameState.is_host and not GameState.game_id.is_empty()
	if not GameState.game_id.is_empty():
		ApiClient.ws_event.connect(_on_ws_event)

func _exit_tree() -> void:
	if ApiClient.ws_event.is_connected(_on_ws_event):
		ApiClient.ws_event.disconnect(_on_ws_event)

func _on_ws_event(event_name: String, data: Dictionary) -> void:
	## The host assigned. Everyone in the room moves to the round screen together.
	if event_name == "apf_opened":
		GameState.record_apf_open(data)
		_go_rounds()
		return
	if event_name == "clues_shared":
		GameState.merge_shared_clues({
			data.get("phase", "witness"): data.get("clues", [])
		})
		_rebuild_shared_intel()

func _populate() -> void:
	title_label.text = _mystery.title

	setting_label.text = (
		"[b]%s[/b] — [i]%s[/i]\n%s" % [
			_mystery.location,
			_mystery.time_period,
			_mystery.setting_description,
		]
	)

	crime_label.text = (
		"[b]The Crime[/b]\n%s\n[i]When: %s[/i]\n[i]Discovered: %s[/i]" % [
			_mystery.what_happened,
			_mystery.when_occurred,
			_mystery.initial_discovery,
		]
	)

	# --- Cast ---
	# Clear any placeholder children
	for child in cast_container.get_children():
		child.queue_free()

	var victim := _mystery.get_victim()
	if victim.name:
		_add_cast_row("VICTIM", victim.name, victim.occupation, Palette.NEGATIVE)

	for suspect in _mystery.get_suspects():
		_add_cast_row("SUSPECT", suspect.name, suspect.occupation, Palette.BRASS)

	var witnesses := _mystery.characters.filter(func(c): return c.role == "witness")
	for w in witnesses:
		_add_cast_row("WITNESS", w.name, w.occupation, Palette.STEEL_BRIGHT)

	# --- Coherence badge ---
	if _mystery.coherence_passed:
		coherence_label.text = "Coherence: PASS (%d warnings)" % _mystery.coherence_warnings
		coherence_label.add_theme_color_override("font_color", Palette.POSITIVE)
	else:
		coherence_label.text = (
			"Coherence: FAIL — %d blocking, %d warnings" % [
				_mystery.coherence_blocking,
				_mystery.coherence_warnings,
			]
		)
		coherence_label.add_theme_color_override("font_color", Palette.NEGATIVE)

	# --- Evidence ---
	for child in evidence_container.get_children():
		child.queue_free()
	for ev in _mystery.evidence:
		_add_evidence_row(ev)

	# --- Gameplay notes ---
	var twists_text := " · ".join(_mystery.key_twists) if _mystery.key_twists else "none"
	gameplay_label.text = (
		"Difficulty: %s  ·  Playtime: %s\nKey twists: %s" % [
			_mystery.difficulty,
			_mystery.estimated_playtime,
			twists_text,
		]
	)

	# --- Investigation areas ---
	_populate_areas()

	# --- Leads ---
	_populate_leads()

	# --- Shared Intel (multiplayer) ---
	_rebuild_shared_intel()

	# --- Viability rating buttons ---
	_build_viability_buttons()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
func _add_cast_row(role_tag: String, name: String, occupation: String, color: Color) -> void:
	var lbl := Label.new()
	lbl.text = "[%s] %s — %s" % [role_tag, name, occupation]
	lbl.add_theme_color_override("font_color", color)
	cast_container.add_child(lbl)

func _add_evidence_row(ev: MysteryData.EvidenceData) -> void:
	# Dictionary.get() returns Variant, so `:=` infers Variant here and Godot
	# treats that inference as an error. The type has to be stated.
	var relevance_icon: String = {"critical": "★", "red_herring": "✗", "supporting": "·"}.get(ev.relevance, "·")
	var lbl := Label.new()
	lbl.text = "%s [%s] %s (%s)" % [relevance_icon, ev.id, ev.name, ev.type]
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	evidence_container.add_child(lbl)

func _build_viability_buttons() -> void:
	# Free only the buttons this function added. The previous version freed
	# every child and then re-added viability_label -- but that label is a
	# child of ViabilityRow in the scene, so add_child() on it raises
	# "already has a parent", and the queue_free() then deleted it at the end
	# of the frame. The row lost its label and printed an engine error.
	for child in viability_hbox.get_children():
		if child != viability_label:
			child.queue_free()
	viability_label.text = "Rate this mystery: "
	for i in range(1, 11):
		var btn := Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(36, 36)
		btn.pressed.connect(_on_rate.bind(i))
		viability_hbox.add_child(btn)

func _on_rate(rating: int) -> void:
	_current_rating = rating
	var slug: String = GameState.current_mystery.get("_slug", "")
	if slug.is_empty():
		return
	ApiClient.rate_mystery(slug, rating, func(err, _d):
		if err:
			push_warning("Rating save failed: " + err)
	)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_interrogate() -> void:
	GameState.game_phase = GameState.Phase.INTERROGATION
	get_tree().change_scene_to_file("res://scenes/ui/Interrogation.tscn")

## Build the casefiles and set the rounds going, and let the game ANNOUNCE its length before
## play begins. Owner, Session 41: "the game TELLS the users. This mystery has a
## maximum of X rounds. It creates tension and sets expectations."
##
## The assignment is free and deterministic, so a refusal here is a statement about
## the mystery rather than bad luck -- it is shown as such instead of as a retry.
func _on_begin_rounds() -> void:
	begin_rounds_button.disabled = true
	begin_rounds_button.text = "Opening the case…"
	ApiClient.apf_open(GameState.game_id, GameState.player_id, _on_dealt)

func _on_dealt(error: String, data: Dictionary) -> void:
	if error:
		begin_rounds_button.disabled = false
		begin_rounds_button.text = "Begin the investigation"
		coherence_label.text = "This mystery cannot be assigned: " + error
		coherence_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	GameState.record_apf_open(data)
	_go_rounds()

func _go_rounds() -> void:
	GameState.game_phase = GameState.Phase.INTERROGATION
	get_tree().change_scene_to_file("res://scenes/ui/ApfRound.tscn")

func _go_accuse() -> void:
	GameState.game_phase = GameState.Phase.ACCUSATION
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")

func _populate_areas() -> void:
	if not is_instance_valid(areas_container):
		return
	for child in areas_container.get_children():
		child.queue_free()
	if _mystery.investigation_areas.is_empty():
		return
	var header := Label.new()
	header.text = "Investigation Areas"
	header.add_theme_color_override("font_color", Palette.STEEL_BRIGHT)
	areas_container.add_child(header)
	for area in _mystery.investigation_areas:
		var lbl := Label.new()
		lbl.text = "  [%s] %s" % [area.id, area.name]
		lbl.tooltip_text = area.description
		areas_container.add_child(lbl)

func _populate_leads() -> void:
	if not is_instance_valid(leads_container):
		return
	for child in leads_container.get_children():
		child.queue_free()
	if _mystery.leads.is_empty():
		return
	var header := Label.new()
	header.text = "Leads"
	header.add_theme_color_override("font_color", Palette.BRASS)
	leads_container.add_child(header)
	for lead in _mystery.leads:
		var lbl := Label.new()
		lbl.text = "  [%s] %s — %s" % [lead.id, lead.title, lead.brief]
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		leads_container.add_child(lbl)

func _rebuild_shared_intel() -> void:
	if not is_instance_valid(shared_intel_container):
		return
	for child in shared_intel_container.get_children():
		child.queue_free()
	var all_shared: Array = []
	for phase_key in ["witness", "investigation", "lead"]:
		all_shared.append_array(GameState.shared_clues[phase_key])
	if all_shared.is_empty():
		return
	var header := Label.new()
	header.text = "Shared Intel"
	header.add_theme_color_override("font_color", Palette.POSITIVE)
	shared_intel_container.add_child(header)
	for clue in all_shared:
		var lbl := Label.new()
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var sender: String = clue.get("sender_name", "?")
		if clue.has("question"):
			lbl.text = "  [%s → %s] %s" % [sender, clue.get("character", "?"), clue.get("response", "")]
		elif clue.has("area_name"):
			lbl.text = "  [%s @ %s] %s" % [sender, clue.get("area_name", "?"), clue.get("findings", "")]
		else:
			lbl.text = "  [%s lead] %s" % [sender, clue.get("findings", "")]
		shared_intel_container.add_child(lbl)
