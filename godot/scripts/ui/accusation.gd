## Accusation — player selects a suspect and submits their final answer.
## Compares locally against the solution already in the mystery dict —
## no extra API call needed (the server included the solution in /generate).
##
## SESSION ANNOTATION — Phase 3:
## In multiplayer, accusation must be validated server-side to prevent cheating.
## Add a POST /accuse endpoint and call it here instead of comparing locally.
## The server broadcasts the result to all players.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var suspect_dropdown: OptionButton = $VBox/SuspectDropdown
@onready var submit_button: Button = $VBox/SubmitButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var confirm_dialog: ConfirmationDialog = $ConfirmDialog

var _mystery: MysteryData
var _selected_suspect: String = ""

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	_mystery = MysteryData.from_dict(GameState.current_mystery)

	for name in _mystery.suspect_names():
		suspect_dropdown.add_item(name)

	submit_button.pressed.connect(_on_submit_pressed)
	back_button.pressed.connect(_go_case)
	confirm_dialog.confirmed.connect(_on_confirmed)

	if suspect_dropdown.item_count == 0:
		submit_button.disabled = true
		status_label.text = "No suspects found in this mystery."
	else:
		_warn_if_unsolvable()

## Playtest aid: say so on screen when no listed suspect can possibly be the
## answer. The coherence report already knows (it is why _coherence.passed is
## false), but nothing acted on that verdict, so the failure used to reach the
## player as an ordinary "Wrong" and looked like their mistake.
func _warn_if_unsolvable() -> void:
	var culprit: String = GameState.current_mystery.get("solution", {}).get("culprit", "")
	var suspects := _mystery.suspect_names()
	for s in suspects:
		if _is_culprit(str(s), culprit, suspects):
			return
	status_label.text = "⚠ This mystery's solution names no listed suspect — it cannot be solved as generated."
	status_label.add_theme_color_override("font_color", Palette.CAUTION)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_submit_pressed() -> void:
	if suspect_dropdown.item_count == 0:
		return
	_selected_suspect = suspect_dropdown.get_item_text(suspect_dropdown.selected)
	confirm_dialog.dialog_text = (
		"Are you sure you want to accuse %s?\nThis ends the investigation." % _selected_suspect
	)
	confirm_dialog.popup_centered()

## Returns true if `accused` is named as a culprit in `culprit_field`.
##
## solution.culprit is meant to be exactly one character name, and
## coherence_validator raises P1.C4.culprit_not_in_characters (BLOCKING,
## "Chain is broken; players can never identify them") when it is not.
## Generation still produces prose for multi-culprit solutions -- one saved
## mystery reads "Smurfwick the Craftsmurf (primary architect) and Smurfadel,
## Master of Adornment (accomplice who physically carried the Star)". Under
## exact equality every accusation on such a mystery is wrong, including the
## correct one, so the game cannot be won at all. Substring matching makes it
## winnable without pretending the underlying data is clean.
func _is_culprit(accused: String, culprit_field: String, all_suspects: Array) -> bool:
	if accused == culprit_field:
		return true
	if accused.is_empty() or not culprit_field.contains(accused):
		return false
	# A shorter name can sit inside a longer one ("Smurf" inside "Smurfwick"),
	# in which case a substring hit proves nothing about who was named.
	for other in all_suspects:
		if other != accused and str(other).contains(accused):
			return false
	return true

## IN A ROOM THE SERVER DECIDES, and it has to. First CORRECT accusation wins,
## and only the server can adjudicate that -- two players can both be right
## within a second of each other, and a client comparing locally would tell them
## both they won. It is also the only side that has the solution: /mystery-brief
## deliberately withholds it, so a phone client could not compare even if it
## wanted to.
##
## Single player keeps the local comparison. There is no race, no server-held
## solution to consult, and no room to broadcast to.
func _on_confirmed() -> void:
	if GameState.game_id.is_empty():
		_finish_locally()
		return
	submit_button.disabled = true
	status_label.text = "Making the accusation…"
	ApiClient.accuse(GameState.game_id, GameState.player_id, _selected_suspect, _on_accused)

func _on_accused(error: String, data: Dictionary) -> void:
	## A network failure must not swallow the accusation. Falling back to the
	## local comparison still reaches the result screen, which is the stage-1
	## test -- it just cannot say who got there first.
	if error:
		status_label.text = "The table did not answer (" + error + ") — scoring locally."
		status_label.add_theme_color_override("font_color", Palette.CAUTION)
		_finish_locally()
		return
	var solution: Dictionary = GameState.current_mystery.get("solution", {})
	GameState.accusation_result = {
		"correct": bool(data.get("correct", false)),
		"won": bool(data.get("won", false)),
		"suspect_guessed": _selected_suspect,
		"culprit": solution.get("culprit", ""),
		"solution": solution,
	}
	_go_result()

func _finish_locally() -> void:
	var solution: Dictionary = GameState.current_mystery.get("solution", {})
	var culprit: String = solution.get("culprit", "")
	var correct: bool = _is_culprit(_selected_suspect, culprit, _mystery.suspect_names())

	GameState.accusation_result = {
		"correct": correct,
		"suspect_guessed": _selected_suspect,
		"culprit": culprit,
		"solution": solution,
	}
	_go_result()

func _go_result() -> void:
	GameState.game_phase = GameState.Phase.RESULT
	get_tree().change_scene_to_file("res://scenes/ui/ResultScreen.tscn")

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
