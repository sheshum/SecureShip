import { useState } from 'react'
import { useListSessionsApiSessionsGet } from '../../api/generated/client'
import type { SessionItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'

const ITEMS_PER_PAGE = 10

export function SessionsTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const offset = (currentPage - 1) * ITEMS_PER_PAGE
  
  const { data: response, isLoading } = useListSessionsApiSessionsGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
  })
  const data = (response?.data && 'sessions' in response.data) ? response.data.sessions : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0

  const columns = [
    {
      header: 'Session ID',
      key: 'id',
      accessor: (row: SessionItem) => (
        <span className="font-mono text-xs">{row.id.substring(0, 8)}...</span>
      ),
    },
    {
      header: 'State',
      key: 'state',
      accessor: (row: SessionItem) => (
        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium capitalize text-slate-700">
          {row.state.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      header: 'Started',
      key: 'started_at',
      accessor: (row: SessionItem) => new Date(row.started_at).toLocaleString(),
    },
    {
      header: 'Ended',
      key: 'ended_at',
      accessor: (row: SessionItem) => (row.ended_at ? new Date(row.ended_at).toLocaleString() : '—'),
    },
  ]

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Chat Sessions</h2>
        <p className="text-sm text-slate-500">All customer support chat sessions</p>
      </div>
      <DataTable 
        data={data} 
        columns={columns} 
        isLoading={isLoading} 
        emptyMessage="No sessions found"
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
