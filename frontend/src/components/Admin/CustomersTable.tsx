import { useState } from 'react'
import {
  useCreateCustomerApiCustomersPost,
  useDeleteCustomerApiCustomersCustomerIdDelete,
  useListCustomersApiCustomersGet,
  useUpdateCustomerApiCustomersCustomerIdPatch,
} from '../../api/generated/client'
import type { CustomerItem } from '../../api/generated/schemas'
import { CustomerFormModal, type CustomerFormValues } from './CustomerFormModal'
import { DataTable } from './DataTable'
import { DeleteConfirmModal } from './DeleteConfirmModal'

const ITEMS_PER_PAGE = 10

export function CustomersTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE

  const [formState, setFormState] = useState<{ row?: CustomerItem } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [deletingRow, setDeletingRow] = useState<CustomerItem | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: response, isLoading, refetch } = useListCustomersApiCustomersGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
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

  const columns = [
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
          <h2 className="text-lg font-semibold text-slate-900">Customers</h2>
          <p className="text-sm text-slate-500">All registered customers</p>
        </div>
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
      <DataTable
        data={data}
        columns={columns}
        isLoading={isLoading}
        emptyMessage="No customers found"
        pagination={{
          currentPage,
          totalItems: total,
          itemsPerPage: ITEMS_PER_PAGE,
          onPageChange: setCurrentPage,
        }}
      />

      <CustomerFormModal
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
        resourceLabel={deletingRow ? `${deletingRow.first_name} ${deletingRow.last_name}` : 'customer'}
        onConfirm={handleDelete}
        onClose={() => setDeletingRow(null)}
      />
    </div>
  )
}
