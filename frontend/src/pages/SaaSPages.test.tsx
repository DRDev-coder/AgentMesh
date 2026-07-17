import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import React from 'react'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceRouteContext } from '../components/SaaSShell'
import {
  ConfigurationPage,
  DecisionsPage,
  DevelopersPage,
  KnowledgePage,
  OverviewPage,
  PlatformPage,
  PlaygroundPage,
  ReviewsPage,
  SettingsPage,
  TeamPage,
  UsagePage,
} from './SaaSPages'

/* ------------------------------------------------------------------ */
/*  Shared fixtures and helpers                                       */
/* ------------------------------------------------------------------ */

const ORG = {
  id: 'org-1',
  name: 'TestCo',
  slug: 'testco',
  role: 'owner',
  status: 'ACTIVE',
  billing_email: 'owner@testco.com',
  spend_cap_cents: null,
  created_at: '2026-01-01T00:00:00Z',
}

const WORKSPACE = {
  id: 'ws-1',
  organization_id: 'org-1',
  name: 'Support',
  slug: 'support',
  industry_template: 'GENERAL',
  status: 'ACTIVE',
  active_profile_version_id: null,
  active_knowledge_release_id: null,
  created_at: '2026-01-01T00:00:00Z',
}

const CONTEXT: WorkspaceRouteContext = {
  organization: ORG,
  workspace: WORKSPACE,
  organizations: [ORG],
  workspaces: [WORKSPACE],
  basePath: '/app/testco/support',
}

function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

/**
 * URL-based fetch mock: maps URL substring patterns to response bodies.
 * This avoids issues with TanStack Query firing hooks in unpredictable order.
 */
function mockFetchRoutes(routes: Record<string, unknown>) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : (input as Request).url
    for (const [pattern, body] of Object.entries(routes)) {
      if (url.includes(pattern)) return json(body)
    }
    return json([])
  })
}

/** Renders a page inside the outlet context that SaaSShell provides. */
function renderPage(Page: React.ComponentType, context: WorkspaceRouteContext = CONTEXT) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  })
  function Layout() {
    return <Outlet context={context} />
  }
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/app/testco/support/current']}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/app/testco/support/current" element={<Page />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  sessionStorage.clear()
})

/* ------------------------------------------------------------------ */
/*  OverviewPage                                                      */
/* ------------------------------------------------------------------ */

