---
name: humanizer
description: Rewrite text so it reads like its real author instead of a chatbot, then clean hidden AI markers from the result. On first use it runs a short interview and learns the person's own writing style from their documents, saves that style profile to memory, and applies it to every later rewrite. Removes machine writing patterns, verifies the result with scripts, and strips hidden metadata, invisible characters, chatbot residue and tracking parameters from docx, pptx, xlsx, pdf, images and text. Use when the user asks to humanize or de-AI a text, rewrite something in their own voice, set up or change their writing style, check text for AI habits, remove metadata, watermarks or hidden characters from a file, return edits as Word tracked changes, or draft an AI assistance note.
license: MIT
metadata:
  version: "3.1.0"
  based_on: "Wikipedia: Signs of AI writing (WikiProject AI Cleanup), humanizer v2.8.0"
---

# Humanizer

This skill makes a text sound like the person who owns it, removes the habits that make text read as machine written, and cleans the hidden traces that AI tools and editors leave in files. The voice always comes from the person's own style profile, never from a generic "human" voice. Nothing about any particular person is built into this skill: the profile is created on first use and lives in that person's memory.

Skill folder: the directory this SKILL.md was loaded from. Scripts are in `scripts/`, longer references in `references/`. Run scripts with `python3 -I` (isolated mode) because they read files the person supplied.

## Rules that always apply

1. **Never invent.** Do not add names, sources, studies, numbers, dates or quotes that are not in the source text or given by the person. If a passage is vague and the source allows nothing more, say it plainly, cut it, or leave a visible placeholder such as `[add: year]` and mention it.
2. **Preserve meaning and content.** Keep every point, number, citation, name, technical term, quotation and code block exactly. Five paragraphs in, five paragraphs out, unless the person asks for cuts.
3. **The person's voice outranks generic rules.** A habit the person really has (semicolons, passive voice, formal connectors, long sentences) is their voice, not a tell. The pattern list is a default for people with no profile.
4. **Be honest about what is and is not possible.** Never promise that text will pass an AI detector, and never claim to remove statistical watermarks. See "Cleaning hidden markers".
5. **Memory is silent.** Use the profile without announcing that memory was read. Never save anything without the person's yes (see "Saving").
6. **The person's own work.** This skill is for editing the person's own drafts. If they mention a school, employer or publisher that requires AI disclosure, remind them once, briefly, when delivering work for that context.

## Step 0: find the style profile (always first)

Check in this order and stop at the first hit:

1. **Memory.** Look in the memory listing for a file about the person's writing style (usually `/topics/writing-style.md`). Read it. Also read any stored metrics.
2. **Local file.** `style-profile.md` (and `style-metrics.json`) in the skill folder. This is the fallback when memory tools are unavailable.
3. **A sample in the request.** Text or a file the person gives as "my writing". Analyse it as in `references/onboarding.md`, phase B, and use it for this task only.
4. **Nothing found.** Offer the first time setup in one sentence ("I don't have your writing style yet. Want a ten minute setup so rewrites sound like you, or just a standard rewrite now?"). If they decline, run a standard rewrite with the default patterns and offer setup again at the end, once.

If the profile has several registers (for example academic, email, messages), pick the one that fits the text and the request, and say which you used only if it is not obvious. Explicit instructions in the current request ("make this more casual") override the stored profile for that piece only.

**Other languages.** The pattern list and the scripts are English centred. For a text in another language, rely on the person's own samples and your own judgment of that language, skip `scan_tells.py` and the style comparison, and still run `clean_metadata.py`, which is language independent.

## First time setup (the interview)

Run when the person says "set up my writing style", "redo my setup", or accepts the offer in Step 0. Read `references/onboarding.md` and follow it. In short:

