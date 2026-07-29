import { useRef } from 'react'
import { ChatInput } from './ChatInput'
import { MessageContent } from './MessageContent'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

type ChatPanelProps = {
  draft: string
  messages: Message[]
  isLoading: boolean
  onDraftChange: (value: string) => void
  onSubmit: () => void
}

export function ChatPanel({
  draft,
  messages,
  isLoading,
  onDraftChange,
  onSubmit,
}: ChatPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const hasMessages = messages.length > 0
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
        {hasMessages ? (
          <div className="mb-4 flex flex-1 flex-col gap-3 overflow-y-auto">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`rounded-lg px-4 py-3 ${
                  message.role === 'user'
                    ? 'ml-auto max-w-[80%] bg-sky-100 text-sky-900'
                    : 'mr-auto max-w-[80%] bg-white text-slate-900 shadow-sm'
                }`}
              >
                {message.role === 'user' ? (
                  <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                ) : (
                  <MessageContent content={message.content} />
                )}
              </div>
            ))}
            {isLoading && (
              <div className="mr-auto max-w-[80%] rounded-lg bg-white px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-1 flex-col justify-center">
            <div className="mx-auto w-full max-w-2xl rounded-3xl border border-slate-200/90 bg-white/80 p-5 text-center shadow-[0_16px_46px_rgba(15,23,42,0.08)] sm:p-6">
              <h3 className="text-lg font-semibold text-slate-900">What can I help you with today?</h3>
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

        <div className="mt-5 border-t border-slate-200/80 pt-4 sm:pt-5">
          <ChatInput
            value={draft}
            onChange={onDraftChange}
            onSubmit={onSubmit}
            inputRef={inputRef}
          />
        </div>
      </div>
    </section>
  )
}