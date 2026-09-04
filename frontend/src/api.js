// Thin fetch wrapper around every endpoint the backend exposes.
// Base URL comes from an env var so switching backends (Render -> Cloud Run)
// never means touching component code -- see .env.example.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Request failed (${status})`)
    this.status = status
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    let detail
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      detail = res.statusText
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  health: () => request('/api/v1/health'),

  uploadDocument: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/v1/documents', { method: 'POST', body: form })
  },
  getDocument: (documentId) => request(`/api/v1/documents/${documentId}`),

  search: ({ query, documentId, topK = 5 }) =>
    request('/api/v1/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        ...(documentId ? { document_id: documentId } : {}),
        top_k: topK,
      }),
    }),

  generate: ({ question, documentId, topK = 5 }) =>
    request('/api/v1/generate', {
      method: 'POST',
      body: JSON.stringify({
        question,
        ...(documentId ? { document_id: documentId } : {}),
        top_k: topK,
      }),
    }),

  chat: ({ question, conversationId, documentId, topK = 5 }) =>
    request('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        question,
        ...(conversationId ? { conversation_id: conversationId } : {}),
        ...(documentId ? { document_id: documentId } : {}),
        top_k: topK,
      }),
    }),

  listConversations: ({ documentId, limit = 20, offset = 0 } = {}) => {
    const params = new URLSearchParams({ limit, offset })
    if (documentId) params.set('document_id', documentId)
    return request(`/api/v1/conversations?${params}`)
  },
  getConversation: (conversationId) => request(`/api/v1/conversations/${conversationId}`),
}

export { ApiError }