- It works like a grilling session: **one question at a time**, each with a recommended answer or a few quick options, then wait. Use the question tool when it exists, plain text otherwise. Walk the decision tree in order; when an answer opens a branch (for example "no dashes" opens the hyphen question), follow it. Do not ask what the documents already answer.
- **Phase A, samples.** Ask for 3 to 5 pieces of their own writing in different situations (an essay or report, an email, a message), docx, pdf, txt, md or pasted, at least 1500 words in total, ideally written without AI help.
- **Phase B, measure and read.** Run `scripts/analyze_style.py` on the files, then read them yourself and note qualitative habits. Confirm those observations with the person instead of asserting them.
- **Phase C, interview** the gaps: language and spelling variety, main uses, formality, person and voice, rhythm, punctuation rules including dashes, words to ban and words they like, structure, citations, tone, output preferences, file cleaning defaults, disclosure rules.
- **Phase D, calibrate.** Draft the profile (format in `references/style-profile-template.md`), show it compactly, then rewrite a short neutral paragraph in their voice and ask what is off. Two rounds at most.
- **Phase E, save** (next section).

The person can stop at any time; save whatever has been confirmed so far and say what is still default.

## Saving the profile

After the person confirms the profile, ask once: "Save this so it applies in every chat?" On yes:

- **Memory:** write or update the style file (for example `/topics/writing-style.md`) following the memory instructions of the session. Read the file first if it exists and append or edit rather than overwrite. One short line per confirmed fact. Store patterns and rules, plus at most a handful of short signature phrases. Never store passages from their documents, names of people in them, or anything sensitive.
- **Local copy:** also write `style-profile.md` and `style-metrics.json` into the skill folder, and give the person both files so they can keep them (the skill folder may be reset when it is reinstalled).
- If memory tools are unavailable, say so and rely on the local copy.

Later changes ("I never use semicolons", "this doesn't sound like me") are offered as profile updates and saved only after a yes. Offer to update after the person edits one of your rewrites and the edit shows a consistent habit.

## Humanizing a text

1. **Intake.** Pasted text, or an attached file. For docx, edit the paragraph text in place so formatting survives (use the docx skill if available); do not regenerate the document. Work on a copy, never the upload.
2. **Baseline.** For anything over about 300 words, write the text to a scratch file and run `scripts/scan_tells.py FILE --dashes POLICY` (POLICY from the profile: none, minimal or natural). Note the tells per 1000 words and the categories.
3. **Draft.** Load `references/ai-patterns.md`. Rewrite using the patterns and the profile together: sentence length and rhythm, connectors, person and voice, punctuation rules, preferred and banned words, paragraph shape, structure, citation style. Replace machine habits with the person's habits, not with a neutral blank. Add opinion, humor or first person only where the profile and the content call for it.
4. **Audit.** Ask yourself: "What still reads as machine written, or as not this person?" Fix what you find. Look specifically for tidy template paragraphs, stacked short fragments, stock openers and closers, and any detail you added that the source does not support.
5. **Verify with scripts.** Run `scripts/scan_tells.py` again with the dash policy. If `style-metrics.json` exists, run `scripts/analyze_style.py --compare style-metrics.json FILE`. Treat CHECK lines as prompts to look, not as targets: fix a gap when it is a real mismatch with the person's voice, and ignore it when the content explains it (a short email will not match an essay profile).
   Then run `scripts/flag_claims.py FILE` and mention any figures, years or vague authorities that lack support, so the person can add sources. Do not fix them by inventing sources.
6. **Clean.** Run `scripts/clean_metadata.py` on the final text or file, with the defaults from the profile (author name, keep dates, straight quotes). For pasted text write the final to a scratch file, run it, and use the cleaned output.
7. **Deliver.** Follow the profile's output preference. Default: the final text only, plus a two or three line note listing anything you could not verify and any placeholders. "Show the work" mode adds the main changes and the before and after scan numbers. Files go back as files, never as text pasted into the chat. For a docx the person wants to review edit by edit, offer **tracked changes**: `python3 -I scripts/tracked_changes.py SOURCE.docx --dump paragraphs.txt`, rewrite that text file keeping the same number of paragraphs, then `tracked_changes.py SOURCE.docx rewritten.txt -o OUT.docx --author "Humanizer"`. Clean the result with `clean_metadata.py` only if the person does not mind the change author being kept (use `--anonymize-authors` otherwise).

