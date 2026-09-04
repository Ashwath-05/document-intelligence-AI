import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api'

const NAV_ITEMS = [
  { to: '/', label: 'Upload', icon: '01' },
  { to: '/search', label: 'Search', icon: '02' },
  { to: '/chat', label: 'Chat', icon: '03' },
  { to: '/history', label: 'History', icon: '04' },
]

export default function Sidebar() {
  const [health, setHealth] = useState('checking')

  useEffect(() => {
    api
      .health()
      .then(() => setHealth('online'))
      .catch(() => setHealth('offline'))
  }, [])

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <h1>
          DOC<span className="brand-accent">/</span>INTEL
        </h1>
        <p className="status-line">document intelligence platform</p>
      </div>

      <ul className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
            >
              <span className="sidebar-link-index">{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className={`status-line readout sidebar-status ${health === 'online' ? 'online' : health === 'offline' ? 'error' : ''}`}>
        <span className="status-dot" />
        backend: {health}
      </div>
    </nav>
  )
}
