import type { DailyTrendItem } from '../../api/types'
import { ShiftHeatmap } from '../../components/charts/ShiftHeatmap'
import { Panel } from '../../components/ui/Panel'

/** Recent shifts at a glance: color is volume, rose marks an unusual hour. */
export function RecentShiftsCard({ trend, date }: { trend: DailyTrendItem[]; date: string }) {
  const unusual = trend.reduce((n, d) => n + d.unusual_hours.length, 0)
  return (
    <Panel
      title="Recent shifts"
      description={`Requests per hour across the last ${trend.length} working days · ${unusual} unusual ${unusual === 1 ? 'hour' : 'hours'}`}
    >
      <ShiftHeatmap days={trend} selectedDate={date} />
    </Panel>
  )
}
