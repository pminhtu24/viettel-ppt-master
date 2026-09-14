# Conversion Tools

> Architecture rationale (why native-Python first with pandoc fallback, why curl_cffi for TLS impersonation): see [docs/technical-design.md "Source Content Conversion"](../../../../docs/technical-design.md#source-content-conversion).

Source conversion tools turn PDFs, documents, slide decks, and web pages into Markdown before project creation.

## `source_to_md/pdf_to_md.py`

Recommended first choice for native PDFs.

```bash
python3 scripts/source_to_md/pdf_to_md.py book.pdf
python3 scripts/source_to_md/pdf_to_md.py book.pdf -o output.md
python3 scripts/source_to_md/pdf_to_md.py ./pdfs
python3 scripts/source_to_md/pdf_to_md.py ./pdfs -o ./markdown

# Image extraction control (default: filtered)
python3 scripts/source_to_md/pdf_to_md.py book.pdf --images filtered  # size/quality filters applied
python3 scripts/source_to_md/pdf_to_md.py book.pdf --images all       # extract all images, no filtering
python3 scripts/source_to_md/pdf_to_md.py book.pdf --images none      # skip all images (text only)
```

Use cases:
- Native PDFs exported from Word, PowerPoint, LaTeX, or similar tools
- Privacy-sensitive documents that should stay local
- Fast first-pass extraction before falling back to OCR-heavy tools

Prefer MinerU or another OCR/layout tool when:
- The PDF is scanned or image-based
- Multi-column layout parsing is poor
- Encoding is garbled

Dependency:

```bash
pip install PyMuPDF
```

## `source_to_md/doc_to_md.py`

Hybrid converter: pure-Python for the common formats, pandoc fallback for the rest.

**Bundled wheels** — mammoth, cobble, ebooklib, nbconvert, markdownify,
beautifulsoup4, and all pure-Python transitive dependencies are shipped as
universal wheels in `scripts/source_to_md/vendor_wheels/universal/`.
The script auto-loads them at startup, so `.docx`, `.html`, `.epub`, and
`.ipynb` conversion works without internet access or `pip install`.

Legacy `.doc` is first converted to a temporary `.docx`, then passed through
the same Mammoth path. LibreOffice `soffice` is preferred on Linux and Windows;
Windows falls back to installed Microsoft Word COM. The temporary DOCX is deleted.

For `.epub`, if `lxml` (C extension) is not available on the system, a
stdlib fallback using `zipfile` + `xml.etree.ElementTree` handles extraction
instead of `ebooklib`.

For `.ipynb`, a bundled `pyzmq_stub.py` provides the minimal `zmq` module
surface that `nbconvert`'s import chain requires. Static conversion (no
kernel execution) works without `pyzmq` installed.

Native path (no external binary or pip install required):
- `.docx` — via `mammoth` (bundled wheel)
- `.html` / `.htm` — via `markdownify` + `beautifulsoup4` (bundled wheel)
- `.epub` — via `ebooklib` (bundled) if `lxml` present, else stdlib fallback
- `.ipynb` — via `nbconvert` (bundled wheel) + `pyzmq_stub`

Pandoc fallback (only if you need these):
- `.odt`, `.rtf`, `.tex`/`.latex`, `.rst`, `.org`, `.typ`

```bash
python3 scripts/source_to_md/doc_to_md.py lecture.docx
python3 scripts/source_to_md/doc_to_md.py legacy.doc
python3 scripts/source_to_md/doc_to_md.py lecture.docx -o output.md
python3 scripts/source_to_md/doc_to_md.py notes.epub
python3 scripts/source_to_md/doc_to_md.py paper.tex -o paper.md  # uses pandoc
```

Optional system dependencies:

```bash
# Only needed for .epub if you want ebooklib's full fidelity (otherwise stdlib fallback)
pip install lxml

# Legacy .doc conversion (Word COM is an automatic Windows-only fallback)
# Ubuntu:  sudo apt install libreoffice
# Windows: install LibreOffice or Microsoft Word

# Pandoc fallback — only for .odt/.rtf/.tex/.rst/.org/.typ
# macOS:   brew install pandoc
# Ubuntu:  sudo apt install pandoc
# Windows: https://pandoc.org/installing.html
```

All paths produce the same output convention: `<input>.md` plus a sibling
`<input>_files/` directory containing extracted images with relative references.
Image-capable converters write `<input>_files/image_manifest.json` with source
provenance when supported. During project import, missing or unreadable manifests are
replaced with fallback metadata so discovered image assets still reach `project/images/`.

## `source_to_md/excel_to_md.py`

Excel workbook converter for presentation source intake.

Supported formats:
- `.xlsx`
- `.xlsm`

Unsupported by default:
- `.xls` — resave as `.xlsx` first

```bash
python3 scripts/source_to_md/excel_to_md.py report.xlsx
python3 scripts/source_to_md/excel_to_md.py report.xlsx -o output.md
python3 scripts/source_to_md/excel_to_md.py report.xlsm --max-rows 200 --max-cols 40
```

Behavior:
- preserves workbook and sheet structure in Markdown
- exports visible sheets only
- trims empty outer rows and columns
- propagates merged-cell labels for readable Markdown tables
- exports formula cells as cached values; it does not recalculate formulas

Dependency:

```bash
pip install openpyxl
```

CSV/TSV files are already plain-text table sources and do not require this converter.

## `source_to_md/ppt_to_md.py`

Structured PowerPoint-to-Markdown converter for Open XML slide decks.

Supported formats include:
- `.pptx`, `.pptm`
- `.ppsx`, `.ppsm`
- `.potx`, `.potm`

```bash
python3 scripts/source_to_md/ppt_to_md.py sales_deck.pptx
python3 scripts/source_to_md/ppt_to_md.py sales_deck.pptx -o output.md
python3 scripts/source_to_md/ppt_to_md.py ./decks
python3 scripts/source_to_md/ppt_to_md.py ./decks -o ./markdown
python3 scripts/source_to_md/ppt_to_md.py template.ppsx -o output/template.md
```

Behavior:
- extracts slide text in reading order
- converts PowerPoint tables to Markdown tables
- exports embedded pictures to a sibling `_files/` directory

Dependency:

```bash
pip install python-pptx
```

Legacy `.ppt` is not parsed directly. Resave it as `.pptx` or export it to PDF first.

## `source_to_md/web_to_md.py`

Convert web pages to Markdown and download images locally.

```bash
python3 scripts/source_to_md/web_to_md.py https://example.com/article
python3 scripts/source_to_md/web_to_md.py https://url1.com https://url2.com
python3 scripts/source_to_md/web_to_md.py -f urls.txt
python3 scripts/source_to_md/web_to_md.py https://example.com -o output.md
```

When `curl_cffi` is installed (included in `requirements.txt`), this script
automatically impersonates a modern Chrome TLS fingerprint, which lets it
fetch WeChat Official Accounts (`mp.weixin.qq.com`) and other sites that
block Python's default TLS fingerprint. No extra flags needed. If
`curl_cffi` is not available, it falls back to plain `requests`.


## `rotate_images.py`

Fix image EXIF orientation in downloaded or imported assets.

```bash
python3 scripts/rotate_images.py auto projects/xxx_files
python3 scripts/rotate_images.py gen projects/xxx_files
python3 scripts/rotate_images.py fix fixes.json
```

Use this when extracted photos appear sideways after conversion or import.
