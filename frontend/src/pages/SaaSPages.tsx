import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Check,
  Clipboard,
  Code2,
  Copy,
  CreditCard,
  FileText,
  KeyRound,
  LockKeyhole,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Trash2,
  Upload,
  Users,
} from 'lucide-react'
import { useOutletContext } from 'react-router-dom'
import type { WorkspaceRouteContext } from '../components/SaaSShell'
import {
  SaaSApiError,
  saasRequest,
  type ApiKeyRecord,
  type DecisionRecord,
  type DocumentRecord,
  type ReviewRecord,
  type UsageSummary,
} from '../lib/saas-api'

function useWorkspace() {
  return useOutletContext<WorkspaceRouteContext>()
}

function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <div className="alert danger">
      <strong>{error instanceof SaaSApiError ? error.code.replaceAll('_', ' ') : 'Request failed'}</strong>
      <p>{error instanceof Error ? error.message : 'An unexpected error occurred.'}</p>
    </div>
  )
}

function Empty({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="empty-state compact"><h2>{title}</h2><p>{children}</p></div>
}

export function OverviewPage() {
  const { organization, workspace, basePath } = useWorkspace()
  const usage = useQuery({
    queryKey: ['usage', organization.id],
    queryFn: () => saasRequest<UsageSummary>(`/organizations/${organization.id}/usage`),
  })
  const decisions = useQuery({
    queryKey: ['decisions', workspace.id],
    queryFn: () => saasRequest<DecisionRecord[]>(`/organizations/${organization.id}/workspaces/${workspace.id}/decisions?limit=8`),
  })
  const documents = useQuery({
    queryKey: ['documents', workspace.id],
    queryFn: () => saasRequest<DocumentRecord[]>(`/organizations/${organization.id}/workspaces/${workspace.id}/documents`),
  })
  return (
    <div className="saas-page overview-page">
      <ErrorNotice error={usage.error || decisions.error || documents.error} />
      <section className="metric-grid">
        <article><span>Completed this month</span><strong>{usage.data?.completed_decisions ?? '—'}</strong><small>{usage.data?.period || 'Current period'}</small></article>
        <article><span>Free decisions remaining</span><strong>{usage.data?.remaining_free_decisions ?? '—'}</strong><small>of {usage.data?.included_decisions ?? 500} included</small></article>
        <article><span>Published documents</span><strong>{documents.data?.filter((item) => item.status === 'PUBLISHED').length ?? '—'}</strong><small>{documents.data?.length ?? 0} total documents</small></article>
        <article><span>Billing state</span><strong className="metric-word">{usage.data?.billing_status || 'FREE'}</strong><small>{usage.data?.payment_method_present ? 'Payment method active' : 'Free allowance only'}</small></article>
      </section>
      <section className="dashboard-grid">
        <article className="panel-card">
          <header><div><p className="eyebrow">Recent records</p><h2>Latest decisions</h2></div><a href={`${basePath}/decisions`}>View all <ArrowRight size={14} /></a></header>
          {!decisions.data?.length ? <Empty title="No decisions yet">Use the playground or API to create the first evidence record.</Empty> : (
            <div className="record-list">
              {decisions.data.map((item) => <div key={item.id}><span className={`decision-badge ${item.state === 'APPROVED' ? 'success' : 'warning'}`}>{item.state}</span><div><strong>{item.reason}</strong><small>{new Date(item.created_at).toLocaleString()} · {item.environment}</small></div><code>{item.id.slice(0, 8)}</code></div>)}
            </div>
          )}
        </article>
        <article className="panel-card readiness-card">
          <header><div><p className="eyebrow">Launch checklist</p><h2>Workspace readiness</h2></div></header>
          <ul>
            <li className={documents.data?.length ? 'complete' : ''}><span>{documents.data?.length ? <Check size={14} /> : '01'}</span><div><strong>Upload approved knowledge</strong><small>Keep customer data and secrets out.</small></div></li>
            <li className={workspace.active_knowledge_release_id ? 'complete' : ''}><span>{workspace.active_knowledge_release_id ? <Check size={14} /> : '02'}</span><div><strong>Publish a release</strong><small>Live keys only read published evidence.</small></div></li>
            <li><span>03</span><div><strong>Run an integration test</strong><small>Verify the answer, trace, and billing unit.</small></div></li>
          </ul>
        </article>
      </section>
    </div>
  )
}

export function KnowledgePage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [versionTarget, setVersionTarget] = useState('new')
  const [previewId, setPreviewId] = useState<string | null>(null)
  const documents = useQuery({
    queryKey: ['documents', context.workspace.id],
    queryFn: () => saasRequest<DocumentRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/documents`),
    refetchInterval: (query) => {
      const data = query.state.data as DocumentRecord[] | undefined
      return data?.some((item) => item.status === 'PROCESSING') ? 1000 : false
    },
  })
  const releases = useQuery({
    queryKey: ['knowledge-releases', context.workspace.id],
    queryFn: () => saasRequest<Array<{ id: string; version: number; document_version_ids: string[]; published_at: string }>>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/knowledge-releases`),
  })
  const preview = useQuery({
    queryKey: ['document-preview', previewId],
    queryFn: () => saasRequest<{ version: number; chunks: Array<{ chunk_index: number; page_number: number | null; text: string }> }>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/documents/${previewId}/preview`),
    enabled: Boolean(previewId),
  })
  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Choose a document first.')
      const form = new FormData()
      form.append('file', file)
      const suffix = versionTarget === 'new' ? '' : `/${versionTarget}/versions`
      return saasRequest<DocumentRecord>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/documents${suffix}`, { method: 'POST', body: form })
    },
    onSuccess: async () => {
      setFile(null)
      setVersionTarget('new')
      await queryClient.invalidateQueries({ queryKey: ['documents', context.workspace.id] })
    },
  })
  const publish = useMutation({
    mutationFn: () => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/knowledge-releases`, { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['documents', context.workspace.id] })
      await queryClient.invalidateQueries({ queryKey: ['workspaces', context.organization.id] })
      await queryClient.invalidateQueries({ queryKey: ['knowledge-releases', context.workspace.id] })
    },
  })
  const archive = useMutation({
    mutationFn: (id: string) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/documents/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents', context.workspace.id] }),
  })
  const activate = useMutation({
    mutationFn: (id: string) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/knowledge-releases/${id}/activate`, { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['knowledge-releases', context.workspace.id] })
      await queryClient.invalidateQueries({ queryKey: ['workspaces', context.organization.id] })
    },
  })
  const hasProcessingDocuments = documents.data?.some((item) => item.status === 'PROCESSING') ?? false
  const hasPublishableDocuments = documents.data?.some((item) => ['READY_FOR_REVIEW', 'PUBLISHED'].includes(item.status)) ?? false
  return (
    <div className="saas-page knowledge-page">
      <ErrorNotice error={documents.error || releases.error || preview.error || upload.error || publish.error || archive.error || activate.error} />
      <section className="upload-panel">
        <div><p className="eyebrow">Private source storage</p><h2>Add approved knowledge</h2><p>PDF, DOCX, TXT, or Markdown · 25 MB maximum · OCR is not supported.</p></div>
        <label><span>Upload target</span><select value={versionTarget} onChange={(event) => setVersionTarget(event.target.value)}><option value="new">New document</option>{documents.data?.map((item) => <option value={item.id} key={item.id}>New version of {item.name}</option>)}</select></label>
        <label className="file-picker"><Upload size={18} /><span>{file?.name || 'Choose a document'}</span><input type="file" accept=".pdf,.docx,.txt,.md" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
        <button className="button primary" disabled={!file || upload.isPending} onClick={() => upload.mutate()}>{upload.isPending ? 'Processing…' : 'Upload document'}</button>
      </section>
      <section className="panel-card">
        <header><div><p className="eyebrow">Knowledge inventory</p><h2>Documents</h2></div><button className="button primary small" disabled={!hasPublishableDocuments || hasProcessingDocuments || publish.isPending} onClick={() => publish.mutate()}><ShieldCheck size={14} />{hasProcessingDocuments ? 'Processing…' : publish.isPending ? 'Publishing…' : 'Publish release'}</button></header>
        {hasProcessingDocuments && <div className="policy-warning compact"><RefreshCw size={17} className="spin" /><div><strong>Document processing is running.</strong><p>AgentMesh is extracting evidence now. This page refreshes automatically until the file is ready to publish.</p></div></div>}
        {!documents.data?.length ? <Empty title="No workspace documents">Upload approved policies or product documentation to begin.</Empty> : (
          <div className="resource-table-wrap"><table className="resource-table"><thead><tr><th>Document</th><th>Status</th><th>Size</th><th>Version</th><th>Updated</th><th /></tr></thead><tbody>{documents.data.map((item) => <tr key={item.id}><td><div className="resource-name"><FileText size={16} /><span><strong>{item.name}</strong><small>{item.filename}</small></span></div></td><td><span className={`state-pill ${item.status.toLowerCase()}`}>{item.status.replaceAll('_', ' ')}</span>{item.extraction_error && <small className="field-error">{item.extraction_error}</small>}</td><td>{item.byte_size ? `${(item.byte_size / 1024).toFixed(1)} KB` : '—'}</td><td>v{item.current_version}</td><td>{new Date(item.updated_at).toLocaleDateString()}</td><td><div className="table-actions"><button className="icon-button quiet" aria-label={`Preview ${item.name}`} onClick={() => setPreviewId(item.id)}><BookOpen size={15} /></button><button className="icon-button quiet" aria-label="Archive document" onClick={() => archive.mutate(item.id)}><Trash2 size={15} /></button></div></td></tr>)}</tbody></table></div>
        )}
      </section>
      {previewId && <section className="panel-card"><header><div><p className="eyebrow">Extracted provenance</p><h2>Version {preview.data?.version ?? ''} preview</h2></div><button className="button secondary small" onClick={() => setPreviewId(null)}>Close</button></header>{preview.isLoading ? <p>Loading extracted text…</p> : !preview.data?.chunks.length ? <Empty title="No extracted text">Processing may still be running.</Empty> : <div className="preview-chunks">{preview.data.chunks.map((chunk) => <article key={chunk.chunk_index}><small>Chunk {chunk.chunk_index + 1}{chunk.page_number ? ` · page ${chunk.page_number}` : ''}</small><p>{chunk.text}</p></article>)}</div>}</section>}
      <section className="panel-card"><header><div><p className="eyebrow">Atomic history</p><h2>Knowledge releases</h2></div></header>{!releases.data?.length ? <Empty title="No releases">Publish reviewed documents to create the first immutable release.</Empty> : <div className="version-list">{releases.data.map((release) => <div key={release.id}><span className="version-number">v{release.version}</span><div><strong>{release.document_version_ids.length} document versions</strong><small>{new Date(release.published_at).toLocaleString()}</small></div>{context.workspace.active_knowledge_release_id === release.id ? <span className="state-pill published">ACTIVE</span> : <button className="button secondary small" disabled={activate.isPending} onClick={() => activate.mutate(release.id)}>Activate rollback</button>}</div>)}</div>}</section>
      <div className="policy-warning"><AlertTriangle size={18} /><div><strong>Regulated sensitive data is excluded from this MVP.</strong><p>Do not upload PHI, payment-card data, credentials, authentication secrets, or private banking records.</p></div></div>
    </div>
  )
}

