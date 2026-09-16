# Data management plan

**Study ID:** CA-UX-001
**Version:** 0.1-draft
**Status:** Requires ethics/privacy confirmation before use

## Data-minimisation rule

Collect only what is required to answer the formative usability questions. Do not collect patient
records, medication lists, diagnoses, images of clinical documents, national identifiers, dates of
birth, addresses, clinical credentials beyond the minimum needed to confirm an expert reviewer's
qualification, or unrelated demographic data.

## Data inventory

| Dataset | Direct identifiers | Purpose | Storage | Access |
|---|---|---|---|---|
| Recruitment contacts | Name and email | Scheduling only | Approved NUS workspace, separate from observations | Investigator only |
| Consent record | Name/signature or approved electronic evidence | Document consent | Approved restricted folder | Investigator and authorised ethics auditor |
| Screening record | Study ID, cohort, eligibility answers | Eligibility and sampling | Approved restricted folder | Investigator only |
| Session observations | Study ID, task outcomes, ratings, de-identified notes | Formative analysis | Approved NUS research storage | Study team |
| Recording, if separately approved | Voice/screen may be identifiable | Transcript accuracy | Encrypted approved storage | Named study team only |
| Linkage key | Contact record to study ID | Scheduling/withdrawal | Separate encrypted location | Investigator only |
| Aggregate report | Counts, medians, de-identified quotations | Dissemination | Repository/report | Public after review |

The CareAlign production service is not a research-data store. Do not paste research notes,
identifiers, or real health information into the application.

## Identifiers and pseudonymisation

Assign sequential IDs such as `UX-P-001` and `UX-H-001`. Keep the linkage key separate from consent
records and observations. Remove names, employers, specific workplaces, unusual job titles, and
other indirect identifiers from notes and quotations. Review every quotation for re-identification
risk before release.

## Collection and transfer

- Use institution-approved forms, conferencing, and storage after the responsible office confirms
  them.
- Disable cloud recording and automatic transcription by default.
- If recording is approved, obtain separate explicit consent and state the platform and transfer
  location in the participant information sheet.
- Do not transfer research files through personal email, public links, messaging apps, or this
  public GitHub repository.
- Do not export identifiable data to an LLM or third-party analytics service.

## Access and security

Apply least privilege and multifactor authentication. Maintain an access list with date granted,
date removed, and role. Encrypt data in transit and at rest using the approved institutional
service. Lock unattended devices and do not retain local downloads after transfer and verification.
Report suspected loss, accidental disclosure, or unauthorised access through the approved NUS
incident route and pause the study.

## Retention and destruction

The final retention period must be confirmed by the approving DERC/NUS-IRB and applicable NUS
policy before submission. Until confirmed, do not promise a specific number of years.

The approved protocol must state:

1. the retention period for consent and research records;
2. the event that starts the retention clock;
3. who authorises destruction;
4. secure deletion method for digital data and recordings; and
5. how deletion is documented.

Delete recruitment contacts after scheduling/withdrawal needs end, subject to the approved plan.
Delete recordings as soon as an approved transcript or coding check is complete. Destroy the
linkage key before publishing the final de-identified dataset unless the approved withdrawal period
requires it longer.

## Withdrawal and corrections

Before irreversible de-identification, use the linkage key to locate and remove a withdrawing
participant's observations where the approved consent permits. Document the request, action, date,
and any limit. Corrections to coded data must preserve an audit trail; never silently overwrite a
raw record.

## Publication and repository rule

Only aggregate tables, de-identified quotations, blank templates, and approved protocol materials
may enter the public repository. Do not commit completed screening forms, consent records, session
notes, recordings, linkage keys, reviewer licence numbers, signatures, personal emails, or raw
participant-level exports.

## Breach and protocol-deviation response

1. Stop collection and contain further access.
2. Preserve an incident record without copying exposed data into GitHub.
3. Notify the supervisor/PI and the required NUS privacy/ethics contact.
4. Follow institutional assessment and notification instructions.
5. Record corrective action and obtain approval before resuming.

This plan is an operational draft, not a claim of PDPA compliance. The final controller,
institutional systems, retention rule, and incident route require written confirmation.
