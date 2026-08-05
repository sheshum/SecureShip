import { useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { AdminSidebar } from '../components/Admin/AdminSidebar'
import { CustomersTable } from '../components/Admin/CustomersTable'
import { PackagesTable } from '../components/Admin/PackagesTable'
import { SessionsTable } from '../components/Admin/SessionsTable'
import { ShipmentsTable } from '../components/Admin/ShipmentsTable'

type AdminView = 'sessions' | 'shipments' | 'packages' | 'customers'

export function AdminPage() {
  const { user, logout } = useAuth0()
  const [activeView, setActiveView] = useState<AdminView>('sessions')

  const handleLogout = () => logout({ logoutParams: { returnTo: window.location.origin } })

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white">
        <AdminSidebar
          activeView={activeView}
          onNavigate={setActiveView}
          userEmail={user?.email}
          onLogout={handleLogout}
        />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Admin Dashboard</p>
        </header>

        <div className="flex-1 overflow-y-auto bg-slate-50">
          {activeView === 'sessions' && <SessionsTable />}
          {activeView === 'shipments' && <ShipmentsTable />}
          {activeView === 'packages' && <PackagesTable />}
          {activeView === 'customers' && <CustomersTable />}
        </div>
      </div>
    </div>
  )
}
