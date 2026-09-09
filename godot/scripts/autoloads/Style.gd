## Style — builds the one Theme every CYM screen wears, and puts it on.
##
## WHY THIS IS A SCRIPT AND NOT A .tres. A Theme resource would be editable in
## the Godot theme editor, which is a real advantage, and it loses on the two
## things that matter more here:
##
##   1. It would be a fourth copy of the palette. Palette.gd is generated from
##      palette.py and checked for drift; a .tres full of Color(...) literals
##      is not, and the whole point of this session's work is that hand-copied
##      colours drift. Built in code, every value below traces to one file.
##   2. A .tres is authored in the same text format as a .tscn, and Session 36
##      lost five panels of Interrogation.tscn to a comment character that
##      format does not accept. Hand-writing several hundred lines of it blind,
##      with no engine here to load it, is the same bet with worse odds.
##
## HOW IT APPLIES WITHOUT TOUCHING A SINGLE SCENE. `get_tree().root` is a
## Window, Window has a `theme`, and every Control inherits its nearest
## ancestor's theme. So one assignment in _ready() restyles all nine screens,
## and no .tscn node tree is edited to get it. That matters beyond tidiness:
## editing scene files is precisely where the last session's defects lived.
##
## The GROUND is not painted here. It is the viewport clear colour, set in
## project.godot as rendering/environment/defaults/default_clear_color, which
## is the correct home for it — it paints before any Control exists, so there
## is no frame of engine grey on startup, and it is exactly the "ground colour
## alone until a mystery is named" state that CLAUDE.md item 17 specifies.

extends Node

## The built theme, kept so a script that creates a Control or Window at
## runtime can hand it over explicitly. Godot propagates the root theme down
## the tree on its own, so nothing in the eight scenes needs this today -- it
## is here for the case where something is built outside the tree and styled
## before being added to it.
var theme: Theme


func _ready() -> void:
	theme = build_theme()
	get_tree().root.theme = theme


# ---------------------------------------------------------------------------
# Theme construction
# ---------------------------------------------------------------------------

## Built as a pure function so it can be called from a test scene or the editor
## without depending on the autoload having run.
func build_theme() -> Theme:
	var t: Theme = Theme.new()
	t.default_font_size = Palette.TYPE_BODY

	_style_fonts(t)
	_style_labels(t)
	_style_buttons(t)
	_style_inputs(t)
	_style_lists(t)
	_style_containers(t)
	_style_progress(t)
	_style_windows(t)
	_declare_variations(t)
	return t


## A filled panel: the "paper on the desk" tier. Everything that holds text
## sits on one of these rather than directly on the ground.
func _panel(fill: Color, radius: int, border: Color = Palette.LINE_SOFT) -> StyleBoxFlat:
	var box: StyleBoxFlat = StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = border
	box.set_border_width_all(Palette.BORDER_WIDTH)
	box.set_corner_radius_all(radius)
	box.set_content_margin_all(float(Palette.SPACE_BASE))
	return box


## A control-sized box: same idea, tighter margins, and its border is held to
## the measured LINE rather than decorative LINE_SOFT, because on a control the
## outline is the affordance.
func _control_box(fill: Color, border: Color) -> StyleBoxFlat:
	var box: StyleBoxFlat = StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = border
	box.set_border_width_all(Palette.BORDER_WIDTH)
	box.set_corner_radius_all(Palette.RADIUS_BASE)
	box.content_margin_left = float(Palette.SPACE_WIDE)
	box.content_margin_right = float(Palette.SPACE_WIDE)
	box.content_margin_top = float(Palette.SPACE_SMALL)
	box.content_margin_bottom = float(Palette.SPACE_SMALL)
	return box


## The focus ring. Drawn as a border with no fill so it sits ON TOP of whatever
## state box is underneath instead of replacing it — a focused-and-hovered
## button should still look hovered. Brass because focus is the one thing on
## screen that should be impossible to lose track of.
func _focus_ring() -> StyleBoxFlat:
	var box: StyleBoxFlat = StyleBoxFlat.new()
	box.draw_center = false
	box.border_color = Palette.BRASS_BRIGHT
	box.set_border_width_all(2)
	box.set_corner_radius_all(Palette.RADIUS_BASE)
	return box


