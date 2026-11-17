"""
Parchea fuentes de Nerd Fonts (las familias [[font]] de icons.toml: CaskaydiaCove,
JetBrainsMono, FiraCode, MesloLG, Hack...) con iconos de IA de devicons que Nerd Fonts
todavía no incluye. Iconos y versiones de upstream: icons.toml.

- Escala por em de devicons (como font-patcher), no por glifo, para conservar
  las proporciones relativas entre iconos
- NF:    caja de UPM x UPM, avance = 1 celda (el icono desborda, igual que nf-cod-*)
- Mono:  caja de 1 celda, centrada; avance = 1 celda (sigue siendo monoespaciada)
- Propo: caja de UPM x UPM; avance = ancho del icono
- Centra verticalmente en (sTypoAscender + sTypoDescender) / 2
- Inserta en todas las subtablas cmap Unicode (formato 4 y 12)
- Agrega " AI" a la familia y "AI" al nombre PostScript. Si el nameID 1 de algún peso
  pasa de 31 caracteres, toda esa familia usa el nombre corto ('Nerd Font Mono' ->
  'NFM') y, si aún no cabe, se abrevia el peso ('ExtraLight' -> 'ExtLt')
- Se niega a parchear si la fuente ya tiene glifos en el rango de icons.toml

Uso:
    python patch_all.py <carpeta_ttf> --devicons <devicons.ttf> [-o Patched]
"""
import argparse
import glob
import os
import re
import sys

from fontTools.pens.boundsPen import ControlBoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from icons import DEVICONS, GLYPH_MAP, NERD_FONTS, RANGE

GLYPH_PREFIX = "ai-"
FAMILY_SUFFIX = " AI"
PS_SUFFIX = "AI"
FILE_SUFFIX = "-AI"
VERSION_NOTE = f"; AI icons (devicons {DEVICONS})"
# Tablas que dependen de numGlyphs y quedarían inválidas al agregar glifos
DROP_TABLES = ("hdmx", "LTSH", "VDMX")
# Límite del nameID 1 en apps antiguas (GDI)
MAX_FAMILY = 31
# Abreviaturas tomadas de las tablas de font-patcher (bin/scripts/name_parser/
# FontnameTools.py de Nerd Fonts): modificador + peso, como el 'SemBd' de FiraCode, y los
# pesos sueltos que upstream ya abrevia ('Med', 'Ret'). No es el algoritmo de font-patcher.
STYLE_MODIFIERS = {"Extra": "Ext", "Semi": "Sem", "Demi": "Dem", "Ultra": "Ult"}
STYLE_WEIGHTS = {"Bold": "Bd", "Light": "Lt", "Black": "Blk", "Heavy": "Hv", "Thin": "Th"}
STYLE_STANDALONE = {"Medium": "Med", "Retina": "Ret"}
STYLE_COMPOUND = re.compile(rf"\b({'|'.join(STYLE_MODIFIERS)})({'|'.join(STYLE_WEIGHTS)})\b")
SHORT_FAMILIES = ((" Nerd Font Mono", " NFM"), (" Nerd Font Propo", " NFP"), (" Nerd Font", " NF"))


def variant(font):
    """'mono', 'propo' o 'nf' según los nombres y post.isFixedPitch."""
    family = " ".join(r.toUnicode() for r in font["name"].names if r.nameID in (1, 16))
    if "Propo" in family or "NFP" in family:
        return "propo"
    if font["post"].isFixedPitch:
        return "mono"
    return "nf"


def icon_transform(dev, src_name, upm, center_y, cell, kind):
    """Devuelve (matriz afín, avance) que lleva el glifo de devicons a la fuente destino."""
    gs = dev.getGlyphSet()
    dev_upm = dev["head"].unitsPerEm

    # Bounds por puntos de control: es lo que usa TrueType para el bbox del glifo
    bounds = ControlBoundsPen(gs)
    gs[src_name].draw(bounds)
    x0, y0, x1, y1 = bounds.bounds

    # Escala por em; si el dibujo se sale del em (p. ej. microsoft-copilot: -1..1009),
    # se reduce lo justo para que quepa en la caja
    box = cell if kind == "mono" else upm
    scale = box / max(dev_upm, x1 - x0, y1 - y0)

    # Vertical: centro del em de devicons -> centro de la celda destino. Si el dibujo
    # es más alto que el em (p. ej. kiro-icon: -8..1011) se centra el dibujo, si no
    # se saldría de la caja por el lado más largo
    dev_center = (dev["hhea"].ascent + dev["hhea"].descent) / 2
    if y1 - y0 > dev_upm:
        dev_center = (y0 + y1) / 2
    dy = center_y - dev_center * scale
    # Horizontal: centrado en la celda (Mono) o alineado al inicio (NF/Propo)
    if kind == "mono":
        dx = (cell - (x0 + x1) * scale) / 2
    else:
        dx = -x0 * scale

    advance = round((x1 - x0) * scale) if kind == "propo" else cell
    return (scale, 0, 0, scale, dx, dy), advance


