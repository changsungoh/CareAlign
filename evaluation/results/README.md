# Evaluation result provenance

- `demo-parser-v1.json` is a deterministic component regression. It makes zero LLM calls and does
  not measure live-model performance.
- `live-llm-v1.json` is the explicitly cost-confirmed live run completed on 15 September 2026.
  It retains failed-case accounting, token usage, supplied pricing, exact model/version metadata,
  and all calculated metrics without manual editing.
- Neither report is independent review, clinical validation, or evidence of real-world safety.

Do not overwrite one report with the other or present deterministic perfect scores as AI accuracy.