## Nunito Sans — OFL 1.1, three static instances (400/600/700).
##
## STATIC INSTANCES, NOT THE VARIABLE FONT, although upstream ships variable
## (four axes: YTLC, opsz, wdth, wght). Godot supports variable fonts, but each
## weight then needs its own resource carrying a `variation_opentype` dictionary,
## so "one file" becomes three resources plus three axis maps to get right —
## more moving parts than three files, for identical output.
##
## ONE FAMILY ACROSS THE WHOLE HIERARCHY, so there is no fallback chain to
## maintain. A pairing needs the body face listed as the display face's
## fallback, because a display face usually has thinner coverage and a missing
## glyph renders as a box; with a single family covering all three weights, that
## whole class of bug does not exist. It matters here: one title on disk is
## "Schatten am Checkpoint", and these instances carry the Latin-1 accents.
##
## Loaded defensively. A .ttf that has not been imported yet resolves to null,
## and assigning null as default_font would strip every label in the product of
## its font with no error — the same silent-no-op shape as a wrong theme item
## name. Better to keep the engine default and say so.
func _style_fonts(t: Theme) -> void:
	var regular: Font = _font("NunitoSans-Regular.ttf")
	var semibold: Font = _font("NunitoSans-SemiBold.ttf")
	var bold: Font = _font("NunitoSans-Bold.ttf")
	if regular == null:
		return

	t.default_font = regular
	for type_name: String in ["Label", "Button", "CheckBox", "LineEdit", "TextEdit",
			"OptionButton", "PopupMenu", "ItemList", "ProgressBar", "TooltipLabel"]:
		t.set_font("font", type_name, regular)
	t.set_font("normal_font", "RichTextLabel", regular)
	t.set_font("bold_font", "RichTextLabel", bold if bold else regular)

	## Weight carries the hierarchy now that colour and size already do.
	## TitleLabel takes Bold NunitoSans; section headings and the one primary
	## action take SemiBold; everything else stays Regular, which is most of
	## the screen. The Window's OS-level title bar text stays NunitoSans Bold
	## too -- a decorative display face in tiny native titlebar chrome is a
	## legibility risk for no visible payoff, and it is not in-game content.
	if bold:
		t.set_font("font", "TitleLabel", bold)
		t.set_font("title_font", "Window", bold)
	if semibold:
		t.set_font("font", "HeadingLabel", semibold)
		t.set_font("font", "PrimaryButton", semibold)
		t.set_font("font", "DangerButton", semibold)
	## PlayerNameLabel is sized to match DisplayLabel (owner, playtest
	## WaitingSept7: player names as big as the room code) but stays
	## NunitoSans, not Cinzel Decorative -- these render free-typed player
	## names, and Cinzel Decorative has no true lowercase glyphs (playtest
	## SolvedSept7's font follow-up), which would turn an ordinary name into
	## small caps nobody asked for.
	##
	## CodeLabel is the SAME correction applied to the room code itself (owner,
	## playtest WaitingSept7, immediately after seeing a render: the code was
	## "hard to read in that font"). An alphanumeric code is exactly the string
	## Cinzel Decorative's small-caps rendering hurts most -- it was never a
	## brand moment the way the main-menu wordmark is, it is a string someone
	## has to type correctly on a phone across the room. DisplayLabel now means
	## ONLY the main-menu wordmark again.
	if bold:
		t.set_font("font", "PlayerNameLabel", bold)
		t.set_font("font", "CodeLabel", bold)

	## DisplayLabel, MysteryTitleLabel and VerdictLabel are BRAND and
	## DRAMATIC-MOMENT text -- the game's own name on MainMenu/Lobby, a
	## generated mystery's own title on CaseDisplay, and the win/lose banner
	## on ResultScreen -- not functional screen headers. Cinzel Decorative
	## there; NunitoSans everywhere else. Deliberately NOT applied to
	## TitleLabel, which is used broadly for workaday status headers
	## ("Round 2 of 4", "Set Your Mystery") that are read fast during play --
	## a heavy decorative serif risks looking overwrought there, and this was
	## a scope call flagged to the owner rather than assumed (font upload,
	## playtest SolvedSept7).
	##
	## All three share Bold. DisplayLabel wore Black through playtest
	## SolvedSept7/WaitingSept7; owner called it too heavy on startSept8 and
	## dropped it a tier, so there is no longer a weight distinction between
	## the brand name and the other two dramatic-moment labels.
	var display_bold: Font = _font("CinzelDecorative-Bold.ttf")
	if display_bold:
		t.set_font("font", "DisplayLabel", display_bold)
		t.set_font("font", "MysteryTitleLabel", display_bold)
		t.set_font("font", "VerdictLabel", display_bold)


