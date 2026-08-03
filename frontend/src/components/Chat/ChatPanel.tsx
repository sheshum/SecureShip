import { useRef } from 'react'
import { ChatInput } from './ChatInput'
import { MessageContent } from './MessageContent'
import type { ChatSessionState } from '../../api/generated/schemas/chatSessionState'

type Message = {
  role: 'user' | 'assistant'
  content: string
}

type ChatPanelProps = {
  draft: string
  messages: Message[]
  isLoading: boolean
  sessionState?: ChatSessionState
  onDraftChange: (value: string) => void
  onSubmit: () => void
  onClose: () => void
}

type ChatHeaderProps = {
  onClose: () => void
}

function ChatHeader({ onClose }: ChatHeaderProps) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 sm:px-6">
      <div className="flex items-center gap-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5 text-sky-500"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 2L9.5 8.5L3 9l5.5 4.5L7 21l5-3.5L17 21l-1.5-7.5L21 9l-6.5-.5z" />
          <path d="M12 0l-1.5 4L8 4.5l3 2.5L10 11l2-1.5L14 11l-1-4 3-2.5-2.5-.5z" opacity="0.6" />
        </svg>
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-slate-700">SecureShip Assistant</p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-400 transition hover:border-slate-400 hover:text-slate-600"
        aria-label="Close chat"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </header>
  )
}

function EscalationBanner() {
  return (
    <div className="mx-4 mt-4 flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 sm:mx-6">
      <span className="text-xl">👤</span>
      <div className="flex-1">
        <p className="text-sm font-semibold text-amber-900">Connected to Human Support</p>
        <p className="mt-0.5 text-xs text-amber-700">A customer service representative will assist you shortly.</p>
      </div>
    </div>
  )
}

type MessageListProps = {
  messages: Message[]
  isLoading: boolean
}

function MessageList({ messages, isLoading }: MessageListProps) {
  return (
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
  )
}

export function ChatPanel({
  draft,
  messages,
  isLoading,
  sessionState,
  onDraftChange,
  onSubmit,
  onClose,
}: ChatPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const hasMessages = messages.length > 0
  const isEscalated = sessionState === 'escalated_to_human'
  const starterPrompts = [
    'Where is my shipment right now?',
    'When will my package be delivered?',
    'My tracking has not updated. What should I do?',
  ]

  return (
    <section className="flex min-h-[calc(100svh-4.5rem)] w-full flex-col rounded-[1.6rem] border border-white/70 bg-white/84 shadow-[0_24px_80px_rgba(15,23,42,0.14)] backdrop-blur-xl lg:basis-[76%]">
      <ChatHeader onClose={onClose} />

      {isEscalated && <EscalationBanner />}

      <div className="flex min-h-0 flex-1 flex-col px-4 pb-4 pt-4 sm:px-6 sm:pb-6 sm:pt-5">
        {hasMessages ? (
          <MessageList messages={messages} isLoading={isLoading} />
        ) : (
          <div className="flex flex-1 flex-col justify-center">
            <div className="mx-auto w-full max-w-2xl rounded-3xl border border-slate-200/90 bg-white/80 p-5 text-center shadow-[0_16px_46px_rgba(15,23,42,0.08)] sm:p-6">
              <h3 className="text-lg font-semibold text-slate-900">What can I help you with today?</h3>
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