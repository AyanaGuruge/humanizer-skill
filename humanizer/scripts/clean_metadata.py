#!/usr/bin/env python3
"""
clean_metadata.py: remove hidden metadata and chatbot residue from writing deliverables.

What it handles
  Text (.txt .md .html .csv .tex ...)   invisible Unicode, odd spaces, pasted chatbot markers, tracking params
  Word / PowerPoint / Excel (.docx .pptx .xlsx and template/macro variants)
                                        document properties, revision IDs, local paths, thumbnails,
                                        zip timestamps, embedded image metadata, plus the text clean above
  PDF (.pdf)                            Info dictionary, XMP packets, page level metadata
  Images (.jpg .png .webp)              EXIF, XMP, IPTC, PNG text chunks, C2PA/JUMBF content credentials

What it cannot do (and says so in every report)
  Statistical text watermarks (patterns in word choice) and invisible pixel level image watermarks are not
  stored as metadata, so this tool can neither detect nor remove them. It does not make text undetectable.

Usage
  clean_metadata.py --check FILE...          dry run: show what is hidden in the file(s)
  clean_metadata.py FILE...                  write FILE.clean.EXT next to each input
  clean_metadata.py -o OUTDIR FILE...        write cleaned copies into OUTDIR
  clean_metadata.py --in-place FILE...       overwrite the originals
  cat draft.txt | clean_metadata.py -        clean stdin to stdout (report goes to stderr)
Run with python3 -I when the inputs are files you did not write yourself.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import struct
import subprocess
import sys
import unicodedata
import zipfile
import zlib
from collections import Counter
from pathlib import Path

LIMITS = (
    "Limits: this tool removes file metadata, invisible characters and pasted chatbot markers. It cannot "
    "detect or remove statistical text watermarks (token choice patterns) or invisible pixel level image "
    "watermarks, and it does not make a text undetectable."
)

AI_SIG = re.compile(
    r"(chat\s?gpt|openai|\bgpt-?\d|claude|anthropic|gemini|\bbard\b|copilot|perplexity|midjourney|dall[-· ]?e|"
    r"stable ?diffusion|firefly|\bgrok\b|deepseek|synthid|comfyui|automatic1111|c2pa|content ?credentials|"
    r"trainedAlgorithmicMedia|jumbf)",
    re.I,
)

# --------------------------------------------------------------------------------------
# Text level cleaning
# --------------------------------------------------------------------------------------

SPACE_MAP = {cp: " " for cp in list(range(0x2000, 0x200B)) + [0x202F, 0x205F]}
SPACE_MAP[0x2028] = "\n"
SPACE_MAP[0x2029] = "\n\n"
ALWAYS_REMOVE = {
    0x2060, 0x00AD, 0x180E, 0x034F, 0x3164, 0xFFA0, 0x115F, 0x1160, 0x17B4, 0x17B5, 0xFEFF,
    0x2061, 0x2062, 0x2063, 0x2064, 0x206A, 0x206B, 0x206C, 0x206D, 0x206E, 0x206F,
}
BIDI = {0x200E, 0x200F, 0x061C} | set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
SUSPECT = re.compile(
    "[­͏؜ᅟᅠ឴឵᠎ -‏ -  -⁯ㅤ"
    "︀-️﻿ﾠ\U000E0100-\U000E01EF]"
)
TAG_RUN = re.compile("[\U000E0000-\U000E007F]+")
NAMES = {
    0x200B: "zero width space", 0x200C: "zero width non joiner", 0x200D: "zero width joiner",
    0x2060: "word joiner", 0xFEFF: "BOM / zero width no break space", 0x00AD: "soft hyphen",
    0x202F: "narrow no break space", 0x2009: "thin space", 0x200A: "hair space",
    0x200E: "left to right mark", 0x200F: "right to left mark", 0x034F: "combining grapheme joiner",
    0x3164: "hangul filler", 0xFFA0: "halfwidth hangul filler", 0x2028: "line separator",
    0x2029: "paragraph separator", 0x00A0: "no break space",
}
NONLATIN_KEEP_ZWSP = {"THAI", "KHMER", "LAO", "MYANMAR", "TIBETAN"}


def _script(ch: str) -> str:
    try:
        return unicodedata.name(ch).split(" ")[0]
    except ValueError:
        return ""


def _latinish(ch: str) -> bool:
    if not ch:
        return True
    if ch.isascii():
        return True
    if _script(ch) == "LATIN":
        return True
    return unicodedata.category(ch)[0] in "PSZN"


def _emojiish(ch: str) -> bool:
    if not ch:
        return False
    cp = ord(ch)
    return (
        cp >= 0x1F000 or 0x2190 <= cp <= 0x2BFF or 0x2600 <= cp <= 0x27BF
        or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D, 0x3297, 0x3299, 0x20E3)
        or ch.isdigit() or ch in "#*"
    )


def _cjk(ch: str) -> bool:
    cp = ord(ch) if ch else 0
    return 0x3400 <= cp <= 0x4DBF or 0x4E00 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF


def _vis_neighbor(s: str, i: int, step: int) -> str:
    j = i + step
    while 0 <= j < len(s) and SUSPECT.match(s[j]):
        j += step
    return s[j] if 0 <= j < len(s) else ""


# Pasted chatbot residue. Each entry: (label, compiled regex, replacement)
def _utm_repl(m: re.Match) -> str:
    sep, tail = m.group("sep"), m.group("tail")
    if sep == "?":
        return "?" if tail else ""
    return sep if tail else ""


RESIDUE = [
    ("ChatGPT citation span (private use markers)", re.compile("cite(?:[^]*)+"), ""),
    ("ChatGPT entity span (private use markers)", re.compile("entity\\[\"[^\"]*\",\\s*\"([^\"]*)\"[^]*"), r"\1"),
    ("ChatGPT leftover private use markers", re.compile("[-]"), ""),
    ("ChatGPT contentReference/oaicite marker", re.compile(r"[ \t]?:?contentReference\[oaicite:\d+\]\{index=\d+\}"), ""),
    ("OpenAI source marker", re.compile(r"[ \t]?【[^】\n]{0,160}†[^】\n]{0,160}】"), ""),
    ("ChatGPT turnNsearchN marker", re.compile(r"[ \t]?(?:cite)?(?:turn\d+(?:search|news|view|image|file|product|forecast|finance|sports|calculator)\d+)+"), ""),
    ("Gemini [cite_start] marker", re.compile(r"\[cite_start\]"), ""),
    ("Gemini [cite: N] marker", re.compile(r"[ \t]?\[cite:\s*\d+(?:\s*,\s*\d+)*\]"), ""),
    ("cite tag from a chat interface", re.compile(r"</?(?:antml:)?cite\b[^>]*>"), ""),
    (
        "chatbot tracking parameter (utm_source) in a URL",
        re.compile(r"(?P<sep>\?|&amp;|&)utm_source=(?:chatgpt\.com|openai|copilot\.com|perplexity\.ai|perplexity|claude\.ai)(?P<tail>&amp;|&)?"),
        _utm_repl,
    ),
]

QUOTE_MAP = {"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "‚": "'"}


_NUMREF = re.compile(r"&#(?:[xX]([0-9a-fA-F]{1,6})|([0-9]{1,7}));")
_NAMED_INVISIBLE = {"&shy;": "\u00ad", "&ZeroWidthSpace;": "\u200b", "&zwnj;": "\u200c", "&zwj;": "\u200d",
                    "&lrm;": "\u200e", "&rlm;": "\u200f", "&NoBreak;": "\u2060", "&hairsp;": "\u200a",
                    "&thinsp;": "\u2009", "&ThinSpace;": "\u2009", "&VeryThinSpace;": "\u200a"}


def expose_invisible_refs(s: str, html_entities: bool = False) -> str:
    """Turn numeric (and, for HTML, named) references to invisible characters back into the characters,
    so clean_text can see them. Ordinary references such as &#38; or &amp; are left untouched."""

    def repl(m: re.Match) -> str:
        cp = int(m.group(1), 16) if m.group(1) else int(m.group(2))
        if cp > 0x10FFFF:
            return m.group(0)
        ch = chr(cp)
        if SUSPECT.match(ch) or TAG_RUN.match(ch) or 0xE200 <= cp <= 0xE206:
            return ch
        return m.group(0)

    s = _NUMREF.sub(repl, s)
    if html_entities:
        for k, v in _NAMED_INVISIBLE.items():
            s = s.replace(k, v)
    return s