interface Profile {
  id: string
  version: number
  status: string
  template_key: string
  tone: string
  response_length: string
  custom_instructions: string
  supported_topics: string[]
  enabled_rule_packs: string[]
  escalation_threshold: number
  published_at: string | null
}

export function ConfigurationPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const profiles = useQuery({
    queryKey: ['profiles', context.workspace.id],
    queryFn: () => saasRequest<Profile[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/profiles`),
  })
  const current = profiles.data?.[0]
  const [draft, setDraft] = useState({ template_key: context.workspace.industry_template, tone: 'PROFESSIONAL', response_length: 'CONCISE', custom_instructions: '', supported_topics: '', escalation_threshold: 7 })
  const create = useMutation({
    mutationFn: () => saasRequest<Profile>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/profiles`, {
      method: 'POST',
      body: {
        ...draft,
        supported_topics: draft.supported_topics.split(',').map((item) => item.trim()).filter(Boolean),
        enabled_rule_packs: draft.template_key === 'GENERAL' ? [] : [draft.template_key === 'HEALTHCARE' ? 'HEALTHCARE_INFORMATION' : `${draft.template_key}_SUPPORT`],
      },
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profiles', context.workspace.id] }),
  })
  const publish = useMutation({
    mutationFn: (id: string) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/profiles/${id}/publish`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profiles', context.workspace.id] }),
  })
  return (
    <div className="saas-page configuration-page">
      <ErrorNotice error={profiles.error || create.error || publish.error} />
      <div className="configuration-grid">
        <section className="panel-card configuration-form">
          <header><div><p className="eyebrow">Guided controls</p><h2>Create profile draft</h2></div></header>
          <div className="form-grid">
            <label><span>Industry template</span><select value={draft.template_key} onChange={(event) => setDraft({ ...draft, template_key: event.target.value })}><option>GENERAL</option><option>FINANCE</option><option>HEALTHCARE</option><option>ECOMMERCE</option></select></label>
            <label><span>Default tone</span><select value={draft.tone} onChange={(event) => setDraft({ ...draft, tone: event.target.value })}><option>PROFESSIONAL</option><option>FRIENDLY</option><option>PATIENT</option><option>EMPATHETIC</option></select></label>
            <label><span>Response length</span><select value={draft.response_length} onChange={(event) => setDraft({ ...draft, response_length: event.target.value })}><option>CONCISE</option><option>BALANCED</option><option>DETAILED</option></select></label>
            <label><span>Escalation threshold</span><input type="number" min={1} max={10} value={draft.escalation_threshold} onChange={(event) => setDraft({ ...draft, escalation_threshold: Number(event.target.value) })} /></label>
            <label className="full"><span>Supported topics</span><input value={draft.supported_topics} onChange={(event) => setDraft({ ...draft, supported_topics: event.target.value })} placeholder="returns, shipping, warranties" /><small>Comma-separated, informational labels.</small></label>
            <label className="full"><span>Approved instructions</span><textarea rows={6} value={draft.custom_instructions} onChange={(event) => setDraft({ ...draft, custom_instructions: event.target.value })} maxLength={2000} placeholder="Describe approved response behavior. Safety controls cannot be overridden." /></label>
          </div>
          <button className="button primary" disabled={create.isPending} onClick={() => create.mutate()}>{create.isPending ? 'Saving…' : 'Save draft'}</button>
        </section>
        <aside className="panel-card guardrail-card">
          <LockKeyhole size={22} />
          <p className="eyebrow">Non-overridable</p><h2>Platform safeguards</h2>
          <p>Prompt-injection, credential, unsafe-action, and secret-exposure controls always run before approval.</p>
          <ul><li><Check size={14} /> Global safety pack</li><li><Check size={14} /> Evidence verification</li><li><Check size={14} /> Fail-closed precedence</li><li><Check size={14} /> Edited-answer revalidation</li></ul>
        </aside>
      </div>
      <section className="panel-card"><header><div><p className="eyebrow">Immutable history</p><h2>Profile versions</h2></div></header>{!profiles.data?.length ? <Empty title="No profiles">Create the first guided profile.</Empty> : <div className="version-list">{profiles.data.map((profile) => <div key={profile.id}><span className="version-number">v{profile.version}</span><div><strong>{profile.template_key} · {profile.tone}</strong><small>{profile.enabled_rule_packs.join(', ')}</small></div><span className={`state-pill ${profile.status.toLowerCase()}`}>{profile.status}</span>{profile.status === 'DRAFT' && <button className="button secondary small" onClick={() => publish.mutate(profile.id)}>Publish</button>}</div>)}</div>}</section>
    </div>
  )
}

interface WebhookRecord { id: string; url: string; event_types: string[]; status: string; created_at: string; signing_secret?: string }
interface WebhookDeliveryRecord { id: string; endpoint_id: string; event_type: string; status: string; attempts: number; response_status: number | null; created_at: string }

export function DevelopersPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [name, setName] = useState('Integration key')
  const [environment, setEnvironment] = useState<'test' | 'live'>('test')
  const [revealed, setRevealed] = useState<string | null>(null)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookSecret, setWebhookSecret] = useState<string | null>(null)
  const keys = useQuery({
    queryKey: ['api-keys', context.workspace.id],
    queryFn: () => saasRequest<ApiKeyRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/api-keys`),
  })
  const webhooks = useQuery({ queryKey: ['webhooks', context.workspace.id], queryFn: () => saasRequest<WebhookRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/webhooks`) })
  const deliveries = useQuery({ queryKey: ['webhook-deliveries', context.workspace.id], queryFn: () => saasRequest<WebhookDeliveryRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/webhook-deliveries`) })
  const create = useMutation({
    mutationFn: () => saasRequest<ApiKeyRecord>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/api-keys`, { method: 'POST', body: { name, environment, scopes: ['decisions:write', 'decisions:read', 'traces:read'] } }),
    onSuccess: async (value) => {
      if (value.secret) {
        setRevealed(value.secret)
        sessionStorage.setItem(`agentmesh.key.${context.workspace.id}`, value.secret)
      }
      await queryClient.invalidateQueries({ queryKey: ['api-keys', context.workspace.id] })
    },
  })
  const revoke = useMutation({
    mutationFn: (id: string) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/api-keys/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['api-keys', context.workspace.id] }),
  })
  const createWebhook = useMutation({ mutationFn: () => saasRequest<WebhookRecord>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/webhooks`, { method: 'POST', body: { url: webhookUrl, event_types: ['escalation.created', 'escalation.updated', 'escalation.resolved'] } }), onSuccess: async (value) => { setWebhookSecret(value.signing_secret || null); setWebhookUrl(''); await queryClient.invalidateQueries({ queryKey: ['webhooks', context.workspace.id] }) } })
  const disableWebhook = useMutation({ mutationFn: (id: string) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/webhooks/${id}`, { method: 'DELETE' }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['webhooks', context.workspace.id] }) })
  return (
    <div className="saas-page developers-page">
      <ErrorNotice error={keys.error || webhooks.error || deliveries.error || create.error || revoke.error || createWebhook.error || disableWebhook.error} />
      {revealed && <section className="secret-banner"><KeyRound size={20} /><div><strong>Copy this key now—it will not be shown again.</strong><code>{revealed}</code></div><button className="icon-button" onClick={() => void navigator.clipboard.writeText(revealed)}><Copy size={16} /></button></section>}
      <section className="panel-card key-create"><header><div><p className="eyebrow">Credentials</p><h2>Create API key</h2></div></header><div className="inline-form"><label><span>Name</span><input value={name} onChange={(event) => setName(event.target.value)} /></label><label><span>Environment</span><select value={environment} onChange={(event) => setEnvironment(event.target.value as 'test' | 'live')}><option value="test">Test</option><option value="live">Live</option></select></label><button className="button primary" disabled={create.isPending} onClick={() => create.mutate()}><Plus size={14} />Create key</button></div></section>
      <section className="panel-card"><header><div><p className="eyebrow">Workspace secrets</p><h2>API keys</h2></div></header>{!keys.data?.length ? <Empty title="No API keys">Create a test key to use the playground.</Empty> : <div className="resource-table-wrap"><table className="resource-table"><thead><tr><th>Name</th><th>Environment</th><th>Key</th><th>Status</th><th>Last used</th><th /></tr></thead><tbody>{keys.data.map((key) => <tr key={key.id}><td><strong>{key.name}</strong></td><td><span className="state-pill">{key.environment}</span></td><td><code>••••{key.last_four}</code></td><td>{key.status}</td><td>{key.last_used_at ? new Date(key.last_used_at).toLocaleString() : 'Never'}</td><td><button className="icon-button quiet" onClick={() => revoke.mutate(key.id)} aria-label="Revoke key"><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>}</section>
      {webhookSecret && <section className="secret-banner"><KeyRound size={20} /><div><strong>Copy this webhook signing secret now.</strong><code>{webhookSecret}</code></div><button className="icon-button" onClick={() => void navigator.clipboard.writeText(webhookSecret)}><Copy size={16} /></button></section>}
      <section className="panel-card"><header><div><p className="eyebrow">Signed events</p><h2>Workspace webhooks</h2></div></header><div className="inline-form"><label><span>HTTPS endpoint</span><input type="url" value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} placeholder="https://example.com/agentmesh" /></label><button className="button primary" disabled={!webhookUrl || createWebhook.isPending} onClick={() => createWebhook.mutate()}><Plus size={14} />Add endpoint</button></div>{Boolean(webhooks.data?.length) && <div className="version-list">{webhooks.data?.map((webhook) => <div key={webhook.id}><Code2 size={16} /><div><strong>{webhook.url}</strong><small>{webhook.event_types.join(', ')}</small></div><span className="state-pill">{webhook.status}</span>{webhook.status === 'ACTIVE' && <button className="button secondary small" onClick={() => disableWebhook.mutate(webhook.id)}>Disable</button>}</div>)}</div>}</section>
      <section className="panel-card"><header><div><p className="eyebrow">Delivery history</p><h2>Recent webhook attempts</h2></div></header>{!deliveries.data?.length ? <Empty title="No deliveries">Escalation events will appear here after they are queued.</Empty> : <div className="version-list">{deliveries.data.map((delivery) => <div key={delivery.id}><span className="version-number">{delivery.attempts}</span><div><strong>{delivery.event_type}</strong><small>{new Date(delivery.created_at).toLocaleString()}</small></div><span className={`state-pill ${delivery.status.toLowerCase()}`}>{delivery.status}{delivery.response_status ? ` · ${delivery.response_status}` : ''}</span></div>)}</div>}</section>
      <section className="panel-card code-sample"><header><div><p className="eyebrow">Quick start</p><h2>Create a decision</h2></div><button className="icon-button" onClick={() => void navigator.clipboard.writeText('POST /api/v1/decisions')}><Clipboard size={15} /></button></header><pre><code>{`curl -X POST "$AGENTMESH_URL/api/v1/decisions" \\
  -H "Authorization: Bearer $AGENTMESH_API_KEY" \\
  -H "Idempotency-Key: request-001" \\
  -H "Content-Type: application/json" \\
  -d '{"input":"What is our return policy?"}'`}</code></pre></section>
    </div>
  )
}

export function PlaygroundPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [decision, setDecision] = useState<DecisionRecord | null>(null)
  const mutation = useMutation({
    mutationFn: () => saasRequest<DecisionRecord>(
      `/organizations/${context.organization.id}/workspaces/${context.workspace.id}/playground/decisions`,
      {
        method: 'POST',
        idempotencyKey: crypto.randomUUID(),
        body: { input },
      },
    ),
    onSuccess: async (value) => {
      setDecision(value)
      await queryClient.invalidateQueries({ queryKey: ['decisions', context.workspace.id] })
      await queryClient.invalidateQueries({ queryKey: ['usage', context.organization.id] })
      await queryClient.invalidateQueries({ queryKey: ['reviews', context.workspace.id] })
    },
  })
  return (
    <div className="saas-page playground-page">
      <ErrorNotice error={mutation.error} />
      <div className="playground-grid">
        <section className="panel-card playground-composer"><header><div><p className="eyebrow">Dashboard test environment</p><h2>Run the full council</h2></div></header><div className="policy-warning compact"><KeyRound size={17} /><div><strong>No API key required here.</strong><p>AgentMesh uses this signed-in workspace and creates a scoped test credential behind the scenes for audit and usage tracking.</p></div></div><label><span>Customer question</span><textarea rows={8} maxLength={4000} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question covered by your uploaded knowledge..." /></label><div className="composer-actions"><small>{input.length} / 4000</small><button className="button primary" disabled={!input.trim() || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? 'Council reviewing...' : 'Run decision'}<Send size={14} /></button></div></section>
        <aside className="panel-card playground-result"><header><div><p className="eyebrow">Latest result</p><h2>{decision ? decision.decision_state : 'Decision output'}</h2></div></header>{!decision ? <Empty title="No result yet">Your answer, state, citations, and trace will appear here.</Empty> : <><span className={`decision-badge ${decision.decision_state === 'APPROVED' ? 'success' : 'warning'}`}>{decision.decision_state}</span><p className="decision-answer">{decision.answer}</p><dl className="compact-definition-list"><div><dt>Decision</dt><dd>{decision.decision_reason}</dd></div><div><dt>Usage</dt><dd>{decision.usage_units} unit</dd></div><div><dt>Record</dt><dd><code>{decision.id}</code></dd></div></dl><details className="decision-evidence"><summary>Evidence ({decision.citations?.length || 0})</summary>{decision.citations?.map((citation) => <blockquote key={citation.chunk_id}>{citation.text}<cite>{citation.metadata.filename as string || citation.document_id}</cite></blockquote>)}</details><details className="decision-evidence"><summary>Agent trace</summary><pre>{JSON.stringify(decision.trace?.agent_findings || {}, null, 2)}</pre></details></>}</aside>
      </div>
    </div>
  )
}

export function DecisionsPage() {
  const context = useWorkspace()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const list = useQuery({ queryKey: ['decisions', context.workspace.id], queryFn: () => saasRequest<DecisionRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/decisions?limit=100`) })
  const detail = useQuery({ queryKey: ['decision', selectedId], queryFn: () => saasRequest<DecisionRecord>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/decisions/${selectedId}`), enabled: Boolean(selectedId) })
  return <div className="saas-page decisions-page"><ErrorNotice error={list.error || detail.error} /><div className="split-record-layout"><section className="panel-card"><header><div><p className="eyebrow">Immutable history</p><h2>Decision records</h2></div></header>{!list.data?.length ? <Empty title="No records">Run the playground or call the API.</Empty> : <div className="decision-list">{list.data.map((item) => <button key={item.id} className={selectedId === item.id ? 'active' : ''} onClick={() => setSelectedId(item.id)}><span className={`decision-badge ${item.state === 'APPROVED' ? 'success' : 'warning'}`}>{item.state}</span><div><strong>{item.reason}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div><code>{item.id.slice(0, 8)}</code></button>)}</div>}</section><section className="panel-card decision-inspector">{!detail.data ? <Empty title="Select a decision">Inspect its answer, evidence, and specialist trace.</Empty> : <><header><div><p className="eyebrow">Decision {detail.data.id.slice(0, 8)}</p><h2>{detail.data.decision_state}</h2></div></header><p className="decision-answer">{detail.data.answer}</p><h3>Evidence</h3>{detail.data.citations?.map((citation) => <blockquote key={citation.chunk_id}>{citation.text}<cite>{citation.document_id}</cite></blockquote>)}<details><summary>Specialist trace</summary><pre>{JSON.stringify(detail.data.trace?.agent_findings, null, 2)}</pre></details></>}</section></div></div>
}

export function ReviewsPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const queue = useQuery({ queryKey: ['reviews', context.workspace.id], queryFn: () => saasRequest<ReviewRecord[]>(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/reviews`) })
  const selected = queue.data?.find((item) => item.id === selectedId) || queue.data?.[0]
  const action = useMutation({
    mutationFn: ({ name, record, answer }: { name: 'claim' | 'approve' | 'reject' | 'resolve'; record: ReviewRecord; answer?: string }) => saasRequest(`/organizations/${context.organization.id}/workspaces/${context.workspace.id}/reviews/${record.id}/${name}`, { method: 'POST', body: { expected_version: record.lock_version, answer, notes: `${name} action recorded in AgentMesh.` } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews', context.workspace.id] }),
  })
  return <div className="saas-page reviews-page"><ErrorNotice error={queue.error || action.error} /><div className="split-record-layout"><section className="panel-card"><header><div><p className="eyebrow">Accountable review</p><h2>Escalation queue</h2></div></header>{!queue.data?.length ? <Empty title="Queue clear">No decisions currently need human review.</Empty> : <div className="decision-list">{queue.data.map((item) => <button key={item.id} onClick={() => setSelectedId(item.id)} className={selected?.id === item.id ? 'active' : ''}><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span><div><strong>{item.reason}</strong><small>{item.status} · {new Date(item.created_at).toLocaleString()}</small></div></button>)}</div>}</section><section className="panel-card review-inspector">{!selected ? <Empty title="Select a review">Review evidence and record a disposition.</Empty> : <ReviewEditor record={selected} pending={action.isPending} onAction={(name, answer) => action.mutate({ name, record: selected, answer })} />}</section></div></div>
}

function ReviewEditor({ record, pending, onAction }: { record: ReviewRecord; pending: boolean; onAction: (name: 'claim' | 'approve' | 'reject' | 'resolve', answer?: string) => void }) {
  const [answer, setAnswer] = useState(record.draft_answer)
  React.useEffect(() => setAnswer(record.draft_answer), [record])
  return <><header><div><p className="eyebrow">{record.priority} priority</p><h2>{record.status.replaceAll('_', ' ')}</h2></div></header><section className="review-question"><span>Customer input</span><p>{record.query}</p></section><label><span>Reviewed answer</span><textarea rows={9} value={answer} onChange={(event) => setAnswer(event.target.value)} /></label><p className="muted-text">Approval reruns safety and evidence verification. Failed validation leaves the case in review.</p><div className="action-button-row">{record.status === 'OPEN' ? <button className="button primary" disabled={pending} onClick={() => onAction('claim')}>Claim review</button> : record.status === 'IN_REVIEW' ? <><button className="button primary" disabled={pending} onClick={() => onAction('approve', answer)}>Approve</button><button className="button danger" disabled={pending} onClick={() => onAction('reject')}>Reject</button><button className="button secondary" disabled={pending} onClick={() => onAction('resolve')}>Resolve</button></> : <span className="state-pill published">Review complete</span>}</div></>
}

export function UsagePage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [spendCap, setSpendCap] = useState('')
  const usage = useQuery({ queryKey: ['usage', context.organization.id], queryFn: () => saasRequest<UsageSummary>(`/organizations/${context.organization.id}/usage`) })
  const subscription = useMutation({
    mutationFn: () => saasRequest<{ url: string }>(`/organizations/${context.organization.id}/billing/subscription`, { method: 'POST' }),
    onSuccess: (value) => window.location.assign(value.url),
  })
  const cap = useMutation({
    mutationFn: () => saasRequest<UsageSummary>(`/organizations/${context.organization.id}/usage/spend-cap`, {
      method: 'PATCH',
      body: { spend_cap_paise: spendCap ? Math.round(Number(spendCap) * 100) : null },
    }),
    onSuccess: async () => {
      setSpendCap('')
      await queryClient.invalidateQueries({ queryKey: ['usage', context.organization.id] })
    },
  })
  const percentage = usage.data ? Math.min(100, (usage.data.completed_decisions / usage.data.included_decisions) * 100) : 0
  const projected = usage.data?.projected_overage_paise
  const billingActive = Boolean(
    usage.data?.payment_method_present
      && ['ACTIVE', 'AUTHENTICATED'].includes(usage.data.billing_status),
  )
  return (
    <div className="saas-page usage-page">
      <ErrorNotice error={usage.error || subscription.error || cap.error} />
      <section className="billing-hero">
        <div>
          <p className="eyebrow">{usage.data?.period}</p>
          <h2>{usage.data?.completed_decisions ?? 0} completed decisions</h2>
          <p>The first {usage.data?.included_decisions ?? 500} decisions are included across every workspace and environment.</p>
        </div>
        <span className={`state-pill ${(usage.data?.billing_status || 'free').toLowerCase()}`}>{usage.data?.billing_status || 'FREE'}</span>
      </section>
      <section className="panel-card usage-meter">
        <div className="usage-meter-labels"><span>Monthly allowance</span><strong>{usage.data?.remaining_free_decisions ?? 500} remaining</strong></div>
        <div className="usage-track"><i style={{ width: `${percentage}%` }} /></div>
        <div className="usage-meter-labels"><small>0</small><small>{usage.data?.included_decisions ?? 500} included</small></div>
      </section>
      <div className="billing-grid">
        <section className="panel-card">
          <CreditCard size={22} />
          <p className="eyebrow">Razorpay subscription</p>
          <h2>{billingActive ? 'Billing is active' : 'Continue after the free allowance'}</h2>
          <p>Completed decisions beyond the included allowance are submitted to Razorpay as subscription add-ons. Platform failures are not billed.</p>
          <p><strong>AgentMesh projection:</strong> {projected === null || projected === undefined ? 'Set by deployment pricing' : `₹${(projected / 100).toFixed(2)}`}. Razorpay add-on charges update asynchronously.</p>
          {billingActive
            ? <p className="muted-text">Razorpay sends payment-method update and recovery links directly to the billing contact.</p>
            : <button className="button primary" disabled={subscription.isPending} onClick={() => subscription.mutate()}>Start Razorpay billing <ArrowRight size={14} /></button>}
        </section>
        <section className="panel-card">
          <ShieldCheck size={22} />
          <p className="eyebrow">Billing safeguards</p>
          <h2>Monthly spend cap</h2>
          <p>{usage.data?.spend_cap_paise == null ? 'No customer spend cap is configured.' : `Current cap: ₹${(usage.data.spend_cap_paise / 100).toFixed(2)}`}</p>
          {context.organization.role === 'owner' && <div className="inline-form compact"><label><span>Cap in INR</span><input type="number" min="0" step="0.01" value={spendCap} onChange={(event) => setSpendCap(event.target.value)} placeholder="Leave blank to remove" /></label><button className="button secondary" disabled={cap.isPending || (Boolean(spendCap) && !Number.isFinite(Number(spendCap)))} onClick={() => cap.mutate()}>Save cap</button></div>}
          <ul><li>Idempotent retries count once</li><li>Blocked and escalated completed decisions count</li><li>Validation and platform failures do not count</li><li>Ambiguous Razorpay add-on deliveries require review to prevent duplicate charges</li></ul>
        </section>
      </div>
    </div>
  )
}