def build_glyph(dev, src_name, font, kind):
    """Devuelve (glyph, avance) del glifo de devicons escalado y posicionado para `font`."""
    os2 = font["OS/2"]
    cell = font["hmtx"][font.getBestCmap()[ord("M")]][0]
    center_y = (os2.sTypoAscender + os2.sTypoDescender) / 2
    matrix, advance = icon_transform(dev, src_name, font["head"].unitsPerEm, center_y, cell, kind)

    pen = TTGlyphPen(None)
    dev.getGlyphSet()[src_name].draw(TransformPen(pen, matrix))
    return pen.glyph(), advance


def short_style(style):
    """'ExtraLight' -> 'ExtLt', 'SemiBold' -> 'SemBd', 'Medium' -> 'Med'."""
    style = STYLE_COMPOUND.sub(lambda m: STYLE_MODIFIERS[m.group(1)] + STYLE_WEIGHTS[m.group(2)], style)
    for long, short in STYLE_STANDALONE.items():
        style = re.sub(rf"\b{long}\b", short, style)
    return style


def short_family(family):
    """'FiraCode Nerd Font Mono' -> 'FiraCode NFM', como los nombres cortos de Nerd Fonts."""
    for long, short in SHORT_FAMILIES:
        if family.endswith(long):
            return family[: -len(long)] + short
    return family


def family_bases(names):
    """Familias con las que empiezan los nombres, la más larga primero: la tipográfica
    (nameID 16, 'CaskaydiaCove Nerd Font Mono') y, si la hay, la corta ('CaskaydiaCove NFM')."""
    bases = {r.toUnicode() for r in names.names if r.nameID == 16} or {names.getDebugName(1)}
    return sorted(bases, key=len, reverse=True)


def overflows(font):
    """(familia tipográfica, True si algún nameID 1 con el sufijo pasa de MAX_FAMILY)."""
    names = font["name"]
    bases = family_bases(names)
    over = False
    for record in names.names:
        if record.nameID == 1:
            s = record.toUnicode()
            base = next((b for b in bases if s.startswith(b)), s)
            over |= len(base + FAMILY_SUFFIX + s[len(base):]) > MAX_FAMILY
    return bases[0], over


def rename(font, short_families=()):
    """Inserta el sufijo tras la familia: 'CaskaydiaCove NFM SemiLight' -> 'CaskaydiaCove NFM AI SemiLight'.

    El nameID 1 no puede pasar de 31 caracteres. Si algún peso de una familia tipográfica no
    cabe (está en `short_families`), todos sus pesos usan la familia corta, como hace Nerd
    Fonts con CaskaydiaCove: 'FiraCode NFM AI', 'FiraCode NFM AI Light'. Así la familia no
    queda con nombres largos y cortos mezclados. Si aun así no cabe, se abrevia el peso:
    'JetBrainsMonoNL NFM AI ExtLt'."""
    names = font["name"]
    bases = family_bases(names)
    shorten = bases[0] in short_families
    had_typographic = any(r.nameID == 16 for r in names.names)

    for record in list(names.names):
        s = record.toUnicode()
        if record.nameID in (1, 3, 4, 16):
            for base in bases:
                if s.startswith(base) and not s.startswith(base + FAMILY_SUFFIX):
                    new = base + FAMILY_SUFFIX + s[len(base):]
                    if record.nameID == 1:
                        if shorten:
                            new = short_family(base) + FAMILY_SUFFIX + s[len(base):]
                            if not had_typographic:
                                # Sin nameID 16 la familia tipográfica es el nameID 1: se conserva
                                # completa para que no se separe del resto de pesos
                                names.setName(base + FAMILY_SUFFIX, 16, record.platformID,
                                              record.platEncID, record.langID)
                        if len(new) > MAX_FAMILY:
                            new = short_family(base) + FAMILY_SUFFIX + short_style(s[len(base):])
                        if len(new) > MAX_FAMILY:
                            raise ValueError(f"nameID 1 de {len(new)} caracteres (> {MAX_FAMILY}): {new!r}")
                    record.string = new
                    break
        elif record.nameID == 5:
            if not s.endswith(VERSION_NOTE):
                record.string = s + VERSION_NOTE
        elif record.nameID == 6:
            family, sep, style = s.partition("-")
            if not family.endswith(PS_SUFFIX):
                record.string = family + PS_SUFFIX + sep + style


