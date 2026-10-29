"""
Verifica que los iconos con brand_colors en icons.toml usen la paleta oficial de la marca.

- Los colores del SVG de devicons, con `recolor` aplicado, deben ser exactamente brand_colors.
  Así un recolor a medias (p. ej. Jupyter con texto blanco y lunas grises) falla.
- Si brand_ref es un .svg, se descarga y sus colores también deben ser brand_colors. Fíjalo a
  un commit (raw.githubusercontent.com/<org>/<repo>/<sha>/...) para que no cambie bajo los pies.
  Si es una página (p. ej. la guía de marca de AWS), solo documenta de dónde sale la paleta.

Uso:
    python verify_brand.py --devicons-pkg <carpeta package del npm devicons>
"""
import argparse
import os
import re
import sys
import urllib.request

from build_symbols import sprite_svg
from icons import BRANDED, HEX, norm_color


def colors(svg):
    return {norm_color(m.group(0)) for m in HEX.finditer(svg)}


def fmt(cs):
    return ", ".join(sorted(cs)) or "(ninguno)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--devicons-pkg", required=True,
                    help="carpeta 'package' del npm devicons (con dist/sprite-symbol.svg)")
    args = ap.parse_args()
    with open(os.path.join(args.devicons_pkg, "dist", "sprite-symbol.svg"), encoding="utf-8") as f:
        sprite = f.read()

    errors = []
    for e in BRANDED:
        where = f"U+{e['cp']:04X} {e['label']}"
        brand = {norm_color(c) for c in e["brand_colors"]}
        got = colors(sprite_svg(sprite, e["name"], e.get("recolor"))[0])
        if got != brand:
            errors.append(f"{where}: el SVG usa {fmt(got)}; la marca, {fmt(brand)}"
                          f" (sobran {fmt(got - brand)}; faltan {fmt(brand - got)})")
        ref = e.get("brand_ref", "")
        if re.search(r"\.svg$", ref, re.I):
            with urllib.request.urlopen(ref, timeout=30) as r:
                official = colors(r.read().decode("utf-8"))
            if official != brand:
                errors.append(f"{where}: brand_colors {fmt(brand)} no coincide con {ref} ({fmt(official)})")
        print(f"{where}: {fmt(brand)}" + (" (SVG oficial)" if ref.lower().endswith(".svg") else ""))

    if errors:
        sys.exit("Colores de marca:\n  " + "\n  ".join(errors))
    print(f"OK: {len(BRANDED)} iconos con la paleta de su marca")


if __name__ == "__main__":
    main()
