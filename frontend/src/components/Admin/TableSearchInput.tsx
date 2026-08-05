type TableSearchInputProps = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function TableSearchInput({ value, onChange, placeholder = 'Search…' }: TableSearchInputProps) {
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-sky-400 focus:outline-none"
    />
  )
}
