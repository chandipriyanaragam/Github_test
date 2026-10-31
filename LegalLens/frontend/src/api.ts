export type Workflow = 'ask' | 'draft' | 'summary'

export type ApiMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  workflow: Workflow | null
  created_at: string
  citations: Citation[]
}

export type Citation = { id: string; document_id: string; filename: string; page: number | null; excerpt: string; source_number: number }

export type ConversationSummary = {
  id: string
  title: string
  jurisdiction: string | null
  created_at: string
  updated_at: string
  document_ids: string[]
  message_count: number
}

export type ConversationDetail = ConversationSummary & { messages: ApiMessage[] }

export type DocumentRecord = {
  id: string
  filename: string
  media_type: string
  size_bytes: number
  status: 'awaiting_processing' | 'ready' | 'failed' | 'deleted'
  conversation_id: string | null
  created_at: string
}

type ApiErrorBody = { error?: { code?: string; message?: string; request_id?: string | null } }

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000'
const API_BASE = configuredBase.replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new Error(`Cannot reach the LegalLens backend at ${API_BASE}. Start the backend and try again.`)
  }

  if (!response.ok) {
    let body: ApiErrorBody = {}
    try { body = await response.json() as ApiErrorBody } catch { /* The response may not contain JSON. */ }
    const message = body.error?.message ?? `Backend request failed (${response.status}).`
    const requestId = body.error?.request_id ? ` Request ID: ${body.error.request_id}.` : ''
    throw new Error(`${message}${requestId}`)
  }
  if (response.status === 204) return undefined as T
  return await response.json() as T
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const results: ConversationSummary[] = []
  let cursor: string | null = null
  do {
    const query = new URLSearchParams({ limit: '100' })
    if (cursor) query.set('cursor', cursor)
    const page = await request<{ items: ConversationSummary[]; next_cursor: string | null }>(`/api/v1/conversations?${query}`)
    results.push(...page.items)
    cursor = page.next_cursor
  } while (cursor)
  return results
}

export function createConversation(title?: string) {
  return request<ConversationSummary>('/api/v1/conversations', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }),
  })
}

export function listDocuments() {
  return request<DocumentRecord[]>('/api/v1/documents')
}

export function copyDocumentToConversation(documentId: string, conversationId: string) {
  const query = new URLSearchParams({ conversation_id: conversationId })
  return request<DocumentRecord>(`/api/v1/documents/${encodeURIComponent(documentId)}/copy?${query}`, { method: 'POST' })
}

export function getConversation(id: string) {
  return request<ConversationDetail>(`/api/v1/conversations/${encodeURIComponent(id)}`)
}

export function patchConversation(id: string, fields: { title?: string; jurisdiction?: string | null }) {
  return request<ConversationSummary>(`/api/v1/conversations/${encodeURIComponent(id)}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields),
  })
}

export function submitTurn(input: {
  conversation_id: string | null
  message: { content: string; workflow: Workflow; jurisdiction: string | null; document_ids: string[] }
}) {
  return request<{ turn_id: string; conversation_id: string; user_message: ApiMessage; status: 'completed' | 'failed'; assistant_message: ApiMessage | null }>(
    '/api/v1/chat/turns', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) },
  )
}

export function uploadDocument(file: File, conversationId: string | null) {
  const body = new FormData()
  body.append('file', file)
  if (conversationId) body.append('conversation_id', conversationId)
  return request<DocumentRecord>('/api/v1/documents', { method: 'POST', body })
}

export function getDocumentStatus(id: string) {
  return request<DocumentRecord & { detail: string | null }>(`/api/v1/documents/${encodeURIComponent(id)}/status`)
}

export function deleteDocument(id: string) {
  return request<void>(`/api/v1/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function deleteConversation(id: string) {
  return request<void>(`/api/v1/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function healthCheck() {
  return request<{ status: string }>('/health')
}

export function readinessCheck() {
  return request<{ status: string; dependencies: Record<string, string> }>('/ready')
}

