import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Users } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { saasRequest, type Organization, type Workspace } from '../lib/saas-api'

export default function AcceptInvitePage() {
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const token = search.get('token') || ''
  const accept = useMutation({
    mutationFn: () => saasRequest<Organization>(`/invitations/accept?token=${encodeURIComponent(token)}`, { method: 'POST' }),
    onSuccess: async (organization) => {
      const workspaces = await saasRequest<Workspace[]>(`/organizations/${organization.id}/workspaces`)
      const workspace = workspaces[0]
      navigate(workspace ? `/app/${organization.slug}/${workspace.slug}/overview` : '/')
    },
  })
  return <main className="onboarding-layout"><section className="onboarding-card completion-card"><span className="completion-mark"><Users size={24} /></span><p className="eyebrow">Team invitation</p><h1>Join this AgentMesh organization.</h1><p>Your verified email must match the invitation. Access is granted with the role selected by the organization administrator.</p>{accept.error && <div className="alert danger">{accept.error instanceof Error ? accept.error.message : 'Invitation could not be accepted.'}</div>}<button className="button primary" disabled={!token || accept.isPending} onClick={() => accept.mutate()}>{accept.isPending ? 'Joining…' : 'Accept invitation'} <ArrowRight size={15} /></button></section></main>
}