def clean_text(s: str, straight_quotes: bool = False, aggressive: bool = False) -> tuple[str, dict]:
    """Return (clean text, report). Report keys: removed (Counter), notes (dict)."""
    removed: Counter = Counter()
    notes: dict = {}

    for label, rx, repl in RESIDUE:
        s, n = rx.subn(repl, s)
        if n:
            removed[label] += n

    def tag_repl(m: re.Match) -> str:
        start = m.start()
        before = m.string[start - 1] if start else ""
        if before == "\U0001F3F4":  # legitimate subdivision flag emoji (England, Scotland, Wales)
            return m.group(0)
        decoded = "".join(chr(ord(c) - 0xE0000) for c in m.group(0) if 0x20 <= ord(c) - 0xE0000 < 0x7F)
        removed["Unicode tag characters (hidden text)"] += len(m.group(0))
        if decoded:
            notes.setdefault("hidden_tag_message", []).append(decoded[:300])
        return ""

    if TAG_RUN.search(s):
        s = TAG_RUN.sub(tag_repl, s)

    if SUSPECT.search(s):
        has_rtl = any(unicodedata.bidirectional(c) in ("R", "AL") for c in s)
        out, last = [], 0
        for m in SUSPECT.finditer(s):
            i, ch = m.start(), m.group(0)
            cp = ord(ch)
            prev, nxt = _vis_neighbor(s, i, -1), _vis_neighbor(s, i, 1)
            repl: str | None = ""  # default: remove
            if cp in SPACE_MAP:
                repl = SPACE_MAP[cp]
                if cp == 0x200A or cp == 0x2009 or cp == 0x202F or cp in range(0x2000, 0x200B):
                    pass
            elif cp == 0x200B:
                if _script(prev) in NONLATIN_KEEP_ZWSP or _script(nxt) in NONLATIN_KEEP_ZWSP:
                    repl = None
            elif cp in (0x200C, 0x200D):
                if _emojiish(prev) or _emojiish(nxt) or not (_latinish(prev) and _latinish(nxt)):
                    repl = None
            elif cp in BIDI:
                if has_rtl:
                    repl = None
            elif 0xFE00 <= cp <= 0xFE0F:
                if _emojiish(prev) or (_cjk(prev) and cp != 0xFE0F):
                    repl = None
            elif 0xE0100 <= cp <= 0xE01EF:
                if _cjk(prev):
                    repl = None
            elif cp in ALWAYS_REMOVE:
                repl = ""
            if repl is None:
                continue
            out.append(s[last:i])
            out.append(repl)
            last = m.end()
            removed[NAMES.get(cp, f"U+{cp:04X}") + (" (replaced by plain space)" if repl == " " else "")] += 1
        out.append(s[last:])
        s = "".join(out)

    nbsp = s.count(" ")
    if nbsp:
        if aggressive:
            s = s.replace(" ", " ")
            removed["no break space (replaced by plain space)"] += nbsp
        else:
            notes["no_break_spaces_kept"] = nbsp

    if straight_quotes:
        n = sum(s.count(k) for k in QUOTE_MAP)
        if n:
            for k, v in QUOTE_MAP.items():
                s = s.replace(k, v)
            removed["curly quotes converted to straight"] += n

    mixed = []
    for w in re.findall(r"\w+", s):
        if w.isascii():
            continue
        scripts = {_script(c) for c in w if c.isalpha()}
        if "LATIN" in scripts and scripts & {"CYRILLIC", "GREEK"}:
            mixed.append(w)
    if mixed:
        notes["mixed_script_words_possible_homoglyphs"] = sorted(set(mixed))[:15]

    return s, {"removed": removed, "notes": notes}


