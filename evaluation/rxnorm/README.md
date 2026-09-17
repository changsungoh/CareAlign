# RxNorm terminology contract

`cases-v1.json` is a versioned engineering contract for CareAlign's optional live RxNorm adapter.
It tests terminology behavior—not clinical equivalence—and is separate from the pending independent
expert reference set in `research/clinical/`.

Validate the contract structure without network access:

```bash
cd backend
uv run python ../evaluation/evaluate_rxnorm.py
```

Execute the live NLM contract manually:

```bash
cd backend
uv run python ../evaluation/evaluate_rxnorm.py \
  --live \
  --confirm-live \
  --output ../evaluation/results/rxnorm-live-v1.json
```

The live run is deliberately not a CI dependency because RxNorm releases and network availability
are external. Run it for a release candidate, retain the exact RxNorm dataset/API version, inspect
every drift failure, and update expectations only after terminology and clinical review. The runner
sends requests sequentially at no more than ten case starts per second; the application adds a
bounded 12-hour in-memory cache for repeated normalized queries.

A passing report establishes only that the current NLM service satisfies the declared engineering
identity invariants. It does not show that two medication orders are clinically interchangeable.