describe('OverviewPage', () => {
  it('renders usage metrics, decision list, and readiness checklist', async () => {
    mockFetchRoutes({
      '/usage': {
        organization_id: 'org-1',
        period: '2026-07',
        completed_decisions: 42,
        included_decisions: 500,
        overage_decisions: 0,
        remaining_free_decisions: 458,
        billing_status: 'FREE',
        payment_method_present: false,
        spend_cap_cents: null,
        projected_overage_cents: null,
        stripe_projection_is_async: true,
      },
      '/decisions': [{
        id: 'd-1',
        session_id: 's-1',
        state: 'APPROVED',
        reason: 'Grounded and verified',
        environment: 'test',
        created_at: '2026-01-01T00:00:00Z',
      }],
      '/documents': [{
        id: 'doc-1',
        name: 'Returns Policy',
        status: 'PUBLISHED',
        current_version: 1,
        filename: 'returns.md',
        media_type: 'text/markdown',
        byte_size: 1024,
        sha256: 'abc123',
        extraction_error: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }],
    })

    renderPage(OverviewPage)

    expect(await screen.findByText('42')).toBeInTheDocument()
    expect(screen.getByText('458')).toBeInTheDocument()
    expect(screen.getByText('FREE')).toBeInTheDocument()
    expect(screen.getByText('APPROVED')).toBeInTheDocument()
    expect(screen.getByText('Workspace readiness')).toBeInTheDocument()
    expect(screen.getByText('Upload approved knowledge')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  KnowledgePage                                                     */
/* ------------------------------------------------------------------ */

describe('KnowledgePage', () => {
  it('renders upload panel, document table, and publish button', async () => {
    mockFetchRoutes({
      '/documents': [{
        id: 'doc-1',
        name: 'Returns Policy',
        status: 'READY_FOR_REVIEW',
        current_version: 1,
        filename: 'returns.md',
        media_type: 'text/markdown',
        byte_size: 2048,
        sha256: 'abc',
        extraction_error: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }],
      '/knowledge-releases': [],
    })

    renderPage(KnowledgePage)

    expect(await screen.findByText('Returns Policy')).toBeInTheDocument()
    expect(screen.getByText('READY FOR REVIEW')).toBeInTheDocument()
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
    expect(screen.getByText('Add approved knowledge')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /publish release/i })).toBeInTheDocument()
    expect(screen.getByText(/Do not upload PHI/)).toBeInTheDocument()
  })

  it('shows empty state when no documents exist', async () => {
    mockFetchRoutes({ '/documents': [], '/knowledge-releases': [] })
    renderPage(KnowledgePage)
    expect(await screen.findByText('No workspace documents')).toBeInTheDocument()
  })

  it('explains async processing and disables publishing until documents are ready', async () => {
    mockFetchRoutes({
      '/documents': [{
        id: 'doc-1',
        name: 'Returns Policy',
        status: 'PROCESSING',
        current_version: 1,
        filename: 'returns.md',
        media_type: 'text/markdown',
        byte_size: 2048,
        sha256: 'abc',
        extraction_error: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }],
      '/knowledge-releases': [],
    })
    renderPage(KnowledgePage)

    expect(await screen.findByText('Document processing is running.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /processing/i })).toBeDisabled()
  })
})

/* ------------------------------------------------------------------ */
/*  ConfigurationPage                                                 */
/* ------------------------------------------------------------------ */

describe('ConfigurationPage', () => {
  it('renders profile form with template, tone, and escalation fields', async () => {
    mockFetchRoutes({
      '/profiles': [{
        id: 'pv-1',
        version: 1,
        status: 'DRAFT',
        template_key: 'GENERAL',
        tone: 'PROFESSIONAL',
        response_length: 'CONCISE',
        custom_instructions: '',
        supported_topics: [],
        enabled_rule_packs: [],
        escalation_threshold: 7,
        published_at: null,
      }],
    })

    renderPage(ConfigurationPage)

    /* Wait for data-dependent content (profile version list) before asserting */
    expect(await screen.findByRole('button', { name: /publish/i })).toBeInTheDocument()
    expect(screen.getByText('Create profile draft')).toBeInTheDocument()
    expect(screen.getByText('Industry template')).toBeInTheDocument()
    expect(screen.getByText('Default tone')).toBeInTheDocument()
    expect(screen.getByText('Escalation threshold')).toBeInTheDocument()
    expect(screen.getByText('Platform safeguards')).toBeInTheDocument()
    expect(screen.getByText('Profile versions')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save draft/i })).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  DevelopersPage                                                    */
/* ------------------------------------------------------------------ */

describe('DevelopersPage', () => {
  it('renders key creation form, key table with revoke, and webhook management', async () => {
    mockFetchRoutes({
      '/api-keys': [{
        id: 'key-1',
        name: 'CI key',
        environment: 'test',
        scopes: ['decisions:write'],
        last_four: 'abcd',
        status: 'ACTIVE',
        expires_at: null,
        last_used_at: null,
        created_at: '2026-01-01T00:00:00Z',
      }],
      '/webhook-deliveries': [],
      '/webhooks': [],
    })

    renderPage(DevelopersPage)

    expect(await screen.findByText('CI key')).toBeInTheDocument()
    expect(screen.getByText('Create API key')).toBeInTheDocument()
    expect(screen.getByText('••••abcd')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /revoke key/i })).toBeInTheDocument()
    expect(screen.getByText('Workspace webhooks')).toBeInTheDocument()
    expect(screen.getByText('Create a decision')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  PlaygroundPage                                                    */
/* ------------------------------------------------------------------ */

describe('PlaygroundPage', () => {
  it('renders composer without requiring a pasted API key', () => {
    renderPage(PlaygroundPage)

    expect(screen.getByText('Run the full council')).toBeInTheDocument()
    expect(screen.getByText('No API key required here.')).toBeInTheDocument()
    expect(screen.queryByText('Test API key')).not.toBeInTheDocument()
    expect(screen.getByText('Customer question')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /run decision/i })).toBeDisabled()
    expect(screen.getByText('No result yet')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  DecisionsPage                                                     */
/* ------------------------------------------------------------------ */

describe('DecisionsPage', () => {
  it('renders decision list and detail inspector', async () => {
    mockFetchRoutes({
      '/decisions': [{
        id: 'd-1',
        session_id: 's-1',
        state: 'APPROVED',
        reason: 'Evidence verified',
        environment: 'test',
        created_at: '2026-01-01T00:00:00Z',
      }],
    })

    renderPage(DecisionsPage)

    /* Wait for data-dependent text that confirms the query resolved */
    expect(await screen.findByText('APPROVED')).toBeInTheDocument()
    expect(screen.getByText('Decision records')).toBeInTheDocument()
    expect(screen.getByText('Evidence verified')).toBeInTheDocument()
    expect(screen.getByText('Select a decision')).toBeInTheDocument()
  })

  it('shows empty state when no decisions exist', async () => {
    mockFetchRoutes({ '/decisions': [] })
    renderPage(DecisionsPage)
    expect(await screen.findByText('No records')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  ReviewsPage                                                       */
/* ------------------------------------------------------------------ */

describe('ReviewsPage', () => {
  it('renders escalation queue with claim action for OPEN reviews', async () => {
    mockFetchRoutes({
      '/reviews': [{
        id: 'esc-1',
        decision_id: 'd-1',
        session_id: 's-1',
        query: 'I need an immediate refund',
        draft_answer: 'Our policy allows returns within 30 days.',
        reason: 'High-risk financial request',
        priority: 'HIGH',
        status: 'OPEN',
        assigned_to: null,
        resolution_notes: null,
        lock_version: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }],
    })

    renderPage(ReviewsPage)

    /* Wait for data-dependent text that confirms the query resolved */
    expect(await screen.findByText('I need an immediate refund')).toBeInTheDocument()
    expect(screen.getByText('Escalation queue')).toBeInTheDocument()
    expect(screen.getByText('HIGH')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /claim review/i })).toBeInTheDocument()
    expect(screen.getByText(/Approval reruns safety/)).toBeInTheDocument()
  })

  it('shows empty queue message when no reviews exist', async () => {
    mockFetchRoutes({ '/reviews': [] })
    renderPage(ReviewsPage)
    expect(await screen.findByText('Queue clear')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  UsagePage                                                         */
/* ------------------------------------------------------------------ */

describe('UsagePage', () => {
  it('renders usage meter, billing status, checkout button, and spend cap form', async () => {
    mockFetchRoutes({
      '/usage': {
        organization_id: 'org-1',
        period: '2026-07',
        completed_decisions: 120,
        included_decisions: 500,
        overage_decisions: 0,
        remaining_free_decisions: 380,
        billing_status: 'FREE',
        payment_method_present: false,
        spend_cap_cents: null,
        projected_overage_cents: null,
        stripe_projection_is_async: true,
      },
    })

    renderPage(UsagePage)

    expect(await screen.findByText('120 completed decisions')).toBeInTheDocument()
    expect(screen.getByText('380 remaining')).toBeInTheDocument()
    expect(screen.getByText('2026-07')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add payment method/i })).toBeInTheDocument()
    expect(screen.getByText('Monthly spend cap')).toBeInTheDocument()
    expect(screen.getByText(/Stripe invoice projections update asynchronously/)).toBeInTheDocument()
  })

  it('shows billing portal button when payment method is active', async () => {
    mockFetchRoutes({
      '/usage': {
        organization_id: 'org-1',
        period: '2026-07',
        completed_decisions: 600,
        included_decisions: 500,
        overage_decisions: 100,
        remaining_free_decisions: 0,
        billing_status: 'ACTIVE',
        payment_method_present: true,
        spend_cap_cents: 5000,
        projected_overage_cents: 200,
        stripe_projection_is_async: true,
      },
    })

    renderPage(UsagePage)

    expect(await screen.findByText('600 completed decisions')).toBeInTheDocument()
    expect(screen.getByText('Billing is active')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open billing portal/i })).toBeInTheDocument()
    expect(screen.getByText('Current cap: $50.00')).toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  TeamPage                                                          */
/* ------------------------------------------------------------------ */

describe('TeamPage', () => {
  it('renders invitation form and member table with role management', async () => {
    mockFetchRoutes({
      '/members': [
        {
          id: 'm-1',
          auth_user_id: 'u-1',
          email: 'owner@testco.com',
          role: 'owner',
          status: 'ACTIVE',
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'm-2',
          auth_user_id: 'u-2',
          email: 'dev@testco.com',
          role: 'developer',
          status: 'ACTIVE',
          created_at: '2026-01-02T00:00:00Z',
        },
      ],
    })

    renderPage(TeamPage)

    expect(await screen.findByText('owner@testco.com')).toBeInTheDocument()
    expect(screen.getByText('Invite a team member')).toBeInTheDocument()
    expect(screen.getByText('dev@testco.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send invitation/i })).toBeInTheDocument()
  })

  it('hides invitation form for non-admin roles', async () => {
    mockFetchRoutes({
      '/members': [{
        id: 'm-1',
        auth_user_id: 'u-1',
        email: 'viewer@testco.com',
        role: 'viewer',
        status: 'ACTIVE',
        created_at: '2026-01-01T00:00:00Z',
      }],
    })

    const viewerContext = {
      ...CONTEXT,
      organization: { ...ORG, role: 'viewer' },
    }
    renderPage(TeamPage, viewerContext)

    expect(await screen.findByText('viewer@testco.com')).toBeInTheDocument()
    expect(screen.queryByText('Invite a team member')).not.toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  SettingsPage                                                      */
/* ------------------------------------------------------------------ */

describe('SettingsPage', () => {
  it('renders workspace identity, workspace creation form, and org deletion for owner', () => {
    renderPage(SettingsPage)

    expect(screen.getByText('Workspace identity')).toBeInTheDocument()
    expect(screen.getByText('TestCo')).toBeInTheDocument()
    expect(screen.getByText('Create another workspace')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create workspace/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete organization/i })).toBeInTheDocument()
    expect(screen.getByText(/not configured for PHI/)).toBeInTheDocument()
  })

  it('hides danger zone for non-owner roles', () => {
    const adminContext = {
      ...CONTEXT,
      organization: { ...ORG, role: 'admin' },
    }
    renderPage(SettingsPage, adminContext)

    expect(screen.getByText('Workspace identity')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /delete organization/i })).not.toBeInTheDocument()
  })
})

/* ------------------------------------------------------------------ */
/*  PlatformPage                                                      */
/* ------------------------------------------------------------------ */

describe('PlatformPage', () => {
  it('renders platform metrics, health, organizations, and templates', async () => {
    mockFetchRoutes({
      '/platform/metrics': {
        organizations: 12,
        decisions: 3400,
        failed_billing_events: 0,
        failed_jobs: 2,
        failed_webhooks: 1,
        failed_emails: 0,
      },
      '/platform/organizations': [{
        id: 'org-a',
        name: 'Acme Corp',
        slug: 'acme',
        status: 'ACTIVE',
        billing_email: 'billing@acme.com',
        created_at: '2026-01-01T00:00:00Z',
      }],
      '/platform/service-health': {
        postgresql: true,
        redis: true,
        pending_jobs: 5,
        pending_billing_events: 0,
      },
      '/platform/templates': [{
        id: 'tpl-1',
        key: 'GENERAL',
        version: 1,
        name: 'General template',
        enabled: true,
        mandatory_rule_keys: ['GLOBAL_SAFETY'],
      }],
    })

    /* PlatformPage is rendered outside the outlet context */
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
    })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/platform']}>
          <Routes>
            <Route path="/platform" element={<PlatformPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    /* Wait for data-dependent text to confirm async queries settled */
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('AgentMesh platform')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('3400')).toBeInTheDocument()
    expect(screen.getByText('General template')).toBeInTheDocument()
    expect(screen.getByText('GLOBAL_SAFETY')).toBeInTheDocument()
  })
})
