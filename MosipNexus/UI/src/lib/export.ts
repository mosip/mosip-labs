/**
 * @file Offline HTML export for chat transcripts.
 * Builds a self-contained report (MOSIP-tinted styles) and triggers a download.
 */
import type { ChatMessage } from '../types'

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function mdToHtml(text: string): string {
  let t = escapeHtml(text)
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>')
  t = t.replace(/^(\d+)\.\s+/gm, '<br><strong>$1.</strong> ')
  t = t.replace(/^[-*•]\s+/gm, '<br>&nbsp;&nbsp;• ')
  t = t.replace(/\n/g, '<br>')
  t = t.replace(/^(<br>)+/, '')
  return t
}

function safeUrl(url: string): string {
  const lower = url.toLowerCase()
  return lower.startsWith('http://') || lower.startsWith('https://') ? url : '#'
}

/**
 * Render the conversation as a standalone HTML document string.
 * Includes product title, timestamp, language, confidence badges, and source links.
 */
export function exportChatHtml(
  messages: ChatMessage[],
  productName: string,
  language: string,
): string {
  const now = new Date().toLocaleString()
  let rows = ''
  for (const msg of messages) {
    if (msg.role === 'user') {
      rows += `<div class="turn"><div class="question"><span class="label">Question</span><p>${escapeHtml(msg.content)}</p></div>`
    } else {
      const badge =
        msg.confidence === 'high'
          ? 'High'
          : msg.confidence === 'medium'
            ? 'Medium'
            : msg.confidence === 'low'
              ? 'Low'
              : ''
      let sourcesHtml = ''
      if (msg.sources?.length) {
        const seen = new Set<string>()
        let links = ''
        for (const src of msg.sources) {
          const url = src.source
          if (!url || seen.has(url)) continue
          seen.add(url)
          const title = src.title || url
          links += `<li><a href="${escapeHtml(safeUrl(url))}" target="_blank" rel="noreferrer">${escapeHtml(title)}</a></li>`
        }
        if (links) {
          sourcesHtml = `<div class="sources"><strong>Sources:</strong><ul>${links}</ul></div>`
        }
      }
      rows += `<div class="answer"><span class="label">Answer</span>${
        badge ? `<span class="badge">${badge}</span>` : ''
      }<div class="answer-body">${mdToHtml(msg.content)}</div>${sourcesHtml}${
        msg.token_usage?.total_tokens
          ? `<div class="tokens">Tokens: ${msg.token_usage.total_tokens.toLocaleString()} (in ${msg.token_usage.prompt_tokens.toLocaleString()} · out ${msg.token_usage.completion_tokens.toLocaleString()})</div>`
          : ''
      }</div></div>`
    }
  }

  const turns = messages.filter((m) => m.role === 'user').length
  const tokenTotal = messages.reduce(
    (sum, m) => sum + (m.role === 'assistant' ? m.token_usage?.total_tokens || 0 : 0),
    0,
  )
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>${escapeHtml(productName)} — Chat Report</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;color:#1c1917}
.meta{color:#78716c;font-size:.9em;margin-bottom:30px;text-align:center}
.turn{border:1px solid #e7e5e4;border-radius:10px;margin-bottom:20px;overflow:hidden}
.question{background:#eef4fb;padding:16px}.answer{background:#fff;padding:16px}
.label{font-size:.75em;font-weight:700;text-transform:uppercase;color:#5b6573;display:block;margin-bottom:6px}
.badge{font-size:.8em;background:#e8f6ef;padding:2px 8px;border-radius:12px;margin-bottom:10px;display:inline-block}
.answer-body{line-height:1.65}.sources{margin-top:14px;font-size:.85em;background:#f7f9fc;padding:10px;border-radius:6px}
.tokens{margin-top:10px;font-size:.8em;color:#78716c}
a{color:#1b52a4}
</style></head>
<body>
<h1 style="text-align:center;color:#1b52a4">${escapeHtml(productName)} — Chat Report</h1>
<div class="meta">Generated: ${escapeHtml(now)} | Language: ${escapeHtml(language)} | Turns: ${turns}${
    tokenTotal ? ` | Tokens: ${tokenTotal.toLocaleString()}` : ''
  }</div>
${rows}
</body></html>`
}

/**
 * Trigger a browser download of an HTML blob under the given filename.
 */
export function downloadHtml(filename: string, html: string): void {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
