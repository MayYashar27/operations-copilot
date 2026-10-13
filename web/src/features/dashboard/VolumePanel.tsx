import { useState } from 'react'
import type { VolumeProfile } from '../../api/types'
import { HourlyVolumeChart } from '../../components/charts/HourlyVolumeChart'
import { Panel } from '../../components/ui/Panel'
import { SegmentedControl } from '../../components/ui/SegmentedControl'
import { EmptyState } from '../../components/ui/States'
import { formatNumber } from '../../lib/format'

export function VolumePanel({ profile }: { profile: VolumeProfile | null }) {
  const [view, setView] = useState<'chart' | 'table'>('chart')

  if (!profile) {
    return (
      <Panel title="Requests by hour">
        <EmptyState title="No hourly data for this day" />
      </Panel>
    )
  }

  const unusual = profile.hours.filter((h) => h.above_threshold)
  const summary = unusual.length
    ? `${unusual.length} unusual ${unusual.length === 1 ? 'hour' : 'hours'}: ${unusual.map((h) => h.hour.replace('-', '–')).join(', ')}`
    : 'No unusual hours'

  return (
    <Panel
      title="Requests by hour"
      description={
        <>
          Average {formatNumber(profile.average_hourly_requests, 1)} per hour. Hours at or above{' '}
          {profile.threshold_multiplier}× the average are marked unusual. <span className="text-ink-2">{summary}.</span>
        </>
      }
      actions={
        <SegmentedControl
          label="View"
          value={view}
          onChange={setView}
          options={[{ value: 'chart', label: 'Chart' }, { value: 'table', label: 'Table' }]}
        />
      }
    >
      {view === 'chart' ? (
        <HourlyVolumeChart profile={profile} />
      ) : (
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-[12px] text-ink-3">
              <th className="pb-2 font-medium">Hour</th>
              <th className="pb-2 text-right font-medium">Requests</th>
              <th className="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line-soft">
            {profile.hours.map((hour) => (
              <tr key={hour.hour}>
                <td className="py-1.5 tabular">{hour.hour.replace('-', ' – ')}</td>
                <td className="py-1.5 text-right font-medium tabular">{hour.requests}</td>
                <td className="py-1.5 text-right text-ink-3">{hour.above_threshold ? 'Unusual' : 'Typical'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  )
}
