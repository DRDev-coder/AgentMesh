const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim()

export const API_BASE_URL = (configuredBaseUrl || '/api/v1').replace(/\/$/, '')

const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS)
export const DEFAULT_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout > 0
  ? configuredTimeout
  : 90_000

export class ApiError extends Error {
  constructor(message, { kind = 'request', status = null, details = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.details = details
  }
}

function validationMessage(detail) {
  if (!Array.isArray(detail)) return null

  const messages = detail
    .map((item) => {
      if (!item || typeof item !== 'object') return null
      const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
      return [location, item.msg].filter(Boolean).join(': ')
    })
    .filter(Boolean)

  return messages.length ? messages.join('; ') : null
}

function responseMessage(payload, status) {
  if (payload && typeof payload === 'object') {
    const validation = validationMessage(payload.detail)
    if (validation) return validation
    if (typeof payload.detail === 'string') return payload.detail
    if (typeof payload.message === 'string') return payload.message
    if (typeof payload.error === 'string') return payload.error
  }

  return `Request failed with status ${status}`
}

async function parseErrorPayload(response) {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  try {
    const text = await response.text()
    return text ? { message: text } : null
  } catch {
    return null
  }
}

export async function apiRequest(path, {
  method = 'GET',
  body,
  signal,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  headers = {},
} = {}) {
  const controller = new AbortController()
  let timedOut = false

  const abortFromCaller = () => controller.abort()
  if (signal?.aborted) controller.abort()
  else signal?.addEventListener('abort', abortFromCaller, { once: true })

  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      if (timedOut) {
        throw new ApiError(`The request timed out after ${Math.round(timeoutMs / 1000)} seconds.`, {
          kind: 'timeout',
        })
      }
      throw new ApiError(
        'You stopped waiting for this response. The backend may still finish and persist the request.',
        { kind: 'cancelled' },
      )
    }

    throw new ApiError('The API could not be reached. Check the backend connection and try again.', {
      kind: 'network',
      details: error?.message,
    })
  } finally {
    clearTimeout(timeoutId)
    signal?.removeEventListener('abort', abortFromCaller)
  }

  if (!response.ok) {
    const payload = await parseErrorPayload(response)
    const kind = response.status === 422
      ? 'validation'
      : response.status >= 500
        ? 'server'
        : 'request'

    throw new ApiError(responseMessage(payload, response.status), {
      kind,
      status: response.status,
      details: payload,
    })
  }

  if (response.status === 204) return null

  try {
    return await response.json()
  } catch {
    throw new ApiError('The API returned an unreadable response.', {
      kind: 'protocol',
      status: response.status,
    })
  }
}

export function describeApiError(error) {
  const descriptions = {
    validation: { title: 'Check your request', tone: 'warning' },
    timeout: { title: 'Request timed out', tone: 'warning' },
    network: { title: 'Connection problem', tone: 'danger' },
    server: { title: 'Service error', tone: 'danger' },
    protocol: { title: 'Unexpected response', tone: 'danger' },
    cancelled: { title: 'Stopped waiting', tone: 'neutral' },
    request: { title: 'Request failed', tone: 'danger' },
  }

  return {
    ...(descriptions[error?.kind] || descriptions.request),
    message: error?.message || 'An unexpected error occurred.',
    status: error?.status || null,
  }
}
