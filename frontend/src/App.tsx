import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { WelcomePage } from './pages/WelcomePage'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<WelcomePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
