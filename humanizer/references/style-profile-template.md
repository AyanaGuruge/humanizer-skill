# Style profile format

Used for the stored memory file and for the local `style-profile.md`. Every line is a fact or rule the person confirmed. Keep it short: it is read at the start of every humanize request.

## Memory file (compact, about 15 to 25 lines)

Path: `/topics/writing-style.md` (follow the session's memory instructions for front matter and tagging). One fact per line.

```
Voice in one line: <for example "formal academic, long flowing sentences, careful and methodical">
Languages: <language(s)>; English variety: <British | American | other>
Registers: <register name: key traits>; <register name: key traits>
Sentences: mean <N> words, wide spread; keep long sentences joined by formal connectors
Voice and person: passive voice <often | sometimes | rarely>; first person <I | we | avoid>; contractions <never | sometimes | often>
Connectors they use: <list>; connectors they avoid: <list>
Dash policy: <none | minimal | natural>; hyphens in compounds: <fine | avoid>
Other punctuation: semicolons <yes | no>; Oxford comma <yes | no>; quotes <straight | curly>; exclamation marks <never | rarely>
Words they never use: <list>; signature words or phrases: <short list>
Structure: paragraphs about <N> words; <prose | bullets | mixed>; headings <numbered | plain | none>; openings <how>; closings <how>
Citations: <style>; never touch citations or quotations
Personality: <neutral | light | strong>; opinions <yes | no>; humor <yes | no>
Output: <final only | show changes>; length <within 10 percent | free>
Files: clean automatically <yes | no>; author name <blank | name>; keep dates <yes | no>; straight quotes <yes | no>
Disclosure reminder: <none | text of the one line reminder>
Metrics file: style-metrics.json (local copy) holds the measured fingerprint
```

## Local file `style-profile.md` (fuller)

Same fields as above, plus:

- **Measured summary:** paste the output of `analyze_style.py` (the readable summary), with the date and the files it came from (names only).
- **Observed habits (confirmed):** the five to eight observations the person agreed with.
- **Do and don't list:** concrete examples, for instance "Do: open with a context sentence before the claim. Don't: end paragraphs with a summarizing sentence."
- **Calibration notes:** what was wrong in the test paragraph and how the profile changed.
- **Changelog:** date and one line per later update.

## What never goes in the profile

- Passages copied from the person's documents (patterns and short signature phrases only).
- Names of people, employers or institutions mentioned in the samples.
- Anything sensitive about the person (health, finances, identity), or guesses about their personality. Only writing rules the person confirmed.
- Instructions that would make future rewrites less honest, for example "never flag unsupported claims" or "invent supporting detail". Rule 1 of the skill always applies.
