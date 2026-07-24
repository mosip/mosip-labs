/**
 * @file Main chat experience.
 * Owns session/messages, language lock, similar-thread lookup, composer,
 * HTML export, and composes Sidebar + MessageBubble list.
 */
import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, chat, deleteSession, findSimilar } from '../api/client'
import { ErrorBanner } from '../components/ErrorBanner'
import { MessageBubble } from '../components/MessageBubble'
import { Sidebar } from '../components/Sidebar'
import { downloadHtml, exportChatHtml } from '../lib/export'
import { detectLangInstruction, detectLanguageHint } from '../lib/language'
import { asProductMode } from '../lib/settings'
import type { ChatMessage, ProductConfig, ProductMode, SettingsState } from '../types'

interface Props {
  config: ProductConfig
  settings: SettingsState
  sidebarOpen: boolean
  onToggleSidebar: () => void
  onProductModeChange: (mode: ProductMode) => void
}

/**
 * Primary chat page: send questions via the Nexus API, render turns, and
 * manage language / session lifecycle.
 */
export function ChatPage({
  config,
  settings,
  sidebarOpen,
  onToggleSidebar,
  onProductModeChange,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [language, setLanguage] = useState('English')
  const [langCode, setLangCode] = useState('en')
  const [langLocked, setLangLocked] = useState(false)
  const [pendingLang, setPendingLang] = useState<{ code: string; name: string } | null>(null)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | string | null>(null)
  const [retryQuestion, setRetryQuestion] = useState<string | null>(null)
  const [showGoto, setShowGoto] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Per-product conversation persistence: save/restore messages + session when switching modes
  const messagesMapRef = useRef<Record<string, ChatMessage[]>>({})
  const sessionMapRef = useRef<Record<string, string | null>>({})
  const prevSlugRef = useRef<string>(config.product_slug)
  const messagesRef = useRef(messages)
  messagesRef.current = messages
  const sessionIdRef = useRef(sessionId)
  sessionIdRef.current = sessionId

  useEffect(() => {
    const prev = prevSlugRef.current
    const curr = config.product_slug
    if (prev === curr) return
    messagesMapRef.current[prev] = messagesRef.current
    sessionMapRef.current[prev] = sessionIdRef.current
    setMessages(messagesMapRef.current[curr] ?? [])
    setSessionId(sessionMapRef.current[curr] ?? null)
    setLanguage('English')
    setLangCode('en')
    setLangLocked(false)
    setPendingLang(null)
    setError(null)
    setRetryQuestion(null)
    prevSlugRef.current = curr
  }, [config.product_slug])

  const turnCount = messages.filter((m) => m.role === 'user').length
  const tokenTotal = messages.reduce(
    (sum, m) => sum + (m.role === 'assistant' ? m.token_usage?.total_tokens || 0 : 0),
    0,
  )
  const hasKey = Boolean(settings.llmApiKey.trim())

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const onScroll = () => {
      const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      setShowGoto(fromBottom > 280)
    }
    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  async function handleNewChat() {
    await deleteSession(sessionId)
    setSessionId(null)
    setMessages([])
    setLanguage('English')
    setLangCode('en')
    setLangLocked(false)
    setPendingLang(null)
    setError(null)
    setRetryQuestion(null)
  }

  function handleExport() {
    const html = exportChatHtml(messages, config.product_name, language)
    const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')
    downloadHtml(`${config.product_slug}_nexus_${stamp}.html`, html)
  }

  async function sendMessage(raw: string) {
    const question = raw.trim()
    if (!question || busy) return
    if (!hasKey) {
      setError('Add an LLM API key in Settings before chatting.')
      setRetryQuestion(null)
      return
    }

    setError(null)
    setRetryQuestion(null)
    setInput('')

    let nextLang = language
    const instruction = detectLangInstruction(question)
    if (instruction && instruction.code !== langCode) {
      setPendingLang(instruction)
    } else if (!langLocked) {
      const hint = detectLanguageHint(question, langCode)
      if (hint) {
        nextLang = hint.name
        setLangCode(hint.code)
        setLanguage(hint.name)
      }
    }

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    }
    setMessages((prev) => [...prev, userMsg])
    setBusy(true)

    let similarThread: ChatMessage['similarThread']
    try {
      const similar = await findSimilar(question)
      if (similar) {
        similarThread = {
          title: similar.title,
          source: similar.source,
          similarity_score: similar.similarity_score,
        }
      }
    } catch {
      /* optional — chat still proceeds */
    }

    try {
      const result = await chat({
        question,
        sessionId,
        language: nextLang,
        llmProvider: settings.llmProvider,
        llmApiKey: settings.llmApiKey,
        llmModel: settings.llmModel,
      })
      setSessionId(result.session_id)
      const assistant: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.answer,
        sources: result.sources,
        source_type: result.source_type,
        confidence: result.confidence,
        similar_questions: result.similar_questions,
        token_usage: result.token_usage,
        similarThread,
        userQuestion: question,
        turn: result.turn,
      }
      setMessages((prev) => {
        const next = [...prev, assistant]
        const max = Math.max(5, settings.maxHistoryTurns) * 2
        return next.length > max ? next.slice(next.length - max) : next
      })
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError('Something went wrong.', { code: 'UNKNOWN' })
      setError(apiErr)
      if (apiErr.retryable) setRetryQuestion(question)
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `**Error:** ${apiErr.message}`,
          confidence: 'n/a',
          source_type: 'none',
        },
      ])
    } finally {
      setBusy(false)
    }
  }

  function handleRetry() {
    if (!retryQuestion || busy) return
    const q = retryQuestion
    setRetryQuestion(null)
    setError(null)
    // Drop the last user + error assistant pair so retry does not duplicate them
    setMessages((prev) => {
      if (prev.length < 2) return prev
      const last = prev[prev.length - 1]
      const prevUser = prev[prev.length - 2]
      if (
        last.role === 'assistant' &&
        last.source_type === 'none' &&
        prevUser.role === 'user' &&
        prevUser.content === q
      ) {
        return prev.slice(0, -2)
      }
      return prev
    })
    void sendMessage(q)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage(input)
    }
  }

  return (
    <div className={`app-shell${sidebarOpen ? '' : ' sidebar-collapsed'}`}>
      <Sidebar
        config={config}
        productMode={asProductMode(settings.productMode)}
        onProductModeChange={(mode) => {
          onProductModeChange(mode)
        }}
        language={language}
        langLocked={langLocked}
        turnCount={turnCount}
        tokenTotal={tokenTotal}
        hasMessages={messages.length > 0}
        onNewChat={() => void handleNewChat()}
        onExport={handleExport}
        onLockLanguage={() => setLangLocked(true)}
        onUnlockLanguage={() => setLangLocked(false)}
        onSwitchEnglish={() => {
          setLanguage('English')
          setLangCode('en')
          setLangLocked(true)
          setPendingLang(null)
        }}
      />

      <main className="main">
        <div className="topbar">
          <button type="button" className="icon-btn" onClick={onToggleSidebar} aria-label="Toggle sidebar">
            ☰
          </button>
        </div>

        <header className="hero">
          <h2>{config.product_name}</h2>
          <p>
            {config.default_answer_mode === 'direct' || config.product_slug === 'generic'
              ? 'Ask anything — answers from your BYOK LLM (no docs knowledge base required).'
              : `Ask anything about ${config.product_short} — answers from docs, community forum, GitHub issues, Confluence, and source code.`}
          </p>
        </header>

        {!hasKey && (
          <div className="banner banner-warn">
            No LLM configured.{' '}
            <Link to="/settings">Open Settings</Link> to add a Claude, OpenAI, or Groq API key —
            or use Claude Desktop with MCP.
          </div>
        )}

        {pendingLang && (
          <div className="banner banner-info">
            Stay in <strong>{pendingLang.name}</strong> for the rest of this conversation?
            <div className="row-actions" style={{ marginTop: '0.65rem' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => {
                  setLanguage(pendingLang.name)
                  setLangCode(pendingLang.code)
                  setLangLocked(true)
                  setPendingLang(null)
                }}
              >
                Yes, lock to {pendingLang.name}
              </button>
              <button type="button" className="btn" onClick={() => setPendingLang(null)}>
                No, just this reply
              </button>
            </div>
          </div>
        )}

        {error && (
          <ErrorBanner
            error={error}
            onDismiss={() => {
              setError(null)
              setRetryQuestion(null)
            }}
            onRetry={retryQuestion ? handleRetry : undefined}
          />
        )}

        <div className="chat-scroll" ref={scrollRef}>
          {messages.length === 0 && !busy && (
            <div className="empty-state">
              <h3>Start a conversation</h3>
              <p>
                Try asking about error codes, module setup, or deployment for {config.product_short}.
              </p>
            </div>
          )}

          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              productShort={config.product_short}
              communityNewTopicUrl={config.community_new_topic_url}
              language={language}
              sessionId={sessionId}
              onFeedbackSubmitted={(rating) => {
                setMessages((prev) =>
                  prev.map((msg) => (msg.id === m.id ? { ...msg, feedbackRating: rating } : msg)),
                )
              }}
            />
          ))}

          {busy && (
            <div className="message-row assistant">
              <div className="avatar assistant" aria-hidden>
                N
              </div>
              <div className="bubble">
                <div className="typing" aria-label="Searching">
                  <i />
                  <i />
                  <i />
                </div>
                Searching docs and community…
              </div>
            </div>
          )}
        </div>

        {showGoto && (
          <button
            type="button"
            className="goto-latest"
            onClick={() =>
              scrollRef.current?.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: 'smooth',
              })
            }
          >
            ↓ Latest message
          </button>
        )}

        <div className="composer-wrap">
          <div className="composer">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={`Ask anything about ${config.product_short}…`}
              rows={1}
              disabled={busy}
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy || !input.trim()}
              onClick={() => void sendMessage(input)}
            >
              Send
            </button>
          </div>
          <div className="footer-note">
            Powered by LangChain · pgvector · HuggingFace
            {hasKey
              ? ` · ${
                  settings.llmProvider === 'anthropic'
                    ? 'Claude'
                    : settings.llmProvider === 'openai'
                      ? 'OpenAI'
                      : 'Groq'
                }`
              : ''}
          </div>
        </div>
      </main>
    </div>
  )
}
