import { ChatInput } from './ChatInput'
import { ChatMessageList, type ChatMessage } from './ChatMessageList'

type ChatPanelProps = {
  messages: ChatMessage[]
  draft: string
  isStreaming: boolean
  isLoadingHistory: boolean
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
  isLoadingHistory,
  errorMessage,
  isRefreshingSessions,
  onDraftChange,
  onSubmit,
  onCancel,
}: ChatPanelProps) {
  const hasMessages = messages.length > 0
  const shouldShowHistorySkeleton = isLoadingHistory && !hasMessages

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
      ) : shouldShowHistorySkeleton ? (
        <>
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-1">
            <div className="max-w-[68%] animate-pulse rounded-md border border-slate-200 bg-white px-5 py-4">
              <div className="h-3 w-11/12 rounded bg-slate-200" />
              <div className="mt-2 h-3 w-8/12 rounded bg-slate-200" />
            </div>
            <div className="ml-auto max-w-[72%] animate-pulse rounded-md border border-sky-200/80 bg-sky-100/80 px-5 py-4">
              <div className="h-3 w-10/12 rounded bg-sky-200" />
              <div className="mt-2 h-3 w-7/12 rounded bg-sky-200" />
            </div>
            <div className="max-w-[64%] animate-pulse rounded-md border border-slate-200 bg-white px-5 py-4">
              <div className="h-3 w-9/12 rounded bg-slate-200" />
              <div className="mt-2 h-3 w-6/12 rounded bg-slate-200" />
            </div>
          </div>
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
      {shouldShowHistorySkeleton ? <p className="mt-2 text-xs text-slate-500">Loading chat history...</p> : null}
      {isRefreshingSessions ? <p className="mt-2 text-xs text-slate-500">Refreshing sessions...</p> : null}
    </section>
  )
}