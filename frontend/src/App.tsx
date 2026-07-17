import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { AuthPage, ForgotPasswordPage, VerifyPage } from './auth/AuthPages'
import { useAuth } from './auth/AuthProvider'
import SaaSShell from './components/SaaSShell'
import { saasRequest, type Organization, type Workspace } from './lib/saas-api'
import LandingPage from './pages/LandingPage'
import AdminDashboard from './pages/AdminDashboard'
import OnboardingPage from './pages/OnboardingPage'
import AcceptInvitePage from './pages/AcceptInvitePage'
import {
  ConfigurationPage,
  DecisionsPage,
  DevelopersPage,
  KnowledgePage,
  OverviewPage,
  PlaygroundPage,
  ReviewsPage,
  SettingsPage,
  TeamPage,
  UsagePage,
} from './pages/SaaSPages'

function ProtectedRoute() {
  const auth = useAuth()
  if (auth.loading) return <div className="fullscreen-loading"><span className="spin" /> Verifying session…</div>
  if (!auth.user) return <Navigate to="/login" replace />
  return <Outlet />
}

function EntryRedirect() {
  const organizations = useQuery({
    queryKey: ['organizations'],
    queryFn: () => saasRequest<Organization[]>('/organizations'),
  })
  const first = organizations.data?.[0]
  const workspaces = useQuery({
    queryKey: ['workspaces', first?.id],
    queryFn: () => saasRequest<Workspace[]>(`/organizations/${first!.id}/workspaces`),
    enabled: Boolean(first),
  })
  if (organizations.isLoading || (first && workspaces.isLoading)) return <div className="fullscreen-loading"><span className="spin" /> Loading AgentMesh…</div>
  if (organizations.error) return <div className="fullscreen-loading">Unable to load organizations.</div>
  if (!first) return <Navigate to="/onboarding" replace />
  const workspace = workspaces.data?.[0]
  if (!workspace) return <Navigate to="/onboarding" replace />
  return <Navigate to={`/app/${first.slug}/${workspace.slug}/overview`} replace />
}

function BillingRedirect() {
  const navigate = useNavigate()
  React.useEffect(() => {
    void navigate('/dashboard', { replace: true })
  }, [navigate])
  return <div className="fullscreen-loading">Returning to billing…</div>
}

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/signup" element={<AuthPage mode="signup" />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/verify" element={<VerifyPage />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<EntryRedirect />} />
        <Route path="/billing" element={<BillingRedirect />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
        <Route path="/app/:orgSlug/:workspaceSlug" element={<SaaSShell />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="playground" element={<PlaygroundPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="configuration" element={<ConfigurationPage />} />
          <Route path="decisions" element={<DecisionsPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
          <Route path="developers" element={<DevelopersPage />} />
          <Route path="usage" element={<UsagePage />} />
          <Route path="team" element={<TeamPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="/platform/*" element={<AdminDashboard />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
