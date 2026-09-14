import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import doc_to_md  # noqa: E402


class DocxStructureTest(TestCase):
    def test_headings_lists_tables_and_order_survive(self):
        html = (
            "<h1>I. Overview</h1><p>Before</p>"
            "<ol><li>First</li><li>Second</li></ol>"
            "<table><tr><td>Owner</td><td>Value</td></tr>"
            "<tr><td>Viettel</td><td>100</td></tr></table>"
            "<h2>1.1 Detail</h2><p>After</p>"
        )
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.docx"
            output = Path(directory) / "raw_source.md"
            source.write_bytes(b"stub")
            result = SimpleNamespace(value=html, messages=[])
            doc_to_md._ensure_vendored_deps()
            with patch("mammoth.convert_to_html", return_value=result), patch.object(
                doc_to_md, "_docx_image_occurrences", return_value=[]
            ):
                markdown = doc_to_md._convert_docx(source, output)

        expected = [
            "# I. Overview", "Before", "1. First", "2. Second",
            "| Owner | Value |", "| Viettel | 100 |", "## 1.1 Detail", "After",
        ]
        positions = [markdown.index(value) for value in expected]
        self.assertEqual(positions, sorted(positions))


class LegacyDocTest(TestCase):
    def test_libreoffice_docx_is_passed_to_docx_converter_and_cleaned(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.doc"
            output = Path(directory) / "raw_source.md"
            source.write_bytes(b"stub")

            def convert(args, **_kwargs):
                Path(args[args.index("--outdir") + 1], "source.docx").write_bytes(b"docx")
                return SimpleNamespace(returncode=0, stderr="")

            with patch.object(doc_to_md, "_find_soffice", return_value="soffice"), patch.object(
                doc_to_md.subprocess, "run", side_effect=convert
            ), patch.object(doc_to_md, "_convert_docx", return_value="converted") as convert_docx:
                self.assertEqual(doc_to_md._convert_doc(source, output), "converted")
                temporary_docx = convert_docx.call_args.args[0]

            self.assertFalse(temporary_docx.exists())

    def test_windows_falls_back_to_word_and_word_always_has_cleanup(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.doc"
            output = Path(directory) / "raw_source.md"
            source.write_bytes(b"stub")

            def word(_source, destination):
                destination.write_bytes(b"docx")
                return True

            with patch.object(doc_to_md, "_find_soffice", return_value=None), patch.object(
                doc_to_md, "_is_windows", return_value=True
            ), patch.object(doc_to_md, "_word_com_to_docx", side_effect=word), patch.object(
                doc_to_md, "_convert_docx", return_value="converted"
            ):
                self.assertEqual(doc_to_md._convert_doc(source, output), "converted")

            captured = {}

            def powershell(args, **kwargs):
                captured["script"] = args[-1]
                Path(kwargs["env"]["VPM_DOCX_OUTPUT"]).write_bytes(b"docx")
                return SimpleNamespace(returncode=0)

            with patch.object(doc_to_md.shutil, "which", return_value="powershell.exe"), patch.object(
                doc_to_md.subprocess, "run", side_effect=powershell
            ):
                self.assertTrue(doc_to_md._word_com_to_docx(source, Path(directory) / "word.docx"))
            self.assertIn("finally", captured["script"])
            self.assertIn(".Close($false)", captured["script"])
            self.assertIn(".Quit()", captured["script"])


if __name__ == "__main__":
    main()
