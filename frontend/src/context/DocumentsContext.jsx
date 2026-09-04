import { createContext, useContext, useEffect, useState } from 'react'

// The backend has no "list all documents" endpoint by design -- GET
// /api/v1/documents/{id} only looks up a document you already have the id
// for (see Phase 0's own reasoning: no user scoping yet, so a list-all
// route would enumerate everyone's uploads). This context is the client-side
// stand-in: it remembers what THIS browser has uploaded, in localStorage,
// so Search/Chat can offer "scope to a document" without the backend
// needing to change.
const DocumentsContext = createContext(null)
const STORAGE_KEY = 'doc-intelligence:documents'

export function DocumentsProvider({ children }) {
  const [documents, setDocuments] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(documents))
  }, [documents])

  const addDocument = (doc) => {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)])
  }

  return (
    <DocumentsContext.Provider value={{ documents, addDocument }}>
      {children}
    </DocumentsContext.Provider>
  )
}

export function useDocuments() {
  const ctx = useContext(DocumentsContext)
  if (!ctx) throw new Error('useDocuments must be used within DocumentsProvider')
  return ctx
}
