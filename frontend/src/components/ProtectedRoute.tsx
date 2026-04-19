import type { ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

type ProtectedRouteProps = {
  isLoggedIn: boolean
  children: ReactElement
}

export function ProtectedRoute({
  isLoggedIn,
  children,
}: ProtectedRouteProps) {
  const location = useLocation()

  if (!isLoggedIn) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}
