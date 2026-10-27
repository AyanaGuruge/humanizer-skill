#!/usr/bin/env python3
"""
analyze_style.py: build a measurable writing style fingerprint from a person's own documents.

Usage
  analyze_style.py FILE [FILE ...]                    print a readable summary (also saves nothing)
  analyze_style.py FILE ... --json out.json           also write the metrics as JSON
  analyze_style.py --compare profile.json DRAFT.txt   check a rewrite against a saved fingerprint

Accepted inputs: .txt .md .docx .pdf  (English prose; other languages give partial results)
Run with python3 -I when the files come from outside. Standard library only; pdftotext or pypdf for PDFs.

The numbers describe habits (sentence length, punctuation, connectors, voice). They are a guide for the
rewrite, not a score to chase, and samples under about 1500 words give low confidence results.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import statistics
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

# ----------------------------------------------------------------------------- extraction


def _docx_paragraphs(path: Path) -> tuple[list[str], dict]:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    paras, headings, list_items = [], 0, 0
    for block in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        if re.search(r'<w:pStyle w:val="(Heading|Title)', block):
            headings += 1
            continue
        if "<w:numPr>" in block:
            list_items += 1
        text = "".join(html.unescape(t) for t in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", block, re.S))
        if text.strip():
            paras.append(text.strip())
    return paras, {"headings": headings, "list_items": list_items}


def _pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, timeout=90).stdout.decode("utf-8", "replace")
        if out.strip():
            return out
    except Exception:
        pass
    from pypdf import PdfReader  # type: ignore

    return "\n\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)


def extract(path: Path) -> tuple[list[str], dict]:
    ext = path.suffix.lower()
    fmt = {"headings": 0, "list_items": 0}
    if ext == ".docx":
        return _docx_paragraphs(path)
    if ext == ".pdf":
        raw = _pdf_text(path)
        raw = re.sub(r"-\n(?=[a-z])", "", raw)
        paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", raw)]
    elif ext in (".txt", ".md", ".markdown", ".rst", ".tex"):
        raw = path.read_text(encoding="utf-8", errors="replace")
        paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", raw)]
        if ext in (".md", ".markdown"):
            fmt["headings"] = sum(1 for p in raw.splitlines() if p.startswith("#"))
            fmt["list_items"] = sum(1 for p in raw.splitlines() if re.match(r"\s*([-*+]|\d+\.)\s", p))
            paras = [p for p in paras if not p.startswith("#")]
    else:
        raise ValueError(f"unsupported file type: {ext}")
    return [p for p in paras if len(p.split()) >= 3], fmt


# ----------------------------------------------------------------------------- analysis

ABBR = re.compile(r"\b(e\.g|i\.e|et al|etc|vs|Fig|Eq|Dr|Mr|Mrs|Ms|Prof|No|approx|cf|Sec|Ref)\.", re.I)
STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being it its this that these those
i we you he she they them his her our their my your not no so than then there here which who whom whose what when where why how
can could may might must shall should will would do does did have has had also such into over under between about""".split())
TRANSITIONS = [
    "however", "therefore", "thus", "hence", "moreover", "furthermore", "additionally", "consequently", "nevertheless",
    "nonetheless", "whereas", "although", "while", "because", "since", "in addition", "as a result", "for example",
    "for instance", "in contrast", "similarly", "likewise", "meanwhile", "finally", "first", "second", "then", "thereby",
    "overall", "in conclusion", "on the other hand", "in other words", "that is", "indeed", "instead", "otherwise", "so",
    "but", "and yet", "still", "even so", "in particular", "specifically", "notably",
]
PASSIVE = re.compile(r"\b(am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(\w+ed|known|made|done|shown|seen|given|taken|found|built|used|chosen|written|held|kept|led|set|put|run|paid|sent|told|understood|began|begun)\b", re.I)
CONTRACTION = re.compile(r"\b\w+['’](?:s|t|re|ve|ll|d|m)\b", re.I)
BRIT = ["colour", "behaviour", "favour", "analyse", "organis", "realis", "centre", "metre", "programme", "licence", "defence", "grey", "whilst", "optimis", "recognis", "summaris", "utilis", "modelling", "labelling"]
AMER = ["color", "behavior", "favor", "analyze", "organiz", "realiz", "center", "meter", "program ", "license", "defense", "gray", "while", "optimiz", "recogniz", "summariz", "utiliz", "modeling", "labeling"]


