# First time setup: the style interview

Goal: end with a style profile specific enough that a rewrite sounds like the person and generic enough to reuse. Time budget: about ten minutes, roughly ten to fourteen questions. The method is a grilling session: one question at a time, with a recommended answer, resolving each branch before moving on.

## How to run it

- Open with two sentences: what will happen (share some of your writing, a few quick questions, a test paragraph, then save) and that they can stop at any time.
- Say once, plainly, that the documents stay in this chat and only patterns and a few short phrases are saved, never passages. Ask them to remove confidential material from samples.
- One question per turn. Give your recommended answer first, based on what you measured, and 2 to 4 short options. Accept a free answer at any point. Use the question tool if the session has one; otherwise ask in plain text.
- Do not ask what the samples already show. Instead state what you saw and ask for confirmation ("Your sentences average 28 words and you use passive voice a lot. Keep both?").
- When an answer contradicts the measurements, point it out gently and let them decide. The stated preference wins; record it as a rule.
- Follow branches: a "no dashes" answer opens the hyphen question and the number range question; "formal" opens the contractions question; "I write in two languages" opens a per language profile.
- If they have no samples, run the interview alone, say the profile will be rougher, and offer to refine it after the first few rewrites.
- Keep each message short. Never dump the full question list.

## Phase A: collect samples

Ask for 3 to 5 pieces of their own writing from different situations, for example an essay or report, a work email, and a casual message. File types: docx, pdf, txt, md, or pasted text. At least about 1500 words in total. Best if written without AI help. Recommended: add one piece they are proud of.

If all their writing is AI assisted, ask them to say which parts are theirs, and lean on the interview.

Optional, later: one example of writing they dislike or that "sounds like a robot to me", to learn what to avoid.

## Phase B: measure and read

1. Run `python3 -I scripts/analyze_style.py FILE... --json style-metrics.json` on the uploaded files (copies, not the originals). Note the confidence line; under 1500 words means low confidence.
2. Read the samples yourself. Note, as candidate observations to confirm: how paragraphs open and close, how arguments are built, typical connectors, humor or restraint, hedging habits, favorite constructions, recurring phrases, how they handle lists and citations, anything unusual (second language influence, regional phrasing).
3. Pick the five to eight most useful observations and the numbers that matter. Do not read the whole report out.

## Phase C: question bank

Ask only what is still open. Order matters because later questions depend on earlier answers.

1. **Language and variety.** Which language(s) do you write in, and which English (British, American, other)? Recommend the measured spelling variant. If not English, say the pattern list is English centred and you will rely on their samples and judgment.
2. **Main uses.** What will you mostly humanize? Academic papers or reports, work emails, blog or social posts, creative writing, applications and cover letters, a mix. This sets the registers; if they need two registers, record both (for example "academic: formal, passive; messages: casual, short").
3. **Register.** Formality from casual to formal, warmth, directness. Recommend what the samples show.
4. **Person and voice.** Is first person fine (I, we)? Passive voice? Contractions? Recommend the measured rates.
5. **Rhythm.** State their average and spread. Keep it, tighten it, or vary it more?
6. **Punctuation rules.** Ask separately, because these are the cheapest wins:
   - Dashes: use freely, minimal, or none at all. If none, ask: no hyphens in compound words either? Then ranges are written with words.
   - Semicolons and colons, Oxford comma, exclamation marks, parentheses.
   - Straight or curly quotes.
7. **Words.** Any words or phrases you never use or hate seeing? (Offer the common machine vocabulary as a quick ban: delve, tapestry, testament, pivotal, vibrant, landscape, underscore, showcase, foster, crucial.) Any signature words or phrases that are very you?
8. **Structure and formatting.** Prose or bullets? Headings? Typical paragraph length? How do you usually open and close a piece? Numbered sections?
9. **Citations.** Style (IEEE, APA, Harvard, footnotes, none). Rule: citations and quotations are never touched.
10. **Personality.** Should rewrites add opinion, humor or first person voice, or stay neutral? Recommend neutral for academic and technical writing, a light touch for blogs and messages.
11. **Output preferences.** Final text only, or also the changes and before and after numbers? Keep length within about 10 percent or free? Chat reply or file when the input was a file?
12. **File cleaning defaults.** Clean files automatically before returning them (recommended)? Author name to write: blank (recommended), their name, or keep? Keep created and modified dates? Convert curly quotes to straight?
13. **Disclosure.** Do you have to disclose AI assistance anywhere (university, employer, journal)? If yes, record a short reminder to give when delivering work for that context. Ask this as a practical setting, one line, no lecture.
14. **Anything else** that makes your writing yours, or that rewrites keep getting wrong?

Stop early when the remaining questions would not change the output.

## Phase D: draft, show, calibrate

1. Fill the template in `style-profile-template.md`. Keep the memory version to about 15 to 25 short lines.
2. Show it as a compact summary (not the whole file) and ask what to correct.
3. Calibration: write a neutral, slightly machine sounding paragraph of about 80 words on a topic from their field, then rewrite it in their voice using the profile. Ask: "Does this sound like you? What is off?" Adjust the profile; one more round if needed. Then run `scripts/scan_tells.py` and `scripts/analyze_style.py --compare` on the rewritten paragraph as a sanity check (short samples are rough).
4. Get an explicit confirmation of the final profile.

## Phase E: save

Follow "Saving the profile" in SKILL.md: ask permission once, write memory, write the local `style-profile.md` and `style-metrics.json`, hand the files to the person. Finish with one sentence on how to use it ("Send me any text and say humanize") and how to change it ("say 'update my style' any time").

## Updating later

- "Update my style": run only the relevant questions; compare with the stored profile; edit changed lines and keep the rest.
- "Redo setup": run the whole interview, then replace the stored profile after confirmation.
- When they edit one of your rewrites, look at what they changed. If it shows a clear habit (they always remove "Moreover", they shorten openings), offer to add it as a rule.
