# What clean_metadata.py touches, and what it does not

Run: `python3 -I scripts/clean_metadata.py --check FILE` to look, without `--check` to write a `.clean` copy (use `-o DIR` for a folder or `--in-place` to overwrite). Use `-` to clean text from stdin. Add `--json` for a machine readable report.

## Text (.txt .md .html .csv .tex and the text inside Office files)

| Found | Action |
| --- | --- |
| Zero width space, joiner, non joiner, word joiner, BOM, soft hyphen, combining grapheme joiner, invisible math operators, Hangul fillers | Removed. Joiners are kept where they are legitimate: inside emoji sequences, and in scripts that need them (Arabic, Indic, Thai and similar). |
| Left to right and right to left marks, bidi overrides | Removed unless the text contains right to left script. |
| Variation selectors | Kept after emoji and CJK characters, removed elsewhere. |
| Unicode tag characters (U+E0000 range) | Removed and decoded in the report. Hidden text in this range is a known way to smuggle instructions into prompts, so any hit is flagged as a security note. Flag emoji for England, Scotland and Wales are left intact. |
| Thin, hair, narrow no break and other typographic spaces | Replaced by a plain space. Ordinary no break spaces are kept (often legitimate) unless `--aggressive`. |
| ChatGPT citation markers, `oaicite` and `contentReference`, `turn0search0` style markers, source brackets with a dagger | Removed (with the one space before them). |
| Gemini `[cite_start]` and `[cite: 1, 2]`, cite tags from chat interfaces | Removed. |
| `utm_source=chatgpt.com` and similar in URLs | Parameter removed, URL kept. |
| Curly quotes | Converted only with `--straight-quotes`. |
| Words mixing Latin letters with Cyrillic or Greek lookalikes | Reported, never changed. |

## Word, PowerPoint, Excel

Author, last modified by, subject, keywords, comments, category, created and modified dates (unless `--keep-dates`), application name and version, company, manager, template, total editing time, custom properties, thumbnail, revision session IDs (`rsid`), local file paths stored by Excel (`absPath`), metadata inside embedded JPEG, PNG and WebP images (lossless, pixels untouched), zip entry timestamps. The document title is kept unless `--strip-title`. `--set-author NAME` writes a name instead of blank. `--anonymize-authors` renames comment and revision authors.

Reported but not removed, because they are content: comments, tracked changes, hidden text. Accept or reject changes in the document, or ask for them to be removed explicitly.

## PDF

Info dictionary (author, creator, producer, title, subject, keywords, dates), XMP packets on the document, pages and images, private application data. The text layer cannot be cleaned safely in place; if it contains hidden characters or chatbot markers the report says so, and the fix is to correct the source file and export again.

## Images (.jpg .png .webp)

EXIF (camera, software, dates, GPS), XMP, IPTC, JPEG comments, PNG text chunks (including Stable Diffusion style `parameters` and ComfyUI `prompt` or `workflow`), C2PA and JUMBF content credentials, trailing bytes after the image end. The operation is lossless: bytes are removed, pixels are not re-encoded. For rotated phone photos only the orientation tag is kept so the picture still displays upright. Other formats: `exiftool -all= FILE`.

## What it cannot do

- **Statistical text watermarks.** Some systems bias word choice in a hidden pattern. There is nothing in the file to remove and nothing this tool can detect. Rewriting changes the words, but no guarantee follows, and nothing here should be described as making text undetectable.
- **Pixel level image watermarks.** These live in the image content, not the metadata.
- **Detector scores.** AI detectors are unreliable in both directions; false positives on genuine human writing are common. This skill does not try to game them and should not be described as doing so.
- **Platform side records.** Version history in cloud editors, server logs and email headers are outside the file.

## Reading a report

`hidden metadata found` lists values seen before cleaning. `removed or reset` counts what was changed. `flag` lines need the person's attention (AI tool names in properties, GPS, content credentials, comments or tracked changes still present, hidden Unicode text). `note` lines are informational. The footer repeats the limits above. A clean file re-checked with `--check` should say "nothing found".
