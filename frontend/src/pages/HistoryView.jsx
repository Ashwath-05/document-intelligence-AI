import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function HistoryView() {
  const [conversations, setConversations] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .listConversations()
      .then((data) => setConversations(data.conversations ?? []))
      .catch(() => setError('Could not load conversation history.'))
  }, [])

  const openConversation = async (id) => {
    try {
      const detail = await api.getConversation(id)
      setSelected(detail)
    } catch {
      setError('Could not load that conversation.')
    }
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Conversation history</h2>
        <p>Past conversations, most recently active first.</p>
      </div>

      {error && <p className="status-line error">{error}</p>}

      <div className="history-layout">
        <ul className="doc-list history-list">
          {conversations === null && <li className="status-line">loading...</li>}
          {conversations?.length === 0 && (
            <li style={{ color: 'var(--text-muted)' }}>No conversations yet -- start one from Chat.</li>
          )}
          {conversations?.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`doc-list-item history-item${selected?.id === c.id ? ' active' : ''}`}
                onClick={() => openConversation(c.id)}
              >
                <span className="doc-list-name">{c.document_id ? 'scoped conversation' : 'general conversation'}</span>
                <span className="status-line">{new Date(c.updated_at).toLocaleString()}</span>
              </button>
            </li>
          ))}
        </ul>

        {selected && (
          <div className="bracket-frame history-detail">
            <div className="row" style={{ alignItems: 'center', marginBottom: 12 }}>
              <span className="status-line">{selected.id}</span>
              <Link className="btn primary" to={`/chat?conversation_id=${selected.id}`}>
                Continue in chat
              </Link>
            </div>
            {selected.messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role}`}>
                <span className="status-line chat-role">{m.role === 'user' ? 'you' : 'assistant'}</span>
                <p>{m.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
