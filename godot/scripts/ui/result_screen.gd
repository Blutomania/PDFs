## ResultScreen — shows whether the accusation was correct and the full solution.
## Also hosts the viability rating (1–10) so the player/creator can rate
## the mystery quality before moving on.
##
## SESSION ANNOTATION — Phase 2:
## The rating save (ApiClient.rate_mystery) fires-and-forgets — failure is
## logged as a warning but does not block the player.
## Phase 3: In multiplayer, the result is broadcast to all players by the server.
## This scene should display who won (first correct accusation), not just
## whether the local player was right.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var verdict_label: Label = $ScrollContainer/MainVBox/VerdictLabel
@onready var solution_label: RichTextLabel = $ScrollContainer/MainVBox/SolutionLabel
@onready var stats_label: RichTextLabel = $ScrollContainer/MainVBox/StatsLabel
@onready var rating_row: HBoxContainer = $ScrollContainer/MainVBox/RatingRow
@onready var play_again_button: Button = $ScrollContainer/MainVBox/Buttons/PlayAgainButton
@onready var review_button: Button = $ScrollContainer/MainVBox/Buttons/ReviewButton
@onready var disclosure_title: Label = $ScrollContainer/MainVBox/DisclosureTitle
@onready var disclosure_note: Label = $ScrollContainer/MainVBox/DisclosureNote
@onready var disclosure_container: VBoxContainer = $ScrollContainer/MainVBox/DisclosureContainer

var _rating_given: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	play_again_button.pressed.connect(_on_play_again)
	review_button.pressed.connect(_go_case)
	_populate()
	_build_rating_buttons()
	_load_disclosure()

# ---------------------------------------------------------------------------
# Populate
# ---------------------------------------------------------------------------
func _populate() -> void:
	var result: Dictionary = GameState.accusation_result
	var correct: bool = result.get("correct", false)
	var suspect: String = result.get("suspect_guessed", "?")
	var culprit: String = result.get("culprit", "?")
	var plot: Dictionary = result.get("plot_reveal", {})

	if correct:
		verdict_label.text = "Correct! %s is the culprit." % culprit
		verdict_label.add_theme_color_override("font_color", Palette.POSITIVE)
	else:
		verdict_label.text = "Wrong. You accused %s — the real culprit was %s." % [suspect, culprit]
		verdict_label.add_theme_color_override("font_color", Palette.NEGATIVE)

	# Full solution breakdown. plot_reveal.key_evidence entries are already
	# {id, name, description} -- resolved server-side (_format_plot_reveal(),
	# or locally on the single-player path via _local_plot_reveal()) -- so
	# this screen shows clue NAMES and never a bare id like "E2" (owner,
	# playtest SolvedSept7).
	var key_ev: Array = plot.get("key_evidence", [])
	var clue_names: Array = []
	for entry in key_ev:
		clue_names.append(str(entry.get("name", "?")))

	# GDScript has no implicit adjacent-string concatenation -- the `+` are
	# required, and without them this file fails to PARSE, so the whole script
	# never loads and every line in it silently does nothing.
	var sol_text: String = (
		"[b]The Culprit:[/b] %s\n"
		+ "[b]The Crime:[/b] %s\n"
		+ "[b]His/Her Motive:[/b] %s\n"
		+ "[b]Key Clues:[/b] %s"
	) % [
		plot.get("culprit", culprit),
		plot.get("method", "?"),
		plot.get("motive", "?"),
		", ".join(clue_names) if not clue_names.is_empty() else "?",
	]
	solution_label.text = sol_text

	_populate_stats(result.get("gameplay_stats", {}))

