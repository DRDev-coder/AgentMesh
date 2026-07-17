import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthPage } from './AuthPages'
import { AuthProvider } from './AuthProvider'

function renderLogin() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/" element={<div>Dashboard destination</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('authentication pages', () => {
  it('validates credentials and signs in with the local development identity', async () => {
    const user = userEvent.setup()
    renderLogin()

    expect(screen.getByText('Local authentication mode is active.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Work email'), 'developer@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-password')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Dashboard destination')).toBeInTheDocument()
    expect(localStorage.getItem('agentmesh.dev.email')).toBe('developer@example.com')
  })
})
