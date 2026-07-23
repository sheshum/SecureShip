type ChatInputProps = {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
}

export function ChatInput({ value, onChange, onSubmit }: ChatInputProps) {
  return (
    <form
      className="w-full"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
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
          placeholder="Ask about your shipment details"
          className="h-12 flex-1 rounded-full border-none bg-transparent px-4 text-base text-slate-900 outline-none placeholder:text-slate-400"
        />
      </div>
    </form>
  )
}