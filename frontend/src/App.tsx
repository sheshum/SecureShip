import { Routes, Route } from 'react-router-dom'
import { WelcomePage } from './pages/WelcomePage'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import { ProtectedRoute } from './components/Auth/ProtectedRoute'
import { RedirectIfAuthenticated } from './components/Auth/RedirectIfAuthenticated'
import { Auth0ProviderWithNavigate } from './auth/Auth0ProviderWithNavigate'
import { Auth0TokenBridge } from './auth/Auth0TokenBridge'

function App() {
  return (
    <Auth0ProviderWithNavigate>
      <Auth0TokenBridge />
      <Routes>
        <Route
          path="/"
          element={
            <RedirectIfAuthenticated>
              <WelcomePage />
            </RedirectIfAuthenticated>
          }
        />
        <Route
          path="/chat"
          element={
            <RedirectIfAuthenticated>
              <ChatPage />
            </RedirectIfAuthenticated>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Auth0ProviderWithNavigate>
  )
}

export default App
