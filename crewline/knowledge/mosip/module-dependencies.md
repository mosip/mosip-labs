# Module dependencies (automation view)

- Every API module → `apitest-commons` (rebuild commons first after any change; a new `GlobalConstants` module constant needs a rebuild of all dependents).
- pre-registration → Keycloak, ID Schema, masterdata data, booking service: see pre-registration/.crewline/qa/dependencies.md.
- Other modules: Unknown until each module is profiled (one `.crewline/qa/` per module, added when that module joins).
