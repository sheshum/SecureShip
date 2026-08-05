import { useState } from 'react'
import {
  useCreateShipmentApiShipmentsPost,
  useDeleteShipmentApiShipmentsShipmentIdDelete,
  useListShipmentsApiShipmentsGet,
  useUpdateShipmentApiShipmentsShipmentIdPatch,
} from '../../api/generated/client'
import type {
  ShipmentCreateRequestStatus,
  ShipmentItem,
  ShipmentUpdateRequestStatus,
} from '../../api/generated/schemas'
import { DataTable } from './DataTable'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { ShipmentFormModal, type ShipmentFormValues } from './ShipmentFormModal'

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

  const [formState, setFormState] = useState<{ row?: ShipmentItem } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [deletingRow, setDeletingRow] = useState<ShipmentItem | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: response, isLoading, refetch } = useListShipmentsApiShipmentsGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
  })
  const data = (response?.data && 'shipments' in response.data) ? response.data.shipments : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const createMutation = useCreateShipmentApiShipmentsPost()
  const updateMutation = useUpdateShipmentApiShipmentsShipmentIdPatch()
  const deleteMutation = useDeleteShipmentApiShipmentsShipmentIdDelete()

  const handleSubmit = async (values: ShipmentFormValues) => {
    setFormError(null)
    try {
      if (formState?.row) {
        await updateMutation.mutateAsync({
          shipmentId: formState.row.id,
          data: {
            tracking_number: values.tracking_number,
            status: values.status as ShipmentUpdateRequestStatus,
            carrier: values.carrier,
            origin: values.origin,
            destination: values.destination,
            estimated_delivery: values.estimated_delivery,
          },
        })
      } else {
        await createMutation.mutateAsync({
          data: {
            customer_id: values.customer_id,
            tracking_number: values.tracking_number,
            status: values.status as ShipmentCreateRequestStatus,
            carrier: values.carrier,
            origin: values.origin,
            destination: values.destination,
            estimated_delivery: values.estimated_delivery,
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
      await deleteMutation.mutateAsync({ shipmentId: deletingRow.id })
      setDeletingRow(null)
      await refetch()
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : 'Something went wrong')
    }
  }

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
    {
      header: 'Actions',
      key: 'actions',
      accessor: (row: ShipmentItem) => (
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
          <h2 className="text-lg font-semibold text-slate-900">Shipments</h2>
          <p className="text-sm text-slate-500">All shipments across all customers</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setFormError(null)
            setFormState({})
          }}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          + Add Shipment
        </button>
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

      <ShipmentFormModal
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
        resourceLabel={deletingRow ? `shipment ${deletingRow.tracking_number}` : 'shipment'}
        onConfirm={handleDelete}
        onClose={() => setDeletingRow(null)}
      />
    </div>
  )
}
