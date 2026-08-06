import type { RefObject } from 'react'

type ChatInputProps = {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  inputRef?: RefObject<HTMLTextAreaElement | null>
}

export function ChatInput({ value, onChange, onSubmit, inputRef }: ChatInputProps) {
  const canSend = value.trim().length > 0

  const handleSubmit = () => {
    if (canSend) {
      onSubmit()
    }
  }

  return (
    <form
      className="w-full"
      onSubmit={(event) => {
        event.preventDefault()
      }}
    >
      <label className="sr-only" htmlFor="chat-message">
        Ask about your shipment
      </label>
      <p id="chat-message-hint" className="sr-only">
        Press Shift plus Enter to send your message. Press Enter to add a new line.
      </p>
      <div className="flex items-end rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-[0_18px_50px_rgba(15,23,42,0.12)] backdrop-blur focus-within:ring-2 focus-within:ring-sky-500 focus-within:ring-offset-2">
        <textarea
          ref={inputRef}
          id="chat-message"
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby="chat-message-hint"
          onKeyDown={(event) => {
            if (event.key === 'Enter' && event.shiftKey) {
              event.preventDefault()
              handleSubmit()
            }
          }}
          placeholder="Ask about your shipment details"
          autoComplete="off"
          className="max-h-48 min-h-12 flex-1 resize-none overflow-y-auto rounded-lg border-none bg-transparent px-4 py-3 text-base text-slate-900 outline-none placeholder:text-slate-400"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSend}
          className="flex h-12 w-12 items-center justify-center rounded-full border border-sky-300 bg-sky-500 text-white shadow-sm transition hover:bg-sky-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500"
          aria-label="Send message"
        >
          <svg viewBox="0 0 20 20" className="h-5 w-5" fill="currentColor" aria-hidden="true">
            <path d="M2.6 9.52a1 1 0 0 1 .34-1.62l13.6-5.44a1 1 0 0 1 1.32 1.3L12.4 17.4a1 1 0 0 1-1.9-.16L9.36 12.4 4.53 10.2a1 1 0 0 1-.59-.68ZM15.1 4.92 6.44 8.4l3.28 1.5a1 1 0 0 1 .52.56l.9 3.27 3.96-8.8Z" />
          </svg>
        </button>
      </div>
    </form>
  )
}