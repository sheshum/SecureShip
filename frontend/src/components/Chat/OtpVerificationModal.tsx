import { type FormEvent, useState } from 'react'

type OtpVerificationModalProps = {
  isSubmitting: boolean
  errorMessage: string | null
  helperMessage: string | null
  remainingAttempts: number | null
  onSubmit: (code: string) => Promise<void> | void
  onClose: () => void
}

export function OtpVerificationModal({
  isSubmitting,
  errorMessage,
  helperMessage,
  remainingAttempts,
  onSubmit,
  onClose,
}: OtpVerificationModalProps) {
  const [code, setCode] = useState('')

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit(code.trim())
  }

  return (
    <dialog
      open
      className="fixed inset-0 z-50 m-0 flex h-screen w-screen max-h-none max-w-none items-center justify-center overflow-visible border-none bg-transparent p-4"
    >
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/55"
        onClick={onClose}
        aria-label="Close verification modal"
      />

      <section className="relative z-10 w-full max-w-md rounded-2xl border border-white/65 bg-white p-5 shadow-[0_24px_80px_rgba(15,23,42,0.28)]">
        <h3 className="text-lg font-semibold text-slate-900">Enter Verification Code</h3>
        <p className="mt-1 text-sm text-slate-600">
          We sent a one-time code to your verified phone number.
        </p>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Verification Code
            <input
              value={code}
              onChange={(event) => setCode(event.target.value)}
              minLength={1}
              maxLength={20}
              required
              disabled={isSubmitting}
              placeholder="123456"
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          {helperMessage ? <p className="text-xs text-slate-600">{helperMessage}</p> : null}
          {remainingAttempts !== null ? (
            <p className="text-xs text-slate-600">Remaining attempts: {remainingAttempts}</p>
          ) : null}
          {errorMessage ? <p className="text-sm text-rose-700">{errorMessage}</p> : null}

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-sky-300 bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
            >
              {isSubmitting ? 'Verifying...' : 'Verify code'}
            </button>
          </div>
        </form>
      </section>
    </dialog>
  )
}
