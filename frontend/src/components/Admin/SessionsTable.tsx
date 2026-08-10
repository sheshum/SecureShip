import { useState } from 'react'
import { useListSessionsApiSessionsGet } from '../../api/generated/client'
import { ChatSessionState } from '../../api/generated/schemas'
import type { SessionItem } from '../../api/generated/schemas'
import { DataTable } from './DataTable'
import { TableFilterSelect } from './TableFilterSelect'

const ITEMS_PER_PAGE = 10

const SESSION_STATE_OPTIONS = Object.values(ChatSessionState).map((state) => ({
  value: state,
  label: state.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
}))

function isChatSessionState(value: string): value is ChatSessionState {
  return (
    value === ChatSessionState.anonymous ||
    value === ChatSessionState.collecting_identity ||
    value === ChatSessionState.code_sent ||
    value === ChatSessionState.awaiting_code ||
    value === ChatSessionState.verified ||
    value === ChatSessionState.escalated_to_human ||
    value === ChatSessionState.code_expired
  )
}

function buildSessionColumns(onNavigateToCustomers?: (customerId: string) => void) {
  return [
    {
      header: 'Session ID',
      key: 'id',
      accessor: (row: SessionItem) => (
        <span className="font-mono text-xs">{row.id.substring(0, 8)}...</span>
      ),
    },
    {
      header: 'Customer',
      key: 'customer_name',
      accessor: (row: SessionItem) => row.customer_name ?? '—',
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
    {
      header: 'Actions',
      key: 'actions',
      accessor: (row: SessionItem) => {
        const customerId = row.customer_id
        if (typeof customerId !== 'string') {
          return <span className="text-xs text-slate-400">—</span>
        }

        return (
          <button
            type="button"
            onClick={() => onNavigateToCustomers?.(customerId)}
            className="rounded-lg px-2 py-1 text-xs font-semibold text-sky-700 transition hover:bg-sky-50"
          >
            View Customer →
          </button>
        )
      },
    },
  ]
}

type SessionsTableProps = {
  onNavigateToCustomers?: (customerId: string) => void
}

export function SessionsTable({ onNavigateToCustomers }: SessionsTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [filterState, setFilterState] = useState<ChatSessionState | ''>('')
  const offset = (currentPage - 1) * ITEMS_PER_PAGE

  const handleFilterChange = (value: string) => {
    if (value === '') {
      setFilterState('')
    } else if (isChatSessionState(value)) {
      setFilterState(value)
    }
    setCurrentPage(1)
  }

  const { data: response, isLoading } = useListSessionsApiSessionsGet({
    limit: ITEMS_PER_PAGE,
    offset: offset,
    state: filterState || undefined,
  })
  const data = (response?.data && 'sessions' in response.data) ? response.data.sessions : []
  const total = (response?.data && 'total' in response.data) ? response.data.total : 0
  const columns = buildSessionColumns(onNavigateToCustomers)

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Chat Sessions</h2>
          <p className="text-sm text-slate-500">All customer support chat sessions</p>
        </div>
        <TableFilterSelect
          value={filterState}
          onChange={handleFilterChange}
          options={SESSION_STATE_OPTIONS}
          allLabel="All states"
        />
      </div>
      <DataTable 
        data={data} 
        columns={columns} 
        getRowKey={(row) => row.id}
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
