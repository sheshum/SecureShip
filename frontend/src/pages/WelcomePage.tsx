import { useNavigate } from 'react-router-dom'

export function WelcomePage() {
  const navigate = useNavigate()

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-[calc(100svh-1.5rem)] w-full max-w-6xl items-center justify-center rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:min-h-[calc(100svh-2rem)] sm:p-5">
        <div className="w-full max-w-2xl rounded-3xl border border-slate-200/90 bg-white/90 px-8 py-12 shadow-[0_16px_46px_rgba(15,23,42,0.08)] backdrop-blur-sm sm:px-12 sm:py-16">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              SecureShip Assistant
            </p>
            <h1 className="mt-4 text-3xl font-bold text-slate-900 sm:text-4xl">
              Welcome back
            </h1>
            <p className="mt-4 text-base text-slate-600 sm:text-lg">
              Start a new conversation to track your shipment, or head to the admin dashboard.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <button
                type="button"
                onClick={() => navigate('/chat')}
                className="rounded-lg bg-slate-700 px-6 py-3 font-medium text-white shadow-sm transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
              >
                Start new chat
              </button>
              <button
                type="button"
                onClick={() => navigate('/admin')}
                className="rounded-lg border border-slate-300 bg-white px-6 py-3 font-medium text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
              >
                Admin Dashboard
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
