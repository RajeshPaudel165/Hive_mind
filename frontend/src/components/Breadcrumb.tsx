import { Link, useLocation } from 'react-router-dom'
import './Breadcrumb.css'

export function Breadcrumb() {
  const location = useLocation()

  const breadcrumbs = generateBreadcrumbs(location.pathname)

  return (
    <nav className="breadcrumb" aria-label="Breadcrumb">
      <ol className="breadcrumb-list">
        {breadcrumbs.map((crumb, index) => (
          <li key={crumb.path}>
            {index < breadcrumbs.length - 1 ? (
              <>
                <Link to={crumb.path} className="breadcrumb-link">
                  {crumb.label}
                </Link>
                <span className="breadcrumb-separator">/</span>
              </>
            ) : (
              <span className="breadcrumb-current">{crumb.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

function generateBreadcrumbs(
  pathname: string,
): Array<{ path: string; label: string }> {
  const pathnames = pathname.split('/').filter((x) => x)

  const breadcrumbs: Array<{ path: string; label: string }> = [
    { path: '/dashboard', label: 'Dashboard' },
  ]

  let currentPath = ''

  for (let i = 0; i < pathnames.length; i++) {
    const segment = pathnames[i]
    currentPath += `/${segment}`

    const label = getBreadcrumbLabel(segment)

    if (label && currentPath !== '/dashboard') {
      breadcrumbs.push({ path: currentPath, label })
    }
  }

  return breadcrumbs
}

function getBreadcrumbLabel(segment: string): string {
  const labels: Record<string, string> = {
    'new': 'New Agent',
    'settings': 'Settings',
    'profile': 'Profile',
    'api': 'API Keys',
    'telegram': 'Telegram Settings',
  }

  return labels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1)
}
