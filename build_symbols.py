"""
Genera AI Symbols: una fuente que solo contiene los iconos de IA, para usarla como
fallback detrás de cualquier fuente en la lista del terminal, por ejemplo en
Windows Terminal: "font": {"face": "CaskaydiaCove Nerd Font, AI Symbols"}.

- Iconos y versiones de upstream: icons.toml (GLYPH_MAP, COLOR_ICONS, COLOR_VARIANTS)
- Misma geometría que patch_all.py (icon_transform)
- Métricas verticales y celda leídas de la fuente de referencia (CaskaydiaCove Nerd Font)
- AI Symbols:      iconos de UPM x UPM, avance = 1 celda (desbordan, como en NF)
  AI Symbols Mono: iconos de 1 celda, centrados
- Contorno monocromo de devicons.ttf como glifo base: sin soporte de color se ve
  igual que en la fuente parcheada y toma el color del tema
- COLOR_VARIANTS: versiones a color de iconos que Nerd Fonts ya tiene en monocromo
  (nf-cod-claude, nf-dev-pytorch...), en su propio bloque y solo en AI Symbols
- COLR v0 + CPAL para COLOR_ICONS y COLOR_VARIANTS, con los colores del sprite SVG de devicons:
  * un solo color  -> una capa con el contorno completo
  * degradados / mallas / desenfoques -> el contorno troceado en GRID x GRID teselas,
    cada una con el color medio del SVG renderizado en esa zona (Windows Terminal
    solo dibuja COLR v0, sin degradados); los colores se reducen a MAX_COLORS y las
    teselas del mismo color se unen en una sola capa

Uso:
    python build_symbols.py --devicons-pkg <carpeta package del npm devicons> \
        --reference <CaskaydiaCoveNerdFont-Regular.ttf> [-o out]
"""
import argparse
import io
import os
import re
import sys

import pathops
import resvg_py
from fontTools.colorLib.builder import buildCOLR, buildCPAL
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from PIL import Image

from icons import ALL_ICONS, COLOR_ICONS, COLOR_VARIANTS, DEVICONS, SYMBOLS_FAMILIES as FAMILIES
from patch_all import GLYPH_PREFIX, icon_transform

GRID = 32            # teselas por lado
RENDER = 640         # px del render del SVG (20 px por tesela)
OVERLAP = 0.15       # fracción de tesela que se solapa con la vecina (evita rayas)
SOLID_TOLERANCE = 6  # diferencia máx. por canal (0-255) para tratar el icono como un solo color
MAX_COLORS = 48      # colores por icono: las teselas de un mismo color se unen en una capa

VERSION = "1.000"


def reference_metrics(path):
    """(UPM, ascent, descent, celda) de la fuente de referencia; NF y Mono son iguales."""
    font = TTFont(path)
    os2 = font["OS/2"]
    metrics = (font["head"].unitsPerEm, os2.sTypoAscender, os2.sTypoDescender,
               font["hmtx"][font.getBestCmap()[ord("M")]][0])
    font.close()
    return metrics


def sprite_svg(sprite, name):
    """SVG independiente de un <symbol> del sprite de devicons."""
    m = re.search(r'<symbol([^>]*?)\bid="%s"([^>]*)>(.*?)</symbol>' % re.escape(name), sprite, re.S)
    if not m:
        raise KeyError(f"{name} no está en sprite-symbol.svg")
    view_box = re.search(r'viewBox="([^"]+)"', m.group(1) + m.group(2)).group(1)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{m.group(3)}</svg>', view_box


def render(svg):
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=RENDER, height=RENDER))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def mean_color(img, box):
    """Media ponderada por alfa de los píxeles de `box`; None si es transparente."""
    r = g = b = a = 0
    for pr, pg, pb, pa in img.crop(box).get_flattened_data():
        r, g, b, a = r + pr * pa, g + pg * pa, b + pb * pa, a + pa
    return (round(r / a), round(g / a), round(b / a)) if a else None


def rect(x0, y0, x1, y1):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()
    return p


def to_glyph(path, matrix):
    pen = TTGlyphPen(None)
    path.draw(TransformPen(Cu2QuPen(pen, max_err=1.0, reverse_direction=False), matrix))
    return pen.glyph()


def color_layers(dev, name, sprite):
    """[(pathops.Path en unidades de devicons, (r, g, b))] del icono a color."""
    dev_upm = dev["head"].unitsPerEm
    outline = pathops.Path()
    dev.getGlyphSet()[name].draw(outline.getPen())

    svg, view_box = sprite_svg(sprite, name)
    if [float(v) for v in view_box.split()][2:] != [600.0, 600.0]:
        # devicons dibuja cada SVG de 600x600 sobre su em de 1000 (y invertida)
        raise ValueError(f"{name}: viewBox inesperado {view_box}")
    img = render(svg)
    px = RENDER / dev_upm  # px por unidad de devicons

    x0, y0, x1, y1 = outline.bounds
    tw, th = (x1 - x0) / GRID, (y1 - y0) / GRID
    tiles = []
    for j in range(GRID):
        for i in range(GRID):
            tx0, ty0 = x0 + i * tw, y0 + j * th
            o = OVERLAP * min(tw, th)
            piece = pathops.op(outline, rect(tx0 - o, ty0 - o, tx0 + tw + o, ty0 + th + o),
                               pathops.PathOp.INTERSECTION)
            if abs(piece.area) < 1:
                continue
            box = (int(tx0 * px), int((dev_upm - ty0 - th) * px),
                   int((tx0 + tw) * px) + 1, int((dev_upm - ty0) * px) + 1)
            tiles.append((piece, mean_color(img, box)))

    known = [c for _, c in tiles if c]
    if not known:
        raise ValueError(f"{name}: el SVG no tiene píxeles bajo el contorno")
    avg = tuple(round(sum(c[k] for c in known) / len(known)) for k in range(3))
    if all(max(abs(c[k] - avg[k]) for k in range(3)) <= SOLID_TOLERANCE for c in known):
        return [(outline, avg)]

    # Paleta reducida del icono; las teselas del mismo color se unen en una capa
    colors = [c or avg for _, c in tiles]
    swatch = Image.new("RGB", (len(colors), 1))
    swatch.putdata(colors)
    quant = swatch.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    flat = quant.getpalette()
    groups = {}
    for (piece, _), idx in zip(tiles, quant.get_flattened_data()):
        groups.setdefault(tuple(flat[idx * 3:idx * 3 + 3]), []).append(piece)
    layers = []
    for rgb, pieces in groups.items():
        merged = pathops.Path()
        pen = merged.getPen()
        for piece in pieces:
            piece.draw(pen)
        merged.simplify()
        layers.append((merged, rgb))
    return layers


