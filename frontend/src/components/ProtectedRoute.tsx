import type { ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

type ProtectedRouteProps = {
  isLoggedIn: boolean
  authReady: boolean
  children: ReactElement
}

export function ProtectedRoute({
  isLoggedIn,
  authReady,
  children,
}: ProtectedRouteProps) {
  const location = useLocation()

  if (!authReady) {
    return (
      <div className="page-bg">
        <div className="page-shell single-col-shell">
          <section className="card auth-card">
            <p className="eyebrow dark-eyebrow">Loading</p>
            <h1>Preparing your workspace...</h1>
          </section>
        </div>
      </div>
    )
  }

  if (!isLoggedIn) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