interface Member { id: string; auth_user_id: string; email: string; role: string; status: string; created_at: string }

export function TeamPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('viewer')
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const members = useQuery({ queryKey: ['members', context.organization.id], queryFn: () => saasRequest<Member[]>(`/organizations/${context.organization.id}/members`) })
  const invite = useMutation({ mutationFn: () => saasRequest<{ invite_url: string }>(`/organizations/${context.organization.id}/invitations`, { method: 'POST', body: { email, role } }), onSuccess: async (value) => { setInviteLink(value.invite_url); setEmail(''); await queryClient.invalidateQueries({ queryKey: ['members', context.organization.id] }) } })
  const update = useMutation({ mutationFn: ({ member, nextRole, status = member.status }: { member: Member; nextRole: string; status?: string }) => saasRequest<Member>(`/organizations/${context.organization.id}/members/${member.id}`, { method: 'PATCH', body: { role: nextRole, status } }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members', context.organization.id] }) })
  const canManage = ['owner', 'admin'].includes(context.organization.role)
  return <div className="saas-page team-page"><ErrorNotice error={members.error || invite.error || update.error} />{inviteLink && <div className="secret-banner"><Users size={20} /><div><strong>Invitation created and queued for email</strong><code>{inviteLink}</code></div><button className="icon-button" onClick={() => void navigator.clipboard.writeText(inviteLink)}><Copy size={15} /></button></div>}{canManage && <section className="panel-card"><header><div><p className="eyebrow">Organization access</p><h2>Invite a team member</h2></div></header><div className="inline-form"><label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label><span>Role</span><select value={role} onChange={(event) => setRole(event.target.value)}><option value="admin">Admin</option><option value="developer">Developer</option><option value="reviewer">Reviewer</option><option value="viewer">Viewer</option></select></label><button className="button primary" disabled={!email || invite.isPending} onClick={() => invite.mutate()}>Send invitation</button></div></section>}<section className="panel-card"><header><div><p className="eyebrow">Role-based access</p><h2>Members</h2></div></header><div className="resource-table-wrap"><table className="resource-table"><thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Joined</th></tr></thead><tbody>{members.data?.map((member) => <tr key={member.id}><td><strong>{member.email}</strong></td><td>{member.role === 'owner' || !canManage ? <span className="state-pill">{member.role}</span> : <select value={member.role} disabled={update.isPending} onChange={(event) => update.mutate({ member, nextRole: event.target.value })}><option value="admin">admin</option><option value="developer">developer</option><option value="reviewer">reviewer</option><option value="viewer">viewer</option></select>}</td><td>{member.role === 'owner' || !canManage ? member.status : <button className="button secondary small" onClick={() => update.mutate({ member, nextRole: member.role, status: member.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE' })}>{member.status}</button>}</td><td>{new Date(member.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></section></div>
}

export function SettingsPage() {
  const context = useWorkspace()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [template, setTemplate] = useState('GENERAL')
  const create = useMutation({ mutationFn: () => saasRequest(`/organizations/${context.organization.id}/workspaces`, { method: 'POST', body: { name, industry_template: template } }), onSuccess: async () => { setName(''); await queryClient.invalidateQueries({ queryKey: ['workspaces', context.organization.id] }) } })
  const remove = useMutation({ mutationFn: () => saasRequest(`/organizations/${context.organization.id}`, { method: 'DELETE' }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['organizations'] }); window.location.assign('/') } })
  return <div className="saas-page settings-page"><ErrorNotice error={create.error || remove.error} /><section className="panel-card"><header><div><p className="eyebrow">Workspace identity</p><h2>{context.workspace.name}</h2></div></header><dl className="definition-list"><div><dt>Organization</dt><dd>{context.organization.name}</dd></div><div><dt>Workspace ID</dt><dd><code>{context.workspace.id}</code></dd></div><div><dt>Template</dt><dd>{context.workspace.industry_template}</dd></div><div><dt>Published profile</dt><dd>{context.workspace.active_profile_version_id || 'Not published'}</dd></div><div><dt>Knowledge release</dt><dd>{context.workspace.active_knowledge_release_id || 'Not published'}</dd></div><div><dt>Content retention</dt><dd>30 days</dd></div></dl></section>{['owner', 'admin'].includes(context.organization.role) && <section className="panel-card"><header><div><p className="eyebrow">Product isolation</p><h2>Create another workspace</h2></div></header><div className="inline-form"><label><span>Name</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Product support" /></label><label><span>Template</span><select value={template} onChange={(event) => setTemplate(event.target.value)}><option value="GENERAL">General</option><option value="FINANCE">Finance</option><option value="HEALTHCARE">Healthcare information</option><option value="ECOMMERCE">E-commerce</option></select></label><button className="button primary" disabled={name.trim().length < 2 || create.isPending} onClick={() => create.mutate()}><Plus size={14} />Create workspace</button></div></section>}<section className="policy-warning"><LockKeyhole size={18} /><div><strong>Data boundary</strong><p>AgentMesh is not configured for PHI, PCI data, credentials, patient records, or regulated decisions. Workspace owners remain responsible for uploaded content.</p></div></section>{context.organization.role === 'owner' && <section className="panel-card danger-zone"><p className="eyebrow">Owner-only danger zone</p><h2>Delete organization</h2><p>This archives all workspaces and immediately prevents tenant access. Contact support for bounded source-storage deletion status.</p><button className="button danger" disabled={remove.isPending} onClick={() => { if (window.confirm(`Delete ${context.organization.name}? This cannot be undone.`)) remove.mutate() }}>Delete organization</button></section>}</div>
}

interface PlatformMetrics { organizations: number; decisions: number; failed_billing_events: number; failed_jobs: number; failed_webhooks: number; failed_emails: number }
interface PlatformOrganization { id: string; name: string; slug: string; status: string; billing_email: string; created_at: string }
interface PlatformHealth { postgresql: boolean; redis: boolean; pending_jobs: number; pending_billing_events: number }
interface PlatformTemplate { id: string; key: string; version: number; name: string; enabled: boolean; mandatory_rule_keys: string[] }

export function PlatformPage() {
  const metrics = useQuery({ queryKey: ['platform-metrics'], queryFn: () => saasRequest<PlatformMetrics>('/platform/metrics') })
  const organizations = useQuery({ queryKey: ['platform-organizations'], queryFn: () => saasRequest<PlatformOrganization[]>('/platform/organizations') })
  const health = useQuery({ queryKey: ['platform-health'], queryFn: () => saasRequest<PlatformHealth>('/platform/service-health') })
  const templates = useQuery({ queryKey: ['platform-templates'], queryFn: () => saasRequest<PlatformTemplate[]>('/platform/templates') })
  return <main className="platform-layout"><header><div><p className="eyebrow">MFA-gated operations</p><h1>AgentMesh platform</h1><p>Global health and commercial metadata. Tenant prompts, answers, and documents are excluded.</p></div><a className="button secondary" href="/">Return to workspace</a></header><ErrorNotice error={metrics.error || organizations.error || health.error || templates.error} />{metrics.data && <section className="metric-grid"><article><span>Organizations</span><strong>{metrics.data.organizations}</strong></article><article><span>Completed decisions</span><strong>{metrics.data.decisions}</strong></article><article><span>Billing failures</span><strong>{metrics.data.failed_billing_events}</strong></article><article><span>Operational failures</span><strong>{metrics.data.failed_jobs + metrics.data.failed_webhooks + metrics.data.failed_emails}</strong></article></section>}<div className="billing-grid"><section className="panel-card"><p className="eyebrow">Service health</p><h2>Runtime dependencies</h2><dl className="definition-list"><div><dt>PostgreSQL</dt><dd>{health.data?.postgresql ? 'Ready' : 'Unavailable'}</dd></div><div><dt>Redis</dt><dd>{health.data?.redis ? 'Ready' : 'Unavailable'}</dd></div><div><dt>Pending jobs</dt><dd>{health.data?.pending_jobs ?? '—'}</dd></div><div><dt>Pending billing events</dt><dd>{health.data?.pending_billing_events ?? '—'}</dd></div></dl></section><section className="panel-card"><p className="eyebrow">Curated controls</p><h2>Templates and mandatory packs</h2><div className="version-list">{templates.data?.map((template) => <div key={template.id}><span className="version-number">v{template.version}</span><div><strong>{template.name}</strong><small>{template.mandatory_rule_keys.join(', ')}</small></div><span className={`state-pill ${template.enabled ? 'published' : ''}`}>{template.enabled ? 'ACTIVE' : 'DISABLED'}</span></div>)}</div></section></div><section className="panel-card"><header><div><p className="eyebrow">Tenant directory</p><h2>Organizations</h2></div><button className="icon-button" onClick={() => { void metrics.refetch(); void organizations.refetch(); void health.refetch(); void templates.refetch() }}><RefreshCw size={15} /></button></header><div className="resource-table-wrap"><table className="resource-table"><thead><tr><th>Organization</th><th>Status</th><th>Billing email</th><th>Created</th></tr></thead><tbody>{organizations.data?.map((organization) => <tr key={organization.id}><td><strong>{organization.name}</strong><small>{organization.slug}</small></td><td>{organization.status}</td><td>{organization.billing_email}</td><td>{new Date(organization.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div></section></main>
}
