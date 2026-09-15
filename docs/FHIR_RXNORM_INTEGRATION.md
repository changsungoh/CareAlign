# FHIR and RxNorm integration design

## RxNorm identity

The optional resolver calls the NLM RxNorm API `findRxcuiByString`, concept properties, and generic
product endpoints. NLM documents the API as a web service for the RxNorm dataset and lists
`/rxcui?name=...` for string lookup:
[NLM RxNorm API](https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html).

Safety rules:

1. The curated map runs first because it explicitly distinguishes the salt/form demo cases.
2. RxNorm is disabled by default and is never required for the bundled demo.
3. Exactly one RxCUI must be returned; zero or multiple results are unresolved.
4. A generic product link may supply the comparison identity while the original RxCUI remains in
   provenance.
5. Timeout, malformed response, ambiguous match, or missing relationship returns review—not a guess.
6. RxNorm identity is terminology normalization, not evidence that two clinical orders are
   therapeutically interchangeable.

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
