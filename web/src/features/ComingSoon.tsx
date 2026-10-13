import { ArrowLeft, Construction } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useDatedLink } from '../app/context'
import { PageHeader } from '../components/layout/PageHeader'
import { Panel } from '../components/ui/Panel'
import { EmptyState } from '../components/ui/States'

/** Temporary placeholder for screens built in the next steps. */
export function ComingSoon({ title }: { title: string }) {
  const { agentId } = useParams()
  const datedLink = useDatedLink()

  return (
    <>
      <PageHeader eyebrow={agentId ? 'Agent' : undefined} title={agentId ? `Agent ${agentId}` : title} />
      <Panel>
        <EmptyState
          icon={Construction}
          title={`${title} is being built next`}
          action={
            <Link to={datedLink('/')} className="btn-secondary">
              <ArrowLeft className="size-3.5" /> Back to dashboard
            </Link>
          }
        />
      </Panel>
    </>
  )
}
