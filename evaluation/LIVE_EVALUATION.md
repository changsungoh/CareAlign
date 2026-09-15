# Live LLM evaluation

The committed deterministic report is a component regression and makes no claim about LLM
performance. A live report does not exist until the command below completes with a real backend-only
provider key.

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
