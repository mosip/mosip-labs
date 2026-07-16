/**
 * @file Single chat turn renderer.
 * User messages are plain text; assistant messages use GFM markdown plus
 * confidence, sources, similar questions, community CTA, and optional ExpertForm.
 */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage } from '../types'
import { ExpertForm } from './ExpertForm'

const SOURCE_LABEL: Record<string, string> = {
  mosip_docs: 'Documentation',
  community: 'Community Forum',
  github: 'GitHub Issues',
  code: 'Source Code',
  confluence: 'Confluence',
  jira: 'Jira Tickets',
  mixed: 'Docs · Community · GitHub · Code',
  web: 'Web Sources',
}

function safeUrl(url: string): string {
  const lower = url.toLowerCase()
  return lower.startsWith('http://') || lower.startsWith('https://') ? url : '#'
}

interface Props {
  message: ChatMessage
  productShort: string
  communityNewTopicUrl: string
  language: string
  onExpertDone?: () => void
}

/**
 * Renders one user or assistant bubble in the conversation list.
 */
export function MessageBubble({
  message,
  productShort,
  communityNewTopicUrl,
  language,
}: Props) {
  const isUser = message.role === 'user'
  const confidence = message.confidence
  const showExpert =
    !isUser &&
    (message.source_type === 'web' ||
      message.source_type === 'none' ||
      confidence === 'low') &&
    message.source_type !== 'chat'

  return (
    <div className={`message-row ${message.role}`}>
      {!isUser && (
        <div className="avatar assistant" aria-hidden>
          N
        </div>
      )}
      <div className="bubble">
        {message.similarThread && (
          <div className="banner banner-info" style={{ margin: '0 0 0.75rem' }}>
            <strong>Similar thread found</strong> (
            {Math.round(message.similarThread.similarity_score * 100)}%)
            <br />
            <a href={safeUrl(message.similarThread.source)} target="_blank" rel="noreferrer">
              {message.similarThread.title}
            </a>
          </div>
        )}

        <div className="md">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>

        {!isUser && message.source_type === 'web' && (
          <div className="banner banner-warn" style={{ margin: '0.75rem 0 0' }}>
            This answer is from external web sources, not official {productShort} docs.
            Verify before production use.
          </div>
        )}

        {!isUser && confidence === 'low' && message.source_type && !['none', 'chat', 'web', 'n/a'].includes(message.source_type) && (
          <div className="banner banner-warn" style={{ margin: '0.75rem 0 0' }}>
            Low confidence — the knowledge base may not fully cover this topic. The team can be
            notified automatically.
          </div>
        )}

        {!isUser && confidence && confidence !== 'n/a' && (
          <div className={`confidence ${confidence}`}>
            {confidence === 'high' && 'High confidence'}
            {confidence === 'medium' && 'Medium confidence'}
            {confidence === 'low' && 'Low confidence — answer may be incomplete'}
          </div>
        )}

        {!isUser && !!message.token_usage?.total_tokens && (
          <div className="token-usage" title="LLM tokens used for this query (input + output)">
            <span className="token-total">
              {message.token_usage.total_tokens.toLocaleString()} tokens
            </span>
            <span className="token-detail">
              in {message.token_usage.prompt_tokens.toLocaleString()} · out{' '}
              {message.token_usage.completion_tokens.toLocaleString()}
            </span>
          </div>
        )}

        {!isUser && !!message.similar_questions?.length && (
          <details className="panel" open>
            <summary>Related community threads</summary>
            <div className="panel-body">
              <ul>
                {message.similar_questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          </details>
        )}

        {!isUser && !!message.sources?.length && (
          <details className="panel" open>
            <summary>{SOURCE_LABEL[message.source_type || ''] || 'Sources'}</summary>
            <div className="panel-body">
              {(() => {
                const seen = new Set<string>()
                return message.sources!.map((src) => {
                  if (!src.source || seen.has(src.source)) return null
                  seen.add(src.source)
                  return (
                    <a
                      key={src.source}
                      href={safeUrl(src.source)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {src.title || src.source}
                      {src.tags ? ` · ${src.tags}` : ''}
                      {src.accepted ? ' ✓' : ''}
                    </a>
                  )
                })
              })()}
            </div>
          </details>
        )}

        {showExpert && (
          <>
            {message.source_type === 'none' && (
              <div className="banner banner-warn" style={{ marginTop: '0.75rem' }}>
                This question is not covered in {productShort} documentation, community, or web
                search.
              </div>
            )}
            <div className="row-actions">
              <a
                className="btn btn-block"
                style={{ textAlign: 'center', textDecoration: 'none' }}
                href={`${communityNewTopicUrl}?title=${encodeURIComponent((message.userQuestion || message.content).slice(0, 100))}`}
                target="_blank"
                rel="noreferrer"
              >
                Post to {productShort} Community
              </a>
            </div>
            <ExpertForm
              question={message.userQuestion || message.content.slice(0, 200)}
              language={language}
              context={message.content.slice(0, 300)}
              unanswered={message.source_type === 'none'}
              productShort={productShort}
            />
          </>
        )}
      </div>
      {isUser && (
        <div className="avatar user" aria-hidden>
          You
        </div>
      )}
    </div>
  )
}
