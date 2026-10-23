# Input expansion: language, PDF and image input

**Status:** design note. Only the safety boundary in the first section is implemented.

## What the system does today

CareAlign accepts typed text and works as designed for **English** instructions. Every safety net
that sits between the model and a "validated" instruction reads English vocabulary: the schedule
checks (as needed, taper, every other day, weekly), the frequency/interval/route/action
consistency checks, the dose-unit check and the teach-back matcher.

That has one consequence that matters. A model can mislabel a PRN or every-other-day instruction as a
fixed schedule. In English the evidence check catches it. In Korean, Russian or any other script it
cannot, so before this boundary existed such an instruction ended `validated`.

**Implemented boundary:** an instruction whose evidence quote contains letters outside the Latin
script is never auto-validated. It is returned as `needs_review`, still source-linked, and is left out
of teach-back. Dose, frequency and omission comparison remain language-independent because they
compare numbers, so a changed dose is still flagged. Teach-back never reports a non-Latin expected
value as correct; it reports it as missing.

This is a safety boundary, not language support.

## Why Korean and other languages are not simply "turned on"

- The schedule vocabulary needs a reviewed list per language (for example the words for as needed,
  at bedtime, 30 minutes after meals, every other day, and the many ways to write once or twice a
  day). A list written without a native-speaking clinician will miss phrasings, and a miss is a
  silent validation, not an error.
- Korean attaches particles to nouns, so the whole-token matching used for English teach-back does
  not transfer. Naive substring matching would reintroduce false "correct" answers.
- Dose notation differs (units written in words, counters, mixed scripts).
- The evaluation sets are English. A language without an independently labelled set has no evidence.

## Before a language can be enabled

1. A written vocabulary for that language, reviewed by a clinician who works in it.
2. At least 30 independently labelled cases, including mislabelled-schedule cases like the 8
   `mislabelled_schedule` cases in `evaluation/cases/atypical-v1.jsonl`.
3. The gate that already exists for English: 0 unsafe cases may stay `validated`, and no more than
   10% of correct cases may be downgraded.
4. A live-model run on those cases.

Only then is the language added to the allowed scripts, and only together with its own checks.

## PDF and image input

Not implemented, deliberately.

- **Privacy boundary.** The prototype is for synthetic text only. A file upload invites real
  discharge summaries, which carry identifiers the text box does not.
- **Silent errors.** OCR can turn a dose into a different dose. The current evidence check proves
  that a quote exists in the supplied *text*; it cannot show that the text matches the page.
- **Provider handling.** Sending page images to a model provider needs its own data-handling
  decision.

A defensible order, each step behind its own gate:

1. **PDF with a text layer, no OCR.** Extract the text and keep page and offset as evidence. This
   needs no new model behaviour and keeps the existing evidence check meaningful.
2. **Images or scanned PDFs.** Show the extracted text next to the page and require the user to
   confirm every dose, frequency and route before analysis. Never auto-validate OCR output.
3. **Real patient data.** Only after the ethics and privacy determination described in
   `research/ethics/`.
