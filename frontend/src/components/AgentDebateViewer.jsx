import React from 'react'
import { BookOpenText, FileCheck2, HeartPulse, ShieldCheck } from 'lucide-react'
import BlockchainProof from './BlockchainProof'
import {
  AGENT_DEFINITIONS,
  formatConfidence,
  formatValue,
  humanize,
  normalizeDecision,
  prettyJson,
} from '../decision'
import {
  ClaimResult,
  DecisionBadge,
  DefinitionList,
  EmptyState,
  EvidenceRow,
  SectionHeader,
  StatusIndicator,
} from './ui'

const AGENT_ICONS = {
  sage: BookOpenText,
  guardian: ShieldCheck,
  empath: HeartPulse,
  oracle: FileCheck2,
}

function findingPayload(rawFinding) {
  if (!rawFinding || typeof rawFinding !== 'object' || Array.isArray(rawFinding)) return {}
  const output = rawFinding.output && typeof rawFinding.output === 'object' && !Array.isArray(rawFinding.output)
    ? rawFinding.output
    : rawFinding
  return {
    ...output,
    agent_state: rawFinding.state ?? rawFinding.agent_state ?? rawFinding.availability ?? null,
    agent_error: rawFinding.error ?? null,
  }
}

function ListField({ label, values, empty = 'None reported' }) {
  const items = Array.isArray(values) ? values : values ? [values] : []
  return (
    <div className="trace-list-field">
      <h4>{label}</h4>
      {items.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${typeof item === 'string' ? item : prettyJson(item)}-${index}`}>
              {typeof item === 'string' ? item : prettyJson(item)}
            </li>
          ))}
        </ul>
      ) : <p className="muted-text">{empty}</p>}
    </div>
  )
}

function SageFinding({ finding }) {
  return (
    <>
      <DefinitionList items={[
        { label: 'Retrieval state', value: finding.agent_state },
        { label: 'Answer mode', value: finding.generation_mode },
        { label: 'Confidence', value: formatConfidence(finding.confidence) },
        { label: 'Retrieval quality', value: finding.retrieval_quality },
        { label: 'Insufficient data', value: finding.insufficient_data },
      ]} />
      <ListField label="Warnings" values={finding.warnings} />
      {finding.answer && <div className="trace-copy"><h4>Grounded draft</h4><p>{finding.answer}</p></div>}
    </>
  )
}

function GuardianFinding({ finding }) {
  return (
    <>
      <DefinitionList items={[
        { label: 'Security status', value: finding.status },
        { label: 'Resulting action', value: finding.action },
        { label: 'Safety veto', value: finding.blocking },
        { label: 'Confidence', value: formatConfidence(finding.confidence) },
      ]} />
      <div className="trace-columns">
        <ListField label="Deterministic findings" values={finding.deterministic_violations} />
        <ListField label="Semantic findings" values={finding.semantic_violations} />
      </div>
      <ListField label="All security findings" values={finding.violations} />
      {finding.reasoning && <div className="trace-copy"><h4>Review reason</h4><p>{finding.reasoning}</p></div>}
      {finding.safe_guidance && <div className="trace-copy"><h4>Safe guidance</h4><p>{finding.safe_guidance}</p></div>}
    </>
  )
}

function EmpathFinding({ finding }) {
  return (
    <DefinitionList items={[
      { label: 'Emotion', value: finding.emotion },
      { label: 'Urgency', value: finding.urgency },
      { label: 'Sentiment', value: finding.sentiment_label },
      { label: 'Sentiment score', value: finding.sentiment_score },
      { label: 'Churn risk', value: finding.churn_risk },
      { label: 'Urgent review', value: finding.requires_urgent_review },
      { label: 'Recommended tone', value: finding.recommended_tone },
    ]} />
  )
}

function OracleFinding({ finding }) {
  const claims = Array.isArray(finding.claims) ? finding.claims : []
  return (
    <>
      <DefinitionList items={[
        { label: 'Overall supported', value: finding.overall_supported },
        { label: 'Recommendation', value: finding.recommendation },
        { label: 'Confidence', value: formatConfidence(finding.confidence) },
      ]} />
      <ListField label="Unsupported claims" values={finding.unsupported_claims} />
      <div className="claim-results">
        <h4>Claim verification</h4>
        {claims.length
          ? claims.map((claim, index) => <ClaimResult key={`${claim.claim || 'claim'}-${index}`} claim={claim} />)
          : <p className="muted-text">No claim-level results were reported.</p>}
      </div>
    </>
  )
}

const FINDING_VIEWS = {
  sage: SageFinding,
  guardian: GuardianFinding,
  empath: EmpathFinding,
  oracle: OracleFinding,
}

function AgentReviewSection({ definition, rawFinding, completed, last }) {
  const finding = findingPayload(rawFinding)
  const FindingView = FINDING_VIEWS[definition.key]
  const Icon = AGENT_ICONS[definition.key]
  const reported = Object.keys(finding).some((key) => finding[key] !== null && finding[key] !== undefined)
  const serviceState = finding.agent_state || (completed ? 'AVAILABLE' : 'NOT_REPORTED')

  return (
    <article className={`agent-review-section ${last ? 'last' : ''}`}>
      <div className="review-sequence-marker" aria-hidden="true"><Icon size={17} /></div>
      <div className="agent-review-content">
        <header className="agent-review-heading">
          <div>
            <span className="agent-name">{definition.name}</span>
            <h3>{definition.role}</h3>
          </div>
          <StatusIndicator status={serviceState} compact />
        </header>
        {reported ? <FindingView finding={finding} /> : (
          <p className="unreported-state">No finding was returned for this specialist.</p>
        )}
        {finding.agent_error && <div className="inline-error">{finding.agent_error}</div>}
        {reported && (
          <details className="raw-details">
            <summary>Raw returned finding</summary>
            <pre>{prettyJson(rawFinding)}</pre>
          </details>
        )}
      </div>
    </article>
  )
}

export default function AgentDebateViewer({ decision: rawDecision, sessionId, onOpenChat }) {
  if (!rawDecision) {
    return (
      <section className="page-container">
        <EmptyState
          title="No completed decision yet"
          description="Send a support question first. Decision Trace displays returned findings and never simulates agent activity."
          action={<button type="button" className="button primary" onClick={onOpenChat}>Open customer chat</button>}
        />
      </section>
    )
  }

  const decision = normalizeDecision(rawDecision)
  const completed = new Set(decision.completedAgents.map((name) => name.toLowerCase()))
  const responseTreatment = decision.factualAnswer && decision.finalAnswer !== decision.factualAnswer
    ? 'Final response differs from the grounded draft'
    : 'Grounded draft returned without a reported rewrite'

  return (
    <section className="page-container trace-page" aria-label="Agent decision trace">
      <section className="decision-record" aria-labelledby="decision-record-heading">
        <div className="decision-record-main">
          <p className="eyebrow">Customer query</p>
          <h2 id="decision-record-heading">{decision.query || 'Query not returned'}</h2>
          {decision.finalAnswer && (
            <div className="response-record">
              <h3>Customer-facing response</h3>
              <p>{decision.finalAnswer}</p>
            </div>
          )}
          {decision.factualAnswer && decision.factualAnswer !== decision.finalAnswer && (
            <details className="draft-details">
              <summary>View grounded draft before response treatment</summary>
              <p>{decision.factualAnswer}</p>
            </details>
          )}
        </div>
        <aside className="decision-record-side">
          <DecisionBadge status={decision.decisionState} />
          <p>{decision.decisionReason || 'Decision reason was not reported.'}</p>
          <dl>
            <div><dt>Session</dt><dd><code>{decision.sessionId || sessionId || 'Not reported'}</code></dd></div>
            <div><dt>Completed checks</dt><dd>{decision.completedAgents.length || 'Not reported'}</dd></div>
          </dl>
        </aside>
      </section>

      {(decision.escalationTicketId || decision.escalationRequested) && (
        <div className="escalation-notice">
          <div>
            <strong>This request requires human review</strong>
            <p>{decision.escalationTicketId ? 'An escalation ticket was created.' : 'Escalation was requested without a returned ticket ID.'}</p>
          </div>
          {decision.escalationTicketId && <code>{decision.escalationTicketId}</code>}
        </div>
      )}

      <section className="trace-section" aria-labelledby="specialist-findings-heading">
        <SectionHeader
          eyebrow="Review sequence"
          title="Specialist findings"
          id="specialist-findings-heading"
          description="Each section reflects the latest completed API response."
        />
        <div className="agent-review-sequence">
          {AGENT_DEFINITIONS.map((definition, index) => (
            <AgentReviewSection
              key={definition.key}
              definition={definition}
              rawFinding={decision.agentFindings[definition.key]}
              completed={completed.has(definition.key)}
              last={index === AGENT_DEFINITIONS.length - 1}
            />
          ))}
        </div>
      </section>

      <section className="trace-section" aria-labelledby="trace-evidence-heading">
        <SectionHeader
          eyebrow="Policy evidence"
          title="Retrieved sources"
          id="trace-evidence-heading"
          description="Retrieval relevance is kept distinct from claim-level factual support."
        />
        {decision.citations.length ? (
          <div className="evidence-list">
            {decision.citations.map((citation, index) => (
              <EvidenceRow key={`${citation.key}-${index}`} citation={citation} index={index} />
            ))}
          </div>
        ) : <p className="unreported-state">No retrieved citations were returned for this decision.</p>}
      </section>

      <section className="trace-section final-decision" aria-labelledby="final-decision-heading">
        <SectionHeader eyebrow="Outcome" title="Final decision" id="final-decision-heading" />
        <div className="final-decision-row">
          <DecisionBadge status={decision.decisionState} />
          <p>{decision.decisionReason || 'Decision reason was not reported.'}</p>
        </div>
        <DefinitionList items={[
          { label: 'Response treatment', value: responseTreatment },
          { label: 'Escalation result', value: decision.escalationTicketId || (decision.escalationRequested ? 'Requested' : 'Not requested'), mono: Boolean(decision.escalationTicketId) },
          { label: 'Audit state', value: humanize(decision.audit.status) },
        ]} />
      </section>

      <BlockchainProof audit={decision.audit} />
    </section>
  )
}
