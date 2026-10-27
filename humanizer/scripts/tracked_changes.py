#!/usr/bin/env python3
"""
tracked_changes.py: deliver a rewrite as Word tracked changes, so the person can accept or reject each edit.

Usage
  tracked_changes.py SOURCE.docx --dump paragraphs.txt
        write the editable paragraphs (blank line separated) to a text file
  tracked_changes.py SOURCE.docx REWRITTEN.txt -o OUT.docx [--author NAME]
        REWRITTEN.txt must hold the same number of paragraphs, in the same order, as the dump

Editable paragraphs are those with text and no pictures, fields, links or footnote marks; others are left as they are.
Inside an edited paragraph, formatting of the first run is applied to all of it (limitation).
Run python3 -I when SOURCE comes from outside.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import html
import re
import sys
import zipfile
from pathlib import Path

PARA = re.compile(r"<w:p[ >].*?</w:p>", re.S)
SKIP = re.compile(r"<w:(drawing|pict|fldChar|fldSimple|hyperlink|footnoteReference|endnoteReference|object|sdt)\b")


def text_of(p: str) -> str:
    return "".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, re.S))


def editable(p: str) -> bool:
    return bool(text_of(p).strip()) and not SKIP.search(p) and "<w:ins " not in p and "<w:del " not in p


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(p: str, new: str, ids: list[int], author: str, date: str) -> str:
    old = text_of(p)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
    rpr = re.search(r"<w:rPr>.*?</w:rPr>", p, re.S)
    head = re.match(r"<w:p[^>]*>", p).group(0)
    rp = rpr.group(0) if rpr else ""
    tok = lambda t: re.findall(r"\s+|[^\s]+", t)
    a, b = tok(old), tok(new)
    out = []

    def attrs() -> str:
        ids[0] += 1
        return f'w:id="{ids[0]}" w:author="{esc(author)}" w:date="{date}"'

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            out.append(f'<w:r>{rp}<w:t xml:space="preserve">{esc("".join(a[i1:i2]))}</w:t></w:r>')
            continue
        if i2 > i1:
            out.append(f'<w:del {attrs()}><w:r>{rp}<w:delText xml:space="preserve">{esc("".join(a[i1:i2]))}</w:delText></w:r></w:del>')
        if j2 > j1:
            out.append(f'<w:ins {attrs()}><w:r>{rp}<w:t xml:space="preserve">{esc("".join(b[j1:j2]))}</w:t></w:r></w:ins>')
    return head + (ppr.group(0) if ppr else "") + "".join(out) + "</w:p>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("rewritten", nargs="?")
    ap.add_argument("--dump")
    ap.add_argument("-o", "--out")
    ap.add_argument("--author", default="Editor")
    a = ap.parse_args()
    with zipfile.ZipFile(a.source) as z:
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    doc = next(d for i, d in entries if i.filename == "word/document.xml").decode("utf-8")
    paras = [p for p in PARA.findall(doc) if editable(p)]
    if a.dump:
        Path(a.dump).write_text("\n\n".join(text_of(p) for p in paras), encoding="utf-8")
        print(f"{len(paras)} editable paragraphs written to {a.dump}")
        return 0
    if not (a.rewritten and a.out):
        ap.error("give REWRITTEN.txt and -o OUT.docx, or use --dump")
    new = [x.strip() for x in re.split(r"\n\s*\n", Path(a.rewritten).read_text(encoding="utf-8")) if x.strip()]
    if len(new) != len(paras):
        print(f"paragraph count mismatch: document has {len(paras)} editable paragraphs, rewrite has {len(new)}", file=sys.stderr)
        return 2
    ids, date = [0], datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    it = iter(new)

    def repl(m: re.Match) -> str:
        p = m.group(0)
        if not editable(p):
            return p
        n = next(it)
        return p if n == text_of(p) else build(p, n, ids, a.author, date)

    new_doc = PARA.sub(repl, doc)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as zo:
        for info, data in entries:
            zo.writestr(info, new_doc.encode("utf-8") if info.filename == "word/document.xml" else data)
    print(f"written {a.out} with {ids[0]} tracked changes by '{a.author}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
