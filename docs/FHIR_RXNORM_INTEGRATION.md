# FHIR and RxNorm integration design

## RxNorm identity

The optional resolver calls the NLM RxNorm API `findRxcuiByString`, concept properties, and generic
product endpoints. NLM documents the API as a web service for the RxNorm dataset and lists
`/rxcui?name=...` for string lookup:
[NLM RxNorm API](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html).

Safety rules implemented in `backend/app/services/rxnorm.py`:

1. The curated map runs first because it explicitly distinguishes the salt/form demo cases.
2. RxNorm is disabled by default and is never required for the bundled demo.
3. Active-concept exact search (`search=0`, `allsrc=0`) runs first. Exactly one RxCUI is required.
4. When exact search fails, normalized search is used only to expose a
   `normalized_candidate_needs_review`; it never supplies `normalized_id`. NLM documents that
   normalized search can ignore punctuation, word order, suffixes, and salt/form words, so automatic
   acceptance would be unsafe for this use case.
5. Only complete ingredient/product TTYs (`IN`, `PIN`, `MIN`, `SCD`, `SBD`, `GPCK`, `BPCK`) are
   accepted. Component/group TTYs remain review because they can omit strength or dose form.
6. The generic-product endpoint is called only for documented product TTYs. It may map an SBD to one
   SCD or a BPCK to one GPCK while retaining the source RxCUI; zero/multiple/unsupported relationships
   fail closed.
7. Both source and canonical concepts must explicitly report `suppress=N`; obsolete, alien, and
   otherwise suppressed concepts fail closed even if an exact lookup returns them.
8. The result preserves source and canonical names, RxCUIs, TTYs, suppression flags, match strategy,
   lookup status, RxNorm dataset version, API version, and CareAlign terminology-policy version.
9. Successful and deterministic fail-closed resolutions use a bounded in-process LRU cache with a
   12-hour default TTL. Transient transport/provider failures are never cached. The version endpoint
   is cached only after a successful response.
10. Timeout, malformed response, ambiguous match, unsupported TTY, or missing relationship returns
   review—not a guess.
11. RxNorm identity is terminology normalization, not evidence that two clinical orders are
   therapeutically interchangeable.

`evaluation/rxnorm/cases-v1.json` is the versioned terminology contract. CI validates its structure
without network calls. A release candidate that enables RxNorm must separately run
`evaluation/evaluate_rxnorm.py --live --confirm-live`, retain the returned RxNorm dataset/API
versions, and inspect every failed or drifted case. Live terminology output is engineering evidence,
not an expert clinical equivalence label.

Relevant NLM endpoint specifications:

- `findRxcuiByString`: https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.findRxcuiByString.html
- `getGenericProduct`: https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getGenericProduct.html
- `getRxConceptProperties`: https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getRxConceptProperties.html
- `getRxNormVersion`: https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getRxNormVersion.html
- Terms of service and attribution: https://lhncbc.nlm.nih.gov/RxNav/TermsofService.html

RxNorm remains disabled by default until the identity policy and edge-case set receive the
independent clinical review defined in
[`research/clinical/EXPERT_REVIEW_PROTOCOL.md`](../research/clinical/EXPERT_REVIEW_PROTOCOL.md).

## Future FHIR import

FHIR import remains read-only and out of the hackathon runtime. The relevant resource is
`MedicationRequest`, which represents an order or request for medication and includes medication,
subject, authored date, dosage instruction and related provenance:
[HL7 FHIR R5 MedicationRequest](https://hl7.org/fhir/R5/medicationrequest.html).

| CareAlign field | Candidate FHIR source | Guardrail |
|---|---|---|
| document ID/date | Bundle entry ID, `authoredOn` | Preserve source and timezone; never invent chronology |
| medication | `medication` CodeableReference | Retain coding system, code, display and original text |
| action/status | `status`, `intent` plus source text | Do not translate status into patient advice |
| dose/frequency/timing | `dosageInstruction` | Unsupported structures remain source text and review |
| route | `dosageInstruction.route` | Normalize only known coding/text equivalence |
| evidence | original resource path and rendered text | Every displayed statement links back to its resource |

Production import would require OAuth authorization, explicit consent/notice, minimum scopes,
tenant isolation, audit logs, revocation, token security, provenance display, version handling, and a
clinical terminology service agreement.
