import React, { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, Copy, KeyRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { saasRequest, type ApiKeyRecord, type Organization, type Workspace } from '../lib/saas-api'

const schema = z.object({
  companyName: z.string().min(2).max(160),
  workspaceName: z.string().min(2).max(160),
  template: z.enum(['GENERAL', 'FINANCE', 'HEALTHCARE', 'ECOMMERCE']),
})

type FormValues = z.infer<typeof schema>

interface OnboardingResponse {
  organization: Organization
  workspace: Workspace
}

export default function OnboardingPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [result, setResult] = useState<OnboardingResponse | null>(null)
  const [secret, setSecret] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { workspaceName: 'Support', template: 'GENERAL' },
  })

  const submit = form.handleSubmit(async (values) => {
    setError(null)
    try {
      const created = await saasRequest<OnboardingResponse>('/organizations', {
        method: 'POST',
        body: {
          name: values.companyName,
          workspace_name: values.workspaceName,
          industry_template: values.template,
        },
      })
      const key = await saasRequest<ApiKeyRecord>(
        `/organizations/${created.organization.id}/workspaces/${created.workspace.id}/api-keys`,
        {
          method: 'POST',
          body: {
            name: 'First test key',
            environment: 'test',
            scopes: ['decisions:write', 'decisions:read', 'traces:read'],
          },
        },
      )
      if (key.secret) {
        sessionStorage.setItem(`agentmesh.key.${created.workspace.id}`, key.secret)
        setSecret(key.secret)
      }
      setResult(created)
      await queryClient.invalidateQueries({ queryKey: ['organizations'] })
    } catch (value) {
      setError(value instanceof Error ? value.message : 'Company setup failed.')
    }
  })

  if (result) {
    const basePath = `/app/${result.organization.slug}/${result.workspace.slug}`
    return (
      <main className="onboarding-layout">
        <section className="onboarding-card completion-card">
          <span className="completion-mark"><Check size={24} /></span>
          <p className="eyebrow">Workspace created</p>
          <h1>{result.workspace.name} is ready to configure.</h1>
          <p>Your test key is shown once. Store it in a secret manager; AgentMesh keeps only its digest.</p>
          {secret && (
            <div className="secret-reveal">
              <code>{secret}</code>
              <button type="button" className="icon-button" onClick={() => void navigator.clipboard.writeText(secret)} aria-label="Copy API key"><Copy size={16} /></button>
            </div>
          )}
          <div className="onboarding-next-grid">
            <div><span>01</span><strong>Upload knowledge</strong><p>Add approved PDF, DOCX, text, or Markdown files.</p></div>
            <div><span>02</span><strong>Publish a release</strong><p>Preview processed evidence before live use.</p></div>
            <div><span>03</span><strong>Run a decision</strong><p>Use the playground or your new API key.</p></div>
          </div>
          <button className="button primary" onClick={() => navigate(`${basePath}/knowledge`)}>Continue to knowledge <ArrowRight size={15} /></button>
        </section>
      </main>
    )
  }

  return (
    <main className="onboarding-layout">
      <form className="onboarding-card" onSubmit={submit}>
        <div className="onboarding-progress"><span className="active">Company</span><i /><span>Workspace</span><i /><span>Test key</span></div>
        <p className="eyebrow">New organization</p>
        <h1>Configure your first AgentMesh workspace.</h1>
        <p>Each workspace has isolated documents, controls, API keys, reviews, and usage.</p>
        {error && <div className="alert danger"><strong>Setup failed</strong><p>{error}</p></div>}
        <div className="form-grid">
          <label><span>Company name</span><input {...form.register('companyName')} placeholder="Acme Support" />{form.formState.errors.companyName && <small>{form.formState.errors.companyName.message}</small>}</label>
          <label><span>Workspace name</span><input {...form.register('workspaceName')} />{form.formState.errors.workspaceName && <small>{form.formState.errors.workspaceName.message}</small>}</label>
          <label className="full"><span>Starting template</span><select {...form.register('template')}><option value="GENERAL">General support</option><option value="FINANCE">Financial support</option><option value="HEALTHCARE">Healthcare information</option><option value="ECOMMERCE">E-commerce support</option></select></label>
        </div>
        <div className="sensitive-data-notice"><KeyRound size={17} /><div><strong>Public MVP data boundary</strong><p>Do not upload patient records, payment-card data, bank credentials, or authentication secrets.</p></div></div>
        <button className="button primary" disabled={form.formState.isSubmitting}>{form.formState.isSubmitting ? 'Creating workspace…' : 'Create company and test key'}<ArrowRight size={15} /></button>
      </form>
    </main>
  )
}
