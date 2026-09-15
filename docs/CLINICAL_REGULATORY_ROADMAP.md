# Clinical, privacy, and regulatory roadmap

> Planning document only. It is not legal, regulatory, security, or clinical advice and does not
> state that CareAlign is compliant, validated, cleared, or approved.

## Current prototype boundary

CareAlign is a synthetic-data research prototype. It does not determine which medication order is
correct, recommend a treatment, replace medication reconciliation, or provide time-critical alerts.
It displays source-linked potential differences and prepares questions for a qualified professional.
No real patient data, clinical deployment, or clinical performance claim is permitted in this phase.

## Stage gates

| Stage | Permitted work | Evidence required before advancement | Stop condition |
|---|---|---|---|
| 0: Hackathon | Synthetic data, usability inspection, engineering tests | Source traceability and safe-failure gates | Any false reassurance or invented evidence |
| 1: Formative research | Consented interviews using fictional cases | Ethics determination, protocol, accessibility review | Participant confusion about medical-advice boundary |
| 2: Retrospective validation | Properly governed de-identified records | DUA/BAA as applicable, IRB/ethics review, clinician gold standard | Unsafe subgroup performance or unresolved privacy risk |
| 3: Silent prospective study | No patient-facing output | Registered protocol, monitoring and incident process | Drift, clinically meaningful false negatives, workflow harm |
| 4: Controlled pilot | Human-supervised output in one workflow | Regulatory determination, QMS, security assessment, training | Safety threshold breach or unauthorized data exposure |

## Clinical evaluation design

Primary engineering endpoints are conflict precision/recall, evidence traceability, unsupported
pattern containment, and false reassurance. A future clinical study must separately measure whether
clinicians agree that a flag warrants clarification, whether patients understand the generated
question, time burden, false-alert fatigue, subgroup performance, and any delayed or inappropriate
care. Labels require at least two independent qualified reviewers with adjudication; the current
synthetic author-reviewed dataset is not a clinical benchmark.

## Privacy pathway

The current application stores no documents server-side and prohibits PHI. Before any ePHI use, the
project must determine covered-entity/business-associate roles, complete risk analysis, data-flow and
vendor reviews, establish minimum-necessary access, authentication, audit controls, integrity and
transmission protections, incident response, retention/deletion, workforce procedures, and required
agreements. HHS describes administrative, physical, and technical safeguards and emphasizes
confidentiality, integrity, and availability; the current disclaimer is not a substitute for these
controls: [HHS HIPAA Security Rule summary](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html).

For GDPR-scoped work, obtain qualified review of lawful basis, controller/processor roles, special
category data conditions, data minimization, DPIA need, data-subject rights, transfers, retention,
and automated-decision safeguards before processing personal health data.

## Regulatory pathway

CareAlign must obtain a jurisdiction-specific regulatory determination before clinical deployment.
The analysis must consider intended user, intended use, whether output is patient-facing, urgency,
automation, explainability, and whether a professional can independently review the basis. The FDA's
current final Clinical Decision Support guidance is dated January 2026:
[FDA CDS guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software).
Until counsel and regulators determine otherwise, all product language must remain conservative and
must not claim that CareAlign is exempt, non-device, safe, effective, or cleared.

## Accessibility and health literacy

Patient-facing research targets plain language, nonjudgmental teach-back, keyboard operation,
meaningful headings, high contrast, large text, reduced motion, printable questions, and testing with
older adults, caregivers, low-literacy users, assistive-technology users, and multilingual users.

## Ownership

The engineering owner maintains model/prompt/rules versions, security controls, incident logs, and
release gates. A future clinical lead owns labeling instructions and safety adjudication. A privacy
and security owner approves data flows. Qualified regulatory counsel owns classification strategy.
No single hackathon participant can self-approve advancement through these gates.
