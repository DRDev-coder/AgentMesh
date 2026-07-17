import React, { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { useAuth } from './AuthProvider'
import { MeshMark } from '../components/AppShell'

declare global {
  interface Window {
    turnstile?: {
      render(element: HTMLElement, options: {
        sitekey: string
        callback: (token: string) => void
        'expired-callback': () => void
        theme: 'light'
      }): string
      remove(widgetId: string): void
    }
  }
}

const captchaSiteKey = import.meta.env.VITE_TURNSTILE_SITE_KEY?.trim()

function SignupCaptcha({ onToken }: { onToken: (token: string | null) => void }) {
  const container = React.useRef<HTMLDivElement>(null)
  React.useEffect(() => {
    if (!captchaSiteKey || !container.current) return
    const renderWidget = () => {
      if (!window.turnstile || !container.current || container.current.dataset.rendered) return
      container.current.dataset.rendered = 'true'
      const widgetId = window.turnstile.render(container.current, {
        sitekey: captchaSiteKey,
        callback: (token) => onToken(token),
        'expired-callback': () => onToken(null),
        theme: 'light',
      })
      container.current.dataset.widgetId = widgetId
    }
    const existing = document.querySelector<HTMLScriptElement>('script[data-agentmesh-turnstile]')
    if (existing) {
      existing.addEventListener('load', renderWidget)
      renderWidget()
      return () => existing.removeEventListener('load', renderWidget)
    }
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    script.async = true
    script.defer = true
    script.dataset.agentmeshTurnstile = 'true'
    script.addEventListener('load', renderWidget)
    document.head.appendChild(script)
    return () => script.removeEventListener('load', renderWidget)
  }, [onToken])
  if (!captchaSiteKey) return <div className="alert danger">Signup CAPTCHA is not configured.</div>
  return <div ref={container} className="captcha-container" aria-label="Signup verification" />
}

const credentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, 'Use at least eight characters.'),
})

type Credentials = z.infer<typeof credentialsSchema>

export function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const { register, handleSubmit, formState } = useForm<Credentials>({
    resolver: zodResolver(credentialsSchema),
  })

  if (auth.user) return <Navigate to="/dashboard" replace />

  const submit = handleSubmit(async (values) => {
    setError(null)
    try {
      if (mode === 'login') await auth.signIn(values.email, values.password)
      else await auth.signUp(values.email, values.password, captchaToken || undefined)
      navigate(mode === 'signup' && !auth.developmentMode ? '/verify' : '/dashboard')
    } catch (value) {
      setError(value instanceof Error ? value.message : 'Authentication failed.')
    }
  })

  return (
    <main className="auth-layout">
      <section className="auth-brand-panel">
        <div className="auth-brand-mark"><MeshMark size={32} /></div>
        <div className="auth-floating-dots" aria-hidden="true">
          <span /><span /><span /><span /><span /><span />
        </div>
        <p className="eyebrow">AgentMesh cloud</p>
        <h1>Every answer carries its evidence and its risk decision.</h1>
        <p>Configure an isolated support council for each product, publish approved knowledge, and integrate with one API key.</p>
        <ul>
          <li><CheckCircle2 size={16} /> Tenant-isolated knowledge</li>
          <li><CheckCircle2 size={16} /> Non-overridable safety controls</li>
          <li><CheckCircle2 size={16} /> 500 decisions included monthly</li>
        </ul>
      </section>
      <section className="auth-form-panel">
        <form className="auth-card" onSubmit={submit}>
          <p className="eyebrow">{mode === 'login' ? 'Welcome back' : 'Create your company'}</p>
          <h2>{mode === 'login' ? 'Sign in to AgentMesh' : 'Start building with AgentMesh'}</h2>
          <p>{auth.developmentMode ? 'Local authentication mode is active.' : 'Use a verified work email to continue.'}</p>
          {error && <div className="alert danger"><strong>Authentication failed</strong><p>{error}</p></div>}
          <label>
            <span>Work email</span>
            <input type="email" autoComplete="email" {...register('email')} />
            {formState.errors.email && <small>{formState.errors.email.message}</small>}
          </label>
          <label>
            <span>Password</span>
            <input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} {...register('password')} />
            {formState.errors.password && <small>{formState.errors.password.message}</small>}
          </label>
          {mode === 'signup' && !auth.developmentMode && <SignupCaptcha onToken={setCaptchaToken} />}
          <button className="button primary" disabled={formState.isSubmitting || (mode === 'signup' && !auth.developmentMode && !captchaToken)}>
            {formState.isSubmitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            <ArrowRight size={15} />
          </button>
          {!auth.developmentMode && (
            <button className="button secondary" type="button" onClick={() => void auth.signInWithGoogle()}>
              Continue with Google
            </button>
          )}
          <footer>
            {mode === 'login' ? (
              <><Link to="/forgot-password">Forgot password?</Link><span>New here? <Link to="/signup">Create an account</Link></span></>
            ) : (
              <span>Already registered? <Link to="/login">Sign in</Link></span>
            )}
          </footer>
        </form>
      </section>
    </main>
  )
}

export function ForgotPasswordPage() {
  const auth = useAuth()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  return (
    <main className="auth-layout compact">
      <section className="auth-form-panel">
        <form className="auth-card" onSubmit={async (event) => {
          event.preventDefault()
          setError(null)
          try {
            await auth.sendPasswordReset(email)
            setSent(true)
          } catch (value) {
            setError(value instanceof Error ? value.message : 'Reset request failed.')
          }
        }}>
          <p className="eyebrow">Account recovery</p>
          <h2>Reset your password</h2>
          {sent ? <div className="alert success"><strong>Check your email</strong><p>If an account exists, a recovery link has been sent.</p></div> : (
            <>
              {error && <div className="alert danger">{error}</div>}
              <label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
              <button className="button primary">Send recovery link</button>
            </>
          )}
          <footer><Link to="/login">Return to sign in</Link></footer>
        </form>
      </section>
    </main>
  )
}

export function VerifyPage() {
  return (
    <main className="auth-layout compact">
      <section className="auth-form-panel">
        <div className="auth-card">
          <p className="eyebrow">Identity check</p>
          <h2>Verify your email</h2>
          <p>Open the confirmation link sent to your inbox. Once verified, continue to company setup.</p>
          <Link className="button primary" to="/onboarding">Continue to onboarding <ArrowRight size={15} /></Link>
        </div>
      </section>
    </main>
  )
}
