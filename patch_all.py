"""
Parchea las fuentes CaskaydiaCove Nerd Font con iconos de IA de devicons que Nerd Fonts
todavía no incluye. Iconos y versiones de upstream: icons.toml.

- Escala por em de devicons (como font-patcher), no por glifo, para conservar
  las proporciones relativas entre iconos
- NF:    caja de UPM x UPM, avance = 1 celda (el icono desborda, igual que nf-cod-*)
- Mono:  caja de 1 celda, centrada; avance = 1 celda (sigue siendo monoespaciada)
- Propo: caja de UPM x UPM; avance = ancho del icono
- Centra verticalmente en (sTypoAscender + sTypoDescender) / 2
- Inserta en todas las subtablas cmap Unicode (formato 4 y 12)
- Agrega " AI" a la familia y "AI" al nombre PostScript (familia <= 31 caracteres)
- Se niega a parchear si la fuente ya tiene glifos en el rango de icons.toml

Uso:
    python patch_all.py <carpeta_ttf> --devicons <devicons.ttf> [-o Patched]
"""
import argparse
import glob
import os
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


def rename(font):
    """Inserta el sufijo tras la familia: 'CaskaydiaCove NFM SemiLight' -> 'CaskaydiaCove NFM AI SemiLight'."""
    names = font["name"]
    bases = {r.toUnicode() for r in names.names if r.nameID == 16}
    if not bases:
        bases = {names.getDebugName(1)}
    bases = sorted(bases, key=len, reverse=True)

    for record in names.names:
        s = record.toUnicode()
        if record.nameID in (1, 3, 4, 16):
            for base in bases:
                if s.startswith(base) and not s.startswith(base + FAMILY_SUFFIX):
                    record.string = base + FAMILY_SUFFIX + s[len(base):]
                    break
        elif record.nameID == 5:
            if not s.endswith(VERSION_NOTE):
                record.string = s + VERSION_NOTE
        elif record.nameID == 6:
            family, sep, style = s.partition("-")
            if not family.endswith(PS_SUFFIX):
                record.string = family + PS_SUFFIX + sep + style


def patch_font(path, dev, out_dir):
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

    rename(font)

    stem, ext = os.path.splitext(os.path.basename(path))
    out_path = os.path.join(out_dir, f"{stem}{FILE_SUFFIX}{ext}")
    font.save(out_path)
    font.close()
    return kind, out_path


def main():
    ap = argparse.ArgumentParser(description="Agrega iconos de IA de devicons a CaskaydiaCove Nerd Font.")
    ap.add_argument("src", help=f"carpeta con los .ttf originales de CaskaydiaCove Nerd Font {NERD_FONTS}")
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

    failed = 0
    for path in fonts:
        print(f"  {os.path.basename(path)} ... ", end="", flush=True)
        try:
            kind, _ = patch_font(path, dev, args.out)
            print(f"OK ({kind})")
        except Exception as e:  # sigue con las demás y reporta al final
            failed += 1
            print(f"ERROR: {e}")

    dev.close()
    print(f"\nListo. {len(fonts) - failed}/{len(fonts)} fuentes parcheadas en {os.path.abspath(args.out)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
