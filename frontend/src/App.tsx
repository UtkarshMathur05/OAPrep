import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './lib/auth'
import Layout from './components/Layout'
import Home from './pages/Home'
import Browse from './pages/Browse'
import Directory from './pages/Directory'
import ProblemPage from './pages/ProblemPage'
import Reconstruct from './pages/Reconstruct'
import Contribute from './pages/Contribute'
import Solve from './pages/Solve'
import SignIn from './pages/SignIn'
import { ResetPassword, VerifyEmail } from './pages/AuthLink'

export default function App() {
  return (
    <BrowserRouter>
      {/* Inside the router: signing in navigates, so the provider needs to be
          able to use router hooks. Outside <Routes>, so one /auth/me answers
          for every route rather than one per navigation. */}
      <AuthProvider>
        <Routes>
          {/* Everything inside the site shell. */}
          <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="problems" element={<Browse />} />
          <Route path="problems/:slug" element={<ProblemPage />} />
          <Route path="companies" element={<Directory axis="company" />} />
          <Route path="topics" element={<Directory axis="topic" />} />
          <Route path="recall" element={<Reconstruct />} />
          <Route path="contribute" element={<Contribute />} />
          <Route path="signin" element={<SignIn />} />
          {/* Where the emailed links land. */}
          <Route path="auth/verify" element={<VerifyEmail />} />
          <Route path="auth/reset" element={<ResetPassword />} />
          <Route path="*" element={<NotFound />} />
          </Route>

          {/* Outside it: the editor takes the whole screen. */}
          <Route path="solve/:slug" element={<Solve />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

function NotFound() {
  return (
    <div className="mx-auto max-w-reading px-5 py-20">
      <h1 className="text-2xl font-semibold tracking-tight">No such page</h1>
      <p className="mt-2 text-ink2">
        Try <a href="/problems" className="text-link underline underline-offset-2">the problem list</a>.
      </p>
    </div>
  )
}
