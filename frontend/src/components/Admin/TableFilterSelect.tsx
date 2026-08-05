type Option = { value: string; label: string }

type TableFilterSelectProps = {
  value: string
  onChange: (value: string) => void
  options: readonly Option[]
  allLabel?: string
}

export function TableFilterSelect({ value, onChange, options, allLabel = 'All' }: TableFilterSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-sky-400 focus:outline-none"
    >
      <option value="">{allLabel}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}
