import { useState } from 'react'
import { useListCustomersApiCustomersGet } from '../../api/generated/client'
import type { CustomerItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'

const ITEMS_PER_PAGE = 10

export function CustomersTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE

  const { data: response, isLoading } = useListCustomersApiCustomersGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
  })
  const data = (response?.data && 'customers' in response.data) ? response.data.customers : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

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
  ]

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Customers</h2>
        <p className="text-sm text-slate-500">All registered customers</p>
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
    </div>
  )
}
