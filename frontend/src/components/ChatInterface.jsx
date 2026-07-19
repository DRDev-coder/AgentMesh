import React, { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUpRight, BookMarked, SendHorizontal, ShieldCheck, Square } from 'lucide-react'
import { apiRequest, describeApiError } from '../api'
import { formatConfidence, humanize, normalizeDecision } from '../decision'
import { MeshMark } from './AppShell'
import { DecisionBadge, ErrorState, EvidenceRow, StatusIndicator } from './ui'

const QUERY_LIMIT = 4000

const EXAMPLE_QUERIES = [
  { label: 'Refunds', query: 'How long will my refund take?' },
  { label: 'Security', query: 'A support executive asked for my OTP.' },
  { label: 'Urgent', query: 'My card is blocked and I need urgent help.' },
  { label: 'Compliance', query: 'Can you guarantee an investment return?' },
]

function DecisionSummary({ payload, onOpenTrace }) {
  const decision = normalizeDecision(payload)
  const confidence = decision.agentFindings?.sage?.output?.confidence
    ?? decision.agentFindings?.sage?.confidence
    ?? decision.legacyConfidence

  return (
    <aside className="decision-summary" aria-label="Decision summary">
      <div className="decision-summary-heading">
        <DecisionBadge status={decision.decisionState} />
        {confidence !== null && confidence !== undefined && (
          <span className="decision-confidence">Policy confidence {formatConfidence(confidence)}</span>
        )}
      </div>

      {decision.decisionReason && <p className="decision-reason">{decision.decisionReason}</p>}

      <dl className="decision-metadata">
        <div><dt>Evidence</dt><dd>{decision.citations.length} source{decision.citations.length === 1 ? '' : 's'}</dd></div>
        <div><dt>Review checks</dt><dd>{decision.completedAgents.length || 'Not reported'}</dd></div>
        <div><dt>Audit anchor</dt><dd>{humanize(decision.audit.status)}</dd></div>
      </dl>

      {decision.escalationTicketId && (
        <div className="ticket-notice">
          <span>Human review ticket created</span>
          <code>{decision.escalationTicketId}</code>
        </div>
      )}

      {decision.citations.length > 0 && (
        <details className="decision-evidence">
          <summary>Inspect supporting evidence</summary>
          <div>
            {decision.citations.map((citation, index) => (
              <EvidenceRow key={`${citation.key}-${index}`} citation={citation} index={index} />
            ))}
          </div>
        </details>
      )}

      <button type="button" className="text-link" onClick={onOpenTrace}>
        Inspect full decision trace
        <ArrowRight size={15} aria-hidden="true" />
      </button>
    </aside>
  )
}

function TextareaComposer({ value, onChange, onSubmit, loading, onCancel }) {
  const remaining = QUERY_LIMIT - value.length
  return (
    <form className="composer" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="support-query">Support question</label>
      <div className="composer-control">
        <textarea
          id="support-query"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              onSubmit(event)
            }
          }}
          placeholder={'Ask about a policy, an account issue, or a suspicious request\u2026'}
          rows={2}
          maxLength={QUERY_LIMIT}
          disabled={loading}
          aria-describedby="composer-guidance composer-count"
        />
        <div className="composer-toolbar">
          <span id="composer-guidance">
            {remaining <= 400 ? `${remaining} characters remaining` : <>Enter to send &middot; Shift+Enter for newline</>}
          </span>
          {loading ? (
            <button type="button" className="composer-send stop" onClick={onCancel} aria-label="Stop waiting">
              <Square size={13} fill="currentColor" aria-hidden="true" />
              Stop
            </button>
          ) : (
            <button type="submit" className="composer-send" disabled={!value.trim()} aria-label="Send question">
              <SendHorizontal size={14} strokeWidth={1.75} aria-hidden="true" />
              Send
            </button>
          )}
        </div>
      </div>
      <div className="composer-meta">
        <span id="composer-count">Deterministic controls active</span>
        <span>Never share passwords, OTPs, CVVs, or credentials in chat.</span>
      </div>
    </form>
  )
}

function ContextRail({ decisionPayload, health, sessionId }) {
  const decision = decisionPayload ? normalizeDecision(decisionPayload) : null
  const specialists = [
    { key: 'sage', label: 'Policy Guard' },
    { key: 'guardian', label: 'Prompt Integrity' },
    { key: 'oracle', label: 'Factual Grounding' },
    { key: 'empath', label: 'Urgency Triage' },
  ]

  const dependencyStatus = (key) => {
    if (health?.loading && !health.lastChecked) return { status: 'PENDING', label: 'Checking' }
    const dependency = health?.dependencies?.[key]
    if (!dependency) return { status: 'UNAVAILABLE', label: 'Unavailable' }
    return dependency.ready
      ? { status: 'OPERATIONAL', label: 'Ready' }
      : { status: 'UNAVAILABLE', label: 'Unavailable' }
  }

  return (
    <aside className="chat-context" aria-label="Conversation context">
      <section className="context-section">
        <h2>Latest decision</h2>
        {decision ? (
          <div className="context-decision">
            <DecisionBadge status={decision.decisionState} />
            <p>{decision.decisionReason || 'No decision reason was returned.'}</p>
            <dl>
              <div><dt>Evidence</dt><dd>{decision.citations.length} source{decision.citations.length === 1 ? '' : 's'}</dd></div>
              <div><dt>Audit</dt><dd>{humanize(decision.audit.status)}</dd></div>
              {decision.escalationTicketId && <div><dt>Ticket</dt><dd><code>{decision.escalationTicketId}</code></dd></div>}
            </dl>
          </div>
        ) : <p className="context-empty">Send a message to see the mesh&apos;s grounded verdict, cited evidence, and specialist checks here.</p>}
      </section>

      {decision && (
        <section className="context-section">
          <header>
            <ShieldCheck size={16} aria-hidden="true" />
            <h2>Specialist mesh</h2>
          </header>
          <ul className="specialist-status-list">
            {specialists.map((specialist) => {
              const state = dependencyStatus(specialist.key)
              return (
                <li key={specialist.key}>
                  <span>{specialist.label}</span>
                  <StatusIndicator status={state.status} label={state.label} compact />
                </li>
              )
            })}
          </ul>
        </section>
      )}

      {decision && (
        <section className="context-section context-playbook">
          <header>
            <BookMarked size={16} aria-hidden="true" />
            <h2>Playbook</h2>
          </header>
          <p>Responses are grounded in the configured policy corpus.</p>
          <p>High-risk requests create a human-review ticket.</p>
          <p>Audit status reflects the receipt state returned by the API.</p>
          {sessionId && <code title={sessionId}>{sessionId}</code>}
        </section>
      )}
    </aside>
  )
}

