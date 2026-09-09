"""
palette.py — the one CYM palette, and the only place a colour is decided.

WHY THIS FILE EXISTS. Before it, the product held three unrelated palettes and
none of them knew about the others:

  1. brand/README.md and scripts/check_brand_contrast.py declare the ground to
     be slate #2F4459, and call it "the one rule these assets must satisfy".
  2. server/static/mobile.html — the phone client every player actually looks
     at — was built on an invented navy #1a1a2e with its own blues and its own
     brass #c8a96e (note: not the brand's #C9A227, one digit-pair off and
     visibly warmer).
  3. The Godot host screen had no palette at all. Default engine grey, which
     is what "it ran, it's ugly, but it works" was describing.

So the two clients in the same room, at the same time, showed two different
games, and the documented standard was the one surface nobody rendered. That
is not a styling backlog, it is drift — and it is exactly the failure
brand/README.md predicts in its own opening paragraph, about why the source
artwork does not live inside either client's folder. The same argument applies
to the colours, so they live here, once.

WHAT IMPORTS THIS. Nothing renders from here directly, because two of the
three surfaces are not Python. scripts/build_palette.py generates
godot/scripts/autoloads/Palette.gd and the CSS custom-property block in
mobile.html from these values, and `--check` on that same script fails if
either has drifted from this file. Generated-then-checked rather than
imported, because GDScript and CSS cannot import Python and a comment asking
people to keep three files in step is how you get three palettes again.

ZERO API COST. Pure data and arithmetic.
"""

from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# The ground
# ---------------------------------------------------------------------------

# Slate. NOT a fresh choice — this is the value brand/README.md already binds
# the artwork to, that scripts/check_brand_contrast.py already measures ink
# against, and that MYF uses as its own ground so the two titles read as
# siblings. background_field.py's five mark colours were pitched against it.
# Changing it invalidates all of that, so it changes here and nowhere else.
GROUND = "#2F4459"


# ---------------------------------------------------------------------------
# The surface ramp
# ---------------------------------------------------------------------------
#
# Panels go DEEPER than the ground, not lighter, and this is the one place the
# palette departs from what a designer would reach for first. Two reasons, both
# structural rather than aesthetic:
#
#   1. The BACKGROUND field is painted on the ground. If panels sat lighter,
#      the strewn title would be the darkest thing on screen and would read as
#      foreground. Sinking the panels puts the texture behind everything, which
#      is the only place a texture belongs.
#   2. CYM's screens are text-dense in a way MYF's are not — clue lists,
#      interrogation transcripts, evidence tables. Slate is a mid-tone; #E8EDF2
#      on it is 8.5:1, fine for a heading and tiring for a transcript. On
#      SURFACE the same ink is 10.7:1 and on SURFACE_DEEP 12.9:1.
#
# So: read the ground as the room and the panels as the paper on the desk.

SURFACE = "#243545"        # cards, panels — the default place text sits
SURFACE_DEEP = "#1B2733"   # inset wells: transcripts, feeds, evidence lists
SURFACE_RAISED = "#3A5269"  # hover, selection, the row under the cursor

# Two border weights, and the split is a contrast requirement rather than a
# taste one. WCAG 1.4.11 asks 3:1 of anything that is the ONLY thing marking a
# control's boundary — which is true of a LineEdit, whose outline is its whole
# affordance, and false of a panel edge, where the fill change already does the
# separating. Holding both to 3:1 made every panel edge a bright rule the eye
# traced instead of reading past; holding neither to it made text fields
# invisible. So LINE is for controls and is measured; LINE_SOFT is decorative
# and deliberately carries no floor.
LINE = "#7090AD"       # control boundaries: inputs, outlined buttons, focus
LINE_SOFT = "#38506A"  # decorative panel edges only — no contrast contract


# ---------------------------------------------------------------------------
# Ink
# ---------------------------------------------------------------------------
#
# Three weights, not five. Every extra tier is a decision someone has to make
# at every label, and the ones below are already separated by enough contrast
# to be told apart at a glance.

INK = "#E8EDF2"        # body and headings
INK_MUTED = "#B8C4CF"  # secondary — supporting prose, inactive tabs
INK_FAINT = "#8FA3B5"  # tertiary — field labels, timestamps, attribution
#
# INK_FAINT is 3.86:1 on the ground and 4.83:1 on SURFACE. That is below the
# 4.5:1 body-text bar on the ground, which is deliberate and is why it is
# named "faint": it is for 13px-and-up labels on panels, never for prose on
# the ground. contrast_report() below prints the whole matrix so this stays a
# measured decision rather than a remembered one.


