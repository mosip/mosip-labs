/**
 * @file BYOK settings page.
 * Lets the user pick LLM provider, API key, model, and max history turns.
 * Values are owned by `App` and persisted to localStorage — never stored on the Server by the UI.
 */
import { Link } from 'react-router-dom'
import { asProductMode, PROVIDER_META, PROVIDER_MODELS } from '../lib/settings'
import type { LlmProvider, ProductConfig, ProductMode, SettingsState } from '../types'

interface Props {
  config: ProductConfig
  settings: SettingsState
  onChange: (next: SettingsState) => void
}

/**
 * Form for bring-your-own-key LLM configuration.
 */
/** MCP's stdio transport spawns a local process against a local database — it only
 * ever works from the machine Nexus itself is running on. Detected from the URL
 * this page was loaded from, not a build-time flag, so the same deployed bundle
 * shows correct instructions whether it's opened from a dev machine or not. */
function isLocalhostOrigin(): boolean {
  return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
}

/** Per-deployment MCP SSE endpoint (Server/k8s/05b-ingress-mcp.yaml), if this
 * environment has one deployed. Unset for deployments that haven't set it up. */
const MCP_SSE_URL = import.meta.env.VITE_MCP_SSE_URL?.trim() || ''

export function SettingsPage({ config, settings, onChange }: Props) {
  const meta = PROVIDER_META[settings.llmProvider]
  const models = PROVIDER_MODELS[settings.llmProvider]
  const hasKey = Boolean(settings.llmApiKey.trim())
  const productMode = asProductMode(settings.productMode)
  const isLocal = isLocalhostOrigin()

  function setProvider(provider: LlmProvider) {
    const first = PROVIDER_MODELS[provider][0]?.value ?? ''
    onChange({ ...settings, llmProvider: provider, llmModel: first })
  }

  function setProductMode(mode: ProductMode) {
    onChange({ ...settings, productMode: mode })
  }

  return (
    <div className="settings-page">
      <Link to="/" className="btn" style={{ textDecoration: 'none', marginBottom: '1rem', display: 'inline-block' }}>
        ← Back to chat
      </Link>

      <h2>Settings</h2>
      <p className="lede">
        Configure your LLM provider. Keys stay in this browser only — never stored on the server.
      </p>

      <span className={`status-pill ${hasKey ? 'ok' : 'warn'}`}>
        {hasKey ? `Active — ${meta.label}` : 'No LLM configured'}
      </span>

      <section className="card">
        <h3>Product mode</h3>
        <p className="desc">
          Choose MOSIP or Inji knowledge bases. The server uses matching docs, community, GitHub,
          and code URLs/collections.
        </p>
        <div className="product-toggle product-toggle-3" role="group" aria-label="Product mode">
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'mosip' ? ' active' : ''}`}
            onClick={() => setProductMode('mosip')}
          >
            <img src="/logos/mosip.png" alt="" className="product-toggle-logo" />
            MOSIP
          </button>
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'inji' ? ' active' : ''}`}
            onClick={() => setProductMode('inji')}
          >
            <img src="/logos/inji.png" alt="" className="product-toggle-logo" />
            Inji
          </button>
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'generic' ? ' active' : ''}`}
            onClick={() => setProductMode('generic')}
          >
            <img src="/logos/generic.svg" alt="" className="product-toggle-logo" />
            Direct
          </button>
        </div>
        <p className="product-hint" style={{ marginTop: '0.75rem' }}>
          {productMode === 'generic' ? (
            <>
              Active: <strong>{config.product_name}</strong> · Direct BYOK (no knowledge URLs
              required)
            </>
          ) : (
            <>
              Active: <strong>{config.product_name}</strong> · Docs:{' '}
              <a href={config.docs_base_url} target="_blank" rel="noreferrer">
                {config.docs_base_url}
              </a>
            </>
          )}
        </p>
      </section>

      <section className="card">
        <h3>Choose your AI provider</h3>
        <p className="desc">
          Select a provider and enter your own API key for {config.product_name} chat.
        </p>

        <div className="provider-grid">
          {(Object.keys(PROVIDER_META) as LlmProvider[]).map((p) => (
            <button
              key={p}
              type="button"
              className={`provider-chip${settings.llmProvider === p ? ' active' : ''}`}
              onClick={() => setProvider(p)}
            >
              {PROVIDER_META[p].label}
            </button>
          ))}
        </div>

        <details className="key-guide" style={{ marginBottom: '0.75rem' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
            How do I get a {meta.label} API key?
          </summary>
          <ol style={{ margin: '0.6rem 0 0', paddingLeft: '1.25rem' }}>
            {meta.keySteps.map((step, i) => (
              <li key={i} style={{ marginBottom: '0.3rem' }}>
                {step}
              </li>
            ))}
          </ol>
          {meta.keyNote && (
            <p className="desc" style={{ marginTop: '0.5rem', marginBottom: 0 }}>
              {meta.keyNote}
            </p>
          )}
        </details>

        <div className="field">
          <label htmlFor="api-key">
            API key —{' '}
            <a href={meta.keyUrl} target="_blank" rel="noreferrer">
              {meta.keyUrlLabel}
            </a>
          </label>
          <input
            id="api-key"
            type="password"
            placeholder={meta.keyHint}
            value={settings.llmApiKey}
            onChange={(e) => onChange({ ...settings, llmApiKey: e.target.value })}
            autoComplete="off"
          />
        </div>

        <div className="field">
          <label htmlFor="model">Model</label>
          <select
            id="model"
            value={settings.llmModel}
            onChange={(e) => onChange({ ...settings, llmModel: e.target.value })}
          >
            {models.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div className="privacy">Key is session-only in localStorage — never logged by Nexus.</div>
      </section>

      <section className="card">
        <div className="mcp-card">
          <strong>Claude Desktop (MCP)</strong>
          <span
            style={{
              marginLeft: '0.45rem',
              fontSize: '0.72rem',
              background: 'var(--primary)',
              color: '#fff',
              padding: '0.15rem 0.45rem',
              borderRadius: '4px',
              fontWeight: 700,
            }}
          >
            No API key needed
          </span>
          <p className="desc" style={{ marginTop: '0.45rem', marginBottom: 0 }}>
            Connect Claude Desktop to Nexus MCP. Claude uses your subscription; Nexus only
            retrieves knowledge. Use dual entries for MOSIP vs Inji (or pass{' '}
            <code>product</code> on tools).
          </p>
        </div>
        {isLocal && (
          <details>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Setup guide (dual product)</summary>
            <pre
              style={{
                overflow: 'auto',
                background: '#1c1917',
                color: '#fafaf9',
                padding: '0.85rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                marginTop: '0.75rem',
              }}
            >{`{
  "mcpServers": {
    "mosip-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "<path-to>/MOSIPNexus/Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "mosip"
      }
    },
    "inji-nexus": {
      "command": "uv",
      "args": ["run", "python", "Server/mcp_server/server.py"],
      "env": {
        "PYTHONPATH": "<path-to>/MOSIPNexus/Server",
        "PG_CONNECTION": "postgresql+psycopg://mosip:mosip@localhost:5433/mosipnexus",
        "MCP_TRANSPORT": "stdio",
        "MCP_DEFAULT_PRODUCT": "inji"
      }
    }
  }
}

