# CaskaydiaCove Nerd Font — Patched with AI Icons

[CaskaydiaCove Nerd Font](https://github.com/ryanoasis/nerd-fonts) **v3.5.1** extended with AI tool icons that Nerd Fonts does not ship yet, taken from [devicons](https://github.com/vorillaz/devicons) **v2.4.0**.

![Glyphs rendered in the NF, Mono and Propo variants, next to the official Nerd Fonts AI icons](preview.png)

## Included glyphs

| Codepoint | Icon | devicons glyph |
|-----------|------|----------------|
| `U+E00B` | Claude Code (robot) | `claude-code` |
| `U+E00C` | Anthropic | `anthropic-icon` |
| `U+E00D` | Google Gemini | `google-gemini-icon` |
| `U+E00E` | Ollama | `ollama-icon` |
| `U+E00F` | Cursor (editor) | `cursor-icon` |
| `U+E010` | Microsoft Copilot | `microsoft-copilot` |

### Already in Nerd Fonts — use the official codepoints

Since v3.5.1, Nerd Fonts includes these through Codicons, so this patch does not duplicate them:

| Codepoint | Nerd Fonts name |
|-----------|-----------------|
| `U+EC82` | `nf-cod-claude` |
| `U+EC81` | `nf-cod-openai` |
| `U+EC47` | `nf-cod-mcp` |
| `U+EC1E` | `nf-cod-copilot` (GitHub Copilot) |

### Why `U+E00B`?

Nerd Fonts appends new icons to the end of each icon set's block (Devicons `U+E700…`, Codicons `U+EA60…`), and those blocks grow with every release. `U+E00B–E09F` is the unused gap after Pomicons (`U+E000–E00A`), which has not changed in years, so it is the least likely place to collide with a future Nerd Fonts release. If Nerd Fonts adds any of these icons officially, they will be removed from this patch in favor of the official codepoint.

## Installing

Download the zip from [Releases](../../releases), extract it, select the `.ttf` files, and choose **Install** (or **Install for all users**).

The fonts install as a separate family (`CaskaydiaCove NF Patched`, `CaskaydiaCove NFM Patched`, `CaskaydiaCove NFP Patched`), so they can live side by side with the upstream Nerd Font.

| Variant | Use it when |
|---------|-------------|
| **NFM** (Mono) | Your terminal requires strict monospacing. Icons fit in one cell. |
| **NF** | Most terminals. Icons are larger and overflow to about 1.7 cells, like the official Nerd Fonts icons. |
| **NFP** (Propo) | Proportional contexts: GUI elements and presentations. |

To check the glyphs in your terminal:

```powershell
0xE00B..0xE010 | ForEach-Object { "$([char]$_)  U+{0:X4}" -f $_ }
```

In an Oh My Posh theme, use the escape sequence, e.g. `""` for the Claude Code robot.

## Building the fonts yourself

```powershell
pip install fonttools

# 1. CaskaydiaCove Nerd Font v3.5.1
#    https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1/CascadiaCode.tar.xz
# 2. devicons v2.4.0 (dist/devicons.ttf inside the npm package)
#    https://registry.npmjs.org/devicons/-/devicons-2.4.0.tgz

python patch_all.py <folder-with-ttf> --devicons <path\to\devicons.ttf> -o Patched
python verify.py <folder-with-ttf> Patched
```

`patch_all.py`:

- Scales each icon by the devicons em (like Nerd Fonts' `font-patcher`), so icons keep their relative sizes. Glyphs that overflow the em are shrunk to fit.
- **Mono**: fits the icon in one cell, centered, with a one-cell advance, so the font stays monospaced.
- **NF**: UPM-sized icon, one-cell advance, overflowing to the right like `nf-cod-*`.
- **Propo**: UPM-sized icon, with an advance equal to the icon width.
- Centers icons vertically on `(sTypoAscender + sTypoDescender) / 2`.
- Adds the glyphs to every Unicode `cmap` subtable (formats 4 and 12).
- Renames the family to `… Patched` and the PostScript name to `…Patched-Style`, and appends a note to the version string.
- Refuses to patch a font that already uses these codepoints, for example a font that was already patched.

`verify.py` compares each output font with its source and checks codepoints, advances, the cell box, vertical centering, a duplicate-free glyph order, unchanged original metrics, and names. The release fonts also pass [OpenType Sanitizer](https://github.com/khaledhosny/ots-python) (`python -m ots`).

## Licenses

- **Fonts**: SIL Open Font License 1.1 — see [`OFL.txt`](OFL.txt). This applies to Cascadia Code (© Microsoft, Reserved Font Name *Cascadia Code*), to the Nerd Fonts patches, and to these modified versions, which must remain under the OFL.
- **Icons**: from [devicons](https://github.com/vorillaz/devicons) (MIT). The logos are trademarks of their respective owners and are included only to identify those tools.
- **Scripts** (`patch_all.py`, `verify.py`): GNU GPL v3 — see [`LICENSE`](LICENSE).
