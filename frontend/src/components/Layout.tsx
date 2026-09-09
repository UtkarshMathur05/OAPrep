import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

/**
 * Two groups, not five equal links.
 *
 * Browsing a corpus is what every OA site does; recalling a problem you cannot
 * name is the only thing this one does. Flattening both into one row of
 * identical links said they were the same kind of thing. A rule between them
 * says they are not, and costs nothing.
 */
// `narrow: false` means the tab is dropped on a phone. Five tabs plus the
// wordmark need ~570px, so on a 390px screen `recall` and `contribute` — the
// two things this site is for — sat off the right edge of a scroller with no
// affordance saying to scroll. Companies and Topics are pure directories,
// reachable from the home page and from the filters on /problems, so they are
// what gives way.
const BROWSE = [
  { to: '/problems', label: 'problems', narrow: true },
  { to: '/companies', label: 'companies', narrow: false },
  { to: '/topics', label: 'topics', narrow: false },
]
const DO = [
  { to: '/recall', label: 'recall', narrow: true },
  { to: '/contribute', label: 'contribute', narrow: true },
]

export default function Layout() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-lineStrong bg-ground/95 backdrop-blur">
        <div className="shell flex h-16 items-stretch gap-3 sm:gap-6">
          <Link to="/" className="flex shrink-0 items-center font-mono text-base font-semibold tracking-tight">
            memoize<span className="text-accent">/</span>
          </Link>

          <nav className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
            {BROWSE.map((item) => <Tab key={item.to} {...item} />)}
            <span aria-hidden className="mx-2 my-4 w-px shrink-0 bg-line sm:mx-3" />
            {DO.map((item) => <Tab key={item.to} {...item} accent />)}
          </nav>

          {/* Search belongs in the chrome, not only on the home page — on a
              question bank it is the most-used control on every screen. */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const term = q.trim()
              navigate(term ? `/problems?search=${encodeURIComponent(term)}` : '/problems')
            }}
            className="hidden shrink-0 items-center self-center lg:flex"
          >
            <label htmlFor="nav-search" className="sr-only">Search problems</label>
            <input
              id="nav-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="search problems"
              className="field w-52 py-1.5 font-mono text-micro"
            />
          </form>

          <Account />
        </div>
      </header>

      <Claimed />

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="shell flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 py-8">
          <p className="font-mono text-micro text-ink3">
            community-maintained · every contributed question is labelled and scored
          </p>
          <p className="font-mono text-micro text-ink3">
            solutions run in a sandbox · up to 11 languages
          </p>
        </div>
        {/* Attribution, not a feature callout — curated statements, signatures
            and worked examples are not ours, and saying so is the difference
            between reuse and passing it off. One line: a legal note earns a
            footer's last line, not a paragraph competing with the site. The
            row above already says contributed questions are labelled. */}
        <div className="shell border-t border-line py-4">
          <p className="font-mono text-micro leading-relaxed text-ink3">
            Curated questions sourced from{' '}
            <a href="https://leetcode.com" target="_blank" rel="noopener noreferrer"
               className="link">LeetCode</a>
            {' '}and remain their owners' property · Memoize is not affiliated with
            or endorsed by LeetCode
          </p>
        </div>
      </footer>
    </div>
  )
}

/**
 * "Your work came with you."
 *
 * The whole reason `session_id` was stored before accounts existed, and
 * invisible unless it is said out loud — somebody who solved two problems
 * signed out has no way to tell whether signing in kept them.
 */
function Claimed() {
  const { claimed, dismissClaimed } = useAuth()
  if (!claimed) return null

  const parts = [
    claimed.submissions && `${claimed.submissions} ${claimed.submissions === 1 ? 'run' : 'runs'}`,
    claimed.contributions && `${claimed.contributions} ${claimed.contributions === 1 ? 'contribution' : 'contributions'}`,
    claimed.problems && `${claimed.problems} ${claimed.problems === 1 ? 'problem you added' : 'problems you added'}`,
  ].filter(Boolean) as string[]

  return (
    <div className="border-b border-line bg-panel">
      <div className="shell flex items-center gap-4 py-2.5">
        <p className="font-mono text-micro text-ink2">
          Moved to your account: {parts.join(' · ')}.
        </p>
        <button
          onClick={dismissClaimed}
          className="tap ml-auto shrink-0 px-1 font-mono text-micro text-ink3 hover:text-ink"
        >
          dismiss
        </button>
      </div>
    </div>
  )
}

/**
 * Sign in, or who you are.
 *
 * Renders nothing at all while the first /auth/me is in flight. A "sign in"
 * link that flickers into an avatar on every page load looks broken, and the
 * gap is one request long.
 */
function Account() {
  const { user, loading, signOut } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', esc)
    }
  }, [open])

  if (loading) return <span className="w-16 shrink-0" aria-hidden />

  if (!user) {
    // Carry where they were, so signing in returns them rather than dumping
    // them on the home page.
    const next = encodeURIComponent(location.pathname + location.search)
    return (
      <Link
        to={`/signin?next=${next}`}
        className="flex shrink-0 items-center self-center px-2 font-mono text-small text-ink2 transition-colors hover:text-ink"
      >
        sign in
      </Link>
    )
  }

  return (
    <div ref={box} className="relative shrink-0 self-center">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex min-h-8 items-center gap-2 px-1 font-mono text-micro text-ink2 transition-colors hover:text-ink"
      >
        {user.avatar_url
          ? <img src={user.avatar_url} alt="" width={24} height={24} className="h-6 w-6 shrink-0 border border-line" />
          : <span aria-hidden className="grid h-6 w-6 shrink-0 place-items-center border border-line bg-raised text-ink2">
              {user.display_name.slice(0, 1).toUpperCase()}
            </span>}
        <span className="hidden max-w-[8rem] truncate sm:inline">{user.display_name}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-30 mt-2 w-56 border border-lineStrong bg-panel py-1"
        >
          <p className="truncate px-3 py-2 font-mono text-micro text-ink3">{user.email}</p>
          {!user.email_verified && (
            <p className="border-y border-line bg-medium/5 px-3 py-2 text-micro leading-relaxed text-medium">
              Address not confirmed yet — check your inbox.
            </p>
          )}
          <Link
            to="/problems" role="menuitem" onClick={() => setOpen(false)}
            className="block px-3 py-2 font-mono text-micro text-ink2 hover:bg-raised hover:text-ink"
          >
            my progress
          </Link>
          <button
            role="menuitem"
            onClick={() => { setOpen(false); void signOut() }}
            className="block w-full px-3 py-2 text-left font-mono text-micro text-ink2 hover:bg-raised hover:text-ink"
          >
            sign out
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * A real tab: the active underline sits flush on the header's bottom rule
 * rather than floating above it, so the two rules meet instead of stacking.
 */
function Tab({ to, label, accent, narrow = true }:
             { to: string; label: string; accent?: boolean; narrow?: boolean }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative flex shrink-0 items-center px-2.5 font-mono text-small transition-colors sm:px-3
         ${narrow ? '' : 'hidden sm:flex'}
         after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:transition-colors
         ${isActive
           ? 'text-ink after:bg-accent'
           : `after:bg-transparent hover:text-ink ${accent ? 'text-ink2' : 'text-ink3'}`}`
      }
    >
      {label}
    </NavLink>
  )
}
