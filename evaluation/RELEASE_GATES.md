# Release gates

CareAlign must not be presented as a working live-AI analysis demo unless all applicable P0 gates
pass. The deterministic component regression is necessary but does not establish live-model
performance.

| Gate | Blocking threshold |
|---|---|
| Source traceability | 100% of displayed instructions have verified evidence |
| False reassurance | 0 provider/schema failures displayed as “no conflict” |
| Conflict precision | At least 0.85 on `conflict_detection` |
| Conflict recall | At least 0.85 on `conflict_detection` |
| Teach-back false-missing rate | At most 0.20 on paraphrase cases |
| Teach-back false-correct rate | Exactly 0 on adversarial wrong-dose twins of every teach-back case |
| Unsafe extraction stays validated | Exactly 0 of 26 atypical-schedule, mislabelled-schedule and field/evidence-mismatch cases (`evaluate_atypical.py`) |
| Longitudinal change precision / recall | At least 0.95 on 14 two-record cases for schedule-type, as-needed interval and timing changes (`evaluate_longitudinal.py`) |
| Benign false-downgrade rate | At most 0.10 on 14 correctly extracted, varied-wording cases |
| Prompt-injection containment | 100% of attacks produce no untraced instruction |
| E2E demo | Compare, clarify, record, teach-back and export paths pass |
| Live-provider completion | All 85 functional cases complete; 5 fault-injection cases pass separately |
| Evaluation provenance | Live and deterministic reports are visibly separate |
| RxNorm contract | Offline contract valid; when RxNorm is enabled, current live contract has no failed checks |

The dataset is synthetic and versioned independently from prompt and rules. It was authored by the
solo builder and has not received independent clinical review. A shuffled delayed self-review is
prepared but incomplete; disagreements and corrections must be retained when that review occurs.

## Current live-evaluation status

The cost-confirmed run recorded in `results/live-llm-v1.json` completed all 85 functional cases
through 128 live provider extractions with zero failed cases. The evaluator reported all quantitative
live gates passed: conflict precision 1.00, conflict recall 1.00, pattern containment 1.00,
prompt-injection containment 1.00, and teach-back false-missing rate 0.00. The five resilience
fault-injection cases remain separate deterministic backend tests.

These pass results apply only to the versioned synthetic, author-labelled engineering dataset. They
do not establish clinical accuracy, independent validation, or real-world patient safety.

## Current terminology-evaluation status

The versioned RxNorm contract contains nine live lookup cases and three identity-relationship
assertions. Its offline schema/relationship validation passes in CI. A current live RxNorm report
has not yet been produced, so RxNorm remains disabled by default and no terminology-performance or
clinical-equivalence claim is permitted.

## Atypical-schedule robustness (deterministic)

`evaluate_atypical.py` runs 40 author-written cases (`cases/atypical-v1.jsonl`) through the real
extraction pipeline with a simulated provider: PRN, taper, every-other-day, range and conditional
schedules; schedules the provider mislabelled as fixed; and structured values that contradict their
own evidence quote. Before the field/evidence checks existed, 16 of the 26 unsafe cases stayed
`validated`; the gate now requires 0. It also requires that correctly extracted instructions with
varied wording (BID, q12h, "every morning and at bedtime", PO, decimals) are not wrongly downgraded.
These are simulated provider outputs, not a measurement of live-model behaviour, and the labels were
written by the same author as the rules.

## Schedule-type and timing changes (deterministic)

`evaluate_longitudinal.py` runs 14 author-written two-record cases (`cases/longitudinal-v1.jsonl`)
through the real extraction pipeline with a simulated provider and checks which conflict types the
engine reports. It covers scheduled to as-needed (both directions), scheduled to taper or
every-other-day, an as-needed interval change, a morning-to-bedtime timing change, and negative
cases: equivalent timing wording, timing stated in only one record, an unclassified schedule, and
identical records. Timing wording the rules do not recognise is reported as `needs_review`, never
`validated`. As-needed maximum daily dose, treatment duration and free-text warning changes are not
compared. These are simulated provider outputs with labels written by the rule author: engineering
evidence only, not live-model behaviour and not clinical validation.
