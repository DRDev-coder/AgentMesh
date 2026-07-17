import React from 'react'
import { ExternalLink } from 'lucide-react'
import { humanize } from '../decision'
import { SectionHeader, StatusIndicator } from './ui'

export default function BlockchainProof({ audit }) {
  const status = audit?.status || 'NOT_REPORTED'
  const transactionHash = audit?.transaction_hash
  const explorerBase = audit?.explorer_url?.replace(/\/$/, '')
    || import.meta.env.VITE_BLOCK_EXPLORER_TX_URL?.replace(/\/$/, '')

  return (
    <section className="trace-section audit-section" aria-labelledby="audit-heading">
      <SectionHeader
        eyebrow="Optional integration"
        title="Audit anchor"
        id="audit-heading"
        description="A submitted hash is not treated as confirmed until the API reports receipt confirmation."
        action={<StatusIndicator status={status} label={humanize(status)} />}
      />

      <dl className="audit-details">
        <div>
          <dt>Network</dt>
          <dd>{audit?.network || 'Not reported'}</dd>
        </div>
        <div>
          <dt>Transaction hash</dt>
          <dd>
            {transactionHash ? <code>{transactionHash}</code> : 'Not reported'}
            {transactionHash && explorerBase && (
              <a href={`${explorerBase}/${encodeURIComponent(transactionHash)}`} target="_blank" rel="noreferrer">
                Open explorer <ExternalLink size={13} aria-hidden="true" />
              </a>
            )}
          </dd>
        </div>
      </dl>

      {audit?.error && <div className="inline-error">{audit.error}</div>}
    </section>
  )
}
