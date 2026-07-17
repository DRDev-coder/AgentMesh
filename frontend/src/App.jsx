import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { apiRequest, describeApiError } from './api'
import AgentDebateViewer from './components/AgentDebateViewer'
import AppShell from './components/AppShell'
import ChatInterface from './components/ChatInterface'
import HumanReviewQueue from './components/HumanReviewQueue'
import SystemStatus from './components/SystemStatus'

const PAGES = {
  chat: {
    eyebrow: 'Customer channel',
    title: 'Customer chat',
    description: 'Evidence-grounded support with policy, safety, grounding, and urgency checks on every reply.',
  },
  trace: {
    eyebrow: 'Decision record',
    title: 'Decision Trace',
    description: 'Inspect the evidence and specialist findings behind the latest response.',
  },
  review: {
    eyebrow: 'Operations',
    title: 'Human Review',
    description: 'Assess escalated responses and record an accountable reviewer decision.',
  },
  status: {
    eyebrow: 'Environment',
    title: 'System Status',
    description: 'Verify API liveness, readiness, and configured dependencies.',
  },
}

const INITIAL_HEALTH = {
  loading: true,
  liveness: { status: 'PENDING', label: 'Checking' },
  readiness: { status: 'PENDING', label: 'Checking' },
  dependencies: {},
  lastChecked: null,
  error: null,
}

function useSystemHealth() {
  const [health, setHealth] = useState(INITIAL_HEALTH)

  const refresh = useCallback(async () => {
    setHealth((current) => ({ ...current, loading: true, error: null }))
    const [livenessResult, readinessResult] = await Promise.allSettled([
      apiRequest('/healthz', { timeoutMs: 10_000 }),
      apiRequest('/health', { timeoutMs: 10_000 }),
    ])

    const livenessOk = livenessResult.status === 'fulfilled'
      && String(livenessResult.value?.status || '').toLowerCase() === 'alive'
    const readinessPayload = readinessResult.status === 'fulfilled' ? readinessResult.value : null
    const readinessOk = Boolean(readinessPayload?.ready)
    const failedResult = livenessResult.status === 'rejected'
      ? livenessResult
      : readinessResult.status === 'rejected'
        ? readinessResult
        : null

    setHealth({
      loading: false,
      liveness: livenessOk
        ? { status: 'OPERATIONAL', label: 'Operational' }
        : { status: 'UNAVAILABLE', label: 'Unavailable' },
      readiness: readinessPayload
        ? readinessOk
          ? { status: 'OPERATIONAL', label: 'Operational' }
          : { status: 'DEGRADED', label: 'Degraded' }
        : { status: 'UNAVAILABLE', label: 'Unavailable' },
      dependencies: readinessPayload?.dependencies || {},
      lastChecked: new Date().toISOString(),
      error: failedResult ? describeApiError(failedResult.reason) : null,
    })
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { health, refresh }
}

function App() {
  const [activeSession, setActiveSession] = useState(null)
  const [latestDecision, setLatestDecision] = useState(null)
  const [conversationResetToken, setConversationResetToken] = useState(0)
  const [view, setView] = useState('chat')
  const { health, refresh } = useSystemHealth()

  const handleDecision = (decision) => {
    if (decision?.session_id) setActiveSession(decision.session_id)
    setLatestDecision(decision)
  }

  const startNewConversation = () => {
    setActiveSession(null)
    setLatestDecision(null)
    setConversationResetToken((token) => token + 1)
    setView('chat')
  }

  const readiness = useMemo(() => {
    if (health.loading && !health.lastChecked) return { status: 'PENDING', label: 'Checking system' }
    if (health.liveness.status === 'UNAVAILABLE') return { status: 'UNAVAILABLE', label: 'System unavailable' }
    if (health.readiness.status === 'OPERATIONAL') return { status: 'OPERATIONAL', label: 'System ready' }
    return { status: 'DEGRADED', label: 'System degraded' }
  }, [health])

  return (
    <AppShell
      view={view}
      onNavigate={setView}
      page={PAGES[view]}
      readiness={readiness}
      health={health}
      activeSession={activeSession}
      onNewConversation={startNewConversation}
    >
      <div className="chat-view" hidden={view !== 'chat'}>
        <ChatInterface
          sessionId={activeSession}
          resetToken={conversationResetToken}
          latestDecision={latestDecision}
          health={health}
          onDecision={handleDecision}
          onOpenTrace={() => setView('trace')}
        />
      </div>

      {view === 'trace' && (
        <AgentDebateViewer
          decision={latestDecision}
          sessionId={activeSession}
          onOpenChat={() => setView('chat')}
        />
      )}

      {view === 'review' && <HumanReviewQueue />}
      {view === 'status' && <SystemStatus health={health} onRefresh={refresh} />}
    </AppShell>
  )
}

export default App
