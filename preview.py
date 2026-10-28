"""
Genera preview.png (la imagen del README) a partir de icons.toml y las fuentes ya construidas.

- Cada [[icon]]: el glifo de la fuente parcheada (monocromo) y el de AI Symbols (a color
  si tiene color = true)
- Cada [[variant]]: el icono oficial de Nerd Fonts (nf_cp) y la versión a color de AI Symbols
- Etiqueta naranja: a color en AI Symbols; gris: monocromo también en AI Symbols

Uso:
    python preview.py --nerd-font <CaskaydiaCoveNerdFont-Regular.ttf> \
        --patched <CaskaydiaCoveNerdFontAI-Regular.ttf> --symbols <AISymbols-Regular.ttf> \
        [-o preview.png]
"""
import argparse
import re

from PIL import Image, ImageDraw, ImageFont

from icons import ICONS, NERD_FONTS, RECOLOR, VARIANTS

WIDTH = 1480
MARGIN = 24
COLS = 9             # columnas de [[icon]]
ROW_H = 99           # alto de cada fila de iconos
ICON_SIZE = 40       # px del em de los iconos
TEXT_SIZE = 15
SMALL_SIZE = 11

BG = (23, 22, 27)
TEXT = (154, 152, 163)
DIM = (93, 91, 102)
ORANGE = (224, 122, 82)
ICON = (232, 230, 239)


def short(name):
    """Nombre corto de devicons para la etiqueta: google-gemini-icon -> gemini."""
    name = re.sub(r"-icon$", "", name)
    name = re.sub(r"^(google|aws)-", "", name)
    return re.sub(r"^microsoft-(?!azure)", "ms-", name).removeprefix("microsoft-")


def main():
    ap = argparse.ArgumentParser(description="Genera preview.png para el README.")
    ap.add_argument("--nerd-font", required=True, help="CaskaydiaCove Nerd Font sin parchear (texto e iconos de Nerd Fonts)")
    ap.add_argument("--patched", required=True, help="CaskaydiaCove NF AI generada por patch_all.py")
    ap.add_argument("--symbols", required=True, help="AI Symbols (familia NF) generada por build_symbols.py")
    ap.add_argument("-o", "--out", default="preview.png")
    args = ap.parse_args()

    text = ImageFont.truetype(args.nerd_font, TEXT_SIZE)
    small = ImageFont.truetype(args.nerd_font, SMALL_SIZE)
    footer = ImageFont.truetype(args.nerd_font, 13)
    nf_icons = ImageFont.truetype(args.nerd_font, ICON_SIZE)
    patched = ImageFont.truetype(args.patched, ICON_SIZE)
    symbols = ImageFont.truetype(args.symbols, ICON_SIZE)

    icon_rows = -(-len(ICONS) // COLS)
    height = MARGIN + 38 + icon_rows * ROW_H + 30 + 38 + ROW_H + 30 + 40
    img = Image.new("RGB", (WIDTH, height), BG)
    d = ImageDraw.Draw(img)
    col_w = (WIDTH - 2 * MARGIN) // COLS

    def cell(x, y, label, cp_text, colored, left, right):
        d.text((x + 2, y), label, font=text, fill=ORANGE if colored else TEXT)
        d.text((x + 2, y + 16), cp_text, font=small, fill=DIM)
        for dx, (font, char) in zip((0, col_w // 2 - 6), (left, right)):
            d.text((x + dx, y + 30), char, font=font, fill=ICON, embedded_color=True)

    y = MARGIN
    d.text((MARGIN, y), "Cada icono: fuente parcheada CaskaydiaCove NF AI (monocromo, color del tema)  ·  "
           "AI Symbols (fallback a color)", font=text, fill=TEXT)
    y += 38
    for i, e in enumerate(ICONS):
        row, col = divmod(i, COLS)
        cell(MARGIN + col * col_w, y + row * ROW_H, short(e["name"]), f"U+{e['cp']:04X}", e.get("color"),
             (patched, chr(e["cp"])), (symbols, chr(e["cp"])))
    y += icon_rows * ROW_H + 30

    d.text((MARGIN, y), f"Variantes de color en AI Symbols: icono oficial de Nerd Fonts {NERD_FONTS}  ·  "
           "versión a color", font=text, fill=TEXT)
    y += 38
    var_w = (WIDTH - 2 * MARGIN) // len(VARIANTS)
    for i, e in enumerate(VARIANTS):
        x = MARGIN + i * var_w
        label = short(e["name"]) + (" (recolor)" if e["cp"] in RECOLOR else "")
        d.text((x + 2, y), label, font=text, fill=ORANGE)
        d.text((x + 2, y + 16), f"U+{e['cp']:04X} · nf U+{e['nf_cp']:04X}", font=small, fill=DIM)
        d.text((x, y + 38), chr(e["nf_cp"]), font=nf_icons, fill=ICON)
        d.text((x + 72, y + 38), chr(e["cp"]), font=symbols, fill=ICON, embedded_color=True)
    y += ROW_H + 30

    d.text((MARGIN, y), "Naranja: icono a color en AI Symbols. Gris: monocromo también en AI Symbols "
           "(toma el color del tema).", font=footer, fill=TEXT)
    d.text((MARGIN, y + 20), 'Windows Terminal: "font": { "face": "CaskaydiaCove Nerd Font, AI Symbols" }',
           font=footer, fill=TEXT)

    img.save(args.out, optimize=True)
    print(f"{args.out}: {img.width}x{img.height}")


if __name__ == "__main__":
    main()
