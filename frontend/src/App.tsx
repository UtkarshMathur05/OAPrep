import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Browse from './pages/Browse'
import Directory from './pages/Directory'
import ProblemPage from './pages/ProblemPage'
import Reconstruct from './pages/Reconstruct'
import Contribute from './pages/Contribute'
import Solve from './pages/Solve'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Everything inside the site shell. */}
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="problems" element={<Browse />} />
          <Route path="problems/:slug" element={<ProblemPage />} />
          <Route path="companies" element={<Directory axis="company" />} />
          <Route path="topics" element={<Directory axis="topic" />} />
          <Route path="recall" element={<Reconstruct />} />
          <Route path="contribute" element={<Contribute />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        {/* Outside it: the editor takes the whole screen. */}
        <Route path="solve/:slug" element={<Solve />} />
      </Routes>
    </BrowserRouter>
  )
}

function NotFound() {
  return (
    <div className="mx-auto max-w-reading px-5 py-20">
      <h1 className="text-2xl font-semibold tracking-tight">No such page</h1>
      <p className="mt-2 text-muted">
        Try <a href="/problems" className="text-brownRed underline underline-offset-2">the problem list</a>.
      </p>
    </div>
  )
}
