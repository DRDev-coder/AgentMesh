export interface AgentMeshRuntimeConfig {
  VITE_API_URL?: string
  VITE_API_TIMEOUT_MS?: string
  VITE_BLOCK_EXPLORER_TX_URL?: string
  VITE_GOOGLE_OAUTH_ENABLED?: string
  VITE_SUPABASE_PUBLISHABLE_KEY?: string
  VITE_SUPABASE_URL?: string
  VITE_TURNSTILE_SITE_KEY?: string
}

declare global {
  interface Window {
    __AGENTMESH_CONFIG__?: AgentMeshRuntimeConfig
  }
}

export function runtimeConfig(
  name: keyof AgentMeshRuntimeConfig,
  buildValue?: string,
): string | undefined {
  return window.__AGENTMESH_CONFIG__?.[name]?.trim() || buildValue?.trim() || undefined
}
