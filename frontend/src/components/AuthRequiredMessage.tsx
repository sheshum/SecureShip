import { type FormEvent, useState } from 'react'

export type IdentityInput = {
  firstName: string
  lastName: string
  phoneNumber: string
}

type AuthRequiredMessageProps = {
  message: string
  ctaLabel: string
  isSubmitting: boolean
  infoMessage?: string | null
  onSubmit: (input: IdentityInput) => Promise<void> | void
}

export function AuthRequiredMessage({
  message,
  ctaLabel,
  isSubmitting,
  infoMessage,
  onSubmit,
}: AuthRequiredMessageProps) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit({
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      phoneNumber: phoneNumber.trim(),
    })
  }

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-slate-800 shadow-sm">
      <p className="text-sm font-medium text-amber-900">{message}</p>

      <form className="mt-3 grid gap-2 sm:grid-cols-2" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
          First Name
          <input
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            disabled={isSubmitting}
            minLength={1}
            maxLength={100}
            required
            className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
          Last Name
          <input
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            disabled={isSubmitting}
            minLength={1}
            maxLength={100}
            required
            className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
          />
        </label>

        <label className="sm:col-span-2 flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
          Phone Number
          <input
            value={phoneNumber}
            onChange={(event) => setPhoneNumber(event.target.value)}
            disabled={isSubmitting}
            minLength={4}
            maxLength={50}
            required
            placeholder="+14155550112"
            className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
          />
        </label>

        <div className="sm:col-span-2 flex items-center justify-between gap-3 pt-1">
          <button
            type="submit"
            disabled={isSubmitting}
            className="min-h-11 rounded-xl border border-sky-300 bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
          >
            {isSubmitting ? 'Starting verification...' : ctaLabel}
          </button>

          {infoMessage ? <p className="text-xs text-slate-600">{infoMessage}</p> : null}
        </div>
      </form>
    </section>
  )
}