Do not fix what is not broken. If a passage already sounds like the person, leave it. Clean human prose with no tells should come back almost unchanged and you should say so.

## Cleaning hidden markers

Use this on its own when the person asks to clean, scrub or check a file for metadata, watermarks, hidden characters or AI traces, and as step 6 above.

1. Run `scripts/clean_metadata.py --check FILE` first and tell the person what was found, in plain words and a few lines. Flags matter most: AI tool names in properties, GPS in pictures, content credentials, comments or tracked changes still inside a document, hidden Unicode text.
2. Then run it without `--check` (it writes a `.clean` copy next to the file, or use `-o DIR`). Re-run `--check` on the result to confirm it is clean.
3. Report what was removed and where the cleaned file is.

What it handles: invisible Unicode (zero width characters, soft hyphens, bidi marks, hidden Unicode tag text), odd spaces, pasted chatbot markers (oaicite, turn0search, source brackets, cite tags, utm_source=chatgpt.com), Office document properties, revision IDs, local file paths, thumbnails and zip timestamps, PDF Info and XMP, image EXIF, XMP, IPTC, PNG text chunks and C2PA content credentials. Details and limits are in `references/metadata-cleaning.md`.

What it cannot do, which you must say whenever the person asks about "watermarks" or "AI detection": statistical text watermarks live in word choice, not in metadata, and invisible pixel level image watermarks live in the pixels. This tool detects and removes neither. Rewriting in the person's own voice changes the text but gives no guarantee about any detector, and detectors are unreliable in both directions. Do not suggest otherwise.

Things the cleaner deliberately leaves alone and only reports: comments, tracked changes, hidden text, lookalike letters from other alphabets. Ask before removing content.

## Learning from corrections

When the person edits one of your rewrites and sends it back, or says "this doesn't sound like me", run `scripts/diff_edits.py REWRITE FINAL`. It lists what they shortened, removed twice or more, and swapped. Show the candidate rules in a few lines and offer to add the confirmed ones to the profile. Never update the profile without a yes, and ignore one off edits (a single change is not a habit).

## Batch mode

For a folder of files: list the files and the profile you will apply, run the pipeline per file (baseline, rewrite, verify, clean), write results to a separate output folder, and finish with one summary table: file, tells per 1000 words before and after, items removed by the cleaner, flags. Use `clean_metadata.py -r -o OUTDIR FOLDER` when only cleaning is needed. Ask before starting if there are more than ten files, since each rewrite takes time.

## Disclosure note

If the person asks for an AI assistance statement, or the profile has a disclosure reminder, read `references/disclosure-note.md` and draft a short, accurate note for their context. Describe only what was actually done; the person decides whether and where to include it.

## Other requests this skill covers

- "Show my style profile": print the stored profile in a readable form.
- "Check this for AI tells": run `scripts/scan_tells.py`, explain the categories, offer a rewrite. State that it is a habit counter, not a detector.
- "Compare this with my style": run `scripts/analyze_style.py --compare`.
- "Show the work" (or the profile says so): after the final text, give the main changes in a few lines and a before and after line from the scan, for example "tracked habits 41 to 6 per 1000 words, average sentence 14 to 23 words".
- "Change my style rule": edit the profile after the person confirms the change.

## Reference files

| File | When to read it |
| --- | --- |
| `references/onboarding.md` | Running the first time setup interview |
| `references/style-profile-template.md` | Drafting, showing, or saving the profile |
| `references/ai-patterns.md` | Drafting and auditing any rewrite (35 patterns, personality guidance, false positives) |
| `references/metadata-cleaning.md` | Explaining what the cleaner touches, or handling an unusual file |
| `references/disclosure-note.md` | Drafting an AI assistance statement |

Scripts: `scripts/analyze_style.py` (measure or compare a style), `scripts/scan_tells.py` (count machine habits and check dash policy), `scripts/clean_metadata.py` (check or clean files and text), `scripts/flag_claims.py` (unsupported claims), `scripts/diff_edits.py` (learn from the person's edits), `scripts/tracked_changes.py` (deliver a rewrite as Word tracked changes).