export default function ChatInterface({ sessionId, resetToken, latestDecision, health, onDecision, onOpenTrace }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [requestError, setRequestError] = useState(null)
  const inFlightRef = useRef(null)
  const requestEpochRef = useRef(0)
  const messageCounterRef = useRef(0)
  const transcriptRef = useRef(null)

  useEffect(() => () => inFlightRef.current?.abort(), [])

  const resetConversationState = useCallback(() => {
    requestEpochRef.current += 1
    inFlightRef.current?.abort()
    inFlightRef.current = null
    setMessages([])
    setInput('')
    setRequestError(null)
    setLoading(false)
  }, [])

  useEffect(() => {
    resetConversationState()
  }, [resetToken, resetConversationState])

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    transcriptRef.current?.scrollTo({
      top: transcriptRef.current.scrollHeight,
      behavior: reduceMotion ? 'auto' : 'smooth',
    })
  }, [messages, loading])

  const nextMessageId = () => {
    messageCounterRef.current += 1
    return messageCounterRef.current
  }

  const sendMessage = async (event) => {
    event?.preventDefault()
    const query = input.trim()
    if (!query || loading || inFlightRef.current) return

    const controller = new AbortController()
    const requestEpoch = requestEpochRef.current + 1
    requestEpochRef.current = requestEpoch
    inFlightRef.current = controller
    setMessages((previous) => [...previous, { id: nextMessageId(), role: 'user', text: query }])
    setInput('')
    setRequestError(null)
    setLoading(true)

    try {
      const data = await apiRequest('/chat', {
        method: 'POST',
        body: {
          query,
          ...(sessionId ? { session_id: sessionId } : {}),
        },
        signal: controller.signal,
      })

      if (!data || typeof data !== 'object' || Array.isArray(data)) {
        throw Object.assign(new Error('The API did not return a decision object.'), { kind: 'protocol' })
      }
      if (requestEpochRef.current !== requestEpoch || controller.signal.aborted) return

      const answer = data.final_answer || data.factual_answer || 'No customer-facing answer was returned.'
      setMessages((previous) => [
        ...previous,
        { id: nextMessageId(), role: 'assistant', text: answer, decision: data },
      ])
      onDecision(data)
    } catch (error) {
      if (requestEpochRef.current !== requestEpoch) return
      setRequestError(describeApiError(error))
    } finally {
      if (requestEpochRef.current === requestEpoch && inFlightRef.current === controller) {
        inFlightRef.current = null
        setLoading(false)
      }
    }
  }

  return (
    <section className="chat-page" aria-label="Customer support conversation">
      <div className="chat-layout">
        <div className="chat-workspace">
          <div className="transcript" ref={transcriptRef} aria-live="polite" aria-busy={loading}>
            {messages.length === 0 && (
              <div className="chat-empty-state">
                <div className="empty-state-kicker">
                  <MeshMark size={32} dark={false} />
                  <span>Suggested requests</span>
                </div>
                <h2>How can we help?</h2>
                <p>Every reply is checked against policy, credential-safety, factual sources, and urgency before it reaches the customer.</p>
                <ul className="prompt-list" aria-label="Example questions">
                  {EXAMPLE_QUERIES.map((item, index) => (
                    <li key={item.query}>
                      <button type="button" onClick={() => setInput(item.query)}>
                        <span className="prompt-number">{String(index + 1).padStart(2, '0')}</span>
                        <span className="prompt-category">{item.label}</span>
                        <span className="prompt-copy">{item.query}</span>
                        <ArrowUpRight size={15} strokeWidth={1.5} aria-hidden="true" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {messages.map((message) => (
              <article key={message.id} className={`message-row ${message.role}`}>
                <div className="message-label">{message.role === 'user' ? 'You' : 'AgentMesh'}</div>
                {message.role === 'user' ? (
                  <div className="user-message"><p>{message.text}</p></div>
                ) : (
                  <div className="assistant-message">
                    <div className="assistant-answer"><p>{message.text}</p></div>
                    {message.decision && <DecisionSummary payload={message.decision} onOpenTrace={onOpenTrace} />}
                  </div>
                )}
              </article>
            ))}

            {loading && (
              <div className="request-progress" role="status">
                <span className="request-progress-mark" aria-hidden="true" />
                <span>Reviewing policy and safety checks...</span>
              </div>
            )}
          </div>

          {requestError && <ErrorState error={requestError} />}

          <TextareaComposer
            value={input}
            onChange={setInput}
            onSubmit={sendMessage}
            loading={loading}
            onCancel={() => inFlightRef.current?.abort()}
          />
        </div>

        <ContextRail decisionPayload={latestDecision} health={health} sessionId={sessionId} />
      </div>
    </section>
  )
}
