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

## These two headings are a matched PAIR by design (owner, playtest StartPageSept7):
## "The Scene:" sits above the setting description, "The Crime:" sits above
## what happened, and they read as one visual family — same weight, same
## "word(s) + colon" shape. If either wording changes, change the other to
## match; do not let them drift into two different heading conventions for
## what is visually the same kind of label.
const _SCENE_HEADING: String = "The Scene:"
const _CRIME_HEADING: String = "The Crime:"

func _populate() -> void:
	title_label.text = _mystery.title

	setting_label.text = (
		"[b]%s[/b]\n[b]%s[/b] — [i]%s[/i]\n%s" % [
			_SCENE_HEADING,
			_mystery.location,
			_mystery.time_period,
			_mystery.setting_description,
		]
	)

	crime_label.text = (
		"[b]%s[/b]\n%s\n[i]When: %s[/i]\n[i]Discovered: %s[/i]" % [
			_CRIME_HEADING,
			_mystery.what_happened,
			_mystery.when_occurred,
			_mystery.initial_discovery,
		]
	)

	# --- Cast ---
	# Clear any placeholder children
	for child in cast_container.get_children():
		child.queue_free()

	## Role labels, not bracketed tags (owner, playtest StartPageSept7): "The
	## Victim:", "Suspect 1:", "Witness 1:" — numbered per person within their
	## own role, in cast order. `_add_cast_row` takes the finished label text
	## rather than a bare tag, since numbering has to happen here where the
	## index is available, not inside the row-builder.
	var victim := _mystery.get_victim()
	if victim.name:
		_add_cast_row("The Victim:", victim.name, victim.occupation, Palette.NEGATIVE)

	var suspects := _mystery.get_suspects()
	for i in range(suspects.size()):
		## No `.id` field on CharacterData -- `.name` is the stable, unique-
		## per-mystery key the server side already treats it as, so it is the
		## right seed for Icons.suspect() too.
		var suspect_icon: String = Icons.suspect(suspects[i].name, GameState.game_id)
		_add_cast_row("Suspect %d:" % (i + 1), suspects[i].name, suspects[i].occupation, Palette.BRASS, suspect_icon)

	var witnesses := _mystery.characters.filter(func(c): return c.role == "witness")
	for i in range(witnesses.size()):
		_add_cast_row("Witness %d:" % (i + 1), witnesses[i].name, witnesses[i].occupation, Palette.STEEL_BRIGHT)

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
	for i in range(_mystery.evidence.size()):
		_add_evidence_row(i, _mystery.evidence[i])

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
## `role_label` is the finished heading -- "The Victim:", "Suspect 2:" -- not a
## bare tag. Numbering a suspect or witness needs the loop index, which lives
## with the caller, not here.
## `icon_path` is optional (default "" -- no icon drawn), matching the way
## Icons.texture() itself degrades: a role with no icon set yet (victim,
## witness -- SUSPECT is the only set wired to a row so far, playtest
## StartPageSept7) renders exactly as it did before this parameter existed.
func _add_cast_row(role_label: String, name: String, occupation: String, color: Color,
		icon_path: String = "") -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", Palette.SPACE_SMALL)

	var icon_tex: Texture2D = Icons.texture(icon_path)
	if icon_tex:
		var icon_rect := TextureRect.new()
		icon_rect.texture = icon_tex
		icon_rect.custom_minimum_size = Vector2(20, 20)
		icon_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon_rect.modulate = Icons.tint()
		row.add_child(icon_rect)

	var lbl := Label.new()
	lbl.text = "%s %s — %s" % [role_label, name, occupation]
	lbl.add_theme_color_override("font_color", color)
	lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(lbl)

	cast_container.add_child(row)

## `index` is this clue's position among ALL evidence (0-based); the row reads
## "Clue 1:", "Clue 2:", ... in that order -- the id (`ev.id`, "E1") stays the
## STORAGE key, matching cast rows' "Suspect 1:"/"Witness 1:" numbering
## (owner, playtest StartPageSept7).
func _add_evidence_row(index: int, ev: MysteryData.EvidenceData) -> void:
	# Dictionary.get() returns Variant, so `:=` infers Variant here and Godot
	# treats that inference as an error. The type has to be stated.
	var relevance_icon: String = {"critical": "★", "red_herring": "✗", "supporting": "·"}.get(ev.relevance, "·")

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", Palette.SPACE_SMALL)

	## Decorative only -- Icons.gd's own rule: which of the four magnifiers
	## lands here carries no information about the clue. Seeded on the clue's
	## own id plus the game id, so it stays stable for as long as anyone is
	## looking at it and reshuffles between games (owner, playtest
	## StartPageSept7 -- the first screen this ever gets wired to).
	var icon_tex: Texture2D = Icons.texture(Icons.clue(ev.id, GameState.game_id))
	if icon_tex:
		var icon_rect := TextureRect.new()
		icon_rect.texture = icon_tex
		icon_rect.custom_minimum_size = Vector2(20, 20)
		icon_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon_rect.modulate = Icons.tint()
		row.add_child(icon_rect)

	var lbl := Label.new()
	lbl.text = "%s Clue %d: %s (%s)" % [relevance_icon, index + 1, ev.name, ev.type]
	lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(lbl)

	evidence_container.add_child(row)

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
	ApiClient.apf_open(GameState.game_id, GameState.player_id, _on_assigned)

func _on_assigned(error: String, data: Dictionary) -> void:
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
