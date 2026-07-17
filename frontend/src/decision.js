export const AGENT_DEFINITIONS = [
  { key: 'sage', name: 'SAGE', role: 'Policy grounding' },
  { key: 'guardian', name: 'GUARDIAN', role: 'Security review' },
  { key: 'empath', name: 'EMPATH', role: 'Customer context' },
  { key: 'oracle', name: 'ORACLE', role: 'Evidence verification' },
]

function objectOrEmpty(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function firstArray(...values) {
  return values.find(Array.isArray) || []
}

export function normalizeCitation(citation, index = 0) {
  if (typeof citation === 'string') {
    return {
      document_id: null,
      chunk_id: null,
      text: citation,
      metadata: {},
      distance_or_similarity: null,
      key: `citation-${index}`,
    }
  }

  const source = objectOrEmpty(citation)
  return {
    document_id: source.document_id ?? source.source_id ?? null,
    chunk_id: source.chunk_id ?? null,
    text: source.text ?? source.content ?? source.document ?? '',
    metadata: objectOrEmpty(source.metadata),
    distance_or_similarity: source.distance_or_similarity ?? source.distance ?? source.similarity ?? null,
    key: source.chunk_id || source.document_id || `citation-${index}`,
  }
}

function normalizeAudit(payload) {
  const audit = objectOrEmpty(payload.audit)
  if (Object.keys(audit).length) {
    return {
      status: audit.status ?? 'NOT_REPORTED',
      transaction_hash: audit.transaction_hash ?? audit.tx_hash ?? null,
      error: audit.error ?? null,
      network: audit.network ?? null,
      explorer_url: audit.explorer_url ?? null,
    }
  }

  const legacyTransaction = payload.blockchain_tx
  if (typeof legacyTransaction === 'string' && legacyTransaction.startsWith('BLOCKCHAIN_ERROR')) {
    return {
      status: 'FAILED (legacy response)',
      transaction_hash: null,
      error: legacyTransaction.replace(/^BLOCKCHAIN_ERROR:\s*/, ''),
      network: null,
      explorer_url: null,
    }
  }
  if (typeof legacyTransaction === 'string' && legacyTransaction) {
    return {
      status: 'SUBMITTED (legacy response; confirmation unknown)',
      transaction_hash: legacyTransaction,
      error: null,
      network: null,
      explorer_url: null,
    }
  }

  return {
    status: 'NOT_REPORTED',
    transaction_hash: null,
    error: null,
    network: null,
    explorer_url: null,
  }
}

export function normalizeDecision(payload) {
  const source = objectOrEmpty(payload)
  const agentFindings = objectOrEmpty(
    Object.keys(objectOrEmpty(source.agent_findings)).length
      ? source.agent_findings
      : source.agent_votes,
  )
  const sage = objectOrEmpty(agentFindings.sage)
  const sageOutput = objectOrEmpty(sage.output)
  const citations = firstArray(
    source.citations,
    sageOutput.citations,
    sageOutput.sources,
    sage.citations,
    sage.sources,
  )

  return {
    raw: source,
    sessionId: source.session_id ?? null,
    query: source.query ?? '',
    finalAnswer: source.final_answer ?? '',
    factualAnswer: source.factual_answer ?? '',
    decisionState: source.decision_state ?? source.consensus_status ?? 'NOT_REPORTED',
    decisionReason: source.decision_reason ?? source.consensus_reason ?? '',
    citations: citations.map(normalizeCitation),
    agentFindings,
    completedAgents: firstArray(source.completed_agents).map(String),
    escalationTicketId: source.escalation_ticket_id ?? null,
    audit: normalizeAudit(source),
    legacyConfidence: source.confidence ?? null,
    escalationRequested: Boolean(source.escalate),
  }
}

export function formatConfidence(value) {
  if (value === null || value === undefined || value === '') return 'Not reported'

  if (typeof value === 'string' && Number.isNaN(Number(value))) {
    return humanize(value)
  }

  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  if (numeric < 0 || numeric > 100) return String(value)
  return `${Number(numeric.toFixed(1))}%`
}

export function formatValue(value) {
  if (value === null || value === undefined || value === '') return 'Not reported'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'None reported'
  if (typeof value === 'object') return JSON.stringify(value)
  const text = String(value)
  return text.includes('_') || (/[A-Z]/.test(text) && text === text.toUpperCase())
    ? humanize(text)
    : text
}

export function humanize(value) {
  if (value === null || value === undefined || value === '') return 'Not reported'
  const text = String(value).replaceAll('_', ' ').trim()
  if (!text) return 'Not reported'
  return text.toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function statusTone(status) {
  const value = String(status || '').toUpperCase()
  if (
    [
      'UNSUPPORTED',
      'NOT_SUPPORTED',
      'UNSAFE',
      'UNCONFIRMED',
      'NOT_CONFIRMED',
      'BLOCKED',
      'CRITICAL',
      'REJECTED',
      'FAILED',
      'ERROR',
      'UNAVAILABLE',
      'NOT_READY',
      'TIMEOUT',
      'INVALID_OUTPUT',
      'MODEL_ERROR',
      'DEPENDENCY_UNAVAILABLE',
    ].some((item) => value.includes(item))
  ) {
    return 'danger'
  }
  if (['ESCALATED', 'CLARIFICATION', 'WARNING', 'REWRITE', 'PENDING', 'SUBMITTED', 'OPEN', 'DEGRADED'].some((item) => value.includes(item))) {
    return 'warning'
  }
  if (['APPROVED', 'SAFE', 'SUPPORTED', 'RESOLVED', 'CONSENSUS_REACHED', 'CONFIRMED', 'AVAILABLE', 'OPERATIONAL', 'READY', 'ALIVE'].some((item) => value.includes(item))) {
    return 'success'
  }
  return 'neutral'
}

export function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}
