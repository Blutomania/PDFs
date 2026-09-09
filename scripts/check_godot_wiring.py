#!/usr/bin/env python3
"""
Pre-playtest wiring check for the Godot client. Zero API cost, no Godot binary.

Godot only reports a bad `$NodePath` or a forgotten `.connect()` at runtime --
the first as an error the moment the scene loads, the second as silence. A
button that was never connected looks completely correct in the editor, in the
scene file and in the script; it simply does nothing when a playtester clicks
it. That is how MainMenu's "Browse Saved Mysteries" popup shipped inert.

This checks three things across every scene/script pair:

  1. Every `$Path` a script dereferences exists in its scene.
  2. Every `@onready var x: T = $Path` matches the node's actual type in the
     scene (a wrong type is a crash on first use, not on load).
  3. Every interactive control in the scene is referenced by the script at all
     -- the cheap proxy for "this control does something".
  4. Every `GameState.x` / `ApiClient.x` / `NetworkManager.x` a UI script
     touches actually exists on that autoload, and is called with an argument
     count the definition accepts.

Check 3 is a lint, not a proof: it cannot tell a deliberately-decorative
control from a forgotten one, so it reports NOTE rather than FAIL. Checks 1
and 2 are real failures.

Usage:  python3 scripts/check_godot_wiring.py
Exit:   0 = no failures (notes may still be printed), 1 = failures found
"""
import re
import sys
from pathlib import Path

GODOT = Path(__file__).resolve().parent.parent / "godot"

# Controls a player can act on. A control of one of these types that the script
# never mentions is worth a look.
INTERACTIVE = {
    "Button", "CheckBox", "CheckButton", "OptionButton", "MenuButton",
    "LinkButton", "ItemList", "LineEdit", "TextEdit", "Slider", "HSlider",
    "VSlider", "SpinBox", "Tree", "TabBar", "TabContainer",
}


def strip_comments(src: str) -> str:
    """Blank out `#` comments, leaving line structure intact.

    Needed because doc comments in these scripts describe the very calls being
    checked -- `main_menu.gd`'s header says "calls ApiClient.list_mysteries()",
    which the arity check read as a real zero-argument call.
    """
    out = []
    for line in src.splitlines():
        in_str = None
        for i, ch in enumerate(line):
            if in_str:
                if ch == in_str and (i == 0 or line[i - 1] != "\\"):
                    in_str = None
            elif ch in "\"'":
                in_str = ch
            elif ch == "#":
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def parse_scene(path: Path):
    """Return (node_path -> type) for one .tscn, plus its script's file path."""
    nodes = {}
    script_path = None
    ext_scripts = {}

    for line in path.read_text().splitlines():
        m = re.match(r'\[ext_resource type="Script" path="res://([^"]+)" id="([^"]+)"\]', line)
        if m:
            ext_scripts[m.group(2)] = m.group(1)
            continue

        m = re.match(r'\[node name="([^"]+)" type="([^"]+)"(?: parent="([^"]*)")?\]', line)
        if m:
            name, ntype, parent = m.group(1), m.group(2), m.group(3)
            if parent is None:          # the scene root
                node_path = ""
            elif parent == ".":
                node_path = name
            else:
                node_path = f"{parent}/{name}"
            nodes[node_path] = ntype
            continue

        m = re.match(r'script = ExtResource\("([^"]+)"\)', line)
        if m and script_path is None:
            script_path = ext_scripts.get(m.group(1))

    return nodes, script_path


def check_implicit_concat(script: Path, src: str):
    """Flag adjacent string literals across lines -- GDScript has no implicit concat.

    Python and C join `"a" "b"` into `"ab"`. GDScript does not: it is a syntax
    error, `Expected closing ")" after grouping expression`, and it is fatal at
    PARSE time. The whole script fails to load, so every line in it silently
    does nothing while the scene's static nodes still render -- which looks like
    a layout bug, not a syntax error. That is exactly how result_screen.gd
    reached a playtest showing an empty verdict, an empty solution and no rating
    buttons, with no runtime error logged anywhere.

    Comments are stripped before this runs. This pattern only catches literals
    on SEPARATE lines; a single-line Python docstring is caught by
    check_python_docstrings() below, which is a different failure and was the
    reason the "none exist in this project today" note here was wrong for three
    call sites until Session 38 went looking.
    """
    fails = []
    for m in re.finditer(r'"\s*\n\s*"', src):
        line = src[:m.start()].count("\n") + 1
        fails.append(
            f"{script.name}:{line}: adjacent string literals across lines -- "
            f"GDScript needs an explicit `+`, or the whole script fails to parse"
        )
    return fails


