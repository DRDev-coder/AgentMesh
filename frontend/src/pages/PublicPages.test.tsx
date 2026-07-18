import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import LandingPage from './LandingPage'
import { ApiDocumentationPage, CompanyPage, DevelopersPublicPage } from './PublicPages'


function renderPublic(page: React.ReactNode) {
  return render(<MemoryRouter>{page}</MemoryRouter>)
}

describe('public product information', () => {
  it('links footer documentation and company content without requiring signup', () => {
    renderPublic(<LandingPage />)

    expect(screen.getAllByRole('link', { name: 'API documentation' })[0]).toHaveAttribute('href', '/docs')
    expect(screen.getAllByRole('link', { name: 'About' })[0]).toHaveAttribute('href', '/company')
    expect(screen.getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
  })

  it('renders public API, developer, and company pages', () => {
    const api = renderPublic(<ApiDocumentationPage />)
    expect(screen.getByText('Build evidence-grounded support decisions.')).toBeInTheDocument()
    api.unmount()

    const developers = renderPublic(<DevelopersPublicPage />)
    expect(screen.getByText('Integrate without guessing.')).toBeInTheDocument()
    developers.unmount()

    renderPublic(<CompanyPage />)
    expect(screen.getByText('Trust infrastructure for support teams.')).toBeInTheDocument()
  })
})
