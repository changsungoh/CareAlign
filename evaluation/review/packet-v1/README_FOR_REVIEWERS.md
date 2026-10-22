# CareAlign independent review packet

**Protocol:** CA-CLIN-001 (first pass) | **Data:** fictional, synthetic text only | **Time:** about 2 hours

Thank you for reviewing. CareAlign is a research prototype that compares medication instructions
from different care records and prepares questions for a healthcare professional. You are asked to
judge the source text yourself. **Please do not look up the project's code, dataset or results while
reviewing** - your independence is what makes this review useful. You will not be shown any
CareAlign output in this pass.

## What you receive
- `conflict-review-sheet.csv`: 43 pairs of two dated, fictional records (an earlier and a later one).
- `extraction-review-sheet.csv`: 35 single fictional instructions.
- `REVIEWER_ATTESTATION.md`: independence and conflict-of-interest declaration. Please complete it.

All case IDs are random and the order is shuffled. All text is fictional; never enter real patient data.

## Sheet 1 - conflict review
Read both records and decide whether a pharmacist or prescriber would want the difference clarified.
Fill, for each row:
- `reference_outcome`: one of clarification_warranted, no_clarification_warranted, insufficient_information
- `reference_category`: one of dose, frequency, route, action, possible_omission, identity, other, none. Use `possible_omission` when a medicine in one
  record is simply absent from the other and you cannot tell whether that was intended. Use `none`
  when no clarification is warranted.
- `clinically_meaningful`: yes / no / uncertain
- `evidence_document_1`, `evidence_document_2`: the exact words that support your decision
- `confidence_1_to_5` and a short `rationale`

Do not infer an intention that the text does not state (for example, that an absent medicine was
stopped on purpose).

## Sheet 2 - instruction reading
For each instruction, record how *you* read it:
- `schedule_type`: one of fixed_daily, interval, prn, taper, non_daily, range, conditional, other
  (`fixed_daily` = a set number of doses each day; `interval` = every N hours; `prn` = as needed;
  `taper` = changing dose over time; `non_daily` = less often than daily; `range` = a dose or
  frequency range; `conditional` = depends on a condition; `other` = none of these or unclear)
- `dose_value` (number only) and `dose_unit`; leave blank when not stated or not a single value
- `times_per_day` or `interval_hours` (whichever the text gives; leave the other blank)
- `route` (oral, sublingual, topical, inhaled, intramuscular, intravenous, subcutaneous) or blank
- `action` (continue, start, stop, hold) or blank when not stated
- `safe_to_compare_as_fixed_daily`: yes / no / uncertain - could a software check safely compare
  this instruction with another by treating it as a fixed daily schedule?
- `confidence_1_to_5` and a short `rationale`

## Returning your work
Save your answers in the same CSV files (do not rename columns) and return them with the completed
attestation. Please do not discuss your answers with other reviewers before returning them.
