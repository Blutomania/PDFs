## ApfRound — the APF play screen, and the only screen the mechanic needs.
##
## THIS SCREEN IS THE GAME. With exploration gone there is no traversal, no
## budget and no phase gate; what is left is a casefile, a decision about it, and a
## board that makes the decision visible. docs/PLAYTEST_FLOW.md: "the casefile and
## the share are not part of the game — they are the game."
##
## WHY THE SHARE IS NOT ITS OWN SCREEN. It used to be (ShareSelection.tscn,
## still here and still wired to the gather loop). Under the rhythm the share
## belongs beside the board, because the board is what makes withholding legible
## without a word of explanation: a face stays lit that you could have darkened,
## and everyone can see you didn't. Moving the decision to a separate screen
## hides the one thing that gives it weight.
##
## THE CLIENT DERIVES NOTHING. The round, the requirement, the board and the
## pool all arrive from GET /apf/state. In particular the share minimum is the
## server's own answer — a second implementation of that rule has already cost
## this project a screen's worth of silently-refused legal moves, and
## scripts/test_share_rule.py exists to stop it coming back.
##
## Reached from the lobby once the host has assigned. Leaves for Accusation.tscn.

extends Control

# ---------------------------------------------------------------------------
# Node references (wire in ApfRound.tscn)
# ---------------------------------------------------------------------------
@onready var round_label: Label = $Margin/MainVBox/Header/RoundLabel
@onready var requirement_label: Label = $Margin/MainVBox/Header/RequirementLabel
@onready var board_container: VBoxContainer = $Margin/MainVBox/Columns/BoardColumn/BoardScroll/BoardContainer
@onready var casefile_container: VBoxContainer = $Margin/MainVBox/Columns/CasefileColumn/CasefileScroll/CasefileContainer
@onready var pool_container: VBoxContainer = $Margin/MainVBox/Columns/PoolColumn/PoolScroll/PoolContainer
@onready var table_label: Label = $Margin/MainVBox/TableLabel
@onready var status_label: Label = $Margin/MainVBox/StatusLabel
@onready var share_button: Button = $Margin/MainVBox/Actions/ShareButton
@onready var next_round_button: Button = $Margin/MainVBox/Actions/NextRoundButton
@onready var close_case_button: Button = $Margin/MainVBox/Actions/CloseCaseButton
@onready var accuse_button: Button = $Margin/MainVBox/Actions/AccuseButton

## Checkboxes for findings not yet shared, parallel to _selectable.
var _checkboxes: Array[CheckBox] = []
## The finding dicts each checkbox stands for. Shared findings are NOT in here:
## sharing is monotone, so an already-shared finding has no decision left in it.
var _selectable: Array = []
var _busy: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	share_button.pressed.connect(_on_share)
	next_round_button.pressed.connect(_on_next_round)
	close_case_button.pressed.connect(_on_close_case)
	accuse_button.pressed.connect(_on_accuse)

	## Other players' shares change the board and the pool, so the screen has to
	## react to them rather than only to its own actions. One refetch per event
	## is cheap: /apf/state is set arithmetic over a mystery already in memory.
	ApiClient.ws_event.connect(_on_ws_event)

	_render()
	_refresh()

func _on_ws_event(event_name: String, _data: Dictionary) -> void:
	if event_name in ["apf_state", "apf_opened", "apf_disclosed"]:
		_refresh()

# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------
func _refresh() -> void:
	ApiClient.apf_state(GameState.game_id, GameState.player_id, _on_state)

func _on_state(error: String, data: Dictionary) -> void:
	if error:
		status_label.text = "Could not reach the table: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	GameState.record_apf_state(data)
	_render()

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
func _render() -> void:
	var state: Dictionary = GameState.apf_state
	if state.is_empty():
		round_label.text = "Opening the case…"
		return

	var current: int = int(state.get("round", 0))
	var total: int = int(state.get("rounds", 0))
	round_label.text = "Round %d of %d" % [current, total]

	_render_requirement(state)
	_render_board()
	_render_casefile()
	_render_pool(state)
	_render_table(state)
	_render_actions(state)

## The requirement is stated as a TOTAL, because that is what it is. Saying
## "share 1 more" would hide the shape of the rule — the ladder is cumulative,
## and a player who gave two away in round 2 has already met round 4.
func _render_requirement(state: Dictionary) -> void:
	var required: int = int(state.get("share_required", 0))
	var held: int = int(state.get("held", 0))
	var owed: int = int(state.get("share_outstanding", 0))

	if bool(state.get("disclosed", false)):
		requirement_label.text = "The case is closed — everything is on the table."
		requirement_label.remove_theme_color_override("font_color")
		return
	if required <= 0:
		## Round 1. Holding a single finding forces a share whatever the difficulty, so
		## there is no decision here and the screen does not pretend otherwise.
		requirement_label.text = "Read your finding. Nothing is asked of you yet."
		requirement_label.remove_theme_color_override("font_color")
		return

	requirement_label.text = "%d of your %d must be on the table" % [required, held]
	if owed > 0:
		requirement_label.text += "  ·  %d still owed" % owed
		requirement_label.add_theme_color_override("font_color", Palette.CAUTION)
	else:
		requirement_label.add_theme_color_override("font_color", Palette.POSITIVE)

