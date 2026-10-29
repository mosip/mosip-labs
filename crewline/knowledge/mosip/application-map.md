---
topic: mosip/application-map
scope: global
status: Verified for listed rows (Api_Automation/CLAUDE.md service table); others Unknown
last_verified: 2026-10-27
---

# MOSIP / Inji automation map

| Repo dir | `-Dmodules=` | Package | Runner | Matrix | Module context |
|---|---|---|---|---|---|
| pre-registration | prereg | io.mosip.testrig.apirig.prereg | MosipTestRunner | ✅ complete (reference) | pre-registration/.crewline/ |
| keymanager | keymanager | io.mosip.testrig.apirig.keymanager | MosipTestRunner | next after prereg (design record) | — |
| resident-services | resident | io.mosip.testrig.apirig.resident | MosipTestRunner | has api-test/CLAUDE.md | — |
| esignet-signup | signup | io.mosip.testrig.apirig.signup | MosipTestRunner | has api-test/CLAUDE.md | — |
| admin-services | masterdata | io.mosip.testrig.apirig.masterdata | MosipTestRunner | Unknown | — |
| id-authentication | auth | io.mosip.testrig.apirig.auth | MosipTestRunner | Unknown | — |
| id-repository | idrepo | io.mosip.testrig.apirig.idrepo | MosipTestRunner | Unknown | — |
| partner-management-services | pmp | io.mosip.testrig.apirig.partner | MosipTestRunner | Unknown | — |
| esignet | esignet | io.mosip.testrig.apirig.esignet | MosipTestRunner | Unknown | — |
| inji-certify / inji-verify / mimoto | injicertify / injiverify / mimoto | io.inji.testrig.apirig.* | InjiTestRunner | Unknown | — |

Shared: `mosip-functional-tests/apitest-commons` (see knowledge/frameworks/apitest-commons.md).
UI: `UI_Automation/uitestrig-platform` (see knowledge/frameworks/uitestrig.md).
