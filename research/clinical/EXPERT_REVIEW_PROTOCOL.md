# Independent medical expert review protocol

**Protocol ID:** CA-CLIN-001  
**Version:** 0.1-draft  
**Date:** 2026-09-16  
**Status:** Reviewers not recruited; no independent validation completed

## Objective

Create an independent reference set for whether synthetic source pairs contain a difference that
warrants professional clarification, whether CareAlign’s evidence is source-faithful, and whether
the clarification wording avoids a treatment recommendation.

## Independence and qualifications

Recruit at least two reviewers who did not author the cases, labels, rules, prompts, or product
code. The panel should include a licensed pharmacist with medication-reconciliation experience and
a licensed prescribing clinician or equivalently relevant physician/advanced-practice reviewer.
Record jurisdiction, active-license confirmation method, relevant experience, conflicts, payment,
and relationship to the builder. A third qualified reviewer adjudicates unresolved disagreements.

## Blinding

For the first pass, randomize case order and hide CareAlign output, original author labels, expected
category, and other reviewers’ answers. Reviewers receive only the fictional source documents,
dates, controlled labeling instructions, and a randomly generated case ID. Lock first-pass files
before revealing system output.

## Review set

Use all 43 conflict-detection cases plus a separately frozen RxNorm edge set covering brand/generic,
salt, formulation, strength/dose form, multi-ingredient, package, misspelling, ambiguous, unavailable,
and unsupported-term-type cases. Unsupported-pattern, security, teach-back, and resilience cases
remain engineering endpoints unless separately assigned to an appropriate reviewer.

The initial 12-case terminology set is
[`rxnorm-edge-cases-v1.csv`](rxnorm-edge-cases-v1.csv). Its clinical labels intentionally remain
`pending_independent_review`; the engineering disposition is a fail-closed requirement, not an
expert determination of interchangeability.

## First-pass questions

For each transition, independently record:

1. `reference_outcome`: clarification warranted / no clarification warranted / insufficient information.
2. `reference_category`: dose / frequency / route / action / possible omission / identity / other / none.
3. `clinically_meaningful`: yes / no / uncertain, with reason.
4. Exact supporting spans from each source.
5. Whether a salt/form/brand/generic relation can be treated as the same comparison identity.
6. Reviewer confidence from 1–5 and a brief rationale.

After locking the first pass, reveal CareAlign output and independently rate evidence fidelity,
neutrality, potential for harmful interpretation, and whether the question should be shown.

## Adjudication

Compare locked reviewer files with a script that does not overwrite either judgment. Discuss every
primary-outcome or category disagreement. Record the final label, rationale, cited source text,
participants, and whether consensus or third-reviewer decision was used in
`ADJUDICATION_LOG.csv`. Report raw agreement and disagreement counts before adjudication. If an
important ambiguity cannot be resolved, retain `insufficient_information` rather than force a label.

## Metrics and release interpretation

Calculate precision and recall only against the locked adjudicated reference set, with 95%
confidence intervals and raw confusion-matrix counts. Separately report evidence-fidelity failures,
harmful-wording cases, identity-policy errors, and abstentions. Subgroups with very small counts are
descriptive. Thresholds for any clinical claim or deployment must be set prospectively by the
clinical/statistical leads; the current synthetic gate of 0.85 is an engineering release rule, not a
clinical safety threshold.

## Integrity controls

- Hash and date the case bundle, instructions, and locked reviewer exports.
- Record all exclusions, unavailable reviews, and protocol deviations.
- Do not tune the product on the final locked test set; create a separate development set.
- Publish reviewer funding/conflicts and whether they saw the system before their first pass.
- Call the result “independent synthetic expert review,” not clinical validation of real patients.
