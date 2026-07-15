# Server documentation

Guides that belong with the **Server** package (API, crawlers, DB, MCP).

| Document | Description |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Request flow, RAG pipeline, DB split (app vs LangChain), MCP |
| [ENVIRONMENT.md](./ENVIRONMENT.md) | Important env vars grouped by purpose |
| [DATABASE_SETUP.md](./DATABASE_SETUP.md) | What to configure in Postgres / `PG_CONNECTION` before first run |
| [DATABASE_LAYER.md](./DATABASE_LAYER.md) | Alembic, models, repositories, controllers |
| [ADDING_DATA_SOURCES.md](./ADDING_DATA_SOURCES.md) | How to add a new crawler → ingest → retrieve path |
| [MCP_SERVER.md](./MCP_SERVER.md) | FastMCP tools (`search_knowledge` + `product`), SSE/stdio, dual Claude Desktop |
| [DIRECT_BYOK.md](./DIRECT_BYOK.md) | White-label `generic` product + `answer_mode=direct` (no docs KB) |

Main entry: [../README.md](../README.md) · [Package map](../PACKAGE_MAP.md)  
Kubernetes: [../k8s/README.md](../k8s/README.md)  
Full-stack Rancher deploy (shared): [../../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md](../../docs/MOSIP_Nexus_Rancher_Deployment_Guide.md)
