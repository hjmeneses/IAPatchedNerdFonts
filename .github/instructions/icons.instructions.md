---
applyTo: "icons.toml"
---

# Review of icons.toml

`verify_brand.py` already checks in CI that a recolored SVG uses exactly `brand_colors`. In review, check what CI cannot: that `brand_colors` really is the palette of an official version of the logo.

When a pull request adds or changes a `recolor`, `brand_colors` or `brand_ref`:

- The recolor must reproduce an official version of the logo (for example, Jupyter's `whitetext-orangebody-whitemoons`), not a new combination. Ask which official version it reproduces if that is not clear.
- The brand's main color is never recolored: AWS orange `#FF9900`, Jupyter orange `#F37726`. Only the dark parts change, the same way the brand's own dark-background version changes them.
- Flag combinations the brand does not publish, such as Jupyter with white text and grey moons.
- `brand_ref` should be an `.svg` from the brand's own repository, pinned to a commit (`raw.githubusercontent.com/<org>/<repo>/<sha>/...`), so CI can compare the palettes. A brand guidelines page is only acceptable when the brand does not publish an SVG; say so in a comment next to it.
- `note` must say which background the variant is for ("for dark backgrounds" / "for light backgrounds").
- If a new `[[variant]]` reuses a `name` with a `recolor`, the existing variant with the original colors should get the matching `note`.
