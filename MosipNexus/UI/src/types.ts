/**
 * @file Shared TypeScript types for the Nexus UI.
 * Mirrors Server JSON shapes for product config, chat, similar-thread lookup,
 * and client-side BYOK settings.
 */

/** Supported bring-your-own-key LLM providers. */
export type LlmProvider = 'groq' | 'anthropic' | 'openai' | 'xai'

/** Product mode — MOSIP/Inji RAG, or generic direct BYOK. */
export type ProductMode = 'mosip' | 'inji' | 'generic'

/** How the server answers: RAG over KB, or direct LLM only. */
export type AnswerMode = 'rag' | 'direct'

/** Confidence label returned with an assistant answer. */
export type Confidence = 'high' | 'medium' | 'low' | 'n/a' | string

/** One knowledge source shown in the sidebar. */
export interface KnowledgeSource {
  key: string
  label: string
}

/** Branding and deep-link URLs from `GET /config` (one product). */
export interface ProductConfig {
  product_name: string
  product_short: string
  product_slug: string
  docs_base_url: string
  community_base_url: string
  community_new_topic_url: string
  github_org: string
  logo_url?: string
  retrieval_enabled?: boolean
  default_answer_mode?: AnswerMode
  default_product?: string
  active_product?: string
  products?: Record<string, ProductConfig>
  answer_modes?: AnswerMode[]
  /** Knowledge sources configured for this product (from server). */
  sources?: KnowledgeSource[]
}

/** One cited source attached to a chat answer. */
export interface SourceItem {
  source: string
  title: string
  source_type: string
  tags: string
  accepted: boolean
}

/** LLM token counters for one assistant answer. */
export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

/** Response body from `POST /chat`. */
export interface ChatResponse {
  answer: string
  sources: SourceItem[]
  source_type: string
  confidence: Confidence
  similar_questions: string[]
  session_id: string
  token_usage?: TokenUsage
  /** 1-based turn number — pass to `submitFeedback` to rate this answer. */
  turn?: number
}

/** Feedback rating submitted for one turn. */
export type FeedbackRating = 'positive' | 'negative'

/** Response body from `POST /similar`. */
export interface SimilarResult {
  found: boolean
  title: string
  source: string
  similarity_score: number
  message: string
}

/**
 * One bubble in the in-memory conversation.
 * Assistant messages may carry sources, confidence, and expert/community context.
 */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceItem[]
  source_type?: string
  confidence?: Confidence
  similar_questions?: string[]
  token_usage?: TokenUsage
  /** Original user question (on assistant messages) for expert / community actions */
  userQuestion?: string
  similarThread?: {
    title: string
    source: string
    similarity_score: number
  }
  /** 1-based turn number (on assistant messages) — needed to submit feedback. */
  turn?: number
  /** Rating already submitted for this turn, if any (prevents double-submit). */
  feedbackRating?: FeedbackRating
}

/** BYOK settings persisted under `nexus-ui-settings` in localStorage. */
export interface SettingsState {
  llmProvider: LlmProvider
  llmApiKey: string
  llmModel: string
  maxHistoryTurns: number
  /** Active product knowledge mode (MOSIP vs Inji). */
  productMode: ProductMode
}
