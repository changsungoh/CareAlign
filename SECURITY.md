# Security policy

CareAlign accepts synthetic demonstration data only. Do not report real patient information in a
security issue. Report vulnerabilities privately through GitHub Security Advisories.

The prototype is stateless: the API has no application database, raw document logging is disabled
by default, and user-entered clarifications remain in browser `sessionStorage`. Input length, per-IP
rate limits and a daily request ceiling constrain abuse. Provider failures, invalid schemas, unknown
units and unverified evidence fail to an uncertain state rather than a reassuring result.

This is not a HIPAA-compliant service and must not be used with protected health information.
