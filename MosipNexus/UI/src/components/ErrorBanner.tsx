/**
 * @file Dismissible / retryable API error banner.
 */
import type { ApiError } from '../api/client'

interface Props {
  error: ApiError | string
  onDismiss: () => void
  onRetry?: () => void
}

function asMessage(error: ApiError | string): string {
  return typeof error === 'string' ? error : error.message
}

function isRetryable(error: ApiError | string): boolean {
  return typeof error !== 'string' && Boolean(error.retryable)
}

/**
 * Inline banner for chat / form failures with optional Retry for capacity errors.
 */
export function ErrorBanner({ error, onDismiss, onRetry }: Props) {
  const message = asMessage(error)
  const retryable = isRetryable(error) && onRetry
  const code = typeof error === 'string' ? undefined : error.code
  const requestId = typeof error === 'string' ? undefined : error.requestId

  return (
    <div className="banner banner-error" role="alert">
      <div className="banner-error-body">
        <p className="banner-error-msg">{message}</p>
        {(code || requestId) && (
          <p className="banner-error-meta">
            {code && <span>{code}</span>}
            {code && requestId && <span aria-hidden="true"> · </span>}
            {requestId && <span title="Request id">id {requestId.slice(0, 8)}</span>}
          </p>
        )}
      </div>
      <div className="banner-error-actions">
        {retryable && (
          <button type="button" className="btn btn-primary" onClick={onRetry}>
            Retry
          </button>
        )}
        <button type="button" className="btn" onClick={onDismiss} aria-label="Dismiss error">
          Dismiss
        </button>
      </div>
    </div>
  )
}
