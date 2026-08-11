# AGENTS.md

Guidance for the `ussd-proxy-service` project inside the `mosip-labs`
monorepo. See [`../AGENTS.md`](../AGENTS.md) for repo-wide conventions
(branching, CI overview, PR scoping) — this file covers only what's specific
to this project.

## Repository Overview

`ussd-proxy-service` is a bridge between a USSD (Unstructured Supplementary
Service Data) gateway and MOSIP Resident Services, so that people on basic
phones — no smartphone or internet needed — can check RID/UIN status, view
auth history, lock/unlock their UIN, and manage credentials over a USSD
menu. The current implementation targets Africa's Talking as the USSD
aggregator (tested against their sandbox and phone simulator), with an
Emnify integration also present in the code (`org.mosip.ussd.emnify`
package) for SMS/USSD push via a different provider.

Menu flow is driven by a small state-machine engine defined in this
project (`org.mosip.ussd.sm`), not a general-purpose library — states,
transitions, and handlers are all wired through
`src/main/resources/statemachine/sm.json` and per-language menu files.

## Technology Stack

- **Language**: Java 8 (`java.version=1.8` in `pom.xml`).
- **Framework**: Spring Boot 2.3.12.RELEASE (`spring-boot-starter-web`,
  `spring-boot-starter-data-jpa`, `spring-boot-starter-batch`).
- **Database**: H2, both file-backed (`spring.datasource.url=jdbc:h2:file:./USSDDataBase`)
  by default in `application.properties`.
- **API docs**: springdoc-openapi-ui (Swagger).
- **HTTP clients**: Retrofit2, Apache HttpClient, OkHttp logging
  interceptor — used to call MOSIP Resident/IDA APIs and the
  Emnify/Africa's Talking gateways.
- **Build**: Maven (`pom.xml`, no Maven wrapper checked in — a local `mvn`
  install is required).

## Build & Test Commands

There is no test source directory in this project and no test dependency
declared in `pom.xml` — there is nothing for `mvn test` to run. Verify
behavior changes manually (run the service, exercise it with the `curl`
commands in `run.sh` / the Swagger UI).

```bash
mvn clean install          # from ussd-proxy-service/, builds the jar
mvn spring-boot:run          # runs the app directly (reads application.properties)
```

Docker build (from `ussd-proxy-service/deploy/`, matching
`deploy/build-docker.sh`):

```bash
cp ../target/*.jar .
docker build -t mosip.io/ussdproxy .
```

The `deploy/Dockerfile` copies the fat jar in and runs it directly:

```dockerfile
ENTRYPOINT ["java","-jar","/app.jar"]
```

If you ever need to add a JVM system property to that entrypoint, `-D`
flags must come **before** `-jar`, e.g. `java -Dspring.profiles.active=prod
-jar /app.jar` — not after.

`run.sh` (both the one at the project root and `deploy/run.sh`) isn't a
startup script — it's a pair of `curl` calls against an already-running
instance that register the USSD setup and a test partner:

```bash
# Local-only smoke test — do not run against a shared/production endpoint.
curl -X POST "http://localhost/AT/ussd/setup" -H "accept: */*"
PARTNER_KEY="${PARTNER_KEY:?Set PARTNER_KEY for this test}"
curl -X POST "http://localhost/ussd/partner/" -H "accept: */*" \
  -H "Content-Type: application/json" \
  -d "{\"partnerId\":\"1000\",\"partnerUrl\":\"http://localhost:8080/credentials/\",\"partnerKey\":\"${PARTNER_KEY}\"}"
```

## Configuration

`src/main/resources/application.properties` holds all runtime
configuration: server port (`server.port=80`), Emnify callback/API
settings, the MOSIP `mosip.appId` / `mosip.clientId` / `mosip.clientSecret`
/ `mosip.baseUrl` used to call MOSIP APIs, and the H2 datasource.

**This file, as checked into the repo, already contains non-placeholder-
looking values** — a live-looking `emnify.apikey` JWT and a
`mosip.clientSecret` — not just example/blank placeholders. Treat both as
compromised, since this is a public repo: they should be revoked/rotated
by whoever owns them, and removed from the tracked file (and ideally from
git history) rather than left in place. This is a known issue in this
project, not a pattern to follow: do not add further real credentials to
`application.properties`, and if you're setting up your own environment,
override these via Spring's usual mechanisms (environment variables,
`-D` system properties before `-jar`, or a profile-specific properties
file) rather than editing the committed values in place.

There is no separate `.env.example` or secrets-management convention in
this project — it's all in the one properties file.

## Project Structure Notes

