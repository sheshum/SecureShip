import { useNavigate } from 'react-router-dom'

export function AdminPage() {
  const navigate = useNavigate()

  return (
    <main className="relative min-h-screen overflow-hidden bg-[url('/secure-ship-background.jpeg')] bg-cover bg-fixed bg-center px-2 py-3 sm:px-4 sm:py-4">
      <div className="pointer-events-none absolute inset-0 bg-slate-950/38" aria-hidden="true" />

      <div className="relative mx-auto flex min-h-[calc(100svh-1.5rem)] w-full max-w-6xl flex-col gap-4 rounded-[2rem] border border-white/35 bg-slate-100/72 p-3 shadow-[0_30px_90px_rgba(15,23,42,0.34)] backdrop-blur-2xl sm:min-h-[calc(100svh-2rem)] sm:gap-5 sm:p-5">
        <section className="flex min-h-[calc(100svh-4.5rem)] w-full flex-col rounded-[1.6rem] border border-white/70 bg-white/84 shadow-[0_24px_80px_rgba(15,23,42,0.14)] backdrop-blur-xl">
          <header className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 sm:px-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Admin Dashboard</p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              ← Back to Home
            </button>
          </header>

          <div className="flex flex-1 items-center justify-center p-8">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
              <p className="mt-3 text-slate-600">Coming soon...</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}
