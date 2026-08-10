import { useState } from 'react'
import {
  useCreateCustomerApiCustomersPost,
  useDeleteCustomerApiCustomersCustomerIdDelete,
  useListCustomersApiCustomersGet,
  useUpdateCustomerApiCustomersCustomerIdPatch,
} from '../../api/generated/client'
import type { CustomerItem } from '../../api/generated/schemas'
import { useDebounce } from '../../lib/useDebounce'
import { CustomerFormModal, type CustomerFormValues } from './CustomerFormModal'
import { DataTable } from './DataTable'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { TableSearchInput } from './TableSearchInput'

const ITEMS_PER_PAGE = 10

type CustomersTableProps = {
  initialCustomerId?: string
  onNavigateToShipments?: (customerId: string) => void
}

function buildCustomerColumns({
  onNavigateToShipments,
  onEdit,
  onDelete,
}: {
  onNavigateToShipments?: (customerId: string) => void
  onEdit: (row: CustomerItem) => void
  onDelete: (row: CustomerItem) => void
}) {
  return [
    {
      header: 'First Name',
      key: 'first_name',
      accessor: (row: CustomerItem) => row.first_name,
    },
    {
      header: 'Last Name',
      key: 'last_name',
      accessor: (row: CustomerItem) => row.last_name,
    },
    {
      header: 'Phone Number',
      key: 'phone_number',
      accessor: (row: CustomerItem) => row.phone_number,
    },
    {
      header: 'Address',
      key: 'address',
      accessor: (row: CustomerItem) => (
        <span className="max-w-xs truncate" title={row.address}>
          {row.address}
        </span>
      ),
    },
    {
      header: 'Actions',
      key: 'actions',
      accessor: (row: CustomerItem) => (
        <div className="flex gap-2">
          {onNavigateToShipments && (
            <button
              type="button"
              onClick={() => onNavigateToShipments(row.id)}
              className="rounded-lg px-2 py-1 text-xs font-semibold text-sky-700 transition hover:bg-sky-50"
            >
              Shipments →
            </button>
          )}
          <button
            type="button"
            onClick={() => onEdit(row)}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onDelete(row)}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-[#b3432b] transition hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      ),
    },
  ]
}

export function CustomersTable({ initialCustomerId, onNavigateToShipments }: CustomersTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedQuery = useDebounce(searchQuery, 300)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    setCurrentPage(1)
  }

  const [formState, setFormState] = useState<{ row?: CustomerItem } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [deletingRow, setDeletingRow] = useState<CustomerItem | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: response, isLoading, refetch } = useListCustomersApiCustomersGet({
    limit: ITEMS_PER_PAGE,
    offset,
    q: debouncedQuery || undefined,
    customer_id: initialCustomerId || undefined,
  })
  const data = (response?.data && 'customers' in response.data) ? response.data.customers : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const createMutation = useCreateCustomerApiCustomersPost()
  const updateMutation = useUpdateCustomerApiCustomersCustomerIdPatch()
  const deleteMutation = useDeleteCustomerApiCustomersCustomerIdDelete()

  const handleSubmit = async (values: CustomerFormValues) => {
    setFormError(null)
    try {
      if (formState?.row) {
        await updateMutation.mutateAsync({ customerId: formState.row.id, data: values })
      } else {
        await createMutation.mutateAsync({ data: values })
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
      await deleteMutation.mutateAsync({ customerId: deletingRow.id })
      setDeletingRow(null)
      await refetch()
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : 'Something went wrong')
    }
  }

  const columns = buildCustomerColumns({
    onNavigateToShipments,
    onEdit: (row) => {
      setFormError(null)
      setFormState({ row })
    },
    onDelete: (row) => {
      setDeleteError(null)
      setDeletingRow(row)
    },
  })

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Customers</h2>
          <p className="text-sm text-slate-500">All registered customers</p>
        </div>
        {!initialCustomerId && (
          <div className="flex items-center gap-3">
            <TableSearchInput
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search customers…"
            />
            <button
              type="button"
              onClick={() => {
                setFormError(null)
                setFormState({})
              }}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              + Add Customer
            </button>
          </div>
        )}
      </div>
      {initialCustomerId && (
        <div className="mb-3 flex items-center rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-800">
          <span>Showing customer from session</span>
        </div>
      )}
      <DataTable
        data={data}
        columns={columns}
        getRowKey={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No customers found"
        pagination={{
          currentPage,
          totalItems: total,
          itemsPerPage: ITEMS_PER_PAGE,
          onPageChange: setCurrentPage,
        }}
      />

      {formState !== null && (
        <CustomerFormModal
          isSubmitting={createMutation.isPending || updateMutation.isPending}
          errorMessage={formError}
          initialValues={formState.row}
          onSubmit={handleSubmit}
          onClose={() => setFormState(null)}
        />
      )}

      {deletingRow !== null && (
        <DeleteConfirmModal
          isDeleting={deleteMutation.isPending}
          errorMessage={deleteError}
          resourceLabel={`${deletingRow.first_name} ${deletingRow.last_name}`}
          onConfirm={handleDelete}
          onClose={() => setDeletingRow(null)}
        />
      )}
    </div>
  )
}