func _font(file_name: String) -> Font:
	var path: String = "res://assets/fonts/" + file_name
	if not ResourceLoader.exists(path):
		push_warning("Style: %s is missing — falling back to Godot's default face." % path)
		return null
	return load(path) as Font


func _style_labels(t: Theme) -> void:
	t.set_color("font_color", "Label", Palette.INK)
	t.set_font_size("font_size", "Label", Palette.TYPE_BODY)
	## Prose is read in paragraphs here — case briefs, interrogation replies.
	## Godot's default line spacing is tight for that.
	t.set_constant("line_spacing", "Label", 4)

	t.set_color("default_color", "RichTextLabel", Palette.INK)
	t.set_font_size("normal_font_size", "RichTextLabel", Palette.TYPE_BODY)
	t.set_font_size("bold_font_size", "RichTextLabel", Palette.TYPE_BODY)
	t.set_color("selection_color", "RichTextLabel", Palette.STEEL)
	t.set_constant("line_separation", "RichTextLabel", 4)
	## RichTextLabel carries the longest text in the product, so it gets the
	## well treatment: sunk, so the eye has an edge to hold on to.
	t.set_stylebox("normal", "RichTextLabel", _panel(Palette.SURFACE_DEEP, Palette.RADIUS_CARD))

	var rule: StyleBoxLine = StyleBoxLine.new()
	rule.color = Palette.LINE_SOFT
	rule.thickness = Palette.BORDER_WIDTH
	t.set_stylebox("separator", "HSeparator", rule)
	t.set_constant("separation", "HSeparator", Palette.SPACE_SECTION)

	var v_rule: StyleBoxLine = StyleBoxLine.new()
	v_rule.color = Palette.LINE_SOFT
	v_rule.thickness = Palette.BORDER_WIDTH
	v_rule.vertical = true
	t.set_stylebox("separator", "VSeparator", v_rule)
	t.set_constant("separation", "VSeparator", Palette.SPACE_SECTION)


func _style_buttons(t: Theme) -> void:
	## The default button is the QUIET one — outlined, sitting on the surface
	## tier. Screens here carry five or six buttons at once (investigate,
	## interrogate, share, accuse, back), and if the default were the loud
	## brass one every screen would be shouting and nothing would read as the
	## next step. Brass is opted into, via the PrimaryButton variation.
	t.set_stylebox("normal", "Button", _control_box(Palette.SURFACE, Palette.LINE))
	t.set_stylebox("hover", "Button", _control_box(Palette.SURFACE_RAISED, Palette.LINE))
	t.set_stylebox("pressed", "Button", _control_box(Palette.SURFACE_DEEP, Palette.LINE))
	t.set_stylebox("focus", "Button", _focus_ring())

	var off: StyleBoxFlat = _control_box(Palette.SURFACE_DEEP, Palette.LINE_SOFT)
	t.set_stylebox("disabled", "Button", off)

	t.set_color("font_color", "Button", Palette.INK)
	t.set_color("font_hover_color", "Button", Palette.INK)
	t.set_color("font_pressed_color", "Button", Palette.BRASS)
	t.set_color("font_focus_color", "Button", Palette.INK)
	## Disabled is INK_FAINT rather than a transparency, because CYM disables
	## buttons to mean "already used this round" — a state a player has to be
	## able to READ, not just notice is greyed. It clears 4.5:1 on the deep
	## tier; see palette.py's contract.
	t.set_color("font_disabled_color", "Button", Palette.INK_FAINT)
	t.set_font_size("font_size", "Button", Palette.TYPE_BODY)
	t.set_constant("h_separation", "Button", Palette.SPACE_SMALL)

	t.set_color("font_color", "CheckBox", Palette.INK)
	t.set_color("font_hover_color", "CheckBox", Palette.INK)
	t.set_color("font_pressed_color", "CheckBox", Palette.BRASS)
	t.set_color("font_disabled_color", "CheckBox", Palette.INK_FAINT)
	t.set_font_size("font_size", "CheckBox", Palette.TYPE_BODY)
	t.set_stylebox("focus", "CheckBox", _focus_ring())
	t.set_constant("h_separation", "CheckBox", Palette.SPACE_BASE)


