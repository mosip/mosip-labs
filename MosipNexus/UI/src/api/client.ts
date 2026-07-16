/**
 * @file HTTP client for the Nexus Server.
 * Browser calls same-origin `/api` (Vite or nginx proxy) unless
 * `VITE_NEXUS_API_URL` overrides the base URL.
 *
 * Error bodies follow the server shape::
 *
 *   { detail: { code, message, details, request_id } }
 *
 * Older plain-string ``detail`` values are still accepted.
 */
import type { ChatResponse, ProductConfig, ProductMode, SimilarResult } from '../types'

/** Active product mode for API calls (set by App when settings change). */
let _productMode: ProductMode = 'mosip'

/** Update the product mode used for `X-Nexus-Product` on every request. */
export function setApiProductMode(mode: ProductMode): void {
  if (mode === 'inji') _productMode = 'inji'
  else if (mode === 'generic') _productMode = 'generic'
  else _productMode = 'mosip'
}

export function getApiProductMode(): ProductMode {
  return _productMode
}

/** Structured API error with status, code, and optional retry hint. */
export class ApiError extends Error {
  status?: number
  code?: string
  requestId?: string
  details?: unknown
  retryAfter?: number

  constructor(
    message: string,
    opts?: {
      status?: number
      code?: string
      requestId?: string
      details?: unknown
      retryAfter?: number
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = opts?.status
    this.code = opts?.code
    this.requestId = opts?.requestId
    this.details = opts?.details
    this.retryAfter = opts?.retryAfter
  }

  /** True when the server asked the client to retry (capacity / rate limits). */
  get retryable(): boolean {
    return (
      this.code === 'CAPACITY_EXCEEDED' ||
      this.status === 503 ||
      this.status === 429
    )
  }
}

interface StructuredDetail {
  code?: string
  message?: string
  details?: unknown
  request_id?: string
}

function parseErrorPayload(
  data: unknown,
  text: string,
  status: number,
  retryAfterHeader: string | null,
): ApiError {
  let message = text || `Request failed (${status})`
  let code: string | undefined
  let requestId: string | undefined
  let details: unknown
  let retryAfter: number | undefined

  if (retryAfterHeader) {
    const n = Number(retryAfterHeader)
    if (!Number.isNaN(n) && n >= 0) retryAfter = n
  }

  if (typeof data === 'object' && data && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail
    if (typeof detail === 'string') {
      message = detail
    } else if (typeof detail === 'object' && detail) {
      const d = detail as StructuredDetail
      if (typeof d.message === 'string' && d.message) message = d.message
      if (typeof d.code === 'string') code = d.code
      if (typeof d.request_id === 'string') requestId = d.request_id
      details = d.details
      if (
        details &&
        typeof details === 'object' &&
        'retry_after' in (details as object) &&
        retryAfter === undefined
      ) {
        const ra = Number((details as { retry_after: unknown }).retry_after)
        if (!Number.isNaN(ra)) retryAfter = ra
      }
    } else if (detail != null) {
      message = String(detail)
    }
  }

  return new ApiError(message, { status, code, requestId, details, retryAfter })
}

/** Browser calls /api (Vite proxy or nginx). Override with VITE_NEXUS_API_URL if needed. */
function apiBase(): string {
  const explicit = import.meta.env.VITE_NEXUS_API_URL?.trim()
  if (explicit) return explicit.replace(/\/$/, '')
  return '/api'
}

async function request<T>(
  method: string,
  path: string,
  body?: Record<string, unknown>,
  timeoutMs = 120_000,
): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'X-Nexus-Product': _productMode,
    }
    if (body) headers['Content-Type'] = 'application/json'
    const res = await fetch(`${apiBase()}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
    const text = await res.text()
    let data: unknown = {}
    if (text) {
      try {
        data = JSON.parse(text)
      } catch {
        data = { detail: text }
      }
    }
    if (!res.ok) {
      throw parseErrorPayload(data, text, res.status, res.headers.get('Retry-After'))
    }
    return data as T
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('Request timed out. Try again.', {
        code: 'TIMEOUT',
        status: 408,
      })
    }
    throw new ApiError(
      `Cannot reach Nexus API at ${apiBase()}. Is the Server running?`,
      { code: 'NETWORK_ERROR' },
    )
  } finally {
    window.clearTimeout(timer)
  }
}

const FALLBACK_CONFIG: ProductConfig = {
  product_name: 'MOSIP Nexus',
  product_short: 'MOSIP',
  product_slug: 'mosip',
  docs_base_url: 'https://docs.mosip.io/1.2.0',
  community_base_url: 'https://community.mosip.io',
  community_new_topic_url: 'https://community.mosip.io/new-topic',
  github_org: 'mosip',
  logo_url: '/logos/mosip.png',
  default_product: 'mosip',
  active_product: 'mosip',
  answer_modes: ['rag', 'direct'],
  products: {
    mosip: {
      product_name: 'MOSIP Nexus',
      product_short: 'MOSIP',
      product_slug: 'mosip',
      docs_base_url: 'https://docs.mosip.io/1.2.0',
      community_base_url: 'https://community.mosip.io',
      community_new_topic_url: 'https://community.mosip.io/new-topic',
      github_org: 'mosip',
      logo_url: '/logos/mosip.png',
      retrieval_enabled: true,
      default_answer_mode: 'rag',
    },
    inji: {
      product_name: 'Inji Nexus',
      product_short: 'Inji',
      product_slug: 'inji',
      docs_base_url: 'https://docs.inji.io',
      community_base_url: 'https://community.mosip.io/c/inji/16',
      community_new_topic_url: 'https://community.mosip.io/new-topic?category=inji',
      github_org: 'mosip',
      logo_url: '/logos/inji.png',
      retrieval_enabled: true,
      default_answer_mode: 'rag',
    },
    generic: {
      product_name: 'Nexus',
      product_short: 'Assistant',
      product_slug: 'generic',
      docs_base_url: '',
      community_base_url: '',
      community_new_topic_url: '',
      github_org: '',
      logo_url: '/logos/generic.svg',
      retrieval_enabled: false,
      default_answer_mode: 'direct',
    },
  },
}

/**
 * Fetch product branding catalog from `GET /config`.
 * Returns MOSIP/Inji fallback defaults if the Server is unreachable.
 */
export async function getConfig(): Promise<ProductConfig> {
  try {
    return await request<ProductConfig>('GET', '/config', undefined, 10_000)
  } catch {
    return FALLBACK_CONFIG
  }
}

/** Pick the active product entry from a config catalog. */
export function resolveProductConfig(
  catalog: ProductConfig,
  mode: ProductMode,
): ProductConfig {
  const fromCatalog = catalog.products?.[mode]
  if (fromCatalog) {
    return {
      ...fromCatalog,
      products: catalog.products,
      default_product: catalog.default_product ?? 'mosip',
      active_product: mode,
    }
  }
  if (catalog.product_slug === mode) return { ...catalog, active_product: mode }
  return {
    ...FALLBACK_CONFIG.products![mode],
    products: catalog.products ?? FALLBACK_CONFIG.products,
    default_product: catalog.default_product ?? 'mosip',
    active_product: mode,
  }
}

/**
 * Best-effort delete of a server-side chat session (`DELETE /session/:id`).
 * No-ops when `sessionId` is null; swallows errors so the UI can reset locally.
 */
export async function deleteSession(sessionId: string | null): Promise<void> {
  if (!sessionId) return
  try {
    await request('DELETE', `/session/${sessionId}`, undefined, 10_000)
  } catch {
    /* ignore — local reset still proceeds */
  }
}

/**
 * Send a question to `POST /chat` with session, language, and BYOK LLM fields.
 * @returns Answer, sources, confidence, similar questions, and session id.
 */
export async function chat(params: {
  question: string
  sessionId: string | null
  language: string
  llmProvider: string
  llmApiKey: string
  llmModel?: string
}): Promise<ChatResponse> {
  const payload: Record<string, unknown> = {
    question: params.question,
    session_id: params.sessionId,
    language: params.language,
    llm_provider: params.llmProvider,
    llm_api_key: params.llmApiKey,
    notify_on_low_confidence: true,
    product: _productMode,
    answer_mode: _productMode === 'generic' ? 'direct' : 'rag',
  }
  if (params.llmModel) payload.llm_model = params.llmModel
  return request<ChatResponse>('POST', '/chat', payload)
}

/**
 * Look up a similar community/docs thread for the question (`POST /similar`).
 * @returns The result when `found` is true; otherwise `null`.
 */
export async function findSimilar(question: string): Promise<SimilarResult | null> {
  const result = await request<SimilarResult>('POST', '/similar', { question }, 30_000)
  return result.found ? result : null
}

/**
 * Notify a MOSIP expert about a question (`POST /notify/expert`).
 * Used by the Ask Expert form on low-confidence or unanswered turns.
 */
export async function notifyExpert(params: {
  question: string
  language: string
  userEmail: string
  context?: string
  unanswered?: boolean
}): Promise<{ ok: boolean; message: string }> {
  return request('POST', '/notify/expert', {
    question: params.question,
    language: params.language,
    user_email: params.userEmail,
    context: params.context ?? '',
    unanswered: params.unanswered ?? false,
  })
}