def check_control_bytes(script: Path, raw: str):
    """Flag a raw control byte (NUL and friends) sitting in the source text.

    `Icons.gd` shipped a literal NUL byte inside a string literal --
    `const _SEP: String = "<NUL>"` -- meant as "a character that cannot appear
    in a real key or salt". The INTENT was fine; a raw NUL between the quotes
    is not. GDScript's lexer cannot terminate a string containing one, so it
    reports `Unterminated string` even though the quotes visibly balance, and
    the whole script -- and everything that imports it -- fails to load. No
    static check here had ever run a real GDScript grammar over the source, so
    this sat invisible through every session until someone actually pressed F5
    (Session 42; `CLAUDE.md` already names this exact gap: nothing in a session
    environment can load a scene through the real engine, so a defect like this
    stays invisible until a human's machine hits it).

    Tab, newline and carriage return are legitimate inside a source file and
    are excluded. Everything else in the C0 control range (0x00-0x1F) has no
    business appearing literally in GDScript text -- the correct way to put a
    control character INTO a string is the `\\uXXXX` escape, which is what this
    fix uses and what this check does not flag.
    """
    fails = []
    for i, ch in enumerate(raw):
        code = ord(ch)
        if code < 0x20 and ch not in "\t\n\r":
            line = raw[:i].count("\n") + 1
            fails.append(
                f"{script.name}:{line}: raw control byte 0x{code:02x} in the source -- "
                f"a literal control character inside a string literal parses as "
                f"`Unterminated string`, not as the character; use a \\u{code:04x} "
                f"escape instead"
            )
    return fails


def check_python_docstrings(script: Path, src: str):
    """Flag Python-style \"\"\"docstrings\"\"\" -- valid GDScript, and dead weight.

    GDScript does have triple-quoted multiline strings, so this PARSES. What it
    does not have is docstrings: a string literal alone on a line is a
    standalone expression, so the engine evaluates it, discards it, and logs
    STANDALONE_EXPRESSION. Three of these sat in the client -- two of them in
    ApiClient.gd, an autoload -- putting warnings into the Output panel that
    docs/F5_CHECKLIST.md tells you to read for the `Style:` font canary. A
    procedure that says "check Output for warnings" is worth less for every
    warning that is already there and is fine.

    `##` is the real doc comment, is what the other ~145 doc lines in this
    client use, and is what Godot's own documentation tooling reads.
    """
    fails = []
    for i, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith('"""'):
            fails.append(
                f"{script.name}:{i}: Python-style docstring -- GDScript parses "
                f"this as a standalone expression and warns; use `##` instead"
            )
    return fails


def check_scene_comments(path: Path):
    """Flag `#` comment lines in a .tscn -- they are not comments to Godot.

    The scene format comments with `;`. A line starting with `#` is garbage to
    the TSCN parser, and the node declared immediately after one is silently
    DROPPED from the loaded scene: `$Path` returns null at runtime and the
    first method call on it fails with "Cannot call method ... on a null value".

    This checker reads `[node name=...]` lines with a regex and so used to see
    those nodes perfectly well -- it passed Interrogation.tscn while every one
    of its five sub-panels was missing at runtime. Reading the file is not the
    same as loading it, and this is the gap.
    """
    fails = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("#"):
            fails.append(
                f"{path.name}:{i}: `#` is not a comment in a .tscn (use `;`) -- "
                f"the next node declared after it is dropped when the scene loads"
            )
    return fails


