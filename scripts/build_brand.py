#!/usr/bin/env python3
"""Mirror the canonical brand marks into godot/assets/brand/. Zero API cost.

    python3 scripts/build_brand.py          # write the generated copies
    python3 scripts/build_brand.py --check  # fail if they have drifted

WHY A SEPARATE SCRIPT FROM build_icons.py, NOT A SHARED ONE. build_icons.py
flattens a decorative icon to a single palette hue and produces TWO differently
-painted copies (white for Godot's modulate, currentColor for the phone's CSS)
because a clue icon is retinted per screen and carries no fixed identity of its
own. A brand mark is the opposite: it IS a fixed identity, drawn once with its
own defined values, and recolouring it on the way in would be editing the logo,
not shipping it. So this script does the plain thing that operation actually
needs -- a byte-exact copy from source to client -- and nothing else.

WHY brand/ IS NOT INSIDE godot/ IN THE FIRST PLACE. See brand/README.md: CYM
has two clients (Godot host, phone at /play) that both need the same mark, so
the original lives once, outside either, and each client gets a generated copy
-- same "generated, then checked" shape as palette.py -> Palette.gd and
icons/ -> godot/assets/icons/. A copy nobody regenerates is a copy that drifts
the moment the source is touched, which is the whole reason those two scripts
exist; this is the same argument a third time.

WHAT IT REFUSES. brand/negative_logo.svg and brand/organic_logo.svg -- the
pre-Session-33 files, still on disk for provenance -- are PNGs wrapped in SVG
syntax (a base64 <image>, zero real <path> elements). build_icons.py already
documents why that shape cannot be recoloured; here the concern is narrower
but the same in kind: this script only ever mirrors the NEW*.svg names, so an
old raster-wrapper file is never silently picked up by a future glob change.

Only the Godot copy exists today -- CYM's phone client (server/static/mobile.html)
has no chrome pass yet (stage 3, docs/CLAUDE.md Delivery Priority), so there is
nothing on that side to mirror to until that work starts.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
GODOT_OUT = ROOT / "godot" / "assets" / "brand"

# Source name -> generated name. Deliberately explicit rather than a glob over
# brand/*.svg: a glob would also pick up the deprecated raster-wrapper files
# (negative_logo.svg, organic_logo.svg) the moment nobody was looking.
MARKS = {
    "NEWnegative_CYM.svg": "negative_mark.svg",
    "NEWorganic_cym.svg": "organic_mark.svg",
}


def build(check_only: bool) -> int:
    targets: list[tuple[Path, bytes, bytes | None]] = []
    missing: list[str] = []

    for src_name, out_name in MARKS.items():
        src = BRAND / src_name
        if not src.exists():
            missing.append(src_name)
            continue
        wanted = src.read_bytes()
        dest = GODOT_OUT / out_name
        current = dest.read_bytes() if dest.exists() else None
        targets.append((dest, wanted, current))

    if missing:
        print(f"error: missing source mark(s): {', '.join(missing)}")
        return 1

    drifted = [d for d, wanted, current in targets if wanted != current]

    if check_only:
        for d in drifted:
            print(f"  DRIFTED  {d.relative_to(ROOT)}")
        if not drifted:
            print(f"  in sync  {len(targets)} generated file(s) from {len(MARKS)} source mark(s)")
        else:
            print("\nRegenerate with: python3 scripts/build_brand.py")
        return 1 if drifted else 0

    for dest, wanted, current in targets:
        if wanted == current:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(wanted)
        print(f"  wrote      {dest.relative_to(ROOT)}")

    print(f"\n{len(MARKS)} source mark(s) -> {len(targets)} generated file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(build(check_only="--check" in sys.argv))
