"""
Carga y valida icons.toml. Los scripts importan de aquí GLYPH_MAP, COLOR_ICONS,
COLOR_VARIANTS y las versiones de upstream. Solo usa la biblioteca estándar (Python 3.11+).

Validación: codepoints y nombres sin repetir (un mismo glifo puede repetirse con otro
recolor), dentro de [range], campos obligatorios.

Uso:
    python icons.py check                 valida y muestra el siguiente codepoint libre
    python icons.py readme [--check]      regenera las secciones generadas del README
    python icons.py bump [--nerd-fonts X] [--devicons Y]
                                          cambia las versiones de upstream en icons.toml
"""
import argparse
import os
import re
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
TOML_PATH = os.path.join(HERE, "icons.toml")
README_PATH = os.path.join(HERE, "README.md")


def _cp(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-F]{4,5}", value):
        raise ValueError(f"{where}: codepoint {value!r} debe ser hexadecimal en mayúsculas, p. ej. \"E00B\"")
    return int(value, 16)


def load(path=TOML_PATH):
    with open(path, "rb") as f:
        data = tomllib.load(f)

    upstream = data["upstream"]
    start, end = _cp(data["range"]["start"], "range.start"), _cp(data["range"]["end"], "range.end")
    icons, variants = data.get("icon", []), data.get("variant", [])
    errors, seen_cp, seen_name = [], {}, {}

    for kind, entries, required in (("icon", icons, ("cp", "name", "label")),
                                    ("variant", variants, ("cp", "name", "label", "nf_cp", "nf_name"))):
        for i, e in enumerate(entries):
            where = f"{kind}[{i}] {e.get('name', '?')}"
            missing = [k for k in required if k not in e]
            if missing:
                errors.append(f"{where}: faltan {', '.join(missing)}")
                continue
            try:
                e["cp"] = _cp(e["cp"], where)
                if kind == "variant":
                    e["nf_cp"] = _cp(e["nf_cp"], where)
            except ValueError as err:
                errors.append(str(err))
                continue
            if not start <= e["cp"] <= end:
                errors.append(f"{where}: U+{e['cp']:04X} fuera del rango U+{start:04X}–{end:04X}")
            if e["cp"] in seen_cp:
                errors.append(f"{where}: U+{e['cp']:04X} repetido (también en {seen_cp[e['cp']]})")
            recolor = e.get("recolor", {})
            if not isinstance(recolor, dict) or not all(
                    re.fullmatch(r"#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?", c) for kv in recolor.items() for c in kv):
                errors.append(f"{where}: recolor debe ser una tabla {{ \"#rrggbb\" = \"#rrggbb\" }}")
                recolor = {}
            key = (e["name"], tuple(sorted(recolor.items())))
            if key in seen_name:
                errors.append(f"{where}: glifo repetido (también en {seen_name[key]})")
            if not isinstance(e.get("color", False), bool):
                errors.append(f"{where}: color debe ser true o false")
            seen_cp[e["cp"]], seen_name[key] = where, where

    if errors:
        raise ValueError("icons.toml no es válido:\n  " + "\n  ".join(errors))
    return upstream, (start, end), icons, variants


UPSTREAM, RANGE, ICONS, VARIANTS = load()
NERD_FONTS = UPSTREAM["nerd_fonts"]
DEVICONS = UPSTREAM["devicons"]

# Codepoint -> nombre del glifo en devicons (dist/devicons.ttf)
GLYPH_MAP = {e["cp"]: e["name"] for e in ICONS}
# Iconos de GLYPH_MAP con capas a color en AI Symbols
COLOR_ICONS = {e["name"] for e in ICONS if e.get("color")}
# Versiones a color de iconos de Nerd Fonts; solo en AI Symbols, siempre a color
COLOR_VARIANTS = {e["cp"]: e["name"] for e in VARIANTS}
ALL_ICONS = {**GLYPH_MAP, **COLOR_VARIANTS}
# Colores del SVG que se sustituyen antes de renderizarlo (p. ej. letras de AWS en blanco)
RECOLOR = {e["cp"]: e["recolor"] for e in ICONS + VARIANTS if e.get("recolor")}
# Nombre del glifo en AI Symbols; los recoloreados llevan el codepoint para no chocar
GLYPH_NAMES = {cp: f"{name}.u{cp:04X}" if cp in RECOLOR else name for cp, name in ALL_ICONS.items()}

# Familias de AI Symbols (build_symbols.py y verify_symbols.py)
SYMBOLS_FAMILIES = {"nf": "AI Symbols", "mono": "AI Symbols Mono"}


# --- README -------------------------------------------------------------------------

