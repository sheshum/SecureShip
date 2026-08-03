import { useListPackagesApiPackagesGet } from '../../api/generated/client'
import type { PackageItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'

export function PackagesTable() {
  const { data: response, isLoading } = useListPackagesApiPackagesGet()
  const data = (response?.data && 'packages' in response.data) ? response.data.packages : []

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
      <DataTable data={data} columns={columns} isLoading={isLoading} emptyMessage="No packages found" />
    </div>
  )
}
