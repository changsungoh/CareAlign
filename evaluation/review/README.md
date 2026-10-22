# Review status

Status: **prepared, not completed**.

`blinded-v1.jsonl` and the blank `labels-v1.csv` were generated from the frozen synthetic dataset.
No second-pass labels or disagreements have been recorded. Because the same solo builder authored
and will review the cases, this process cannot provide independent or clinical validation.

After a meaningful delay, complete the CSV without opening the source labels, run
`python evaluation/blind_review.py score`, and publish the resulting disagreement report without
silently changing the first-pass labels.

## Independent reviewer packet (`packet-v1/`)

`python evaluation/reviewer_packet.py prepare` builds the blinded first-pass packet for the
independent pharmacist/clinician review defined in `research/clinical/EXPERT_REVIEW_PROTOCOL.md`:

- `conflict-review-sheet.csv`: the 43 conflict-detection cases as shuffled, randomly numbered
  record pairs;
- `extraction-review-sheet.csv`: the 35 distinct atypical/plain instruction texts, to be read
  independently (schedule type, dose, frequency, route, action);
- `README_FOR_REVIEWERS.md` and the independence attestation.

Reviewers receive only these files. They never see CareAlign output, the author's labels, or the
dataset. `packet-v1-key.json` maps the random IDs back to the source cases and holds the author's
labels; keep it from reviewers. (The underlying labels are also in the public dataset, so reviewers
must be asked not to look them up.)

When a reviewer returns the sheets:

```bash
python evaluation/reviewer_packet.py score --reviewer R1 \
  --conflicts returned-conflicts.csv --extraction returned-extraction.csv
```

This writes `results/summary-R1.json` (agreement and Cohen's kappa) and
`results/disagreements-R1.csv`. Neither the reviewer's file nor the author's labels are altered;
disagreements go to adjudication under the protocol. Until a qualified reviewer who did not author
the cases completes the packet, no label in this repository is independently reviewed.
