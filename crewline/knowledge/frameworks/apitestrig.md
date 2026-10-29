---
topic: framework/apitestrig
scope: framework
status: Verified unless marked
last_verified: 2026-10-27 @ pre-registration 1e7b6e0a48, mosip-functional-tests 7138e82b82 (both working trees had uncommitted coverage-tooling changes)
owner_or_reviewer: TBD (Phase 0 decision)
related_items: [pre-registration/.crewline/qa/profile.yaml, pre-registration/.crewline/qa/module-context.md]
---

# API TestRig: canonical testcase format profile (P0)

This is the evidence-backed profile required by Plan §24 and Blueprint §8 step 2. It **describes**
the existing format. It does not define a new one.

**Read these first. They are authoritative and more detailed than this file:**
- `Api_Automation/CLAUDE.md`: framework architecture, YAML structure, tokens, script classes, pitfalls.
- `<module>/api-test/src/main/resources/coverage/README.md` and `AGENTS.md`: matrix format, 31 gap types, row-authoring playbook.
- `mosip-functional-tests/docs/coverage-matrix/design-record.md`: locked decisions and gotchas.

## 1. Where a testcase lives

| Artifact | Location | Evidence |
|---|---|---|
| Case definitions | `<module>/api-test/src/main/resources/<moduleDir>/<Subject>/<Subject>.yml` | 43 YAML in `preReg/` |
| Request / response templates | same folder, `<Subject>.hbs`, `<Subject>Result.hbs` (Handlebars) | 92 `.hbs` in prereg |
| Wiring | `testNgXmlFiles/<module>Suite.xml`: one `<test>` = one YAML + one script class (+ `idKeyName`, `pathParams`) | `preregSuite.xml`: 41 `<test>` |
| Intent + traceability | `src/main/resources/coverage/<moduleDir>/<Subject>.md` (one per wired subject) + planned `<VERB>_<path>.md` | 58 matrix files |
| Subset selection | `testCasesToExecute` (comma-separated `uniqueIdentifier`s) in module properties | `CLAUDE.md` § Run a subset |
| Runtime skip | `src/main/resources/testCaseSkippedList.txt` | `CLAUDE.md` |

## 2. YAML structure (observed: 292 cases / 43 files in prereg)

```yaml
<RootKey>:                      # API group, e.g. CreatePrereg
   <CaseName>:                  # e.g. Prereg_CreatePrereg_All_Valid_Smoke_sid_pos
      endPoint: /preregistration/v1/applications/prereg    # full gateway path
      uniqueIdentifier: TC_Prereg_CreatePrereg_01          # stable identity
      description: Validate that ...
      role: batch               # batch | admin | noauth | ... -> KernelAuthentication.getTokenByRole
      restMethod: post          # documentation; the wired script class decides the real verb
      inputTemplate: preReg/createPrereg/createPrereg
      outputTemplate: preReg/createPrereg/createPreregResult
      input: '{ ... JSON with $TOKENS$ ... }'
      output: '{ ... expected values ... }'
```

| Field | Present in | Notes |
|---|---|---|
| endPoint, description, restMethod, inputTemplate, outputTemplate, input, output | 292/292 | required in practice |
| role | 291/292 | `batch` 270, `admin` 19, others 3 |
| uniqueIdentifier | 290/292 | the 2 without are in unwired YAML (baselined) |
| checkErrorsOnlyInResponse | 75 | passes when the response has no `errors`; **skips value comparison** |
| additionalDependencies | 10 | values are `uniqueIdentifier`s |
| templateFields | 8 | per-language iteration (multilang) |
| checkOnlyStatusCodeInResponse | 2 | status-code-only assertion |

## 3. Identity and naming (corrects the Plan's assumption)

- **Stable ID = `uniqueIdentifier`**, unique module-wide, compared case-insensitively. Enforced by CoverageCli (`duplicate-unique-identifier`, `case-without-unique-identifier`). Matrix rows use it verbatim as their ID.
- Pattern `TC_<module>_<Subject>_<NN>`. prereg uses `TC_prereg_` (260) and `TC_Prereg_` (30). 290/290 match `^TC_(?i:prereg)_[A-Za-z0-9]+_\d+$`.
- **Case names** always start with the module prefix (`Prereg_`, 292/292). Tokens with framework meaning:
  - `Smoke` (any case): selected when `testLevel=smoke` (`AdminTestUtil.java:3788-3790`, `key.toLowerCase().contains("smoke")`). 106 prereg cases.
  - `_sid` (any case): the response field named by the suite's `idKeyName` is stored for later cases (`AdminTestUtil.java:607` and about 15 other call sites). 158 cases.
  - `_reqsid`: request-side capture variant (`AdminTestUtil.java:1323`). Inferred purpose, not yet traced.
- **`_smoke_Pos` / `_Neg` is not a prereg convention.** `_Neg` appears in 24/292 names and `_pos` in 3. `_smoke_Pos` appears in idrepo examples (`AdminTestUtil.java:4752` comment). The Plan's §23.3 wording is therefore module-specific. The validator reads naming rules from a per-module profile.

## 4. Dependency tokens

