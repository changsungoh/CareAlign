# Live LLM evaluation

The committed deterministic report is a component regression and makes no claim about LLM
performance. A separate cost-confirmed live report was produced with a real backend-only provider
key and is published as [`results/live-llm-v1.json`](results/live-llm-v1.json).

## Published run

On 15 September 2026, `claude-haiku-4-5-20251001` completed all 85 functional cases through 128
provider extractions with no failed cases. The run used 103,389 input and 13,479 output tokens. At
the explicitly supplied rates of $1 and $5 per million input/output tokens, respectively, estimated
cost was $0.170784 ($0.002009 per completed case). All configured quantitative live release gates
passed. The report remains a synthetic author-labelled engineering evaluation, not independent
review or clinical validation.

The 90-case manifest contains 85 functional cases and 5 resilience fault-injection cases. A full
live run performs 128 provider extractions: 86 across 43 two-document conflict cases, plus 5 complex
pattern, 15 adversarial, and 22 teach-back source extractions. The five resilience cases are exercised
separately by backend tests because a real provider outage cannot be ethically or reproducibly
scheduled.

1. Verify current provider pricing from the provider's official documentation.
2. Set `ANTHROPIC_API_KEY` only in the backend environment.
3. Set a provider-console spending ceiling.
4. Run:

```bash
cd backend
uv run python ../evaluation/evaluate_live.py \
  --confirm-cost \
  --input-cost-per-million-usd CURRENT_INPUT_RATE \
  --output-cost-per-million-usd CURRENT_OUTPUT_RATE
```

The script writes `evaluation/results/live-llm-v1.json`, including the exact model, versions,
timestamp, provider call count, token usage, supplied pricing, estimated total/average cost, failed
case IDs, and live metrics. Commit that file without editing its numbers. An incomplete run remains
an incomplete run; do not calculate metrics only over successful cases or overwrite it with the
deterministic report.

## Atypical-schedule live evaluation

`evaluate_atypical_live.py` sends the 35 distinct instruction texts of `cases/atypical-v1.jsonl`
through the live provider. The simulated suite (`evaluate_atypical.py`) proves that the safety net
catches a *wrong* provider output; this run measures the real model: does it label PRN, taper,
non-daily, range and conditional wording correctly on its own, how often is the field/evidence check
the only thing that stopped an unsafe reading, and how often are plainly worded, correct
instructions wrongly downgraded?

Gates, declared before any live run: no instruction from an atypical text may end `validated`; at
most 10% of plain texts may be downgraded; every case must complete. At roughly 35 short calls the
expected cost is a few cents at the rates used for the published run.

```bash
cd backend
ANTHROPIC_API_KEY=... uv run python ../evaluation/evaluate_atypical_live.py \
  --confirm-cost \
  --input-cost-per-million-usd CURRENT_INPUT_RATE \
  --output-cost-per-million-usd CURRENT_OUTPUT_RATE
```

The script refuses to run without `--confirm-cost` and a key, writes
`results/atypical-live-v1.json`, and keeps provider failures in the report instead of dropping them.
Commit the file without editing its numbers. Errors injected on purpose (a wrong dose from the
provider) cannot be reproduced against a real model and stay in the simulated suite. Labels are the
author's; independent labels come from the reviewer packet below.
