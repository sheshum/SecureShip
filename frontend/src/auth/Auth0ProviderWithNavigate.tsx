import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Auth0Provider, type AppState } from '@auth0/auth0-react'

function readStringEnv(name: string): string {
  const value = Reflect.get(import.meta.env, name)
  return typeof value === 'string' ? value : ''
}

export function Auth0ProviderWithNavigate({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const domain = readStringEnv('VITE_AUTH0_DOMAIN')
  const clientId = readStringEnv('VITE_AUTH0_CLIENT_ID')
  const audience = readStringEnv('VITE_AUTH0_AUDIENCE')

  const onRedirectCallback = (appState?: AppState) => {
    void navigate(appState?.returnTo ?? window.location.pathname)
  }

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience,
      }}
      onRedirectCallback={onRedirectCallback}
    >
      {children}
    </Auth0Provider>
  )
}