def declared_variations():
    """Every theme type variation Style.gd declares, as a set of names.

    Read out of the GDScript rather than out of a .tres, because the theme is
    built in code -- see Style.gd's own header for why. A regex over
    set_type_variation() calls is enough: they are all literal, one per line,
    and if that ever stops being true this check fails loudly rather than
    quietly passing everything.
    """
    style = GODOT / "scripts" / "autoloads" / "Style.gd"
    if not style.exists():
        return None
    return set(re.findall(r'set_type_variation\("([^"]+)"', style.read_text()))


def check_type_variations(path: Path, declared):
    """Flag a theme_type_variation in a .tscn that no theme declares.

    This is the guard for the one part of the styling a scene has to name.
    Godot's own failure here is SILENT and mild -- an undeclared variation
    falls back to the base type, so a typo yields a label that is merely
    unstyled, with no error anywhere. Mild is exactly what makes it worth
    checking: nothing will ever draw attention to it, and "why is that one
    heading small" is a bad way to find a typo.
    """
    if declared is None:
        return []
    fails = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        m = re.match(r'theme_type_variation = &?"([^"]+)"', line.strip())
        if m and m.group(1) not in declared:
            fails.append(
                f"{path.name}:{i}: theme_type_variation \"{m.group(1)}\" is not "
                f"declared in Style.gd -- Godot silently falls back to the base "
                f"type, so this renders unstyled with no error. "
                f"Declared: {', '.join(sorted(declared))}"
            )
    return fails


def check(scene: Path):
    comment_fails = check_scene_comments(scene)

    nodes, script_rel = parse_scene(scene)
    if not script_rel:
        return comment_fails, []

    script = GODOT / script_rel
    if not script.exists():
        return comment_fails + [f"{scene.name}: script {script_rel} does not exist"], []

    src = strip_comments(script.read_text())
    fails, notes = list(comment_fails), []

    # 1 + 2 -- every $Path the script dereferences must exist, with the right type.
    typed = {}   # node_path -> declared type, from @onready declarations
    for m in re.finditer(r'@onready\s+var\s+(\w+)\s*:\s*(\w+)\s*=\s*\$"?([^"\s#]+)"?', src):
        typed[m.group(3)] = (m.group(1), m.group(2))

    for m in re.finditer(r'\$"([^"]+)"|\$([A-Za-z_][\w/]*)', src):
        node_path = m.group(1) or m.group(2)
        if node_path not in nodes:
            fails.append(f"{script_rel}: ${node_path} does not exist in {scene.name}")
        elif node_path in typed:
            var_name, declared = typed[node_path]
            actual = nodes[node_path]
            if declared != actual:
                fails.append(
                    f"{script_rel}: {var_name} declared {declared} but "
                    f"{node_path} is a {actual} in {scene.name}"
                )

    # 3 -- interactive controls the script never mentions.
    for node_path, ntype in sorted(nodes.items()):
        if ntype not in INTERACTIVE:
            continue
        leaf = node_path.rsplit("/", 1)[-1]
        if f"${node_path}" not in src and f'$"{node_path}"' not in src:
            notes.append(f"{scene.name}: {ntype} '{leaf}' is never referenced by {script_rel}")

    return fails, notes


# Members every autoload inherits from Node/Object. Referencing one of these is
# legitimate and must not be reported as missing.
INHERITED = {
    "name", "owner", "multiplayer", "process_mode", "call", "call_deferred",
    "connect", "disconnect", "emit_signal", "free", "queue_free", "get_node",
    "has_node", "add_child", "remove_child", "get_tree", "set", "get",
    "has_method", "has_signal", "is_inside_tree", "notification",
}


