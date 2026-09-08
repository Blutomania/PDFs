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
## A square image slot with no image in it yet (owner, playtest FindingsSept7:
## "we need more images in this game... images will come later when we use
## GenAI"). "FPO" -- production shorthand for "for position only" -- says the
## empty slot is deliberate. Deliberately NOT the PLAYTEST_FLOW.md video-slot
## approach (fill the gap with the best real content available, a map instead
## of an announcement) -- there IS no real-content stand-in for "what this
## person looks like" the way a map stands in for a scene, so naming the gap
## honestly is the only option that exists here, not a lesser copy of that one.
func _fpo_square(square_size: float) -> Control:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(square_size, square_size)

	var box := StyleBoxFlat.new()
	box.bg_color = Palette.SURFACE_DEEP
	box.border_color = Palette.LINE_SOFT
	box.set_border_width_all(Palette.BORDER_WIDTH)
	box.set_corner_radius_all(Palette.RADIUS_SMALL)
	panel.add_theme_stylebox_override("panel", box)

	var lbl := Label.new()
	lbl.text = "FPO"
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	lbl.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
	lbl.add_theme_color_override("font_color", Palette.INK_FAINT)
	panel.add_child(lbl)

	return panel

func _render_board() -> void:
	for child in board_container.get_children():
		child.queue_free()

	for entry in GameState.apf_board():
		var row: Dictionary = entry
		var wrapper := HBoxContainer.new()
		wrapper.add_theme_constant_override("separation", Palette.SPACE_SMALL)
		wrapper.add_child(_fpo_square(40.0))

		var box := VBoxContainer.new()
		box.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var name_label := Label.new()
		name_label.text = str(row.get("name", "?"))
		name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

		var cleared: bool = bool(row.get("cleared", false))
		if cleared:
			## Struck through and dimmed: the face is still on the board, because
			## knowing who is out is half the deduction. Dimming the WRAPPER, not
			## just the name, so the FPO square dims along with it.
			name_label.add_theme_color_override("font_color", Palette.INK_FAINT)
			wrapper.modulate = Color(1.0, 1.0, 1.0, 0.55)
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
			## NOT a verdict and not a nudge (owner, playtest FindingsSept7): this
			## reports only that no shared finding has cleared them yet -- the same
			## fact "cleared by X in round Y" reports in the other direction. The
			## MECHANIC is unchanged (item 27's board still greys a face only on a
			## shared exoneration); only the wording and visual weight of the
			## not-yet-cleared state changed, from a phrase that reads as a verdict
			## in an attention-grabbing accent (BRASS) to a neutral status in a
			## quiet one.
			by_label.text = "not yet cleared"
			by_label.add_theme_color_override("font_color", Palette.INK_FAINT)
		box.add_child(by_label)

		wrapper.add_child(box)
		board_container.add_child(wrapper)
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

## The point at which a body cuts to its excerpt, when no sentence ending is
## found short enough to use as one. Chosen to be a couple of lines on this
## column's width, not a hard rule.
const _EXCERPT_FALLBACK_CHARS: int = 140

## Titles that end in a period without ending a sentence. Checked against the
## word immediately before a "." candidate -- found by running the excerpt
## against the accepted mystery's own real evidence text before trusting it:
## E2 opens "Written notes made by Dr. Voss within thirty minutes..." and a
## naive splitter cuts it to "Written notes made by Dr." -- a real defect in
## real content, not a hypothetical one, caught by testing against data
## instead of only against invented sentences.
const _TITLE_ABBREVIATIONS: Array[String] = [
	"mr", "mrs", "ms", "dr", "st", "capt", "rev", "prof", "jr", "sr", "mme", "mlle", "hon",
]

## A finding's excerpt: its OWN first sentence, verbatim -- never a generated
## summary (owner, playtest FindingsSept7; see the reply in this same turn on
## why that stays a deliberate, costed decision rather than a default). Falls
## back to a hard cut at the nearest word boundary when there is no sentence
## ending within a reasonable span, so one run-on paragraph cannot defeat the
## whole point of excerpting.
func _first_sentence(body: String) -> String:
	var search_from: int = 0
	while true:
		var idx: int = -1
		for mark in [". ", "! ", "? "]:
			var found: int = body.find(mark, search_from)
			if found != -1 and (idx == -1 or found < idx):
				idx = found
		if idx == -1:
			break
		if body[idx] == "." and _ends_in_title_abbreviation(body, idx):
			search_from = idx + 1
			continue
		return body.substr(0, idx + 1)

	if body.length() > 0 and body[body.length() - 1] in ".!?":
		return body
	if body.length() <= _EXCERPT_FALLBACK_CHARS:
		return body
	var cut: int = body.rfind(" ", _EXCERPT_FALLBACK_CHARS)
	if cut <= 0:
		cut = _EXCERPT_FALLBACK_CHARS
	return body.substr(0, cut) + "…"

## Whether the "." at `period_idx` closes a title abbreviation ("Dr.") rather
## than a sentence -- the word immediately before it, case-insensitively.
func _ends_in_title_abbreviation(body: String, period_idx: int) -> bool:
	var start: int = period_idx
	while start > 0 and body[start - 1] != " ":
		start -= 1
	var word: String = body.substr(start, period_idx - start).to_lower()
	return word in _TITLE_ABBREVIATIONS

## One finding's body, as a scannable bullet rather than a paragraph (owner,
## playtest FindingsSept7: "the findings are summarized so you can ingest them
## and begin to deduce from there"). "Full Finding", not "Full Testimony" --
## a finding can be a witness statement, a clue or a lead, and only the first
## of those is testimony. Skipped entirely when the excerpt already IS the
## whole body: a link with nothing left to reveal is a dead link, not a
## feature. Used by both this column and the shared pool below, so a finding
## reads the same way wherever it is shown.
func _body_block(body: String) -> Control:
	var wrap := VBoxContainer.new()

	var excerpt: String = _first_sentence(body)
	var bullet := Label.new()
	bullet.text = "•  " + excerpt
	bullet.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	bullet.add_theme_color_override("font_color", Palette.INK_MUTED)
	wrap.add_child(bullet)

	if excerpt.strip_edges() == body.strip_edges():
		return wrap

	var full := Label.new()
	full.text = body
	full.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	full.add_theme_color_override("font_color", Palette.INK_MUTED)
	full.visible = false
	wrap.add_child(full)

	var link := LinkButton.new()
	link.text = "Full Finding"
	link.add_theme_font_size_override("font_size", Palette.TYPE_LABEL)
	link.pressed.connect(func() -> void:
		full.visible = not full.visible
		bullet.visible = not full.visible
		link.text = "Show less" if full.visible else "Full Finding"
	)
	wrap.add_child(link)

	return wrap

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

		box.add_child(_body_block(str(finding.get("body", ""))))

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

		box.add_child(_body_block(str(item.get("body", ""))))

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