def _merge(report: dict, sub: dict) -> None:
    for k, v in sub.get("removed", {}).items():
        report["removed"][k] += v
    for k, v in sub.get("notes", {}).items():
        if isinstance(v, list):
            report["notes"].setdefault(k, [])
            for x in v:
                if x not in report["notes"][k]:
                    report["notes"][k].append(x)
        else:
            report["notes"][k] = report["notes"].get(k, 0) + v


# --------------------------------------------------------------------------------------
# Images (lossless: bytes are removed, pixels are never re-encoded)
# --------------------------------------------------------------------------------------

def parse_exif(buf: bytes) -> dict:
    info: dict = {}
    try:
        e = "<" if buf[:2] == b"II" else ">" if buf[:2] == b"MM" else None
        if not e:
            return info
        off = struct.unpack(e + "I", buf[4:8])[0]
        n = struct.unpack(e + "H", buf[off:off + 2])[0]
        for k in range(min(n, 200)):
            p = off + 2 + 12 * k
            tag, typ, cnt = struct.unpack(e + "HHI", buf[p:p + 8])
            val = buf[p + 8:p + 12]
            if tag == 0x0112:
                info["orientation"] = struct.unpack(e + "H", val[:2])[0]
            elif tag in (0x010F, 0x0110, 0x0131, 0x0132, 0x013B, 0x8298) and typ == 2:
                data = val[:cnt] if cnt <= 4 else buf[struct.unpack(e + "I", val)[0]:][:cnt]
                name = {0x010F: "make", 0x0110: "model", 0x0131: "software", 0x0132: "datetime", 0x013B: "artist", 0x8298: "copyright"}[tag]
                info[name] = data.split(b"\0")[0].decode("latin1", "replace")
            elif tag == 0x8825:
                info["gps"] = True
    except Exception:
        pass
    return info


def _orientation_exif(orientation: int) -> bytes:
    tiff = b"MM\x00\x2a\x00\x00\x00\x08" + struct.pack(">H", 1) + struct.pack(">HHIHH", 0x0112, 3, 1, orientation, 0) + b"\x00\x00\x00\x00"
    payload = b"Exif\x00\x00" + tiff
    return b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload


