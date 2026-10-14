const EM_DASH = '—'

/** Parse "YYYY-MM-DD" as a calendar date (no timezone shift). */
function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function formatDateLong(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

export function formatDateShort(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function formatDateOption(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  })
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return EM_DASH
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? EM_DASH : `${formatNumber(value, digits)}%`
}

export function formatMinutes(value: number | null | undefined): string {
  return value === null || value === undefined ? EM_DASH : `${formatNumber(value, 1)} min`
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export function formatWeekdayShort(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-GB', { weekday: 'short' })
}

export function formatDayMonth(iso: string): string {
  return parseDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

/** Relative change in percent, or null when there is no baseline. */
export function percentChange(current: number | null, baseline: number | null): number | null {
  if (current === null || baseline === null || baseline === 0) return null
  return ((current - baseline) / baseline) * 100
}

export function average(values: (number | null)[]): number | null {
  const present = values.filter((v): v is number => v !== null)
  return present.length ? present.reduce((sum, v) => sum + v, 0) / present.length : null
}

/** "14 Oct, 13:02" for a full ISO timestamp, in the viewer's time zone. */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export function isToday(iso: string): boolean {
  return new Date(iso).toDateString() === new Date().toDateString()
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m ? `${m}m ${s.toString().padStart(2, '0')}s` : `${s}s`
}
