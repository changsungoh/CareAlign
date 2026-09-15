# Evaluation result provenance

- `demo-parser-v1.json` is a deterministic component regression. It makes zero LLM calls and does
  not measure live-model performance.
- `live-llm-v1.json` does not exist until an explicitly cost-confirmed live run completes. If
  generated, it must retain failures, token usage, pricing inputs, and exact model/version metadata.
- Neither report is independent review, clinical validation, or evidence of real-world safety.

Do not overwrite one report with the other or present deterministic perfect scores as AI accuracy.
