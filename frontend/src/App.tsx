import { BrowserRouter, Route, Routes } from 'react-router-dom'

import Home from './pages/Home'
import Practice from './pages/Practice'
import Reconstruct from './pages/Reconstruct'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/reconstruct" element={<Reconstruct />} />
        <Route path="/practice" element={<Practice />} />
      </Routes>
    </BrowserRouter>
  )
}
