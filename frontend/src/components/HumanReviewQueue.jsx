import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Check,
  ChevronRight,
  RefreshCw,
  Save,
  Search,
  X,
} from 'lucide-react'
import { apiRequest, describeApiError } from '../api'
import { formatValue, normalizeCitation, prettyJson } from '../decision'
import {
  ClaimResult,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  EvidenceRow,
  LoadingState,
  StatusIndicator,
} from './ui'

const REVIEW_KEY_STORAGE = 'agentmesh.prototypeReviewKey'
const STATUS_OPTIONS = ['OPEN', 'APPROVED', 'REJECTED', 'RESOLVED']
const PRIORITY_OPTIONS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

function storedReviewKey() {
  try {
    return window.sessionStorage.getItem(REVIEW_KEY_STORAGE) || ''
  } catch {
    return ''
  }
}

function reviewHeaders(key) {
  return key ? { 'X-Review-API-Key': key } : {}
}

function ticketId(ticket) {
  return ticket?.ticket_id ?? ticket?.id ?? null
}

function arrayFromListResponse(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  if (Array.isArray(payload?.escalations)) return payload.escalations
  if (Array.isArray(payload?.tickets)) return payload.tickets
  return []
}

function ticketFindings(ticket) {
  const findings = ticket?.agent_findings
  return findings && typeof findings === 'object' && !Array.isArray(findings) ? findings : {}
}

function findingPayload(finding) {
  if (!finding || typeof finding !== 'object' || Array.isArray(finding)) return {}
  return finding.output && typeof finding.output === 'object' ? finding.output : finding
}

function ticketAnswer(ticket) {
  return ticket?.draft_answer ?? ticket?.suggested_response ?? ticket?.final_answer ?? ''
}

function humanDate(value) {
  if (!value) return 'Not reported'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString()
}

function createdTime(ticket) {
  const value = new Date(ticket?.created_at || 0).getTime()
  return Number.isNaN(value) ? 0 : value
}

function securityReason(ticket) {
  const guardian = findingPayload(ticketFindings(ticket).guardian)
  if (guardian.reasoning) return guardian.reasoning
  if (Array.isArray(guardian.violations) && guardian.violations.length) return formatValue(guardian.violations[0])
  return 'Not reported'
}

function ticketUrgency(ticket) {
  return formatValue(findingPayload(ticketFindings(ticket).empath).urgency)
}

function ticketDecision(ticket) {
  return ticket?.decision_state ?? ticket?.consensus_status ?? 'Not reported'
}

