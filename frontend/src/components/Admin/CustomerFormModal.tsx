import { type FormEvent, useEffect, useState } from 'react'
import type { CustomerItem } from '../../api/generated/schemas'

export type CustomerFormValues = {
  first_name: string
  last_name: string
  phone_number: string
  address: string
}

type CustomerFormModalProps = {
  isOpen: boolean
  isSubmitting: boolean
  errorMessage: string | null
  initialValues?: CustomerItem
  onSubmit: (values: CustomerFormValues) => Promise<void> | void
  onClose: () => void
}

const EMPTY_VALUES: CustomerFormValues = {
  first_name: '',
  last_name: '',
  phone_number: '',
  address: '',
}

export function CustomerFormModal({
  isOpen,
  isSubmitting,
  errorMessage,
  initialValues,
  onSubmit,
  onClose,
}: CustomerFormModalProps) {
  const [values, setValues] = useState<CustomerFormValues>(EMPTY_VALUES)
  const isEdit = Boolean(initialValues)

  useEffect(() => {
    if (isOpen) {
      setValues(initialValues ? { ...initialValues } : EMPTY_VALUES)
    }
  }, [isOpen, initialValues])

  if (!isOpen) {
    return null
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await onSubmit(values)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/55"
        onClick={onClose}
        aria-label="Close modal"
      />

      <section className="relative w-full max-w-md rounded-2xl border border-white/65 bg-white p-5 shadow-[0_24px_80px_rgba(15,23,42,0.28)]">
        <h3 className="text-lg font-semibold text-slate-900">{isEdit ? 'Edit Customer' : 'Add Customer'}</h3>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            First Name
            <input
              value={values.first_name}
              onChange={(event) => setValues({ ...values, first_name: event.target.value })}
              required
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Last Name
            <input
              value={values.last_name}
              onChange={(event) => setValues({ ...values, last_name: event.target.value })}
              required
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Phone Number
            <input
              value={values.phone_number}
              onChange={(event) => setValues({ ...values, phone_number: event.target.value })}
              required
              pattern="\+[1-9]\d{1,11}"
              title="Phone number must be in E.164 format, e.g. +14556801189"
              placeholder="+14556801189"
              maxLength={13}
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Address
            <input
              value={values.address}
              onChange={(event) => setValues({ ...values, address: event.target.value })}
              required
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

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
              className="min-h-11 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-300"
            >
              {isSubmitting ? 'Saving...' : isEdit ? 'Save changes' : 'Add customer'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
