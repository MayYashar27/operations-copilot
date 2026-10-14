import { BarChart3, Table2 } from 'lucide-react'
import { useState } from 'react'
import type { HourlyActivity } from '../../api/types'
import { ACTIVITY_METRICS, type ActivityMetric } from '../../components/charts/activityMetrics'
import { ShiftActivityChart } from '../../components/charts/ShiftActivityChart'
import { Panel } from '../../components/ui/Panel'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { EmptyState } from '../../components/ui/States'
import { formatNumber } from '../../lib/format'

export function ActivityPanel({ hours, baselineDays }: { hours: HourlyActivity[]; baselineDays: number }) {
  const [metric, setMetric] = useState<ActivityMetric>('requests')
  const [asTable, setAsTable] = useState(false)
  const spec = ACTIVITY_METRICS[metric]
  const unusual = hours.filter((h) => h.above_threshold)

  return (
    <Panel
      title="Shift activity"
      description={
        unusual.length
          ? `${unusual.length} unusual ${unusual.length === 1 ? 'hour' : 'hours'} today: ${unusual.map((h) => h.hour.replace('-', '–')).join(', ')}`
          : 'No unusual hours today. Hover any hour to compare it with a typical day.'
      }
      actions={
        <>
          <SegmentedControl
            label="Metric"
            value={metric}
            onChange={setMetric}
            options={(Object.keys(ACTIVITY_METRICS) as ActivityMetric[]).map((m) => ({ value: m, label: ACTIVITY_METRICS[m].label }))}
          />
          <button
            type="button"
            onClick={() => setAsTable((v) => !v)}
            className="btn-ghost size-8 justify-center px-0"
            aria-label={asTable ? 'Show chart' : 'Show table'}
            title={asTable ? 'Show chart' : 'Show table'}
          >
            {asTable ? <BarChart3 className="size-4" /> : <Table2 className="size-4" />}
          </button>
        </>
      }
    >
      {hours.length === 0 ? (
        <EmptyState title="No hourly data for this day" />
      ) : (
        <>
          <div className="mb-3 flex items-center gap-4 text-[12px] text-ink-2">
            <span className="inline-flex items-center gap-1.5">
              <span className={`size-2.5 ${spec.form === 'bar' ? 'rounded-[2px]' : 'rounded-full'} bg-chart-today`} /> Today
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-0.5 w-3.5 rounded-full bg-chart-typical" /> Typical ({baselineDays} earlier days)
            </span>
            {metric === 'requests' && unusual.length > 0 && (
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2.5 rounded-[2px] bg-chart-unusual" /> Unusual hour
              </span>
            )}
          </div>
          {asTable ? (
            <table className="w-full text-[13px]">
              <thead>
                <tr className="text-left text-[12px] text-ink-3">
                  <th className="pb-2 font-medium">Hour</th>
                  <th className="pb-2 text-right font-medium">Today</th>
                  <th className="pb-2 text-right font-medium">Typical</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {hours.map((h) => (
                  <tr key={h.hour}>
                    <td className="py-1.5 tabular">{h.hour.replace('-', ' – ')}</td>
                    <td className="py-1.5 text-right font-medium tabular">{formatNumber(spec.today(h), spec.digits)}</td>
                    <td className="py-1.5 text-right text-ink-2 tabular">{formatNumber(spec.typical(h), spec.digits)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <ShiftActivityChart hours={hours} metric={metric} />
          )}
        </>
      )}
    </Panel>
  )
}
