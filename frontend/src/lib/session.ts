/**
 * Who this browser is.
 *
 * There are no accounts yet, so this identifies a *browser*, not a person. It
 * exists now rather than later for one reason: every run, submit and
 * contribution is stored against it, so when accounts land this activity can be
 * claimed by a real user instead of being an anonymous pile that has to be
 * discarded. On the server, `app/identity.py` is the matching seam.
 *
 * Deliberately not a cookie: nothing here is a credential, it is never a
 * security boundary, and treating it as one would invite exactly that mistake.
 */

const KEY = 'memoize.session'

/** Used when storage is unavailable — private windows, or storage blocked. */
let ephemeral: string | null = null

function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  // Older Safari. Good enough: this is an opaque key, not a secret.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

/**
 * The session id, created on first use and kept across visits.
 *
 * Never throws. If storage is blocked the id lives for the page's lifetime —
 * progress then stops persisting across reloads, which is a degraded but
 * working state rather than a broken one.
 */
export function getSessionId(): string {
  try {
    let id = localStorage.getItem(KEY)
    if (!id) {
      id = uuid()
      localStorage.setItem(KEY, id)
    }
    return id
  } catch {
    if (!ephemeral) ephemeral = uuid()
    return ephemeral
  }
}
