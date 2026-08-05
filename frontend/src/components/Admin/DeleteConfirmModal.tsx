type DeleteConfirmModalProps = {
  isOpen: boolean
  isDeleting?: boolean
  errorMessage?: string | null
  resourceLabel: string
  onClose: () => void
  onConfirm: () => void
}

export function DeleteConfirmModal({
  isOpen,
  isDeleting,
  errorMessage,
  resourceLabel,
  onClose,
  onConfirm,
}: DeleteConfirmModalProps) {
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
        <h3 className="text-lg font-semibold text-slate-900">Delete {resourceLabel}?</h3>
        <p className="mt-2 text-sm text-slate-600">This action cannot be undone.</p>

        {errorMessage && <p className="mt-3 text-sm text-red-600">{errorMessage}</p>}

        <div className="mt-6 flex justify-end gap-3">
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
            disabled={isDeleting}
            className="rounded-lg bg-[#b3432b] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#9a3724] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </section>
    </div>
  )
}
