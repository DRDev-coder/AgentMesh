import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  ArrowLeft,
  BarChart3,
  Building2,
  ChevronDown,
  Heart,
  LayoutGrid,
  LogOut,
  RefreshCw,
  Search,
  Server,
  Settings,
  ShieldCheck,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { MeshMark } from '../components/AppShell'
import { saasRequest, SaaSApiError } from '../lib/saas-api'

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */
interface PlatformMetrics {
  organizations: number
  decisions: number
  failed_billing_events: number
  failed_jobs: number
  failed_webhooks: number
  failed_emails: number
}

interface PlatformOrganization {
  id: string
  name: string
  slug: string
  status: string
  billing_email: string
  created_at: string
}

interface PlatformHealth {
  postgresql: boolean
  redis: boolean
  pending_jobs: number
  pending_billing_events: number
}

interface PlatformTemplate {
  id: string
  name: string
  version: number
  mandatory_rule_keys: string[]
  enabled: boolean
}

/* ------------------------------------------------------------------ */
/*  Sidebar navigation config                                        */
/* ------------------------------------------------------------------ */
const ADMIN_NAV = [
  { id: 'overview', label: 'Overview', description: 'Platform metrics', icon: LayoutGrid },
  { id: 'organizations', label: 'Organizations', description: 'Tenant directory', icon: Building2 },
  { id: 'health', label: 'Service health', description: 'Runtime dependencies', icon: Heart },
  { id: 'templates', label: 'Templates', description: 'Industry controls', icon: Settings },
]

/* ------------------------------------------------------------------ */
/*  Error notice                                                     */
/* ------------------------------------------------------------------ */
function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <div className="alert danger">
      <strong>{error instanceof SaaSApiError ? error.code.replaceAll('_', ' ') : 'Request failed'}</strong>
      <p>{error instanceof Error ? error.message : 'An unexpected error occurred.'}</p>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Sub-views                                                        */
/* ------------------------------------------------------------------ */
function OverviewView({ metrics }: { metrics: PlatformMetrics | undefined }) {
  return (
    <>
      <section className="metric-grid">
        <article>
          <span>Organizations</span>
          <strong>{metrics?.organizations ?? '—'}</strong>
          <small>Active tenants</small>
        </article>
        <article>
          <span>Completed decisions</span>
          <strong>{metrics?.decisions ?? '—'}</strong>
          <small>All time</small>
        </article>
        <article>
          <span>Billing failures</span>
          <strong>{metrics?.failed_billing_events ?? '—'}</strong>
          <small>Needs attention</small>
        </article>
        <article>
          <span>Operational failures</span>
          <strong>{(metrics?.failed_jobs ?? 0) + (metrics?.failed_webhooks ?? 0) + (metrics?.failed_emails ?? 0)}</strong>
          <small>Jobs + webhooks + emails</small>
        </article>
      </section>
      <div className="admin-overview-grid">
        <article className="panel-card">
          <header>
            <div>
              <p className="eyebrow">Quick actions</p>
              <h2>Platform operations</h2>
            </div>
          </header>
          <div className="admin-quick-actions">
            <button className="button secondary"><RefreshCw size={14} /> Refresh all caches</button>
            <button className="button secondary"><BarChart3 size={14} /> Export usage report</button>
            <button className="button secondary"><ShieldCheck size={14} /> Run security audit</button>
          </div>
        </article>
        <article className="panel-card">
          <header>
            <div>
              <p className="eyebrow">System status</p>
              <h2>Activity feed</h2>
            </div>
          </header>
          <div className="admin-activity-feed">
            <div className="admin-activity-item">
              <span className="admin-activity-dot success" />
              <div><strong>System operational</strong><small>All services running normally</small></div>
              <time>Now</time>
            </div>
            <div className="admin-activity-item">
              <span className="admin-activity-dot info" />
              <div><strong>Metrics refreshed</strong><small>Dashboard metrics updated</small></div>
              <time>2m ago</time>
            </div>
            <div className="admin-activity-item">
              <span className="admin-activity-dot warning" />
              <div><strong>Billing sync</strong><small>Stripe webhook processing</small></div>
              <time>15m ago</time>
            </div>
          </div>
        </article>
      </div>
    </>
  )
}

