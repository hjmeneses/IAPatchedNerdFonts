"""
Verifica las fuentes generadas por build_symbols.py.

- Todos los iconos de GLYPH_MAP y COLOR_VARIANTS en todas las subtablas cmap Unicode
- Avance = 1 celda en todos los glifos; Mono: los iconos caben en la celda
- Iconos centrados verticalmente y dentro de la caja (celda en Mono, UPM en NF)
- COLR v0 solo en COLOR_ICONS y COLOR_VARIANTS; capas que existen, dentro del icono base y con
  índices de paleta válidos
- glyphOrder sin duplicados; familia y post.isFixedPitch correctos

UPM, métricas verticales y celda se leen de la propia fuente (la celda, del avance de
"space"). Solo necesita fontTools.

Uso:
    python verify_symbols.py <carpeta_symbols>
"""
import os
import sys

from fontTools.ttLib import TTFont

from icons import ALL_ICONS, COLOR_ICONS, COLOR_VARIANTS, GLYPH_NAMES, SYMBOLS_FAMILIES as FAMILIES
from patch_all import GLYPH_PREFIX

TOLERANCE = 2  # unidades de redondeo


def bounds(glyf, name):
    g = glyf[name]
    g.recalcBounds(glyf)
    return g.xMin, g.yMin, g.xMax, g.yMax


def check(path, kind):
    errors = []
    font = TTFont(path)
    glyf, hmtx, os2 = font["glyf"], font["hmtx"], font["OS/2"]
    upm, cell = font["head"].unitsPerEm, hmtx["space"][0]
    box = cell if kind == "mono" else upm
    center_y = (os2.sTypoAscender + os2.sTypoDescender) / 2

    order = font.getGlyphOrder()
    if len(order) != len(set(order)):
        errors.append("glyphOrder con duplicados")
    if font["name"].getDebugName(1) != FAMILIES[kind]:
        errors.append(f"familia {font['name'].getDebugName(1)!r} != {FAMILIES[kind]!r}")
    if font["post"].isFixedPitch != int(kind == "mono"):
        errors.append(f"post.isFixedPitch = {font['post'].isFixedPitch}")

    for table in font["cmap"].tables:
        if table.isUnicode():
            for cp in ALL_ICONS:
                if table.cmap.get(cp) != GLYPH_PREFIX + GLYPH_NAMES[cp]:
                    errors.append(f"cmap ({table.platformID},{table.platEncID},f{table.format}) sin U+{cp:04X}")

    widths = {hmtx[n][0] for n in order if n != ".notdef"}
    if widths != {cell}:
        errors.append(f"avances distintos de la celda: {sorted(widths)}")

    for cp in ALL_ICONS:
        x0, y0, x1, y1 = bounds(glyf, GLYPH_PREFIX + GLYPH_NAMES[cp])
        if x1 - x0 > box + TOLERANCE or y1 - y0 > box + TOLERANCE:
            errors.append(f"U+{cp:04X} {x1 - x0}x{y1 - y0} excede la caja {box}")
        if kind == "mono" and (x0 < -TOLERANCE or x1 > cell + TOLERANCE):
            errors.append(f"U+{cp:04X} se sale de la celda ({x0}..{x1})")
        if y0 < center_y - box / 2 - TOLERANCE or y1 > center_y + box / 2 + TOLERANCE:
            errors.append(f"U+{cp:04X} fuera de la caja vertical ({y0}..{y1})")

    colr = font["COLR"]
    palette = font["CPAL"].palettes[0]
    color_bases = {GLYPH_PREFIX + GLYPH_NAMES[cp] for cp, n in ALL_ICONS.items()
                   if n in COLOR_ICONS or cp in COLOR_VARIANTS}
    if set(colr.ColorLayers) != color_bases:
        errors.append(f"COLR para {sorted(colr.ColorLayers)}, se esperaba {sorted(color_bases)}")
    for base, layers in colr.ColorLayers.items():
        bx0, by0, bx1, by1 = bounds(glyf, base)
        for layer in layers:
            if layer.name not in glyf:
                errors.append(f"{base}: capa {layer.name} no existe")
                continue
            if layer.colorID >= len(palette):
                errors.append(f"{base}: color {layer.colorID} fuera de la paleta ({len(palette)})")
            lx0, ly0, lx1, ly1 = bounds(glyf, layer.name)
            if lx0 < bx0 - TOLERANCE or ly0 < by0 - TOLERANCE or lx1 > bx1 + TOLERANCE or ly1 > by1 + TOLERANCE:
                errors.append(f"{base}: capa {layer.name} se sale del icono")

    font.close()
    return errors


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    failed = 0
    for kind, family in FAMILIES.items():
        path = os.path.join(sys.argv[1], f"{family.replace(' ', '')}-Regular.ttf")
        label = os.path.basename(path)
        if not os.path.exists(path):
            failed += 1
            print(f"  FALTA  {label}")
            continue
        errors = check(path, kind)
        print(f"  {'OK   ' if not errors else 'FALLA'}  {label} ({kind})")
        for e in errors:
            print(f"         - {e}")
        failed += bool(errors)

    print(f"\n{len(FAMILIES) - failed}/{len(FAMILIES)} fuentes verificadas")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
