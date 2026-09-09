import {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from 'react'
import type { ReactNode } from 'react'
import * as api from '../services/api'
import type { Claimed, PublicUser } from '../types'

/**
 * Who is signed in, for the whole app.
 *
 * The session itself lives in an httpOnly cookie, so nothing here holds a
 * credential — this is a cache of "what does /auth/me say", refreshed when it
 * could have changed. That is deliberate: a token in JavaScript is a token any
 * injected script can read, and the whole point of the cookie is that it cannot.
 *
 * `lib/session.ts` still exists alongside this and still matters. It identifies
 * the *browser* so a signed-out visitor's work is attributable, and signing in
 * claims it.
 */

interface AuthState {
  user: PublicUser | null
  /** True until the first /auth/me lands. Distinct from "signed out". */
  loading: boolean
  /** Problems a signed-out visitor may still run. Null once signed in. */
  guestRunsLeft: number | null
  /** What the last sign-in pulled over from the anonymous session. */
  claimed: Claimed | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName?: string) => Promise<void>
  signOut: () => Promise<void>
  refresh: () => Promise<void>
  dismissClaimed: () => void
}

const AuthContext = createContext<AuthState | null>(null)

/**
 * The claim summary outlives the render that produced it.
 *
 * Signing in usually happens *from* somewhere — the editor's gate sends you to
 * /signin and back — so the navigation that follows would drop an in-memory
 * banner before anybody read it, and a full reload drops it for certain. It
 * survives in sessionStorage until dismissed or the tab closes, which is
 * exactly as long as the message is worth showing.
 */
const CLAIM_KEY = 'memoize.claimed'

function readClaim(): Claimed | null {
  try {
    const raw = sessionStorage.getItem(CLAIM_KEY)
    return raw ? (JSON.parse(raw) as Claimed) : null
  } catch {
    return null
  }
}

function writeClaim(value: Claimed | null) {
  try {
    if (value) sessionStorage.setItem(CLAIM_KEY, JSON.stringify(value))
    else sessionStorage.removeItem(CLAIM_KEY)
  } catch {
    // Private windows and blocked storage: the banner just does not persist.
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PublicUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [guestRunsLeft, setGuestRunsLeft] = useState<number | null>(null)
  const [claimed, setClaimed] = useState<Claimed | null>(readClaim)

  const refresh = useCallback(async () => {
    try {
      const me = await api.getMe()
      setUser(me.user)
      setGuestRunsLeft(me.guest_runs_left)
    } catch {
      // A backend that is down, or VITE_USE_MOCK with no server: signed out is
      // the honest reading, and it keeps the rest of the site usable.
      setUser(null)
      setGuestRunsLeft(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const adopt = useCallback((res: { user: PublicUser; claimed: Claimed }) => {
    setUser(res.user)
    setGuestRunsLeft(null)
    // Only worth surfacing when it actually moved something.
    const total = res.claimed.submissions + res.claimed.contributions + res.claimed.problems
    const next = total > 0 ? res.claimed : null
    setClaimed(next)
    writeClaim(next)
  }, [])

  const value = useMemo<AuthState>(() => ({
    user,
    loading,
    guestRunsLeft,
    claimed,
    signIn: async (email, password) => adopt(await api.signIn({ email, password })),
    signUp: async (email, password, display_name = '') =>
      adopt(await api.signUp({ email, password, display_name })),
    signOut: async () => {
      try {
        await api.signOut()
      } finally {
        // Locally signed out even if the call failed. Leaving the UI signed in
        // after somebody pressed sign out is the worse of the two wrong states.
        setUser(null)
        setClaimed(null)
        writeClaim(null)
        void refresh()
      }
    },
    refresh,
    dismissClaimed: () => { setClaimed(null); writeClaim(null) },
  }), [user, loading, guestRunsLeft, claimed, adopt, refresh])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
