# Ethics determination request draft

**Study ID:** CA-UX-001
**Version:** 0.1-draft
**Date:** 2026-09-16
**Applicant:** OH CHANGSUNG, student researcher
**Status:** Not submitted; no recruitment or data collection is authorised

> Complete every bracketed field, obtain the required supervisor role, and use the route confirmed by
> the relevant NUS Departmental Ethics Review Committee (DERC) or NUS-IRB. This repository draft is
> not an approval, exemption, or Review Not Required determination.

## Administrative fields to complete

- NUS school/department and programme: **[TO COMPLETE]**
- Student number: **[TO COMPLETE — do not commit to this public repository]**
- NUS email and phone: **[TO COMPLETE — do not commit personal contact details publicly]**
- Supervisor/Principal Investigator: **[TO COMPLETE]**
- Departmental ethics contact or DERC: **[TO CONFIRM]**
- Proposed study dates: **[TO COMPLETE after determination]**
- Funding, incentives, and conflicts: **None currently; update before submission**
- CITI Social & Behavioral Research certificate: **[TO COMPLETE]**

## Requested determination

Please determine the appropriate review route for a minimal-risk, formative usability study of
CareAlign, a research prototype that compares fictional medication-instruction records. The study
uses only fixed synthetic scenarios. It does not request, collect, or analyse participants' health
records, diagnoses, medication lists, treatment decisions, or biological material.

The project is expected to fall within Social, Behavioural and Educational Research (SBER), not
Human Biomedical Research (HBR), because the research question concerns interface comprehension
and safe interpretation rather than health outcomes or biomedical intervention. This is an
applicant assessment only; NUS/DERC makes the determination.

## Purpose and research questions

The purpose is to identify usability failures that could cause a user to misunderstand the
prototype as making a treatment recommendation or verifying a clinical resolution.

1. Can intended users explain that CareAlign flags source-linked differences but does not choose
   the correct instruction?
2. Can users locate the original evidence and identify the next safe action?
3. Do users understand that a response saved in the browser is user-entered and unverified?
4. What accessibility or workflow barriers prevent safe completion of the synthetic tasks?

No clinical accuracy, treatment outcome, diagnosis, efficacy, or population-level claim will be
estimated.

## Participants and recruitment

- 8–12 adult patient/caregiver-perspective participants across iterative rounds.
- 5–8 adult healthcare professionals involved in medication reconciliation, including at least one
  pharmacist and one prescribing professional where feasible.
- Adults able to consent and use the supported interface language.
- No recruitment based on a diagnosis, medication, hospitalisation, or current care need.
- No patients under the direct clinical authority of an investigator or reviewer.
- Recruitment materials will explicitly prohibit entry of real patient data.

Potential participants will see the approved recruitment notice and complete a minimal screening
form. A study team member will confirm eligibility without requesting health information. Any
payment or reimbursement will be inserted into the participant information sheet and approved
before recruitment.

## Procedures

Each remote or in-person session will last approximately 30–45 minutes:

1. review the participant information and document consent;
2. confirm that only fictional text may be entered;
3. complete seven fixed tasks using the frozen CareAlign build and synthetic scenarios;
4. provide task-ease ratings and de-identified feedback;
5. receive a debrief and reminder that the prototype is not medical advice; and
6. clear browser-session data.

The moderator will not solicit medical history, answer treatment questions, or coach during scored
tasks. Screen/audio recording is disabled unless separately approved and separately consented.

## Data collected

- study ID and cohort, not participant name, in the analysis dataset;
- eligibility and consent status;
- task completion, time, assistance count, and ease rating;
- observed misunderstandings and accessibility barriers;
- de-identified notes and short quotations; and
- protocol deviations and technical failures.

Recruitment contact information, signed/electronic consent evidence, and study observations will be
stored separately. The production application will not receive or store research data. No real
patient data is permitted.

## Risks and mitigations

The anticipated risk is no greater than ordinary interaction with a web prototype, but foreseeable
risks include accidental disclosure of health information, confusion that the tool gives medical
advice, discomfort discussing medication-transition errors, loss of confidentiality, and power
imbalance in student recruitment.

Controls include synthetic-only scenarios, repeated safety notices, immediate stopping if personal
health data is entered, separate identity keys, least-privilege storage, no recruitment through a
clinical care relationship, voluntary participation, withdrawal without penalty, and a moderator
script for redirecting urgent concerns to appropriate local clinical or emergency services.

## Consent and withdrawal

Consent will be obtained before any study task. Participation is voluntary. A participant may skip
questions or stop at any time without giving a reason. Withdrawal handling and the last date at
which identifiable data can be removed will be stated in the approved participant information
sheet. After irreversible de-identification or aggregation, it may no longer be possible to remove
an individual's contribution; this limit will be explained before consent.

## Analysis and dissemination

Results will be descriptive and formative: counts, medians, task failures, critical
misunderstandings, accessibility barriers, and de-identified quotations. All attempted sessions,
withdrawals, technical failures, and deviations will be reported. Outputs may appear in a student
project report, presentation, GitHub repository, or publication only in aggregated or de-identified
form and only within the approved determination.

## Attached study documents

- [`../usability/PROTOCOL.md`](../usability/PROTOCOL.md)
- [`../usability/CONSENT_AND_MODERATOR_GUIDE.md`](../usability/CONSENT_AND_MODERATOR_GUIDE.md)
- [`PARTICIPANT_INFORMATION_AND_CONSENT.md`](PARTICIPANT_INFORMATION_AND_CONSENT.md)
- [`DATA_MANAGEMENT_PLAN.md`](DATA_MANAGEMENT_PLAN.md)
- [`../recruitment/USER_RECRUITMENT_NOTICE.md`](../recruitment/USER_RECRUITMENT_NOTICE.md)
- [`../recruitment/SCREENING_FORM.md`](../recruitment/SCREENING_FORM.md)
- fixed scenarios, session log, and analysis template in `research/usability/`

## Submission route verified on 2026-09-16

NUS states that human research requires ethics review before it starts, defines research as a
systematic investigation intended to contribute to generalisable knowledge, and directs NUS
students to their DERC where one exists. DERC may refer the application to NUS-IRB. NUS-IRB
applications are submitted through iRIMS-IRB. From 1 March 2026, NUS staff and students submitting
SBER to IRB or DERC must include the CITI Social & Behavioral Research Basic/Refresher completion
report.

The applicant must confirm the exact departmental route because NUS publishes different DERC
contacts by school. If the project is within the School of Computing, the current NUS DERC directory
lists Ms Iris Chang as the contact. If the applicant's affiliation is different, use that unit's
published DERC contact. Questions may be sent to `irb@nus.edu.sg`.

## Official references

- [NUS-IRB FAQ](https://nus.edu.sg/research/irb/resources/faq)
- [NUS DERC directory and student-research guidance](https://www.nus.edu.sg/research/irb/derc)
- [NUS-IRB training requirements](https://www.nus.edu.sg/research/irb/resources/training)
- [NUS iRIMS](https://www.nus.edu.sg/research/research-administration-and-shared-services/irims)