- A `_sid` case stores `<case name without its first "_" segment>_<field>`. Example: `Prereg_CreatePrereg_All_Valid_Smoke_sid_pos` + idKeyName `preRegistrationId` → `$ID:CreatePrereg_All_Valid_Smoke_sid_pos_preRegistrationId$`.
- `idKeyName` may list several fields (`appointment_date,time_slot_from`).
- Some script classes store extra fields: prereg `CreatePreReg.java:157-158` and `UpdatePrereg.java:142-143` store `EMAIL` and `PHONE`, **only when the case name contains `_pos`** (`CreatePreReg.java:155`, `UpdatePrereg.java:141`; corrected 2026-10-29, earlier notes said `_sid`). Commons `AdminTestUtil.java:6063-6069` stores `UIN`/`EMAIL`/`PASSWORD` for identity flows.
- **The `_sid` check lives at the call sites, not in the store** (Verified, commons 1.5.0 sources: `AdminTestUtil.writeAutoGeneratedId(Response, idKeyName, testCaseName)` at 3587 has no `_sid` check). A module's own script class can store IDs for every case. inji-verify `SimplePostForAutoGenIdWithHeaders` does so for `requestId`/`transactionId`. Profiles express this with `capture_without_sid` and `extra_id_fields_gate`; `crewline discover` detects both from the module's sources.
- Other tokens (`$TIMESTAMP$`, `$1STLANG$`, `$IGNORE$`, `$REMOVE$`, `$SCHEMAVERSION$`, …): see `CLAUDE.md` § Dynamic substitution tokens.

## 5. What is already enforced deterministically (do not rebuild)

`CoverageCli check` (`io.mosip.testrig.apirig.coverage`, apitest-commons). CI fails the PR via `.github/workflows/coverage-matrix-check.yml`:
duplicate/missing `uniqueIdentifier`, `restMethod` vs script-class verb, unwired/empty YAML, orphan cases (case without a row),
rows without Steps/Expected/Story-key format, unresolvable `Test` refs, unmapped/unreachable controller endpoints, legacy-ID loss,
unsynced files and stale generated reports.
Baseline on 2026-10-27: **0 open gaps, 11 accepted by baseline; 41 wired subjects, 58 matrix files, 53 controller endpoints.**

## 6. Added by this assistant (`validators/crewline`)

| Validator | Covers | Why CoverageCli does not |
|---|---|---|
| `testcase` | case-name prefix, ID pattern, `$ID:` producer resolution, `additionalDependencies` resolution | it does not model the ID-capture chain |
| `expected-diff` | changed `output`/`outputTemplate`, `$IGNORE$`, relaxed check flags, removed cases, ID churn, result `.hbs`, skip list, role | it compares rows to YAML, not YAML to its own history |
| `secrets`, `dco` | secret patterns (redacted), Signed-off-by | out of its scope |
| `manifest` | workflow transitions, repair cap, approval records | orchestration, not coverage |

## 7. Open items (Unknown)

- Whether an unresolved `$ID:` token in `output` fails, passes or is compared literally (see known-issues).
- DCO enforcement on the MOSIP repos: 1 of the last 10 pre-registration commits has a sign-off that does not match the author email (GitHub noreply address). Confirm the policy.

## 8. Learned in PILOT-001 (Verified 2026-10-28)

- **Resolved commons version is what runs.** pre-registration fork pins apitest-commons 1.5.0-SNAPSHOT; `mosip/develop` pins
  **1.6.0**; the local mosip-functional-tests checkout is 1.8.0-SNAPSHOT. Read `~/.m2/.../apitest-commons-<v>-sources.jar` for the
  version the module resolves.
- **Runtime-generated templates.** `CreatePreReg` replaces the YAML input template with `AdminTestUtil.generateHbsForPrereg(false)`.
  In ≤1.6.0 that template sends the phone through `$PHONENUMBERFORIDENTITY$` and email through `$EMAILVALUE$`, so
  `CreatePreReg` generates both and caches them as `<case>_PHONE` / `_EMAIL`. **From 1.7.0 the phone slot is `{{phone}}`** (YAML
  literal) while the cache still holds the generated value. YAML input alone does not show what is sent.
- `checkErrorsOnlyInResponse: true` skips every value comparison: a case with it and a rich `output` asserts nothing but "no errors".
- `role: noauth` sends an **empty** `Authorization` cookie. Pre-reg answers HTTP 500 to it (MOSIP-45714); other modules use
  `invalidtoken` for KER-ATH-401.
- A `$ID:` consumer is SKIPPED (not failed) when its producer didn't run: always include producers in a targeted subset.
- Known-issue mechanism: `testCaseSkippedList.txt` lines `<JIRA key>------<testCaseName>` → skipped as "known issue" (KI).
- Local runs on this machine need `-Djdk.net.unixdomain.tmpdir=<dir outside the user Temp folder>` (Java 21 HttpClient loopback).
- Extent full report (`*full-report*.html`) is the reliable per-uniqueIdentifier result source; `testng-results.xml` marks
  out-of-scope cases as SKIP. Ignored cases are listed under "Passed".
- Upstream `mosip/develop` (b1691c23f4) pre-existing issues: `preReg/AuditLog/AuditLog.yml` contains a tab (unparseable, unwired);
  duplicate `TC_prereg_UploadDocument_01/_02` (GetAllDocForPrId vs uploadDocument); 43 failing cases on released (full suite).
