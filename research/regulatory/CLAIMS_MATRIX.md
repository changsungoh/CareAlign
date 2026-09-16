# Product claims matrix

**Status:** Draft control document. Each public claim must have an evidence owner and version.

| Claim | Current status | Required evidence | Approved wording now |
|---|---|---|---|
| Finds rule-verifiable differences in synthetic cases | Supported as engineering evidence | Versioned synthetic dataset and report | “Detects potential differences in synthetic medication instructions.” |
| Preserves source evidence | Supported by tests | Evidence-span test results | “Links each displayed flag to supplied source text.” |
| Uses RxNorm | Conditional | Runtime enabled, version captured, clinical review | “Includes an optional, disabled-by-default RxNorm terminology aid.” |
| Improves patient safety | Prohibited | Prospective clinical evidence and regulatory review | None |
| Prevents medication errors | Prohibited | Clinical outcome study and regulatory review | None |
| Clinically validated | Prohibited | Independent locked study meeting prespecified endpoints | None |
| Accurate or 100% accurate | Prohibited | Defined population, independent reference standard, uncertainty | Report metric plus dataset and limitations only |
| HIPAA compliant / PDPA compliant | Prohibited | Applicability determination, implemented controls, legal review | “Not configured for identifiable health information.” |
| FDA/HSA cleared, approved, registered, exempt, or non-device | Prohibited | Written jurisdiction-specific determination | “Regulatory status has not been determined.” |
| Reconciles medications | Prohibited for patient-facing MVP | Validated clinician workflow and regulatory review | “Prepares questions for professional confirmation.” |
| AI resolved the conflict | Prohibited by design | Not applicable | “A user recorded an unverified care-team response.” |

## Review rule

Screenshots, demos, README text, presentations, social posts, and spoken pitches are all promotional
surfaces for this matrix. If a new sentence implies a stronger claim, it must be added here before
publication.

