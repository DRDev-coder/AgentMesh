const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim()
export const API_BASE_URL = (configuredBaseUrl || '/api/v1').replace(/\/$/, '')

type TokenProvider = () => Promise<string | null>

let tokenProvider: TokenProvider = async () => null
let developmentIdentity = {
  userId: localStorage.getItem('agentmesh.dev.user') || 'local-owner',
  email: localStorage.getItem('agentmesh.dev.email') || 'owner@example.local',
}

export function setTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider
}

export function setDevelopmentIdentity(userId: string, email: string): void {
  developmentIdentity = { userId, email }
  localStorage.setItem('agentmesh.dev.user', userId)
  localStorage.setItem('agentmesh.dev.email', email)
}

export class SaaSApiError extends Error {
  status: number
  code: string
  details: unknown

  constructor(message: string, status = 0, code = 'request_failed', details?: unknown) {
    super(message)
    this.name = 'SaaSApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  apiKey?: string
  idempotencyKey?: string
}

export async function saasRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const token = options.apiKey ? null : await tokenProvider()
  const isFormData = options.body instanceof FormData
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.apiKey) headers.set('Authorization', `Bearer ${options.apiKey}`)
  else if (token) headers.set('Authorization', `Bearer ${token}`)
  else {
    headers.set('X-Dev-User', developmentIdentity.userId)
    headers.set('X-Dev-Email', developmentIdentity.email)
  }
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey)
  if (options.body !== undefined && !isFormData) headers.set('Content-Type', 'application/json')

  let requestBody: BodyInit | undefined
  if (options.body instanceof FormData) requestBody = options.body
  else if (options.body !== undefined) requestBody = JSON.stringify(options.body)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      body: requestBody,
    })
  } catch (error) {
    throw new SaaSApiError(
      error instanceof Error ? error.message : 'The AgentMesh API could not be reached.',
      0,
      'network_error',
    )
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const error = payload?.error
    throw new SaaSApiError(
      error?.message || payload?.detail || `Request failed with status ${response.status}.`,
      response.status,
      error?.code || 'request_failed',
      error?.details,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export interface Organization {
  id: string
  name: string
  slug: string
  role: string
  status: string
  billing_email: string
  spend_cap_paise: number | null
  created_at: string
}

export interface Workspace {
  id: string
  organization_id: string
  name: string
  slug: string
  industry_template: string
  status: string
  active_profile_version_id: string | null
  active_knowledge_release_id: string | null
  created_at: string
}

export interface DocumentRecord {
  id: string
  name: string
  status: string
  current_version: number
  filename: string | null
  media_type: string | null
  byte_size: number | null
  sha256: string | null
  extraction_error: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyRecord {
  id: string
  name: string
  environment: 'test' | 'live'
  scopes: string[]
  last_four: string
  status: string
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  secret?: string
}

export interface UsageSummary {
  organization_id: string
  period: string
  completed_decisions: number
  included_decisions: number
  overage_decisions: number
  remaining_free_decisions: number
  billing_status: string
  payment_method_present: boolean
  spend_cap_paise: number | null
  projected_overage_paise: number | null
  razorpay_projection_is_async: boolean
}

export interface DecisionRecord {
  id: string
  session_id: string
  answer?: string
  state?: string
  decision_state?: string
  reason?: string
  decision_reason?: string
  environment?: string
  citations?: Array<{
    document_id: string
    chunk_id: string
    text: string
    metadata: Record<string, unknown>
    distance_or_similarity: number
  }>
  trace?: {
    agent_findings: Record<string, unknown>
    profile_version_id: string | null
    knowledge_release_id: string | null
    model_id: string
  } | null
  escalation_id: string | null
  usage_units: number
  created_at: string
}

export interface ReviewRecord {
  id: string
  decision_id: string | null
  session_id: string
  query: string
  draft_answer: string
  reason: string
  priority: string
  status: string
  assigned_to: string | null
  resolution_notes: string | null
  lock_version: number
  created_at: string
  updated_at: string
}