## The suspect board. A row greys out when somebody SHARES a finding that clears
## that person, and the sharer's name goes on it. Nothing here greys a face on a
## narrowing (item 27): "man's size large" is a line the player draws, and a
## board that draws it for them deletes the deduction.
func _render_board() -> void:
	for child in board_container.get_children():
		child.queue_free()

	for entry in GameState.apf_board():
		var row: Dictionary = entry
		var box := VBoxContainer.new()

		var name_label := Label.new()
		name_label.text = str(row.get("name", "?"))
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

		var cleared: bool = bool(row.get("cleared", false))
		if cleared:
			## Struck through and dimmed: the face is still on the board, because
			## knowing who is out is half the deduction.
			name_label.add_theme_color_override("font_color", Palette.INK_FAINT)
			box.modulate = Color(1.0, 1.0, 1.0, 0.55)
		else:
			name_label.add_theme_color_override("font_color", Palette.INK)

		box.add_child(name_label)

		var by_label := Label.new()
		by_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		by_label.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
		if cleared:
			by_label.text = _cleared_by_text(row.get("cleared_by", []))
			by_label.add_theme_color_override("font_color", Palette.INK_MUTED)
		else:
			by_label.text = "still standing"
			by_label.add_theme_color_override("font_color", Palette.BRASS)
		box.add_child(by_label)

		board_container.add_child(box)
		board_container.add_child(HSeparator.new())

## Attribution is the point, so the first name is spelled out rather than
## counted. "Ana cleared them in round 2" is a sentence about a person.
func _cleared_by_text(sources: Array) -> String:
	if sources.is_empty():
		return "cleared"
	var first: Dictionary = sources[0]
	var who: String = str(first.get("player_name", "someone"))
	var text: String = "cleared by %s in round %d" % [who, int(first.get("round", 0))]
	if bool(first.get("disclosure", false)):
		text += " (full disclosure)"
	if sources.size() > 1:
		text += " · and %d more" % (sources.size() - 1)
	return text

## Your casefile. Findings you have already shared stay in it — an investigator
## cannot be made to forget — but they carry no checkbox, because there is
## nothing left to decide about them. What you spend is exclusivity.
func _render_casefile() -> void:
	for child in casefile_container.get_children():
		child.queue_free()
	_checkboxes.clear()
	_selectable.clear()

	for entry in GameState.apf_casefile():
		var finding: Dictionary = entry
		var shared: bool = bool(finding.get("shared", false))
		var box := VBoxContainer.new()

		var head := HBoxContainer.new()
		if shared:
			var mark := Label.new()
			mark.text = "shared"
			mark.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
			mark.add_theme_color_override("font_color", Palette.POSITIVE)
			head.add_child(mark)
		else:
			var cb := CheckBox.new()
			cb.toggled.connect(_on_toggle)
			head.add_child(cb)
			_checkboxes.append(cb)
			_selectable.append(finding)

		var title := Label.new()
		title.text = "%s  ·  %s" % [str(finding.get("title", "?")), str(finding.get("kind", ""))]
		title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		title.add_theme_color_override("font_color", Palette.INK)
		head.add_child(title)
		box.add_child(head)

		var body := Label.new()
		body.text = str(finding.get("body", ""))
		body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		body.add_theme_color_override("font_color", Palette.INK_MUTED)
		box.add_child(body)

		if shared:
			box.modulate = Color(1.0, 1.0, 1.0, 0.7)

		casefile_container.add_child(box)
		casefile_container.add_child(HSeparator.new())

## What the room has. Ordered oldest first, with the name of whoever put it
## there — the order IS the social record, and it is what "she's held back twice
## now" is read off.
func _render_pool(state: Dictionary) -> void:
	for child in pool_container.get_children():
		child.queue_free()

	var pool: Array = state.get("shared_pool", [])
	if pool.is_empty():
		var empty := Label.new()
		empty.text = "Nothing yet."
		empty.add_theme_color_override("font_color", Palette.INK_FAINT)
		pool_container.add_child(empty)
		return

	for entry in pool:
		var item: Dictionary = entry
		var box := VBoxContainer.new()

		var who := Label.new()
		who.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
		if bool(item.get("disclosure", false)):
			who.text = "%s held this back · round %d" % [
				str(item.get("shared_by", "?")), int(item.get("shared_round", 0))]
			who.add_theme_color_override("font_color", Palette.CAUTION)
		else:
			who.text = "%s shared this · round %d" % [
				str(item.get("shared_by", "?")), int(item.get("shared_round", 0))]
			who.add_theme_color_override("font_color", Palette.BRASS)
		box.add_child(who)

		var title := Label.new()
		title.text = str(item.get("title", "?"))
		title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		title.add_theme_color_override("font_color", Palette.INK)
		box.add_child(title)

		var body := Label.new()
		body.text = str(item.get("body", ""))
		body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		body.add_theme_color_override("font_color", Palette.INK_MUTED)
		box.add_child(body)

		pool_container.add_child(box)
		pool_container.add_child(HSeparator.new())

