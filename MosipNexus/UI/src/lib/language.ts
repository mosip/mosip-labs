/**
 * @file Client-side language helpers for chat.
 * Detects script/heuristics and explicit “reply in …” instructions
 * without a server-side langdetect dependency.
 */

const LANG_NAMES: Record<string, string> = {
  en: 'English',
  ta: 'Tamil',
  hi: 'Hindi',
  fr: 'French',
  de: 'German',
  es: 'Spanish',
  ar: 'Arabic',
  ja: 'Japanese',
  ko: 'Korean',
  pt: 'Portuguese',
  ru: 'Russian',
  it: 'Italian',
  nl: 'Dutch',
  tr: 'Turkish',
  pl: 'Polish',
  ml: 'Malayalam',
  te: 'Telugu',
  kn: 'Kannada',
  bn: 'Bengali',
  ur: 'Urdu',
  zh: 'Chinese',
}

const INSTRUCTION_MAP: Record<string, { code: string; name: string }> = {
  english: { code: 'en', name: 'English' },
  tamil: { code: 'ta', name: 'Tamil' },
  hindi: { code: 'hi', name: 'Hindi' },
  french: { code: 'fr', name: 'French' },
  german: { code: 'de', name: 'German' },
  spanish: { code: 'es', name: 'Spanish' },
  arabic: { code: 'ar', name: 'Arabic' },
  chinese: { code: 'zh', name: 'Chinese' },
  japanese: { code: 'ja', name: 'Japanese' },
  korean: { code: 'ko', name: 'Korean' },
  portuguese: { code: 'pt', name: 'Portuguese' },
  russian: { code: 'ru', name: 'Russian' },
  italian: { code: 'it', name: 'Italian' },
  dutch: { code: 'nl', name: 'Dutch' },
  turkish: { code: 'tr', name: 'Turkish' },
  polish: { code: 'pl', name: 'Polish' },
  malayalam: { code: 'ml', name: 'Malayalam' },
  telugu: { code: 'te', name: 'Telugu' },
  kannada: { code: 'kn', name: 'Kannada' },
  bengali: { code: 'bn', name: 'Bengali' },
  urdu: { code: 'ur', name: 'Urdu' },
}

const LANG_INSTRUCTION_RE =
  /\b(?:reply|respond|answer|speak|write|communicate|talk)\s+in\s+([a-zA-Z]+)\b|\buse\s+([a-zA-Z]+)\s*(?:language|lang)?\b|\bswitch\s+to\s+([a-zA-Z]+)\b|\btranslate\s+(?:to|in)\s+([a-zA-Z]+)\b/i

/**
 * Lightweight script heuristics (no langdetect dependency in the browser).
 * Also suggests English when the current lock is non-English and the text is ASCII.
 * @returns Detected `{ code, name }` or `null` if no hint applies.
 */
export function detectLanguageHint(
  text: string,
  currentCode: string,
): { code: string; name: string } | null {
  const trimmed = text.trim()
  if (trimmed.length < 5) return null

  if (/[\u0B80-\u0BFF]/.test(trimmed)) return { code: 'ta', name: 'Tamil' }
  if (/[\u0900-\u097F]/.test(trimmed)) return { code: 'hi', name: 'Hindi' }
  if (/[\u0D00-\u0D7F]/.test(trimmed)) return { code: 'ml', name: 'Malayalam' }
  if (/[\u0C00-\u0C7F]/.test(trimmed)) return { code: 'te', name: 'Telugu' }
  if (/[\u0C80-\u0CFF]/.test(trimmed)) return { code: 'kn', name: 'Kannada' }
  if (/[\u0980-\u09FF]/.test(trimmed)) return { code: 'bn', name: 'Bengali' }
  if (/[\u0600-\u06FF]/.test(trimmed)) return { code: 'ar', name: 'Arabic' }
  if (/[\u3040-\u30FF]/.test(trimmed)) return { code: 'ja', name: 'Japanese' }
  if (/[\uAC00-\uD7AF]/.test(trimmed)) return { code: 'ko', name: 'Korean' }
  if (/[\u4E00-\u9FFF]/.test(trimmed)) return { code: 'zh', name: 'Chinese' }

  if (currentCode !== 'en' && trimmed.length >= 40 && /^[\x00-\x7F\s]+$/.test(trimmed)) {
    return { code: 'en', name: 'English' }
  }
  return null
}

/**
 * Parse explicit language-switch phrases (e.g. “reply in Tamil”, “switch to French”).
 * @returns Mapped language or `null` if no instruction matched.
 */
export function detectLangInstruction(
  text: string,
): { code: string; name: string } | null {
  const m = LANG_INSTRUCTION_RE.exec(text)
  if (!m) return null
  const word = (m[1] || m[2] || m[3] || m[4] || '').toLowerCase()
  return INSTRUCTION_MAP[word] ?? null
}

/**
 * Human-readable language name for a BCP-47-ish code; falls back to the code itself.
 */
export function langName(code: string): string {
  return LANG_NAMES[code] ?? code
}