/* Or single SSE (pass product=mosip|inji on tools):
{
  "mcpServers": {
    "nexus": { "url": "http://localhost:8002/sse" }
  }
}
*/`}</pre>
          </details>
        )}

        {!isLocal && MCP_SSE_URL && (
          <details open>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
              Setup guide — connect to this deployment
            </summary>
            <p className="desc" style={{ marginTop: '0.45rem', marginBottom: 0 }}>
              Pass <code>product="mosip"</code> or <code>product="inji"</code> on each tool call
              — this single endpoint serves both.
            </p>
            <pre
              style={{
                overflow: 'auto',
                background: '#1c1917',
                color: '#fafaf9',
                padding: '0.85rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                marginTop: '0.75rem',
              }}
            >{`{
  "mcpServers": {
    "nexus": { "url": "${MCP_SSE_URL}" }
  }
}`}</pre>
          </details>
        )}

        {!isLocal && !MCP_SSE_URL && (
          <div className="banner banner-warn" style={{ marginTop: '0.75rem' }}>
            Not available on this deployment yet — no MCP endpoint is configured
            (<code>VITE_MCP_SSE_URL</code> is unset).{' '}
            <a
              href="https://github.com/mosip/mosip-labs/blob/develop/MosipNexus/Server/docs/MCP_SERVER.md"
              target="_blank"
              rel="noreferrer"
            >
              See the MCP setup guide
            </a>{' '}
            to deploy one, or run a local copy of Nexus instead.
          </div>
        )}
      </section>

      <section className="card">
        <h3>Preferences</h3>
        <p className="desc">Max chat history turns kept in the browser UI.</p>
        <div className="field">
          <label htmlFor="max-turns">Max turns ({settings.maxHistoryTurns})</label>
          <input
            id="max-turns"
            type="range"
            min={5}
            max={30}
            step={5}
            value={settings.maxHistoryTurns}
            onChange={(e) =>
              onChange({ ...settings, maxHistoryTurns: Number(e.target.value) })
            }
          />
        </div>
      </section>

      <p style={{ textAlign: 'center', color: 'var(--ink-soft)', fontSize: '0.8rem' }}>
        <strong style={{ color: 'var(--ink-muted)' }}>{config.product_name}</strong> · React UI ·
        LangChain · pgvector · HuggingFace
      </p>
    </div>
  )
}
