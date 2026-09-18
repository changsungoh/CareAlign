# CareAlign

## Elevator pitch

CareAlign catches conflicting care instructions before they become medication mistakes—then turns
every source-linked mismatch into the exact question a patient should ask.

## Inspiration and problem

A patient leaving a hospital may receive instructions from a discharge team, a specialist, and a
pharmacy. The documents rarely use identical wording, may arrive on different dates, and can quietly
omit an earlier medication. The patient is then expected to determine whether a change was
intentional. A 2020 systematic review included 54 studies overall; in its adult unintentional
medication-discrepancy analysis of 11 studies, the median rate after hospital discharge was 50%
(IQR 39–76%) (Alqenae, Steinke, and Keers, *Drug Safety*, 2020;
[PubMed 32125666](https://pubmed.ncbi.nlm.nih.gov/32125666/)).

## What it does

CareAlign compares two to five chronological synthetic care documents. AI extracts differently
worded medication instructions into a strict schema. Code verifies every evidence span, normalizes
known medication identities/routes/units, and deterministically checks dose, frequency, route,
action, and possible omissions. The product does not select the correct instruction. It shows the
original source and prepares a plain-language clarification question for the care team.

The user can copy, print, or download questions; record a fictional care-team response in the current
browser session; and optionally use teach-back on validated, non-conflicted instructions. User-entered
responses remain visibly unverified, and AI cannot mark a conflict resolved.

## Why AI is necessary—and bounded

String comparison cannot reliably recognize that “take one tablet morning and evening” and “two
doses daily” may express related meaning. The LLM handles semantic extraction only. It operates
inside an untrusted-document boundary and must return strict structured output with source evidence.
Deterministic code owns comparison and failure policy. Unknown identity, unsupported schedules,
unverifiable evidence, low confidence, invalid output, or provider failure produces review or
unavailable—not false reassurance.

## How we built it

- Next.js 16, React 19 and TypeScript for the accessible patient-facing workflow
- FastAPI and Pydantic for the stateless API and strict contracts
- Anthropic-compatible structured extraction for live AI mode
- NLM RxNorm API as an optional, conservative terminology resolver
- Read-only FHIR R4 medication import with source-date grouping and field-level provenance
- Decimal unit conversion and versioned deterministic rules
- Browser `sessionStorage` for ephemeral, human-entered notes
- Pytest, Ruff, Playwright, GitHub Actions, Docker, Render and Vercel configuration

## Safety, privacy, and challenges

The prototype accepts synthetic data only and is not HIPAA compliant, clinically validated, medical
advice, or a diagnostic/prescriptive device. It has no case database or retrieval endpoint, and raw
logging is disabled. The hardest design challenge was preserving useful AI semantics without letting
the model make a clinical decision. We addressed this through evidence verification, curated
salt/form distinctions, unsupported-pattern containment, explicit uncertainty, human-only
resolution, rate limits, prompt-injection tests, and a visibly labelled Demo Mode.

PRN, conditional, taper, range, and other complex schedules remain source text and are routed to
review. Future work may separately extract PRN maximum dose/frequency, conditional thresholds, and
taper-phase context. We also considered an IR-to-ER formulation-change category but excluded it from
the MVP to avoid introducing a new clinical inference surface without adequate validation; CareAlign
does not infer whether a formulation change was intentional.

## Evaluation

The repository includes 90 versioned synthetic cases across conflict detection, unsupported-pattern
containment, teach-back paraphrases, adversarial text, and fault injection. The deterministic
bundled-parser report is kept separate from a cost-confirmed live Claude run of 85 functional cases
(128 provider calls) plus five resilience fault-injection cases. Both reports produced perfect
results on this synthetic, author-labeled dataset; neither is independent or clinical validation.
The prepared delayed solo label review remains incomplete. Artifacts retain model, prompt, rules,
dataset, token, cost, and failure accounting for reproducibility.

## Impact and future scope

CareAlign targets one preventable part of medication harm: the information gap between care records
and patient understanding. Next steps are independent clinician labeling, longitudinal usability
research, broader accessibility testing, deeper RxNorm-assisted identity, consented EHR OAuth,
and formal privacy, security, ethics, and regulatory assessment before any real-data pilot.

## Team

- **OH CHANGSUNG — Solo Builder:** product strategy, healthcare research, architecture, AI
  pipeline, deterministic rules, frontend and backend implementation, accessibility, evaluation,
  documentation, and deployment integration.
