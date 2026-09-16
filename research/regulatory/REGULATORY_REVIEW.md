# US and Singapore regulatory review file

**Document ID:** CA-REG-001  
**Version:** 0.1-draft  
**Date:** 2026-09-16  
**Decision status:** Open — no classification conclusion

This is a structured question set for qualified counsel or a regulatory professional. It is not a
legal opinion and deliberately does not conclude that CareAlign is or is not a medical device.

## Facts to freeze before review

1. Intended use and exclusions: [`INTENDED_USE.md`](INTENDED_USE.md).
2. Patient/caregiver-facing output is a source-linked discrepancy and clarification question.
3. The system does not state which instruction is correct, but its output may influence whether and
   how a user seeks professional clarification.
4. Current public deployment permits synthetic data only and is not configured for PHI.
5. LLM output cannot directly create a conflict; strict validation and deterministic rules do so.
6. Unsupported, ambiguous, and unavailable states fail to review rather than no-conflict.

## United States questions

- Does the exact patient/caregiver-facing intended use place any function within the device
  definition or another FDA digital-health policy, even though the output is non-prescriptive?
- Which functions, if any, can satisfy each element of the current non-device CDS criteria, given
  that the primary user is not always a healthcare professional?
- Must the source/evidence display provide any additional basis information for independent review?
- Would adding urgency, prioritization, interaction checking, dose recommendations, or automatic
  resolution materially change classification?
- What quality-system, complaint, change-control, cybersecurity, and validation obligations apply
  before any US clinical pilot?
- Separately, are the planned activities research involving human subjects, and which IRB/privacy
  determinations and agreements are required?

Primary reference: FDA’s final *Clinical Decision Support Software* guidance, January 2026:
https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software

## Singapore questions

- Does CareAlign qualify as Clinical Decision Support Software, Software as a Medical Device, or a
  non-medical-device function under the current HSA guidance and the proposed intended use?
- If it is a medical device, what risk class, registration route, local registrant, and evidence are
  required before supply or clinical use in Singapore?
- Does the output count as a recommendation, and is its basis “solely established clinical
  guidelines” when LLM extraction plus deterministic comparison is used?
- What changes to intended user, claimed benefit, or output would change qualification/class?
- Which HSA pre-submission clarification route should be used before a controlled pilot?
- Which PDPA roles, notification/consent purposes, retention, access, breach, transfer, and vendor
  obligations would apply to any future personal-data processing?

Primary references:

- HSA update effective 21 July 2025:
  https://www.hsa.gov.sg/announcements/update-for-guidelines-on-risk-classification-of-samd-and-qualification-of-clinical-decision-support-software--cdss-/
- Singapore PDPC, *Advisory Guidelines for the Healthcare Sector*:
  https://www.pdpc.gov.sg/

## Human-subject research gate

Before recruiting anyone, obtain a written determination from the responsible NUS or other
institutional ethics channel. NUS materials state that student research involving human subjects
requires ethics review through the applicable route. Record the determination ID, date, protocol
version, and conditions in the study folder; do not infer exemption independently.

## Decision record

| Jurisdiction | Reviewer/name and qualification | Date | Protocol/intended-use version | Determination | Conditions | Evidence link |
|---|---|---|---|---|---|---|
| United States | Pending | — | CA-IU-001 v0.1 | Open | No clinical deployment | — |
| Singapore | Pending | — | CA-IU-001 v0.1 | Open | No clinical deployment | — |
| Research ethics | Pending | — | Usability protocol v0.1 | Open | No recruitment | — |

