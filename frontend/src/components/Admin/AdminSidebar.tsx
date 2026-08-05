type AdminView = 'sessions' | 'shipments' | 'packages' | 'customers'

interface AdminSidebarProps {
  activeView: AdminView
  onNavigate: (view: AdminView) => void
  userEmail?: string
  onLogout: () => void
}

const navItems: { value: AdminView; label: string }[] = [
  { value: 'sessions', label: 'Chat Sessions' },
  { value: 'customers', label: 'Customers' },
  { value: 'shipments', label: 'Shipments' },
  { value: 'packages', label: 'Packages' },
]

export function AdminSidebar({ activeView, onNavigate, userEmail, onLogout }: AdminSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      {/* Branding */}
      <div className="border-b border-slate-200 px-4 py-3">
        <img src="/Logo3_wide.png" alt="SecureShipAI" className="h-16 w-auto" />
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

      {/* Account / Logout */}
      <div className="border-t border-slate-200 p-4">
        {userEmail && <p className="mb-2 truncate px-4 text-s text-slate-500">{userEmail}</p>}
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-lg px-4 py-2.5 text-left text-sm font-semibold text-slate-700 transition hover:bg-slate-100 hover:text-slate-900"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1" />
          </svg>
          Log out
        </button>
      </div>
    </div>
  )
}
