import { useState } from 'react'
import { api, ApiError } from '../api'
import { useDocuments } from '../context/DocumentsContext'

export default function SearchView() {
  const { documents } = useDocuments()
  const [query, setQuery] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [results, setResults] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setStatus('searching')
    setError(null)
    try {
      const data = await api.search({ query, documentId: documentId || undefined })
      setResults(data.results ?? [])
      setStatus('idle')
    } catch (err) {
      setStatus('error')
      setError(err instanceof ApiError ? err.message : 'Search failed.')
    }
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Search chunks</h2>
        <p>Raw vector search over your uploaded documents -- no generation, just retrieval.</p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="field-group">
          <label htmlFor="search-query">QUERY</label>
          <input
            id="search-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. how do exceptions work?"
          />
        </div>
        <div className="row" style={{ marginBottom: 16 }}>
          <div className="field-group" style={{ marginBottom: 0 }}>
            <label htmlFor="search-doc">SCOPE (OPTIONAL)</label>
            <select id="search-doc" value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
              <option value="">All documents</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
          <button className="btn primary" type="submit" disabled={status === 'searching'}>
            {status === 'searching' ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {status === 'error' && <p className="status-line error">{error}</p>}

      {results && (
        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p className="status-line">{results.length} result{results.length === 1 ? '' : 's'}</p>
          {results.map((r) => (
            <div key={r.chunk_id} className="bracket-frame">
              <div className="result-meta">
                <span className="status-line online">{r.filename}</span>
                <span className="status-line">distance {r.distance.toFixed(3)}</span>
              </div>
              <p className="result-text">{r.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