def build(dev, sprite, kind, metrics, out_dir):
    upm, ascent, descent, cell = metrics
    family = FAMILIES[kind]
    ps_family = family.replace(" ", "")
    center_y = (ascent + descent) / 2
    gs = dev.getGlyphSet()

    glyphs = {".notdef": TTGlyphPen(None).glyph(), "space": TTGlyphPen(None).glyph()}
    cmap = {0x20: "space"}
    color_glyphs, palette, palette_index = {}, [], {}

    for cp, src_name in sorted(ALL_ICONS.items()):
        name = GLYPH_PREFIX + src_name
        matrix, _ = icon_transform(dev, src_name, upm, center_y, cell, kind)
        pen = TTGlyphPen(None)
        gs[src_name].draw(TransformPen(pen, matrix))
        glyphs[name] = pen.glyph()
        cmap[cp] = name

        if src_name not in COLOR_ICONS and cp not in COLOR_VARIANTS:
            continue
        layers = []
        for k, (path, rgb) in enumerate(color_layers(dev, src_name, sprite)):
            layer = f"{name}.c{k:03d}"
            glyphs[layer] = to_glyph(path, matrix)
            if rgb not in palette_index:
                palette_index[rgb] = len(palette)
                palette.append(tuple(v / 255 for v in rgb) + (1.0,))
            layers.append((layer, palette_index[rgb]))
        color_glyphs[name] = layers

    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(list(glyphs))
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]
    hmetrics = {}
    for name in glyphs:
        glyf[name].recalcBounds(glyf)
        hmetrics[name] = (cell, getattr(glyf[name], "xMin", 0))
    fb.setupHorizontalMetrics(hmetrics)
    fb.setupHorizontalHeader(ascent=ascent, descent=descent)
    fb.setupNameTable({
        "familyName": family,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"{ps_family}-Regular {VERSION}",
        "fullName": f"{family} Regular",
        "psName": f"{ps_family}-Regular",
        "version": f"Version {VERSION}; devicons {DEVICONS}",
        "licenseDescription": "Icons from devicons (MIT). Logos are trademarks of their respective owners.",
        "licenseInfoURL": "https://github.com/vorillaz/devicons",
    })
    fb.setupOS2(
        sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
        usWinAscent=ascent, usWinDescent=-descent,
        xAvgCharWidth=cell, achVendID="NONE", fsType=0,
        panose=_panose(kind),
    )
    fb.setupPost(isFixedPitch=int(kind == "mono"))
    fb.font["COLR"] = buildCOLR(color_glyphs, version=0, glyphMap=fb.font.getReverseGlyphMap())
    fb.font["CPAL"] = buildCPAL([palette])

    out_path = os.path.join(out_dir, f"{ps_family}-Regular.ttf")
    fb.save(out_path)
    return out_path, len(glyphs), {n: len(l) for n, l in color_glyphs.items()}, len(palette)


def _panose(kind):
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    p = Panose()
    p.bFamilyType = 5         # Pictorial
    p.bProportion = 9 if kind == "mono" else 0
    return p


def main():
    ap = argparse.ArgumentParser(description="Genera la fuente AI Symbols (iconos de IA a color).")
    ap.add_argument("--devicons-pkg", required=True,
                    help=f"carpeta 'package' del npm devicons {DEVICONS} (con dist/devicons.ttf y dist/sprite-symbol.svg)")
    ap.add_argument("--reference", required=True,
                    help="CaskaydiaCove Nerd Font de la que se toman UPM, métricas verticales y celda")
    ap.add_argument("-o", "--out", default="Symbols", help="carpeta de salida (default: Symbols)")
    args = ap.parse_args()

    metrics = reference_metrics(args.reference)

    dist = os.path.join(args.devicons_pkg, "dist")
    dev = TTFont(os.path.join(dist, "devicons.ttf"))
    with open(os.path.join(dist, "sprite-symbol.svg"), encoding="utf-8") as f:
        sprite = f.read()
    missing = [n for n in ALL_ICONS.values() if n not in dev.getGlyphSet()]
    if missing:
        sys.exit(f"devicons.ttf no tiene: {', '.join(missing)}")

    os.makedirs(args.out, exist_ok=True)
    for kind in FAMILIES:
        path, n_glyphs, layers, n_colors = build(dev, sprite, kind, metrics, args.out)
        detail = ", ".join(f"{n.removeprefix(GLYPH_PREFIX)}={c}" for n, c in layers.items())
        print(f"  {os.path.basename(path)}: {n_glyphs} glifos, {n_colors} colores | capas: {detail}")
    dev.close()


if __name__ == "__main__":
    main()
