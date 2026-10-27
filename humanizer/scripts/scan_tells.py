#!/usr/bin/env python3
"""
scan_tells.py: count the surface patterns that make text read as machine written, before and after a rewrite.

Usage
  scan_tells.py FILE                      readable report (.txt .md .docx .pdf)
  scan_tells.py FILE --dashes none        also list every dash like character (policy: none | minimal | natural)
  scan_tells.py FILE --json               machine readable
  cat draft.txt | scan_tells.py -         read stdin

This is NOT an AI detector and says nothing about who wrote a text. It measures a fixed list of stylistic
habits (see references/ai-patterns.md) so a rewrite can be compared with its source. A lower density means
fewer of those habits, nothing more. Standard library only.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import subprocess
import sys
import zipfile
from pathlib import Path

VOCAB = """delve delves delving tapestry testament pivotal vibrant intricate intricacies meticulous meticulously landscape
underscore underscores underscoring showcase showcases showcasing garner garnered foster fostering fosters enduring crucial
realm leverage leveraging seamless seamlessly robust holistic synergy elevate unlock unleash embark navigate navigating
ever-evolving multifaceted nuanced transformative groundbreaking cutting-edge game-changer paramount plethora myriad
commendable noteworthy invaluable interplay beacon cornerstone""".split()

PHRASES = {
    "significance inflation": [r"\bstands? as a testament\b", r"\bserves? as a (?:reminder|testament)\b", r"\bplays? a (?:vital|crucial|pivotal|key|significant) role\b",
                               r"\bmarking a pivotal\b", r"\bevolving landscape\b", r"\bin today'?s (?:fast[- ]paced|rapidly evolving|digital)\b",
                               r"\bit(?:'s| is) (?:important|worth) (?:to note|noting)\b", r"\bindelible mark\b"],
    "chatbot residue": [r"\bI hope this helps\b", r"\bcertainly!", r"\bof course!", r"\bgreat question\b", r"\blet me know if\b", r"\bwould you like me to\b",
                        r"\bas an ai\b", r"\bhere(?:'s| is) (?:a|an|the) (?:summary|overview|breakdown)\b", r"\byou'?re absolutely right\b"],
    "signposting": [r"\blet'?s (?:dive|delve|explore|break|unpack)\b", r"\bhere'?s what you need to know\b", r"\bwithout further ado\b", r"\bnow let'?s look\b"],
    "authority tropes": [r"\bthe real question is\b", r"\bat its core\b", r"\bwhat really matters\b", r"\bthe heart of the matter\b", r"\bthe deeper issue\b"],
    "fake candid openers": [r"(?m)^(?:honestly|look|real talk|here'?s the thing|the thing is)[,?:.]", r"\blet'?s be honest\b"],
    "generic positive endings": [r"\bthe future looks bright\b", r"\bexciting times (?:lie|are) ahead\b", r"\bin conclusion,", r"\bonly time will tell\b", r"\bthis represents a major step\b"],
    "filler": [r"\bin order to\b", r"\bdue to the fact that\b", r"\bat this point in time\b", r"\bin the event that\b", r"\bhas the ability to\b"],
    "vague attribution": [r"\b(?:experts|observers|critics|industry reports|studies) (?:say|argue|suggest|believe|have noted|note)\b", r"\bsome critics argue\b"],
    "negative parallelism": [r"\bnot (?:just|only|merely) [^.;\n]{1,80}[,;]? (?:but|it'?s|it is)\b", r"\bit'?s not (?:just |merely )?(?:about )?[^.;\n]{1,60}[;,] it'?s\b",
                             r"\bnot [a-z ]{1,25}, but\b"],
    "tailing negation": [r",\s(?:no|zero) [a-z]+(?: [a-z]+)?\.", r"\.\s(?:No|Zero) [a-z]+(?: [a-z]+)?\.(?=\s|$)"],
    "aphorism formula": [r"\bis the (?:language|currency|architecture|backbone|engine) of\b", r"\bbecomes a trap\b", r"\bnot a tool but a\b"],
}
TRANSITION_OPENERS = r"(?m)(?:^|[.!?]\s+)(?:Additionally|Moreover|Furthermore|Consequently|Notably|Importantly|Ultimately|Overall),"
ROT = re.compile(r"\b[\w-]+(?: [\w-]+)?, [\w-]+(?: [\w-]+)?,? (?:and|or) [\w-]+(?: [\w-]+)?\b")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌]")
DASHLIKE = re.compile(r"[—–‒―]|(?<=\s)--(?=\s)|\s-\s|\b[A-Za-z]+-[A-Za-z]+\b")


def load(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
        return "\n\n".join("".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", b, re.S)) for b in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S))
    if ext == ".pdf":
        raw = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, timeout=90).stdout.decode("utf-8", "replace")
        return re.sub(r"\n(?!\n)", " ", raw)
    return p.read_text(encoding="utf-8", errors="replace")


def scan(text: str, dashes: str) -> dict:
    words = re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text)
    n = max(len(words), 1)
    low = [w.lower() for w in words]
    cats: dict[str, dict] = {}

    def add(cat: str, count: int, examples: list[str]) -> None:
        if count:
            cats[cat] = {"count": count, "examples": examples[:5]}

    hits = [w for w in low if w in set(VOCAB)]
    add("AI vocabulary", len(hits), sorted(set(hits)))
    for cat, pats in PHRASES.items():
        found: list[str] = []
        for p in pats:
            found += [m.group(0).strip() for m in re.finditer(p, text, re.I)]
        add(cat, len(found), found)
    t = re.findall(TRANSITION_OPENERS, text)
    add("stacked transition openers", len(t) if len(t) >= 3 else 0, [x.strip(" .!?\n") for x in t])
    rot = ROT.findall(text)
    add("rule of three lists", len(rot) if len(rot) * 1000 / n > 4 else 0, rot)
    add("emoji", len(EMOJI.findall(text)), EMOJI.findall(text))
    add("markdown bold in prose", len(re.findall(r"\*\*[^*\n]+\*\*", text)), re.findall(r"\*\*[^*\n]+\*\*", text))
    add("title case headings", len([h for h in re.findall(r"(?m)^#{1,4} (.+)$", text) if sum(1 for w in h.split() if w[:1].isupper()) >= 3 and len(h.split()) >= 3]), [])
    em = text.count("—")
    en = text.count("–")
    if dashes != "natural":
        add("em or en dashes", em + en, [])
    curly = sum(text.count(c) for c in "“”‘’")
    if curly >= 4 and text.count('"') + text.count("'") == 0:
        cats["curly quotes only (weak signal; many editors insert them)"] = {"count": curly, "examples": []}

    sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 1]
    lens = [len(s.split()) for s in sents] or [0]
    cv = round(statistics.pstdev(lens) / statistics.mean(lens), 2) if len(lens) > 2 and statistics.mean(lens) else 0
    short_run = 0
    run = 0
    for L in lens:
        run = run + 1 if L <= 5 else 0
        if run == 3:
            short_run += 1
    add("staccato runs (three or more fragments in a row)", short_run, [])

    total = sum(c["count"] for c in cats.values())
    out = {
        "words": len(words), "sentences": len(sents), "tells_total": total, "tells_per_1000_words": round(total * 1000 / n, 1),
        "sentence_length_variation": cv, "categories": cats,
        "dash_policy": dashes,
    }
    if dashes in ("none", "minimal"):
        spots = []
        for m in DASHLIKE.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            if m.group(0).strip() == "-" and text[line_start:m.start()].strip() == "":
                continue  # a list marker, not a dash in prose
            spots.append(text[max(0, m.start() - 25):m.end() + 25].replace("\n", " "))
        out["dash_like_characters"] = {"count": len(spots), "context": spots[:25]}
        out["dash_policy_ok"] = (len(spots) == 0) if dashes == "none" else (em + en) * 1000 / n <= 1.0
    return out


def render(r: dict) -> str:
    L = [f"TELL SCAN  {r['words']} words, {r['sentences']} sentences: {r['tells_total']} flagged habits ({r['tells_per_1000_words']} per 1000 words); sentence length variation {r['sentence_length_variation']}"]
    for cat, v in sorted(r["categories"].items(), key=lambda kv: -kv[1]["count"]):
        ex = f"  e.g. {', '.join(map(str, v['examples']))}" if v["examples"] else ""
        L.append(f"  {v['count']:>3}  {cat}{ex}")
    if not r["categories"]:
        L.append("  none of the tracked habits found")
    if "dash_like_characters" in r:
        d = r["dash_like_characters"]
        L.append(f"  dash policy '{r['dash_policy']}': {'OK' if r['dash_policy_ok'] else 'VIOLATED'} ({d['count']} dash like characters incl. hyphens in words)")
        for c in d["context"][:12]:
            L.append(f"        ...{c}...")
    L.append("Not an AI detector: this counts stylistic habits only. Lower is not proof of anything.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Count machine writing habits in a text.")
    ap.add_argument("file")
    ap.add_argument("--dashes", choices=["none", "minimal", "natural"], default="natural")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = scan(load(a.file), a.dashes)
    print(json.dumps(r, indent=2, ensure_ascii=False) if a.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
