import { useEffect, useRef } from 'react'
import { ChatInput } from './ChatInput'
import { MessageContent } from './MessageContent'
import { ChatSessionState } from '../../api/generated/schemas'

type Message = {
  id: string
  role: 'user' | 'assistant' | 'melany' | 'event'
  content: string
}

type ChatPanelProps = {
  draft: string
  messages: Message[]
  isLoading: boolean
  isHandoffSequencePlaying?: boolean
  sessionState?: ChatSessionState
  onDraftChange: (value: string) => void
  onSubmit: (message?: string) => void
  onStopRequest: () => void
  onClose: () => void
}

type ChatHeaderProps = {
  sessionState?: ChatSessionState
  onClose: () => void
}

function HumanBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-teal-700">
      Human Support
    </span>
  )
}

function VerificationBadge({ isVerified }: { isVerified: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        isVerified ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
      }`}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-3 w-3"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        {isVerified ? (
          <path
            fillRule="evenodd"
            d="M16.704 5.29a1 1 0 00-1.408-1.42l-6.361 6.29-2.227-2.202a1 1 0 00-1.408 1.42l2.932 2.9a1 1 0 001.408 0l7.064-6.988z"
            clipRule="evenodd"
          />
        ) : (
          <path d="M10 2a4 4 0 00-4 4v2H5a1 1 0 00-1 1v8a1 1 0 001 1h10a1 1 0 001-1v-8a1 1 0 00-1-1h-1V6a4 4 0 00-4-4zm2 6H8V6a2 2 0 114 0v2z" />
        )}
      </svg>
      {isVerified ? 'Verified' : 'Unverified'}
    </span>
  )
}

function ChatHeader({ sessionState, onClose }: ChatHeaderProps) {
  const isVerified = sessionState === ChatSessionState.verified
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 sm:px-6">
      <div className="flex items-center gap-2">
        <img src="/Logo_icon_only.png" alt="" className="h-10 w-12" />
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-slate-700">SecureShip Assistant</p>
          <VerificationBadge isVerified={isVerified} />
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

function HumanAvatar() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-100 shadow-sm">
      <img src="/human_avatar.svg" alt="" className="h-5 w-5" aria-hidden="true" />
    </span>
  )
}

function AiAvatar() {
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-stone-100 shadow-sm">
      <img src="/ai_avatar.svg" alt="" className="h-4 w-4" aria-hidden="true" />
    </span>
  )
}



type MessageListProps = {
  messages: Message[]
  isLoading: boolean
}

function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="mb-4 flex flex-1 flex-col gap-5 overflow-y-auto">
      {messages.map((message) => {
        if (message.role === 'event') {
          return (
            <div key={message.id} className="flex items-center gap-3 px-2">
              <div className="h-px flex-1 bg-teal-200" />
              <span className="text-xs font-medium text-teal-600">{message.content}</span>
              <div className="h-px flex-1 bg-teal-200" />
            </div>
          )
        }
        return (
          <div
            key={message.id}
            className={`flex max-w-[80%] items-start gap-2 ${message.role === 'user' ? 'ml-auto' : 'mr-auto'}`}
          >
            {message.role === 'melany' && <HumanAvatar />}
            {message.role === 'assistant' && <AiAvatar />}
            <div
              className={
                message.role === 'user'
                  ? 'rounded-2xl rounded-br-sm bg-gradient-to-br from-sky-400 to-blue-600 px-4 py-3 text-sm text-white shadow-sm'
                  : message.role === 'melany'
                  ? 'rounded-2xl rounded-bl-sm border border-teal-200 border-l-2 border-l-teal-500 bg-teal-50 px-4 py-3 text-slate-900 shadow-sm'
                  : 'rounded-2xl rounded-bl-sm border border-stone-200 border-l-2 border-l-sky-400 bg-stone-100 px-4 py-3 text-slate-900 shadow-sm'
              }
            >
              {message.role === 'user' ? (
                <p className="whitespace-pre-wrap">{message.content}</p>
              ) : (
                <MessageContent content={message.content} />
              )}
            </div>
          </div>
        )
      })}
      {isLoading && (
        <div className="mr-auto max-w-[80%] rounded-lg bg-stone-100 px-4 py-3 shadow-sm">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
            <div className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

export function ChatPanel({
  draft,
  messages,
  isLoading,
  isHandoffSequencePlaying = false,
  sessionState,
  onDraftChange,
  onSubmit,
  onStopRequest,
  onClose,
}: ChatPanelProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const hasMessages = messages.length > 0
  const isEscalated = sessionState === ChatSessionState.escalated_to_human
  const starterPrompts = [
    'Where is my shipment right now?',
    'When will my package be delivered?',
    'My tracking has not updated. What should I do?',
  ]

  return (
    <section
      className={`flex min-h-0 flex-1 w-full flex-col rounded-[1.6rem] border shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur-xl lg:basis-[76%] transition-colors duration-700 ${
        isEscalated
          ? 'border-teal-200/60 bg-gradient-to-b from-teal-50 via-emerald-50/95 to-stone-50/80'
          : 'border-slate-200/60 bg-gradient-to-b from-white via-slate-50/95 to-slate-100/80'
      }`}
    >
      <ChatHeader sessionState={sessionState} onClose={onClose} />

      <div className="flex min-h-0 flex-1 flex-col px-4 pb-4 pt-4 sm:px-6 sm:pb-6 sm:pt-5">
        {hasMessages ? (
          <MessageList messages={messages} isLoading={isLoading} />
        ) : (
          <div className="flex flex-1 flex-col justify-center">
            <div className="mx-auto w-full max-w-2xl rounded-3xl border border-stone-200/90 bg-stone-50/90 p-5 text-center shadow-[0_16px_46px_rgba(15,23,42,0.08)] sm:p-6">
              <h3 className="text-lg font-semibold text-slate-900">What can I help you with today?</h3>
              <div className="mt-4 flex flex-wrap justify-center gap-2.5">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => onSubmit(prompt)}
                    className="rounded-full border border-stone-300 bg-stone-50 px-3.5 py-2 text-xs font-medium text-slate-700 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-800"
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
            isSending={isLoading || isHandoffSequencePlaying}
            onStop={onStopRequest}
            inputRef={inputRef}
          />
        </div>
      </div>
    </section>
  )
}