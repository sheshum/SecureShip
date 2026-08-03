import { useState } from 'react'
import { useListShipmentsApiShipmentsGet } from '../../api/generated/client'
import type { ShipmentItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'

const ITEMS_PER_PAGE = 10

const statusColors: Record<string, string> = {
  delivered: 'bg-green-100 text-green-800',
  in_transit: 'bg-blue-100 text-blue-800',
  out_for_delivery: 'bg-blue-100 text-blue-800',
  label_created: 'bg-slate-100 text-slate-700',
  exception: 'bg-orange-100 text-orange-800',
}

export function ShipmentsTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE
  
  const { data: response, isLoading } = useListShipmentsApiShipmentsGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
  })
  const data = (response?.data && 'shipments' in response.data) ? response.data.shipments : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const columns = [
    {
      header: 'Tracking #',
      key: 'tracking_number',
      accessor: (row: ShipmentItem) => (
        <span className="font-mono text-xs font-semibold">{row.tracking_number}</span>
      ),
    },
    {
      header: 'Customer',
      key: 'customer_name',
      accessor: (row: ShipmentItem) => row.customer_name || '—',
    },
    {
      header: 'Status',
      key: 'status',
      accessor: (row: ShipmentItem) => (
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium capitalize ${statusColors[row.status] || 'bg-slate-100 text-slate-700'}`}
        >
          {row.status.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      header: 'Carrier',
      key: 'carrier',
      accessor: (row: ShipmentItem) => row.carrier,
    },
    {
      header: 'Route',
      key: 'route',
      accessor: (row: ShipmentItem) => (
        <span className="text-xs">
          {row.origin} → {row.destination}
        </span>
      ),
    },
    {
      header: 'Est. Delivery',
      key: 'estimated_delivery',
      accessor: (row: ShipmentItem) => new Date(row.estimated_delivery).toLocaleDateString(),
    },
    {
      header: 'Packages',
      key: 'package_count',
      accessor: (row: ShipmentItem) => (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
          {row.package_count}
        </span>
      ),
    },
  ]

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Shipments</h2>
        <p className="text-sm text-slate-500">All shipments across all customers</p>
      </div>
      <DataTable 
        data={data} 
        columns={columns} 
        isLoading={isLoading} 
        emptyMessage="No shipments found"
        pagination={{
          currentPage,
          totalItems: total,
          itemsPerPage: ITEMS_PER_PAGE,
          onPageChange: setCurrentPage,
        }}
      />
    </div>
  )
}