```text
ussd-proxy-service/
├── pom.xml
├── run.sh                        # curl smoke-test commands, not a launcher
├── deploy/
│   ├── Dockerfile                  # java -jar entrypoint, EXPOSE 80
│   ├── build-docker.sh              # copies target/*.jar in, then docker build
│   ├── run-docker.sh                 # same curl smoke tests as run.sh
│   └── run.sh
└── src/main/
    ├── java/org/mosip/ussd/
    │   ├── IdServiceProvider/          # Calls to Resident APIs (IDSAPI) and Mimoto (IDCredsAPI)
    │   ├── controller/                  # USSDController, PartnerController, EMnifyController
    │   ├── dialog/                       # UssdMenu, UssdDialogEmnify — menu rendering
    │   ├── emnify/                        # Emnify gateway integration
    │   ├── sm/                             # State-machine engine: SMProcessor, SMAction, actions/*
    │   ├── service/                         # ResidentService, CredentialService, SessionService, etc.
    │   ├── storage/                          # Spring Data JPA repositories (H2-backed)
    │   └── entity/, model/                    # JPA entities and DTOs
    └── resources/
        ├── application.properties
        ├── en/menu.json, hi/menu.json          # Per-language USSD menu text
        └── statemachine/sm.json                 # State machine definition (states, transitions, handlers)
```

To change USSD menu text, edit the relevant `resources/<lang>/menu.json`
(currently English and Hindi are present, despite the README describing a
French example — verify the actual language directories in
`src/main/resources/` before assuming one exists). To change the flow
itself (what happens after which input), edit `resources/statemachine/sm.json`
and, if a new state needs custom logic, add a handler class under
`sm/actions/` and wire it in per the existing handlers' pattern.

## Development Workflow

1. Set real values for `mosip.baseUrl`, `mosip.clientId`,
   `mosip.clientSecret`, and the Emnify/Africa's Talking settings for your
   target environment — don't rely on the values already committed in
   `application.properties`, which point at specific dev/sandbox instances
   and a real-looking secret.
2. `mvn clean install` to build; `mvn spring-boot:run` (or run the built
   jar) to start the service on port 80. `spring.datasource.url=jdbc:h2:file:./USSDDataBase`
   is relative to the JVM's **current working directory**, not the jar's
   location — running `java -jar target/*.jar` from the repo root creates
   `./USSDDataBase` there, not inside `target/`.
3. Use the `curl` calls in `run.sh` to register the USSD setup and a test
   partner before exercising the USSD flow end to end.
4. There's no automated test suite — validate state-machine or handler
   changes by walking the actual USSD menu (simulator or gateway sandbox)
   through the affected path.

## Pull Request Guidelines

- Target `develop` (see repo-wide [`../AGENTS.md`](../AGENTS.md)).
- This project has no CI wiring in `.github/workflows/` — no automated
  build or Docker publish runs against it in this repo, so a passing local
  `mvn clean install` is the only pre-merge signal; call out in the PR
  description that you built and manually verified the change.
- Do not add real credentials to `application.properties` as part of a PR,
  even to "fix" the ones already there — flag it as a follow-up rather than
  mixing a secrets-handling change into a functional one.

## Repository-Specific Considerations

- The project's Spring Boot version (2.3.12.RELEASE, from 2020) and Java
  version (8) are noticeably older than other MOSIP services. Match the
  existing style rather than upgrading dependencies or the Java version as
  a side effect of an unrelated change.
- Several dependencies in `pom.xml` are commented out (`db-util`, an
  `emnify` SDK, Spring Data Redis/Jedis, Apache Derby) — these read as
  abandoned experiments, not currently-wired functionality. Don't assume
  code referencing them (if any) is live.
- `emnify.callbackbase` in `application.properties` points at an ngrok
  tunnel URL — this is a dev-only value that will not resolve in any other
  environment; it must be overridden per deployment, not treated as a
  working default.

## Agent rules

### Do

1. Override `application.properties` values (MOSIP client credentials,
   Emnify settings, callback URLs) per environment instead of relying on
   the values already committed there.
2. Put `-D` JVM system properties before `-jar` in any `java` command you
   write or document.
3. Add new USSD flow logic through the existing `sm/actions/` handler
   pattern and register it in `statemachine/sm.json`.
4. Verify changes manually (build + run + exercise the affected USSD path)
   since there is no automated test suite here.

### Do not

1. Do not commit new real credentials or tokens into
   `application.properties`.
2. Do not upgrade the Java version or Spring Boot version as a side effect
   of a functional change — treat that as a separate, deliberate decision.
3. Do not assume commented-out dependencies (Redis/Jedis, the Emnify SDK,
   Derby, `db-util`) are active — verify before building on them.
4. Do not assume this project has CI, a Helm chart, or a test suite in this
   repo — it has none of the three.
