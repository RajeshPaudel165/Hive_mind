import { Link, useLocation } from 'react-router-dom'
import './Sidebar.css'

type SidebarProps = {
  userEmail: string
  onLogout: () => void
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ userEmail, onLogout, isOpen = true, onClose }: SidebarProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  const handleLogout = () => {
    onClose?.()
    onLogout()
  }

  return (
    <>
      {/* Mobile overlay */}
      {!isOpen && (
        <div className="sidebar-overlay" onClick={onClose} />
      )}

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Mobile close button */}
        <button
          className="sidebar-close"
          onClick={onClose}
          aria-label="Close sidebar"
        >
          ✕
        </button>

        {/* Logo */}
        <div className="sidebar-header">
          <Link to="/dashboard" className="sidebar-logo">
            HiveMind
          </Link>
        </div>

        {/* User Info */}
        <div className="sidebar-user">
          <div className="user-avatar">
            {userEmail.charAt(0).toUpperCase()}
          </div>
          <div className="user-info">
            <p className="user-email">{userEmail}</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <ul>
            <li>
              <Link
                to="/dashboard"
                className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
                onClick={onClose}
              >
                <span className="nav-icon">📊</span>
                <span className="nav-label">Dashboard</span>
              </Link>
            </li>
            <li>
              <Link
                to="/agents/new"
                className={`nav-link ${isActive('/agents/new') ? 'active' : ''}`}
                onClick={onClose}
              >
                <span className="nav-icon">➕</span>
                <span className="nav-label">New Agent</span>
              </Link>
            </li>
            <li>
              <Link
                to="/settings/profile"
                className={`nav-link ${isActive('/settings/profile') ? 'active' : ''}`}
                onClick={onClose}
              >
                <span className="nav-icon">👤</span>
                <span className="nav-label">Profile</span>
              </Link>
            </li>
            <li>
              <Link
                to="/settings/api"
                className={`nav-link ${isActive('/settings/api') ? 'active' : ''}`}
                onClick={onClose}
              >
                <span className="nav-icon">🔑</span>
                <span className="nav-label">API Keys</span>
              </Link>
            </li>
          </ul>
        </nav>

        {/* Logout Button */}
        <button
          className="btn btn-ghost sidebar-logout"
          type="button"
          onClick={handleLogout}
        >
          Logout
        </button>
      </aside>
    </>
  )
}
