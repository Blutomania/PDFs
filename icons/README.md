# CYM icon sets

Source artwork for the in-game icon sets. Parallel to `brand/`, and here for the
same reason that file gives: CYM has **two** clients that both need these — the
Godot host screen and the phone client at `/play`. Putting the source inside one
client's folder is how the two end up with silently different versions of the
same mark.

## Where to put them

Drop the SVGs straight into these folders. **Filenames do not matter** —
the folder is what assigns the set, so there is no naming convention to get
wrong.

```
icons/
  clue/        <- the magnifier icons (footprints, fingerprint, puzzle, leaf, …)
  witness/     <- the speech-bubble icons (raised hand, two figures, …)
  suspect/     <- portrait/silhouette icons for the interrogation grid and
                   ResultScreen's culprit portrait; a .png is accepted here
                   too (see "What happens to them" below). suspect/README.md
                   carries this set's own provenance and licensing notes
```

Add as many as you like to either folder. The build picks up whatever is there.

## What happens to them

`python3 scripts/build_icons.py` reads all three folders and writes the client
copies. It does two things to each file:

1. **Flattens the colour.** These arrive as multi-hue gradients; the game is
   slate and brass with one warm accent rationed hard (see `palette.py`), so
   eight separate hues would take the whole palette apart. Every gradient, fill
   and stroke collapses to a single value. The Godot copies are flattened to
   pure white so `modulate` can tint them to any palette colour at runtime; the
   phone copies use `currentColor` so CSS does it.
2. **Records them in a manifest**, which generates
   `godot/scripts/theme/IconSet.gd`.

`--check` fails if the generated copies have drifted from the sources, the same
way `scripts/build_palette.py --check` does for the palette.

## The one rule these assets must satisfy

**Real vector, not a raster in an SVG wrapper.** The build reads and rewrites
paint attributes, so an embedded `<image>` or a base64 payload cannot be
recoloured — it would come through in its original hues and be the only
multi-coloured thing in the product. The build **fails loudly** on one rather
than passing it through.

This is not hypothetical here: `brand/negative_logo.svg` and
`brand/organic_logo.svg` were exactly that, raster PNGs inside an SVG wrapper,
and had to be re-cut before anything could be done with their values.

## Why the icons carry no meaning

Owner's instruction, and the build enforces the shape of it: **which** icon a
given clue or witness gets is chosen at random, so it can never be read as a
signal. The choice is *seeded* rather than re-rolled every frame — stable while
you are looking at it, so nothing flickers — and the seed includes the game id,
so the same clue draws a different icon in a different game. That is what makes
the randomness real rather than a fixed mapping in disguise.

The two SETS do differ from each other, and that is intended: a magnifier and a
speech bubble are different kinds of thing. It is only the choice *within* a set
that means nothing.