func _style_inputs(t: Theme) -> void:
	t.set_stylebox("normal", "LineEdit", _control_box(Palette.SURFACE_DEEP, Palette.LINE))
	var focused: StyleBoxFlat = _control_box(Palette.SURFACE_DEEP, Palette.BRASS)
	focused.set_border_width_all(2)
	t.set_stylebox("focus", "LineEdit", focused)
	t.set_stylebox("read_only", "LineEdit", _control_box(Palette.SURFACE, Palette.LINE_SOFT))
	t.set_color("font_color", "LineEdit", Palette.INK)
	t.set_color("font_placeholder_color", "LineEdit", Palette.INK_FAINT)
	t.set_color("font_uneditable_color", "LineEdit", Palette.INK_MUTED)
	t.set_color("caret_color", "LineEdit", Palette.BRASS)
	t.set_color("selection_color", "LineEdit", Palette.STEEL)
	t.set_font_size("font_size", "LineEdit", Palette.TYPE_BODY)

	t.set_stylebox("normal", "TextEdit", _control_box(Palette.SURFACE_DEEP, Palette.LINE))
	t.set_stylebox("focus", "TextEdit", focused)
	t.set_color("font_color", "TextEdit", Palette.INK)
	t.set_color("font_placeholder_color", "TextEdit", Palette.INK_FAINT)
	t.set_color("caret_color", "TextEdit", Palette.BRASS)
	t.set_color("selection_color", "TextEdit", Palette.STEEL)
	t.set_font_size("font_size", "TextEdit", Palette.TYPE_BODY)

	## OptionButton is the accusation dropdown — the single most consequential
	## control in the game, so it is styled as an input rather than inheriting
	## the quiet button.
	t.set_stylebox("normal", "OptionButton", _control_box(Palette.SURFACE_DEEP, Palette.LINE))
	t.set_stylebox("hover", "OptionButton", _control_box(Palette.SURFACE, Palette.LINE))
	t.set_stylebox("pressed", "OptionButton", _control_box(Palette.SURFACE_DEEP, Palette.BRASS))
	t.set_stylebox("focus", "OptionButton", _focus_ring())
	t.set_stylebox("disabled", "OptionButton", _control_box(Palette.SURFACE_DEEP, Palette.LINE_SOFT))
	t.set_color("font_color", "OptionButton", Palette.INK)
	t.set_color("font_hover_color", "OptionButton", Palette.INK)
	t.set_color("font_pressed_color", "OptionButton", Palette.BRASS)
	t.set_color("font_disabled_color", "OptionButton", Palette.INK_FAINT)
	t.set_font_size("font_size", "OptionButton", Palette.TYPE_BODY)

	## The dropdown that OptionButton opens is a PopupMenu and is a separate
	## theme type. Leaving it unstyled is the classic half-themed look: a dark
	## control that opens a light grey list.
	t.set_stylebox("panel", "PopupMenu", _panel(Palette.SURFACE_DEEP, Palette.RADIUS_BASE, Palette.LINE))
	t.set_stylebox("hover", "PopupMenu", _panel(Palette.SURFACE_RAISED, Palette.RADIUS_SMALL, Palette.SURFACE_RAISED))
	t.set_color("font_color", "PopupMenu", Palette.INK)
	t.set_color("font_hover_color", "PopupMenu", Palette.INK)
	t.set_color("font_disabled_color", "PopupMenu", Palette.INK_FAINT)
	t.set_color("font_separator_color", "PopupMenu", Palette.INK_FAINT)
	t.set_font_size("font_size", "PopupMenu", Palette.TYPE_BODY)
	t.set_constant("v_separation", "PopupMenu", Palette.SPACE_TIGHT)


