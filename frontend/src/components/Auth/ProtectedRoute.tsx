import { useState, useEffect, type ReactNode } from 'react'
import { useAuth0 } from '@auth0/auth0-react'

function decodeTokenPermissions(token: string): string[] {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return Array.isArray(payload.permissions) ? (payload.permissions as string[]) : []
  } catch {
    return []
  }
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading, loginWithRedirect, getAccessTokenSilently } = useAuth0()
  const [permitted, setPermitted] = useState<boolean | null>(null)

  useEffect(() => {
    if (!isAuthenticated) return
    getAccessTokenSilently()
      .then((token) => {
        const permissions = decodeTokenPermissions(token)
        console.debug('[ProtectedRoute] token permissions:', permissions)
        setPermitted(permissions.includes('admin:all'))
      })
      .catch((err) => {
        console.error('[ProtectedRoute] getAccessTokenSilently failed:', err)
        setPermitted(false)
      })
  }, [isAuthenticated, getAccessTokenSilently])

  if (isLoading || (isAuthenticated && permitted === null)) {
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

  if (!permitted) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
        Access denied.
      </div>
    )
  }

  return <>{children}</>
}
