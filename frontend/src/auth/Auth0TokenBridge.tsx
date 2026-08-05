import { useEffect } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { setTokenGetter } from '../api/authToken'

export function Auth0TokenBridge() {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0()

  useEffect(() => {
    setTokenGetter(isAuthenticated ? getAccessTokenSilently : null)
    return () => setTokenGetter(null)
  }, [isAuthenticated, getAccessTokenSilently])

  return null
}
