import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import UploadView from './pages/UploadView'
import SearchView from './pages/SearchView'
import ChatView from './pages/ChatView'
import HistoryView from './pages/HistoryView'

function App() {
  // The one orchestrated moment: a brief boot flicker on first load,
  // then everything settles and stays calm. Respects reduced-motion
  // via the CSS media query on .boot-flicker itself.
  const [booted, setBooted] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setBooted(true), 700)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className={`app-shell${booted ? '' : ' boot-flicker'}`}>
      <Sidebar />
      <Routes>
        <Route path="/" element={<UploadView />} />
        <Route path="/search" element={<SearchView />} />
        <Route path="/chat" element={<ChatView />} />
        <Route path="/history" element={<HistoryView />} />
      </Routes>
    </div>
  )
}

export default App
