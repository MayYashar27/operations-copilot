import { Outlet } from 'react-router-dom'
import { useAppContext } from '../../app/context'
import { Rail } from './Rail'

/**
 * The workspace frame: a softly rounded shell on a periwinkle backdrop,
 * holding the icon rail and the current screen. Screens render their own
 * <Workspace> (side panel + main area) inside it.
 */
export function AppShell() {
  const { config } = useAppContext()

  return (
    <div className="flex min-h-screen flex-col lg:h-screen lg:p-3">
      <div className="flex min-h-0 flex-1 flex-col gap-3 bg-frame p-3 lg:flex-row lg:rounded-[28px] lg:shadow-[0_20px_60px_rgb(60_70_140/0.18)] lg:ring-1 lg:ring-white/60">
        <Rail />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <Outlet />
          {config && (
            <p className="px-2 pt-2.5 text-center text-[11.5px] text-ink-3">{config.disclaimer}</p>
          )}
        </div>
      </div>
    </div>
  )
}