def jpeg_strip(data: bytes) -> tuple[bytes, dict]:
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    found: dict = {"dropped": Counter(), "exif": {}, "flags": []}
    n = len(data)
    chunks = [b"\xff\xd8"]
    i = 2
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m == 0xD9:
            chunks.append(b"\xff\xd9")
            if n - (i + 2) > 0:
                found["dropped"]["trailing bytes after image end"] += n - (i + 2)
            break
        if m == 0x01 or 0xD0 <= m <= 0xD8 or m == 0x00:
            chunks.append(data[i:i + 2])
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        seg = data[i:i + 2 + length]
        payload = seg[4:]
        keep = True
        if m == 0xE1:
            keep = False
            if payload.startswith(b"Exif\x00\x00"):
                found["exif"] = parse_exif(payload[6:])
                if set(found["exif"]) - {"orientation"}:
                    found["dropped"]["EXIF"] += 1
            else:
                found["dropped"]["XMP / APP1"] += 1
            if AI_SIG.search(payload[:20000].decode("latin1", "replace")):
                found["flags"].append("AI related marker inside XMP/EXIF: " + AI_SIG.search(payload[:20000].decode("latin1", "replace")).group(0))
        elif m == 0xE2:
            keep = payload.startswith(b"ICC_PROFILE\x00")
            if not keep:
                found["dropped"]["APP2 (multi picture data)"] += 1
        elif m == 0xEE:
            keep = payload.startswith(b"Adobe")
            if not keep:
                found["dropped"]["APP14"] += 1
        elif m == 0xEB:
            keep = False
            found["dropped"]["APP11 (JUMBF / content credentials)"] += 1
            if b"c2pa" in payload.lower() or b"jumb" in payload.lower():
                found["flags"].append("C2PA / Content Credentials manifest present")
        elif m in (0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEC, 0xED, 0xEF):
            keep = False
            found["dropped"][f"APP{m - 0xE0}"] += 1
        elif m == 0xFE:
            keep = False
            found["dropped"]["JPEG comment"] += 1
            if AI_SIG.search(payload.decode("latin1", "replace")):
                found["flags"].append("AI related marker in JPEG comment")
        if keep:
            chunks.append(seg)
        i += 2 + length
        if m == 0xDA:
            j = i
            while j < n - 1:
                if data[j] == 0xFF and data[j + 1] != 0x00 and not (0xD0 <= data[j + 1] <= 0xD7):
                    break
                j += 1
            chunks.append(data[i:j])
            i = j
    orient = found["exif"].get("orientation", 1)
    if orient not in (0, 1):
        pos = 2 if len(chunks) > 1 and chunks[1][:2] == b"\xff\xe0" else 1
        chunks.insert(pos, _orientation_exif(orient))
        if found["dropped"].get("EXIF"):
            found["flags"].append(f"orientation tag {orient} kept (only that tag) so the picture still displays upright")
    return b"".join(chunks), found


PNG_KEEP = {"IHDR", "PLTE", "IDAT", "IEND", "tRNS", "gAMA", "cHRM", "sRGB", "iCCP", "sBIT", "bKGD", "hIST", "pHYs", "sPLT", "acTL", "fcTL", "fdAT", "cICP", "mDCv", "cLLi"}


def _png_text(name: str, body: bytes) -> tuple[str, str]:
    try:
        key, rest = body.split(b"\0", 1)
        if name == "tEXt":
            return key.decode("latin1"), rest.decode("latin1", "replace")
        if name == "zTXt":
            return key.decode("latin1"), zlib.decompressobj().decompress(rest[1:], 100000).decode("utf-8", "replace")
        flag, rest = rest[0], rest[2:]
        _lang, rest = rest.split(b"\0", 1)
        _tkey, text = rest.split(b"\0", 1)
        if flag:
            text = zlib.decompressobj().decompress(text, 100000)
        return key.decode("utf-8", "replace"), text.decode("utf-8", "replace")
    except Exception:
        return "?", ""


def png_strip(data: bytes) -> tuple[bytes, dict]:
    sig = b"\x89PNG\r\n\x1a\n"
    if data[:8] != sig:
        raise ValueError("not a PNG")
    found: dict = {"dropped": Counter(), "text": {}, "flags": []}
    out = bytearray(sig)
    i = 8
    while i + 8 <= len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        name = data[i + 4:i + 8].decode("latin1")
        chunk = data[i:i + 12 + length]
        body = data[i + 8:i + 8 + length]
        if name in PNG_KEEP:
            out += chunk
        else:
            found["dropped"][name] += 1
            if name in ("tEXt", "zTXt", "iTXt"):
                k, v = _png_text(name, body)
                found["text"][k] = v[:80]
                if AI_SIG.search(k + " " + v[:4000]) or k.lower() in ("parameters", "prompt", "workflow"):
                    found["flags"].append(f"generation settings or AI marker in PNG text chunk '{k}'")
            if name == "caBX":
                found["flags"].append("C2PA / Content Credentials manifest present")
        i += 12 + length
        if name == "IEND":
            if len(data) - i > 0:
                found["dropped"]["trailing bytes after image end"] += len(data) - i
            break
    return bytes(out), found


