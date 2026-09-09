import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { resetPassword, verifyEmail } from '../services/api'

/**
 * The two pages an emailed link lands on: confirming an address, and setting a
 * new password.
 *
 * One file because they are the same shape — take a token from the URL, do one
 * thing with it, say what happened — and because both have the same failure
 * mode worth handling well: an expired or reused link. That is the common case,
 * not the exception, so it gets a real explanation and a way forward rather
 * than "invalid token".
 */

export function VerifyEmail() {
  const [params] = useSearchParams()
  const { refresh } = useAuth()
  const token = params.get('token') ?? ''
  const [state, setState] = useState<'working' | 'done' | 'failed'>('working')
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    if (!token) { setState('failed'); setError('That link is missing its token.'); return }
    verifyEmail(token)
      .then(async () => {
        if (!live) return
        // The account's own record of itself changed, so re-read it rather than
        // leaving a stale "unverified" banner on screen.
        await refresh()
        setState('done')
      })
      .catch((err) => {
        if (!live) return
        setError(detailOf(err) || 'That link is not valid.')
        setState('failed')
      })
    return () => { live = false }
  }, [token, refresh])

  return (
    <Frame title="Confirming your address">
      {state === 'working' && <p className="text-small text-ink2">One moment…</p>}
      {state === 'done' && (
        <>
          <p className="text-small leading-relaxed text-ink2">
            Your address is confirmed.
          </p>
          <Link to="/problems" className="btn-accent mt-5 inline-block">start solving</Link>
        </>
      )}
      {state === 'failed' && (
        <>
          <p role="alert" className="text-small leading-relaxed text-hard">{error}</p>
          <p className="mt-3 text-small leading-relaxed text-ink2">
            Links last a day. Sign in and ask for another from your account.
          </p>
          <Link to="/signin" className="btn-primary mt-5 inline-block">sign in</Link>
        </>
      )}
    </Frame>
  )
}

export function ResetPassword() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { refresh } = useAuth()
  const token = params.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      await resetPassword(token, password)
      // Resetting signs you in, so the header must stop saying "sign in".
      await refresh()
      navigate('/problems', { replace: true })
    } catch (err) {
      setError(detailOf(err) || 'We could not set that password. The link may have expired.')
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <Frame title="Set a new password">
        <p role="alert" className="text-small text-hard">That link is missing its token.</p>
        <Link to="/signin" className="btn-primary mt-5 inline-block">back to sign in</Link>
      </Frame>
    )
  }

  return (
    <Frame title="Set a new password">
      <form onSubmit={submit} className="mt-1 flex flex-col gap-3">
        <div>
          <label htmlFor="new-password" className="label">new password</label>
          <input
            id="new-password" type="password" required minLength={8}
            value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password" className="field mt-1"
          />
          <p className="mt-1 font-mono text-micro text-ink3">at least 8 characters</p>
        </div>
        {error && (
          <p role="alert" className="border-l-2 border-hard bg-hard/5 px-3 py-2 text-small text-hard">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy} className="btn-accent w-full">
          {busy ? 'saving…' : 'set password and sign in'}
        </button>
      </form>
      <p className="mt-4 text-micro leading-relaxed text-ink3">
        This signs out anything else using the account, which is the point of
        resetting.
      </p>
    </Frame>
  )
}

function Frame({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="shell max-w-md py-14">
      <h1 className="text-h2">{title}</h1>
      <div className="mt-4">{children}</div>
    </div>
  )
}

function detailOf(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : ''
}