def _readme_sections():
    nf_url = f"https://github.com/ryanoasis/nerd-fonts/releases/download/v{NERD_FONTS}/CascadiaCode.tar.xz"
    dev_url = f"https://registry.npmjs.org/devicons/-/devicons-{DEVICONS}.tgz"

    glyphs = ["| Codepoint | Icon | devicons glyph |", "|-----------|------|----------------|"]
    for e in ICONS:
        if "group" in e:
            glyphs.append(f"| **{e['group']}** | | |")
        glyphs.append(f"| `U+{e['cp']:04X}` | {e['label']} | `{e['name']}` |")

    variants = ["| Color (AI Symbols) | Monochrome (Nerd Fonts) | Icon |",
                "|--------------------|-------------------------|------|"]
    for e in VARIANTS:
        note = f" ({e['note']})" if "note" in e else ""
        variants.append(f"| `U+{e['cp']:04X}` | `U+{e['nf_cp']:04X}` `{e['nf_name']}` | {e['label']}{note} |")

    color = ", ".join(e["label"] for e in ICONS if e.get("color"))
    mono = ", ".join(e["label"] for e in ICONS if not e.get("color"))
    symbols = "\n".join([
        "| Icon | In AI Symbols |",
        "|------|---------------|",
        f"| {color} | **Color** (brand colors from the devicons SVGs) |",
        f"| {mono} | Monochrome: they take your theme's color, like any Nerd Fonts icon. "
        "Black logos, or logos whose monochrome outline does not match the color artwork |",
    ])

    first, last = min(GLYPH_MAP), max(GLYPH_MAP)
    return {
        "upstream": f"[CaskaydiaCove Nerd Font](https://github.com/ryanoasis/nerd-fonts) **v{NERD_FONTS}** "
                    "extended with AI tool icons that Nerd Fonts does not ship yet, taken from "
                    f"[devicons](https://github.com/vorillaz/devicons) **v{DEVICONS}**.",
        "glyphs": "\n".join(glyphs),
        "check": f"```powershell\n0x{first:04X}..0x{last:04X} | ForEach-Object {{ \"$([char]$_)  U+{{0:X4}}\" -f $_ }}\n```",
        "variants": "\n".join(variants),
        "symbols": symbols,
        "sources": f"```text\nCaskaydiaCove Nerd Font v{NERD_FONTS}  {nf_url}\n"
                   f"devicons v{DEVICONS}                {dev_url}\n```",
    }


def render_readme(text):
    for name, body in _readme_sections().items():
        pattern = re.compile(rf"(<!-- generated:{name} -->\n).*?(\n<!-- /generated:{name} -->)", re.S)
        if not pattern.search(text):
            raise ValueError(f"README.md no tiene la sección <!-- generated:{name} -->")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)
    return text


# --- CLI ----------------------------------------------------------------------------

def _bump(nerd_fonts, devicons):
    with open(TOML_PATH, encoding="utf-8") as f:
        text = f.read()
    for key, value in (("nerd_fonts", nerd_fonts), ("devicons", devicons)):
        if value:
            text, n = re.subn(rf'^({key} = )"[^"]*"', rf'\g<1>"{value}"', text, count=1, flags=re.M)
            if not n:
                sys.exit(f"icons.toml: no se encontró {key}")
    with open(TOML_PATH, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description="Valida icons.toml y genera el README.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="valida icons.toml")
    readme = sub.add_parser("readme", help="regenera las secciones generadas del README")
    readme.add_argument("--check", action="store_true", help="falla si el README no está al día")
    bump = sub.add_parser("bump", help="cambia las versiones de upstream")
    bump.add_argument("--nerd-fonts")
    bump.add_argument("--devicons")
    args = ap.parse_args()

    if args.cmd == "check":
        used = set(ALL_ICONS)
        free = next((cp for cp in range(RANGE[0], RANGE[1] + 1) if cp not in used and cp > max(GLYPH_MAP)), None)
        print(f"OK: {len(GLYPH_MAP)} iconos, {len(COLOR_ICONS)} a color, {len(COLOR_VARIANTS)} variantes "
              f"| Nerd Fonts {NERD_FONTS}, devicons {DEVICONS}")
        print(f"Siguiente codepoint libre para [[icon]]: U+{free:04X}" if free else "Rango lleno")
    elif args.cmd == "readme":
        with open(README_PATH, encoding="utf-8") as f:
            old = f.read()
        new = render_readme(old)
        if args.check:
            if new != old:
                sys.exit("README.md no está al día: corre `python icons.py readme`")
            print("README.md al día")
        elif new != old:
            with open(README_PATH, "w", encoding="utf-8") as f:
                f.write(new)
            print("README.md actualizado")
    elif args.cmd == "bump":
        _bump(args.nerd_fonts, args.devicons)


if __name__ == "__main__":
    main()
