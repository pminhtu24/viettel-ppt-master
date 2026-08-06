"""CLI entry point for native SVG-to-PPTX conversion."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .animation_config import load_animation_config, validate_animation_config
from .pptx_builder import create_pptx_with_native_svg
from .pptx_dimensions import CANVAS_FORMATS, get_project_info
from .pptx_discovery import find_svg_files
from .pptx_slide_xml import TRANSITIONS

from check_fonts import build_report
from svg_quality_checker import SVGQualityChecker

try:
    from pptx_animations import ANIMATIONS as _ANIMATIONS
except ImportError:
    _ANIMATIONS = {}


def _font_gate_errors(
    project_path: Path,
    svg_files: list[Path],
    *,
    report: dict[str, object] | None = None,
    allow_font_fallback: bool = False,
) -> list[str]:
    """Return font problems that would otherwise become silent PPT fallbacks."""
    if not (project_path / "spec_lock.md").exists():
        return []

    report = report or build_report(project_path)
    errors = []
    face_report = report.get("viettel_faces")
    if (
        not allow_font_fallback
        and isinstance(face_report, dict)
        and face_report["missing_after"]
    ):
        detail = face_report["install_error"] or "automatic installation did not register all faces"
        errors.append(
            f"missing FS Magistral faces: {', '.join(face_report['missing_after'])} ({detail})"
        )
    for stack in report["stacks"]:
        if not allow_font_fallback and stack["status"] != "installed":
            errors.append(
                f"{stack['key']} requires {stack['stack']}, but the host would use "
                f"{stack['active_family'] or 'no font'}"
            )

    checker = SVGQualityChecker()
    for svg_file in svg_files:
        result = checker.check_file(str(svg_file))
        messages = [*result["errors"], *result["warnings"]]
        for message in messages:
            if "[brand-font]" in message or (
                "[spec-lock-drift]" in message and "font-family" in message
            ):
                errors.append(f"{svg_file.name}: {message}")
    return errors


def main() -> None:
    """Run the native PPTX exporter."""
    transition_choices = [
        "none",
        *(TRANSITIONS.keys() if TRANSITIONS else ("fade", "push", "wipe", "split", "strips", "cover", "random")),
    ]
    animation_choices = [
        "none",
        *(_ANIMATIONS.keys() if _ANIMATIONS else ("fade", "fly", "zoom", "appear")),
        "mixed",
        "random",
    ]

    parser = argparse.ArgumentParser(
        description="PPT Master - native SVG to editable PPTX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
    %(prog)s examples/ppt169_demo
    %(prog)s examples/ppt169_demo -o out.pptx
    %(prog)s examples/ppt169_demo -t push --transition-duration 1.0

Transition effects:
    {", ".join(transition_choices)}

Per-element entrance animation:
    {", ".join(animation_choices)}
""",
    )
    parser.add_argument("project_path", help="Project directory")
    parser.add_argument("-o", "--output", help="Output PPTX path")
    parser.add_argument(
        "-f",
        "--format",
        choices=list(CANVAS_FORMATS),
        help="Canvas format; defaults to project metadata or SVG viewBox",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Reduce output")
    parser.add_argument(
        "--allow-font-fallback",
        action="store_true",
        help="Export despite missing host fonts; SVG font drift remains forbidden",
    )

    def non_negative_float(value: str) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"must be a number: {value}") from exc
        if number < 0:
            raise argparse.ArgumentTypeError("must be non-negative")
        return number

    parser.add_argument("-t", "--transition", choices=transition_choices)
    parser.add_argument("--transition-duration", type=non_negative_float)
    parser.add_argument("--auto-advance", type=non_negative_float)
    parser.add_argument("-a", "--animation", choices=animation_choices)
    parser.add_argument("--animation-duration", type=non_negative_float)
    parser.add_argument(
        "--animation-trigger",
        choices=["on-click", "with-previous", "after-previous"],
    )
    parser.add_argument("--animation-stagger", type=non_negative_float)
    parser.add_argument(
        "--animation-config",
        help="Optional sidecar; defaults to <project>/animations.json when present",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        parser.error(f"path does not exist: {project_path}")

    try:
        project_info = get_project_info(str(project_path))
        project_name = project_info.get("name", project_path.name)
        detected_format = project_info.get("format")
    except Exception:
        project_name = project_path.name
        detected_format = None

    svg_files, source_dir = find_svg_files(project_path)
    if not svg_files:
        parser.error(f"no SVG files found in {project_path / 'svg_output'}")

    font_report = build_report(project_path) if (project_path / "spec_lock.md").exists() else None
    font_errors = _font_gate_errors(
        project_path,
        svg_files,
        report=font_report,
        allow_font_fallback=args.allow_font_fallback,
    )
    if font_errors:
        parser.error(
            "font gate failed; export stopped to prevent Arial/Calibri substitution:\n  - "
            + "\n  - ".join(font_errors)
            + f"\nRun: python3 scripts/check_fonts.py {project_path}"
        )
    if args.allow_font_fallback and font_report and font_report["summary"]["brand_fidelity"] == "degraded":
        print("[WARN] brand fidelity degraded: exporting with a host font fallback")

    if args.output:
        output_path = Path(args.output)
    else:
        exports_dir = project_path / "exports"
        output_path = exports_dir / (
            f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.animation_config:
        config_path = Path(args.animation_config)
        if not config_path.is_absolute():
            config_path = project_path / config_path
        if not config_path.exists():
            parser.error(f"animation config does not exist: {config_path}")

    try:
        animation_config = load_animation_config(project_path, args.animation_config)
    except Exception as exc:
        parser.error(f"failed to load animation config: {exc}")

    verbose = not args.quiet
    if animation_config and verbose:
        config_label = args.animation_config or str(project_path / "animations.json")
        print(f"  Animation config: {config_label}")
        for warning in validate_animation_config(project_path, animation_config):
            print(f"  [warn] {warning}")

    defaults = animation_config.get("defaults", {}) if animation_config else {}
    transition_defaults = defaults.get("transition", {}) if isinstance(defaults, dict) else {}
    animation_defaults = defaults.get("animation", {}) if isinstance(defaults, dict) else {}

    transition_effect = (
        args.transition
        if args.transition is not None
        else transition_defaults.get("effect", "fade")
    )
    transition = None if transition_effect == "none" else transition_effect
    transition_duration = (
        args.transition_duration
        if args.transition_duration is not None
        else float(transition_defaults.get("duration", 0.4))
    )
    animation_effect = (
        args.animation
        if args.animation is not None
        else animation_defaults.get("effect", "mixed")
    )
    animation = None if animation_effect == "none" else animation_effect
    animation_duration = (
        args.animation_duration
        if args.animation_duration is not None
        else float(animation_defaults.get("duration", 0.4))
    )
    animation_stagger = (
        args.animation_stagger
        if args.animation_stagger is not None
        else float(animation_defaults.get("stagger", 0.5))
    )
    animation_trigger = (
        args.animation_trigger
        if args.animation_trigger is not None
        else animation_defaults.get("trigger", "after-previous")
    )
    animation_cli_overrides = {
        "transition": args.transition is not None,
        "transition_duration": args.transition_duration is not None,
        "auto_advance": args.auto_advance is not None,
        "animation": args.animation is not None,
        "animation_duration": args.animation_duration is not None,
        "animation_stagger": args.animation_stagger is not None,
        "animation_trigger": args.animation_trigger is not None,
    }

    if verbose:
        print("PPT Master - Native SVG to PPTX")
        print("=" * 50)
        print(f"  Project path: {project_path}")
        print(f"  SVG directory: {source_dir}")
        print(f"  Output file: {output_path}")
        print()

    success = create_pptx_with_native_svg(
        svg_files=svg_files,
        output_path=output_path,
        canvas_format=(
            args.format
            or (detected_format if detected_format and detected_format != "unknown" else None)
        ),
        verbose=verbose,
        transition=transition,
        transition_duration=transition_duration,
        auto_advance=args.auto_advance,
        animation=animation,
        animation_duration=animation_duration,
        animation_stagger=animation_stagger,
        animation_trigger=animation_trigger,
        animation_config=animation_config,
        animation_cli_overrides=animation_cli_overrides,
    )
    raise SystemExit(0 if success else 1)
