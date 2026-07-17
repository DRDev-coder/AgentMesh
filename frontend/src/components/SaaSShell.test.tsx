import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider'
import SaaSShell from './SaaSShell'

function json(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

const ORGS = [{
  id: 'org-1',
  name: 'TestCo',
  slug: 'testco',
  role: 'owner',
  status: 'ACTIVE',
  billing_email: 'owner@testco.com',
  spend_cap_cents: null,
  created_at: '2026-01-01T00:00:00Z',
}]

const WORKSPACES = [
  {
    id: 'ws-1',
    organization_id: 'org-1',
    name: 'Support',
    slug: 'support',
    industry_template: 'GENERAL',
    status: 'ACTIVE',
    active_profile_version_id: null,
    active_knowledge_release_id: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'ws-2',
    organization_id: 'org-1',
    name: 'Sales',
    slug: 'sales',
    industry_template: 'ECOMMERCE',
    status: 'ACTIVE',
    active_profile_version_id: null,
    active_knowledge_release_id: null,
    created_at: '2026-01-02T00:00:00Z',
  },
]

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function renderShell() {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : (input as Request).url
    if (url.includes('/workspaces')) return json(WORKSPACES)
    if (url.includes('/organizations')) return json(ORGS)
    return json([])
  })

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  })

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/app/testco/support/overview']}>
        <AuthProvider>
          <Routes>
            <Route path="/app/:orgSlug/:workspaceSlug" element={<SaaSShell />}>
              <Route path="overview" element={<div>Overview outlet</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SaaSShell', () => {
  it('renders workspace name, navigation items, and role badge', async () => {
    renderShell()

    expect(await screen.findByText('Overview outlet')).toBeInTheDocument()
    expect(screen.getByText('AgentMesh')).toBeInTheDocument()
    expect(screen.getAllByText('owner')).toHaveLength(2)

    // Navigation items are within the sidebar nav
    const nav = screen.getByRole('navigation', { name: /product navigation/i })
    expect(nav).toBeInTheDocument()
    expect(nav.textContent).toContain('Overview')
    expect(nav.textContent).toContain('Playground')
    expect(nav.textContent).toContain('Knowledge')
    expect(nav.textContent).toContain('Configuration')
    expect(nav.textContent).toContain('Decisions')
    expect(nav.textContent).toContain('Human review')
    expect(nav.textContent).toContain('Developers')
    expect(nav.textContent).toContain('Team')
    expect(nav.textContent).toContain('Settings')
  })

  it('renders workspace switcher with both workspaces', async () => {
    renderShell()

    expect(await screen.findByText('Overview outlet')).toBeInTheDocument()
    const select = screen.getByRole('combobox', { name: /select workspace/i })
    expect(select).toBeInTheDocument()

    const options = Array.from(select.querySelectorAll('option'))
    expect(options).toHaveLength(2)
    expect(options[0].textContent).toBe('Support')
    expect(options[1].textContent).toBe('Sales')
  })

  it('shows sign-out button', async () => {
    renderShell()
    expect(await screen.findByText('Sign out')).toBeInTheDocument()
  })
})
