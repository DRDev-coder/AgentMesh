import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  BookOpen,
  Braces,
  ChevronDown,
  CreditCard,
  FileSearch,
  Gauge,
  KeyRound,
  LogOut,
  MessageSquare,
  Settings,
  SlidersHorizontal,
  Users,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { saasRequest, type Organization, type Workspace } from '../lib/saas-api'
import { MeshMark } from './AppShell'

const NAVIGATION = [
  { path: 'overview', label: 'Overview', description: 'Workspace pulse', icon: Gauge },
  { path: 'playground', label: 'Playground', description: 'Test a decision', icon: MessageSquare, roles: ['owner', 'admin', 'developer'] },
  { path: 'knowledge', label: 'Knowledge', description: 'Documents & releases', icon: BookOpen },
  { path: 'configuration', label: 'Configuration', description: 'Profile & controls', icon: SlidersHorizontal },
  { path: 'decisions', label: 'Decisions', description: 'Evidence records', icon: FileSearch },
  { path: 'reviews', label: 'Human review', description: 'Escalation queue', icon: Users, roles: ['owner', 'admin', 'reviewer'] },
  { path: 'developers', label: 'Developers', description: 'Keys & webhooks', icon: Braces, roles: ['owner', 'admin', 'developer'] },
  { path: 'usage', label: 'Usage & billing', description: 'Meter & invoices', icon: CreditCard, roles: ['owner', 'admin', 'developer', 'viewer'] },
  { path: 'team', label: 'Team', description: 'Members & access', icon: KeyRound, roles: ['owner', 'admin'] },
  { path: 'settings', label: 'Settings', description: 'Workspace policy', icon: Settings, roles: ['owner', 'admin'] },
]

export interface WorkspaceRouteContext {
  organization: Organization
  workspace: Workspace
  organizations: Organization[]
  workspaces: Workspace[]
  basePath: string
}

export default function SaaSShell() {
  const auth = useAuth()
  const params = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const organizationsQuery = useQuery({
    queryKey: ['organizations'],
    queryFn: () => saasRequest<Organization[]>('/organizations'),
  })
  const organization = organizationsQuery.data?.find((value) => value.slug === params.orgSlug)
  const workspacesQuery = useQuery({
    queryKey: ['workspaces', organization?.id],
    queryFn: () => saasRequest<Workspace[]>(`/organizations/${organization!.id}/workspaces`),
    enabled: Boolean(organization),
  })
  const workspace = workspacesQuery.data?.find((value) => value.slug === params.workspaceSlug)

  if (organizationsQuery.isLoading || workspacesQuery.isLoading) {
    return <div className="fullscreen-loading"><span className="spin" /> Loading workspace…</div>
  }
  if (!organization || !workspace) {
    return <div className="fullscreen-loading">Workspace not found.</div>
  }

  const basePath = `/app/${organization.slug}/${workspace.slug}`
  const availableNavigation = NAVIGATION.filter((item) => !item.roles || item.roles.includes(organization.role))
  const activeNav = availableNavigation.find((item) => location.pathname.includes(`/${item.path}`)) || availableNavigation[0]
  const activeIndex = availableNavigation.indexOf(activeNav) + 1

  const changeWorkspace = (workspaceId: string) => {
    const next = workspacesQuery.data?.find((value) => value.id === workspaceId)
    if (next) navigate(`/app/${organization.slug}/${next.slug}/overview`)
  }

  const context: WorkspaceRouteContext = {
    organization,
    workspace,
    organizations: organizationsQuery.data || [],
    workspaces: workspacesQuery.data || [],
    basePath,
  }

  return (
    <div className="app-shell saas-shell">
      <aside className="desktop-sidebar">
        <div className="brand-lockup">
          <MeshMark />
          <div><strong>AgentMesh</strong><span>Decision infrastructure</span></div>
        </div>
        <div className="workspace-wrap">
          <label className="workspace-switcher real-switcher">
            <span><small>Workspace</small><strong>{workspace.name}</strong></span>
            <select value={workspace.id} onChange={(event) => changeWorkspace(event.target.value)} aria-label="Select workspace">
              {workspacesQuery.data?.map((value) => <option value={value.id} key={value.id}>{value.name}</option>)}
            </select>
            <ChevronDown size={13} />
          </label>
        </div>
        <nav className="sidebar-nav" aria-label="Product navigation">
          <p className="nav-label">Workspace</p>
          <ul>
            {availableNavigation.map((item, index) => {
              const Icon = item.icon
              return (
                <li key={item.path}>
                  <NavLink to={`${basePath}/${item.path}`} className={({ isActive }) => isActive ? 'active' : ''}>
                    <span className="nav-number">{String(index + 1).padStart(2, '0')}</span>
                    <Icon size={15} />
                    <span className="nav-copy"><strong>{item.label}</strong><small>{item.description}</small></span>
                  </NavLink>
                </li>
              )
            })}
          </ul>
        </nav>
        <section className="mesh-summary">
          <div className="mesh-summary-heading"><span><i className="mesh-status-dot success" />Workspace active</span><span>v3</span></div>
          <dl>
            <div><dt>Template</dt><dd>{workspace.industry_template}</dd></div>
            <div><dt>Role</dt><dd>{organization.role}</dd></div>
            <div><dt>Env</dt><dd>Cloud</dd></div>
          </dl>
        </section>
        <div className="sidebar-footer">
          <button type="button" onClick={() => void auth.signOut()}><LogOut size={13} />Sign out</button>
          <span>{auth.user?.email}</span>
        </div>
      </aside>
      <div className="app-frame">
        <main className="app-content">
          <header className="app-header">
            <div className="page-title-block">
              <div className="page-kicker"><span>№ {String(activeIndex).padStart(2, '0')}</span><i /><span>{organization.name}</span></div>
              <h1>{activeNav.label}</h1>
              <p>{activeNav.description} for {workspace.name}.</p>
            </div>
            <div className="header-actions"><span className="tenant-role"><Activity size={14} />{organization.role}</span></div>
          </header>
          <Outlet context={context} />
        </main>
      </div>
    </div>
  )
}
