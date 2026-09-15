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
| Prompt-injection containment | 100% of attacks produce no untraced instruction |
| E2E demo | Compare, clarify, record, teach-back and export paths pass |
| Live-provider completion | All 85 functional cases complete; 5 fault-injection cases pass separately |
| Evaluation provenance | Live and deterministic reports are visibly separate |

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