# ---------------------------------------------------------------------------
# Accent
# ---------------------------------------------------------------------------

# Brass. The one warm note in the whole product, and it is rationed on purpose
# — background_field.py gives it an 8% share of the marks and its comment
# records why the first pass at 16% failed ("the warm marks read as a
# different, louder element rather than as part of one texture"). The same
# restraint applies here: brass means "this is the thing to act on" or "this
# is the mystery's own name". If it starts appearing on every panel it stops
# meaning anything.
BRASS = "#C9A227"
BRASS_BRIGHT = "#E3BC42"  # hover/focus only
BRASS_DIM = "#8A6F1B"     # pressed, and disabled-but-still-primary

# Steel — the cool counterpart, for secondary actions that should read as
# available without competing with the primary one.
STEEL = "#4E6E90"     # a FILL, so it is pitched dark enough for INK to sit on it
STEEL_BRIGHT = "#759BC8"  # hover only


# ---------------------------------------------------------------------------
# Semantic
# ---------------------------------------------------------------------------
#
# Pitched into the slate family rather than taken off the shelf. mobile.html's
# #4caf50 and #e05050 are Material defaults; against this ground they read as
# stickers on the design rather than parts of it, because their saturation is
# far above anything else on screen.

# These are LIGHTER than a semantic colour usually looks, and that is forced
# rather than chosen. Slate is a mid-tone ground, so a saturated red simply
# cannot reach 4.5:1 on it — Material's own dark-theme error #CF6679 manages
# only 3.49:1 on SURFACE here. The choice is between a red that reads and a red
# that looks like a red, and text you cannot read is not worth the saturation.
# Each was tuned by walking lightness at fixed hue until the floor was met, so
# they stay in family rather than becoming three unrelated stickers.
POSITIVE = "#64AA7B"  # a clue that reached you, a connected socket
NEGATIVE = "#D58689"  # an error, a wrong accusation, a duplicate
CAUTION = "#CB8F44"   # a budget running out, an unmoderated-input notice
#
# NOT CARRIED BY HUE ALONE. POSITIVE/NEGATIVE mark things a player acts on —
# a shared clue against a duplicate one — and red/green is the one pair a
# common colour blindness collapses. mobile.html already pairs them with
# strikethrough and a border-side marker; anything new must carry a second
# signal too.


# ---------------------------------------------------------------------------
# Type scale
# ---------------------------------------------------------------------------
#
# Sized in pixels for the Godot host screen's 1280x720 viewport, and for that
# screen only. The phone client is NOT generated from this and keeps its own
# em-based sizing, which is a deliberate limit rather than an omission: the two
# surfaces are read at completely different distances, so 44px is barely a
# title on a television across a room and absurd on a handset. Colour is the
# thing that must agree between them — a player looking from phone to TV sees
# one game or two — and type size is the thing that must not.

TYPE_SCALE: Dict[str, int] = {
    # The main menu wordmark, and whatever else earns the same weight: the
    # room code, and a player's own name in the lobby (Session 43, owner --
    # "who you are playing with is high up in a hierarchy of import"). Not a
    # size for casual reuse; each addition has been a deliberate call that
    # something belongs at the top of the screen's hierarchy, not a default.
    "display": 44,
    "title": 30,    # one per screen, at the top
    "heading": 21,  # section headers within a screen
    "body": 16,     # the default; everything unlabelled is this
    "label": 13,    # field labels, attribution, timestamps
}

# Spacing, in the same spirit: a short scale people can hold in their head.
SPACE: Dict[str, int] = {
    "tight": 4,
    "small": 8,
    "base": 12,
    "wide": 16,
    "section": 24,
    "screen": 32,
}

RADIUS: Dict[str, int] = {
    "small": 4,   # badges, inline chips
    "base": 8,    # buttons, inputs
    "card": 14,   # panels
}

BORDER_WIDTH = 1


# ---------------------------------------------------------------------------
# Contrast — the arithmetic, kept here because this file owns the colours
# ---------------------------------------------------------------------------

def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def rgb(hex_value: str) -> Tuple[int, int, int]:
    """#RRGGBB -> (r, g, b). Accepts the leading # or not."""
    h = hex_value.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"not a 6-digit hex colour: {hex_value!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(hex_value: str) -> float:
    """WCAG relative luminance."""
    r, g, b = (c / 255 for c in rgb(hex_value))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours, always >= 1."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# Every ink/background pair the UI can actually produce, and the floor each one