def webp_strip(data: bytes) -> tuple[bytes, dict]:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP")
    found: dict = {"dropped": Counter(), "flags": []}
    i, chunks = 12, []
    while i + 8 <= len(data):
        tag = data[i:i + 4]
        size = struct.unpack("<I", data[i + 4:i + 8])[0]
        body = data[i + 8:i + 8 + size]
        pad = b"\0" if size % 2 else b""
        if tag in (b"EXIF", b"XMP ", b"C2PA"):
            found["dropped"][tag.decode().strip()] += 1
            if tag == b"C2PA" or b"c2pa" in body.lower():
                found["flags"].append("C2PA / Content Credentials manifest present")
            if AI_SIG.search(body[:20000].decode("latin1", "replace")):
                found["flags"].append("AI related marker inside WebP metadata")
        else:
            if tag == b"VP8X" and body:
                body = bytes([body[0] & ~0x0C & 0xFF]) + body[1:]
            chunks.append(tag + struct.pack("<I", len(body)) + body + pad)
        i += 8 + size + (size % 2)
    payload = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(payload)) + payload, found


def clean_image_bytes(data: bytes, ext: str) -> tuple[bytes, dict]:
    ext = ext.lower()
    if ext in (".jpg", ".jpeg"):
        return jpeg_strip(data)
    if ext == ".png":
        return png_strip(data)
    if ext == ".webp":
        return webp_strip(data)
    raise ValueError("unsupported image type")


# --------------------------------------------------------------------------------------
# Office Open XML (.docx .pptx .xlsx)
# --------------------------------------------------------------------------------------

TEXT_PART = re.compile(
    r"^(word/(document|header\d*|footer\d*|footnotes|endnotes|comments\w*)\.xml"
    r"|ppt/(slides|notesSlides|slideLayouts|slideMasters)/[^/]+\.xml|ppt/comments/.*\.xml"
    r"|xl/(sharedStrings|comments\d*)\.xml|xl/worksheets/sheet\d+\.xml|xl/drawings/.*\.xml"
    r"|.*\.rels)$"
)
EMPTY_CUSTOM = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"/>'
)


