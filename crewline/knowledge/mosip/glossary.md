# Glossary

| Term | Meaning |
|---|---|
| Subject | One wired YAML = one `<test>` in the Suite.xml = one matrix file |
| Unit | One endpoint (method + full gateway path) a subject calls; a subject may have several |
| Planned file | `<VERB>_<path>.md` matrix file for a real endpoint with no YAML yet |
| `uniqueIdentifier` | Stable, module-wide unique case ID; also the matrix row ID for automated rows |
| `_sid` case | Case whose response field(s) are stored for later `$ID:` references |
| `$ID:<key>$` | Reference to a stored value; key = case name minus first segment + `_` + field |
| `idKeyName` | Suite parameter naming which response field(s) a `_sid` case stores |
| Smoke | Cases whose name contains `smoke`, selected by `-Denv.testLevel=smoke` |
| Core 8 | Matrix categories: positive, authn, authz, validation, not_found, boundary, idempotency, data_isolation |
| Cycle 2 | Mandatory semantic self-audit of matrix rows against YAML **and** service source (`coverage/AGENTS.md`) |
| Gate | Recorded check in the task manifest: PASS / FAIL / BLOCKED / NOT_RUN / NOT_APPLICABLE |
| Failure fingerprint | `<uniqueIdentifier>|<assertion or error code>|<HTTP status>`; the repair cap counts per fingerprint |
