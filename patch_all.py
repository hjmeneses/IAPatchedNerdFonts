"""
Parchea TODAS las fuentes .ttf en este directorio con 9 glyphs de Devicons.
- Inserta en TODAS las subtablas cmap (format 4 y format 12)
- Cambia nombre interno agregando " Patched"
- Guarda con sufijo -Patched en el nombre de archivo
"""
import os, glob
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import _g_l_y_f as _glyf_mod
from fontTools.ttLib.tables._g_l_y_f import Glyph as TtGlyph

_glyf_mod.table__g_l_y_f.__len__ = lambda self: len(self.glyphs)

INPUT_DIR   = os.path.dirname(os.path.abspath(__file__))
DEVICONS_IN = r"C:\Users\EXX1X80\AppData\Local\Temp\devicons\package\dist\font\devicons.ttf"
OUTPUT_DIR  = os.path.join(INPUT_DIR, "Patched")

GLYPH_MAP = {
    "anthropic-icon": 0xE00B,
    "anthropic":      0xE00C,
    "claude-code":    0xE00D,
    "claude-icon":    0xE00E,
    "claude":         0xE00F,
    "mcp-icon":       0xE010,
    "mcp":            0xE011,
    "openai-icon":    0xE012,
    "openai":         0xE013,
}

# Sufijo para nombres internos
PATCH_SUFFIX = " Patched"
PS_PATCH_SUFFIX = "-Patched"

def patch_name_table(font):
    """Agrega ' Patched' al family name y nombres relacionados."""
    for record in font["name"].names:
        s = record.toUnicode()
        if record.nameID == 1:  # Family
            if not s.endswith(PATCH_SUFFIX.strip()):
                record.string = s + PATCH_SUFFIX
        elif record.nameID == 4:  # Full Name
            if not s.endswith(PATCH_SUFFIX.strip()):
                record.string = s + PATCH_SUFFIX
        elif record.nameID == 6:  # PostScript Name
            if not s.endswith(PS_PATCH_SUFFIX):
                record.string = s + PS_PATCH_SUFFIX
        elif record.nameID == 16:  # Typographic Family
            if not s.endswith(PATCH_SUFFIX.strip()):
                record.string = s + PATCH_SUFFIX

os.makedirs(OUTPUT_DIR, exist_ok=True)
fonts = sorted(glob.glob(os.path.join(INPUT_DIR, "*.ttf")))
print(f"Fuentes: {len(fonts)}  |  Salida: {OUTPUT_DIR}\n")

for font_path in fonts:
    fname = os.path.basename(font_path)
    print(f"  {fname} ... ", end="", flush=True)

    dev = TTFont(DEVICONS_IN)
    dev_glyf = dev["glyf"]
    dev_hmtx = dev["hmtx"].metrics
    dev_upm  = dev["head"].unitsPerEm

    cas = TTFont(font_path)
    cas_glyf = cas["glyf"]
    cas_glyf.ensureDecompiled()
    cas_hmtx = cas["hmtx"].metrics
    cas_upm  = cas["head"].unitsPerEm
    scale    = cas_upm / dev_upm

    for glyph_name, target_cp in GLYPH_MAP.items():
        if glyph_name not in dev_glyf:
            continue
        new_name  = f"devicon.{glyph_name}"
        src_glyph = dev_glyf[glyph_name]

        if src_glyph is not None:
            src_glyph.expand(dev_glyf)
            if scale != 1.0:
                if hasattr(src_glyph, 'coordinates') and src_glyph.coordinates is not None:
                    src_glyph.coordinates.transform(((scale, 0), (0, scale)))
                for attr in ('xMin', 'yMin', 'xMax', 'yMax'):
                    if hasattr(src_glyph, attr):
                        setattr(src_glyph, attr, int(getattr(src_glyph, attr) * scale))

            # Centrar verticalmente entre ascender y descender de la fuente destino
            os2 = cas["OS/2"]
            font_center = (os2.sTypoAscender + os2.sTypoDescender) // 2
            glyph_center = (src_glyph.yMax + src_glyph.yMin) // 2
            dy = font_center - glyph_center
            if hasattr(src_glyph, 'coordinates') and src_glyph.coordinates is not None:
                src_glyph.coordinates.translate((0, dy))
            src_glyph.yMin += dy
            src_glyph.yMax += dy

        cas_glyf.glyphs[new_name] = src_glyph if src_glyph is not None else TtGlyph()

        if glyph_name in dev_hmtx:
            aw, lsb = dev_hmtx[glyph_name]
            cas_hmtx[new_name] = (int(aw * scale), int(lsb * scale))
        else:
            cas_hmtx[new_name] = (cas_upm, 0)

        # Insertar en subtablas cmap format 4 y 12 (no format 6 que es Mac legacy)
        for st in cas["cmap"].tables:
            if st.format in (4, 12, 14):
                st.cmap[target_cp] = new_name

        cas.getGlyphOrder().append(new_name)

    # Sincronizar glyphOrder
    font_go    = cas.getGlyphOrder()
    actual_set = set(cas_glyf.glyphs.keys())
    cas_glyf.glyphOrder = [n for n in font_go if n in actual_set]

    # Cambiar nombre interno
    patch_name_table(cas)

    # Guardar con sufijo -Patched en nombre de archivo
    out_name = fname.replace(".ttf", "-Patched.ttf")
    cas.save(os.path.join(OUTPUT_DIR, out_name))
    print("OK")
    dev.close()
    cas.close()

print(f"\nListo. {len(fonts)} fuentes parcheadas en {OUTPUT_DIR}")
