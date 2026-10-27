# Humanizer

A Claude skill that rewrites text in **your own voice**, removes the habits that make writing read as machine made, and cleans hidden metadata and chatbot residue from the files you hand in.

Most "humanizers" push text toward a generic human voice. This one learns yours: on first use it interviews you, measures your writing from documents you wrote, and saves a style profile to Claude's memory. Every later rewrite is checked against that profile with scripts, not just with vibes.

> Built on the open source [humanizer](https://github.com/blader/humanizer) skill (MIT) and Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). See [Credits](#credits).

## Features

| Area | What it does |
| --- | --- |
| **Personal style profile** | A grilling style interview (one question at a time, with a recommended answer) plus measurement of your own documents. Saved to memory and to a local file. Supports several registers (academic, email, messages). |
| **Rewrite loop** | Baseline scan, draft, audit, verification, cleaning. 35 documented machine writing patterns, with the person's own habits (semicolons, passive voice, long sentences) protected as voice, not flagged as tells. |
| **No invented facts** | Never adds names, studies, numbers or quotes that the source lacks. Vague claims get a visible placeholder or a flag instead. |
| **Hidden marker cleaner** | Removes invisible Unicode, hidden Unicode tag text, pasted chatbot markers (`oaicite`, `turn0search`, cite tags), `utm_source=chatgpt.com`, Office and PDF properties, revision IDs, local paths, thumbnails, EXIF and C2PA data. Lossless for images. |
| **Learn from edits** | `diff_edits.py` compares a rewrite with your final version and proposes profile rules you can accept. |
| **Tracked changes** | Returns a rewrite as Word tracked changes so every edit can be accepted or rejected. |
| **Claim check** | Lists figures, years and vague authorities that lack a citation. |
| **Disclosure helper** | Templates for an honest AI assistance statement. |
| **Batch mode** | Process a folder and get one summary table. |

## Example

Before (90 words) and after, measured by `scan_tells.py` (a habit counter, not an AI detector):

```text
before: 20 flagged habits, 222.2 per 1000 words
        8 AI vocabulary, 3 significance inflation, 2 chatbot residue, 2 tailing negation, ...
after:  0 flagged habits, 0.0 per 1000 words
```

The texts are in [`examples/`](examples). The cleaner reports what it finds before it changes anything:

```text
FILE  report.docx  (docx)
  hidden metadata found:
    author: A. Student
    description/comments: made with ChatGPT
    application: Microsoft Office Word
  would remove or reset:
    core properties reset: 1
    ChatGPT contentReference/oaicite marker: 3
    zero width space: 5
    revision session IDs (rsid): 412
    document thumbnail: 1
  flag  AI related text found in document properties: description/comments=made with ChatGPT
```

## Install

**Claude.ai / Claude app:** Settings, Capabilities, Skills, upload [`dist/humanizer.skill`](dist/humanizer.skill), and turn it on. Turn on memory (Settings, Capabilities, "Generate memory from chats") so the style profile is kept between chats. Without memory the skill keeps a local `style-profile.md` instead.

**Claude Code:**

```bash
git clone https://github.com/AyanaGuruge/humanizer-skill.git
mkdir -p ~/.claude/skills && cp -r humanizer-skill/humanizer ~/.claude/skills/
```

## Quick start

1. Say **"Set up my writing style"** and attach 3 to 5 things you wrote (docx, pdf, txt, md or pasted), 1500 words or more in total.
2. Answer the questions, review the test paragraph in your voice, and confirm.
3. From then on: **"humanize this"** with pasted text or a file. Other commands: "check this for AI tells", "clean this file", "give me this as tracked changes", "learn from my edits", "process this folder", "draft an AI assistance note", "update my style".

## The scripts

All standard library Python 3 (PDF support uses `pikepdf` and `pdftotext` when present). Run them with `python3 -I` when the input is not your own.

```bash
python3 -I humanizer/scripts/analyze_style.py essay.docx email.txt --json style-metrics.json
python3 -I humanizer/scripts/analyze_style.py --compare style-metrics.json draft.txt
python3 -I humanizer/scripts/scan_tells.py draft.txt --dashes none
python3 -I humanizer/scripts/flag_claims.py draft.docx
python3 -I humanizer/scripts/clean_metadata.py --check report.docx photo.jpg   # look first
python3 -I humanizer/scripts/clean_metadata.py -r -o cleaned/ folder/          # then clean
python3 -I humanizer/scripts/diff_edits.py rewrite.txt final.txt
python3 -I humanizer/scripts/tracked_changes.py source.docx --dump paras.txt
```

## Repository layout

```text
humanizer/                 the skill (this folder is what gets installed)
  SKILL.md                 workflow Claude follows
  references/              onboarding interview, profile format, 35 patterns,
                           cleaner details, disclosure templates
  scripts/                 analyze_style, scan_tells, clean_metadata, flag_claims,
                           diff_edits, tracked_changes
dist/humanizer.skill       packaged skill for upload
examples/                  before and after text
tests/                     unit tests for the cleaner
```

## Limits and responsible use

- The cleaner removes **metadata, invisible characters and chatbot residue**. It cannot detect or remove statistical text watermarks (patterns in word choice) or invisible pixel level image watermarks, and it does **not** make text undetectable.
- AI detectors are unreliable in both directions, including false positives on genuine human writing. This project does not try to beat them.
- `scan_tells.py` counts stylistic habits. It is not an AI detector and says nothing about who wrote a text.
- Use it on your own drafts, and follow any rules about disclosing AI assistance that apply to you (school, employer, journal). The skill includes templates for an honest disclosure note.
- Documents you share with the skill stay in the chat. Only writing patterns and a few short phrases are saved, never passages, and only after you say yes.

## Development

```bash
python3 -m unittest discover -s tests
python3 /path/to/skill-creator/scripts/quick_validate.py humanizer   # validate the skill folder
```

## Credits

- [blader/humanizer](https://github.com/blader/humanizer) by Siqi Chen (MIT), the original skill and pattern list.
- Wikipedia: [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup.
- This version adds the style interview and profile, measurement and verification scripts, the metadata cleaner, tracked changes output, claim flagging, edit learning, patterns 34 and 35, and the rule against invented specifics.

## License

MIT. See [LICENSE](LICENSE).
