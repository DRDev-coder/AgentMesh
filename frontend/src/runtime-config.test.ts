import { afterEach, describe, expect, it } from 'vitest'
import { runtimeConfig } from './runtime-config'

describe('runtimeConfig', () => {
  afterEach(() => {
    delete window.__AGENTMESH_CONFIG__
  })

  it('prefers container runtime configuration', () => {
    window.__AGENTMESH_CONFIG__ = { VITE_API_URL: ' https://api.example.com/api/v1 ' }

    expect(runtimeConfig('VITE_API_URL', 'http://localhost:8000/api/v1')).toBe(
      'https://api.example.com/api/v1',
    )
  })

  it('falls back to the Vite build value', () => {
    expect(runtimeConfig('VITE_API_URL', ' http://localhost:8000/api/v1 ')).toBe(
      'http://localhost:8000/api/v1',
    )
  })
})
