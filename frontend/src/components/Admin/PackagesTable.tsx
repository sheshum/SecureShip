import { useState } from 'react'
import { useListPackagesApiPackagesGet } from '../../api/generated/client'
import type { PackageItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'

const ITEMS_PER_PAGE = 10

export function PackagesTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE
  
  const { data: response, isLoading } = useListPackagesApiPackagesGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
  })
  const data = (response?.data && 'packages' in response.data) ? response.data.packages : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const columns = [
    {
      header: 'Package ID',
      key: 'id',
      accessor: (row: PackageItem) => (
        <span className="font-mono text-xs">{row.id.substring(0, 8)}...</span>
      ),
    },
    {
      header: 'Shipment Tracking #',
      key: 'shipment_tracking_number',
      accessor: (row: PackageItem) => (
        <span className="font-mono text-xs font-semibold">
          {row.shipment_tracking_number || '—'}
        </span>
      ),
    },
    {
      header: 'Description',
      key: 'description',
      accessor: (row: PackageItem) => (
        <span className="max-w-xs truncate" title={row.description}>
          {row.description}
        </span>
      ),
    },
    {
      header: 'Weight',
      key: 'weight_kg',
      accessor: (row: PackageItem) => `${row.weight_kg} kg`,
    },
    {
      header: 'Declared Value',
      key: 'declared_value',
      accessor: (row: PackageItem) => `$${parseFloat(row.declared_value).toFixed(2)}`,
    },
  ]

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Packages</h2>
        <p className="text-sm text-slate-500">All packages across all shipments</p>
      </div>
      <DataTable 
        data={data} 
        columns={columns} 
        isLoading={isLoading} 
        emptyMessage="No packages found"
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
