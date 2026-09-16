# Formative usability study protocol

**Protocol ID:** CA-UX-001  
**Version:** 0.1-draft  
**Date:** 2026-09-16  
**Status:** Recruitment prohibited until written ethics/privacy determination

## Objective

Determine whether intended users can use CareAlign’s synthetic workflow without mistaking a
potential difference, rule confidence, or user-recorded response for a treatment recommendation or
verified clinical resolution. This is formative usability research, not a clinical performance or
outcome study.

## Design and sample

Use two separate purposive cohorts:

- **Patient/caregiver-facing cohort:** target 8–12 adults across at least two iterative rounds.
- **Healthcare-professional cohort:** target 5–8 medication-reconciliation stakeholders, including
  at least one pharmacist and one prescribing professional.

These targets support discovery of usability problems; they are not powered for efficacy,
subgroup, or population estimates. Report recruitment and attrition exactly. Do not pool cohorts.

## Eligibility

Adults able to provide consent and use the supported interface language may participate. Seek a
range of digital confidence and, where feasible, older adults and assistive-technology users.
Exclude anyone unable to consent or anyone recruited because of a current medication emergency.
Never request diagnoses, medication lists, medical-record screenshots, or other health history.

## Materials

- Frozen CareAlign deployment and commit SHA.
- Two fixed fictional scenarios plus one no-conflict control.
- Participant information/consent script.
- Moderator guide and session log.
- Screen recording only if separately approved and consented.

## Fixed tasks

1. Load a fictional case and explain what the tool is and is not claiming.
2. Identify the two source records and the words supporting one flag.
3. Explain whether CareAlign selected the correct instruction.
4. Copy or state the clarification question and identify whom to ask.
5. Record a fictional care-team response and explain its verification status.
6. Complete or deliberately skip teach-back.
7. Clear all browser-session data.

The moderator must not coach during task scoring. Assistance is recorded and the task remains
assisted rather than successful-unassisted.

## Measures

Primary formative measures:

- unassisted completion per task;
- critical misunderstanding count;
- source-evidence identification accuracy;
- time on task and assistance count;
- 1–7 single-ease rating after each task;
- participant explanation of the next safe action;
- observed accessibility barrier and verbatim, de-identified feedback.

A **critical misunderstanding** occurs if the participant says or acts as though CareAlign chose the
correct medication instruction, verified a user-entered response, guaranteed there is no problem,
or should replace professional confirmation. The final formative round cannot pass with any
unresolved critical misunderstanding. This is a product release gate, not evidence of clinical
safety.

## Stop rules

Stop and debrief if a participant enters personal health information, attempts to use the fictional
result for real treatment, reports distress, reveals an urgent medication concern, cannot continue
consent, or encounters a privacy/security incident. Direct urgent health questions to appropriate
local clinical or emergency services; do not answer them through CareAlign.

## Analysis plan

Freeze the build, scenarios, and coding guide before each round. Report every attempted session,
including withdrawals and technical failures. Summarize counts and medians descriptively; do not
calculate or market clinical accuracy. Group findings by severity: critical safety issue, major task
failure, accessibility barrier, or minor friction. Link each design change to an issue ID and retest
critical/major issues in a later round.

## Version and deviation control

Any change to tasks, definitions, participants, data collection, or analysis requires a dated
amendment before subsequent sessions. Record unavoidable deviations in `SESSION_LOG.csv`; never
silently exclude a failed session.

