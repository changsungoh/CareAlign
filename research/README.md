# CareAlign validation program

**Program status:** protocol-ready; no human-subject, clinical-validation, regulatory-clearance, or
independent-review claim has been earned.

This directory turns four post-MVP goals into auditable workstreams. A document marked `Draft` is a
plan, not evidence that the activity occurred. Completed work must include dated source artifacts,
the responsible person, deviations, failures, and an immutable result or signed record.

| Workstream | Current evidence | Next external gate | Completion evidence |
|---|---|---|---|
| RxNorm terminology | Exact-first resolver, fail-closed statuses, provenance fields, unit tests | Clinical review of identity policy and edge-case set | Reviewed policy, frozen test set, versioned results |
| Clinical/regulatory | Intended use, claims matrix, risk register, US/Singapore questions | Qualified regulatory review | Signed determination memo per target jurisdiction |
| User testing | Synthetic-only protocol, consent script, task guide, session log | NUS/appropriate ethics determination before recruitment | Determination ID, consent records, de-identified results |
| Independent medical review | Blinded review and adjudication protocol | Recruit independent qualified reviewers | Credential attestations, locked labels, adjudication report |

## Non-negotiable boundaries

- Do not enter or recruit around real patient data in the current application.
- Do not call usability feedback “clinical validation.”
- Do not call the author-created synthetic labels an independent gold standard.
- Do not claim HIPAA/PDPA compliance, FDA/HSA status, safety, effectiveness, or medical-device
  exemption without a written determination from the appropriate qualified owner.
- Do not delete failed sessions, reviewer disagreements, protocol deviations, or excluded cases.

## Artifact map

- [`regulatory/INTENDED_USE.md`](regulatory/INTENDED_USE.md): frozen intended-use boundary.
- [`regulatory/REGULATORY_REVIEW.md`](regulatory/REGULATORY_REVIEW.md): US/Singapore decision file.
- [`regulatory/CLAIMS_MATRIX.md`](regulatory/CLAIMS_MATRIX.md): permitted and prohibited language.
- [`regulatory/RISK_REGISTER.csv`](regulatory/RISK_REGISTER.csv): initial safety-risk inventory.
- [`usability/PROTOCOL.md`](usability/PROTOCOL.md): synthetic formative study protocol.
- [`usability/CONSENT_AND_MODERATOR_GUIDE.md`](usability/CONSENT_AND_MODERATOR_GUIDE.md): participant-facing script.
- [`usability/SESSION_LOG.csv`](usability/SESSION_LOG.csv): one row per attempted session.
- [`usability/ANALYSIS_TEMPLATE.md`](usability/ANALYSIS_TEMPLATE.md): predeclared reporting structure.
- [`clinical/EXPERT_REVIEW_PROTOCOL.md`](clinical/EXPERT_REVIEW_PROTOCOL.md): independent blinded review.
- [`clinical/rxnorm-edge-cases-v1.csv`](clinical/rxnorm-edge-cases-v1.csv): terminology safety set awaiting expert labels.
- [`clinical/REVIEW_FORM.csv`](clinical/REVIEW_FORM.csv): one reviewer judgment per row.
- [`clinical/ADJUDICATION_LOG.csv`](clinical/ADJUDICATION_LOG.csv): disagreement resolution trail.
- [`clinical/REVIEWER_ATTESTATION.md`](clinical/REVIEWER_ATTESTATION.md): qualifications and independence.
