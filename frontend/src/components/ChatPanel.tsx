import { ChatInput } from './ChatInput'
import { ChatMessageList, type ChatMessage } from './ChatMessageList'

type ChatPanelProps = {
  messages: ChatMessage[]
  draft: string
  isStreaming: boolean
  errorMessage: string | null
  isRefreshingSessions: boolean
  onDraftChange: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export function ChatPanel({
  messages,
  draft,
  isStreaming,
  errorMessage,
  isRefreshingSessions,
  onDraftChange,
  onSubmit,
  onCancel,
}: ChatPanelProps) {
  const hasMessages = messages.length > 0

  return (
    <section
      className={[
        'flex w-full flex-col rounded-[1.6rem] border border-white/70 bg-white/72 p-4 shadow-[0_24px_80px_rgba(15,23,42,0.14)] backdrop-blur-xl sm:p-6',
        hasMessages ? 'h-[min(84svh,820px)]' : 'min-h-[calc(100svh-4.5rem)] justify-center',
      ].join(' ')}
    >
      {hasMessages ? (
        <>
          <ChatMessageList messages={messages} isStreaming={isStreaming} />
          <div className="mt-6 w-full">
            <ChatInput
              value={draft}
              onChange={onDraftChange}
              onSubmit={onSubmit}
              onCancel={onCancel}
              isStreaming={isStreaming}
            />
          </div>
        </>
      ) : (
        <div className="mx-auto w-full max-w-3xl">
          <div className="mb-8 rounded-2xl border border-slate-200 bg-white/95 px-5 py-4 text-slate-800 shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
            Hello! Ask me to track shipments, verify delivery status, or explain the latest logistics events.
          </div>
          <ChatInput
            value={draft}
            onChange={onDraftChange}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isStreaming={isStreaming}
          />
        </div>
      )}
      {errorMessage ? <p className="mt-4 text-sm text-red-600">{errorMessage}</p> : null}
      {isRefreshingSessions ? <p className="mt-2 text-xs text-slate-500">Refreshing sessions...</p> : null}
    </section>
  )
}