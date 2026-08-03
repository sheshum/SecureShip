type AdminView = 'sessions' | 'shipments' | 'packages'

interface AdminSidebarProps {
  activeView: AdminView
  onNavigate: (view: AdminView) => void
  onBackToHome: () => void
}

const navItems: { value: AdminView; label: string }[] = [
  { value: 'sessions', label: 'Chat Sessions' },
  { value: 'shipments', label: 'Shipments' },
  { value: 'packages', label: 'Packages' },
]

export function AdminSidebar({ activeView, onNavigate, onBackToHome }: AdminSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      {/* Branding */}
      <div className="border-b border-slate-200 px-4 py-6">
        <h1 className="text-xl font-bold tracking-tight text-slate-900">SECURESHIP</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 pt-6">
        {navItems.map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => onNavigate(item.value)}
            className={`w-full rounded-lg px-4 py-2.5 text-left text-sm font-medium transition ${
              activeView === item.value
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* Back to Home */}
      <div className="border-t border-slate-200 p-4">
        <button
          type="button"
          onClick={onBackToHome}
          className="w-full rounded-lg px-4 py-2.5 text-left text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
        >
          ← Back to chat
        </button>
      </div>
    </div>
  )
}
