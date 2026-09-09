## Icons — which icon a thing gets, and why it means nothing.
##
## THE RULE (owner, Session 37): the icon sets decorate. They must never be
## read as a signal. Which of the four magnifiers sits beside a clue says
## nothing about that clue, and a player who starts believing the fingerprint
## one means something has been actively misled by the interface.
##
## THE OBVIOUS IMPLEMENTATION IS WRONG IN BOTH DIRECTIONS.
##
##   randi() % size, rolled at draw time, re-rolls on every redraw. The icon
##   beside a clue would change whenever the list rebuilds, which reads as a
##   bug and is genuinely distracting on a screen the player is studying.
##
##   hash(clue_id) % size, the fix people reach for next, is a FIXED MAPPING
##   wearing a costume. The same clue draws the same icon in every game
##   forever, so it is exactly the signal the rule forbids -- and worse, it is
##   a signal random-looking enough that nobody would think to check.
##
## SO: seeded, with the GAME in the seed. Stable for as long as anyone is
## looking at it, and reshuffled between games, which is what makes the
## randomness real rather than a lookup table nobody has noticed yet. Same
## technique background_field.py uses for the mark field, and for the same
## reason -- a reconnecting player should rejoin the screen they left.
##
## The two SETS do differ from one another, and that is intended: a magnifier
## and a speech bubble are different kinds of thing, and the shape carries that
## honestly. It is only the choice WITHIN a set that carries nothing.

class_name Icons
extends RefCounted

## Separates salt from key so ("ab", "c") and ("a", "bc") cannot seed the same
## draw. A space would not do it; this cannot appear in either value.
##
## \u0001 (SOH), written as an ESCAPE, not a literal control byte in the
## source -- a real NUL character sitting between the quotes parses as an
## UNTERMINATED STRING, not as a one-character string containing NUL.
## GDScript's lexer never got a chance to apply the "cannot appear in either
## value" reasoning above; it failed before that, on every load, which is why
## this was never caught by anything that reads source text rather than
## running it. First surfaced Session 42, on the first real F5 this file has
## been part of.
const _SEP: String = "\u0001"


## Pick a clue icon. `key` identifies the thing being decorated (a clue id, an
## evidence id); `salt` should be the game id, so the same key draws a
## different icon in a different game.
static func clue(key: String, salt: String = "") -> String:
	return _pick(IconSet.CLUE, key, salt)


## Pick a witness icon. Same contract as clue().
static func witness(key: String, salt: String = "") -> String:
	return _pick(IconSet.WITNESS, key, salt)


## Pick a suspect icon. Same contract as clue(). Was inert -- IconSet.SUSPECT
## shipped empty while the owner sourced artwork separately (playtest
## StartPageSept7) -- until playtest FindingsSept8, when three PNGs landed in
## icons/suspect/ and scripts/build_icons.py ran. No code change was needed
## to activate it: _pick()/texture()'s empty-set handling is exactly what made
## that possible, and it is what a FOURTH suspect icon would still need today.
static func suspect(key: String, salt: String = "") -> String:
	return _pick(IconSet.SUSPECT, key, salt)


## Load a picked icon as a texture, or null when there is nothing to load.
##
## Returns null rather than a placeholder on purpose: an empty set is a
## legitimate state (the sets ship empty until artwork lands in icons/), and a
## screen that draws nothing is correct there, whereas a "missing icon" box
## would be reporting a fault that does not exist.
static func texture(icon_path: String) -> Texture2D:
	if icon_path.is_empty():
		return null
	if not ResourceLoader.exists(icon_path):
		push_warning("Icons: %s is listed in IconSet but is not on disk. " % icon_path
			+ "Run: python3 scripts/build_icons.py")
		return null
	return load(icon_path) as Texture2D


## The generated icons are pure white so that this multiplies cleanly to any
## palette colour -- see scripts/build_icons.py for why Godot recolours by
## modulate while the phone uses currentColor.
static func tint() -> Color:
	return Palette.INK_MUTED


## An empty String when the set has no icons in it yet.
static func _pick(set_paths: Array[String], key: String, salt: String) -> String:
	if set_paths.is_empty():
		return ""
	var seed_text: String = salt + _SEP + key
	var index: int = _mix32(seed_text.hash()) % set_paths.size()
	return set_paths[index]


## Avalanche the hash before taking a modulus of it.
##
## THIS IS NOT DEFENSIVE POLISH -- without it the feature is broken, and a test
## caught it. String.hash() is djb2 (h * 33 + byte), so keys that differ only in
## their last character produce hashes that differ by almost exactly that
## character's value. Taking `% 4` of that reads the low bits, which had barely
## been mixed at all, and the result was:
##
##     clue_0 .. clue_15  ->  1 2 3 0 1 2 3 0 1 2 2 3 0 1 2 3
##
## The icons would have cycled through the set IN ORDER down every list. That
## is the most legible pattern the set could possibly have had -- the exact
## thing the rule at the top of this file forbids, arrived at by accident.
##
## The same flaw hid in the game salt. A different game shifted every key by one
## constant offset, so the whole assignment ROTATED rather than reshuffling: 400
## of 400 keys changed icon, which looks like a pass until you notice they all
## moved together and the mapping is just as fixed as before.
##
## This is the murmur3 32-bit finalizer. Each step is masked back to 32 bits
## because GDScript ints are 64-bit signed and would otherwise carry high bits
## the constants were never chosen for.
static func _mix32(value: int) -> int:
	var h: int = value & 0xFFFFFFFF
	h = ((h ^ (h >> 16)) * 0x7FEB352D) & 0xFFFFFFFF
	h = ((h ^ (h >> 15)) * 0x846CA68B) & 0xFFFFFFFF
	h = (h ^ (h >> 16)) & 0xFFFFFFFF
	return h
