## MainMenu — entry point scene script.
## Buttons: New Game, Browse Saved Mysteries, Settings, Quit.
##
## SESSION ANNOTATION — Phase 2:
## The "Browse Saved" button calls ApiClient.list_mysteries() and shows a
## popup list. The actual browse UI can be a simple ItemList for now.
## Phase 3: Add "Multiplayer" button that opens LobbyCreate/LobbyJoin.

extends Control

# ---------------------------------------------------------------------------
# Node references (set these in the .tscn file)
# ---------------------------------------------------------------------------
@onready var new_game_button: Button = $VBox/NewGameButton
@onready var multiplayer_button: Button = $VBox/MultiplayerButton
@onready var browse_button: Button = $VBox/BrowseSavedButton
@onready var quit_button: Button = $VBox/QuitButton
@onready var status_label: Label = $StatusLabel
@onready var browse_popup: Window = $BrowsePopup          ## Created in scene
@onready var browse_rows: VBoxContainer = $BrowsePopup/VBox/ListPanel/ScrollContainer/RowsContainer
@onready var browse_close_button: Button = $BrowsePopup/VBox/CloseButton

var _saved_mysteries: Array = []

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	GameState.reset()
	new_game_button.pressed.connect(_on_new_game)
	multiplayer_button.pressed.connect(_on_multiplayer)
	browse_button.pressed.connect(_on_browse)
	quit_button.pressed.connect(get_tree().quit)

	# The browse popup's own signals. None of these were connected before, so the
	# popup opened, listed the saved mysteries, and then did nothing at all:
	# clicking a row was inert and the window could not be dismissed (a Godot
	# Window does not hide itself on close_requested — the handler has to).
	browse_close_button.pressed.connect(browse_popup.hide)
	browse_popup.close_requested.connect(browse_popup.hide)

	# Verify backend is reachable on startup
	status_label.text = "Checking backend…"
	ApiClient.health_check(_on_health_check)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_health_check(error: String, _data: Dictionary) -> void:
	if error:
		status_label.text = "Backend unreachable — start server at localhost:8000"
		status_label.add_theme_color_override("font_color", Palette.NEGATIVE)
	else:
		status_label.text = "Backend connected."
		status_label.add_theme_color_override("font_color", Palette.POSITIVE)

func _on_new_game() -> void:
	GameState.is_multiplayer = false
	get_tree().change_scene_to_file("res://scenes/ui/MysteryGeneration.tscn")

func _on_multiplayer() -> void:
	GameState.is_multiplayer = true
	get_tree().change_scene_to_file("res://scenes/ui/MysteryGeneration.tscn")

func _on_browse() -> void:
	browse_button.disabled = true
	status_label.text = "Loading saved mysteries…"
	ApiClient.list_mysteries(_on_mysteries_listed)

func _on_mysteries_listed(error: String, data) -> void:
	browse_button.disabled = false
	if error:
		status_label.text = "Error: " + error
		return
	status_label.text = "Backend connected."
	_saved_mysteries = data if data is Array else []
	for row in browse_rows.get_children():
		row.queue_free()
	for i in _saved_mysteries.size():
		browse_rows.add_child(_build_browse_row(_saved_mysteries[i], i))
	browse_popup.popup_centered(Vector2i(600, 400))

## One row: title+difficulty on the left, a fixed-width right-aligned star
## column on the right, so ratings line up across rows the way BrowseSept8's
## feedback asked for -- ItemList's single string per item can't do that.
func _build_browse_row(m: Dictionary, index: int) -> Button:
	var row := Button.new()
	row.theme_type_variation = &"BrowseRowButton"
	row.flat = true
	row.alignment = HORIZONTAL_ALIGNMENT_LEFT
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.pressed.connect(_on_browse_item_selected.bind(index))

	var hbox := HBoxContainer.new()
	hbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(hbox)

	var title_label := Label.new()
	title_label.text = "%s [%s]" % [m.get("title", "?"), m.get("difficulty", "?")]
	title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_label.clip_text = true
	title_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hbox.add_child(title_label)

	var stars_label := Label.new()
	var rating: int = m.get("viability_rating", 0)
	stars_label.text = "★%d" % rating if rating else ""
	stars_label.custom_minimum_size = Vector2(56, 0)
	stars_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	stars_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hbox.add_child(stars_label)

	return row

func _on_browse_item_selected(index: int) -> void:
	if index < 0 or index >= _saved_mysteries.size():
		return
	var slug: String = _saved_mysteries[index].get("slug", "")
	browse_popup.hide()
	status_label.text = "Loading mystery…"
	ApiClient.get_mystery(slug, _on_mystery_loaded)

func _on_mystery_loaded(error: String, data: Dictionary) -> void:
	if error:
		status_label.text = "Error: " + error
		return
	GameState.current_mystery = data
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
