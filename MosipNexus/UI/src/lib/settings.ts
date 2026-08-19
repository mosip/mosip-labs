/**
 * @file BYOK settings persistence and provider metadata.
 * Settings are stored only in browser localStorage under `nexus-ui-settings`.
 */
import type { LlmProvider, ProductMode, SettingsState } from '../types'

const KEY = 'nexus-ui-settings'

const DEFAULTS: SettingsState = {
  llmProvider: 'groq',
  llmApiKey: '',
  llmModel: 'openai/gpt-oss-120b',
  maxHistoryTurns: 10,
  productMode: 'mosip',
}

/** Model dropdown options keyed by LLM provider.
 * Groq retired llama-3.3-70b-versatile, llama-3.1-8b-instant, and
 * mixtral-8x7b-32768 (confirmed via live 502s on this deployment, 2026-08-17 —
 * see https://console.groq.com/docs/deprecations for the current list before
 * re-adding any Llama/Mixtral entry here). */
export const PROVIDER_MODELS: Record<
  LlmProvider,
  { label: string; value: string }[]
> = {
  groq: [
    { label: 'openai/gpt-oss-120b (recommended)', value: 'openai/gpt-oss-120b' },
    { label: 'openai/gpt-oss-20b (faster)', value: 'openai/gpt-oss-20b' },
  ],
  anthropic: [
    { label: 'claude-haiku-4-5 (recommended)', value: 'claude-haiku-4-5-20251001' },
    { label: 'claude-sonnet-4-6', value: 'claude-sonnet-4-6' },
    { label: 'claude-opus-4-8', value: 'claude-opus-4-8' },
  ],
  openai: [
    { label: 'gpt-4o-mini (recommended)', value: 'gpt-4o-mini' },
    { label: 'gpt-4o', value: 'gpt-4o' },
    { label: 'gpt-4-turbo', value: 'gpt-4-turbo' },
  ],
  xai: [
    { label: 'grok-3-mini (recommended)', value: 'grok-3-mini' },
    { label: 'grok-3', value: 'grok-3' },
    { label: 'grok-2', value: 'grok-2' },
  ],
}

/** Display labels, key format hints, and console URLs for each provider. */
export const PROVIDER_META: Record<
  LlmProvider,
  { label: string; keyHint: string; keyUrl: string; keyUrlLabel: string }
> = {
  groq: {
    label: 'Groq',
    keyHint: 'gsk_...',
    keyUrl: 'https://console.groq.com',
    keyUrlLabel: 'Get a free key at console.groq.com',
  },
  anthropic: {
    label: 'Claude — Anthropic',
    keyHint: 'sk-ant-...',
    keyUrl: 'https://console.anthropic.com',
    keyUrlLabel: 'Get your key at console.anthropic.com',
  },
  openai: {
    label: 'OpenAI',
    keyHint: 'sk-...',
    keyUrl: 'https://platform.openai.com/api-keys',
    keyUrlLabel: 'Get your key at platform.openai.com',
  },
  xai: {
    label: 'xAI Grok',
    keyHint: 'xai-...',
    keyUrl: 'https://console.x.ai',
    keyUrlLabel: 'Get your key at console.x.ai',
  },
}

/**
 * Read settings from localStorage, merging with defaults.
 * Returns a fresh copy of defaults if missing or invalid JSON.
 */
export function loadSettings(): SettingsState {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULTS }
    const parsed = { ...DEFAULTS, ...JSON.parse(raw) } as SettingsState
    if (parsed.productMode !== 'mosip' && parsed.productMode !== 'inji' && parsed.productMode !== 'generic') {
      parsed.productMode = 'mosip'
    }
    // Fall back to the recommended model if the saved one is no longer valid (e.g. retired by the provider).
    const validModels = PROVIDER_MODELS[parsed.llmProvider]?.map((m) => m.value) ?? []
    if (!validModels.includes(parsed.llmModel)) {
      parsed.llmModel = validModels[0] ?? DEFAULTS.llmModel
    }
    return parsed
  } catch {
    return { ...DEFAULTS }
  }
}

/**
 * Persist the full settings object to localStorage.
 * Called by `App` whenever settings state changes.
 */
export function saveSettings(next: SettingsState): void {
  localStorage.setItem(KEY, JSON.stringify(next))
}

/** Normalize a product mode string from the API / UI. */
export function asProductMode(raw: string | undefined | null): ProductMode {
  if (raw === 'inji') return 'inji'
  if (raw === 'generic' || raw === 'direct' || raw === 'byok') return 'generic'
  return 'mosip'
}
