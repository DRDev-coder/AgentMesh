import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import OnboardingPage from './OnboardingPage'

const organization = {
  id: 'org-1',
  name: 'Northstar',
  slug: 'northstar',
  role: 'owner',
  status: 'active',
  billing_email: 'owner@example.com',
  spend_cap_paise: null,
  created_at: '2026-01-01T00:00:00Z',
}

const workspace = {
  id: 'workspace-1',
  organization_id: 'org-1',
  name: 'Support',
  slug: 'support',
  industry_template: 'GENERAL',
  status: 'active',
  active_profile_version_id: null,
  active_knowledge_release_id: null,
  created_at: '2026-01-01T00:00:00Z',
}

afterEach(() => {
  vi.restoreAllMocks()
  sessionStorage.clear()
})

describe('organization onboarding', () => {
  it('creates an isolated workspace and reveals the first test key once', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({ organization, workspace }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        id: 'key-1',
        name: 'First test key',
        environment: 'test',
        scopes: ['decisions:write'],
        last_four: 'last',
        status: 'active',
        expires_at: null,
        last_used_at: null,
        created_at: '2026-01-01T00:00:00Z',
        secret: 'am_test_public.secret-once',
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const user = userEvent.setup()

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <OnboardingPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await user.type(screen.getByLabelText('Company name'), 'Northstar')
    await user.click(screen.getByRole('button', { name: /create company and test key/i }))

    expect(await screen.findByText('Support is ready to configure.')).toBeInTheDocument()
    expect(screen.getByText('am_test_public.secret-once')).toBeInTheDocument()
    expect(sessionStorage.getItem('agentmesh.key.workspace-1')).toBe('am_test_public.secret-once')
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))

    const firstRequest = fetchMock.mock.calls[0]
    expect(firstRequest[0]).toBe('/api/v1/organizations')
    expect(JSON.parse(String(firstRequest[1]?.body))).toMatchObject({
      name: 'Northstar',
      workspace_name: 'Support',
      industry_template: 'GENERAL',
    })
  })
})
