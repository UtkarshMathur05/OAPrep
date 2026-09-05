import Reconstruct from './pages/Reconstruct'

export default function App() {
  return (
    <div className="min-h-screen bg-floralWhite text-prussianBlue font-sans
                    selection:bg-amberEarth/30 selection:text-prussianBlue">
      <header className="sticky top-0 z-20 border-b border-ruleStrong bg-floralWhite/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-baseline gap-3 px-5 py-3">
          <span className="text-base font-semibold tracking-tight">Memoize</span>
          <span className="text-sm text-muted">
            Find the problem you half remember
          </span>
        </div>
      </header>
      <Reconstruct />
    </div>
  )
}
