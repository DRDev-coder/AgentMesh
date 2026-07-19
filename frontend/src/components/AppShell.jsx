import React from 'react'
import {
  Activity,
  ChevronDown,
  GitBranch,
  LifeBuoy,
  MessageSquare,
  Plus,
  Users,
} from 'lucide-react'

const NAV_ITEMS = [
  { id: 'chat', number: '01', label: 'Customer chat', description: 'Support channel', icon: MessageSquare },
  { id: 'trace', number: '02', label: 'Decision trace', description: 'Audit record', icon: GitBranch },
  { id: 'review', number: '03', label: 'Human review', description: 'Escalation queue', icon: Users },
  { id: 'status', number: '04', label: 'System status', description: 'Mesh telemetry', icon: Activity },
]

export function MeshMark({ size = 28, dark = true }) {
  const surface = dark ? '#111111' : '#FAF7F2'
  const ink = dark ? '#F4F0EA' : '#111111'
  return (
    <svg className="mesh-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect x="0.5" y="0.5" width="31" height="31" rx="2" fill={surface} stroke="#111111" />
      <g stroke={ink} strokeWidth="1" strokeLinecap="square" fill="none" opacity="0.9">
        <line x1="16" y1="16" x2="8" y2="8" />
        <line x1="16" y1="16" x2="24" y2="8" />
        <line x1="16" y1="16" x2="8" y2="24" />
        <line x1="16" y1="16" x2="24" y2="24" />
      </g>
      <g fill={ink}>
        <rect x="7" y="7" width="2" height="2" />
        <rect x="23" y="7" width="2" height="2" />
        <rect x="7" y="23" width="2" height="2" />
        <rect x="23" y="23" width="2" height="2" />
      </g>
      <rect x="13.5" y="13.5" width="5" height="5" fill="#EA3323" />
    </svg>
  )
}

function SidebarContent({ view, onNavigate, readiness, activeSession }) {
  const meshLabel = readiness.status === 'OPERATIONAL'
    ? 'Mesh online'
    : readiness.status === 'PENDING'
      ? 'Checking mesh'
      : readiness.status === 'DEGRADED'
        ? 'Mesh degraded'
        : 'Mesh unavailable'
  const meshTone = readiness.status === 'OPERATIONAL'
    ? 'success'
    : readiness.status === 'PENDING'
      ? 'pending'
      : 'danger'

  return (
    <>
      <div className="brand-lockup">
        <MeshMark />
        <div>
          <strong>AgentMesh</strong>
          <span>Risk-aware support</span>
        </div>
      </div>

      <div className="workspace-wrap">
        <button type="button" className="workspace-switcher" aria-label="Current workspace: Support, Demonstration">
          <span>
            <small>Workspace</small>
            <strong>Support &middot; Demonstration</strong>
          </span>
          <ChevronDown size={13} strokeWidth={2} aria-hidden="true" />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Primary navigation">
        <p className="nav-label">Sections</p>
        <ul>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <li key={item.id}>
              <button
                type="button"
                className={view === item.id ? 'active' : ''}
                aria-current={view === item.id ? 'page' : undefined}
                onClick={() => onNavigate(item.id)}
              >
                {view === item.id && <span className="active-rail" aria-hidden="true" />}
                <span className="nav-number">{item.number}</span>
                <Icon size={15} strokeWidth={1.5} aria-hidden="true" />
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

      <section className="mesh-summary" aria-label="System summary">
        <div className="mesh-summary-heading">
          <span><i className={`mesh-status-dot ${meshTone}`} aria-hidden="true" />{meshLabel}</span>
          <span>v3.2.0</span>
        </div>
        <dl>
          <div><dt>Decisions</dt><dd>{activeSession ? '1' : '0'}</dd></div>
          <div><dt>Queue</dt><dd>0</dd></div>
          <div><dt>Env</dt><dd>Demo</dd></div>
        </dl>
      </section>

      <div className="sidebar-footer">
        <button type="button"><LifeBuoy size={13} strokeWidth={1.5} aria-hidden="true" />Help</button>
        <span>v3.2.0</span>
      </div>
    </>
  )
}

export default function AppShell({
  view,
  onNavigate,
  page,
  readiness,
  health,
  activeSession,
  onNewConversation,
  children,
}) {
  const pageNumber = NAV_ITEMS.find((item) => item.id === view)?.number || '01'

  return (
    <div className={`app-shell ${view === 'chat' ? 'chat-active' : ''}`}>
      <aside className="desktop-sidebar">
        <SidebarContent view={view} onNavigate={onNavigate} readiness={readiness} health={health} activeSession={activeSession} />
      </aside>

      <div className="mobile-navigation">
        <MeshMark size={22} />
        <span className="mobile-brand">AgentMesh</span>
        <nav aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                type="button"
                className={view === item.id ? 'active' : ''}
                aria-current={view === item.id ? 'page' : undefined}
                aria-label={item.label}
                onClick={() => onNavigate(item.id)}
              >
                <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
              </button>
            )
          })}
        </nav>
      </div>

      <div className="app-frame">
        <main className="app-content">
          <header className="app-header">
            <div className="page-title-block">
              <div className="page-kicker">
                <span>&#8470; {pageNumber}</span>
                <i aria-hidden="true" />
                <span>{page.eyebrow}</span>
              </div>
              <h1>{page.title}</h1>
              <p>{page.description}</p>
            </div>
            <div className="header-actions">
              {(view === 'chat' || activeSession) && (
                <button type="button" className="button secondary new-conversation" onClick={onNewConversation}>
                  <Plus size={14} strokeWidth={1.75} aria-hidden="true" />
                  <span>New conversation</span>
                </button>
              )}
            </div>
          </header>
          {children}
        </main>
      </div>
    </div>
  )
}
