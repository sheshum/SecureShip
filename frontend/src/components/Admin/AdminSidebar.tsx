type AdminView = 'sessions' | 'shipments' | 'packages'

interface AdminSidebarProps {
  activeView: AdminView
  onNavigate: (view: AdminView) => void
}

const navItems: { value: AdminView; label: string }[] = [
  { value: 'sessions', label: 'Chat Sessions' },
  { value: 'shipments', label: 'Shipments' },
  { value: 'packages', label: 'Packages' },
]

export function AdminSidebar({ activeView, onNavigate }: AdminSidebarProps) {
  return (
    <nav className="space-y-1">
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
  )
}
