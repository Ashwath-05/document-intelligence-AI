import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useDocuments } from '../context/DocumentsContext'

export default function ChatView() {
  const { documents } = useDocuments()
  const [searchParams, setSearchParams] = useSearchParams()
  const [conversationId, setConversationId] = useState(searchParams.get('conversation_id') || null)
  const [documentId, setDocumentId] = useState('')
  const [messages, setMessages] = useState([{role:'user',content:'How do I get priority assignment on new clients?',sources:[]},{role:'assistant',content:'You earn priority assignment on new clients by posting consistently -- delivering clips week after week so you are seen as reliable. [1]',sources:[{chunk_id:'a',filename:'Clipper_Playbook.pdf',distance:0.575}]}])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState('idle') // idle | sending | error
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  // Resuming a conversation from History links here with ?conversation_id=...
  // -- hydrate the full transcript once on mount.
  useEffect(() => {
    const paramId = searchParams.get('conversation_id')
    if (!paramId) return
    api
      .getConversation(paramId)
      .then((conv) => {
        setConversationId(conv.id)
        setDocumentId(conv.document_id || '')
        setMessages(
          conv.messages.map((m) => ({
            role: m.role,
            content: m.content,
            sources: [],
          }))
        )
      })
      .catch(() => setError('Could not load that conversation.'))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const startNewConversation = () => {
    setConversationId(null)
    setDocumentId('')
    setMessages([])
    setSearchParams({})
  }

  const handleSend = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || status === 'sending') return

    setMessages((prev) => [...prev, { role: 'user', content: question, sources: [] }])
    setInput('')
    setStatus('sending')
    setError(null)

    try {
      const data = await api.chat({ question, conversationId, documentId: documentId || undefined })
      setConversationId(data.conversation_id)
      setSearchParams({ conversation_id: data.conversation_id })
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer, sources: data.sources ?? [] }])
      setStatus('idle')
    } catch (err) {
      setStatus('error')
      setError(
        err instanceof ApiError && err.status >= 500
          ? 'The server hit a resource limit generating that answer. Try again in a moment.'
          : err.message
      )
    }
  }

  return (
    <div className="main-content chat-page">
      <div className="page-header row" style={{ alignItems: 'flex-start' }}>
        <div>
          <h2>Chat</h2>
          <p>Ask questions across turns -- follow-ups are reformulated against conversation history.</p>
        </div>
        <button className="btn" type="button" onClick={startNewConversation}>
          New conversation
        </button>
      </div>

      {!conversationId && (
        <div className="field-group" style={{ maxWidth: 360 }}>
          <label htmlFor="chat-doc">SCOPE (OPTIONAL, LOCKS ON FIRST MESSAGE)</label>
          <select id="chat-doc" value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            <option value="">All documents</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="chat-window bracket-frame" ref={scrollRef}>
        {messages.length === 0 ? (
          <p className="status-line">no messages yet -- ask something below</p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`chat-message ${m.role}`}>
              <span className="status-line chat-role">{m.role === 'user' ? 'you' : 'assistant'}</span>
              <p>{m.content}</p>
              {m.sources.length > 0 && (
                <div className="chat-sources">
                  {m.sources.map((s, j) => (
                    <div key={s.chunk_id} className="chat-source">
                      [{j + 1}] {s.filename} · distance {s.distance.toFixed(3)}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {status === 'error' && <p className="status-line error">{error}</p>}

      <form onSubmit={handleSend} className="row" style={{ marginTop: 16 }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={status === 'sending'}
        />
        <button className="btn primary" type="submit" disabled={!input.trim() || status === 'sending'}>
          {status === 'sending' ? 'Thinking...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