## Who has paid and who has not. Public on purpose: the pattern across rounds is
## the thing the mechanic exists to produce.
func _render_table(state: Dictionary) -> void:
	var parts: PackedStringArray = []
	for entry in state.get("players", []):
		var p: Dictionary = entry
		var line: String = "%s: %d shared" % [str(p.get("name", "?")), int(p.get("shared", 0))]
		if int(p.get("outstanding", 0)) > 0:
			line += " (owes %d)" % int(p.get("outstanding", 0))
		parts.append(line)
	table_label.text = "  ·  ".join(parts)

func _render_actions(state: Dictionary) -> void:
	var disclosed: bool = bool(state.get("disclosed", false))
	var current: int = int(state.get("round", 0))
	var total: int = int(state.get("rounds", 0))
	var final_round: bool = current >= total

	## Only the host assigns and closes; everyone else would get a 403.
	next_round_button.visible = GameState.is_host and not disclosed and not final_round
	close_case_button.visible = GameState.is_host and not disclosed and final_round

	next_round_button.disabled = _busy or not bool(state.get("checkpoint_met", false))
	close_case_button.disabled = _busy or not bool(state.get("checkpoint_met", false))
	share_button.visible = not disclosed
	accuse_button.disabled = _busy

	_update_share_button()

func _update_share_button() -> void:
	var owed: int = GameState.apf_outstanding()
	var chosen: int = _selected_ids().size()
	share_button.disabled = _busy or chosen == 0
	if owed > 0 and chosen < owed:
		share_button.text = "Share selected (%d of %d owed)" % [chosen, owed]
	elif chosen > 0:
		share_button.text = "Share %d" % chosen
	else:
		share_button.text = "Share selected"

func _on_toggle(_pressed: bool) -> void:
	_update_share_button()

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------
func _selected_ids() -> Array:
	var ids: Array = []
	for i in range(_checkboxes.size()):
		if _checkboxes[i].button_pressed:
			ids.append(str(_selectable[i].get("id", "")))
	return ids

## Sharing MORE than the minimum is legal and deliberately not blocked: the
## requirement is a floor, not a cap, and giving something away early is a real
## move. The server is the only thing that refuses a share, and it refuses only
## a finding the player was never assigned.
func _on_share() -> void:
	var ids: Array = _selected_ids()
	if ids.is_empty():
		return
	_set_busy(true)
	status_label.text = "Putting %d on the table…" % ids.size()
	ApiClient.apf_share(GameState.game_id, GameState.player_id, ids, _on_share_result)

func _on_share_result(error: String, data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "The table did not accept that: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	var owed: int = int(data.get("outstanding", 0))
	if owed > 0:
		status_label.text = "Shared. You still owe %d." % owed
	else:
		status_label.text = "Shared. The table is waiting on the others."
	_refresh()

func _on_next_round() -> void:
	_set_busy(true)
	status_label.text = "Opening the next round…"
	ApiClient.apf_next_round(GameState.game_id, GameState.player_id, _on_round_result)

func _on_round_result(error: String, _data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "Could not open the next round: " + error
		status_label.add_theme_color_override("font_color", Palette.CAUTION)
		return
	status_label.remove_theme_color_override("font_color")
	status_label.text = ""
	_refresh()

## Full disclosure. Not a tie-breaker and not a rescue — it is the reward for
## having chosen this mystery, and it is what puts a name against every finding
## somebody sat on.
func _on_close_case() -> void:
	_set_busy(true)
	status_label.text = "Closing the case…"
	ApiClient.apf_disclose(GameState.game_id, GameState.player_id, _on_disclose_result)

func _on_disclose_result(error: String, _data: Dictionary) -> void:
	_set_busy(false)
	if error:
		status_label.text = "Could not close the case: " + error
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
		return
	status_label.remove_theme_color_override("font_color")
	status_label.text = "Everything is on the table. Make your accusation."
	_refresh()

func _on_accuse() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")

func _set_busy(busy: bool) -> void:
	_busy = busy
	share_button.disabled = busy
	next_round_button.disabled = busy
	close_case_button.disabled = busy
	accuse_button.disabled = busy
