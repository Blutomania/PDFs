#!/usr/bin/env python3
"""Flatten the icon sets to the palette and generate the client copies. Zero API cost.

    python3 scripts/build_icons.py          # write the generated copies
    python3 scripts/build_icons.py --check  # fail if they have drifted
    python3 scripts/build_icons.py --report # describe what is in the sources

Sources live in icons/clue/ and icons/witness/ — see icons/README.md. Filenames
carry no meaning; the folder assigns the set.

WHY FLATTEN. The icons arrive as multi-hue gradients (amber, blue, magenta,
green, red, cyan, orange, violet). The game is slate and brass with exactly one
warm accent, rationed on purpose — background_field.py's own comment records
what happened when the brass share went to 16% ("the warm marks read as a
different, louder element rather than as part of one texture"). Eight hues would
do that to the whole interface. So every gradient, fill and stroke in an icon
collapses to a single value.

WHY WHITE FOR GODOT AND currentColor FOR THE PHONE. Godot's SVG importer
rasterises with the colours in the file and has no notion of currentColor, so a
Godot icon is recoloured by MODULATING its texture — and modulate multiplies,
which means a white source can become any palette colour and a pre-tinted one
cannot. CSS has the opposite affordance, so the phone copy defers to
currentColor and the stylesheet decides. One source, two mechanisms, no third
copy of the palette.

RASTER SOURCES. A .png in a set folder is handled too, and is second choice
rather than an error: a bitmap cannot be re-cut or re-weighted and cannot scale
past its own resolution, which matters because CYM's host screen is a
television. Flattening one is simpler than flattening vector, because the alpha
channel already IS the artwork — the RGB is discarded and every pixel becomes
white at its original opacity, giving a coverage mask. Godot multiplies that by
a palette colour with modulate; CSS does the same with `mask-image` plus a
`background-color`, which is why the phone copy of a raster icon is the same
white file rather than a currentColor one.

WHAT IT REFUSES. A raster embedded in an SVG wrapper. The rewrite works on paint
attributes, so a base64 <image> passes through untouched and would arrive in the
product as the only multi-coloured thing in it. brand/negative_logo.svg and
brand/organic_logo.svg were exactly that shape and had to be re-cut, so this is
a failure rather than a warning.
"""

from __future__ import annotations

import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import palette  # noqa: E402

SRC = ROOT / "icons"
SETS = ("clue", "witness", "suspect")

GODOT_OUT = ROOT / "godot" / "assets" / "icons"
PHONE_OUT = ROOT / "server" / "static" / "icons"
ICONSET_GD = ROOT / "godot" / "scripts" / "theme" / "IconSet.gd"

# Godot copies are pure white so modulate can tint them; see the header.
GODOT_PAINT = "#FFFFFF"
PHONE_PAINT = "currentColor"

BANNER = "scripts/build_icons.py from icons/ — DO NOT EDIT BY HAND"

