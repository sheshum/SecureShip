import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { AdminSidebar } from '../components/Admin/AdminSidebar'
import { CustomersTable } from '../components/Admin/CustomersTable'
import { PackagesTable } from '../components/Admin/PackagesTable'
import { SessionsTable } from '../components/Admin/SessionsTable'
import { ShipmentsTable } from '../components/Admin/ShipmentsTable'

type AdminView = 'sessions' | 'shipments' | 'packages' | 'customers'

const VALID_VIEWS: AdminView[] = ['sessions', 'shipments', 'packages', 'customers']

export function AdminPage() {
  const { user, logout } = useAuth0()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get('tab')
  const activeTab: AdminView = VALID_VIEWS.includes(rawTab as AdminView) ? (rawTab as AdminView) : 'sessions'

  const [shipmentCustomerFilter, setShipmentCustomerFilter] = useState<string | undefined>()
  const [packageShipmentFilter, setPackageShipmentFilter] = useState<string | undefined>()
  const [customerIdFilter, setCustomerIdFilter] = useState<string | undefined>()

  const handleLogout = () => logout({ logoutParams: { returnTo: window.location.origin } })

  function handleSidebarNavigate(view: AdminView) {
    setSearchParams({ tab: view })
    setShipmentCustomerFilter(undefined)
    setPackageShipmentFilter(undefined)
    setCustomerIdFilter(undefined)
  }

  function navigateToCustomers(customerId: string) {
    setCustomerIdFilter(customerId)
    setSearchParams({ tab: 'customers' })
  }

  function navigateToShipments(customerId: string) {
    setShipmentCustomerFilter(customerId)
    setSearchParams({ tab: 'shipments' })
  }

  function navigateToPackages(shipmentId: string) {
    setPackageShipmentFilter(shipmentId)
    setSearchParams({ tab: 'packages' })
  }

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white">
        <AdminSidebar
          activeView={activeTab}
          onNavigate={handleSidebarNavigate}
          userEmail={user?.email}
          onLogout={handleLogout}
        />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">SecureShip Dashboard</p>
        </header>

        <div className="flex-1 overflow-y-auto bg-slate-50">
          {activeTab === 'sessions' && (
            <SessionsTable onNavigateToCustomers={navigateToCustomers} />
          )}
          {activeTab === 'shipments' && (
            <ShipmentsTable
              key={shipmentCustomerFilter ?? 'all'}
              initialCustomerId={shipmentCustomerFilter}
              onNavigateToPackages={navigateToPackages}
            />
          )}
          {activeTab === 'packages' && (
            <PackagesTable
              key={packageShipmentFilter ?? 'all'}
              initialShipmentId={packageShipmentFilter}
            />
          )}
          {activeTab === 'customers' && (
            <CustomersTable
              key={customerIdFilter ?? 'all'}
              initialCustomerId={customerIdFilter}
              onNavigateToShipments={navigateToShipments}
            />
          )}
        </div>
      </div>
    </div>
  )
}
