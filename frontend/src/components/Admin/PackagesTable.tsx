import { useEffect, useState } from 'react'
import {
  useCreatePackageApiPackagesPost,
  useDeletePackageApiPackagesPackageIdDelete,
  useListPackagesApiPackagesGet,
  useUpdatePackageApiPackagesPackageIdPatch,
} from '../../api/generated/client'
import type { PackageItem } from '../../api/generated/schemas'
import { useDebounce } from '../../lib/useDebounce'
import { DataTable } from './DataTable'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { PackageFormModal, type PackageFormValues } from './PackageFormModal'
import { TableSearchInput } from './TableSearchInput'

const ITEMS_PER_PAGE = 10

type PackagesTableProps = {
  initialShipmentId?: string
}

export function PackagesTable({ initialShipmentId }: PackagesTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [shipmentIdFilter, setShipmentIdFilter] = useState<string | undefined>(initialShipmentId)
  const debouncedQuery = useDebounce(searchQuery, 300)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE

  useEffect(() => {
    setCurrentPage(1)
  }, [debouncedQuery])

  useEffect(() => {
    setCurrentPage(1)
  }, [shipmentIdFilter])

  const [formState, setFormState] = useState<{ row?: PackageItem } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [deletingRow, setDeletingRow] = useState<PackageItem | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: response, isLoading, refetch } = useListPackagesApiPackagesGet({
    limit: ITEMS_PER_PAGE,
    offset,
    q: debouncedQuery || undefined,
    shipment_id: shipmentIdFilter || undefined,
  })
  const data = (response?.data && 'packages' in response.data) ? response.data.packages : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const createMutation = useCreatePackageApiPackagesPost()
  const updateMutation = useUpdatePackageApiPackagesPackageIdPatch()
  const deleteMutation = useDeletePackageApiPackagesPackageIdDelete()

  const handleSubmit = async (values: PackageFormValues) => {
    setFormError(null)
    try {
      if (formState?.row) {
        await updateMutation.mutateAsync({
          packageId: formState.row.id,
          data: {
            description: values.description,
            weight_kg: values.weight_kg,
            declared_value: values.declared_value,
          },
        })
      } else {
        await createMutation.mutateAsync({
          data: {
            tracking_number: values.tracking_number,
            description: values.description,
            weight_kg: values.weight_kg,
            declared_value: values.declared_value,
          },
        })
      }
      setFormState(null)
      await refetch()
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Something went wrong')
    }
  }

  const handleDelete = async () => {
    if (!deletingRow) return
    setDeleteError(null)
    try {
      await deleteMutation.mutateAsync({ packageId: deletingRow.id })
      setDeletingRow(null)
      await refetch()
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : 'Something went wrong')
    }
  }

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
    {
      header: 'Actions',
      key: 'actions',
      accessor: (row: PackageItem) => (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setFormError(null)
              setFormState({ row })
            }}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => {
              setDeleteError(null)
              setDeletingRow(row)
            }}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-[#b3432b] transition hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Packages</h2>
          <p className="text-sm text-slate-500">All packages across all shipments</p>
        </div>
        {!shipmentIdFilter && (
          <div className="flex items-center gap-3">
            <TableSearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder="Search packages…"
            />
            <button
              type="button"
              onClick={() => {
                setFormError(null)
                setFormState({})
              }}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              + Add Package
            </button>
          </div>
        )}
      </div>
      {shipmentIdFilter && (
        <div className="mb-3 flex items-center rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-800">
          <span>Filtered by shipment</span>
          <button
            type="button"
            onClick={() => setShipmentIdFilter(undefined)}
            className="ml-auto text-xs font-semibold text-sky-700 transition hover:text-sky-900"
          >
            Clear ×
          </button>
        </div>
      )}
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

      <PackageFormModal
        isOpen={formState !== null}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
        errorMessage={formError}
        initialValues={formState?.row}
        onSubmit={handleSubmit}
        onClose={() => setFormState(null)}
      />

      <DeleteConfirmModal
        isOpen={deletingRow !== null}
        isDeleting={deleteMutation.isPending}
        errorMessage={deleteError}
        resourceLabel={deletingRow ? `package ${deletingRow.id.substring(0, 8)}...` : 'package'}
        onConfirm={handleDelete}
        onClose={() => setDeletingRow(null)}
      />
    </div>
  )
}