function OrganizationsView({ organizations }: { organizations: PlatformOrganization[] | undefined }) {
  const [search, setSearch] = useState('')
  const filtered = organizations?.filter(
    (org) =>
      org.name.toLowerCase().includes(search.toLowerCase()) ||
      org.slug.toLowerCase().includes(search.toLowerCase()) ||
      org.billing_email.toLowerCase().includes(search.toLowerCase()),
  )
  return (
    <section className="panel-card">
      <header>
        <div>
          <p className="eyebrow">Tenant directory</p>
          <h2>Organizations</h2>
        </div>
        <div className="admin-search-wrap">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search organizations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="admin-search-input"
          />
        </div>
      </header>
      <div className="resource-table-wrap">
        <table className="resource-table">
          <thead>
            <tr>
              <th>Organization</th>
              <th>Status</th>
              <th>Billing email</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {filtered?.length === 0 && (
              <tr><td colSpan={4} className="admin-empty-cell">No organizations match your search.</td></tr>
            )}
            {filtered?.map((org) => (
              <tr key={org.id}>
                <td>
                  <strong>{org.name}</strong>
                  <small>{org.slug}</small>
                </td>
                <td>
                  <span className={`state-pill ${org.status === 'active' ? 'published' : ''}`}>
                    {org.status.toUpperCase()}
                  </span>
                </td>
                <td>{org.billing_email}</td>
                <td>{new Date(org.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function HealthView({ health }: { health: PlatformHealth | undefined }) {
  const services = [
    { name: 'PostgreSQL', status: health?.postgresql, description: 'Primary data store' },
    { name: 'Redis', status: health?.redis, description: 'Cache and job queue' },
  ]
  return (
    <div className="admin-health-grid">
      {services.map((service) => (
        <article key={service.name} className="panel-card admin-health-card">
          <div className="admin-health-indicator">
            <Server size={18} />
            <span className={`admin-health-dot ${service.status ? 'up' : 'down'}`} />
          </div>
          <h3>{service.name}</h3>
          <p>{service.description}</p>
          <span className={`state-pill ${service.status ? 'published' : 'rejected'}`}>
            {service.status ? 'READY' : 'UNAVAILABLE'}
          </span>
        </article>
      ))}
      <article className="panel-card admin-health-card">
        <div className="admin-health-indicator">
          <Activity size={18} />
          <span className="admin-health-dot up" />
        </div>
        <h3>Job queue</h3>
        <p>Background worker tasks</p>
        <dl className="admin-health-dl">
          <div><dt>Pending jobs</dt><dd>{health?.pending_jobs ?? '—'}</dd></div>
          <div><dt>Pending billing</dt><dd>{health?.pending_billing_events ?? '—'}</dd></div>
        </dl>
      </article>
    </div>
  )
}

function TemplatesView({ templates }: { templates: PlatformTemplate[] | undefined }) {
  return (
    <section className="panel-card">
      <header>
        <div>
          <p className="eyebrow">Curated controls</p>
          <h2>Industry templates</h2>
        </div>
      </header>
      <div className="admin-template-list">
        {templates?.map((template) => (
          <div key={template.id} className="admin-template-item">
            <div className="admin-template-version">
              <span className="version-number">v{template.version}</span>
            </div>
            <div className="admin-template-info">
              <strong>{template.name}</strong>
              <small>Mandatory rules: {template.mandatory_rule_keys.join(', ') || 'None'}</small>
            </div>
            <span className={`state-pill ${template.enabled ? 'published' : ''}`}>
              {template.enabled ? 'ACTIVE' : 'DISABLED'}
            </span>
          </div>
        ))}
        {(!templates || templates.length === 0) && (
          <div className="admin-template-empty">No templates configured.</div>
        )}
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/*  Admin Dashboard                                                  */
/* ------------------------------------------------------------------ */
export default function AdminDashboard() {
  const auth = useAuth()
  const [activeView, setActiveView] = useState('overview')

  const metrics = useQuery({
    queryKey: ['platform-metrics'],
    queryFn: () => saasRequest<PlatformMetrics>('/platform/metrics'),
  })
  const organizations = useQuery({
    queryKey: ['platform-organizations'],
    queryFn: () => saasRequest<PlatformOrganization[]>('/platform/organizations'),
  })
  const health = useQuery({
    queryKey: ['platform-health'],
    queryFn: () => saasRequest<PlatformHealth>('/platform/service-health'),
  })
  const templates = useQuery({
    queryKey: ['platform-templates'],
    queryFn: () => saasRequest<PlatformTemplate[]>('/platform/templates'),
  })

  const activeNav = ADMIN_NAV.find((item) => item.id === activeView) || ADMIN_NAV[0]
  const activeIndex = ADMIN_NAV.indexOf(activeNav) + 1

  const handleRefreshAll = () => {
    void metrics.refetch()
    void organizations.refetch()
    void health.refetch()
    void templates.refetch()
  }

  return (
    <div className="app-shell admin-shell">
      {/* ── Sidebar ── */}
      <aside className="desktop-sidebar">
        <div className="brand-lockup">
          <MeshMark />
          <div>
            <strong>AgentMesh</strong>
            <span>Platform admin</span>
          </div>
        </div>

        <div className="workspace-wrap">
          <div className="workspace-switcher admin-role-badge">
            <span>
              <small>Role</small>
              <strong>Platform administrator</strong>
            </span>
            <ShieldCheck size={13} />
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Admin navigation">
          <p className="nav-label">Platform</p>
          <ul>
            {ADMIN_NAV.map((item, index) => {
              const Icon = item.icon
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={activeView === item.id ? 'active' : ''}
                    onClick={() => setActiveView(item.id)}
                    aria-current={activeView === item.id ? 'page' : undefined}
                  >
                    <span className="nav-number">{String(index + 1).padStart(2, '0')}</span>
                    <Icon size={15} />
                    <span className="nav-copy">
                      <strong>{item.label}</strong>
                      <small>{item.description}</small>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>

        <section className="mesh-summary">
          <div className="mesh-summary-heading">
            <span><i className="mesh-status-dot success" />System active</span>
            <span>v3</span>
          </div>
          <dl>
            <div><dt>Orgs</dt><dd>{metrics.data?.organizations ?? '—'}</dd></div>
            <div><dt>Decisions</dt><dd>{metrics.data?.decisions ?? '—'}</dd></div>
            <div><dt>Env</dt><dd>Cloud</dd></div>
          </dl>
        </section>

        <div className="sidebar-footer">
          <Link to="/dashboard" className="admin-back-link"><ArrowLeft size={13} /> Back to workspace</Link>
          <button type="button" onClick={() => void auth.signOut()}><LogOut size={13} /> Sign out</button>
          <span>{auth.user?.email}</span>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="app-frame">
        <main className="app-content">
          <header className="app-header">
            <div className="page-title-block">
              <div className="page-kicker">
                <span>№ {String(activeIndex).padStart(2, '0')}</span>
                <i />
                <span>Platform administration</span>
              </div>
              <h1>{activeNav.label}</h1>
              <p>{activeNav.description}</p>
            </div>
            <div className="header-actions">
              <button className="icon-button" onClick={handleRefreshAll} title="Refresh all data">
                <RefreshCw size={15} />
              </button>
              <span className="tenant-role"><ShieldCheck size={14} /> admin</span>
            </div>
          </header>

          <div className="saas-page admin-page">
            <ErrorNotice error={metrics.error || organizations.error || health.error || templates.error} />
            {activeView === 'overview' && <OverviewView metrics={metrics.data} />}
            {activeView === 'organizations' && <OrganizationsView organizations={organizations.data} />}
            {activeView === 'health' && <HealthView health={health.data} />}
            {activeView === 'templates' && <TemplatesView templates={templates.data} />}
          </div>
        </main>
      </div>
    </div>
  )
}
