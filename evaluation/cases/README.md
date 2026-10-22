# Synthetic evaluation cases

Every case must contain one primary `metric_group`:

- `conflict_detection`
- `pattern_containment`
- `teachback`
- `security`
- `resilience`

Cases use synthetic information only. They were authored by the solo builder and are neither
independently labeled nor clinically validated. A delayed shuffled self-review can reduce recall
bias but must never be described as independent review.

The 43 conflict-detection cases contain 15 frequency-difference cases, 14 possible-omission cases,
and 14 no-expected-conflict controls. There are no formulation-conversion cases in v1; that category
is intentionally outside the MVP's validated scope.

## Atypical-schedule cases (`atypical-v1.jsonl`)

Forty cases, separate from the 90-case v1 contract: `atypical_pattern` (8), `mislabelled_schedule`
(8), `field_mismatch` (10) and `benign_variation` (14). Each case carries the structured output a
provider might return and the statuses the pipeline may assign. Run
`uv run python evaluation/evaluate_atypical.py` (also executed by `pytest`).
