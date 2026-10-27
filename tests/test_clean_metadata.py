"""Smoke tests for scripts/clean_metadata.py. Run: python3 -m unittest discover -s tests"""
import io, struct, subprocess, sys, tempfile, unittest, zipfile, zlib
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "humanizer" / "scripts" / "clean_metadata.py"
sys.path.insert(0, str(SCRIPT.parent))
import clean_metadata as cm  # noqa: E402


def png_with_text() -> bytes:
    def chunk(t, body):
        return struct.pack(">I", len(body)) + t + body + struct.pack(">I", zlib.crc32(t + body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"tEXt", b"parameters\x00prompt: a cat") + chunk(b"caBX", b"c2pa") + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class TextCleaning(unittest.TestCase):
    def test_invisible_and_residue(self):
        s = "Hi​ there­ :contentReference[oaicite:0]{index=0} https://x.com/?utm_source=chatgpt.com"
        out, rep = cm.clean_text(s)
        self.assertEqual(out, "Hi there https://x.com/")
        self.assertTrue(rep["removed"])

    def test_tag_characters_decoded(self):
        hidden = "".join(chr(0xE0000 + ord(c)) for c in "secret")
        out, rep = cm.clean_text("ok" + hidden)
        self.assertEqual(out, "ok")
        self.assertEqual(rep["notes"]["hidden_tag_message"], ["secret"])

    def test_emoji_sequences_survive(self):
        s = "❤️ \U0001F468‍\U0001F469"
        self.assertEqual(cm.clean_text(s)[0], s)

    def test_idempotent(self):
        once = cm.clean_text("a​b :contentReference[oaicite:1]{index=1}")[0]
        self.assertEqual(cm.clean_text(once)[0], once)


class Files(unittest.TestCase):
    def test_png_chunks_removed_pixels_kept(self):
        out, found = cm.png_strip(png_with_text())
        self.assertNotIn(b"tEXt", out)
        self.assertNotIn(b"caBX", out)
        self.assertIn(b"IDAT", out)
        self.assertTrue(found["flags"])

    def test_docx_properties_reset(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.docx"
            doc = Document()
            doc.core_properties.author = "Someone"
            doc.add_paragraph("Hello​ world")
            doc.save(src)
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), "-o", str(Path(d) / "out"), str(src)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = Path(d) / "out" / "a.docx"
            self.assertEqual(Document(out).core_properties.author, "")
            self.assertEqual(Document(out).paragraphs[0].text, "Hello world")
            with zipfile.ZipFile(out) as z:
                self.assertEqual({i.date_time for i in z.infolist()}, {(1980, 1, 1, 0, 0, 0)})


if __name__ == "__main__":
    unittest.main()