SVG_NS = "http://www.w3.org/2000/svg"
PAINTED = ("path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "g", "svg", "use")


class NotVector(Exception):
    """An SVG whose content cannot be recoloured by rewriting paint."""


def _rel(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    relative_to() RAISES on a path outside the repo, and every use of it here
    is inside an error message -- so without this the failure path can itself
    fail, replacing a clear diagnostic with a ValueError traceback. Found by a
    test that fed the checker a fixture from a scratch directory.
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _assert_vector(path: Path, text: str) -> None:
    if re.search(r"<image\b", text, re.IGNORECASE) or "base64," in text:
        raise NotVector(
            f"{_rel(path)} embeds a raster image.\n"
            f"       Paint attributes are what this script rewrites, so a bitmap "
            f"passes through in its original colours.\n"
            f"       Re-cut it as real vector paths (this is what happened to "
            f"brand/negative_logo.svg) and run again."
        )


def _recolour_style_block(css: str, paint: str) -> str:
    """Rewrite paint inside a <style> block.

    Exported SVGs frequently put their paint in CSS classes rather than on the
    elements (`.st0{fill:none;stroke:url(#grad)}`), and a pass that only walked
    attributes would silently leave those files fully coloured while reporting
    success. `none` is preserved wherever it appears -- it is the difference
    between an outline icon and a solid blob.
    """
    def sub(match: re.Match) -> str:
        prop, value = match.group(1), match.group(2).strip()
        if value.lower() == "none":
            return match.group(0)
        return f"{prop}:{paint}"

    return re.sub(r"\b(fill|stroke)\s*:\s*([^;}]+)", sub, css, flags=re.IGNORECASE)


def recolour(text: str, paint: str) -> tuple[str, dict]:
    """Return the SVG with every non-`none` paint set to `paint`, plus a tally.

    `none` is never touched. An outline icon is drawn as `fill:none` with a
    stroke, and painting those fills would turn every one of them into a solid
    silhouette -- which is not a colour change, it is a different icon.
    """
    ET.register_namespace("", SVG_NS)
    root = ET.fromstring(text)
    seen = {"fill": 0, "stroke": 0, "gradient": 0, "style_blocks": 0, "elements": 0}

    for el in root.iter():
        tag = _strip_ns(el.tag)

        if tag == "style" and el.text:
            seen["style_blocks"] += 1
            seen["gradient"] += len(re.findall(r"url\(#", el.text))
            el.text = _recolour_style_block(el.text, paint)
            continue

        if tag in PAINTED:
            seen["elements"] += 1

        for attr in ("fill", "stroke"):
            value = el.get(attr)
            if value is None or value.strip().lower() == "none":
                continue
            if value.strip().lower().startswith("url(#"):
                seen["gradient"] += 1
            seen[attr] += 1
            el.set(attr, paint)

        inline = el.get("style")
        if inline:
            seen["gradient"] += len(re.findall(r"url\(#", inline))
            el.set("style", _recolour_style_block(inline, paint))

    body = ET.tostring(root, encoding="unicode")
    return f"<!-- {BANNER} -->\n{body}\n", seen


def sources() -> dict:
    found = {}
    for name in SETS:
        folder = SRC / name
        if not folder.exists():
            found[name] = []
            continue
        found[name] = sorted(
            p for p in folder.iterdir()
            if p.suffix.lower() in (".svg", ".png")
        )
    return found


def flatten_raster(path: Path) -> bytes:
    """A raster icon as a white coverage mask, PNG-encoded.

    The alpha channel is the drawing; the RGB is thrown away. Converting the
    hues to greys instead would carry the source gradient's own light and dark
    into the result, so the icons would arrive with brightness variation nobody
    chose — the amber magnifier reading heavier than the green one for no
    reason a designer decided.
    """
    from PIL import Image  # imported here so the vector path needs no Pillow

    source = Image.open(path).convert("RGBA")
    mask = Image.new("RGBA", source.size, (255, 255, 255, 0))
    mask.putalpha(source.getchannel("A"))
    buffer = io.BytesIO()
    mask.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_iconset_gd(found: dict) -> str:
    lines = [
        "## " + BANNER,
        "##",
        "## The icon sets, as resource paths. Regenerate with:",
        "##     python3 scripts/build_icons.py",
        "##",
        "## Data only. The PICKING lives in scripts/theme/Icons.gd and is",
        "## hand-written, because which icon a clue gets is a design rule with",
        "## a reason behind it, not a list -- see that file.",
        "class_name IconSet",
        "extends RefCounted",
        "",
    ]
    for name in SETS:
        paths = [f'\t"res://assets/icons/{name}/{p.name}",' for p in found[name]]
        lines.append("")
        lines.append(f"const {name.upper()}: Array[String] = [")
        lines += paths if paths else ["\t# none yet -- drop SVGs into icons/%s/" % name]
        lines.append("]")
    lines.append("")
    return "\n".join(lines)


def build(check_only: bool = False, report: bool = False) -> int:
    found = sources()
    total = sum(len(v) for v in found.values())

    if report or total == 0:
        for name in SETS:
            print(f"  icons/{name}/  {len(found[name])} file(s)")
            for p in found[name]:
                if p.suffix.lower() == ".png":
                    from PIL import Image
                    im = Image.open(p)
                    print(f"      {p.name}: raster {im.width}x{im.height} {im.mode} "
                          f"— flattened from its alpha channel")
                    continue
                try:
                    _, seen = recolour(p.read_text(), GODOT_PAINT)
                    print(f"      {p.name}: {seen['elements']} painted elements, "
                          f"{seen['fill']} fills, {seen['stroke']} strokes, "
                          f"{seen['gradient']} gradient refs, "
                          f"{seen['style_blocks']} style block(s)")
                except (ET.ParseError, NotVector) as exc:
                    print(f"      {p.name}: UNREADABLE — {exc}")
        if report:
            return 0

    targets: list[tuple[Path, object, object]] = []
    for name in SETS:
        for src in found[name]:
            if src.suffix.lower() == ".png":
                # One file serves both clients: Godot tints it with modulate,
                # CSS with mask-image. Neither needs a per-client variant.
                wanted_bytes = flatten_raster(src)
                for out_dir in (GODOT_OUT, PHONE_OUT):
                    dest = out_dir / name / src.name
                    current = dest.read_bytes() if dest.exists() else None
                    targets.append((dest, wanted_bytes, current))
                continue

            text = src.read_text()
            _assert_vector(src, text)
            for out_dir, paint in ((GODOT_OUT, GODOT_PAINT), (PHONE_OUT, PHONE_PAINT)):
                dest = out_dir / name / src.name
                wanted, _ = recolour(text, paint)
                current = dest.read_text() if dest.exists() else None
                targets.append((dest, wanted, current))

    gd = render_iconset_gd(found)
    targets.append((ICONSET_GD, gd, ICONSET_GD.read_text() if ICONSET_GD.exists() else None))

    drifted = [d for d, wanted, current in targets if wanted != current]

    if check_only:
        for d in drifted:
            print(f"  DRIFTED  {_rel(d)}")
        if not drifted:
            print(f"  in sync  {len(targets)} generated file(s) from {total} source icon(s)")
        else:
            print("\nRegenerate with: python3 scripts/build_icons.py")
        return 1 if drifted else 0

    for dest, wanted, current in targets:
        if wanted == current:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(wanted, bytes):
            dest.write_bytes(wanted)
        else:
            dest.write_text(wanted)
        print(f"  wrote      {_rel(dest)}")
    if total == 0:
        print("\nNo icons yet — IconSet.gd generated empty, which is a valid state: "
              "Icons.pick() returns \"\" and screens draw no icon.\n"
              "Drop the SVGs into icons/clue/ and icons/witness/ (see icons/README.md), "
              "then run this again.")
    else:
        print(f"\n{total} source icon(s) -> {len(targets)} generated file(s).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(build(check_only="--check" in sys.argv, report="--report" in sys.argv))
    except NotVector as exc:
        print(f"error: {exc}")
        sys.exit(1)
