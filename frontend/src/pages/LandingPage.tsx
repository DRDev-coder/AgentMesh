import React, { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Eye,
  MessageSquare,
  Shield,
  Sparkles,
  Zap,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { MeshMark } from '../components/AppShell'

/* ------------------------------------------------------------------ */
/*  Animated counter — fires once element scrolls into view           */
/* ------------------------------------------------------------------ */
function AnimatedCounter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const [value, setValue] = useState(0)
  const fired = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !fired.current) {
          fired.current = true
          const duration = 1600
          const start = performance.now()
          const step = (now: number) => {
            const progress = Math.min((now - start) / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setValue(Math.round(eased * target))
            if (progress < 1) requestAnimationFrame(step)
          }
          requestAnimationFrame(step)
        }
      },
      { threshold: 0.3 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [target])

  return <span ref={ref}>{value}{suffix}</span>
}

/* ------------------------------------------------------------------ */
/*  Hero floating mesh node animation                                 */
/* ------------------------------------------------------------------ */
function HeroMesh() {
  return (
    <svg className="hero-mesh-svg" viewBox="0 0 600 400" aria-hidden="true">
      {/* Grid lines */}
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={`h${i}`} x1="0" y1={i * 36} x2="600" y2={i * 36} stroke="#cfc8be" strokeWidth="0.5" />
      ))}
      {Array.from({ length: 18 }).map((_, i) => (
        <line key={`v${i}`} x1={i * 36} y1="0" x2={i * 36} y2="400" stroke="#cfc8be" strokeWidth="0.5" />
      ))}
      {/* Connections */}
      <line x1="300" y1="200" x2="120" y2="100" stroke="#ea3323" strokeWidth="1" opacity="0.35" className="hero-line hero-line-1" />
      <line x1="300" y1="200" x2="480" y2="100" stroke="#ea3323" strokeWidth="1" opacity="0.35" className="hero-line hero-line-2" />
      <line x1="300" y1="200" x2="120" y2="300" stroke="#ea3323" strokeWidth="1" opacity="0.35" className="hero-line hero-line-3" />
      <line x1="300" y1="200" x2="480" y2="300" stroke="#ea3323" strokeWidth="1" opacity="0.35" className="hero-line hero-line-4" />
      {/* Nodes */}
      <circle cx="120" cy="100" r="6" fill="#ea3323" opacity="0.7" className="hero-node hero-node-1" />
      <circle cx="480" cy="100" r="6" fill="#ea3323" opacity="0.7" className="hero-node hero-node-2" />
      <circle cx="120" cy="300" r="6" fill="#ea3323" opacity="0.7" className="hero-node hero-node-3" />
      <circle cx="480" cy="300" r="6" fill="#ea3323" opacity="0.7" className="hero-node hero-node-4" />
      {/* Center hub */}
      <rect x="290" y="190" width="20" height="20" fill="#ea3323" className="hero-hub" />
      {/* Labels */}
      <text x="120" y="82" textAnchor="middle" fill="#393734" fontSize="9" fontFamily="JetBrains Mono, monospace" fontWeight="700" letterSpacing="0.08em">SAGE</text>
      <text x="480" y="82" textAnchor="middle" fill="#393734" fontSize="9" fontFamily="JetBrains Mono, monospace" fontWeight="700" letterSpacing="0.08em">GUARDIAN</text>
      <text x="120" y="324" textAnchor="middle" fill="#393734" fontSize="9" fontFamily="JetBrains Mono, monospace" fontWeight="700" letterSpacing="0.08em">EMPATH</text>
      <text x="480" y="324" textAnchor="middle" fill="#393734" fontSize="9" fontFamily="JetBrains Mono, monospace" fontWeight="700" letterSpacing="0.08em">ORACLE</text>
      <text x="300" y="230" textAnchor="middle" fill="#ea3323" fontSize="8" fontFamily="JetBrains Mono, monospace" fontWeight="700" letterSpacing="0.1em">CONSENSUS</text>
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/*  Agent feature cards                                               */
/* ------------------------------------------------------------------ */
const AGENTS = [
  {
    name: 'SAGE',
    tagline: 'Knowledge retrieval',
    description: 'Retrieves approved workspace knowledge and drafts evidence-grounded support answers.',
    icon: BookOpen,
    accent: '#3b82f6',
  },
  {
    name: 'GUARDIAN',
    tagline: 'Security enforcement',
    description: 'Applies non-overridable safety rules for credentials, prompt injection, phishing, and unsafe actions.',
    icon: Shield,
    accent: '#ea3323',
  },
  {
    name: 'EMPATH',
    tagline: 'Emotional intelligence',
    description: 'Detects urgency and frustration so safe answers can use the right tone or move to review.',
    icon: Sparkles,
    accent: '#a855f7',
  },
  {
    name: 'ORACLE',
    tagline: 'Evidence verification',
    description: 'Checks material draft claims against the exact retrieved evidence before approval.',
    icon: Eye,
    accent: '#f59e0b',
  },
]

