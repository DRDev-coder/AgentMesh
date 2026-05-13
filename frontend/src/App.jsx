import React, { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import AgentDebateViewer from './components/AgentDebateViewer'

function App() {
  const [activeSession, setActiveSession] = useState(null)
  const [view, setView] = useState('chat')

  return (
    <div className="app">
      <header style={{ padding: '20px', textAlign: 'center', borderBottom: '1px solid #334155' }}>
        <h1>AGENTMESH</h1>
        <p>No AI decides alone. 4 agents. 1 consensus. Immutable proof.</p>
        <div style={{ marginTop: '10px' }}>
          <button onClick={() => setView('chat')} style={{ marginRight: '10px' }}>
            Customer Chat
          </button>
          <button onClick={() => setView('debate')}>
            Live Council View
          </button>
        </div>
      </header>

      {view === 'chat' ? (
        <ChatInterface onSessionStart={setActiveSession} />
      ) : (
        <AgentDebateViewer sessionId={activeSession} />
      )}
    </div>
  )
}

export default App
