# SVG Pipeline Tools

## Recommended Pipeline

During skill-driven generation, generate the full SVG deck, run the initial project check and repairs, verify charts when applicable, then normalize Viettel chrome and run the final project scan before native export:

```bash
python3 scripts/svg_quality_checker.py <project_path>
# repair findings and verify charts
python3 scripts/apply_brand_chrome.py <project_path> --brand-chrome viettel  # viettel_default only
python3 scripts/svg_quality_checker.py <project_path>  # final scan, must report 0 errors
python3 scripts/svg_to_pptx.py <project_path>
```

## `svg_to_pptx.py`

The exporter reads `svg_output/*.svg` and writes one editable native PPTX.

```bash
python3 scripts/svg_to_pptx.py <project_path>
python3 scripts/svg_to_pptx.py <project_path> -o output.pptx
python3 scripts/svg_to_pptx.py <project_path> -t none
python3 scripts/svg_to_pptx.py <project_path> --auto-advance 3
python3 scripts/svg_to_pptx.py <project_path> --animation mixed
```

Native export is strict about unsupported visual SVG elements, deduplicates identical media by content hash, and publishes the requested PPTX only after conversion succeeds.

Page transitions use `-t/--transition`; per-element entrance animations use `-a/--animation`. Optional object-level overrides live in `<project>/animations.json` and can be created or checked with `animation_config.py scaffold|validate`.

## `svg_quality_checker.py`

```bash
python3 scripts/svg_quality_checker.py examples/project/svg_output/01_cover.svg
python3 scripts/svg_quality_checker.py examples/project
python3 scripts/svg_quality_checker.py --all examples
```

Checks include canvas/viewBox consistency, banned elements, text overflow contracts, brand chrome, and project-level consistency.

## `svg_position_calculator.py`

Use after the project quality check for supported data charts:

```bash
python3 scripts/svg_position_calculator.py calc bar --data "A:185,B:142" --area "130,155,1200,480" --bar-width 120
python3 scripts/svg_position_calculator.py calc line --data "0:50,10:80,20:120" --area "120,120,1200,600" --y-range "0,150"
python3 scripts/svg_position_calculator.py calc pie --data "A:35,B:25,C:20" --center "420,400" --radius 200
# Add --expect-total 100 when the inputs are percentages.
python3 scripts/svg_position_calculator.py analyze <svg_file>
```

The calculator reports coordinates; update SVG geometry manually and re-run the per-file checker.