const STEPS = [
  { number: '01', title: 'Submit query', description: 'A customer or API sends a support question to your AgentMesh endpoint.' },
  { number: '02', title: 'Pipeline reviews', description: 'AgentMesh retrieves evidence, drafts an answer, checks safety, verifies claims, and reads customer urgency.' },
  { number: '03', title: 'Decision returned', description: 'The deterministic policy approves, rewrites, blocks, asks for clarification, or escalates with a trace.' },
]

/* ------------------------------------------------------------------ */
/*  Landing Page                                                      */
/* ------------------------------------------------------------------ */
export default function LandingPage() {
  return (
    <div className="landing">
      {/* ── Navigation bar ── */}
      <nav className="landing-nav" aria-label="Marketing navigation">
        <div className="landing-nav-inner">
          <Link to="/" className="landing-brand" aria-label="AgentMesh home">
            <MeshMark size={24} />
            <span>AgentMesh</span>
          </Link>
          <div className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <Link to="/docs">API docs</Link>
            <Link to="/company">Company</Link>
          </div>
          <div className="landing-nav-actions">
            <Link to="/login" className="button secondary small">Sign in</Link>
            <Link to="/signup" className="button primary small">Get started free <ArrowRight size={14} /></Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <p className="eyebrow">Decision infrastructure for support teams</p>
          <h1>Every answer carries its evidence and its risk decision.</h1>
          <p className="landing-hero-subtitle">
            Four specialist checks run on every customer query, enforcing safety controls, grounding answers in your knowledge base, and returning a decision you can inspect.
          </p>
          <div className="landing-hero-actions">
            <Link to="/signup" className="button primary">
              Start building free <ArrowRight size={15} />
            </Link>
            <Link to="/login" className="button secondary">
              Sign in to dashboard <ChevronRight size={15} />
            </Link>
          </div>
          <ul className="landing-hero-checks">
            <li><CheckCircle2 size={14} /> 500 decisions included monthly</li>
            <li><CheckCircle2 size={14} /> No credit card required</li>
            <li><CheckCircle2 size={14} /> Test playground included</li>
          </ul>
        </div>
        <div className="landing-hero-visual">
          <HeroMesh />
        </div>
      </section>

      {/* ── Trusted by ── */}
      <section className="landing-trusted">
        <p className="eyebrow">Trusted by forward-thinking teams</p>
        <div className="landing-trusted-logos">
          {['FinStack', 'NeoBank', 'VaultPay', 'CreditFlow', 'PayGrid', 'LedgerAI'].map((name) => (
            <span key={name} className="landing-logo-placeholder">{name}</span>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="landing-features" id="features">
        <div className="landing-section-header">
          <p className="eyebrow">The agent council</p>
          <h2>Four specialists. One verified answer.</h2>
          <p>Each query passes through retrieval, safety, evidence, and tone checks before the decision policy approves the final response.</p>
        </div>
        <div className="landing-features-grid">
          {AGENTS.map((agent) => {
            const Icon = agent.icon
            return (
              <article key={agent.name} className="landing-feature-card">
                <div className="landing-feature-icon" style={{ '--agent-accent': agent.accent } as React.CSSProperties}>
                  <Icon size={20} />
                </div>
                <div className="landing-feature-meta">
                  <span className="eyebrow">{agent.tagline}</span>
                  <h3>{agent.name}</h3>
                </div>
                <p>{agent.description}</p>
              </article>
            )
          })}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="landing-how" id="how-it-works">
        <div className="landing-section-header">
          <p className="eyebrow">How it works</p>
          <h2>From query to verified answer in under two seconds.</h2>
        </div>
        <div className="landing-steps">
          {STEPS.map((step, index) => (
            <React.Fragment key={step.number}>
              {index > 0 && <div className="landing-step-connector" aria-hidden="true" />}
              <article className="landing-step">
                <span className="landing-step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            </React.Fragment>
          ))}
        </div>
      </section>

      {/* ── Metrics / Social proof ── */}
      <section className="landing-metrics" id="metrics">
        <div className="landing-section-header">
          <p className="eyebrow">Why AgentMesh</p>
          <h2>Built for high-stakes customer support.</h2>
        </div>
        <div className="landing-metrics-grid">
          <article>
            <strong><AnimatedCounter target={4} /></strong>
            <span>AI agents per query</span>
          </article>
          <article>
            <strong>&lt; <AnimatedCounter target={2} />s</strong>
            <span>Average response time</span>
          </article>
          <article>
            <strong><AnimatedCounter target={500} suffix="+" /></strong>
            <span>Decisions included monthly</span>
          </article>
          <article>
            <strong><AnimatedCounter target={99} suffix="%" /></strong>
            <span>Safety rule enforcement</span>
          </article>
        </div>
      </section>

      {/* ── Integration highlight ── */}
      <section className="landing-integration">
        <div className="landing-integration-content">
          <p className="eyebrow">Developer-first</p>
          <h2>One API key. Full council access.</h2>
          <p>Integrate AgentMesh into your existing support stack with a single API call. Every response includes the evidence trail, agent findings, citations, decision state, and usage unit.</p>
          <div className="landing-code-block">
            <code>
              <span className="code-keyword">curl</span> -X POST https://api.agentmesh.dev/api/v1/decisions \{'\n'}
              {'  '}-H <span className="code-string">"Authorization: Bearer am_live_public.secret"</span> \{'\n'}
              {'  '}-H <span className="code-string">"Idempotency-Key: request-001"</span> \{'\n'}
              {'  '}-d <span className="code-string">'{`{"input": "How do I dispute a charge?"}`}'</span>
            </code>
          </div>
          <Link to="/signup" className="button primary">
            Get your API key <ArrowRight size={15} />
          </Link>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="landing-cta">
        <div className="landing-cta-inner">
          <h2>Ready to build trustworthy support?</h2>
          <p>Start with 500 free decisions per month. No credit card required.</p>
          <div className="landing-cta-actions">
            <Link to="/signup" className="button primary">
              Create free account <ArrowRight size={15} />
            </Link>
            <Link to="/login" className="button secondary">
              Sign in <ChevronRight size={15} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">
            <div className="landing-brand">
              <MeshMark size={22} />
              <span>AgentMesh</span>
            </div>
            <p>AI-powered decision infrastructure for customer support teams.</p>
          </div>
          <div className="landing-footer-links">
            <div>
              <h4>Product</h4>
              <ul>
                <li><a href="#features">Features</a></li>
                <li><a href="#how-it-works">How it works</a></li>
                <li><a href="#metrics">Why AgentMesh</a></li>
              </ul>
            </div>
            <div>
              <h4>Developers</h4>
              <ul>
                <li><Link to="/docs">API documentation</Link></li>
                <li><Link to="/developers#sdks">SDK & libraries</Link></li>
                <li><Link to="/developers#changelog">Changelog</Link></li>
              </ul>
            </div>
            <div>
              <h4>Company</h4>
              <ul>
                <li><Link to="/company">About</Link></li>
                <li><Link to="/company#blog">Blog</Link></li>
                <li><Link to="/company#careers">Careers</Link></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="landing-footer-bottom">
          <span>© {new Date().getFullYear()} AgentMesh. All rights reserved.</span>
          <div>
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