func _style_lists(t: Theme) -> void:
	t.set_stylebox("panel", "ItemList", _panel(Palette.SURFACE_DEEP, Palette.RADIUS_CARD))
	t.set_stylebox("focus", "ItemList", _focus_ring())
	t.set_stylebox("hovered", "ItemList", _panel(Palette.SURFACE, Palette.RADIUS_SMALL, Palette.SURFACE))
	var chosen: StyleBoxFlat = _panel(Palette.SURFACE_RAISED, Palette.RADIUS_SMALL, Palette.BRASS)
	t.set_stylebox("selected", "ItemList", chosen)
	t.set_stylebox("selected_focus", "ItemList", chosen)
	t.set_color("font_color", "ItemList", Palette.INK)
	t.set_color("font_selected_color", "ItemList", Palette.INK)
	t.set_color("guide_color", "ItemList", Palette.LINE_SOFT)
	t.set_font_size("font_size", "ItemList", Palette.TYPE_BODY)
	t.set_constant("v_separation", "ItemList", Palette.SPACE_TIGHT)


func _style_containers(t: Theme) -> void:
	t.set_stylebox("panel", "Panel", _panel(Palette.SURFACE, Palette.RADIUS_CARD))
	t.set_stylebox("panel", "PanelContainer", _panel(Palette.SURFACE, Palette.RADIUS_CARD))

	t.set_constant("separation", "VBoxContainer", Palette.SPACE_BASE)
	t.set_constant("separation", "HBoxContainer", Palette.SPACE_BASE)
	t.set_constant("margin_left", "MarginContainer", Palette.SPACE_SCREEN)
	t.set_constant("margin_right", "MarginContainer", Palette.SPACE_SCREEN)
	t.set_constant("margin_top", "MarginContainer", Palette.SPACE_SECTION)
	t.set_constant("margin_bottom", "MarginContainer", Palette.SPACE_SECTION)

	## Scrollbars. Godot's defaults are light grey and, on this ground, are the
	## brightest thing on a case screen — brighter than the case text.
	for bar: String in ["VScrollBar", "HScrollBar"]:
		var trough: StyleBoxFlat = StyleBoxFlat.new()
		trough.bg_color = Palette.SURFACE_DEEP
		trough.set_corner_radius_all(Palette.RADIUS_SMALL)
		t.set_stylebox("scroll", bar, trough)

		var grabber: StyleBoxFlat = StyleBoxFlat.new()
		grabber.bg_color = Palette.LINE_SOFT
		grabber.set_corner_radius_all(Palette.RADIUS_SMALL)
		t.set_stylebox("grabber", bar, grabber)

		var grabber_lit: StyleBoxFlat = StyleBoxFlat.new()
		grabber_lit.bg_color = Palette.LINE
		grabber_lit.set_corner_radius_all(Palette.RADIUS_SMALL)
		t.set_stylebox("grabber_highlight", bar, grabber_lit)
		t.set_stylebox("grabber_pressed", bar, grabber_lit)

	t.set_stylebox("panel", "TooltipPanel", _panel(Palette.SURFACE_DEEP, Palette.RADIUS_BASE, Palette.LINE))
	t.set_color("font_color", "TooltipLabel", Palette.INK)
	t.set_font_size("font_size", "TooltipLabel", Palette.TYPE_LABEL)


func _style_progress(t: Theme) -> void:
	## ProgressBar is the interrogation budget — how many questions are left.
	## Brass, because it is the resource the whole round is spent against.
	var trough: StyleBoxFlat = StyleBoxFlat.new()
	trough.bg_color = Palette.SURFACE_DEEP
	trough.border_color = Palette.LINE_SOFT
	trough.set_border_width_all(Palette.BORDER_WIDTH)
	trough.set_corner_radius_all(Palette.RADIUS_SMALL)
	t.set_stylebox("background", "ProgressBar", trough)

	var fill: StyleBoxFlat = StyleBoxFlat.new()
	fill.bg_color = Palette.BRASS
	fill.set_corner_radius_all(Palette.RADIUS_SMALL)
	t.set_stylebox("fill", "ProgressBar", fill)
	t.set_color("font_color", "ProgressBar", Palette.INK)
	t.set_font_size("font_size", "ProgressBar", Palette.TYPE_LABEL)


func _style_windows(t: Theme) -> void:
	## The browse-saved-mysteries popup, and any dialog. An embedded Window
	## draws its own border and title bar, and unstyled they are engine grey
	## against everything else being slate.
	t.set_stylebox("embedded_border", "Window",
		_panel(Palette.SURFACE, Palette.RADIUS_CARD, Palette.LINE))
	t.set_stylebox("embedded_unfocused_border", "Window",
		_panel(Palette.SURFACE, Palette.RADIUS_CARD, Palette.LINE_SOFT))
	t.set_color("title_color", "Window", Palette.INK)
	t.set_font_size("title_font_size", "Window", Palette.TYPE_HEADING)

	t.set_stylebox("panel", "AcceptDialog", _panel(Palette.SURFACE, Palette.RADIUS_CARD, Palette.LINE))
	t.set_constant("buttons_separation", "AcceptDialog", Palette.SPACE_BASE)


