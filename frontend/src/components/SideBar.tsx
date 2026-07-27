import { type ChatSession } from '../features/chat/useChatSessions'
import { SessionsComponent } from './SessionsComponent'

type SideBarProps = {
  sessions: ChatSession[]
  selectedSessionId: string | null
  hasPersistedSessions: boolean
  isStreaming: boolean
  isLoadingSessions: boolean
  isCreatingSession: boolean
  isDeletingSession: boolean
  onCreateSession: () => void
  onDeleteSession: () => void
  onSelectSession: (sessionId: string) => void
  onRequestClose?: () => void
  className?: string
}

export function SideBar({
  sessions,
  selectedSessionId,
  hasPersistedSessions,
  isStreaming,
  isLoadingSessions,
  isCreatingSession,
  isDeletingSession,
  onCreateSession,
  onDeleteSession,
  onSelectSession,
  onRequestClose,
  className,
}: SideBarProps) {
  return (
    <aside
      className={[
        'flex w-full flex-col rounded-[1.5rem] border border-white/75 bg-white/88 p-3 shadow-[0_12px_40px_rgba(15,23,42,0.08)] sm:p-4 lg:basis-[24%] lg:p-5',
        className ?? '',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/75 pb-3">
        <div className="min-w-0">
          <p className="text-sm font-bold tracking-[0.14em] text-slate-800">CHAT SESSIONS</p>
          <p className="mt-1 text-xs text-slate-500">Select or create a conversation.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCreateSession}
            disabled={isStreaming || isCreatingSession || !hasPersistedSessions}
            className="min-h-11 rounded-full border border-sky-300 bg-sky-500 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500"
          >
            {isCreatingSession ? 'Creating...' : 'New'}
          </button>
          {onRequestClose ? (
            <button
              type="button"
              onClick={onRequestClose}
              className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
              aria-label="Close sessions panel"
            >
              ×
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-3 min-h-0 flex-1">
        <SessionsComponent
          sessions={sessions}
          selectedSessionId={selectedSessionId}
          isStreaming={isStreaming}
          isLoading={isLoadingSessions}
          isCreating={isCreatingSession}
          onSelect={onSelectSession}
        />
      </div>

      <div className="border-t border-slate-200/75 pt-3">
        <button
          type="button"
          onClick={onDeleteSession}
          disabled={!selectedSessionId || !hasPersistedSessions || isStreaming || isDeletingSession}
          className="min-h-11 w-full rounded-xl border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
        >
          {isDeletingSession ? 'Deleting...' : 'Delete selected session'}
        </button>
      </div>
    </aside>
  )
}