## Rounds played and elapsed time, in place of "How to deduce" (owner, playtest
## SolvedSept7: "remove the how to deduce section, INSTEAD let's surface
## gameplay stats"). Empty on the single-player/legacy path -- no APF session
## ran, so there is nothing true to report, and the block stays hidden rather
## than showing a guessed zero.
func _populate_stats(stats: Dictionary) -> void:
	if stats.is_empty():
		stats_label.visible = false
		return
	stats_label.visible = true
	var rounds_played: int = stats.get("rounds_played", 0)
	var rounds_total: int = stats.get("rounds_total", 0)
	var elapsed: int = stats.get("elapsed_seconds", 0)
	stats_label.text = (
		"[b]Rounds played:[/b] %d of %d\n"
		+ "[b]Time played:[/b] %s"
	) % [rounds_played, rounds_total, _format_duration(elapsed)]

## "127 seconds" means nothing at a table -- minutes and seconds, the way a
## player would actually say it back.
func _format_duration(seconds: int) -> String:
	var m: int = seconds / 60
	var s: int = seconds % 60
	if m == 0:
		return "%d sec" % s
	return "%d min %d sec" % [m, s]

# ---------------------------------------------------------------------------
# Full disclosure (docs/PLAYTEST_FLOW.md, "Full disclosure closes the game")
#
# NOT A TIE-BREAKER AND NOT A RESCUE. Owner, Session 41: "so much of the fun of
# this game is the Choose aspect of it… seeing the full disclosure is necessary
# to reward that choice." You picked the setting and paid for the generation, so
# you are owed the whole of it, not the fraction that happened to be shared.
#
# And it does a second job for free. Every finding somebody sat on appears with
# their name against it, which is what makes withholding a real decision rather
# than a costless one. "She was holding the ledger page the whole time" is the
# sentence the mechanic exists to produce, and nothing before the end can
# produce it.
#
# Nothing here costs an API call: it is the session's own log, reformatted.
# ---------------------------------------------------------------------------
func _load_disclosure() -> void:
	if GameState.game_id.is_empty():
		return
	ApiClient.apf_disclosure(GameState.game_id, _on_disclosure)

func _on_disclosure(error: String, data: Dictionary) -> void:
	## A single-player or pre-APF game has no assignment, so the server answers 409.
	## That is not an error worth showing anybody — this section simply is not
	## part of that game.
	if error or not bool(data.get("disclosed", false)):
		return

	var withheld: Array = data.get("withheld", [])
	disclosure_title.visible = true
	disclosure_note.visible = true

	if withheld.is_empty():
		disclosure_note.text = "Everything found was shared. Nobody held anything back."
		return

	disclosure_note.text = (
		"%d findings never reached the table until the case closed."
		% withheld.size()
	)

	for entry in withheld:
		var item: Dictionary = entry
		var box := VBoxContainer.new()

		var who := Label.new()
		who.text = "%s held this back" % str(item.get("shared_by", "?"))
		who.add_theme_color_override("font_color", Palette.CAUTION)
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

		disclosure_container.add_child(box)
		disclosure_container.add_child(HSeparator.new())

# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------
func _build_rating_buttons() -> void:
	for i in range(1, 11):
		var btn := Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(36, 36)
		btn.pressed.connect(_on_rate.bind(i))
		rating_row.add_child(btn)

func _on_rate(rating: int) -> void:
	if _rating_given:
		return
	_rating_given = true
	var slug: String = GameState.current_mystery.get("_slug", "")
	if not slug.is_empty():
		ApiClient.rate_mystery(slug, rating, func(err, _d):
			if err:
				push_warning("Rating save failed: " + err)
		)
	# Dim all buttons to show rating was recorded. The chosen one keeps full
	# strength and takes a brass label; the rest recede. modulate is right here
	# and wrong for a Label: these are whole controls -- box, border and text --
	# that should step back together.
	for child: Node in rating_row.get_children():
		if child is Button:
			var btn: Button = child
			var chosen: bool = btn.text.to_int() == rating
			btn.modulate = Color.WHITE if chosen else Color(0.55, 0.55, 0.55)
			if chosen:
				btn.add_theme_color_override("font_color", Palette.BRASS)
			else:
				btn.remove_theme_color_override("font_color")

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _on_play_again() -> void:
	GameState.reset()
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
