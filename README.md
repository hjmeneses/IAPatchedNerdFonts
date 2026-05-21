# Nerd Fonts

This is an archived font from the Nerd Fonts release v3.4.0.

For more information see:
* https://github.com/ryanoasis/nerd-fonts/
* https://github.com/ryanoasis/nerd-fonts/releases/latest/

# Cascadia Code

**Cascadia Code** is a fun, new monospaced font that includes programming ligatures.

For more information have a look at the upstream website: https://github.com/microsoft/cascadia-code

Note that upstream has a version with Nerd Font icons: CascadiaCodeNF. That has not been created with the Nerd Fonts `font-patcher`.

## Preprocessed Source Font

This source font has been preprocessed - it is not taken directly from upstream.
Cascadia Code is mainly a variable font (VF) and the static versions (that Nerd Fonts
are based on) are prepared in a different way: They have been hinted with `ttfautohint`.
That hints differ considerably from the hints in the VF. That changes the rendering for
smaller sizes (usual sizes in terminals) considerably.

To get the 'original' (i.e. VF) feel of the font we redo the hints in the static versions:
Open the font with Microsoft's VisualTrueType (VTT) and apply Light Latin Autohint.
The issue is known upstream and will probably be fixed. But until it is fixed we need
to do this manual process on all source updates.

Version: 2407.24

## Why `CaskaydiaCove` and not `Cascadia Code`?

What's in a name? The reason for the name change is to comply with the SIL Open Font License (OFL), in particular the [Reserved Font Name mechanism][SIL-RFN]

Some fonts have parts of their name "reserved" per the [Reserved Font Name mechanism][SIL-RFN]:
> No Modified Version of the Font Software may use the Reserved Font
> Name(s) unless explicit written permission is granted by the corresponding
> Copyright Holder. This restriction only applies to the primary font name as
> presented to the users.

- The main goals seem to be to: `Avoid collisions`, `Protect authors`, `Minimize support`, and `Encourage derivatives`

See the [Reserved Font Name section][SIL-RFN] for additional information

## Which font?

### TL;DR

* Pick your font family:
  * If you are limited to monospaced fonts (because of your terminal, etc) then pick a font with `Nerd Font Mono` (or `NFM`).
  * If you want to have bigger icons (usually around 1.5 normal letters wide) pick a font without `Mono` i.e. `Nerd Font` (or `NF`). Most terminals support this, but ymmv.
  * If you work in a proportional context (GUI elements or edit a presentation etc) pick a font with `Nerd Font Propo` (or `NFP`).

### Ligatures

Ligatures are generally preserved in the patched fonts.
Nerd Fonts `v2.0.0` had no ligatures in the `Nerd Font Mono` fonts, this has been dropped with `v2.1.0`.
If you have a ligature-aware terminal and don't want ligatures you can (usually) disable them in the terminal settings.

### Explanation

Once you narrow down your font choice of family (`Droid Sans`, `Inconsolata`, etc) and style (`bold`, `italic`, etc) you have 2 main choices:

#### `Option 1: Download already patched font`

 * For a stable version download a font package from the [release page](https://github.com/ryanoasis/nerd-fonts/releases)
 * Or download the development version from the folders here

#### `Option 2: Patch your own font`

 * Patch your own variations with the various options provided by the font patcher (i.e. not include all symbols for smaller font size)

For more information see: [The FAQ](https://github.com/ryanoasis/nerd-fonts/wiki/FAQ-and-Troubleshooting#which-font)

[SIL-RFN]:http://scripts.sil.org/cms/scripts/page.php?item_id=OFL_web_fonts_and_RFNs#14cbfd4a

---

## AI Icons Patch (`patch_all.py`)

### Qué hace

`patch_all.py` toma las 36 fuentes TTF de este directorio y les inserta 9 glyphs personalizados de **Anthropic**, **Claude**, **Claude Code**, **MCP** y **OpenAI**. Los glyphs se escalan al tamaño de cada fuente y se centran verticalmente en la celda. Las fuentes resultantes se guardan en `Patched/` con el sufijo `-Patched`.

### Para qué sirve

Permite usar iconos de las herramientas de IA más usadas directamente en la terminal o el editor, sin plugins ni imágenes — igual que cualquier otro icono de Nerd Fonts.

### Por qué

Las Nerd Fonts no incluyen iconos de herramientas de IA modernas. Este script los añade en el área de uso privado de Unicode (`U+E00B`–`U+E013`), siguiendo la misma convención del proyecto Nerd Fonts.

### Preview

![Glyphs en terminal](preview.png)

### Glyphs incluidos

| Nombre | Codepoint |
|--------|-----------|
| anthropic-icon | U+E00B |
| anthropic | U+E00C |
| claude-code | U+E00D |
| claude-icon | U+E00E |
| claude | U+E00F |
| mcp-icon | U+E010 |
| mcp | U+E011 |
| openai-icon | U+E012 |
| openai | U+E013 |

### Requisitos

```
pip install fonttools
```

Edita la ruta de `devicons.ttf` en `patch_all.py` si es necesario:

```python
DEVICONS_IN = r"C:\ruta\a\devicons.ttf"
```

### Uso

```powershell
python patch_all.py
```

Instala las fuentes de `Patched/` (click derecho → **Instalar**) y verifica los glyphs en Windows Terminal:

```powershell
0xE00B..0xE013 | ForEach-Object { "$([char]$_)  U+{0:X4}" -f $_ }
```