def families_to_shorten(paths):
    """Familias tipográficas de `paths` en las que algún peso no cabe en el nameID 1."""
    short = set()
    for path in paths:
        font = TTFont(path, lazy=True)
        family, over = overflows(font)
        font.close()
        if over:
            short.add(family)
    return short


def patch_font(path, dev, out_dir, short_families=()):
    font = TTFont(path)
    cmap = font.getBestCmap()
    taken = [f"U+{cp:04X}" for cp in range(RANGE[0], RANGE[1] + 1) if cp in cmap]
    if taken:
        raise ValueError(f"el rango U+{RANGE[0]:04X}–{RANGE[1]:04X} ya tiene glifos ({', '.join(taken[:5])}"
                         f"{'...' if len(taken) > 5 else ''}); ¿fuente ya parcheada o Nerd Fonts lo ocupó?")

    kind = variant(font)
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    unicode_tables = [t for t in font["cmap"].tables if t.isUnicode() and t.format in (4, 12)]

    for cp, src_name in GLYPH_MAP.items():
        name = GLYPH_PREFIX + src_name
        glyph, advance = build_glyph(dev, src_name, font, kind)
        glyph.recalcBounds(glyf)
        # glyf.__setitem__ agrega el nombre al glyphOrder de la fuente (es la misma lista)
        glyf[name] = glyph
        hmtx[name] = (advance, glyph.xMin)
        for table in unicode_tables:
            table.cmap[cp] = name

    order = font.getGlyphOrder()
    if len(order) != len(set(order)):
        raise RuntimeError("glyphOrder con nombres duplicados")

    for tag in DROP_TABLES:
        if tag in font:
            del font[tag]

    rename(font, short_families)

    stem, ext = os.path.splitext(os.path.basename(path))
    out_path = os.path.join(out_dir, f"{stem}{FILE_SUFFIX}{ext}")
    font.save(out_path)
    font.close()
    return kind, out_path


def main():
    ap = argparse.ArgumentParser(description="Agrega iconos de IA de devicons a una familia de Nerd Fonts.")
    ap.add_argument("src", help=f"carpeta con los .ttf originales de una familia de Nerd Fonts {NERD_FONTS}")
    ap.add_argument("--devicons", required=True, help=f"ruta a devicons.ttf (npm devicons {DEVICONS}, dist/devicons.ttf)")
    ap.add_argument("-o", "--out", default="Patched", help="carpeta de salida (default: Patched)")
    args = ap.parse_args()

    dev = TTFont(args.devicons)
    missing = [n for n in GLYPH_MAP.values() if n not in dev.getGlyphSet()]
    if missing:
        sys.exit(f"devicons.ttf no tiene: {', '.join(missing)}")

    fonts = sorted(f for f in glob.glob(os.path.join(args.src, "*.ttf")) if FILE_SUFFIX not in os.path.basename(f))
    if not fonts:
        sys.exit(f"No hay .ttf sin parchear en {args.src}")

    os.makedirs(args.out, exist_ok=True)
    print(f"Fuentes: {len(fonts)}  |  Salida: {os.path.abspath(args.out)}\n")
    short_families = families_to_shorten(fonts)
    if short_families:
        print(f"Familia corta en el nameID 1: {', '.join(sorted(short_families))}\n")

    failed = 0
    for path in fonts:
        print(f"  {os.path.basename(path)} ... ", end="", flush=True)
        try:
            kind, _ = patch_font(path, dev, args.out, short_families)
            print(f"OK ({kind})")
        except Exception as e:  # sigue con las demás y reporta al final
            failed += 1
            print(f"ERROR: {e}")

    dev.close()
    print(f"\nListo. {len(fonts) - failed}/{len(fonts)} fuentes parcheadas en {os.path.abspath(args.out)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
