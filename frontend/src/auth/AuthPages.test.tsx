import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AuthPage } from './AuthPages'
import { AuthProvider } from './AuthProvider'

function renderAuth(path: '/login' | '/signup') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/signup" element={<AuthPage mode="signup" />} />
            <Route path="/dashboard" element={<div>Dashboard destination</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('authentication pages', () => {
  beforeEach(() => {
    cleanup()
    localStorage.clear()
  })

  it('validates credentials and signs in with the local development identity', async () => {
    const user = userEvent.setup()
    renderAuth('/login')

    expect(screen.getByText('Local authentication mode is active.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Work email'), 'developer@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Dashboard destination')).toBeInTheDocument()
    expect(localStorage.getItem('agentmesh.dev.email')).toBe('developer@example.com')
  })

  it('collects company and workspace details during signup', async () => {
    const user = userEvent.setup()
    renderAuth('/signup')

    await user.type(screen.getByLabelText('Full name'), 'Muthu Kumar')
    await user.type(screen.getByLabelText('Company name'), 'Northstar Support')
    await user.type(screen.getByLabelText('Work email'), 'muthu@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-password')
    await user.type(screen.getByLabelText('Confirm password'), 'correct-password')
    await user.click(screen.getByLabelText(/I agree to the/i))
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('Dashboard destination')).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem('agentmesh.pending-signup') || '{}')).toMatchObject({
      fullName: 'Muthu Kumar',
      companyName: 'Northstar Support',
      workspaceName: 'Support',
      template: 'GENERAL',
    })
  })
})
