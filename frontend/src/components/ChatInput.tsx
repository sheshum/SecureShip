type ChatInputProps = {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onCancel: () => void
  isStreaming: boolean
}

export function ChatInput({ value, onChange, onSubmit, onCancel, isStreaming }: ChatInputProps) {
  const canSend = value.trim().length > 0

  const handleSubmit = () => {
    if (!isStreaming && canSend) {
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
      <div className="flex items-center rounded-full border border-slate-200 bg-white/95 p-2 shadow-[0_18px_50px_rgba(15,23,42,0.12)] backdrop-blur">
        <input
          id="chat-message"
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && event.shiftKey) {
              event.preventDefault()
              handleSubmit()
              return
            }

            if (event.key === 'Enter') {
              event.preventDefault()
            }
          }}
          placeholder="Ask about your shipment details"
          disabled={isStreaming}
          className="h-12 flex-1 rounded-full border-none bg-transparent px-4 text-base text-slate-900 outline-none placeholder:text-slate-400"
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onCancel}
            className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50"
            aria-label="Stop generating"
          >
            <svg viewBox="0 0 20 20" className="h-5 w-5" fill="currentColor" aria-hidden="true">
              <rect x="5" y="5" width="10" height="10" rx="1.5" />
            </svg>
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSend}
            className="flex h-11 w-11 items-center justify-center rounded-full border border-sky-300 bg-sky-500 text-white shadow-sm transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-200 disabled:text-slate-500"
            aria-label="Send message"
          >
            <svg viewBox="0 0 20 20" className="h-5 w-5" fill="currentColor" aria-hidden="true">
              <path d="M2.6 9.52a1 1 0 0 1 .34-1.62l13.6-5.44a1 1 0 0 1 1.32 1.3L12.4 17.4a1 1 0 0 1-1.9-.16L9.36 12.4 4.53 10.2a1 1 0 0 1-.59-.68ZM15.1 4.92 6.44 8.4l3.28 1.5a1 1 0 0 1 .52.56l.9 3.27 3.96-8.8Z" />
            </svg>
          </button>
        )}
      </div>
    </form>
  )
}