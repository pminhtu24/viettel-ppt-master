# Image Tools

> Web acquisition keeps license metadata in `image_sources.json`; development SVGs use external image references and finalized SVGs embed the files.

Image tools cover web image search, image inspection, and Gemini watermark removal.

Image generation is intentionally not part of this skill. Use user-provided images, openly licensed web images, or placeholders.

## `analyze_images.py`

Analyze images in a project directory before writing the design spec or composing slide layouts.

```bash
python3 scripts/analyze_images.py <project_path>/images
```

Use this instead of opening image files directly when following the project workflow.

## `image_search.py`

Zero-config web image search across openly licensed providers, used when the resource-list row has `Acquire Via: web`.

```bash
python3 scripts/image_search.py "offshore wind farm" \
  --filename cover_bg.jpg --slide 01_cover \
  --orientation landscape -o projects/demo/images
```

Providers (Openverse and Wikimedia work with no key; configure Pexels / Pixabay for better stock-photo quality):

| Provider | Config | Strength |
|---|---|---|
| `openverse` | zero-config | fallback aggregator: Wikimedia + Flickr + museums + rawpixel |
| `wikimedia` | zero-config | educational, scientific, geographic, historical |
| `pexels` | recommended: `PEXELS_API_KEY` | modern stock photography, people, workplace, lifestyle |
| `pixabay` | recommended: `PIXABAY_API_KEY` | broad type coverage including photos and illustrations |

Default search chain (when `--provider` is unset): zero-config providers first, then keyed providers whose API key is set in the environment. Keyed providers without a key are silently skipped. For polished visual decks, configure at least one keyed provider.

`image_search.py` checks the current directory, clone root, and `~/.ppt-master/.env`, so skill installs can keep `PEXELS_API_KEY` / `PIXABAY_API_KEY` in the shared config.

Query guidance:

| Case | Pattern |
|---|---|
| Generic stock concept | `boardroom meeting, professional editorial photography, natural light` |
| China-specific landmark | Official Chinese place name + concrete scene |
| Avoid | Negative prompt wording such as `not tourist snapshot` |

License filter:

- **Default**: search all providers with `cc0,pdm,pexels,pixabay,cc by,cc by-sa` allowed together. The chosen image may be `no-attribution` or `attribution-required`; Executor adds an inline credit only when needed.
- `--strict-no-attribution` restricts the search to `cc0,pdm,pexels,pixabay` — useful for full-bleed hero images or templates that cannot host a credit element.

Pin a provider, refuse attribution, or override the manifest path:

```bash
# Pin Wikimedia
python3 scripts/image_search.py "Olympics opening ceremony" \
  --filename event.jpg --provider wikimedia \
  --orientation landscape -o projects/demo/images

# Strict mode — refuse CC BY / CC BY-SA
python3 scripts/image_search.py "abstract gradient" \
  --filename hero.jpg --strict-no-attribution \
  -o projects/demo/images
```

Output:

- Image saved to the specified output directory (auto-converts webp → jpg via Pillow when the filename extension demands)
- `image_sources.json` manifest with full provenance (provider, license, license_tier, author, source URL, dimensions, attribution_text)
- Manifest is idempotent on `filename` — rerunning replaces that entry only

Allowed licenses (default): CC0, Public Domain, Pexels License, Pixabay Content License, CC BY, CC BY-SA. Auto-rejected: CC BY-NC, CC BY-ND, CC BY-NC-SA, CC BY-NC-ND, all rights reserved, unknown.

The full role-level reference (intent → query translation, on-slide attribution visual specification) is in [`references/image-searcher.md`](../../references/image-searcher.md).

## `gemini_watermark_remover.py`

Remove Gemini watermark assets after manual download.

```bash
python3 scripts/gemini_watermark_remover.py <image_path>
python3 scripts/gemini_watermark_remover.py <image_path> -o output_path.png
python3 scripts/gemini_watermark_remover.py <image_path> -q
```

Notes:
- Requires `scripts/assets/bg_48.png` and `scripts/assets/bg_96.png`
- Best used after downloading “full size” Gemini images

Dependencies:

```bash
pip install Pillow numpy
```
