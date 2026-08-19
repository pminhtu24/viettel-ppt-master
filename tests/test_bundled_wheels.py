#!/usr/bin/env python3
"""
Test doc_to_md.py with bundled wheels — simulates a clean machine
where mammoth, ebooklib, nbconvert, lxml, pyzmq are NOT installed.

Runs all 4 native format conversions (.docx, .html, .epub, .ipynb)
and verifies output.

Usage:
  python3 tests/test_bundled_wheels.py

Prerequisites:
  python3 tests/generate_sample_sources.py   # create sample files first
"""
import importlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import traceback
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_DIR = REPO_ROOT / "scripts" / "source_to_md"
VENDOR_DIR = SCRIPT_DIR / "vendor_wheels"
UNIVERSAL_DIR = VENDOR_DIR / "universal"
SAMPLE_DIR = Path(__file__).parent / "sample_sources"

# Modules that should be provided by bundled wheels, not system
VENDORED_MODULES = {
    "mammoth", "cobble", "ebooklib", "nbconvert", "nbformat", "nbclient",
    "jupyter_client", "jupyter_core", "traitlets", "jinja2", "pygments",
    "bleach", "mistune", "pandocfilters", "defusedxml", "testpath",
    "entrypoints", "jupyterlab_pygments", "webencodings", "packaging",
    "nest_asyncio", "jsonschema", "fastjsonschema", "markdownify",
    "soupsieve", "bs4", "tornado", "markupsafe",
}

# C-extension modules we do NOT bundle — stub or block
BLOCKED_MODULES = {"lxml", "pyzmq", "zmq"}


class _CleanMachineSimulator:
    """Simulate a clean machine by blocking system imports of vendored packages
    and C-extension packages, forcing doc_to_md.py to use bundled wheels only."""

    def __init__(self):
        self._original_meta = sys.meta_path[:]
        self._blocked_imports = set()

    def __enter__(self):
        # Purge all vendored/blocked modules from sys.modules
        to_remove = set()
        for name in sys.modules:
            top = name.split(".")[0]
            if top in VENDORED_MODULES or top in BLOCKED_MODULES:
                to_remove.add(name)
        for name in to_remove:
            del sys.modules[name]

        # Install import blocker for C-extension packages
        sys.meta_path.insert(0, self)
        return self

    def __exit__(self, *args):
        sys.meta_path = self._original_meta[:]
        # Clean up vendored modules we loaded
        for name in list(sys.modules):
            top = name.split(".")[0]
            if top in VENDORED_MODULES or top in BLOCKED_MODULES:
                del sys.modules[name]

    def find_module(self, name, path=None):
        """Block C-extension modules from system path.
        Vendored wheels will still work because they're added to sys.path
        by _ensure_vendored_deps() AFTER this blocker."""
        top = name.split(".")[0]
        if top in BLOCKED_MODULES:
            self._blocked_imports.add(name)
            return self
        return None

    def load_module(self, name):
        raise ImportError(f"Blocked (simulating clean machine): {name}")

    @property
    def blocked(self):
        return sorted(self._blocked_imports)


def _verify_wheel_source(module_name: str) -> bool:
    """Check if a module was loaded from a vendored wheel, not system."""
    mod = sys.modules.get(module_name)
    if mod is None:
        return False
    mod_path = getattr(mod, "__file__", "") or ""
    return "vendor_wheels" in mod_path or ".whl" in mod_path