def _tag_value(xml: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", xml, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m and m.group(1).strip() else None


def _blank_tag(xml: str, tag: str, value: str | None) -> str:
    pat = re.compile(rf"<{tag}(\s[^>]*)?>.*?</{tag}>|<{tag}(\s[^>]*)?/>", re.S)
    if value is None:
        return pat.sub("", xml)
    return pat.sub(lambda m: f"<{tag}{m.group(1) or m.group(2) or ''}>{value}</{tag}>", xml)


def clean_ooxml(src: Path, dst: Path | None, opts: argparse.Namespace) -> dict:
    report = {"kind": "ooxml", "found": {}, "removed": Counter(), "notes": {}, "flags": []}
    check = dst is None
    out_entries: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        total_unpacked = sum(i.file_size for i in zin.infolist())
        if total_unpacked > 500 * 1024 * 1024:
            raise ValueError("archive unpacks to more than 500 MB; refusing")
        drop_targets = {n for n in names if re.match(r"docProps/thumbnail\.\w+$", n)}
        for info in zin.infolist():
            name = info.filename
            if name.endswith("/"):
                continue
            data = zin.read(name)

            if name in drop_targets:
                report["removed"]["document thumbnail"] += 1
                continue

            if name == "_rels/.rels" and drop_targets:
                x = data.decode("utf-8", "replace")
                for t in drop_targets:
                    x = re.sub(rf'<Relationship\b[^>]*Target="{re.escape(t)}"[^>]*/>', "", x)
                data = x.encode("utf-8")

            elif name == "docProps/core.xml":
                x = data.decode("utf-8", "replace")
                for tag, label in (("dc:creator", "author"), ("cp:lastModifiedBy", "last modified by"), ("dc:title", "title"),
                                   ("dc:subject", "subject"), ("cp:keywords", "keywords"), ("dc:description", "description/comments"),
                                   ("cp:category", "category"), ("dcterms:created", "created"), ("dcterms:modified", "modified"),
                                   ("cp:revision", "revision")):
                    v = _tag_value(x, tag)
                    if v and not (tag == "cp:revision" and v == "1") and not (tag == "dc:title" and not opts.strip_title):
                        report["found"][label] = v
                    elif v and tag == "dc:title":
                        report["notes"]["title_kept"] = v
                had = {k for k in report["found"] if k in ("author", "last modified by", "subject", "keywords", "description/comments", "category", "created", "modified")}
                x = _blank_tag(x, "dc:creator", opts.set_author or "")
                x = _blank_tag(x, "cp:lastModifiedBy", "")
                for tag in ("dc:subject", "cp:keywords", "dc:description", "cp:category", "cp:contentStatus"):
                    x = _blank_tag(x, tag, None)
                if opts.strip_title:
                    x = _blank_tag(x, "dc:title", None)
                if not opts.keep_dates:
                    x = _blank_tag(x, "dcterms:created", None)
                    x = _blank_tag(x, "dcterms:modified", None)
                x = _blank_tag(x, "cp:revision", "1")
                if had or opts.strip_title:
                    report["removed"]["core properties reset"] += 1
                data = x.encode("utf-8")

            elif name == "docProps/app.xml":
                app_hit = False
                x = data.decode("utf-8", "replace")
                for tag, label in (("Application", "application"), ("AppVersion", "application version"), ("Company", "company"),
                                   ("Manager", "manager"), ("Template", "template"), ("TotalTime", "editing time")):
                    v = _tag_value(x, tag)
                    if v:
                        report["found"][label] = v
                        app_hit = True
                    x = _blank_tag(x, tag, None)
                if app_hit:
                    report["removed"]["application properties reset"] += 1
                data = x.encode("utf-8")

            elif name == "docProps/custom.xml":
                names_found = re.findall(r'<property\b[^>]*\bname="([^"]*)"', data.decode("utf-8", "replace"))
                if names_found:
                    report["found"]["custom properties"] = ", ".join(names_found[:12])
                    report["removed"]["custom properties"] += len(names_found)
                data = EMPTY_CUSTOM.encode("utf-8")

            elif re.match(r"(word|ppt|xl)/media/[^/]+\.(jpe?g|png|webp)$", name, re.I):
                try:
                    cleaned, f = clean_image_bytes(data, Path(name).suffix)
                    gained = sum(f["dropped"].values())
                    if gained:
                        report["removed"]["metadata blocks in embedded images"] += gained
                    report["flags"].extend(f.get("flags", []))
                    if f.get("exif", {}).get("gps"):
                        report["flags"].append(f"embedded image {name} carried GPS coordinates")
                    data = cleaned
                except Exception:
                    report["notes"].setdefault("embedded_images_skipped", []).append(name)

            elif TEXT_PART.match(name) or name.endswith(".xml"):
                x = data.decode("utf-8", "replace")
                if TEXT_PART.match(name):
                    x = expose_invisible_refs(x)
                    x, sub = clean_text(x, opts.straight_quotes, opts.aggressive)
                    _merge(report, sub)
                if name.startswith("word/") and name.endswith(".xml"):
                    x, n = re.subn(r'\sw:rsid\w*="[0-9A-Fa-f]{8}"', "", x)
                    if n:
                        report["removed"]["revision session IDs (rsid)"] += n
                    x, n = re.subn(r"<w:rsids>.*?</w:rsids>", "", x, flags=re.S)
                    if n:
                        report["removed"]["rsid table in settings"] += n
                if "absPath" in x:
                    x, n = re.subn(r"<mc:AlternateContent[^>]*>\s*<mc:Choice[^>]*>\s*<x15ac:absPath[^>]*/>\s*</mc:Choice>\s*</mc:AlternateContent>", "", x)
                    if n:
                        report["removed"]["local file path (absPath)"] += n
                authors = set(re.findall(r'\b(?:w:author|w15:author)="([^"]+)"', x)) | set(re.findall(r'<p:cmAuthor\b[^>]*\bname="([^"]+)"', x))
                if authors:
                    report["found"].setdefault("comment/revision authors", set()).update(authors)
                if opts.anonymize_authors and (authors or "userId" in x or "w:initials" in x):
                    x = re.sub(r'\b(w:author|w15:author)="[^"]*"', r'\1="Author"', x)
                    x = re.sub(r'\bw:initials="[^"]*"', 'w:initials="A"', x)
                    x = re.sub(r'(<p:cmAuthor\b[^>]*?)\bname="[^"]*"', r'\1name="Author"', x)
                    x = re.sub(r'\b(w15:userId|userId|providerId)="[^"]*"', r'\1=""', x)
                    report["removed"]["comment/revision author names"] += len(authors)
                if name == "word/document.xml":
                    ins, dele, hidden = len(re.findall(r"<w:ins\b", x)), len(re.findall(r"<w:del\b", x)), len(re.findall(r"<w:vanish\b", x))
                    if ins or dele:
                        report["flags"].append(f"{ins} tracked insertions and {dele} tracked deletions are still in the document (accept or reject them to remove)")
                    if hidden:
                        report["flags"].append(f"{hidden} runs of hidden text (w:vanish) are still in the document")
                if name == "word/comments.xml":
                    c = len(re.findall(r"<w:comment\b", x))
                    if c:
                        report["flags"].append(f"{c} comments are still in the document")
                data = x.encode("utf-8")

            out_entries.append((name, data))

    if "comment/revision authors" in report["found"]:
        report["found"]["comment/revision authors"] = ", ".join(sorted(report["found"]["comment/revision authors"]))
    if any(AI_SIG.search(str(v)) for v in report["found"].values()):
        report["flags"].append("AI related text found in document properties: " + "; ".join(f"{k}={v}" for k, v in report["found"].items() if AI_SIG.search(str(v))))

    if not check:
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, data in out_entries:
                zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.create_system = 0
                zout.writestr(zi, data)
        report["removed"]["zip entry timestamps normalised"] += 1
    return report


# --------------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------------

def clean_pdf(src: Path, dst: Path | None, opts: argparse.Namespace) -> dict:
    import pikepdf

    report = {"kind": "pdf", "found": {}, "removed": Counter(), "notes": {}, "flags": []}
    with pikepdf.open(src) as pdf:
        if "/Info" in pdf.trailer:
            for k, v in pdf.trailer["/Info"].items():
                try:
                    report["found"][str(k).lstrip("/")] = str(v)[:120]
                except Exception:
                    pass
        xmp_count = 0
        for obj in pdf.objects:
            try:
                if isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)) and "/Metadata" in obj:
                    try:
                        raw = obj["/Metadata"].read_bytes().decode("utf-8", "replace")
                        if AI_SIG.search(raw):
                            report["flags"].append("AI related marker inside XMP: " + AI_SIG.search(raw).group(0))
                        for tag in ("xmp:CreatorTool", "pdf:Producer", "dc:creator"):
                            mm = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", raw, re.S)
                            if mm:
                                report["found"]["xmp " + tag] = re.sub(r"<[^>]+>", " ", mm.group(1)).strip()[:120]
                    except Exception:
                        pass
                    xmp_count += 1
                    if dst:
                        del obj["/Metadata"]
                if isinstance(obj, pikepdf.Dictionary) and "/PieceInfo" in obj and dst:
                    del obj["/PieceInfo"]
                    report["removed"]["application private data (PieceInfo)"] += 1
            except Exception:
                continue
        if xmp_count:
            report["removed"]["XMP metadata packets"] += xmp_count
        if "/Info" in pdf.trailer:
            report["removed"]["Info dictionary entries"] += len(pdf.trailer["/Info"].keys())
            if dst:
                del pdf.trailer["/Info"]
        if any(AI_SIG.search(str(v)) for v in report["found"].values()):
            report["flags"].append("AI related text in PDF metadata: " + "; ".join(f"{k}={v}" for k, v in report["found"].items() if AI_SIG.search(str(v))))
        if dst:
            pdf.save(dst)
    try:
        txt = subprocess.run(["pdftotext", str(src), "-"], capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
        _, sub = clean_text(txt)
        if sub["removed"] or sub["notes"]:
            report["notes"]["text_layer_findings"] = {**{k: v for k, v in sub["removed"].items()}, **sub["notes"]}
            report["flags"].append("the PDF text layer contains hidden characters or chatbot markers; fix them in the source file and export again (a PDF text layer cannot be cleaned safely in place)")
    except Exception:
        pass
    return report


# --------------------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------------------

TEXT_EXT = {".txt", ".md", ".markdown", ".html", ".htm", ".csv", ".tsv", ".tex", ".rst", ".srt", ".vtt"}
OOXML_EXT = {".docx", ".docm", ".dotx", ".pptx", ".pptm", ".potx", ".xlsx", ".xlsm", ".xltx"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def process(path: Path, opts: argparse.Namespace) -> dict:
    ext = path.suffix.lower()
    check = opts.check
    if opts.in_place:
        dst = path
    elif opts.outdir:
        Path(opts.outdir).mkdir(parents=True, exist_ok=True)
        dst = Path(opts.outdir) / path.name
    else:
        dst = path.with_name(path.stem + ".clean" + path.suffix)
    result: dict = {"file": str(path), "type": ext.lstrip(".")}
    tmp = dst.with_name(dst.name + ".tmp") if not check else None
    try:
        if ext in TEXT_EXT:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig", errors="strict") if raw[:3] == b"\xef\xbb\xbf" else raw.decode("utf-8")
            if raw[:3] == b"\xef\xbb\xbf":
                pre = {"removed": Counter({"BOM / zero width no break space": 1}), "notes": {}}
            else:
                pre = None
            if ext in (".html", ".htm"):
                text = expose_invisible_refs(text, html_entities=True)
            new, rep = clean_text(text, opts.straight_quotes, opts.aggressive)
            if pre:
                _merge(rep, pre)
            result.update(kind="text", removed=rep["removed"], notes=rep["notes"], found={}, flags=[])
            if not check:
                tmp.write_text(new, encoding="utf-8")
        elif ext in OOXML_EXT:
            result.update(clean_ooxml(path, None if check else tmp, opts))
        elif ext == ".pdf":
            result.update(clean_pdf(path, None if check else tmp, opts))
        elif ext in IMAGE_EXT:
            new, f = clean_image_bytes(path.read_bytes(), ext)
            found = {k: v for k, v in (f.get("exif") or {}).items() if k != "orientation"}
            found.update({f"text chunk {k}": v for k, v in (f.get("text") or {}).items()})
            result.update(kind="image", found=found, removed=Counter(f["dropped"]), notes={}, flags=f.get("flags", []))
            if f.get("exif", {}).get("gps"):
                result["flags"].append("GPS coordinates were embedded in the picture")
            if not check:
                tmp.write_bytes(new)
        else:
            result.update(kind="unsupported", error="unsupported file type; for other formats try: exiftool -all= FILE", found={}, removed=Counter(), notes={}, flags=[])
            return result
        if not check:
            tmp.replace(dst)
            result["written"] = str(dst)
    except UnicodeDecodeError:
        result.update(error="file is not valid UTF-8 text; skipped")
    except Exception as exc:  # report and continue with the other files
        result.update(error=f"{type(exc).__name__}: {exc}")
        if tmp and tmp.exists():
            tmp.unlink()
    return result


def render(result: dict) -> str:
    lines = [f"FILE  {result['file']}  ({result.get('type')})"]
    if result.get("error"):
        lines.append(f"  ERROR  {result['error']}")
        return "\n".join(lines)
    if result.get("found"):
        lines.append("  hidden metadata found:")
        for k, v in result["found"].items():
            lines.append(f"    {k}: {v}")
    if result.get("removed"):
        lines.append("  removed or reset:" if "written" in result else "  would remove or reset:")
        for k, v in result["removed"].items():
            lines.append(f"    {k}: {v}")
    else:
        lines.append("  nothing to remove" if "written" in result else "  nothing found")
    notes = result.get("notes") or {}
    if notes.get("hidden_tag_message"):
        lines.append("  SECURITY NOTE  hidden Unicode tag text (possible smuggled instruction): " + " | ".join(notes["hidden_tag_message"]))
    if notes.get("mixed_script_words_possible_homoglyphs"):
        lines.append("  NOTE  words mixing Latin with Cyrillic or Greek letters (possible lookalike characters, not changed): " + ", ".join(notes["mixed_script_words_possible_homoglyphs"]))
    if notes.get("no_break_spaces_kept"):
        lines.append(f"  note  {notes['no_break_spaces_kept']} no break spaces kept (often legitimate; use --aggressive to convert)")
    for other in ("text_layer_findings", "embedded_images_skipped"):
        if notes.get(other):
            lines.append(f"  note  {other.replace('_', ' ')}: {notes[other]}")
    for flag in dict.fromkeys(result.get("flags", [])):
        lines.append(f"  flag  {flag}")
    if result.get("written"):
        lines.append(f"  written  {result['written']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove hidden metadata, invisible characters and chatbot residue.")
    ap.add_argument("paths", nargs="+", help="files or folders; use - for stdin text")
    ap.add_argument("--check", action="store_true", help="dry run, write nothing")
    ap.add_argument("-o", "--outdir", help="write cleaned copies into this folder")
    ap.add_argument("--in-place", action="store_true", help="overwrite originals")
    ap.add_argument("-r", "--recursive", action="store_true", help="descend into folders")
    ap.add_argument("--set-author", default="", help="author name to write instead of blank (Office files)")
    ap.add_argument("--keep-dates", action="store_true", help="keep created and modified dates (Office files)")
    ap.add_argument("--strip-title", action="store_true", help="also blank the document title (Office files)")
    ap.add_argument("--anonymize-authors", action="store_true", help="rename comment and revision authors to 'Author'")
    ap.add_argument("--straight-quotes", action="store_true", help="convert curly quotes to straight quotes")
    ap.add_argument("--aggressive", action="store_true", help="also convert no break spaces to plain spaces")
    ap.add_argument("--json", action="store_true", help="machine readable report")
    opts = ap.parse_args()

    if opts.paths == ["-"]:
        new, rep = clean_text(sys.stdin.read(), opts.straight_quotes, opts.aggressive)
        sys.stdout.write(new)
        res = {"file": "<stdin>", "type": "text", "found": {}, "removed": rep["removed"], "notes": rep["notes"], "flags": []}
        print(json.dumps(res, default=lambda o: dict(o) if isinstance(o, Counter) else str(o)) if opts.json else render(res), file=sys.stderr)
        print(LIMITS, file=sys.stderr)
        return 0

    files: list[Path] = []
    for p in map(Path, opts.paths):
        if p.is_dir():
            it = p.rglob("*") if opts.recursive else p.glob("*")
            files += sorted(f for f in it if f.is_file() and ".clean." not in f.name and f.suffix.lower() in TEXT_EXT | OOXML_EXT | IMAGE_EXT | {".pdf"})
        elif p.exists():
            files.append(p)
        else:
            print(f"missing: {p}", file=sys.stderr)
    results = [process(f, opts) for f in files]
    if opts.json:
        print(json.dumps({"results": results, "limits": LIMITS, "generated": datetime.datetime.now(datetime.timezone.utc).isoformat()},
                         default=lambda o: dict(o) if isinstance(o, Counter) else sorted(o) if isinstance(o, set) else str(o), indent=2))
    else:
        print("\n\n".join(render(r) for r in results))
        print("\n" + LIMITS)
    return 1 if any(r.get("error") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
