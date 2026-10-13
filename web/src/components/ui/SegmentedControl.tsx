interface Option<T extends string> {
  value: T
  label: string
  count?: number
}

interface SegmentedControlProps<T extends string> {
  label: string
  value: T
  options: Option<T>[]
  onChange: (value: T) => void
}

/** A compact set of mutually exclusive buttons (view switches, filters). */
export function SegmentedControl<T extends string>({ label, value, options, onChange }: SegmentedControlProps<T>) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg bg-line-soft p-0.5">
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[12.5px] font-medium whitespace-nowrap transition-colors ${
              selected ? 'bg-surface text-ink shadow-panel' : 'text-ink-2 hover:text-ink'
            }`}
          >
            {option.label}
            {option.count !== undefined && (
              <span className={`tabular ${selected ? 'text-ink-3' : 'text-ink-3/80'}`}>{option.count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
