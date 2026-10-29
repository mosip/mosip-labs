# Escalation — {{task_id}} / {{uniqueIdentifier}}

**Reason:** repair cap reached (3/3) | likely application defect | security | unsafe/weakening fix only | ambiguous expected behaviour | missing authority
**Recommended owner:** {{service team / SDET lead / PO / environment owner}}
**Failure fingerprint:** `{{uniqueIdentifier}}|{{assertion or error code}}|{{HTTP status}}`
**Classification:** {{class}}. Confidence: Verified | Inferred. {{why}}

## Evidence (redacted)
- Request: {{method path, body excerpt without tokens or PII}}
- Expected (source): {{value}}, from {{matrix row / OpenAPI / Class.method}}
- Actual: {{status + body excerpt}}
- Environment: {{env, build versions, timestamp}}
- Report/log paths: {{…}}

## Hypotheses tested
| # | Hypothesis | Change (files) | Validators | Outcome |
|---|---|---|---|---|

## What was deliberately not done
- No assertion weakened, no expected result changed, no case skipped.

## Decision needed
{{the specific question for the human}}
