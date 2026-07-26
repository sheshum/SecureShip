import { type ChatSession } from '../features/chat/useChatSessions'
import { SessionsComponent } from './SessionsComponent'

type SideBarProps = {
  sessions: ChatSession[]
  selectedSessionId: string | null
  isStreaming: boolean
  isLoadingSessions: boolean
  isCreatingSession: boolean
  isDeletingSession: boolean
  onCreateSession: () => void
  onDeleteSession: () => void
  onSelectSession: (sessionId: string) => void
}

export function SideBar({
  sessions,
  selectedSessionId,
  isStreaming,
  isLoadingSessions,
  isCreatingSession,
  isDeletingSession,
  onCreateSession,
  onDeleteSession,
  onSelectSession,
}: SideBarProps) {
  return (
    <aside className="flex w-full flex-col rounded-[1.5rem] border border-white/75 bg-white/85 p-3 shadow-[0_12px_40px_rgba(15,23,42,0.08)] sm:max-w-[290px] sm:p-4">
      <div className="flex items-center justify-between gap-3 pb-3">
        <p className="text-sm font-semibold tracking-[0.12em] text-slate-700">CHAT SESSIONS</p>
        <button
          type="button"
          onClick={onCreateSession}
          disabled={isStreaming || isCreatingSession}
          className="rounded-full border border-sky-300 bg-sky-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500"
        >
          New
        </button>
      </div>

      <SessionsComponent
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        isStreaming={isStreaming}
        isLoading={isLoadingSessions}
        isCreating={isCreatingSession}
        onSelect={onSelectSession}
      />

      <div className="pt-3">
        <button
          type="button"
          onClick={onDeleteSession}
          disabled={!selectedSessionId || isStreaming || isDeletingSession}
          className="w-full rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
        >
          Delete selected session
        </button>
      </div>
    </aside>
  )
}