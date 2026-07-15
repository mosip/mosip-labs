/**
 * @file “Ask Expert” collapsible form.
 * Collects the user’s email and posts to `POST /notify/expert` for
 * low-confidence or unanswered assistant turns.
 */
import { useState, type FormEvent } from 'react'
import { ApiError, notifyExpert } from '../api/client'

interface Props {
  question: string
  language: string
  context: string
  unanswered: boolean
  productShort: string
}

/**
 * Inline form to escalate a question to a MOSIP expert.
 */
export function ExpertForm({
  question,
  language,
  context,
  unanswered,
  productShort,
}: Props) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) {
      setStatus('Please enter your email so the expert can reply.')
      return
    }
    setBusy(true)
    setStatus(null)
    try {
      const res = await notifyExpert({
        question,
        language,
        userEmail: email.trim(),
        context,
        unanswered,
      })
      setStatus(
        res.ok
          ? `${res.message} A ${productShort} expert will be in touch.`
          : res.message,
      )
      if (res.ok) setOpen(false)
    } catch (err) {
      setStatus(err instanceof ApiError ? err.message : 'Failed to send request.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="expert-box">
      {!open ? (
        <button type="button" className="btn btn-block" onClick={() => setOpen(true)}>
          Ask {productShort} Expert
        </button>
      ) : (
        <form onSubmit={(e) => void submit(e)}>
          <strong>Request a {productShort} Expert Response</strong>
          <p className="desc" style={{ marginTop: '0.35rem' }}>
            Leave your email so a team member can reach you.
          </p>
          <div className="field">
            <label htmlFor="expert-email">Your email</label>
            <input
              id="expert-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>
          <div className="row-actions">
            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
              {busy ? 'Sending…' : 'Send request'}
            </button>
            <button
              type="button"
              className="btn btn-block"
              onClick={() => setOpen(false)}
              disabled={busy}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {status && <p style={{ margin: '0.65rem 0 0', fontSize: '0.88rem' }}>{status}</p>}
    </div>
  )
}
