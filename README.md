# MOSIP Labs

A collection of experimental and innovative projects built on top of the MOSIP (Modular Open Source Identity Platform) framework to extend and enhance identity management capabilities.

## Overview

MOSIP Labs is a repository maintained by the MOSIP organization that contains laboratory projects, proof-of-concepts, and experimental services designed to showcase MOSIP's extensibility and integration capabilities. These projects demonstrate how MOSIP can be integrated with various external services and systems to create comprehensive identity solutions.

## Projects

### 1. USSD Proxy Service

A bridge service that connects USSD (Unstructured Supplementary Service Data) gateways with MOSIP Resident Services, enabling mobile users to access identity services through basic telephony interfaces.

### 2. Self-Service UIN Deletion

Lets a MOSIP Collab resident delete their UIN and all linked personal data themselves: "Delete my UIN" on the Collab landing page, sign-in and consent through eSignet, then deletion across Registration Processor, ID Repository, ID Authentication, Resident Portal and the eSignet login, with retry and a hash-only audit trail. Includes a local environment that runs end to end with a mock eSignet. Contributed by Team Matrix (DMP project).

See [self-service-uin-deletion/README.md](self-service-uin-deletion/README.md), and [HANDOVER.md](self-service-uin-deletion/HANDOVER.md) for production readiness.
