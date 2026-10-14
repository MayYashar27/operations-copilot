import type { DailyTrendItem } from '../api/types'
import { formatDateShort } from './format'

export interface SuggestedQuestion {
  /** Short label for a chip or list item. */
  label: string
  /** The full question sent to Copilot. ISO dates keep the agent's tool calls precise. */
  question: string
  /** Why this question is suggested, shown as context. */
  reason: string
}

const hourRange = (hour: string) => hour.split('-') as [string, string]

/**
 * Questions answerable with the Copilot's existing tools (request counts,
 * classifications, statuses, transfers, wait times, monitor metrics, request
 * details). Built from real data only: unusual hours come from the API.
 */
export function suggestedQuestions(date: string, trend: DailyTrendItem[]): SuggestedQuestion[] {
  const questions: SuggestedQuestion[] = []

  const unusual = trend
    .flatMap((day) => day.unusual_hours.map((hour) => ({ date: day.date, ...hour })))
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, 2)

  for (const item of unusual) {
    const [start, end] = hourRange(item.hour)
    questions.push({
      label: `Why did volume spike on ${formatDateShort(item.date)}, ${start}–${end}?`,
      question: `There was an unusually high workload on ${item.date} between ${start} and ${end}. Investigate what happened and explain the likely cause.`,
      reason: `${item.requests} requests, ${item.ratio_to_average}× the hourly average`,
    })
  }

  const previous = [...trend].reverse().find((day) => day.date < date)

  questions.push({
    label: 'Which request types drove today’s workload?',
    question: `Which request classifications drove the workload on ${date}, and how were those requests resolved or transferred?`,
    reason: 'Classification and status breakdown',
  })

  if (previous) {
    questions.push({
      label: `How did customer wait time compare with ${formatDateShort(previous.date)}?`,
      question: `Compare customer wait time on ${date} with ${previous.date}. In which hours was the difference largest, and what operational conditions were associated with it?`,
      reason: 'Wait time and monitor metrics, two days',
    })
  }

  questions.push({
    label: 'Where were transferred requests sent today?',
    question: `On ${date}, how many requests were transferred, to which destinations, and which request classifications were most often transferred?`,
    reason: 'Transfer destinations by classification',
  })

  return questions
}

/** Link to Ask Copilot with the question pre-filled (never auto-submitted). */
export function copilotLink(question: string, date: string | null): string {
  const params = new URLSearchParams({ q: question })
  if (date) params.set('date', date)
  return `/copilot?${params.toString()}`
}
