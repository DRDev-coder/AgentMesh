import React from 'react'
import { Database, FileSearch, Link2, RefreshCw, Server, ShieldCheck, Users } from 'lucide-react'
import { ErrorState, LoadingState, SectionHeader, StatusIndicator } from './ui'

const DEPENDENCY_ROWS = [
  { key: 'sage', label: 'Policy retrieval', description: 'Grounding and approved policy corpus', icon: FileSearch },
  { key: 'guardian', label: 'Security review', description: 'Deterministic and semantic risk checks', icon: ShieldCheck },
  { key: 'empath', label: 'Customer context', description: 'Emotion and urgency assessment', icon: Users },
  { key: 'oracle', label: 'Evidence verification', description: 'Claim support evaluation', icon: FileSearch },
  { key: 'sqlite', label: 'Database', description: 'Conversation and escalation storage', icon: Database },
  { key: 'blockchain', label: 'Audit anchor', description: 'Optional blockchain receipt submission', icon: Link2 },
]

function dependencyStatus(dependency) {
  if (!dependency) return { status: 'UNAVAILABLE', label: 'Unavailable' }
  if (dependency.enabled === false) return { status: 'DISABLED', label: 'Disabled' }
  return dependency.ready
    ? { status: 'OPERATIONAL', label: 'Operational' }
    : { status: 'UNAVAILABLE', label: 'Unavailable' }
}

function StatusRow({ icon: Icon, label, description, status, statusLabel }) {
  return (
    <div className="system-status-row">
      <div className="system-status-name">
        <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
        <div>
          <strong>{label}</strong>
          <span>{description}</span>
        </div>
      </div>
      <StatusIndicator status={status} label={statusLabel} />
    </div>
  )
}

export default function SystemStatus({ health, onRefresh }) {
  const lastChecked = health.lastChecked
    ? new Date(health.lastChecked).toLocaleString()
    : 'Not checked'

  return (
    <section className="page-container system-status-page" aria-labelledby="status-overview-heading">
      <SectionHeader
        eyebrow="Service health"
        title="Current environment"
        id="status-overview-heading"
        description="Status is reported by the API and its configured dependencies. No synthetic uptime or activity data is shown."
        action={(
          <button type="button" className="button secondary" onClick={onRefresh} disabled={health.loading}>
            <RefreshCw size={16} className={health.loading ? 'spin' : ''} aria-hidden="true" />
            Refresh
          </button>
        )}
      />

      {health.error && <ErrorState error={health.error} onRetry={onRefresh} />}
      {health.loading && !health.lastChecked ? <LoadingState label="Checking service status..." /> : (
        <div className="status-list" aria-live="polite">
          <StatusRow
            icon={Server}
            label="API liveness"
            description="Gateway process and request handling"
            status={health.liveness.status}
            statusLabel={health.liveness.label}
          />
          <StatusRow
            icon={Server}
            label="System readiness"
            description="Required dependencies for support decisions"
            status={health.readiness.status}
            statusLabel={health.readiness.label}
          />
          {DEPENDENCY_ROWS.map((row) => {
            const state = dependencyStatus(health.dependencies?.[row.key])
            return (
              <StatusRow
                key={row.key}
                icon={row.icon}
                label={row.label}
                description={row.description}
                status={state.status}
                statusLabel={state.label}
              />
            )
          })}
        </div>
      )}

      <div className="last-checked">
        <span>Last checked</span>
        <time dateTime={health.lastChecked || undefined}>{lastChecked}</time>
      </div>
    </section>
  )
}
