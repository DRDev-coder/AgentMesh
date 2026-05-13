import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const AGENTS = [
  { name: 'SAGE', color: '#3B82F6', role: 'Technical Expert' },
  { name: 'GUARDIAN', color: '#10B981', role: 'Security Enforcer' },
  { name: 'EMPATH', color: '#F59E0B', role: 'Emotional Intel' },
  { name: 'ORACLE', color: '#8B5CF6', role: 'Fact Checker' }
]

export default function AgentDebateViewer({ sessionId }) {
  const [agents, setAgents] = useState(
    AGENTS.map(a => ({ ...a, status: 'idle', confidence: 0, vote: null, output: null }))
  )
  const [consensus, setConsensus] = useState(null)
  const [query, setQuery] = useState('')

  const runSimulation = async () => {
    if (!query.trim()) return

    setAgents(AGENTS.map(a => ({ ...a, status: 'analyzing', confidence: 0, vote: null, output: null })))
    setConsensus(null)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      const data = await res.json()

      const votes = data.agent_votes || {}
      const delay = (ms) => new Promise(r => setTimeout(r, ms))

      for (let i = 0; i < AGENTS.length; i++) {
        await delay(800)
        const agentName = AGENTS[i].name.toLowerCase()
        const voteData = votes[agentName] || {}

        let vote = 'AGREE'
        if (voteData.status === 'SAFE' || voteData.status === 'allow') {
          vote = 'AGREE'
        } else if (voteData.hallucination_flag) {
          vote = 'DISAGREE'
        } else if (voteData.status === 'WARNING' || voteData.status === 'escalate') {
          vote = 'ABSTAIN'
        } else if (voteData.status === 'CRITICAL' || voteData.status === 'block') {
          vote = 'DISAGREE'
        }

        setAgents(prev => prev.map((a, idx) => 
          idx === i ? {
            ...a,
            status: 'done',
            confidence: voteData.confidence || voteData.sentiment_score || voteData.similarity_to_sage || 85,
            vote: vote,
            output: voteData
          } : a
        ))
      }

      await delay(500)
      setConsensus({
        status: data.consensus_status,
        reason: data.consensus_reason,
        txHash: data.blockchain_tx
      })
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Live Agent Council</h2>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Enter a query to watch the council deliberate..."
          style={{ flex: 1 }}
        />
        <button onClick={runSimulation}>Run Council</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '30px' }}>
        {agents.map(agent => (
          <div 
            key={agent.name}
            className={`agent-card ${agent.status}`}
            style={{ borderColor: agent.color }}
          >
            <h3 style={{ color: agent.color }}>{agent.name}</h3>
            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '10px' }}>{agent.role}</p>
            <div className="status" style={{ textTransform: 'uppercase', fontSize: '12px', marginBottom: '8px' }}>
              {agent.status}
            </div>
            {agent.confidence > 0 && (
              <div style={{ fontSize: '14px', marginBottom: '8px' }}>
                Confidence: {Math.round(agent.confidence)}%
              </div>
            )}
            {agent.vote && (
              <div className={`vote ${agent.vote}`} style={{ fontSize: '18px' }}>
                {agent.vote}
              </div>
            )}
          </div>
        ))}
      </div>

      {consensus && (
        <div className={`consensus-result ${consensus.status}`} style={{ padding: '20px', borderRadius: '12px', textAlign: 'center' }}>
          <h3>
            {consensus.status === 'CONSENSUS_REACHED' ? 'CONSENSUS REACHED' : 
             consensus.status === 'BLOCKED' ? 'BLOCKED BY GUARDIAN' :
             consensus.status === 'HALLUCINATION_BLOCKED' ? 'HALLUCINATION DETECTED' :
             'NO CONSENSUS — ESCALATING'}
          </h3>
          <p style={{ marginTop: '10px' }}>{consensus.reason}</p>
          {consensus.txHash && consensus.txHash.startsWith('0x') && (
            <p style={{ marginTop: '10px' }}>
              <a 
                href={`https://mumbai.polygonscan.com/tx/${consensus.txHash}`}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#60a5fa' }}
              >
                View Immutable Audit on Blockchain
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
