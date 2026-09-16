# Intended use statement

**Document ID:** CA-IU-001  
**Version:** 0.1-draft  
**Date:** 2026-09-16  
**Owner:** OH CHANGSUNG  
**Approval status:** Not approved; requires clinical and regulatory review

## Proposed intended use

CareAlign is intended to help an adult patient or caregiver review two to five non-urgent,
text-based medication instruction records from a care transition. It identifies source-verifiable
differences using semantic extraction followed by deterministic rules and presents a neutral
question that the user can take to a qualified healthcare professional.

## Intended users and setting

- Adult patients and caregivers who can read the supported interface language.
- Qualified healthcare professionals reviewing the generated source-linked question.
- Non-emergency care-transition review outside time-critical treatment decisions.
- Current research is limited to fictional, synthetic, or properly governed data approved for the
  relevant study phase.

## Explicit exclusions

CareAlign is not intended to:

- diagnose, prescribe, select the correct order, recommend a treatment, or determine intent;
- replace medication reconciliation, pharmacist review, or clinician judgment;
- provide emergency alerts, dose calculators, interaction checks, or adherence monitoring;
- infer that an omitted medicine was intentionally stopped;
- establish therapeutic equivalence between salts, formulations, brands, or products;
- process real patient data in the current public prototype;
- support pediatric, pregnancy, renal/hepatic dosing, or other population-specific decisions.

## Output and action

The primary output is a potential difference, its source evidence, and a clarification question.
The user action is to contact a qualified professional. A user-entered care-team response is stored
only in the browser session, remains visibly unverified, and does not change the clinical flag to
`resolved`.

## Change control

Any change to intended user, urgency, input source, target population, output wording, automation,
or recommended action requires a new version and a repeat regulatory assessment. Marketing claims
must remain consistent with this document and [`CLAIMS_MATRIX.md`](CLAIMS_MATRIX.md).

