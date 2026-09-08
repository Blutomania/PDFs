## scripts/build_palette.py from palette.py — DO NOT EDIT BY HAND
##
## The CYM palette, as Godot sees it. Regenerate with:
##     python3 scripts/build_palette.py
##
## Not an autoload and not a Theme. `class_name` makes every constant
## reachable as `Palette.GROUND` from any script with no load-order
## question to get wrong; the Theme that USES these is built in
## scripts/autoloads/Style.gd, which is hand-written and is not
## touched by regeneration.
##
## Every declaration states its type. Session 36 lost a whole screen to
## an inferred Variant, and `:=` on a constructor call is exactly the
## shape that went wrong.
class_name Palette
extends RefCounted


## Colours. Float components rather than Color("#RRGGBB") because a
## const initialiser has to be constant-foldable and a String is not.
const GROUND: Color = Color(0.184314, 0.266667, 0.349020, 1.0)  ## #2F4459
const SURFACE: Color = Color(0.141176, 0.207843, 0.270588, 1.0)  ## #243545
const SURFACE_DEEP: Color = Color(0.105882, 0.152941, 0.200000, 1.0)  ## #1B2733
const SURFACE_RAISED: Color = Color(0.227451, 0.321569, 0.411765, 1.0)  ## #3A5269
const LINE: Color = Color(0.439216, 0.564706, 0.678431, 1.0)  ## #7090AD
const LINE_SOFT: Color = Color(0.219608, 0.313725, 0.415686, 1.0)  ## #38506A
const INK: Color = Color(0.909804, 0.929412, 0.949020, 1.0)  ## #E8EDF2
const INK_MUTED: Color = Color(0.721569, 0.768627, 0.811765, 1.0)  ## #B8C4CF
const INK_FAINT: Color = Color(0.560784, 0.639216, 0.709804, 1.0)  ## #8FA3B5
const BRASS: Color = Color(0.788235, 0.635294, 0.152941, 1.0)  ## #C9A227
const BRASS_BRIGHT: Color = Color(0.890196, 0.737255, 0.258824, 1.0)  ## #E3BC42
const BRASS_DIM: Color = Color(0.541176, 0.435294, 0.105882, 1.0)  ## #8A6F1B
const STEEL: Color = Color(0.305882, 0.431373, 0.564706, 1.0)  ## #4E6E90
const STEEL_BRIGHT: Color = Color(0.458824, 0.607843, 0.784314, 1.0)  ## #759BC8
const POSITIVE: Color = Color(0.392157, 0.666667, 0.482353, 1.0)  ## #64AA7B
const NEGATIVE: Color = Color(0.835294, 0.525490, 0.537255, 1.0)  ## #D58689
const CAUTION: Color = Color(0.796078, 0.560784, 0.266667, 1.0)  ## #CB8F44


## Type sizes in pixels, for the 1280x720 host viewport. The phone
## client deliberately does NOT share these — see palette.py.
const TYPE_DISPLAY: int = 44
const TYPE_TITLE: int = 30
const TYPE_HEADING: int = 21
const TYPE_BODY: int = 16
const TYPE_LABEL: int = 13


## Spacing.
const SPACE_TIGHT: int = 4
const SPACE_SMALL: int = 8
const SPACE_BASE: int = 12
const SPACE_WIDE: int = 16
const SPACE_SECTION: int = 24
const SPACE_SCREEN: int = 32


## Corner radii.
const RADIUS_SMALL: int = 4
const RADIUS_BASE: int = 8
const RADIUS_CARD: int = 14

const BORDER_WIDTH: int = 1
