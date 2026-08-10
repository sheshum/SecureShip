import { useNavigate } from 'react-router-dom'
import { AppRoutes } from '../lib/routes'

export function WelcomePage() {
  const navigate = useNavigate()

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative w-full max-w-2xl rounded-3xl border border-slate-200/90 bg-white/90 px-8 py-12 shadow-[0_16px_46px_rgba(15,23,42,0.08)] backdrop-blur-sm sm:px-12 sm:py-16">
        <div className="text-center">
          <img
            src="/Logo3_wide.png"
            alt="SecureShipAI"
            className="mx-auto mb-2 h-auto w-56 sm:w-64"
          />
          <h1 className="mt-4 text-2xl font-light tracking-tight text-slate-700 sm:text-3xl">
            Welcome back
          </h1>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            Start a new conversation to track your shipment, or head to the admin dashboard.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <button
              type="button"
              onClick={() => navigate(AppRoutes.Chat)}
              className="rounded-lg bg-slate-700 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
            >
              Start new chat
            </button>
            <button
              type="button"
              onClick={() => navigate(AppRoutes.Dashboard)}
              className="rounded-lg border border-slate-300 bg-white px-6 py-3 font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
            >
              Admin Dashboard
            </button>
          </div>
        </div>
      </div>
    </main>
  )
}
