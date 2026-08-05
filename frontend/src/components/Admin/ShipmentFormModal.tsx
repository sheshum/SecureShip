import { type FormEvent, useEffect, useState } from 'react'
import { useSearchCustomersApiCustomersSearchGet } from '../../api/generated/client'
import type { ShipmentItem } from '../../api/generated/schemas'

const STATUS_OPTIONS = ['label_created', 'in_transit', 'out_for_delivery', 'delivered', 'exception'] as const

export type ShipmentFormValues = {
  customer_id: string
  tracking_number: string
  status: string
  carrier: string
  origin: string
  destination: string
  estimated_delivery: string
}

type ShipmentFormModalProps = {
  isOpen: boolean
  isSubmitting: boolean
  errorMessage: string | null
  initialValues?: ShipmentItem
  onSubmit: (values: ShipmentFormValues) => Promise<void> | void
  onClose: () => void
}

const EMPTY_VALUES: ShipmentFormValues = {
  customer_id: '',
  tracking_number: '',
  status: STATUS_OPTIONS[0],
  carrier: '',
  origin: '',
  destination: '',
  estimated_delivery: '',
}

export function ShipmentFormModal({
  isOpen,
  isSubmitting,
  errorMessage,
  initialValues,
  onSubmit,
  onClose,
}: ShipmentFormModalProps) {
  const [values, setValues] = useState<ShipmentFormValues>(EMPTY_VALUES)
  const isEdit = Boolean(initialValues)

  const [customerQuery, setCustomerQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [showCustomerResults, setShowCustomerResults] = useState(false)
  const [customerSelectionError, setCustomerSelectionError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      setValues(
        initialValues
          ? {
              customer_id: initialValues.customer_id,
              tracking_number: initialValues.tracking_number,
              status: initialValues.status,
              carrier: initialValues.carrier,
              origin: initialValues.origin,
              destination: initialValues.destination,
              estimated_delivery: initialValues.estimated_delivery.slice(0, 10),
            }
          : EMPTY_VALUES,
      )
      setCustomerQuery('')
      setShowCustomerResults(false)
      setCustomerSelectionError(null)
    }
  }, [isOpen, initialValues])

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedQuery(customerQuery.trim()), 300)
    return () => clearTimeout(timeout)
  }, [customerQuery])

  const { data: customerSearchResponse } = useSearchCustomersApiCustomersSearchGet(
    { q: debouncedQuery, limit: 10 },
    { query: { enabled: debouncedQuery.length >= 2 } },
  )
  const customerResults = Array.isArray(customerSearchResponse?.data) ? customerSearchResponse.data : []

  if (!isOpen) {
    return null
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!isEdit && !values.customer_id) {
      setCustomerSelectionError('Select a customer from the search results')
      return
    }
    setCustomerSelectionError(null)
    await onSubmit(values)
  }

  const inputClass =
    'min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-normal normal-case tracking-normal text-slate-900 focus:border-sky-400 focus:outline-none disabled:bg-slate-100'
  const labelClass = 'flex flex-col gap-1 text-xs font-semibold uppercase tracking-[0.08em] text-slate-600'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/55"
        onClick={onClose}
        aria-label="Close modal"
      />

      <section className="relative w-full max-w-lg rounded-2xl border border-white/65 bg-white p-5 shadow-[0_24px_80px_rgba(15,23,42,0.28)]">
        <h3 className="text-lg font-semibold text-slate-900">{isEdit ? 'Edit Shipment' : 'Add Shipment'}</h3>

        <form className="mt-4 grid grid-cols-2 gap-3" onSubmit={handleSubmit}>
          <label className={`${labelClass} relative col-span-2`}>
            Customer
            {isEdit ? (
              <span className="min-h-11 rounded-xl border border-slate-200 bg-slate-100 px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-slate-600">
                {initialValues?.customer_name || '—'}
              </span>
            ) : (
              <>
                <input
                  value={customerQuery}
                  onChange={(event) => {
                    setCustomerQuery(event.target.value)
                    setValues({ ...values, customer_id: '' })
                    setShowCustomerResults(true)
                  }}
                  onFocus={() => setShowCustomerResults(true)}
                  required
                  disabled={isSubmitting}
                  placeholder="Search by name or phone"
                  autoComplete="off"
                  className={inputClass}
                />
                {showCustomerResults && customerResults.length > 0 ? (
                  <ul className="absolute top-full z-10 mt-1 w-full rounded-xl border border-slate-200 bg-white shadow-lg">
                    {customerResults.map((customer) => (
                      <li key={customer.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setValues({ ...values, customer_id: customer.id })
                            setCustomerQuery(`${customer.first_name} ${customer.last_name} — ${customer.phone_number}`)
                            setShowCustomerResults(false)
                          }}
                          className="w-full px-3 py-2 text-left text-sm font-normal normal-case tracking-normal text-slate-900 hover:bg-slate-100"
                        >
                          {customer.first_name} {customer.last_name} — {customer.phone_number}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {customerSelectionError ? (
                  <span className="text-xs font-normal normal-case tracking-normal text-rose-700">
                    {customerSelectionError}
                  </span>
                ) : null}
              </>
            )}
          </label>

          <label className={labelClass}>
            Tracking Number
            <input
              value={values.tracking_number}
              onChange={(event) => setValues({ ...values, tracking_number: event.target.value })}
              required
              disabled={isSubmitting}
              className={inputClass}
            />
          </label>

          <label className={labelClass}>
            Status
            <select
              value={values.status}
              onChange={(event) => setValues({ ...values, status: event.target.value })}
              disabled={isSubmitting}
              className={inputClass}
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </label>

          <label className={labelClass}>
            Carrier
            <input
              value={values.carrier}
              onChange={(event) => setValues({ ...values, carrier: event.target.value })}
              required
              disabled={isSubmitting}
              className={inputClass}
            />
          </label>

          <label className={labelClass}>
            Estimated Delivery
            <input
              type="date"
              value={values.estimated_delivery}
              onChange={(event) => setValues({ ...values, estimated_delivery: event.target.value })}
              required
              disabled={isSubmitting}
              className={inputClass}
            />
          </label>

          <label className={labelClass}>
            Origin
            <input
              value={values.origin}
              onChange={(event) => setValues({ ...values, origin: event.target.value })}
              required
              disabled={isSubmitting}
              className={inputClass}
            />
          </label>

          <label className={labelClass}>
            Destination
            <input
              value={values.destination}
              onChange={(event) => setValues({ ...values, destination: event.target.value })}
              required
              disabled={isSubmitting}
              className={inputClass}
            />
          </label>

          {errorMessage ? <p className="col-span-2 text-sm text-rose-700">{errorMessage}</p> : null}

          <div className="col-span-2 flex items-center justify-end gap-2 pt-1">
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
              {isSubmitting ? 'Saving...' : isEdit ? 'Save changes' : 'Add shipment'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
