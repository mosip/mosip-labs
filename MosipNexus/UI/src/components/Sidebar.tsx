/**
 * @file Left navigation / brand rail for the chat shell.
 * Shows product branding, MOSIP/Inji mode switch, session actions, and sources.
 */
import { Link } from 'react-router-dom'
import type { KnowledgeSource, ProductConfig, ProductMode } from '../types'

// Fallback used only when the server hasn't returned a sources list yet.
const FALLBACK_SOURCES: KnowledgeSource[] = [
  { key: 'docs', label: 'Documentation' },
  { key: 'community', label: 'Community Forum' },
  { key: 'github', label: 'GitHub Issues' },
  { key: 'code', label: 'Source Code' },
]

interface Props {
  config: ProductConfig
  productMode: ProductMode
  onProductModeChange: (mode: ProductMode) => void
  language: string
  langLocked: boolean
  turnCount: number
  /** Sum of total_tokens across assistant answers in this session. */
  tokenTotal: number
  hasMessages: boolean
  onNewChat: () => void
  onExport: () => void
  onLockLanguage: () => void
  onUnlockLanguage: () => void
  onSwitchEnglish: () => void
}

/**
 * Collapsible chat sidebar with brand mark and session actions.
 */
export function Sidebar({
  config,
  productMode,
  onProductModeChange,
  language,
  langLocked,
  turnCount,
  tokenTotal,
  hasMessages,
  onNewChat,
  onExport,
  onLockLanguage,
  onUnlockLanguage,
  onSwitchEnglish,
}: Props) {
  const logo = config.logo_url || `/logos/${productMode}.png`

  return (
    <aside className="sidebar">
      <div className="brand">
        <img className="brand-logo" src={logo} alt={`${config.product_short} logo`} />
        <h1>{config.product_name}</h1>
        <p>
          {productMode === 'generic'
            ? 'Direct BYOK assistant — no product docs required'
            : `AI-powered ${config.product_short} Knowledge Assistant`}
        </p>
      </div>

      <div className="sidebar-section">
        <h2>Product mode</h2>
        <div className="product-toggle product-toggle-3" role="group" aria-label="Product mode">
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'mosip' ? ' active' : ''}`}
            onClick={() => onProductModeChange('mosip')}
          >
            <img src="/logos/mosip.png" alt="" className="product-toggle-logo" />
            MOSIP
          </button>
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'inji' ? ' active' : ''}`}
            onClick={() => onProductModeChange('inji')}
          >
            <img src="/logos/inji.png" alt="" className="product-toggle-logo" />
            Inji
          </button>
          <button
            type="button"
            className={`product-toggle-btn${productMode === 'generic' ? ' active' : ''}`}
            onClick={() => onProductModeChange('generic')}
          >
            <img src="/logos/generic.svg" alt="" className="product-toggle-logo" />
            Direct
          </button>
        </div>
        <p className="product-hint">
          {productMode === 'generic'
            ? 'Answers via your LLM key only (no docs / community / GitHub retrieval).'
            : `Uses ${config.product_short} docs, community, GitHub, and code collections.`}
        </p>
      </div>

      <div className="sidebar-actions">
        <button type="button" className="btn btn-primary btn-block" onClick={onNewChat}>
          New chat
        </button>
        <button
          type="button"
          className="btn btn-block"
          onClick={onExport}
          disabled={!hasMessages}
        >
          Export chat
        </button>
      </div>

      <div className="sidebar-section">
        <h2>Session</h2>
        <div className="meta-row">
          <span>Language</span>
          <strong>
            {language} {langLocked ? '🔒' : ''}
          </strong>
        </div>
        <div className="meta-row">
          <span>Turns</span>
          <strong>{turnCount}</strong>
        </div>
        <div className="meta-row" title="Total LLM tokens used in this chat session">
          <span>Tokens</span>
          <strong>{tokenTotal.toLocaleString()}</strong>
        </div>
        <div className="sidebar-actions" style={{ marginTop: '0.65rem' }}>
          {!langLocked ? (
            <>
              {language !== 'English' && (
                <button type="button" className="btn btn-block" onClick={onLockLanguage}>
                  Lock to {language}
                </button>
              )}
              <button type="button" className="btn btn-block" onClick={onSwitchEnglish}>
                Switch to English
              </button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-block" onClick={onUnlockLanguage}>
                Unlock language
              </button>
              {language !== 'English' && (
                <button type="button" className="btn btn-block" onClick={onSwitchEnglish}>
                  Switch to English
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {productMode !== 'generic' && (
        <div className="sidebar-section">
          <h2>Sources searched</h2>
          <div className="source-list">
            {(config.sources ?? FALLBACK_SOURCES).map((s) => (
              <span key={s.key}>
                <span aria-hidden>•</span>
                {s.key === 'docs' ? `${config.product_short} ${s.label}` : s.label}
              </span>
            ))}
          </div>
          <div className="source-links">
            {config.docs_base_url && (
              <a href={config.docs_base_url} target="_blank" rel="noreferrer">
                Docs
              </a>
            )}
            {config.community_base_url && (
              <a href={config.community_base_url} target="_blank" rel="noreferrer">
                Community
              </a>
            )}
            {config.github_org && (
              <a
                href={`https://github.com/${config.github_org}`}
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            )}
          </div>
        </div>
      )}

      <div className="sidebar-section" style={{ marginTop: 'auto' }}>
        <Link to="/settings" className="btn btn-block" style={{ textAlign: 'center', textDecoration: 'none' }}>
          Settings
        </Link>
      </div>
    </aside>
  )
}
