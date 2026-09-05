import Reconstruct from './pages/Reconstruct'

export default function App() {
  return (
    <div className="min-h-screen bg-floralWhite text-prussianBlue font-sans selection:bg-amberEarth selection:text-prussianBlue">
      <header className="border-b-2 border-shadowGrey/10 bg-floralWhite sticky top-0 z-10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 bg-brownRed rounded-sm" />
          <h1 className="font-bold text-lg tracking-tight uppercase text-prussianBlue">Recollect</h1>
        </div>
      </header>
      <Reconstruct />
    </div>
  )
}

