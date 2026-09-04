import { useRef, useState } from 'react'
import { api, ApiError } from '../api'
import { useDocuments } from '../context/DocumentsContext'

export default function UploadView() {
  const { documents, addDocument } = useDocuments()
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | uploading | error
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    setStatus('uploading')
    setError(null)
    try {
      const doc = await api.uploadDocument(file)
      addDocument({
        id: doc.id,
        filename: doc.filename ?? file.name,
        status: doc.status ?? 'processed',
      })
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
      setStatus('idle')
    } catch (err) {
      setStatus('error')
      setError(
        err instanceof ApiError && err.status >= 500
          ? 'The server ran out of resources processing this file. This can happen on constrained hosting -- try again, or try a smaller file.'
          : err.message
      )
    }
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h2>Upload a document</h2>
        <p>PDF files are extracted, chunked, and embedded for search and chat.</p>
      </div>

      <form className="bracket-frame" onSubmit={handleUpload} style={{ maxWidth: 520 }}>
        <div className="field-group">
          <label htmlFor="file-input">FILE</label>
          <input
            id="file-input"
            ref={inputRef}
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <button className="btn primary" type="submit" disabled={!file || status === 'uploading'}>
          {status === 'uploading' ? 'Processing...' : 'Upload document'}
        </button>
        {status === 'error' && <p className="status-line error" style={{ marginTop: 12 }}>{error}</p>}
      </form>

      <div style={{ marginTop: 40 }}>
        <p className="status-line">uploaded this session ({documents.length})</p>
        {documents.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', marginTop: 12 }}>
            Nothing uploaded yet. Upload a document above to search and chat with it.
          </p>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.id} className="doc-list-item">
                <span className="doc-list-name">{doc.filename}</span>
                <span className="status-line">{doc.id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
