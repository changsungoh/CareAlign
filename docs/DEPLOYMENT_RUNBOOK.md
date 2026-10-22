# Deployment runbook

## Backend on Render

1. Connect `changsungoh/CareAlign` and apply `render.yaml`.
2. Set `ALLOWED_ORIGINS` to the final HTTPS Vercel origin—no wildcard.
3. Production live extraction uses `DEBUG_LOG_RAW=false` and `DEMO_MODE=false`. Use Demo Mode only when the UI visibly labels it.
4. For live extraction, add `ANTHROPIC_API_KEY`, keep the tested snapshot model, set provider spending
   limits, and keep the key out of previews and frontend variables.
5. Keep `PROVIDER_FAILURE_THRESHOLD=3` and `PROVIDER_RECOVERY_SECONDS=30` unless a reviewed load test supports a change.
6. Verify `GET /api/health`, `GET /api/readiness`, and `GET /api/version` from an incognito session.
   Health proves the process is alive; only readiness proves live extraction is configured and its
   provider circuit is closed.

## Provider credential lifecycle

The API key is the single point of failure for live analysis. An expired or revoked key makes every
analysis fail with an "Analysis unavailable" response while `/api/health` keeps returning `200`.

- Create the key without an expiry date, or with a long one, and record any expiry in a calendar
  reminder at least two weeks ahead. Anthropic emails expiry notices, so keep that mailbox monitored.
- `GET /api/readiness` reports `provider_auth`: `unknown` (no live call yet), `ok`, or `failed` when
  the provider answered 401/403. A `failed` value also turns readiness into `503`. Point an external
  uptime monitor at `/api/readiness` (not `/api/health`) and alert on any non-200 response. Keep the
  Render health check on `/api/health` so a bad key does not cause restart loops.
- To rotate: create the new key in the provider console, replace `ANTHROPIC_API_KEY` in the Render
  environment (value only, no `ANTHROPIC_API_KEY=` prefix or quotes), deploy, run one live analysis,
  confirm `provider_auth` is `ok`, then delete the old key. Never paste a key into chat, issues or logs.
- Set a monthly spending limit in the provider console as a second line of defence behind
  `DAILY_REQUEST_LIMIT` and `PER_CLIENT_DAILY_LIMIT`.

## Request budgets and proxy configuration

`DAILY_REQUEST_LIMIT` is a global ceiling on live analyses. `PER_CLIENT_DAILY_LIMIT` stops one client
from consuming all of it, but a per-client cap is only fair when the client can be identified. It is
therefore applied only when `TRUSTED_PROXY_HOPS` is greater than `0`, or when the socket peer is a
public address. Behind Render, set `TRUSTED_PROXY_HOPS` to the verified number of proxies in front of
the API; until then every user shares the proxy address and only the global ceiling applies.

## Frontend on Vercel

1. Import the same repository with root directory `frontend`.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the Render HTTPS origin.
3. Deploy production and test the final production domain, not only a preview URL.
4. After testing, keep only the production origin in backend CORS.

## Verified production deployment

- Frontend: https://care-align-theta.vercel.app
- Backend: https://carealign-api.onrender.com
- Verified 15 September 2026: health, version metadata, frontend, medical disclaimer, and synthetic-only notice passed `scripts/preflight.py`.
- Verified manually: live two-document analysis, frequency difference, possible omission, source spans, teach-back, browser-session resolution persistence, copy, print, download, and clear-session behavior.

## Release smoke test

- Run `python scripts/release_manifest.py --verify`; regenerate with `--write` only when the
  safety-critical change is intentional and reviewed.
- Open the production UI in a clean browser.
- Confirm all three safety notices are visible before analysis.
- Run the bundled two-document synthetic case.
- Confirm one frequency flag and one possible-omission flag with source spans.
- Copy, print and download the clarification questions.
- Record a response, reload in the same tab, and verify session behavior.
- Run teach-back only on the non-conflicted lisinopril instruction.
- Trigger invalid chronology and provider failure; neither may show “no conflict.”
- Confirm the result footer shows request ID, release revision, provider calls, tokens and duration.
- Confirm the response `X-Request-ID` matches the result metadata and appears in the corresponding
  structured backend log event.
- Close the tab and verify no case can be retrieved from the backend.

## Rollback

If any P0 gate fails, keep the last known good commit deployed or disable live analysis and show an
honest unavailable state. Demo Mode may be used only with its visible badge and known synthetic data.
Never silently substitute cached results for arbitrary user input.

The configured model and structured-output API shape should be rechecked against the current
[Claude model documentation](https://platform.claude.com/docs/en/models/overview) and
[structured-output documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
before the live smoke test.
