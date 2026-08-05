import { Routes, Route, Navigate } from 'react-router-dom'
import { WelcomePage } from './pages/WelcomePage'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import { ProtectedRoute } from './components/Auth/ProtectedRoute'
import { RedirectIfAuthenticated } from './components/Auth/RedirectIfAuthenticated'
import { Auth0ProviderWithNavigate } from './auth/Auth0ProviderWithNavigate'
import { Auth0TokenBridge } from './auth/Auth0TokenBridge'
import { AppRoutes } from './lib/routes'

function App() {
  return (
    <Auth0ProviderWithNavigate>
      <Auth0TokenBridge />
      <Routes>
        <Route
          path={AppRoutes.Home}
          element={
            <RedirectIfAuthenticated>
              <WelcomePage />
            </RedirectIfAuthenticated>
          }
        />
        <Route
          path={AppRoutes.Chat}
          element={
            <RedirectIfAuthenticated>
              <ChatPage />
            </RedirectIfAuthenticated>
          }
        />
        <Route
          path={AppRoutes.Dashboard}
          element={
            <ProtectedRoute>
              <AdminPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to={AppRoutes.Home} replace />} />
      </Routes>
    </Auth0ProviderWithNavigate>
  )
}

export default App
