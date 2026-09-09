import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { forgotPassword, oauthUrl } from '../services/api'

/**
 * Sign in and sign up, on one screen.
 *
 * One screen because the two forms differ by a single field, and because a
 * person who is not sure whether they already have an account should not have
 * to guess before they can type. The toggle is a link, not a route, so nothing
 * is lost switching.
 *
 * The OAuth buttons are `<a>`, not buttons: the provider redirects the browser
 * and comes back to the API, which sets the cookie. An XHR cannot follow that.
 */
export default function SignIn() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { signIn, signUp } = useAuth()

  const next = params.get('next') || '/'
  const [mode, setMode] = useState<'in' | 'up'>(params.get('mode') === 'up' ? 'up' : 'in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  // Seeded from the query string: a failed OAuth round trip lands back here
  // with its reason, rather than showing raw JSON in the address bar.
  const [error, setError] = useState(params.get('error') ?? '')
  const [notice, setNotice] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(''); setNotice('')
    try {
      if (mode === 'up') await signUp(email, password, name)
      else await signIn(email, password)
      navigate(next, { replace: true })
    } catch (err) {
      setError(messageFor(err, mode))
    } finally {
      setBusy(false)
    }
  }

  const forgot = async () => {
    if (!email.trim()) {
      setError('Enter your email address first, then ask for a reset link.')
      return
    }
    setBusy(true); setError('')
    try {
      await forgotPassword(email)
      // Says the same thing whether or not the address has an account — the
      // server is careful about that and the UI must not undo it.
      setNotice('If that address has an account, a reset link is on its way.')
    } catch {
      setError('We could not send that just now. Try again in a moment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="shell max-w-md py-14">
      <h1 className="text-h2">{mode === 'up' ? 'Create an account' : 'Sign in'}</h1>
      <p className="mt-2 text-small leading-relaxed text-ink2">
        {mode === 'up'
          ? 'Keeps your progress, your contributions and the problems you add. Anything you have already solved in this browser comes with you.'
          : 'Your progress follows the account, on any machine.'}
      </p>

      <div className="mt-7 flex flex-col gap-2">
        <a href={oauthUrl('github', next)} className="btn-primary w-full">
          continue with GitHub
        </a>
        <a href={oauthUrl('google', next)} className="btn-primary w-full">
          continue with Google
        </a>
      </div>

      <div className="my-6 flex items-center gap-3">
        <span className="h-px flex-1 bg-line" />
        <span className="label">or use an email</span>
        <span className="h-px flex-1 bg-line" />
      </div>

      <form onSubmit={submit} className="flex flex-col gap-3">
        {mode === 'up' && (
          <div>
            <label htmlFor="name" className="label">name (optional)</label>
            <input
              id="name" value={name} onChange={(e) => setName(e.target.value)}
              autoComplete="name" className="field mt-1"
            />
          </div>
        )}
        <div>
          <label htmlFor="email" className="label">email</label>
          <input
            id="email" type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" className="field mt-1"
          />
        </div>
        <div>
          <label htmlFor="password" className="label">password</label>
          <input
            id="password" type="password" required minLength={mode === 'up' ? 8 : 1}
            value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'up' ? 'new-password' : 'current-password'}
            className="field mt-1"
          />
          {mode === 'up' && (
            <p className="mt-1 font-mono text-micro text-ink3">at least 8 characters</p>
          )}
        </div>

        {error && (
          <p role="alert" className="border-l-2 border-hard bg-hard/5 px-3 py-2 text-small text-hard">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="border-l-2 border-accent bg-panel px-3 py-2 text-small text-ink2">
            {notice}
          </p>
        )}

        <button type="submit" disabled={busy} className="btn-accent mt-1 w-full">
          {busy ? 'working…' : mode === 'up' ? 'create account' : 'sign in'}
        </button>
      </form>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={() => { setMode(mode === 'up' ? 'in' : 'up'); setError('') }}
          className="tap font-mono text-micro text-link link"
        >
          {mode === 'up' ? 'I already have an account' : 'Create an account instead'}
        </button>
        {mode === 'in' && (
          <button onClick={forgot} disabled={busy} className="tap font-mono text-micro text-ink3 link hover:text-ink">
            Forgot your password?
          </button>
        )}
      </div>

      <p className="mt-8 max-w-reading text-micro leading-relaxed text-ink3">
        You do not need an account to browse, and the first two problems run
        without one.{' '}
        <Link to="/problems" className="text-link link">Go and look around instead</Link>.
      </p>
    </div>
  )
}

/** Prefer the server's sentence; it is written for the person reading it. */
function messageFor(err: unknown, mode: 'in' | 'up'): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  // A 422 from Pydantic arrives as an array of field errors, which is not a
  // sentence anybody should read.
  if (Array.isArray(detail)) return 'Check the form and try again.'
  return mode === 'up'
    ? 'We could not create that account just now. Try again in a moment.'
    : 'We could not sign you in just now. Try again in a moment.'
}
