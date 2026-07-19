import React from 'react'
import { ArrowLeft, ArrowRight, BookOpen, Braces, Building2, CheckCircle2, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { MeshMark } from '../components/AppShell'
import { API_BASE_URL } from '../lib/saas-api'

function PublicPageLayout({
  eyebrow,
  title,
  intro,
  children,
}: {
  eyebrow: string
  title: string
  intro: string
  children: React.ReactNode
}) {
  return (
    <div className="public-page">
      <nav className="public-nav">
        <Link to="/" className="landing-brand"><MeshMark size={24} /><span>AgentMesh</span></Link>
        <div>
          <Link to="/docs">API docs</Link>
          <Link to="/developers">Developers</Link>
          <Link to="/company">Company</Link>
        </div>
        <div className="landing-nav-actions">
          <Link to="/login" className="button secondary small">Sign in</Link>
          <Link to="/signup" className="button primary small">Get started <ArrowRight size={14} /></Link>
        </div>
      </nav>
      <main className="public-main">
        <Link to="/" className="public-back"><ArrowLeft size={14} /> Back to home</Link>
        <header className="public-hero">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{intro}</p>
        </header>
        {children}
      </main>
      <footer className="public-footer">
        <span>&copy; {new Date().getFullYear()} AgentMesh</span>
        <div><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link></div>
      </footer>
    </div>
  )
}

export function ApiDocumentationPage() {
  return (
    <PublicPageLayout
      eyebrow="Public API documentation"
      title="Build evidence-grounded support decisions."
      intro="The decision API accepts a customer question and returns the final decision state, citations, agent findings, release identifiers, and usage information. Reading these docs does not require an account."
    >
      <section className="public-card-grid">
        <article><Braces size={20} /><h2>One endpoint</h2><p>Send production traffic to <code>POST /api/v1/decisions</code> with a workspace API key.</p></article>
        <article><ShieldCheck size={20} /><h2>Safe retries</h2><p>Every request requires an idempotency key so an identical retry returns the original decision without charging another usage unit.</p></article>
        <article><BookOpen size={20} /><h2>Exact evidence</h2><p>Approved answers include citations tied to the exact published knowledge and configuration releases used by the council.</p></article>
      </section>
      <section className="public-content-section">
        <p className="eyebrow">Request example</p>
        <h2>Submit a decision</h2>
        <pre><code>{`curl -X POST "${API_BASE_URL}/decisions" \\
  -H "Authorization: Bearer am_live_<public-id>.<secret>" \\
  -H "Idempotency-Key: your-unique-request-id" \\
  -H "Content-Type: application/json" \\
  -d '{"input":"What is the return policy?","metadata":{}}'`}</code></pre>
        <div className="public-note"><strong>Authentication</strong><p>Dashboard sessions use Supabase. Customer decision requests use one-time-reveal AgentMesh test or live API keys created inside a workspace.</p></div>
      </section>
      <section className="public-content-section">
        <p className="eyebrow">Decision states</p>
        <h2>Deterministic outcomes</h2>
        <ul className="public-check-list">
          {['APPROVED — evidence and safety checks passed', 'NEEDS_CLARIFICATION — the request lacks required detail', 'ESCALATED — a human reviewer must decide', 'BLOCKED — the request violates a mandatory safety control', 'SYSTEM_UNAVAILABLE — a required dependency failed and usage is not billed'].map((item) => <li key={item}><CheckCircle2 size={15} />{item}</li>)}
        </ul>
        <p><a href={`${API_BASE_URL.replace(/\/api\/v1$/, '')}/docs`} target="_blank" rel="noreferrer">Open the live OpenAPI explorer</a></p>
      </section>
    </PublicPageLayout>
  )
}

export function DevelopersPublicPage() {
  return (
    <PublicPageLayout eyebrow="Developers" title="Integrate without guessing." intro="Use the public contract to understand AgentMesh before creating an account. Workspace credentials and live data remain protected behind authentication.">
      <section className="public-card-grid">
        <article><BookOpen size={20} /><h2>API reference</h2><p>Review authentication, request fields, decision states, errors, idempotency, and usage behavior.</p><Link to="/docs">Read API docs <ArrowRight size={13} /></Link></article>
        <article id="sdks"><Braces size={20} /><h2>SDKs and types</h2><p>The API is OpenAPI-based. Generate a client for Python, TypeScript, Java, Go, or your preferred supported language.</p></article>
        <article><ShieldCheck size={20} /><h2>Webhook safety</h2><p>Customer webhooks are timestamped and HMAC-signed. Verify the raw body before accepting an event.</p></article>
      </section>
      <section className="public-content-section" id="changelog">
        <p className="eyebrow">Changelog</p><h2>Current public release</h2>
        <p><strong>v3 staging</strong> — Supabase authentication, tenant-isolated workspaces, evidence releases, deterministic decisions, human review, Resend email, and Razorpay subscription plumbing.</p>
        <p>Breaking contract changes will be versioned before production launch.</p>
      </section>
    </PublicPageLayout>
  )
}

export function CompanyPage() {
  return (
    <PublicPageLayout eyebrow="Company" title="Trust infrastructure for support teams." intro="AgentMesh is built around a simple idea: customer-facing AI should show its evidence, enforce non-overridable safety controls, and know when a person must take over.">
      <section className="public-card-grid">
        <article><Building2 size={20} /><h2>About</h2><p>AgentMesh is an early-stage product focused on English-language informational customer support and inspectable decision workflows.</p></article>
        <article id="blog"><BookOpen size={20} /><h2>Engineering notes</h2><p>Product and engineering notes will document evaluation results, safety boundaries, and release changes as the platform matures.</p></article>
        <article id="careers"><Braces size={20} /><h2>Careers</h2><p>There are no open roles published at this time. Future openings will be listed here rather than hidden behind account creation.</p></article>
      </section>
      <section className="public-content-section"><p className="eyebrow">Scope</p><h2>What AgentMesh is not</h2><p>The public MVP is not intended for patient records, payment-card data, bank credentials, authentication secrets, regulated financial or medical decisions, or arbitrary executable rules.</p></section>
    </PublicPageLayout>
  )
}

export function LegalPage({ kind }: { kind: 'privacy' | 'terms' }) {
  const privacy = kind === 'privacy'
  return (
    <PublicPageLayout eyebrow={privacy ? 'Privacy notice' : 'Terms'} title={privacy ? 'Data handling at a glance.' : 'Responsible evaluation terms.'} intro={privacy ? 'This staging notice explains the product’s current data boundaries. A reviewed production policy will replace it before commercial launch.' : 'These staging terms describe acceptable evaluation use. Reviewed commercial terms will replace them before a production launch.'}>
      <section className="public-content-section legal-copy">
        {privacy ? (
          <><h2>Current staging practices</h2><p>Account identity is handled by Supabase. AgentMesh stores organization, workspace, decision, audit, and usage records in tenant-isolated PostgreSQL tables. Transactional application email is sent through Resend.</p><p>Do not upload patient records, card data, bank credentials, authentication secrets, or other regulated or highly sensitive information. Uploaded staging files and queue state may be ephemeral.</p><p>Raw support content is designed for bounded retention; audit and billing metadata may remain longer for integrity and reconciliation.</p></>
        ) : (
          <><h2>Acceptable use</h2><p>Use this staging service only for lawful testing with non-sensitive data. Do not use it to make regulated medical, financial, employment, housing, or eligibility decisions.</p><p>You are responsible for reviewing generated output before relying on it. Do not attempt to bypass tenant isolation, safety controls, rate limits, or access restrictions.</p><p>The staging service may change, scale down, or lose replica-local files and queue state without notice.</p></>
        )}
      </section>
    </PublicPageLayout>
  )
}
