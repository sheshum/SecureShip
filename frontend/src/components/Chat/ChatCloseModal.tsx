type ChatCloseModalProps = {
  isOpen: boolean
  isClosing?: boolean
  errorMessage?: string | null
  onClose: () => void
  onConfirm: () => void
}

export function ChatCloseModal({ isOpen, isClosing, errorMessage, onClose, onConfirm }: ChatCloseModalProps) {
  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute left-0 top-0 h-full w-full bg-slate-950/55"
        onClick={onClose}
        aria-label="Close modal"
      />

      <section className="relative w-full max-w-sm rounded-2xl border border-white/65 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.28)]">
        <h3 className="text-lg font-semibold text-slate-900">Close this chat?</h3>
        <p className="mt-2 text-sm text-slate-600">
          You won't be able to send more messages in this conversation once it's closed.
        </p>
        
        {errorMessage && (
          <p className="mt-3 text-sm text-red-600">{errorMessage}</p>
        )}

        <div className="mt-6 flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isClosing}
            className="rounded-lg bg-[#b3432b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#9a3724] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isClosing ? 'Closing...' : 'Close chat'}
          </button>
        </div>
      </section>
    </div>
  )
}
