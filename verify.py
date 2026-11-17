"""
Verifica las fuentes generadas por patch_all.py comparándolas con las originales.

- Los iconos existen en todas las subtablas cmap Unicode y en el codepoint esperado
- Mono: todos los glifos mapeados conservan el ancho de celda (sigue monoespaciada)
- NF: avance = 1 celda; Propo: avance = ancho del icono
- Iconos centrados verticalmente y dentro de la caja de referencia de Nerd Fonts
- glyphOrder sin duplicados; glifos originales intactos; nombres con " AI"
- La familia es "<subfamilia> Nerd Font[ Mono| Propo] AI" de una subfamilia de icons.toml
- Todos los pesos de una familia usan la misma familia en el nameID 1 (larga o corta)
- La fuente original tiene los iconos de Nerd Fonts de los [[variant]] de icons.toml

Uso:
    python verify.py <carpeta_originales> <carpeta_patched>
"""
import glob
import os
import sys

from fontTools.ttLib import TTFont

from icons import FONTS, GLYPH_MAP, VARIANTS
from patch_all import FAMILY_SUFFIX, FILE_SUFFIX, GLYPH_PREFIX, variant

# "<subfamilia> Nerd Font AI", "… Mono AI", "… Propo AI" (icons.toml [[font]] subfamilies)
FAMILY_NAMES = {f"{s} Nerd Font{v}{FAMILY_SUFFIX}" for f in FONTS for s in f["subfamilies"]
                for v in ("", " Mono", " Propo")}

CENTER_TOLERANCE = 2  # unidades de redondeo


def check(src_path, out_path):
    errors = []
    src, out = TTFont(src_path), TTFont(out_path)
    kind = variant(out)
    glyf, hmtx = out["glyf"], out["hmtx"]
    os2 = out["OS/2"]
    upm = out["head"].unitsPerEm
    cell = hmtx[out.getBestCmap()[ord("M")]][0]
    center_y = (os2.sTypoAscender + os2.sTypoDescender) / 2
    box = cell if kind == "mono" else upm

    order = out.getGlyphOrder()
    if len(order) != len(set(order)):
        errors.append("glyphOrder con duplicados")
    if len(order) != len(src.getGlyphOrder()) + len(GLYPH_MAP):
        errors.append(f"numGlyphs {len(order)} != {len(src.getGlyphOrder())} + {len(GLYPH_MAP)}")

    for table in out["cmap"].tables:
        if table.isUnicode() and table.format in (4, 12):
            for cp, src_name in GLYPH_MAP.items():
                if table.cmap.get(cp) != GLYPH_PREFIX + src_name:
                    errors.append(f"cmap ({table.platformID},{table.platEncID},f{table.format}) sin U+{cp:04X}")

    for cp, src_name in GLYPH_MAP.items():
        name = GLYPH_PREFIX + src_name
        g = glyf[name]
        g.recalcBounds(glyf)
        advance = hmtx[name][0]
        width, height = g.xMax - g.xMin, g.yMax - g.yMin
        if kind in ("mono", "nf") and advance != cell:
            errors.append(f"U+{cp:04X} avance {advance} != celda {cell}")
        if kind == "propo" and abs(advance - width) > CENTER_TOLERANCE:
            errors.append(f"U+{cp:04X} avance {advance} != ancho {width}")
        if width > box + CENTER_TOLERANCE or height > box + CENTER_TOLERANCE:
            errors.append(f"U+{cp:04X} {width}x{height} excede la caja {box}")
        if kind == "mono" and (g.xMin < -CENTER_TOLERANCE or g.xMax > cell + CENTER_TOLERANCE):
            errors.append(f"U+{cp:04X} se sale de la celda ({g.xMin}..{g.xMax})")
        # El em de devicons queda centrado; el dibujo puede no estarlo, pero debe caber
        # entre center_y +- box/2
        if g.yMin < center_y - box / 2 - CENTER_TOLERANCE or g.yMax > center_y + box / 2 + CENTER_TOLERANCE:
            errors.append(f"U+{cp:04X} fuera de la caja vertical ({g.yMin}..{g.yMax})")

    if kind == "mono":
        widths = {hmtx[n][0] for n in out.getBestCmap().values() if hmtx[n][0] > 0}
        if widths != {cell}:
            errors.append(f"Mono con anchos distintos: {sorted(widths)}")

    src_cmap = src.getBestCmap()
    for e in VARIANTS:
        if e["nf_cp"] not in src_cmap:
            errors.append(f"Nerd Fonts ya no tiene U+{e['nf_cp']:04X} {e['nf_name']} (variante U+{e['cp']:04X})")

    src_hmtx = src["hmtx"].metrics
    changed = [n for n in src.getGlyphOrder() if hmtx[n] != src_hmtx[n]]
    if changed:
        errors.append(f"{len(changed)} glifos originales cambiaron métricas")

    names = out["name"]
    families = {r.toUnicode() for r in names.names if r.nameID == 16} or {names.getDebugName(1)}
    typographic = max(families, key=len)
    if typographic not in FAMILY_NAMES:
        sub = typographic.split(" Nerd Font")[0]
        errors.append(f"familia {typographic!r} no está en icons.toml: agrega \"{sub}\" a `subfamilies` "
                      "de su [[font]] (¿Nerd Fonts añadió una subfamilia al .tar.xz?) y corre "
                      "`python icons.py readme`")

    legacy = set()
    for record in out["name"].names:
        s = record.toUnicode()
        if record.nameID in (1, 16) and FAMILY_SUFFIX not in s:
            errors.append(f"nameID {record.nameID} sin sufijo: {s!r}")
        if record.nameID == 1 and len(s) > 31:
            errors.append(f"nameID 1 de {len(s)} caracteres (> 31): {s!r}")
        if record.nameID == 1:
            legacy.add(s.split(FAMILY_SUFFIX)[0])

    src.close()
    out.close()
    return kind, errors, typographic, legacy


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src_dir, out_dir = sys.argv[1:]
    pairs = []
    for src_path in sorted(glob.glob(os.path.join(src_dir, "*.ttf"))):
        stem, ext = os.path.splitext(os.path.basename(src_path))
        pairs.append((src_path, os.path.join(out_dir, f"{stem}{FILE_SUFFIX}{ext}")))

    failed = 0
    legacy_by_family = {}
    for src_path, out_path in pairs:
        label = os.path.basename(out_path)
        if not os.path.exists(out_path):
            failed += 1
            print(f"  FALTA  {label}")
            continue
        kind, errors, typographic, legacy = check(src_path, out_path)
        legacy_by_family.setdefault(typographic, set()).update(legacy)
        print(f"  {'OK   ' if not errors else 'FALLA'}  {label} ({kind})")
        for e in errors:
            print(f"         - {e}")
        failed += bool(errors)

    # Todos los pesos de una familia usan la misma familia en el nameID 1 (larga o corta)
    mixed = {fam: sorted(names) for fam, names in legacy_by_family.items() if len(names) > 1}
    for fam, names in sorted(mixed.items()):
        print(f"  FALLA  {fam}: nameID 1 mezcla {', '.join(repr(n) for n in names)}")

    print(f"\n{len(pairs) - failed}/{len(pairs)} fuentes verificadas")
    sys.exit(1 if failed or mixed else 0)


if __name__ == "__main__":
    main()
