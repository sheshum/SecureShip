import { type FormEvent, useEffect, useState } from 'react'
import type { PackageItem } from '../../api/generated/schemas'

export type PackageFormValues = {
  tracking_number: string
  description: string
  weight_kg: string
  declared_value: string
}

type PackageFormModalProps = {
  isOpen: boolean
  isSubmitting: boolean
  errorMessage: string | null
  initialValues?: PackageItem
  onSubmit: (values: PackageFormValues) => Promise<void> | void
  onClose: () => void
}

const EMPTY_VALUES: PackageFormValues = {
  tracking_number: '',
  description: '',
  weight_kg: '',
  declared_value: '',
}

export function PackageFormModal({
  isOpen,
  isSubmitting,
  errorMessage,
  initialValues,
  onSubmit,
  onClose,
}: PackageFormModalProps) {
  const [values, setValues] = useState<PackageFormValues>(EMPTY_VALUES)
  const isEdit = Boolean(initialValues)

  useEffect(() => {
    if (isOpen) {
      setValues(
        initialValues
          ? {
              tracking_number: initialValues.shipment_tracking_number ?? '',
              description: initialValues.description,
              weight_kg: initialValues.weight_kg,
              declared_value: initialValues.declared_value,
            }
          : EMPTY_VALUES,
      )
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
        <h3 className="text-lg font-semibold text-slate-900">{isEdit ? 'Edit Package' : 'Add Package'}</h3>

        <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Shipment
            {isEdit ? (
              <span className="min-h-11 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-slate-600">
                {values.tracking_number || '—'}
              </span>
            ) : (
              <input
                value={values.tracking_number}
                onChange={(event) => setValues({ ...values, tracking_number: event.target.value })}
                required
                disabled={isSubmitting}
                placeholder="Tracking number"
                className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none disabled:bg-slate-100"
              />
            )}
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Description
            <input
              value={values.description}
              onChange={(event) => setValues({ ...values, description: event.target.value })}
              required
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Weight (kg)
            <input
              type="number"
              step="0.01"
              min="0"
              value={values.weight_kg}
              onChange={(event) => setValues({ ...values, weight_kg: event.target.value })}
              required
              disabled={isSubmitting}
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
            Declared Value ($)
            <input
              type="number"
              step="0.01"
              min="0"
              value={values.declared_value}
              onChange={(event) => setValues({ ...values, declared_value: event.target.value })}
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
              {isSubmitting ? 'Saving...' : isEdit ? 'Save changes' : 'Add package'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
