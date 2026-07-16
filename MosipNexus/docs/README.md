# Documentation index

| Audience | Document | Location |
| --- | --- | --- |
| **Everyone** | [System architecture](./ARCHITECTURE.md) | End-to-end diagram |
| | [API reference](./API_REFERENCE.md) | HTTP + MCP map |
| | [Contributing / doc map](./CONTRIBUTING.md) | Conventions |
| **Server developers** | [Server/README.md](../Server/README.md) | Backend overview |
| | [Server architecture](../Server/docs/ARCHITECTURE.md) | RAG, DB, MCP detail |
| | [Environment variables](../Server/docs/ENVIRONMENT.md) | Env reference |
| | [Database setup](../Server/docs/DATABASE_SETUP.md) | Postgres / pgvector |
| | [Database layer](../Server/docs/DATABASE_LAYER.md) | Alembic / models |
| | [Adding a data source](../Server/docs/ADDING_DATA_SOURCES.md) | New crawlers |
| | [MCP Server](../Server/docs/MCP_SERVER.md) | Claude Desktop / tools |
| **UI developers** | [UI/README.md](../UI/README.md) | React overview |
| | [UI architecture](../UI/docs/ARCHITECTURE.md) | Components, branding |
| | [UI development](../UI/docs/DEVELOPMENT.md) | npm / Docker |
| **Ops / Rancher** | [Rancher Deployment Guide](./MOSIP_Nexus_Rancher_Deployment_Guide.md) | Full-stack K8s |
| **Onboarding** | [Developer Guide](./MOSIP_Nexus_Developer_Guide.docx) | Long-form (`generate_docs.py`) |
| **Stakeholders** | [Presentation](./MOSIP_Nexus_Presentation.pptx) | From `generate_docs.py` |

Regenerate DOCX/PPTX:

```powershell
cd docs
uv run --project ../Server python generate_docs.py
```
