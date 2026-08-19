#!/usr/bin/env python3
"""
Generate sample source files for testing doc_to_md.py bundled wheels.

Creates one file per format in tests/sample_sources/:
  - sample.docx   (Word document with text + image)
  - sample.html   (HTML page with heading + paragraph + image)
  - sample.epub   (EPUB book with 2 chapters + image)
  - sample.ipynb  (Jupyter notebook with markdown + code + output)

Usage:
  python3 tests/generate_sample_sources.py
"""
import io
import json
import os
import struct
import zipfile
from pathlib import Path

OUT_DIR = Path(__file__).parent / "sample_sources"


def _make_minimal_png(width=100, height=50, color=(255, 0, 0)):
    """Create a minimal valid PNG file."""
    def _chunk(ctype, data):
        c = ctype + data
        crc = 0xFFFFFFFF
        for b in c:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + bytes(color) * width
    compressed = __import__("zlib").compress(raw)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


def make_docx(path: Path):
    """Create a minimal .docx with text and one image."""
    png_bytes = _make_minimal_png(120, 60, (0, 100, 200))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/media/image1.png" ContentType="image/png"/>
</Types>''')
        zf.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
        zf.writestr("word/_rels/document.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>''')
        zf.writestr("word/document.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
            xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Test Document</w:t></w:r></w:p>
<w:p><w:r><w:t>This is a test paragraph for DOCX conversion.</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Second paragraph with </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>bold</w:t></w:r><w:r><w:t> text.</w:t></w:r></w:p>
<w:p><w:r>
<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">
<wp:extent cx="1828800" cy="914400"/>
<wp:effectExtent l="0" t="0" r="0" b="0"/>
<wp:docPr id="1" name="Image1"/>
<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:blipFill><a:blip r:embed="rId1"/></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1828800" cy="914400"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>
</a:graphicData></a:graphic>
</wp:inline></w:drawing>
</w:r></w:p>
<w:p><w:r><w:t>End of document.</w:t></w:r></w:p>
</w:body>
</w:document>''')
        zf.writestr("word/media/image1.png", png_bytes)


def make_html(path: Path):
    """Create a simple HTML file."""
    path.write_text('''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Test Page</title></head>
<body>
<h1>Test HTML Page</h1>
<p>This is a <strong>test</strong> paragraph for HTML conversion.</p>
<h2>Subsection</h2>
<ul>
<li>Item one</li>
<li>Item two</li>
<li>Item three</li>
</ul>
<p>End of HTML content.</p>
</body>
</html>
''', encoding="utf-8")


def make_epub(path: Path):
    """Create a minimal EPUB with 2 chapters and 1 image."""
    png_bytes = _make_minimal_png(80, 40, (200, 50, 50))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebbs-package+xml"/>
</rootfiles>
</container>''')
        zf.writestr("OEBPS/content.opf", '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title>Test EPUB Book</dc:title>
<dc:creator>Test Author</dc:creator>
<dc:identifier id="bookid">test-epub-001</dc:identifier>
<dc:language>en</dc:language>
</metadata>
<manifest>
<item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
<item id="ch2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
<item id="cover" href="images/cover.png" media-type="image/png"/>
<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
</manifest>
<spine toc="ncx">
<itemref idref="ch1"/>
<itemref idref="ch2"/>
</spine>
</package>''')
        zf.writestr("OEBPS/toc.ncx", '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="test-epub-001"/></head>
<navMap>
<navPoint id="ch1" playOrder="1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint>
<navPoint id="ch2" playOrder="2"><navLabel><text>Chapter 2</text></navLabel><content src="chapter2.xhtml"/></navPoint>
</navMap>
</ncx>''')
        zf.writestr("OEBPS/chapter1.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
<h1>Chapter One</h1>
<p>This is the first chapter of the test EPUB.</p>
<p>It has <em>italic</em> and <strong>bold</strong> text.</p>
<img src="images/cover.png" alt="Cover"/>
</body>
</html>''')
        zf.writestr("OEBPS/chapter2.xhtml", '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
<h2>Chapter Two</h2>
<p>This is the second chapter.</p>
<ul><li>Bullet A</li><li>Bullet B</li></ul>
</body>
</html>''')
        zf.writestr("OEBPS/images/cover.png", png_bytes)


def make_ipynb(path: Path):
    """Create a Jupyter notebook with markdown + code + output cells."""
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "# Test Notebook\n\nThis notebook tests the IPYNB → Markdown conversion."
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "## Code Example\n\nBelow is a simple code cell:"
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": "x = 42\nprint(f'The answer is {x}')",
                "outputs": [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": "The answer is 42\n"
                    }
                ],
                "execution_count": 1
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "## Error Example\n\nThis cell produces an error:"
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": "1 / 0",
                "outputs": [
                    {
                        "output_type": "error",
                        "ename": "ZeroDivisionError",
                        "evalue": "division by zero",
                        "traceback": ["ZeroDivisionError: division by zero"]
                    }
                ],
                "execution_count": 2
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "End of notebook."
            }
        ]
    }
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = [
        ("sample.docx", make_docx),
        ("sample.html", make_html),
        ("sample.epub", make_epub),
        ("sample.ipynb", make_ipynb),
    ]

    print(f"Generating sample source files in: {OUT_DIR}")
    for name, fn in files:
        path = OUT_DIR / name
        fn(path)
        size = path.stat().st_size
        print(f"  {name:20s} {size:>8,} bytes")
    print(f"\nDone. {len(files)} files created.")
    print(f"\nTo test bundled wheels (simulating clean machine):")
    print(f"  python3 tests/test_bundled_wheels.py")


if __name__ == "__main__":
    main()
