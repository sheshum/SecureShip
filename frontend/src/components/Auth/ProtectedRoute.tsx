import type { ReactNode } from 'react'
import { useAuth0 } from '@auth0/auth0-react'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Loading…
      </div>
    )
  }

  if (!isAuthenticated) {
    void loginWithRedirect({ appState: { returnTo: window.location.pathname } })
    return null
  }

  return <>{children}</>
}
