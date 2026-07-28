import { useRef } from 'react'
import { ChatInput } from './ChatInput'
import { ChatMessageList, type ChatMessage } from './ChatMessageList'

type ChatPanelProps = {
  messages: ChatMessage[]
  draft: string
  isStreaming: boolean
  isInitializingSession: boolean
  errorMessage: string | null
  authRequiredMessage: string | null
  authRequiredInfoMessage: string | null
  onDraftChange: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export function ChatPanel({
  messages,
  draft,
  isStreaming,
  isInitializingSession,
  errorMessage,
  authRequiredMessage,
  authRequiredInfoMessage,
  onDraftChange,
  onSubmit,
  onCancel,
}: ChatPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const hasMessages = messages.length > 0
  const shouldShowHistorySkeleton = isInitializingSession && !hasMessages
  const starterPrompts = [
    'Where is my shipment right now?',
    'When will my package be delivered?',
    'My tracking has not updated. What should I do?',
    'Can I change the delivery address?',
  ]

  return (
    <section className="flex min-h-[calc(100svh-4.5rem)] w-full flex-col rounded-[1.6rem] border border-white/70 bg-white/84 shadow-[0_24px_80px_rgba(15,23,42,0.14)] backdrop-blur-xl lg:basis-[76%]">
      <header className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 sm:px-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">SecureShip Assistant</p>
        </div>

      </header>

      <div className="flex min-h-0 flex-1 flex-col px-4 pb-4 pt-4 sm:px-6 sm:pb-6 sm:pt-5">
        <div className="mb-3 space-y-2" aria-live="polite">
          {isInitializingSession ? (
            <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700">
              Starting a new secure support session...
            </p>
          ) : null}
        </div>

        {hasMessages ? (
          <ChatMessageList messages={messages} isStreaming={isStreaming} />
        ) : shouldShowHistorySkeleton ? (
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
        ) : (
          <div className="flex flex-1 flex-col justify-center">
            <div className="mx-auto w-full max-w-2xl rounded-3xl border border-slate-200/90 bg-white/80 p-5 text-center shadow-[0_16px_46px_rgba(15,23,42,0.08)] sm:p-6">
              <h3 className="text-lg font-semibold text-slate-900">How Can I Help You Today</h3>
              <p className="mt-2 text-sm text-slate-600">
                Start with a quick question about tracking, delivery ETA, or address changes.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-2.5">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => {
                      onDraftChange(prompt)
                      inputRef.current?.focus()
                    }}
                    className="rounded-full border border-slate-300 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-800"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {authRequiredMessage ? (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-900 shadow-sm" role="status" aria-live="polite">
            <p className="font-medium">{authRequiredMessage}</p>
            {authRequiredInfoMessage ? <p className="mt-1 text-xs text-amber-800/90">{authRequiredInfoMessage}</p> : null}
          </div>
        ) : null}

        <div className="mt-5 border-t border-slate-200/80 pt-4 sm:pt-5">
          <ChatInput
            value={draft}
            onChange={onDraftChange}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isStreaming={isStreaming}
            inputRef={inputRef}
          />
        </div>

        {errorMessage ? (
          <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2" role="status" aria-live="assertive">
            <p className="text-sm text-rose-800">{errorMessage}</p>
          </div>
        ) : null}
      </div>
    </section>
  )
}