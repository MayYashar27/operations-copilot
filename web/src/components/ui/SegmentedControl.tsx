import { useLayoutEffect, useRef, useState } from 'react'

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

/** Mutually exclusive options with a white thumb that slides to the selection. */
export function SegmentedControl<T extends string>({ label, value, options, onChange }: SegmentedControlProps<T>) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([])
  const [thumb, setThumb] = useState<{ left: number; width: number } | null>(null)
  const index = options.findIndex((o) => o.value === value)

  useLayoutEffect(() => {
    const el = buttons.current[index]
    if (el) setThumb({ left: el.offsetLeft, width: el.offsetWidth })
  }, [index, options.length])

  return (
    <div role="radiogroup" aria-label={label} className="relative inline-flex rounded-xl bg-frame p-1">
      {thumb && (
        <span aria-hidden
          className="absolute top-1 bottom-1 rounded-[10px] bg-surface shadow-card transition-all duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)]"
          style={{ left: thumb.left, width: thumb.width }} />
      )}
      {options.map((option, i) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            ref={(el) => { buttons.current[i] = el }}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option.value)}
            className={`relative inline-flex h-8 items-center gap-1.5 rounded-[10px] px-3 text-[12.5px] font-semibold whitespace-nowrap transition-colors ${
              selected ? 'text-ink' : 'text-ink-3 hover:text-ink-2'
            }`}
          >
            {option.label}
            {option.count !== undefined && (
              <span className={`rounded-full px-1.5 text-[11px] tabular ${selected ? 'bg-accent-soft text-accent' : 'text-ink-3'}`}>
                {option.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