function TicketTable({ tickets, selectedId, onSelect }) {
  return (
    <>
      <div className="ticket-table-wrap">
        <table className="ticket-table">
          <thead>
            <tr>
              <th scope="col">Ticket</th>
              <th scope="col">Priority</th>
              <th scope="col">Created</th>
              <th scope="col">Decision</th>
              <th scope="col">Customer issue</th>
              <th scope="col">Security reason</th>
              <th scope="col">Urgency</th>
              <th scope="col">Status</th>
              <th scope="col"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            {tickets.map((ticket, index) => {
              const id = ticketId(ticket)
              const selected = Boolean(id && selectedId === id)
              return (
                <tr key={id || `ticket-${index}`} className={selected ? 'selected' : ''}>
                  <td><button type="button" className="ticket-id-button" onClick={() => onSelect(ticket)}><code>{id || 'Missing ID'}</code></button></td>
                  <td><span className={`priority priority-${String(ticket.priority || 'unknown').toLowerCase()}`}>{formatValue(ticket.priority)}</span></td>
                  <td><time dateTime={ticket.created_at || undefined}>{humanDate(ticket.created_at)}</time></td>
                  <td>{formatValue(ticketDecision(ticket))}</td>
                  <td className="ticket-query-cell">{ticket.query || 'Not reported'}</td>
                  <td className="ticket-reason-cell">{securityReason(ticket)}</td>
                  <td>{ticketUrgency(ticket)}</td>
                  <td><StatusIndicator status={ticket.status || 'OPEN'} compact /></td>
                  <td><button type="button" className="icon-button quiet" onClick={() => onSelect(ticket)} aria-label={`Open ticket ${id || index + 1}`}><ChevronRight size={17} aria-hidden="true" /></button></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="ticket-mobile-list">
        {tickets.map((ticket, index) => {
          const id = ticketId(ticket)
          return (
            <button
              type="button"
              className={`ticket-mobile-row ${id && selectedId === id ? 'selected' : ''}`}
              key={id || `mobile-ticket-${index}`}
              onClick={() => onSelect(ticket)}
            >
              <div>
                <code>{id || 'Missing ticket ID'}</code>
                <StatusIndicator status={ticket.status || 'OPEN'} compact />
              </div>
              <p>{ticket.query || 'Customer issue not reported'}</p>
              <dl>
                <div><dt>Priority</dt><dd>{formatValue(ticket.priority)}</dd></div>
                <div><dt>Urgency</dt><dd>{ticketUrgency(ticket)}</dd></div>
                <div><dt>Created</dt><dd>{humanDate(ticket.created_at)}</dd></div>
              </dl>
            </button>
          )
        })}
      </div>
    </>
  )
}

function ReviewSignals({ ticket }) {
  const findings = ticketFindings(ticket)
  const sage = findingPayload(findings.sage)
  const guardian = findingPayload(findings.guardian)
  const empath = findingPayload(findings.empath)
  const oracle = findingPayload(findings.oracle)
  const citations = Array.isArray(sage.citations) ? sage.citations.map(normalizeCitation) : []
  const deterministic = Array.isArray(guardian.deterministic_violations) ? guardian.deterministic_violations : []
  const semantic = Array.isArray(guardian.semantic_violations) ? guardian.semantic_violations : []
  const claims = Array.isArray(oracle.claims) ? oracle.claims : []

  return (
    <div className="review-signals">
      <section>
        <h3>Security findings</h3>
        <div className="signal-status-row">
          <StatusIndicator status={guardian.status || 'NOT_REPORTED'} />
          {guardian.blocking !== undefined && <span>{guardian.blocking ? 'Safety veto applied' : 'No safety veto'}</span>}
        </div>
        {guardian.reasoning && <p>{guardian.reasoning}</p>}
        <div className="signal-columns">
          <div><h4>Deterministic</h4>{deterministic.length ? <ul>{deterministic.map((item, index) => <li key={`${prettyJson(item)}-${index}`}>{formatValue(item)}</li>)}</ul> : <p>None reported</p>}</div>
          <div><h4>Semantic</h4>{semantic.length ? <ul>{semantic.map((item, index) => <li key={`${prettyJson(item)}-${index}`}>{formatValue(item)}</li>)}</ul> : <p>None reported</p>}</div>
        </div>
      </section>

      <section>
        <h3>Customer context</h3>
        <dl className="compact-definition-list">
          <div><dt>Emotion</dt><dd>{formatValue(empath.emotion)}</dd></div>
          <div><dt>Urgency</dt><dd>{formatValue(empath.urgency)}</dd></div>
          <div><dt>Churn risk</dt><dd>{formatValue(empath.churn_risk)}</dd></div>
          <div><dt>Recommended tone</dt><dd>{formatValue(empath.recommended_tone)}</dd></div>
        </dl>
      </section>

      <section>
        <h3>Claim verification</h3>
        {claims.length
          ? <div className="claim-results">{claims.map((claim, index) => <ClaimResult key={`${claim.claim || 'claim'}-${index}`} claim={claim} />)}</div>
          : <p className="muted-text">No claim-level results were stored with this ticket.</p>}
      </section>

      <section>
        <h3>Evidence citations</h3>
        {citations.length
          ? <div className="evidence-list">{citations.map((citation, index) => <EvidenceRow key={`${citation.key}-${index}`} citation={citation} index={index} />)}</div>
          : <p className="muted-text">No controlled citations were stored with this ticket.</p>}
      </section>

      <section>
        <h3>Audit information</h3>
        {ticket.audit ? (
          <dl className="compact-definition-list">
            <div><dt>Status</dt><dd>{formatValue(ticket.audit.status)}</dd></div>
            <div><dt>Transaction</dt><dd><code>{ticket.audit.transaction_hash || 'Not reported'}</code></dd></div>
          </dl>
        ) : <p className="muted-text">Audit information was not stored with this review ticket.</p>}
      </section>
    </div>
  )
}

function TicketDetail({
  ticket,
  loading,
  originalAnswer,
  editableAnswer,
  onAnswerChange,
  onSave,
  onRequestAction,
  busyAction,
  mutationMessage,
}) {
  if (loading) return <LoadingState label="Loading ticket details..." />
  if (!ticket) {
    return <EmptyState compact title="Select a ticket" description="Choose an escalation record to inspect evidence and reviewer actions." />
  }

  const id = ticketId(ticket)
  const dirty = editableAnswer !== ticketAnswer(ticket)

  return (
    <article className="ticket-detail">
      <header className="ticket-detail-header">
        <div>
          <p className="eyebrow">Escalation ticket</p>
          <h2>{id || 'Ticket ID not returned'}</h2>
        </div>
        <div className="ticket-state-group">
          <span className={`priority priority-${String(ticket.priority || 'unknown').toLowerCase()}`}>{formatValue(ticket.priority)}</span>
          <StatusIndicator status={ticket.status || 'OPEN'} />
        </div>
      </header>

      <dl className="ticket-metadata">
        <div><dt>Session</dt><dd><code>{ticket.session_id || 'Not reported'}</code></dd></div>
        <div><dt>Created</dt><dd>{humanDate(ticket.created_at)}</dd></div>
        <div><dt>Updated</dt><dd>{humanDate(ticket.updated_at)}</dd></div>
      </dl>

      <div className="review-detail-grid">
        <div className="review-response-column">
          <section className="review-copy-section">
            <h3>Customer query</h3>
            <p>{ticket.query || 'Query not returned.'}</p>
          </section>
          <section className="review-copy-section">
            <h3>Decision reason</h3>
            <p>{ticket.reason || ticket.decision_reason || 'Reason not reported.'}</p>
          </section>
          <section className="review-copy-section original-draft">
            <h3>Original draft</h3>
            <p>{originalAnswer || 'No draft answer was returned.'}</p>
          </section>
          {ticket.resolution_notes && (
            <section className="review-copy-section">
              <h3>Reviewer notes</h3>
              <p>{ticket.resolution_notes}</p>
            </section>
          )}

          <section className="answer-editor">
            <div className="answer-editor-heading">
              <div><h3>Response for submission</h3><p>Review the exact text before approving or resolving.</p></div>
              {dirty && <span className="unsaved-indicator">Unsaved edit</span>}
            </div>
            <label htmlFor="review-answer">Customer response</label>
            <textarea
              id="review-answer"
              rows={10}
              value={editableAnswer}
              onChange={(event) => onAnswerChange(event.target.value)}
              disabled={Boolean(busyAction)}
              placeholder="No draft answer was returned."
            />
            <button type="button" className="button secondary" disabled={!dirty || Boolean(busyAction)} onClick={onSave}>
              <Save size={15} aria-hidden="true" />
              {busyAction === 'save' ? 'Saving...' : 'Save edit'}
            </button>
          </section>
        </div>

        <aside className="review-evidence-column">
          <ReviewSignals ticket={ticket} />
        </aside>
      </div>

      {mutationMessage && <ErrorState error={mutationMessage} />}

      <section className="review-actions" aria-labelledby="review-actions-heading">
        <div>
          <h3 id="review-actions-heading">Reviewer decision</h3>
          <p>Actions update this review record. They do not send a customer notification.</p>
        </div>
        <div className="action-button-row">
          <button type="button" className="button secondary" disabled={Boolean(busyAction)} onClick={() => onRequestAction('approve')}>
            <Check size={16} aria-hidden="true" /> Approve
          </button>
          <button type="button" className="button danger" disabled={Boolean(busyAction)} onClick={() => onRequestAction('reject')}>
            <X size={16} aria-hidden="true" /> Reject
          </button>
          <button type="button" className="button primary" disabled={Boolean(busyAction)} onClick={() => onRequestAction('resolve')}>
            Resolve
          </button>
        </div>
      </section>
    </article>
  )
}

export default function HumanReviewQueue() {
  const reviewKeyRef = useRef(storedReviewKey())
  const [tickets, setTickets] = useState([])
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [originalAnswer, setOriginalAnswer] = useState('')
  const [editableAnswer, setEditableAnswer] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [listError, setListError] = useState(null)
  const [detailError, setDetailError] = useState(null)
  const [busyAction, setBusyAction] = useState(null)
  const [mutationMessage, setMutationMessage] = useState(null)
  const [pendingAction, setPendingAction] = useState(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [priorityFilter, setPriorityFilter] = useState('ALL')
  const [sortOrder, setSortOrder] = useState('newest')
  const listControllerRef = useRef(null)
  const detailControllerRef = useRef(null)

  const loadTickets = async () => {
    listControllerRef.current?.abort()
    const controller = new AbortController()
    listControllerRef.current = controller
    setLoadingList(true)
    setListError(null)
    try {
      const payload = await apiRequest('/escalations', {
        signal: controller.signal,
        headers: reviewHeaders(reviewKeyRef.current),
      })
      setTickets(arrayFromListResponse(payload))
    } catch (error) {
      if (error?.kind !== 'cancelled') setListError(describeApiError(error))
    } finally {
      if (listControllerRef.current === controller) {
        listControllerRef.current = null
        setLoadingList(false)
      }
    }
  }

  useEffect(() => {
    loadTickets()
    return () => {
      listControllerRef.current?.abort()
      detailControllerRef.current?.abort()
    }
  }, [])

  const visibleTickets = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase()
    return tickets
      .filter((ticket) => statusFilter === 'ALL' || String(ticket.status).toUpperCase() === statusFilter)
      .filter((ticket) => priorityFilter === 'ALL' || String(ticket.priority).toUpperCase() === priorityFilter)
      .filter((ticket) => {
        if (!normalizedSearch) return true
        return [ticketId(ticket), ticket.query, ticket.reason, securityReason(ticket)]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(normalizedSearch))
      })
      .sort((first, second) => sortOrder === 'newest'
        ? createdTime(second) - createdTime(first)
        : createdTime(first) - createdTime(second))
  }, [tickets, search, statusFilter, priorityFilter, sortOrder])

  const selectTicket = async (summary) => {
    const id = ticketId(summary)
    if (!id) {
      setDetailError({ title: 'Missing ticket ID', message: 'This record cannot be opened.', tone: 'danger' })
      return
    }

    detailControllerRef.current?.abort()
    const controller = new AbortController()
    detailControllerRef.current = controller
    setSelectedTicket(summary)
    setOriginalAnswer(ticketAnswer(summary))
    setEditableAnswer(ticketAnswer(summary))
    setLoadingDetail(true)
    setDetailError(null)
    setMutationMessage(null)
    try {
      const detail = await apiRequest(`/escalations/${encodeURIComponent(id)}`, {
        signal: controller.signal,
        headers: reviewHeaders(reviewKeyRef.current),
      })
      const record = detail?.escalation ?? detail?.ticket ?? detail
      setSelectedTicket(record)
      setOriginalAnswer(ticketAnswer(record))
      setEditableAnswer(ticketAnswer(record))
    } catch (error) {
      if (error?.kind !== 'cancelled') setDetailError(describeApiError(error))
    } finally {
      if (detailControllerRef.current === controller) {
        detailControllerRef.current = null
        setLoadingDetail(false)
      }
    }
  }

  const refreshSelected = async (id) => {
    const detail = await apiRequest(`/escalations/${encodeURIComponent(id)}`, {
      headers: reviewHeaders(reviewKeyRef.current),
    })
    const record = detail?.escalation ?? detail?.ticket ?? detail
    setSelectedTicket(record)
    setEditableAnswer(ticketAnswer(record))
  }

  const saveEdit = async () => {
    const id = ticketId(selectedTicket)
    if (!id || busyAction) return
    setBusyAction('save')
    setMutationMessage(null)
    try {
      await apiRequest(`/escalations/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: { draft_answer: editableAnswer },
        headers: reviewHeaders(reviewKeyRef.current),
      })
      await refreshSelected(id)
      await loadTickets()
      setMutationMessage({ title: 'Edit saved', message: 'The review draft was updated.', tone: 'success' })
    } catch (error) {
      setMutationMessage(describeApiError(error))
    } finally {
      setBusyAction(null)
    }
  }

  const runAction = async () => {
    const action = pendingAction
    const id = ticketId(selectedTicket)
    if (!id || !action || busyAction) return
    setBusyAction(action)
    setMutationMessage(null)
    try {
      await apiRequest(`/escalations/${encodeURIComponent(id)}/${action}`, {
        method: 'POST',
        body: { answer: editableAnswer },
        headers: reviewHeaders(reviewKeyRef.current),
      })
      await refreshSelected(id)
      await loadTickets()
      setMutationMessage({
        title: `Ticket ${action === 'approve' ? 'approved' : action === 'reject' ? 'rejected' : 'resolved'}`,
        message: 'The review record was updated.',
        tone: 'success',
      })
      setPendingAction(null)
    } catch (error) {
      setMutationMessage(describeApiError(error))
    } finally {
      setBusyAction(null)
    }
  }

  const selectedId = ticketId(selectedTicket)
  const actionCopy = {
    approve: { title: 'Approve this response?', label: 'Approve response', tone: 'primary' },
    reject: { title: 'Reject this response?', label: 'Reject response', tone: 'danger' },
    resolve: { title: 'Resolve this review?', label: 'Resolve ticket', tone: 'primary' },
  }
  const confirmation = actionCopy[pendingAction]

  return (
    <section className="page-container review-page" aria-labelledby="review-queue-heading">
      <header className="review-queue-header">
        <div>
          <p className="eyebrow">Escalation workspace</p>
          <h2 id="review-queue-heading">Review queue</h2>
          <p>Filter escalated decisions, inspect returned evidence, and record a human outcome.</p>
        </div>
        <button type="button" className="button secondary" onClick={loadTickets} disabled={loadingList}>
          <RefreshCw size={16} className={loadingList ? 'spin' : ''} aria-hidden="true" />
          Refresh
        </button>
      </header>

      <div className="queue-toolbar" role="search">
        <label className="search-field">
          <span className="sr-only">Search tickets</span>
          <Search size={16} aria-hidden="true" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search tickets or customer issues" />
        </label>
        <label>
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="ALL">All statuses</option>
            {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{formatValue(status)}</option>)}
          </select>
        </label>
        <label>
          <span>Priority</span>
          <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
            <option value="ALL">All priorities</option>
            {PRIORITY_OPTIONS.map((priority) => <option key={priority} value={priority}>{formatValue(priority)}</option>)}
          </select>
        </label>
        <label>
          <span>Sort</span>
          <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>

      <ErrorState error={listError} onRetry={loadTickets} />
      {loadingList && tickets.length === 0 ? <LoadingState label="Loading review queue..." /> : null}
      {!loadingList && !listError && visibleTickets.length === 0 ? (
        <EmptyState compact title="No matching tickets" description="Adjust the filters or refresh the queue." />
      ) : null}
      {visibleTickets.length > 0 && (
        <TicketTable tickets={visibleTickets} selectedId={selectedId} onSelect={selectTicket} />
      )}

      <div className="ticket-detail-panel">
        {detailError && <ErrorState error={detailError} />}
        <TicketDetail
          ticket={selectedTicket}
          loading={loadingDetail}
          originalAnswer={originalAnswer}
          editableAnswer={editableAnswer}
          onAnswerChange={setEditableAnswer}
          onSave={saveEdit}
          onRequestAction={setPendingAction}
          busyAction={busyAction}
          mutationMessage={mutationMessage}
        />
      </div>

      <ConfirmDialog
        open={Boolean(confirmation)}
        title={confirmation?.title}
        description="The text below is the response that will be submitted with this reviewer action."
        confirmLabel={confirmation?.label}
        tone={confirmation?.tone}
        onCancel={() => setPendingAction(null)}
        onConfirm={runAction}
        busy={Boolean(busyAction)}
      >
        <div className="submission-preview">
          <span>Response for submission</span>
          <p>{editableAnswer || 'No response text was provided.'}</p>
        </div>
      </ConfirmDialog>
    </section>
  )
}
