import { type ChatSession, formatSessionTimestamp } from '../features/chat/useChatSessions'

type SessionsComponentProps = {
  sessions: ChatSession[]
  selectedSessionId: string | null
  isStreaming: boolean
  isLoading: boolean
  isCreating: boolean
  onSelect: (sessionId: string) => void
}

export function SessionsComponent({
  sessions,
  selectedSessionId,
  isStreaming,
  isLoading,
  isCreating,
  onSelect,
}: SessionsComponentProps) {
  const isPreparing = isLoading || isCreating

  return (
    <div className="flex-1 space-y-2 overflow-y-auto pr-1" role="list" aria-label="Chat sessions">
      {sessions.map((session) => {
        const isActive = session.id === selectedSessionId

        return (
          <button
            key={session.id}
            type="button"
            onClick={() => {
              if (!isActive) {
                onSelect(session.id)
              }
            }}
            disabled={isStreaming}
            aria-current={isActive ? 'true' : undefined}
            className={[
              'w-full rounded-2xl border px-3.5 py-3 text-left transition',
              isActive
                ? 'border-sky-400 bg-sky-100/90 ring-2 ring-sky-200/80 shadow-[0_14px_36px_rgba(56,189,248,0.2)]'
                : 'border-slate-200 bg-white/92 hover:border-sky-200 hover:bg-sky-50/75',
            ].join(' ')}
          >
            <p className="truncate text-sm font-semibold text-slate-900">{session.title}</p>
            <p className={['mt-1 text-xs', isActive ? 'text-sky-700' : 'text-slate-500'].join(' ')}>
              {formatSessionTimestamp(session.started_at)}
            </p>
          </button>
        )
      })}

      {isPreparing ? <p className="px-2 py-4 text-xs text-slate-500">Preparing your sessions...</p> : null}
      {!isPreparing && sessions.length === 0 ? (
        <p className="px-2 py-4 text-xs text-slate-500">
          New chats appear here after your first message in that chat.
        </p>
      ) : null}
    </div>
  )
}
