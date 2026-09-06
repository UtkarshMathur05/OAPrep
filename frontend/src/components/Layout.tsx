import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { getFacets } from '../services/api'

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
  const [total, setTotal] = useState<number | null>(null)

  useEffect(() => {
    getFacets().then((f) => setTotal(f.totals.problems)).catch(() => setTotal(null))
  }, [])

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

          {/* Quiet context rather than a second call to action. The nav already
              has 'recall'; a button repeating it was the loudest redundant
              thing on every page. */}
          <span className="hidden shrink-0 items-center font-mono text-micro text-ink3 lg:flex">
            {total ? `${total.toLocaleString()} problems indexed` : ''}
          </span>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="shell flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 py-8">
          <p className="font-mono text-micro text-ink3">
            statements from LeetCode · community problems labelled and scored
          </p>
          <p className="font-mono text-micro text-ink3">
            hackathon build · python executed on Judge0
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
