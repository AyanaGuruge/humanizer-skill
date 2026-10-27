# Humanizer 3.1

A Claude skill that rewrites text in your own voice, removes the habits that make writing read as machine made, and cleans hidden metadata and AI markers from the result.

The first time you use it, it interviews you (about ten minutes), learns your writing style from documents you wrote, and saves a style profile to Claude's memory. After that, "humanize this" produces text that sounds like you. Nothing about the person who shared the skill is included: your profile is created from your own writing.

## Install

**Claude.ai or the Claude app:** Settings, Capabilities, Skills, upload `humanizer.skill` (or the zipped `humanizer` folder). Turn the skill on.

**Claude Code:**

```bash
mkdir -p ~/.claude/skills
cp -r humanizer ~/.claude/skills/
```

Turn on memory (Settings, Capabilities, "Generate memory from chats") so your style profile is kept between chats. Without memory the skill still works: it keeps a local `style-profile.md` in its folder.

## First run

Say: **"Set up my writing style"** (or just send a text and say "humanize this" and accept the offer).

1. Attach 3 to 5 things you wrote yourself, ideally before AI helped, 1500 words or more in total (docx, pdf, txt, md or pasted).
2. Answer the questions, one at a time. Each has a recommended answer; you can type your own.
3. Check the test paragraph written in your voice and say what is off.
4. Say yes to saving. You get the profile files back to keep.

## Everyday use

- "Humanize this" with pasted text or an attached docx.
- "Check this for AI tells" for a habit count (not a detector).
- "Clean this file" to see and remove hidden metadata, invisible characters and chatbot markers (docx, pptx, xlsx, pdf, jpg, png, webp, text).
- "Update my style" or "show my style profile".
- "Give me this as tracked changes" for a docx you want to review edit by edit.
- "Learn from my edits" after you correct a rewrite.
- "Process this folder" for batch work, and "draft an AI assistance note" for a disclosure statement.
- Several writing registers (academic, email, messages) can live in one profile; the skill picks the one that fits.

## What is in the box

| Path | Purpose |
| --- | --- |
| `SKILL.md` | The workflow Claude follows |
| `references/onboarding.md` | The setup interview |
| `references/style-profile-template.md` | What a profile contains |
| `references/ai-patterns.md` | 35 machine writing patterns with before and after examples |
| `references/metadata-cleaning.md` | Exactly what the cleaner touches and its limits |
| `scripts/analyze_style.py` | Measures your style; compares a draft with it |
| `scripts/scan_tells.py` | Counts machine habits; checks your dash policy |
| `scripts/clean_metadata.py` | Checks and cleans files and text |
| `scripts/flag_claims.py` | Lists figures, years and vague authorities that lack support |
| `scripts/diff_edits.py` | Learns from your edits to a rewrite and proposes profile rules |
| `scripts/tracked_changes.py` | Returns a rewrite as Word tracked changes |
| `references/disclosure-note.md` | Templates for an honest AI assistance statement |

The scripts need Python 3 and use only the standard library, plus `pikepdf` for PDFs and `pdftotext` for PDF text when available.

## Limits you should know

- The cleaner removes metadata, invisible characters and chatbot residue. It cannot detect or remove statistical text watermarks or invisible image watermarks, and it does not make text undetectable. AI detectors are unreliable and this skill does not try to beat them.
- The scan counts stylistic habits. It is not an AI detector.
- Use it on your own drafts and follow any rules about disclosing AI help that apply to you (school, employer, publisher).

## Credits and license

Pattern list adapted from Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup) and the open source humanizer skill v2.8.0 (MIT). This version adds the style interview and profile, measurement scripts, the invented specifics and template paragraph patterns, and the metadata cleaner. MIT license.

## Version history

- **3.1.0** Per register profiles, learning from your edits (`diff_edits.py`), Word tracked changes output, batch mode, unsupported claim flags, disclosure note templates, notes for non English text, before and after summaries.
- **3.0.0** First time style interview with a saved profile (memory plus local file); `analyze_style.py`, `scan_tells.py`, `clean_metadata.py`; dash policy driven by the profile; rule against invented specifics; patterns 34 and 35; patterns moved to `references/`; frontmatter made portable.
- **2.8.0 and earlier** See the upstream humanizer project.
