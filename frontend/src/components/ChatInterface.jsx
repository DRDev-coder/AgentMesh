import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function ChatInterface({ onSessionStart }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMsg = { role: 'user', text: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })
      })
      const data = await res.json()

      onSessionStart(data.session_id)

      const botMsg = {
        role: 'bot',
        text: data.final_answer || data.consensus_reason || 'Processing...',
        meta: data
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + err.message }])
    }

    setLoading(false)
  }

  return (
    <div className="chat-container">
      <div style={{ minHeight: '400px', marginBottom: '20px' }}>
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <p>{m.text}</p>
            {m.meta && m.meta.consensus_status === 'CONSENSUS_REACHED' && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#10b981' }}>
                Verified by 4 Agents | Confidence: {m.meta.confidence}%
                {m.meta.blockchain_tx && m.meta.blockchain_tx.startsWith('0x') && (
                  <div>
                    <a 
                      href={`https://mumbai.polygonscan.com/tx/${m.meta.blockchain_tx}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#60a5fa' }}
                    >
                      View on Blockchain
                    </a>
                  </div>
                )}
              </div>
            )}
            {m.meta && m.meta.escalate && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#ef4444' }}>
                ESCALATED TO HUMAN — {m.meta.consensus_reason}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message bot">Agent Council deliberating...</div>}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Type your support query..."
        />
        <button onClick={sendMessage} disabled={loading}>Send</button>
      </div>
    </div>
  )
}
