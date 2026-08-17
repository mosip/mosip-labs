/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NEXUS_API_URL?: string
  readonly VITE_DEV_API_PROXY?: string
  readonly VITE_MCP_SSE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