def split_sentences(text: str) -> list[str]:
    t = ABBR.sub(lambda m: m.group(0).replace(".", "\u2024"), text)
    t = re.sub(r"(\b[A-Z])\.(?=\s?[A-Z])", "\\1\u2024", t)
    parts = re.split(r'(?<=[.!?])["\')\]]*\s+(?=["(\[]?[A-Z0-9])', t)
    return [p.replace("\u2024", ".").strip() for p in parts if len(p.split()) >= 2]


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith("le") and n > 1:
        n -= 1
    return max(n, 1)


def per1k(count: float, words: int) -> float:
    return round(count * 1000 / words, 2) if words else 0.0


def analyze(paras: list[str], fmt: dict, files: list[str]) -> dict:
    text = "\n\n".join(paras)
    sents = split_sentences(text)
    words = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", text)
    nwords = len(words)
    lower = text.lower()
    lens = [len(re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", s)) for s in sents] or [0]
    mean = statistics.mean(lens)
    stdev = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    sl = sorted(lens)

    def pct(k: int) -> float:
        return sl[min(len(sl) - 1, int(len(sl) * k / 100))]

    syl = sum(syllables(w) for w in words)
    fre = 206.835 - 1.015 * (nwords / max(len(sents), 1)) - 84.6 * (syl / max(nwords, 1))
    fk = 0.39 * (nwords / max(len(sents), 1)) + 11.8 * (syl / max(nwords, 1)) - 15.59

    trans = {}
    for t in TRANSITIONS:
        c = len(re.findall(rf"(?<![a-z]){re.escape(t)}(?![a-z])", lower))
        if c:
            trans[t] = per1k(c, nwords)
    trans = dict(sorted(trans.items(), key=lambda kv: -kv[1])[:15])

    openers = Counter()
    for s in sents:
        m = re.match(r"[\"'(\[]*([A-Za-z]+(?:\s[a-z]+)?)", s)
        if m:
            openers[m.group(1).split()[0].lower()] += 1
    top_open = [(w, round(100 * c / len(sents), 1)) for w, c in openers.most_common(10)]

    tri = Counter()
    toks = [w.lower() for w in words]
    for i in range(len(toks) - 2):
        g = toks[i:i + 3]
        if not (g[0] in STOP and g[2] in STOP) and sum(1 for x in g if x in STOP) <= 1:
            tri[" ".join(g)] += 1
    tics = [(g, c) for g, c in tri.most_common(12) if c >= 3]

    content = Counter(w for w in toks if w not in STOP and len(w) > 3)
    fav = [(w, per1k(c, nwords)) for w, c in content.most_common(25)]

    oxf_with = len(re.findall(r"\w+, \w+(?: \w+)?, (?:and|or) \w+", text))
    oxf_without = len(re.findall(r"\w+, \w+(?: \w+)?,? (?:and|or) \w+", text)) - oxf_with
    brit = sum(lower.count(w) for w in BRIT)
    amer = sum(lower.count(w) for w in AMER)
    variant = "unknown" if brit + amer < 3 else "british" if brit > 2 * amer else "american" if amer > 2 * brit else "mixed"

    first_sg = len(re.findall(r"\b(I|me|my|mine|myself)\b", text))
    first_pl = len(re.findall(r"\b(we|us|our|ours|ourselves)\b", text, re.I))
    second = len(re.findall(r"\b(you|your|yours)\b", text, re.I))
    passive = sum(1 for s in sents if PASSIVE.search(s))
    first_words = words[:2000]
    ttr = round(len({w.lower() for w in first_words}) / max(len(first_words), 1), 3)

    return {
        "files": files,
        "confidence": "low (under 1500 words)" if nwords < 1500 else "ok",
        "words": nwords,
        "sentences": len(sents),
        "paragraphs": len(paras),
        "sentence_length": {
            "mean": round(mean, 1), "median": statistics.median(lens), "stdev": round(stdev, 1),
            "variation_coefficient": round(stdev / mean, 2) if mean else 0,
            "p10": pct(10), "p90": pct(90),
            "pct_over_30_words": round(100 * sum(1 for x in lens if x > 30) / len(lens), 1),
            "pct_under_10_words": round(100 * sum(1 for x in lens if x < 10) / len(lens), 1),
        },
        "paragraph_mean_words": round(nwords / max(len(paras), 1), 1),
        "per_1000_words": {
            "commas": per1k(text.count(","), nwords), "semicolons": per1k(text.count(";"), nwords),
            "colons": per1k(text.count(":"), nwords), "em_dashes": per1k(text.count("\u2014"), nwords),
            "en_dashes": per1k(text.count("\u2013"), nwords),
            "hyphenated_compounds": per1k(len(re.findall(r"\b[A-Za-z]+-[A-Za-z]+\b", text)), nwords),
            "parentheses": per1k(text.count("("), nwords), "question_marks": per1k(text.count("?"), nwords),
            "exclamation_marks": per1k(text.count("!"), nwords),
            "contractions": per1k(len(CONTRACTION.findall(text)), nwords),
            "first_person_singular": per1k(first_sg, nwords), "first_person_plural": per1k(first_pl, nwords),
            "second_person": per1k(second, nwords),
        },
        "passive_sentences_pct": round(100 * passive / max(len(sents), 1), 1),
        "quotes": {"straight": text.count('"') + text.count("'"), "curly": sum(text.count(c) for c in "\u201c\u201d\u2018\u2019")},
        "oxford_comma": {"with": oxf_with, "without": max(oxf_without, 0)},
        "spelling_variant": variant,
        "transitions_per_1000": trans,
        "sentence_openers_pct": top_open,
        "repeated_phrases": tics,
        "favorite_content_words_per_1000": fav,
        "readability": {"flesch_reading_ease": round(fre, 1), "flesch_kincaid_grade": round(fk, 1)},
        "lexical_diversity_first_2000_words": ttr,
        "avg_word_length": round(sum(len(w) for w in words) / max(nwords, 1), 2),
        "citations": {
            "numeric_brackets": len(re.findall(r"\[\d+(?:[,\u2013-]\s*\d+)*\]", text)),
            "author_year": len(re.findall(r"\([A-Z][A-Za-z-]+(?: et al\.)?,? \d{4}[a-z]?\)", text)),
        },
        "formatting": fmt,
    }


# ----------------------------------------------------------------------------- reporting

def summary(m: dict) -> str:
    sl, p = m["sentence_length"], m["per_1000_words"]
    L = [
        f"STYLE FINGERPRINT  ({m['words']} words, {m['sentences']} sentences, confidence: {m['confidence']})",
        f"  sentence length: mean {sl['mean']}, median {sl['median']}, spread {sl['stdev']} (variation {sl['variation_coefficient']}), "
        f"10th to 90th percentile {sl['p10']} to {sl['p90']}; {sl['pct_over_30_words']}% over 30 words, {sl['pct_under_10_words']}% under 10",
        f"  paragraphs: about {m['paragraph_mean_words']} words each",
        f"  voice: passive in {m['passive_sentences_pct']}% of sentences; I {p['first_person_singular']}, we {p['first_person_plural']}, you {p['second_person']} per 1000 words; contractions {p['contractions']} per 1000",
        f"  punctuation per 1000 words: commas {p['commas']}, semicolons {p['semicolons']}, colons {p['colons']}, em dashes {p['em_dashes']}, en dashes {p['en_dashes']}, "
        f"hyphenated compounds {p['hyphenated_compounds']}, parentheses {p['parentheses']}, questions {p['question_marks']}, exclamations {p['exclamation_marks']}",
        f"  quotes: {m['quotes']['straight']} straight, {m['quotes']['curly']} curly; Oxford comma used {m['oxford_comma']['with']} times, skipped {m['oxford_comma']['without']} times; spelling: {m['spelling_variant']}",
        f"  readability: Flesch reading ease {m['readability']['flesch_reading_ease']}, grade level {m['readability']['flesch_kincaid_grade']}; average word length {m['avg_word_length']}",
        "  connectors per 1000 words: " + (", ".join(f"{k} {v}" for k, v in list(m["transitions_per_1000"].items())[:10]) or "none notable"),
        "  common sentence openers (% of sentences): " + ", ".join(f"{w} {v}" for w, v in m["sentence_openers_pct"][:8]),
        "  repeated phrases: " + (", ".join(f"'{g}' x{c}" for g, c in m["repeated_phrases"][:8]) or "none above threshold"),
        "  most used content words: " + ", ".join(w for w, _ in m["favorite_content_words_per_1000"][:15]),
        f"  citations: {m['citations']['numeric_brackets']} numeric bracket, {m['citations']['author_year']} author year; headings {m['formatting']['headings']}, list items {m['formatting']['list_items']}",
    ]
    return "\n".join(L)


CHECKS = [
    ("mean sentence length", ("sentence_length", "mean"), 0.20),
    ("sentence length variation", ("sentence_length", "variation_coefficient"), 0.25),
    ("passive sentences %", ("passive_sentences_pct",), 0.40),
    ("commas per 1000", ("per_1000_words", "commas"), 0.25),
    ("semicolons per 1000", ("per_1000_words", "semicolons"), 0.60),
    ("em dashes per 1000", ("per_1000_words", "em_dashes"), 0.60),
    ("contractions per 1000", ("per_1000_words", "contractions"), 0.50),
    ("first person singular per 1000", ("per_1000_words", "first_person_singular"), 0.50),
    ("paragraph length", ("paragraph_mean_words",), 0.35),
    ("reading ease", ("readability", "flesch_reading_ease"), 0.15),
]


def compare(profile: dict, draft: dict) -> str:
    L = ["COMPARISON with saved fingerprint (tolerance is relative; small absolute gaps are ignored)"]
    if draft["words"] < 150:
        L.append("  note: the draft is short, so treat these numbers as rough")
    for label, path, tol in CHECKS:
        a, b = profile, draft
        for k in path:
            a, b = a[k], b[k]
        gap = abs(a - b)
        rel = gap / abs(a) if a else (1.0 if b else 0.0)
        small = gap < (1.0 if "per 1000" in label else 2.0 if "sentence" in label or "paragraph" in label else 3.0)
        flag = "ok   " if rel <= tol or small else "CHECK"
        direction = "higher" if b > a else "lower"
        L.append(f"  {flag} {label}: profile {a}, draft {b}" + ("" if flag == "ok   " else f"  (draft is {direction} than the person's usual)"))
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure a writing style or compare a draft with a saved fingerprint.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", metavar="OUT", help="write metrics to this JSON file")
    ap.add_argument("--compare", metavar="PROFILE_JSON", help="compare the given draft file against this fingerprint")
    a = ap.parse_args()

    paras, fmt, names = [], {"headings": 0, "list_items": 0}, []
    for f in a.files:
        p = Path(f)
        try:
            ps, fm = extract(p)
        except Exception as exc:
            print(f"skipped {f}: {exc}", file=sys.stderr)
            continue
        paras += ps
        names.append(p.name)
        for k in fmt:
            fmt[k] += fm.get(k, 0)
    if not paras:
        print("no readable text found", file=sys.stderr)
        return 1
    m = analyze(paras, fmt, names)
    if a.compare:
        prof = json.loads(Path(a.compare).read_text())
        print(compare(prof, m))
        return 0
    print(summary(m))
    if a.json:
        Path(a.json).write_text(json.dumps(m, indent=2))
        print(f"\nmetrics saved to {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