def _run_conversion(doc_to_md, input_path: Path, output_path: Path):
    """Run a single conversion and return (success, output, error)."""
    try:
        result = doc_to_md.convert_to_markdown(str(input_path), str(output_path))
        if result:
            return True, result, None
        return False, None, "convert_to_markdown returned empty string"
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def main():
    print("=" * 70)
    print("TEST: doc_to_md.py with bundled wheels (simulated clean machine)")
    print("=" * 70)
    print()

    # Check sample files exist
    if not SAMPLE_DIR.exists():
        print(f"[ERROR] Sample directory not found: {SAMPLE_DIR}")
        print(f"        Run first: python3 tests/generate_sample_sources.py")
        return 1

    expected_files = ["sample.docx", "sample.html", "sample.epub", "sample.ipynb"]
    missing = [f for f in expected_files if not (SAMPLE_DIR / f).exists()]
    if missing:
        print(f"[ERROR] Missing sample files: {missing}")
        print(f"        Run first: python3 tests/generate_sample_sources.py")
        return 1

    # Check vendor wheels exist
    if not UNIVERSAL_DIR.exists():
        print(f"[ERROR] Vendor wheels directory not found: {UNIVERSAL_DIR}")
        return 1

    wheel_count = len(list(UNIVERSAL_DIR.glob("*.whl")))
    print(f"Vendor wheels: {wheel_count} files in {UNIVERSAL_DIR}")
    stub_path = VENDOR_DIR / "pyzmq_stub.py"
    print(f"pyzmq_stub.py: {'found' if stub_path.exists() else 'MISSING'}")
    print()

    # Simulate clean machine
    simulator = _CleanMachineSimulator()
    with simulator:
        # Import doc_to_md fresh
        sys.path.insert(0, str(SCRIPT_DIR))
        # Remove cached import
        if "doc_to_md" in sys.modules:
            del sys.modules["doc_to_md"]
        import doc_to_md

        print(f"Blocked system modules (simulated): {simulator.blocked}")
        print()

        all_pass = True
        test_cases = [
            ("DOCX → MD (mammoth from wheel)", "sample.docx", "sample_docx.md"),
            ("HTML → MD (markdownify+bs4 from wheel)", "sample.html", "sample_html.md"),
            ("EPUB → MD (stdlib fallback, lxml blocked)", "sample.epub", "sample_epub.md"),
            ("IPYNB → MD (nbconvert+pyzmq stub)", "sample.ipynb", "sample_ipynb.md"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            for desc, input_name, output_name in test_cases:
                print("-" * 70)
                print(f"TEST: {desc}")
                print("-" * 70)

                input_path = SAMPLE_DIR / input_name
                output_path = tmpdir / output_name

                success, output, error = _run_conversion(
                    doc_to_md, input_path, output_path
                )

                if success:
                    print(f"  [PASS] {input_name} → {output_name}")
                    print(f"  Output file: {output_path.stat().st_size:,} bytes")
                    preview = output.strip()[:200]
                    print(f"  Preview:\n    {preview.replace(chr(10), chr(10)+'    ')}")

                    # Check for image extraction
                    files_dir = output_path.parent / (output_path.stem + "_files")
                    if files_dir.exists():
                        images = list(files_dir.iterdir())
                        print(f"  Images extracted: {len(images)} file(s)")
                        for img in images:
                            print(f"    - {img.name} ({img.stat().st_size:,} bytes)")

                    # Verify key modules loaded from vendored wheels
                    wheel_checks = {
                        "sample.docx": ["mammoth"],
                        "sample.html": ["markdownify", "bs4"],
                        "sample.epub": [],
                        "sample.ipynb": ["nbconvert"],
                    }
                    for mod_name in wheel_checks.get(input_name, []):
                        if _verify_wheel_source(mod_name):
                            print(f"  [WHEEL] {mod_name} loaded from vendored wheel ✓")
                        elif mod_name in sys.modules:
                            print(f"  [SYS]  {mod_name} loaded from system (not wheel)")
                        else:
                            print(f"  [??]   {mod_name} not in sys.modules")
                else:
                    print(f"  [FAIL] {input_name}")
                    if error:
                        print(f"  Error: {error}")
                    all_pass = False

                print()

    print("=" * 70)
    if all_pass:
        print("RESULT: ALL TESTS PASSED")
    else:
        print("RESULT: SOME TESTS FAILED")
    print("=" * 70)

    # Phase 2: Pure wheel mode — strip system site-packages to prove
    # the bundled wheels work independently
    print()
    print("=" * 70)
    print("PHASE 2: Pure wheel mode (system site-packages stripped)")
    print("=" * 70)
    print()

    # Run in subprocess with PYTHONPATH set to ONLY vendor wheels
    import subprocess
    env = os.environ.copy()
    # Clear PYTHONPATH and PYTHONHOME to avoid interference
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    # Build a subprocess test script
    subprocess_script = f'''
import sys, os, json, tempfile, traceback
from pathlib import Path

# Remove ALL system site-packages — simulate clean Python
import site
site_packages = [p for p in sys.path if "site-packages" in p or "dist-packages" in p]
for p in site_packages:
    sys.path.remove(p)

# Add vendor dir for stubs
sys.path.insert(0, {str(VENDOR_DIR)!r})

# Install stubs BEFORE importing doc_to_md
import pyzmq_stub
pyzmq_stub.install(sys.modules)
import rpds_stub
rpds_stub.install(sys.modules)

# Add script dir for doc_to_md
sys.path.insert(0, {str(SCRIPT_DIR)!r})

import doc_to_md
# Let doc_to_md's bootstrap extract wheels and add to sys.path
doc_to_md._ensure_vendored_deps()

sample_dir = Path({str(SAMPLE_DIR)!r})
tests = [
    ("DOCX", "sample.docx", "out_docx.md"),
    ("HTML", "sample.html", "out_html.md"),
    ("EPUB", "sample.epub", "out_epub.md"),
    ("IPYNB", "sample.ipynb", "out_ipynb.md"),
]

all_pass = True
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    for label, inp, outp in tests:
        try:
            result = doc_to_md.convert_to_markdown(str(sample_dir / inp), str(tmp / outp))
            if result:
                mod_checks = {{"DOCX": "mammoth", "HTML": "markdownify", "IPYNB": "nbconvert"}}
                mod_name = mod_checks.get(label)
                mod_info = ""
                if mod_name and mod_name in sys.modules:
                    mp = getattr(sys.modules[mod_name], "__file__", "") or ""
                    if "vendor_deps_" in mp or "vendor_wheels" in mp:
                        mod_info = f" [WHEEL ✓] {{mod_name}}"
                    else:
                        mod_info = f" [SYS] {{mod_name}}"
                print(f"[PASS] {{label}}: {{len(result)}} chars{{mod_info}}")
            else:
                print(f"[FAIL] {{label}}: empty result")
                all_pass = False
        except Exception as e:
            print(f"[FAIL] {{label}}: {{type(e).__name__}}: {{e}}")
            traceback.print_exc()
            all_pass = False

print()
print("PHASE 2 RESULT:", "ALL PASSED" if all_pass else "FAILED")
sys.exit(0 if all_pass else 1)
'''

    result = subprocess.run(
        [sys.executable, "-c", subprocess_script],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT)
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[:500])
    if result.returncode != 0:
        all_pass = False

    print()
    print("=" * 70)
    print("FINAL RESULT:", "ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED")
    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
