# External validation execution plan

**Owner:** OH CHANGSUNG  
**Version:** 1.0  
**Date:** 2026-09-16  
**Current phase:** Gate 0 — institutional route and documents

The work now moves from internally authored engineering evidence to external review. A gate may
advance only when its evidence exists; planned activity is never reported as completed.

| Gate | Required action | Evidence to retain | Status |
|---|---|---|---|
| 0. Route | Confirm department, supervisor/PI eligibility, DERC/IRB route, CITI, privacy owner | Written route/determination, CITI report, final document versions | In progress |
| 1. Freeze | Tag deployment, export cases, hash all inputs, lock analysis definitions | Commit SHA, deployment URL, manifest and SHA-256 hashes | Not started |
| 2. Expert review | Recruit two independent qualified reviewers; blinded first pass | Attestations, locked reviewer exports, timestamps | Blocked by scope/contract |
| 3. Adjudication | Resolve disagreements without overwriting original judgments | Raw agreement, adjudication log, signed decision trail | Blocked by Gate 2 |
| 4. Usability round 1 | Run approved synthetic sessions | Consent records, session log, deviations, findings | Blocked by Gate 0 |
| 5. Remediation | Fix critical/major findings on a development set | Linked issues, tests, release notes | Blocked by Gates 3–4 |
| 6. Confirmatory round | Retest frozen build and predeclared endpoints | Versioned report including failures and attrition | Blocked by Gate 5 |
| 7. Claims review | Reconcile evidence with claims matrix and regulatory advice | Signed review memo and updated claim status | Blocked by all prior gates |

## Immediate operator checklist

1. Fill the bracketed administrative fields in
   [`ethics/ETHICS_DETERMINATION_REQUEST.md`](ethics/ETHICS_DETERMINATION_REQUEST.md) outside the
   public repository where personal identifiers are involved.
2. Identify the student's NUS school/department and obtain a supervisor/PI sponsor if the route
   requires one.
3. Complete the NUS CITI Social & Behavioral Research Basic/Refresher course and retain the
   completion report; do not commit the certificate publicly.
4. Ask the relevant DERC/NUS-IRB to determine SBER review category and whether DERC or iRIMS-IRB
   submission is required.
5. Confirm the approved storage, retention, incident, consent, recording, compensation, and
   recruitment rules.
6. Finalise expert compensation and secure credential-verification method, then send the invitation
   only after those controls are ready.

## Evidence folder convention

Do not commit identifiable evidence to this public repository. Use an approved restricted location
with this structure:

```text
CA-VALIDATION/
  00-governance/
  01-frozen-inputs/
  02-expert-locked/
  03-adjudication/
  04-usability-raw/
  05-analysis/
  06-reports/
```

Each gate gets a manifest containing artifact name, version, date/time, owner, SHA-256, access
classification, and deviation reference. Public outputs contain only blank templates,
de-identified aggregates, and approved reports.

## Decision rules

- No recruitment, pilot session, or expert case access before its prerequisite gate.
- No retroactive ethics approval claim.
- No deletion of failed cases, withdrawals, disagreements, or adverse interpretations.
- No model/rule tuning on the locked final test set.
- Any material protocol, task, endpoint, or population change requires a dated amendment and any
  required ethics approval before use.
- If a critical misunderstanding or harmful wording is found, pause the affected flow, file an
  issue, remediate, and retest before making a stronger claim.

