## scripts/build_icons.py from icons/ — DO NOT EDIT BY HAND
##
## The icon sets, as resource paths. Regenerate with:
##     python3 scripts/build_icons.py
##
## Data only. The PICKING lives in scripts/theme/Icons.gd and is
## hand-written, because which icon a clue gets is a design rule with
## a reason behind it, not a list -- see that file.
class_name IconSet
extends RefCounted


const CLUE: Array[String] = [
	"res://assets/icons/clue/clue_01.svg",
	"res://assets/icons/clue/clue_02.svg",
	"res://assets/icons/clue/clue_03.svg",
	"res://assets/icons/clue/clue_04.svg",
]

const WITNESS: Array[String] = [
	"res://assets/icons/witness/witness_01.svg",
	"res://assets/icons/witness/witness_02.svg",
	"res://assets/icons/witness/witness_03.svg",
	"res://assets/icons/witness/witness_04.svg",
]

const SUSPECT: Array[String] = [
	# none yet -- drop SVGs into icons/suspect/
]