def parse_autoloads():
    """Return {autoload_name: (funcs, members)} as declared in project.godot."""
    proj = (GODOT / "project.godot").read_text()
    declared = dict(re.findall(
        r'^(\w+)="\*res://scripts/autoloads/(\w+)\.gd"', proj, re.M))

    out = {}
    for autoload_name, stem in declared.items():
        path = GODOT / "scripts" / "autoloads" / f"{stem}.gd"
        if not path.exists():
            continue
        src = path.read_text()

        funcs = {}
        for m in re.finditer(r"^func\s+(\w+)\s*\(([^)]*)\)", src, re.M):
            args = [a for a in m.group(2).split(",") if a.strip()]
            required = sum(1 for a in args if "=" not in a)
            funcs[m.group(1)] = (required, len(args))

        members = set(re.findall(r"^(?:@export\s+)?var\s+(\w+)", src, re.M))
        members |= set(re.findall(r"^const\s+(\w+)", src, re.M))
        members |= set(re.findall(r"^signal\s+(\w+)", src, re.M))
        # Enums are referenced as GameState.Phase.WITNESS -- the enum name is
        # the member. Missing these produced false positives the first time
        # this check was run by hand.
        members |= set(re.findall(r"^enum\s+(\w+)", src, re.M))
        members |= INHERITED

        out[autoload_name] = (funcs, members)
    return out


def _split_args(call_text: str) -> int:
    """Count top-level comma-separated arguments, ignoring nested (), [], {}."""
    depth = 0
    count = 1 if call_text.strip() else 0
    for ch in call_text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count


def _matching_paren(src: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(src)):
        if src[i] in "([{":
            depth += 1
        elif src[i] in ")]}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def check_autoload_calls(autoloads):
    fails = []
    for script in sorted((GODOT / "scripts" / "ui").glob("*.gd")):
        src = strip_comments(script.read_text())
        rel = f"scripts/ui/{script.name}"
        for autoload, (funcs, members) in autoloads.items():
            for m in re.finditer(rf"\b{autoload}\.(\w+)", src):
                member = m.group(1)
                after = src[m.end():]
                is_call = after.lstrip().startswith("(") and after[:1] == "("

                if is_call:
                    if member not in funcs:
                        if member not in members:
                            fails.append(f"{rel}: {autoload}.{member}() is not defined")
                        continue
                    close = _matching_paren(src, m.end())
                    if close == -1:
                        continue
                    given = _split_args(src[m.end() + 1:close])
                    required, total = funcs[member]
                    if given < required or given > total:
                        fails.append(
                            f"{rel}: {autoload}.{member}() called with {given} "
                            f"arg(s), definition takes {required}-{total}"
                        )
                elif member not in members and member not in funcs:
                    fails.append(f"{rel}: {autoload}.{member} is not a member")
    return fails


def check_scripts():
    """Run the parse-level checks over EVERY .gd, not just scene scripts.

    They used to run only on the script a .tscn names, which left the four
    autoloads, MysteryData.gd and the theme scripts unchecked -- and an
    autoload is the worst place to miss one, since nothing at all runs if it
    fails to parse.
    """
    fails = []
    for script in sorted(GODOT.rglob("*.gd")):
        raw = script.read_text()
        fails.extend(check_control_bytes(script, raw))
        fails.extend(check_python_docstrings(script, raw))
        fails.extend(check_implicit_concat(script, strip_comments(raw)))
    return fails


def main():
    all_fails, all_notes = [], []
    scenes = sorted((GODOT / "scenes").rglob("*.tscn"))
    variations = declared_variations()
    for scene in scenes:
        f, n = check(scene)
        all_fails += f
        all_notes += n
        all_fails += check_type_variations(scene, variations)

    autoloads = parse_autoloads()
    all_fails += check_autoload_calls(autoloads)
    all_fails += check_scripts()

    scripts = sorted(GODOT.rglob("*.gd"))
    print(f"Checked {len(scenes)} scenes, {len(autoloads)} autoloads "
          f"and {len(scripts)} scripts.\n")
    if all_notes:
        print(f"NOTES ({len(all_notes)}) -- unreferenced interactive controls:")
        for n in all_notes:
            print(f"  · {n}")
        print()
    if all_fails:
        print(f"FAILURES ({len(all_fails)}):")
        for f in all_fails:
            print(f"  ✗ {f}")
        return 1
    print("No failures: every $NodePath resolves, every declared type matches, "
          "every autoload call exists with a valid arity, every "
          "theme_type_variation is declared in Style.gd, and no script "
          "carries a parse-level defect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
