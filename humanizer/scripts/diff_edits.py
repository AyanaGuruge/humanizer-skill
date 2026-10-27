#!/usr/bin/env python3
"""
diff_edits.py: learn from corrections. Compare a rewrite Claude produced with the version the person
finally used, and list the habits their edits reveal, as candidate profile rules.

Usage: diff_edits.py REWRITE.txt EDITED.txt     (.txt .md .docx)
Output is a list of observations to show the person; nothing is saved by this script.
"""
from __future__ import annotations

import difflib
import html
import re
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path


def load(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        return "\n\n".join("".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", b, re.S)) for b in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S))
    return p.read_text(encoding="utf-8", errors="replace")


def words(t: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*|[;:,—–()!?]", t)


def sent_len(t: str) -> float:
    s = [x for x in re.split(r"(?<=[.!?])\s+", t) if len(x.split()) > 1]
    return statistics.mean(len(x.split()) for x in s) if s else 0


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    a, b = load(sys.argv[1]), load(sys.argv[2])
    wa, wb = words(a), words(b)
    sm = difflib.SequenceMatcher(None, [w.lower() for w in wa], [w.lower() for w in wb], autojunk=False)
    removed, added, swaps = Counter(), Counter(), []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("delete", "replace"):
            removed.update(" ".join(wa[i1:i2]).lower().split(" ") if i2 - i1 <= 3 else [])
            if i2 - i1 <= 4:
                removed[" ".join(wa[i1:i2]).lower()] += 1
        if op in ("insert", "replace") and j2 - j1 <= 4:
            added[" ".join(wb[j1:j2]).lower()] += 1
        if op == "replace" and i2 - i1 <= 4 and j2 - j1 <= 4:
            swaps.append((" ".join(wa[i1:i2]), " ".join(wb[j1:j2])))
    ratio = sm.ratio()
    out = [f"EDIT ANALYSIS  (similarity {ratio:.0%}; the closer to 100%, the less the person had to change)"]
    la, lb = sent_len(a), sent_len(b)
    if la and abs(la - lb) / la > 0.12:
        out.append(f"  sentence length: rewrite {la:.1f} words, final {lb:.1f}: they {'shortened' if lb < la else 'lengthened'} sentences")
    for ch, name in ((";", "semicolons"), (",", "commas"), ("—", "em dashes"), ("(", "parentheses"), ("!", "exclamation marks")):
        ca, cb = a.count(ch), b.count(ch)
        if abs(ca - cb) >= 2:
            out.append(f"  {name}: {ca} in the rewrite, {cb} in the final")
    gone = [(w, c) for w, c in removed.most_common(40) if len(w) > 2 and c >= 2][:8]
    if gone:
        out.append("  removed more than once: " + ", ".join(f"'{w}' x{c}" for w, c in gone))
    came = [(w, c) for w, c in added.most_common(40) if len(w) > 2 and c >= 2][:8]
    if came:
        out.append("  added more than once: " + ", ".join(f"'{w}' x{c}" for w, c in came))
    if swaps:
        out.append("  direct swaps: " + "; ".join(f"'{x}' to '{y}'" for x, y in swaps[:8]))
    out.append("Treat these as candidate rules. Show them to the person and save only the ones they confirm.")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
