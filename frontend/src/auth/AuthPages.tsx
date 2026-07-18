import React, { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { useAuth } from './AuthProvider'
import { MeshMark } from '../components/AppShell'
import { runtimeConfig } from '../runtime-config'
import { googleOAuthEnabled } from '../lib/supabase'
import { savePendingSignup } from './signup-details'

declare global {
  interface Window {
    turnstile?: {
      render(element: HTMLElement, options: {
        sitekey: string
        callback: (token: string) => void
        'error-callback': (errorCode: string) => boolean
        'expired-callback': () => void
        theme: 'light'
      }): string
      remove(widgetId: string): void
    }
  }
}

const captchaSiteKey = runtimeConfig(
  'VITE_TURNSTILE_SITE_KEY',
  import.meta.env.VITE_TURNSTILE_SITE_KEY,
)

export function turnstileErrorMessage(errorCode: string): string {
  if (errorCode === '110200') {
    return `Signup verification is not authorized for ${window.location.hostname}. Please contact support.`
  }
  if (errorCode.startsWith('110')) {
    return 'Signup verification is misconfigured. Please contact support.'
  }
  if (errorCode.startsWith('300') || errorCode.startsWith('600')) {
    return 'The security check failed. Refresh the page or try another browser.'
  }
  return 'The security check could not start. Refresh the page and try again.'
}

function SignupCaptcha({
  onToken,
  onError,
}: {
  onToken: (token: string | null) => void
  onError: (message: string | null) => void
}) {
  const container = React.useRef<HTMLDivElement>(null)
  React.useEffect(() => {
    if (!captchaSiteKey || !container.current) return
    const renderWidget = () => {
      if (!window.turnstile || !container.current || container.current.dataset.rendered) return
      try {
        const widgetId = window.turnstile.render(container.current, {
          sitekey: captchaSiteKey,
          callback: (token) => {
            onError(null)
            onToken(token)
          },
          'error-callback': (errorCode) => {
            onToken(null)
            onError(turnstileErrorMessage(errorCode))
            return true
          },
          'expired-callback': () => onToken(null),
          theme: 'light',
        })
        container.current.dataset.rendered = 'true'
        container.current.dataset.widgetId = widgetId
      } catch {
        onToken(null)
        onError('The security check could not start. Refresh the page and try again.')
      }
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
    const handleScriptError = () => {
      onError('The security check could not load. Check your connection and try again.')
    }
    script.addEventListener('error', handleScriptError)
    document.head.appendChild(script)
    return () => {
      script.removeEventListener('load', renderWidget)
      script.removeEventListener('error', handleScriptError)
    }
  }, [onError, onToken])
  if (!captchaSiteKey) return <div className="alert danger">Signup CAPTCHA is not configured.</div>
  return <div ref={container} className="captcha-container" aria-label="Signup verification" />
}

function credentialsSchema(mode: 'login' | 'signup') {
  return z.object({
    email: z.string().trim().email('Enter a valid work email.'),
    password: z.string().min(8, 'Use at least eight characters.'),
    confirmPassword: z.string().optional(),
    fullName: z.string().trim().optional(),
    companyName: z.string().trim().optional(),
    workspaceName: z.string().trim().optional(),
    template: z.enum(['GENERAL', 'FINANCE', 'HEALTHCARE', 'ECOMMERCE']).optional(),
    terms: z.boolean().optional(),
  }).superRefine((values, context) => {
    if (mode !== 'signup') return
    if (!values.fullName || values.fullName.length < 2) {
      context.addIssue({ code: 'custom', path: ['fullName'], message: 'Enter your full name.' })
    }
    if (!values.companyName || values.companyName.length < 2) {
      context.addIssue({ code: 'custom', path: ['companyName'], message: 'Enter your company name.' })
    }
    if (!values.workspaceName || values.workspaceName.length < 2) {
      context.addIssue({ code: 'custom', path: ['workspaceName'], message: 'Enter a workspace name.' })
    }
    if (values.confirmPassword !== values.password) {
      context.addIssue({ code: 'custom', path: ['confirmPassword'], message: 'Passwords do not match.' })
    }
    if (!values.terms) {
      context.addIssue({ code: 'custom', path: ['terms'], message: 'Accept the terms to continue.' })
    }
  })
}

type Credentials = z.infer<ReturnType<typeof credentialsSchema>>

export function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const [captchaError, setCaptchaError] = useState<string | null>(null)
  const { register, handleSubmit, formState } = useForm<Credentials>({
    resolver: zodResolver(credentialsSchema(mode)),
    defaultValues: {
      workspaceName: 'Support',
      template: 'GENERAL',
      terms: false,
    },
  })

  if (auth.user) return <Navigate to="/dashboard" replace />

  const submit = handleSubmit(async (values) => {
    setError(null)
    try {
      if (mode === 'login') await auth.signIn(values.email, values.password)
      else {
        const details = {
          fullName: values.fullName!,
          companyName: values.companyName!,
          workspaceName: values.workspaceName!,
          template: values.template || 'GENERAL',
        }
        await auth.signUp(values.email, values.password, details, captchaToken || undefined)
        savePendingSignup(details)
      }
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
        <form className={`auth-card ${mode === 'signup' ? 'signup-card' : ''}`} onSubmit={submit}>
          <p className="eyebrow">{mode === 'login' ? 'Welcome back' : 'Create your company'}</p>
          <h2>{mode === 'login' ? 'Sign in to AgentMesh' : 'Start building with AgentMesh'}</h2>
          <p>{auth.developmentMode ? 'Local authentication mode is active.' : mode === 'login' ? 'Use your verified work email to continue.' : 'Create your account and first isolated workspace in one step.'}</p>
          {error && <div className="alert danger"><strong>Authentication failed</strong><p>{error}</p></div>}
          {mode === 'signup' && (
            <div className="auth-signup-grid">
              <label>
                <span>Full name</span>
                <input autoComplete="name" {...register('fullName')} />
                {formState.errors.fullName && <small>{formState.errors.fullName.message}</small>}
              </label>
              <label>
                <span>Company name</span>
                <input autoComplete="organization" placeholder="Acme Support" {...register('companyName')} />
                {formState.errors.companyName && <small>{formState.errors.companyName.message}</small>}
              </label>
            </div>
          )}
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
          {mode === 'signup' && (
            <>
              <label>
                <span>Confirm password</span>
                <input type="password" autoComplete="new-password" {...register('confirmPassword')} />
                {formState.errors.confirmPassword && <small>{formState.errors.confirmPassword.message}</small>}
              </label>
              <div className="auth-signup-grid">
                <label>
                  <span>First workspace</span>
                  <input {...register('workspaceName')} />
                  {formState.errors.workspaceName && <small>{formState.errors.workspaceName.message}</small>}
                </label>
                <label>
                  <span>Support template</span>
                  <select {...register('template')}>
                    <option value="GENERAL">General support</option>
                    <option value="FINANCE">Financial support</option>
                    <option value="HEALTHCARE">Healthcare information</option>
                    <option value="ECOMMERCE">E-commerce support</option>
                  </select>
                </label>
              </div>
              <label className="auth-terms-check">
                <input type="checkbox" {...register('terms')} />
                <span>I agree to the <Link to="/terms">Terms</Link> and <Link to="/privacy">Privacy notice</Link>.</span>
              </label>
              {formState.errors.terms && <small className="field-error">{formState.errors.terms.message}</small>}
            </>
          )}
          {mode === 'signup' && !auth.developmentMode && (
            <>
              <SignupCaptcha onToken={setCaptchaToken} onError={setCaptchaError} />
              {captchaError && (
                <div className="alert danger">
                  <strong>Verification unavailable</strong><p>{captchaError}</p>
                </div>
              )}
            </>
          )}
          <button className="button primary" disabled={formState.isSubmitting || (mode === 'signup' && !auth.developmentMode && !captchaToken)}>
            {formState.isSubmitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
            <ArrowRight size={15} />
          </button>
          {mode === 'login' && !auth.developmentMode && googleOAuthEnabled && (
            <button className="button secondary" type="button" onClick={async () => {
              setError(null)
              try {
                await auth.signInWithGoogle()
              } catch (value) {
                setError(value instanceof Error ? value.message : 'Google sign-in failed.')
              }
            }}>
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

export function ResetPasswordPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  return (
    <main className="auth-layout compact">
      <section className="auth-form-panel">
        <form className="auth-card" onSubmit={async (event) => {
          event.preventDefault()
          setError(null)
          if (password.length < 8) {
            setError('Use at least eight characters.')
            return
          }
          if (password !== confirmation) {
            setError('Passwords do not match.')
            return
          }
          try {
            await auth.updatePassword(password)
            navigate('/dashboard', { replace: true })
          } catch (value) {
            setError(value instanceof Error ? value.message : 'Password update failed.')
          }
        }}>
          <p className="eyebrow">Account recovery</p>
          <h2>Choose a new password</h2>
          {!auth.loading && !auth.user && <div className="alert danger">Open this page from the recovery link in your email.</div>}
          {error && <div className="alert danger">{error}</div>}
          <label><span>New password</span><input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <label><span>Confirm password</span><input type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
          <button className="button primary" disabled={auth.loading || !auth.user}>Update password</button>
          <footer><Link to="/login">Return to sign in</Link></footer>
        </form>
      </section>
    </main>
  )
}

export function VerifyPage() {
  const auth = useAuth()
  return (
    <main className="auth-layout compact">
      <section className="auth-form-panel">
        <div className="auth-card">
          <p className="eyebrow">Identity check</p>
          <h2>Verify your email</h2>
          <p>Open the confirmation link sent to your inbox. After verification, your signup details will be ready for workspace creation.</p>
          <Link className="button primary" to={auth.user ? '/dashboard' : '/login'}>{auth.user ? 'Continue to workspace setup' : 'Sign in after verification'} <ArrowRight size={15} /></Link>
        </div>
      </section>
    </main>
  )
}
