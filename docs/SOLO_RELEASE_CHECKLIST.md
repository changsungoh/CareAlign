# Solo release checklist

## Code freeze

- [ ] `main` CI is green at the exact release commit.
- [ ] The worktree is clean and the release commit is tagged.
- [ ] No secret, PHI, real prescription, or identifying information exists in code or fixtures.
- [ ] Prompt, rules, dataset, app, and provider model versions match the public report.

## Deployment

- [ ] Render health/version endpoints are public over HTTPS.
- [ ] Vercel production frontend points to the production API.
- [ ] CORS contains only the production frontend origin.
- [ ] Provider key exists only in backend secrets and has a spending ceiling.
- [ ] Demo Mode is visibly labelled; live failure never silently switches modes.
- [ ] `scripts/preflight.py` passes against both production URLs.

## Evaluation

- [ ] Freeze automated predictions before the second-pass review.
- [ ] Run `python evaluation/blind_review.py prepare` and wait before reviewing.
- [ ] Complete the shuffled label CSV without opening original labels.
- [ ] Run `python evaluation/blind_review.py score` and disclose disagreements.
- [ ] Describe all results as synthetic engineering evaluation, not clinical performance.
- [ ] Validate the offline RxNorm contract; if RxNorm will be enabled, run and inspect the current
      live contract and record the exact NLM dataset/API versions.

## Submission

- [ ] Record the exact production commit using `docs/DEMO_SCRIPT.md`.
- [ ] Verify the video, app and GitHub links in an incognito browser.
- [ ] Paste and proofread `docs/DEVPOST_SUBMISSION.md`.
- [ ] Confirm solo-builder attribution and AI-use disclosure.
- [ ] Include the safety limitation above the fold.
- [ ] Submit before the deadline and retain confirmation evidence.
