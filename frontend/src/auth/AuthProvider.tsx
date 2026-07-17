import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { authConfigured, supabase } from '../lib/supabase'
import { setDevelopmentIdentity, setTokenProvider } from '../lib/saas-api'

interface AuthContextValue {
  user: User | { id: string; email?: string } | null
  session: Session | null
  loading: boolean
  developmentMode: boolean
  signIn(email: string, password: string): Promise<void>
  signUp(email: string, password: string, captchaToken?: string): Promise<void>
  signInWithGoogle(): Promise<void>
  sendPasswordReset(email: string): Promise<void>
  signOut(): Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function localUser() {
  const id = localStorage.getItem('agentmesh.dev.user')
  if (!id) return null
  return {
    id,
    email: localStorage.getItem('agentmesh.dev.email') || 'owner@example.local',
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [developmentUser, setDevelopmentUser] = useState(localUser)
  const [loading, setLoading] = useState(authConfigured)

  useEffect(() => {
    setTokenProvider(async () => session?.access_token || null)
  }, [session])

  useEffect(() => {
    if (!supabase) return
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setLoading(false)
    })
    return () => data.subscription.unsubscribe()
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user: authConfigured ? session?.user || null : developmentUser,
    session,
    loading,
    developmentMode: !authConfigured,
    async signIn(email, password) {
      if (!supabase) {
        const id = `dev-${email.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 60)}`
        setDevelopmentIdentity(id, email)
        setDevelopmentUser({ id, email })
        return
      }
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
    },
    async signUp(email, password, captchaToken) {
      if (!supabase) {
        const id = `dev-${email.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 60)}`
        setDevelopmentIdentity(id, email)
        setDevelopmentUser({ id, email })
        return
      }
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/verify`,
          captchaToken,
        },
      })
      if (error) throw error
    },
    async signInWithGoogle() {
      if (!supabase) return
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/onboarding` },
      })
      if (error) throw error
    },
    async sendPasswordReset(email) {
      if (!supabase) return
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/verify`,
      })
      if (error) throw error
    },
    async signOut() {
      if (supabase) await supabase.auth.signOut()
      else {
        localStorage.removeItem('agentmesh.dev.user')
        localStorage.removeItem('agentmesh.dev.email')
        setDevelopmentUser(null)
      }
      setSession(null)
    },
  }), [developmentUser, loading, session])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used within AuthProvider')
  return value
}
