import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

/**
 * Two groups, not five equal links.
 *
 * Browsing a corpus is what every OA site does; recalling a problem you cannot
 * name is the only thing this one does. Flattening both into one row of
 * identical links said they were the same kind of thing. A rule between them
 * says they are not, and costs nothing.
 */
const BROWSE = [
  { to: '/problems', label: 'problems' },
  { to: '/companies', label: 'companies' },
  { to: '/topics', label: 'topics' },
]
const DO = [
  { to: '/recall', label: 'recall' },
  { to: '/contribute', label: 'contribute' },
]

export default function Layout() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-20 border-b border-lineStrong bg-ground/95 backdrop-blur">
        <div className="shell flex h-16 items-stretch gap-6">
          <Link to="/" className="flex shrink-0 items-center font-mono text-base font-semibold tracking-tight">
            memoize<span className="text-accent">/</span>
          </Link>

          <nav className="flex min-w-0 flex-1 items-stretch overflow-x-auto">
            {BROWSE.map((item) => <Tab key={item.to} {...item} />)}
            <span aria-hidden className="my-4 mx-3 w-px shrink-0 bg-line" />
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
            className="hidden shrink-0 items-center self-center md:flex"
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
        </div>
      </header>

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
 * A real tab: the active underline sits flush on the header's bottom rule
 * rather than floating above it, so the two rules meet instead of stacking.
 */
function Tab({ to, label, accent }: { to: string; label: string; accent?: boolean }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative flex shrink-0 items-center px-3 font-mono text-small transition-colors
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
