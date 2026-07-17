import React, { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Info,
  X,
  XCircle,
} from 'lucide-react'
import { formatValue, humanize, statusTone } from '../decision'

const STATUS_ICONS = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  neutral: Info,
}

export function StatusIndicator({ status, label, compact = false }) {
  const tone = statusTone(status)
  return (
    <span className={`status-indicator ${tone} ${compact ? 'compact' : ''}`}>
      <span className="status-dot" aria-hidden="true" />
      <span>{label || humanize(status)}</span>
    </span>
  )
}

export function DecisionBadge({ status }) {
  const tone = statusTone(status)
  const Icon = STATUS_ICONS[tone]
  return (
    <span className={`decision-badge ${tone}`}>
      <Icon size={14} strokeWidth={2} aria-hidden="true" />
      <span>{humanize(status)}</span>
    </span>
  )
}

export function SectionHeader({ eyebrow, title, description, action, as = 'h2', id }) {
  const Heading = as
  return (
    <header className="section-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <Heading id={id}>{title}</Heading>
        {description && <p className="section-description">{description}</p>}
      </div>
      {action && <div className="section-action">{action}</div>}
    </header>
  )
}

export function EmptyState({ title, description, action, compact = false }) {
  return (
    <div className={`empty-state ${compact ? 'compact' : ''}`}>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action}
    </div>
  )
}

export function LoadingState({ label = 'Loading' }) {
  return <div className="loading-state" role="status">{label}</div>
}

export function ErrorState({ error, onRetry }) {
  if (!error) return null
  return (
    <div className={`alert ${error.tone || 'danger'}`} role="alert">
      <div>
        <strong>{error.title || 'Request failed'}</strong>
        <p>{error.message}</p>
      </div>
      {onRetry && (
        <button type="button" className="button secondary small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function DefinitionList({ items, compact = false }) {
  return (
    <dl className={`definition-list ${compact ? 'compact' : ''}`}>
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd className={item.mono ? 'mono' : ''}>{formatValue(item.value)}</dd>
        </div>
      ))}
    </dl>
  )
}

export function EvidenceRow({ citation, index = 0 }) {
  const [copied, setCopied] = useState(false)
  const title = citation.document_id || citation.metadata?.title || `Evidence ${index + 1}`
  const reference = [citation.document_id, citation.chunk_id].filter(Boolean).join(' / ')

  const copyEvidence = async (event) => {
    event.preventDefault()
    event.stopPropagation()
    if (!citation.text || !navigator.clipboard) return
    try {
      await navigator.clipboard.writeText(citation.text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <details className="evidence-row">
      <summary>
        <span className="evidence-summary-main">
          <CheckCircle2 size={16} aria-hidden="true" />
          <span>
            <strong>{title}</strong>
            {reference && <code>{reference}</code>}
          </span>
        </span>
        <span className="evidence-summary-actions">
          {citation.text && (
            <button
              type="button"
              className="icon-button quiet"
              onClick={copyEvidence}
              aria-label={copied ? 'Evidence copied' : 'Copy evidence excerpt'}
              title={copied ? 'Copied' : 'Copy excerpt'}
            >
              {copied ? <Check size={15} aria-hidden="true" /> : <Clipboard size={15} aria-hidden="true" />}
            </button>
          )}
          <ChevronDown className="details-chevron" size={16} aria-hidden="true" />
        </span>
      </summary>
      <div className="evidence-detail">
        {citation.text ? <blockquote>{citation.text}</blockquote> : <p>No source excerpt was returned.</p>}
        {citation.distance_or_similarity !== null && citation.distance_or_similarity !== undefined && (
          <p className="evidence-note">
            Retrieval signal: {String(citation.distance_or_similarity)}. This value describes retrieval relevance,
            not factual verification.
          </p>
        )}
        {Object.keys(citation.metadata || {}).length > 0 && (
          <details className="metadata-details">
            <summary>Source metadata</summary>
            <pre>{JSON.stringify(citation.metadata, null, 2)}</pre>
          </details>
        )}
      </div>
    </details>
  )
}

export function ClaimResult({ claim }) {
  const state = claim.supported === true ? 'Supported' : claim.supported === false ? 'Unsupported' : 'Not reported'
  const tone = statusTone(state)
  const Icon = STATUS_ICONS[tone]
  return (
    <article className={`claim-result ${tone}`}>
      <Icon size={16} aria-hidden="true" />
      <div>
        <div className="claim-result-heading">
          <strong>{claim.claim || 'Claim text was not returned'}</strong>
          <span>{state}</span>
        </div>
        {claim.reason && <p>{claim.reason}</p>}
        {Array.isArray(claim.source_ids) && claim.source_ids.length > 0 && (
          <p className="claim-sources">Sources: {claim.source_ids.join(', ')}</p>
        )}
      </div>
    </article>
  )
}

export function ConfirmDialog({ open, title, description, confirmLabel, tone = 'primary', children, onCancel, onConfirm, busy }) {
  const cancelRef = useRef(null)
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    cancelRef.current?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !busy) onCancel()
      if (event.key === 'Tab') {
        const focusable = [...dialogRef.current.querySelectorAll('button:not(:disabled), [href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])')]
        if (!focusable.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, busy, onCancel])

  if (!open) return null
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={() => !busy && onCancel()}>
      <section
        ref={dialogRef}
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <h2 id="confirm-dialog-title">{title}</h2>
            {description && <p>{description}</p>}
          </div>
          <button type="button" className="icon-button quiet" onClick={onCancel} disabled={busy} aria-label="Close dialog">
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        {children}
        <footer>
          <button ref={cancelRef} type="button" className="button secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className={`button ${tone}`} onClick={onConfirm} disabled={busy}>
            {busy ? 'Updating ticket...' : confirmLabel}
          </button>
        </footer>
      </section>
    </div>
  )
}