# ---------------------------------------------------------------------------
# Type variations
# ---------------------------------------------------------------------------

## Named roles a scene opts into with `theme_type_variation = "..."`.
##
## This is the one part of the styling that a .tscn has to name, because only
## the scene knows which of its labels is the screen title. The failure mode is
## deliberately mild: a variation that does not exist here falls back to the
## base type, so a typo yields an unstyled label rather than a missing node.
## scripts/check_godot_wiring.py cross-checks the two lists anyway, so a typo
## is caught before the engine is even opened.
##
## Keep this list SHORT. Every variation is a decision someone has to make at
## every label they add, and the ones below cover the roles the nine screens
## actually contain.
func _declare_variations(t: Theme) -> void:
	## The product's own name, on the main menu. Nowhere else.
	t.set_type_variation("DisplayLabel", "Label")
	t.set_color("font_color", "DisplayLabel", Palette.BRASS)
	t.set_font_size("font_size", "DisplayLabel", Palette.TYPE_DISPLAY)

	## A code someone has to read back correctly -- the room code, in the
	## lobby. Same size and colour as DisplayLabel, deliberately not the same
	## variation: see the font note in _style_fonts for why this one stays
	## NunitoSans.
	t.set_type_variation("CodeLabel", "Label")
	t.set_color("font_color", "CodeLabel", Palette.BRASS)
	t.set_font_size("font_size", "CodeLabel", Palette.TYPE_DISPLAY)

	## One per screen, at the top: "The Case", "Interrogation", "Verdict".
	t.set_type_variation("TitleLabel", "Label")
	t.set_color("font_color", "TitleLabel", Palette.INK)
	t.set_font_size("font_size", "TitleLabel", Palette.TYPE_TITLE)

	## The MYSTERY's own name, wherever it is shown. Brass, because item 17
	## makes the title the thing the whole screen is themed around.
	t.set_type_variation("MysteryTitleLabel", "Label")
	t.set_color("font_color", "MysteryTitleLabel", Palette.BRASS)
	t.set_font_size("font_size", "MysteryTitleLabel", Palette.TYPE_TITLE)

	## The outcome banner on ResultScreen -- "Correct! X is the culprit." /
	## "Wrong. You accused X." A DIFFERENT variation from MysteryTitleLabel
	## on purpose (owner, font follow-up on playtest SolvedSept7): a verdict
	## is not a mystery title, even though both are the one big dramatic
	## announcement a screen opens on and both now wear Cinzel Decorative.
	## Base colour is INK and is never actually seen -- result_screen.gd
	## overrides it to POSITIVE or NEGATIVE the instant it sets the text --
	## kept here anyway so the variation is never colourless before that runs.
	t.set_type_variation("VerdictLabel", "Label")
	t.set_color("font_color", "VerdictLabel", Palette.INK)
	## 35, not Palette.TYPE_TITLE (30) -- owner, playtest ResultSept8: just the
	## single word ("Correct"/"Wrong") should read 25% bigger than the 28px it
	## was actually rendering at (a stale per-node .tscn override had drifted
	## from this variation's own declared 30; that override is gone now).
	## ResultScreen splits the banner into two Labels sharing this variation --
	## VerdictWordLabel (the word, inherits this 35) and VerdictRestLabel (the
	## rest of the sentence, overridden to 28 on its own node, "high twenties"
	## per the same note) -- because one Label cannot mix two sizes in its own
	## text. A one-off literal, not TYPE_TITLE, because nothing else uses this
	## variation's size and it should not silently follow that scale's changes.
	t.set_font_size("font_size", "VerdictLabel", 35)

	## A player's name, wherever roster matters more than anywhere else it
	## appears in the product: the lobby (owner, playtest WaitingSept7 -- "who
	## you are playing with is high up in a hierarchy of import" for a social
	## game). Same size as DisplayLabel/the room code, deliberately not the
	## same variation -- see the font note in _style_fonts for why.
	t.set_type_variation("PlayerNameLabel", "Label")
	t.set_color("font_color", "PlayerNameLabel", Palette.INK)
	t.set_font_size("font_size", "PlayerNameLabel", Palette.TYPE_DISPLAY)

	## Section headers within a screen: "Suspects", "Evidence", "Witnesses".
	t.set_type_variation("HeadingLabel", "Label")
	t.set_color("font_color", "HeadingLabel", Palette.INK)
	t.set_font_size("font_size", "HeadingLabel", Palette.TYPE_HEADING)

	## Supporting prose — subtitles, hints, the sentence under a heading.
	t.set_type_variation("MutedLabel", "Label")
	t.set_color("font_color", "MutedLabel", Palette.INK_MUTED)
	t.set_font_size("font_size", "MutedLabel", Palette.TYPE_BODY)

	## Field labels, attribution, timestamps, status lines.
	t.set_type_variation("FaintLabel", "Label")
	t.set_color("font_color", "FaintLabel", Palette.INK_FAINT)
	t.set_font_size("font_size", "FaintLabel", Palette.TYPE_LABEL)

	## Warnings that are not errors: a budget running out, and the
	## "Not moderated for play testing" notice CLAUDE.md item 17 requires to
	## stay VISIBLE — so it gets a colour that cannot be mistaken for chrome.
	t.set_type_variation("CautionLabel", "Label")
	t.set_color("font_color", "CautionLabel", Palette.CAUTION)
	t.set_font_size("font_size", "CautionLabel", Palette.TYPE_LABEL)

	t.set_type_variation("ErrorLabel", "Label")
	t.set_color("font_color", "ErrorLabel", Palette.NEGATIVE)
	t.set_font_size("font_size", "ErrorLabel", Palette.TYPE_BODY)

	t.set_type_variation("PositiveLabel", "Label")
	t.set_color("font_color", "PositiveLabel", Palette.POSITIVE)
	t.set_font_size("font_size", "PositiveLabel", Palette.TYPE_BODY)

	## The one action a screen most wants taken. At most one per screen —
	## two primaries is the same as none.
	t.set_type_variation("PrimaryButton", "Button")
	var brass: StyleBoxFlat = _control_box(Palette.BRASS, Palette.BRASS)
	t.set_stylebox("normal", "PrimaryButton", brass)
	t.set_stylebox("hover", "PrimaryButton", _control_box(Palette.BRASS_BRIGHT, Palette.BRASS_BRIGHT))
	t.set_stylebox("pressed", "PrimaryButton", _control_box(Palette.BRASS_DIM, Palette.BRASS_DIM))
	t.set_stylebox("disabled", "PrimaryButton", _control_box(Palette.SURFACE_DEEP, Palette.LINE_SOFT))
	t.set_stylebox("focus", "PrimaryButton", _focus_ring())
	## The label on brass is the DEEP tier, not ink: dark text on a light fill.
	t.set_color("font_color", "PrimaryButton", Palette.SURFACE_DEEP)
	t.set_color("font_hover_color", "PrimaryButton", Palette.SURFACE_DEEP)
	t.set_color("font_pressed_color", "PrimaryButton", Palette.INK)
	t.set_color("font_focus_color", "PrimaryButton", Palette.SURFACE_DEEP)
	t.set_color("font_disabled_color", "PrimaryButton", Palette.INK_FAINT)

	## A step sideways rather than forward: Back, Cancel, Skip. Text only, so
	## it reads as available without occupying the weight a bordered button does.
	t.set_type_variation("QuietButton", "Button")
	var bare: StyleBoxFlat = _control_box(Palette.SURFACE, Palette.SURFACE)
	bare.draw_center = false
	bare.set_border_width_all(0)
	t.set_stylebox("normal", "QuietButton", bare)
	var bare_hover: StyleBoxFlat = _control_box(Palette.SURFACE, Palette.SURFACE)
	t.set_stylebox("hover", "QuietButton", bare_hover)
	t.set_stylebox("pressed", "QuietButton", _control_box(Palette.SURFACE_DEEP, Palette.SURFACE_DEEP))
	t.set_stylebox("focus", "QuietButton", _focus_ring())
	t.set_color("font_color", "QuietButton", Palette.INK_MUTED)
	t.set_color("font_hover_color", "QuietButton", Palette.INK)

	## A row inside a scrollable, multi-column list -- the saved-mystery
	## browser needs a title column and a right-aligned star-rating column
	## that line up across rows, which ItemList's one-string-per-item model
	## cannot do (playtest BrowseSept8). Mirrors ItemList's own hover/selected
	## states (_style_lists) so swapping the control doesn't read as a
	## different list.
	t.set_type_variation("BrowseRowButton", "Button")
	var row_normal: StyleBoxFlat = _control_box(Palette.SURFACE_DEEP, Palette.SURFACE_DEEP)
	row_normal.draw_center = false
	row_normal.set_border_width_all(0)
	t.set_stylebox("normal", "BrowseRowButton", row_normal)
	t.set_stylebox("hover", "BrowseRowButton", _panel(Palette.SURFACE, Palette.RADIUS_SMALL, Palette.SURFACE))
	t.set_stylebox("pressed", "BrowseRowButton", _panel(Palette.SURFACE_RAISED, Palette.RADIUS_SMALL, Palette.BRASS))
	t.set_stylebox("focus", "BrowseRowButton", _focus_ring())
	t.set_color("font_color", "BrowseRowButton", Palette.INK)
	t.set_color("font_hover_color", "BrowseRowButton", Palette.INK)
	t.set_color("font_pressed_color", "BrowseRowButton", Palette.INK)
	t.set_font_size("font_size", "BrowseRowButton", Palette.TYPE_BODY)

	## A suspect grid cell -- portrait over name, click either to select who
	## you're interrogating (playtest InterrogationSept8, replacing the old
	## suspect dropdown). Uses toggle_mode + a shared ButtonGroup rather than
	## manual selection-tracking, so "pressed" IS "selected" and stays lit
	## until another cell is chosen. Same hover/selected language as
	## BrowseRowButton -- one card list, one row list, one visual vocabulary.
	t.set_type_variation("SuspectCardButton", "Button")
	var card_normal: StyleBoxFlat = _control_box(Palette.SURFACE_DEEP, Palette.SURFACE_DEEP)
	card_normal.draw_center = false
	card_normal.set_border_width_all(0)
	t.set_stylebox("normal", "SuspectCardButton", card_normal)
	t.set_stylebox("hover", "SuspectCardButton", _panel(Palette.SURFACE, Palette.RADIUS_SMALL, Palette.SURFACE))
	t.set_stylebox("pressed", "SuspectCardButton", _panel(Palette.SURFACE_RAISED, Palette.RADIUS_SMALL, Palette.BRASS))
	t.set_stylebox("focus", "SuspectCardButton", _focus_ring())
	t.set_color("font_color", "SuspectCardButton", Palette.INK)
	t.set_color("font_hover_color", "SuspectCardButton", Palette.INK)
	t.set_color("font_pressed_color", "SuspectCardButton", Palette.BRASS)
	t.set_font_size("font_size", "SuspectCardButton", Palette.TYPE_BODY)

	## Irreversible and consequential: the accusation. CYM has exactly one
	## action a player cannot take back, and it should not look like Back.
	t.set_type_variation("DangerButton", "Button")
	t.set_stylebox("normal", "DangerButton", _control_box(Palette.SURFACE, Palette.NEGATIVE))
	t.set_stylebox("hover", "DangerButton", _control_box(Palette.SURFACE_RAISED, Palette.NEGATIVE))
	t.set_stylebox("pressed", "DangerButton", _control_box(Palette.SURFACE_DEEP, Palette.NEGATIVE))
	t.set_stylebox("disabled", "DangerButton", _control_box(Palette.SURFACE_DEEP, Palette.LINE_SOFT))
	t.set_stylebox("focus", "DangerButton", _focus_ring())
	t.set_color("font_color", "DangerButton", Palette.NEGATIVE)
	t.set_color("font_hover_color", "DangerButton", Palette.NEGATIVE)
	t.set_color("font_pressed_color", "DangerButton", Palette.INK)
	t.set_color("font_disabled_color", "DangerButton", Palette.INK_FAINT)

	## A panel that should read as sunk into the page: transcripts, feeds,
	## evidence lists. The well tier, as a container.
	t.set_type_variation("WellPanel", "PanelContainer")
	t.set_stylebox("panel", "WellPanel", _panel(Palette.SURFACE_DEEP, Palette.RADIUS_CARD))
