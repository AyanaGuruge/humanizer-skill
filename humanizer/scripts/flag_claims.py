#!/usr/bin/env python3
"""
flag_claims.py: list sentences that make checkable claims without support, so a humanized text stays defensible.

Usage: flag_claims.py FILE     (.txt .md .docx)
Flags: figures or years with no citation nearby, vague authorities ("experts say"), and absolute wording.
This is a heuristic reading aid. It cannot judge whether a claim is true.
"""
from __future__ import annotations

import html
import re
import sys
import zipfile
from pathlib import Path

CITE = re.compile(r"\[\d+(?:[,–-]\s*\d+)*\]|\([A-Z][A-Za-z-]+(?: et al\.)?,? \d{4}[a-z]?\)|https?://|\bdoi:|\(\d{4}\)")
VAGUE = re.compile(r"\b(experts|researchers|scientists|studies|critics|observers|many people|some people|it is (?:widely )?(?:known|believed|said)|reports? (?:show|suggest|indicate))\b", re.I)
ABSOLUTE = re.compile(r"\b(always|never|proves?|proven|undeniably|clearly shows|guarantees?|everyone knows|all experts|no one)\b", re.I)
FIGURE = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:%|(?:percent|times|million|billion|thousand)\b)|\b(?:19|20)\d{2}\b")


def load(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        return "\n\n".join("".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", b, re.S)) for b in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S))
    return p.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    text = load(sys.argv[1])
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
    hits = []
    for i, s in enumerate(sents, 1):
        why = []
        if FIGURE.search(s) and not CITE.search(s):
            why.append("figure or year without a citation")
        if VAGUE.search(s) and not CITE.search(s):
            why.append("vague authority")
        if ABSOLUTE.search(s):
            why.append("absolute wording")
        if why:
            hits.append((i, "; ".join(why), s))
    print(f"CLAIM CHECK  {len(sents)} sentences, {len(hits)} to review")
    for i, why, s in hits:
        print(f"  [{i}] {why}\n      {s[:220]}")
    if not hits:
        print("  nothing flagged")
    print("Heuristic only: it finds statements that need support, not statements that are wrong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