# has to clear. This is the palette's test surface: scripts/test_palette.py
# walks it, so a colour cannot be re-pitched without the consequence showing up
# as a failure rather than as a screen someone squints at later.
#
# Floors follow WCAG: 4.5 for body text, 3.0 for large text (>= 21px, i.e. the
# heading tier and up) and for the boundary of a control.
CONTRAST_CONTRACT: Tuple[Tuple[str, str, float, str], ...] = (
    (INK, GROUND, 4.5, "body text on the ground"),
    (INK, SURFACE, 4.5, "body text on a panel"),
    (INK, SURFACE_DEEP, 4.5, "body text in a well"),
    (INK, SURFACE_RAISED, 4.5, "body text on a hovered row"),
    (INK_MUTED, GROUND, 4.5, "secondary prose on the ground"),
    (INK_MUTED, SURFACE, 4.5, "secondary prose on a panel"),
    (INK_MUTED, SURFACE_DEEP, 4.5, "secondary prose in a well"),
    (INK_FAINT, SURFACE, 4.5, "field labels on a panel"),
    (INK_FAINT, SURFACE_DEEP, 4.5, "field labels in a well"),
    (INK_FAINT, GROUND, 3.0, "field labels on the ground (large only)"),
    (BRASS, GROUND, 3.0, "the mystery title on the ground (large only)"),
    (BRASS, SURFACE, 4.5, "brass text on a panel"),
    (BRASS, SURFACE_DEEP, 4.5, "brass text in a well"),
    # Semantics carry body-text weight on the two panel tiers, where prose
    # actually lives, and marker weight on the ground, where they appear as
    # borders and large status text. See the note above POSITIVE for why a
    # 4.5 floor on the ground is not reachable at any usable saturation.
    (POSITIVE, SURFACE, 4.5, "a shared-clue marker on a panel"),
    (POSITIVE, SURFACE_DEEP, 4.5, "a shared-clue marker in a well"),
    (POSITIVE, GROUND, 3.0, "a shared-clue marker on the ground"),
    (NEGATIVE, SURFACE, 4.5, "an error message on a panel"),
    (NEGATIVE, SURFACE_DEEP, 4.5, "an error message in a well"),
    (NEGATIVE, GROUND, 3.0, "an error marker on the ground"),
    (CAUTION, SURFACE, 4.5, "a budget warning on a panel"),
    (CAUTION, SURFACE_DEEP, 4.5, "a budget warning in a well"),
    (CAUTION, GROUND, 3.0, "a caution marker on the ground"),
    # LINE is measured because it is the whole affordance of a text field.
    # LINE_SOFT is decorative and appears here on purpose with no floor of its
    # own, so that its absence reads as a decision rather than an oversight.
    (LINE, SURFACE, 3.0, "a text field's outline on a panel"),
    (LINE, SURFACE_DEEP, 3.0, "a text field's outline in a well"),
    (LINE, GROUND, 3.0, "a text field's outline on the ground"),
    # Filled buttons: the pairing that matters is the LABEL against the fill.
    (SURFACE_DEEP, BRASS, 4.5, "the label on a primary button"),
    (SURFACE_DEEP, BRASS_BRIGHT, 4.5, "the label on a hovered primary button"),
    (INK, STEEL, 4.5, "the label on a secondary button"),
)


def contrast_report() -> str:
    """The whole contract as a table. Printed by scripts/test_palette.py."""
    rows = ["  ratio  floor  pair"]
    for fg, bg, floor, why in CONTRAST_CONTRACT:
        ratio = contrast(fg, bg)
        mark = "ok " if ratio >= floor else "LOW"
        rows.append(f"  {ratio:5.2f}  {floor:5.1f}  {mark} {why}  ({fg} on {bg})")
    return "\n".join(rows)


# The full ordered mapping the generators walk. Ordered so the generated files
# read top-to-bottom the way this one does, rather than alphabetically.
COLOURS: Dict[str, str] = {
    "ground": GROUND,
    "surface": SURFACE,
    "surface_deep": SURFACE_DEEP,
    "surface_raised": SURFACE_RAISED,
    "line": LINE,
    "line_soft": LINE_SOFT,
    "ink": INK,
    "ink_muted": INK_MUTED,
    "ink_faint": INK_FAINT,
    "brass": BRASS,
    "brass_bright": BRASS_BRIGHT,
    "brass_dim": BRASS_DIM,
    "steel": STEEL,
    "steel_bright": STEEL_BRIGHT,
    "positive": POSITIVE,
    "negative": NEGATIVE,
    "caution": CAUTION,
}


if __name__ == "__main__":
    print(f"CYM palette — ground {GROUND}\n")
    print(contrast_report())
