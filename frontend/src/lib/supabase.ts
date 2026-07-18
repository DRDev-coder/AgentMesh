import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { runtimeConfig } from '../runtime-config'

const url = runtimeConfig('VITE_SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL)
const publishableKey = runtimeConfig(
  'VITE_SUPABASE_PUBLISHABLE_KEY',
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
)

export const authConfigured = Boolean(url && publishableKey)

export const supabase: SupabaseClient | null = url && publishableKey
  ? createClient(url, publishableKey, {
      auth: {
        flowType: 'pkce',
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null
