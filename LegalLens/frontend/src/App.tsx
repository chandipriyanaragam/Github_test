import { ChangeEvent, KeyboardEvent, ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import {
  ApiMessage, ConversationDetail, ConversationSummary, copyDocumentToConversation,
  createConversation as createConversationApi, deleteConversation as removeConversation,
  deleteDocument, DocumentRecord, getConversation, getDocumentStatus, healthCheck,
  listConversations, listDocuments, patchConversation, readinessCheck, submitTurn, uploadDocument, Workflow,
} from './api'

type Mode = 'Ask' | 'Draft' | 'Summary'
type Attachment = Pick<DocumentRecord, 'id' | 'filename' | 'status'>

function workflowLabel(workflow: Workflow | null): Mode | undefined {
  return workflow ? ({ ask: 'Ask', draft: 'Draft', summary: 'Summary' } as const)[workflow] : undefined
}

function displayTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true as const }
  const paths: Record<string, ReactNode> = {
    brand: <><path d="M7 4.5h10v15H7z"/><path d="M10 8h4M10 11h4M10 14h2"/><path d="M5 7v13h10"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>, search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4 4"/></>,
    panel: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></>, more: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    attach: <><path d="m8.5 12.5 6.6-6.6a3.2 3.2 0 0 1 4.5 4.5l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.1-8.1"/></>, send: <><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>, down: <path d="m7 10 5 5 5-5"/>, file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></>,
    sparkle: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z"/><path d="m19 16 .9 2.1L22 19l-2.1.9L19 22l-.9-2.1L16 19l2.1-.9Z"/></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
    edit: <><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></>,
    trash: <><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>, close: <><path d="m18 6-12 12M6 6l12 12"/></>,
    check: <path d="m5 12 4 4L19 6"/>, shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    message: <><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8Z"/></>,
  }
  return <svg {...common}>{paths[name] ?? paths.file}</svg>
}

function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ConversationDetail | null>(null)
  const [mode, setMode] = useState<Mode>('Ask')
  const [jurisdiction, setJurisdiction] = useState('')
  const [prompt, setPrompt] = useState('')
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [documentLibrary, setDocumentLibrary] = useState<DocumentRecord[]>([])
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [backendReady, setBackendReady] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const promptRef = useRef<HTMLTextAreaElement>(null)

  const active = conversations.find(item => item.id === activeId)
  const groups = useMemo(() => {
    const filtered = conversations.filter(item => item.title.toLowerCase().includes(search.toLowerCase()))
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const yesterday = today - 86400000
    const names = ['Today', 'Yesterday', 'This week']
    return names.map((date, index) => ({ date, items: filtered.filter(item => {
      const timestamp = new Date(item.updated_at).getTime()
      if (index === 0) return timestamp >= today
      if (index === 1) return timestamp >= yesterday && timestamp < today
      return timestamp < yesterday
    }) })).filter(group => group.items.length)
  }, [conversations, search])

  useEffect(() => {
    let cancelled = false
    async function initialize() {
      setLoading(true)
      try {
        await healthCheck()
        await readinessCheck()
        if (cancelled) return
        setBackendReady(true)
        const [items, documents] = await Promise.all([listConversations(), listDocuments()])
        const documentStatuses = await Promise.all(documents.map(document => getDocumentStatus(document.id).catch(() => document)))
        if (!cancelled) {
          setConversations(items)
          setDocumentLibrary(documentStatuses)
          if (items.length) setActiveId(items[0].id)
        }
      } catch (cause) {
        if (!cancelled) { setError(cause instanceof Error ? cause.message : 'Could not load the backend.'); setBackendReady(false) }
      } finally { if (!cancelled) setLoading(false) }
    }
    void initialize()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadDetail() {
      setDetail(null)
      if (!activeId) return
      try {
        const result = await getConversation(activeId)
        const docs = await Promise.all(result.document_ids.map(id => getDocumentStatus(id).catch(() => null)))
        if (cancelled) return
        setDetail(result)
        setJurisdiction(result.jurisdiction ?? '')
        setMode(workflowLabel([...result.messages].reverse().find(message => message.workflow)?.workflow ?? null) ?? 'Ask')
        setAttachments(docs.filter((doc): doc is NonNullable<typeof doc> => doc !== null).map(doc => ({ id: doc.id, filename: doc.filename, status: doc.status })))
      } catch (cause) {
        if (!cancelled) setError(cause instanceof Error ? cause.message : 'Could not load this conversation.')
      }
    }
    void loadDetail()
    return () => { cancelled = true }
  }, [activeId])

  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(''), 3200); return () => window.clearTimeout(timer) }, [notice])
  useEffect(() => {
    const handler = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); createConversation() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  })

  function createConversation() {
    setActiveId(null); setDetail(null); setMode('Ask'); setJurisdiction(''); setPrompt(''); setAttachments([]); setError(''); setSidebarOpen(false)
    window.setTimeout(() => promptRef.current?.focus(), 0)
  }

  function selectConversation(item: ConversationSummary) {
    setActiveId(item.id); setMode('Ask'); setAttachments([]); setError(''); setSidebarOpen(false)
  }

  async function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (!files.length) return
    const invalid = files.filter(file => !/\.(pdf|docx)$/i.test(file.name) || file.size > 25 * 1024 * 1024 || file.size === 0)
    if (invalid.length) { setError('Only non-empty PDF or DOCX files up to 25 MB are accepted.'); return }
    setError(''); setBusy(true)
    try {
      for (const file of files) {
        const saved = await uploadDocument(file, activeId)
        setAttachments(previous => [...previous.filter(item => item.id !== saved.id), { id: saved.id, filename: saved.filename, status: saved.status }])
      }
      if (activeId) {
        const [updated, items] = await Promise.all([getConversation(activeId), listConversations()])
        setDetail(updated); setConversations(items)
      }
      setDocumentLibrary(await listDocuments())
      setNotice(`${files.length} file${files.length === 1 ? '' : 's'} extracted and ready.`)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Upload failed.') }
    finally { setBusy(false) }
  }

  async function removeAttachment(item: Attachment) {
    setError('')
    try {
      await deleteDocument(item.id)
      setAttachments(previous => previous.filter(file => file.id !== item.id))
      if (activeId) {
        const [updated, items, documents] = await Promise.all([getConversation(activeId), listConversations(), listDocuments()])
        setDetail(updated); setConversations(items); setDocumentLibrary(documents)
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not remove the file.') }
  }

  async function attachExistingDocument(documentId: string) {
    if (!documentId || busy) return
    setError(''); setBusy(true)
    try {
      let conversationId = activeId
      if (!conversationId) {
        const conversation = await createConversationApi('Document summary')
        conversationId = conversation.id
      }
      const copied = await copyDocumentToConversation(documentId, conversationId)
      setActiveId(conversationId)
      setAttachments(previous => [...previous, { id: copied.id, filename: copied.filename, status: copied.status }])
      const [updated, items, documents] = await Promise.all([getConversation(conversationId), listConversations(), listDocuments()])
      setDetail(updated); setConversations(items); setDocumentLibrary(documents)
      setNotice(`${copied.filename} attached to this conversation.`)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not attach this document.') }
    finally { setBusy(false) }
  }

  async function send() {
    const content = prompt.trim()
    if (!content || busy) return
    setError(''); setBusy(true)
    try {
      const result = await submitTurn({
        conversation_id: activeId,
        message: { content, workflow: mode.toLowerCase() as Workflow, jurisdiction: jurisdiction || null, document_ids: attachments.map(file => file.id) },
      })
      setActiveId(result.conversation_id)
      setPrompt('')
      setDetail(await getConversation(result.conversation_id))
      setConversations(await listConversations())
      setNotice('LegalLens finished the response.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this turn.')
      if (!(cause instanceof Error && cause.message.includes('OPENAI_API_KEY'))) {
        try {
          const items = await listConversations()
          setConversations(items)
          if (activeId) setDetail(await getConversation(activeId))
          else if (items.length) setActiveId(items[0].id)
        } catch { /* Keep the original workflow error visible. */ }
      }
    }
    finally { setBusy(false) }
  }

  async function changeJurisdiction(value: string) {
    setJurisdiction(value); setError('')
    if (!activeId) return
    try {
      const updated = await patchConversation(activeId, { jurisdiction: value || null })
      setConversations(previous => previous.map(item => item.id === updated.id ? updated : item))
      setDetail(previous => previous ? { ...previous, jurisdiction: updated.jurisdiction, updated_at: updated.updated_at } : previous)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save jurisdiction.') }
  }

  async function renameConversation(item: ConversationSummary) {
    const proposed = window.prompt('Rename conversation', item.title)
    if (proposed === null) return
    const title = proposed.trim()
    if (!title) { setError('Conversation title cannot be empty.'); return }
    setError('')
    try {
      const updated = await patchConversation(item.id, { title })
      setConversations(previous => previous.map(conversation => conversation.id === item.id ? updated : conversation))
      setDetail(previous => previous?.id === item.id ? { ...previous, title: updated.title, updated_at: updated.updated_at } : previous)
      setNotice('Conversation renamed.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not rename the conversation.') }
  }

  async function removeActiveConversation(item: ConversationSummary) {
    if (!window.confirm(`Delete “${item.title}” and its stored files?`)) return
    setError('')
    try {
      await removeConversation(item.id)
      const [items, documents] = await Promise.all([listConversations(), listDocuments()])
      setConversations(items); setDocumentLibrary(documents)
      if (activeId === item.id) {
        setActiveId(items[0]?.id ?? null); setDetail(null); setAttachments([]); setJurisdiction('')
      }
      setNotice('Conversation deleted.')
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not delete the conversation.') }
  }

  function onPromptKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send() }
  }

  async function copyText(text: string) {
    try { await navigator.clipboard.writeText(text); setNotice('Copied to clipboard.') }
    catch { setError('Clipboard access is unavailable in this browser.') }
  }

  const messages: ApiMessage[] = detail?.messages ?? []

  return <div className={`app-shell ${navCollapsed && !sidebarOpen ? 'nav-collapsed' : ''}`}>
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} aria-label="Conversation navigation">
      <div className="sidebar-top"><a className="brand" href="#home" onClick={event => event.preventDefault()}><span className="brand-mark"><Icon name="brand" size={21} /></span><span>Legal<span className="brand-light">Lens</span></span></a><button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}><Icon name="close" /></button></div>
      <button className="new-chat" onClick={createConversation}><Icon name="plus" size={18} /><span>New conversation</span><kbd>⌘ K</kbd></button>
      <button className={`side-link ${searchOpen ? 'side-active' : ''}`} onClick={() => { setSearchOpen(value => !value); setTimeout(() => document.getElementById('history-search')?.focus(), 0) }}><Icon name="search" size={17} /><span>Search conversations</span></button>
      {searchOpen && <div className="search-wrap"><Icon name="search" size={15} /><input id="history-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search history" aria-label="Search conversations" /></div>}
      <div className="history-label">YOUR WORKSPACE</div>
      <nav className="conversation-list" aria-label="Past conversations">
        {loading ? <p className="no-results">Loading conversations…</p> : groups.length ? groups.map(group => <section className="history-group" key={group.date}><h2>{group.date}</h2>{group.items.map(item => <div className={`conversation-item ${activeId === item.id ? 'selected' : ''}`} key={item.id}><button className="conversation-select" onClick={() => selectConversation(item)} title={item.title}><Icon name="message" size={15} /><span>{item.title}</span></button><button className="conversation-delete" aria-label={`Delete ${item.title}`} onClick={() => void removeActiveConversation(item)}><Icon name="trash" size={14} /></button></div>)}</section>) : <p className="no-results">{search ? 'No conversations found.' : 'No saved conversations yet.'}</p>}
      </nav>
      <div className="sidebar-bottom"><div className="demo-card"><span className="demo-icon"><Icon name="shield" size={16} /></span><div><strong>Local development</strong><p>Shared demo identity</p></div><span className="demo-dot" /></div><div className="profile-button"><span className="avatar">LL</span><span className="profile-info"><strong>LegalLens</strong><small>Development workspace</small></span></div></div>
    </aside>
    {sidebarOpen && <button aria-label="Close navigation overlay" className="sidebar-scrim" onClick={() => setSidebarOpen(false)} />}
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}><Icon name="menu" /></button><button className="icon-button desktop-panel" aria-label="Toggle navigation" onClick={() => setNavCollapsed(value => !value)}><Icon name="panel" /></button><span className="crumb">Workspace</span><Icon name="chevron" size={14} /><span className="crumb-current">{active?.title ?? 'New conversation'}</span></div><div className="topbar-right"><span className="demo-pill"><span />{backendReady ? 'Backend connected' : 'Backend offline'}</span>{active && <><button className="icon-button" aria-label="Rename conversation" onClick={() => void renameConversation(active)}><Icon name="edit" size={16} /></button><button className="icon-button" aria-label="Delete conversation" onClick={() => void removeActiveConversation(active)}><Icon name="trash" size={16} /></button></>}</div></header>
      <div className="demo-banner"><Icon name="shield" size={15} /><span><strong>Development workspace</strong> · Backend uses a shared demo identity and has no authentication. Do not enter real client information.</span></div>
      {error && <div className="integration-error" role="alert"><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={14} /></button></div>}
      <section className="conversation-scroll" aria-label="Conversation messages">
        {!activeId ? <div className="welcome"><div className="welcome-emblem"><Icon name="sparkle" size={25} /></div><p className="eyebrow">YOUR LEGAL WORKSPACE</p><h1>Good work starts<br />with a clear question.</h1><p className="welcome-copy">Ask questions, summarize documents, and prepare drafts with source citations.</p><div className="starter-grid"><button onClick={() => { setMode('Ask'); setPrompt('What should I look for in this agreement?'); promptRef.current?.focus() }}><span className="starter-icon ask-icon"><Icon name="message" /></span><strong>Ask a question</strong><small>Get a cited answer</small><Icon name="chevron" size={15} /></button><button onClick={() => { setMode('Summary'); setPrompt('Summarize the key terms and review points.'); promptRef.current?.focus() }}><span className="starter-icon summary-icon"><Icon name="file" /></span><strong>Summarize a document</strong><small>Review key terms and risks</small><Icon name="chevron" size={15} /></button><button onClick={() => { setMode('Draft'); setPrompt('Draft a concise update based on these facts.'); promptRef.current?.focus() }}><span className="starter-icon draft-icon"><Icon name="edit" /></span><strong>Start a draft</strong><small>Prepare a work product</small><Icon name="chevron" size={15} /></button></div></div> : <div className="thread">
          <div className="thread-heading"><div><div className="thread-kicker">{attachments.length ? <><Icon name="file" size={14} /> {attachments.map(file => file.filename).join(', ')}</> : <><Icon name="message" size={14} /> Conversation</>}</div><h1>{active?.title ?? 'Loading conversation…'}</h1></div><button className="text-button" onClick={() => setNotice('Export is not available in this backend version.')}>Export <Icon name="down" size={15} /></button></div>
          {messages.map(message => <article className={`message ${message.role}`} key={message.id}><div className={`message-avatar ${message.role}`}>{message.role === 'user' ? 'You' : <Icon name="brand" size={18} />}</div><div className="message-body"><div className="message-meta"><strong>{message.role === 'user' ? 'You' : 'LegalLens'}</strong>{message.workflow && <><span className="meta-separator">·</span><span>{workflowLabel(message.workflow)}</span></>}<time>{displayTime(message.created_at)}</time></div><div className="message-text">{message.content.split('\n').map((line, lineIndex) => <p key={`${message.id}-${lineIndex}`}>{line || '\u00a0'}</p>)}</div><div className="message-actions"><button onClick={() => void copyText(message.content)} aria-label="Copy message"><Icon name="copy" size={15} />Copy</button></div>{message.role === 'assistant' && message.citations?.length > 0 && <div className="citation-list"><strong>Sources</strong>{message.citations.map((citation, citationIndex) => <details key={`${message.id}-${citation.document_id}-${citationIndex}`}><summary>[{citation.source_number}] {citation.filename}{citation.page ? `, page ${citation.page}` : ''}</summary><p>{citation.excerpt}</p></details>)}</div>}</div></article>)}
          {busy && <div className="upload-status"><span className="spinner" /> Saving to backend…</div>}
        </div>}
      </section>
      <div className="composer-wrap"><div className="composer-context">{attachments.length > 0 && <div className="attachment-list">{attachments.map(item => <span className="attachment-chip" key={item.id}><Icon name="file" size={14} /><span>{item.filename}</span><span className="ready-dot" aria-label={item.status === 'awaiting_processing' ? 'Awaiting processing' : item.status} /><button aria-label={`Remove ${item.filename}`} onClick={() => void removeAttachment(item)} disabled={busy}><Icon name="close" size={13} /></button></span>)}{attachments.some(item => item.status === 'awaiting_processing') && <span className="processing-chip">Awaiting processing</span>}</div>}<div className="composer-card"><textarea ref={promptRef} value={prompt} onChange={event => setPrompt(event.target.value)} onKeyDown={onPromptKey} placeholder={mode === 'Ask' ? 'Ask a question about your matter…' : mode === 'Draft' ? 'Describe what you’d like to draft…' : 'What would you like to understand about this document?'} rows={2} aria-label="Write a message"/><div className="composer-tools"><div className="composer-left"><div className="mode-select" role="group" aria-label="Choose workflow">{(['Ask', 'Draft', 'Summary'] as Mode[]).map(item => <button key={item} className={mode === item ? 'mode-active' : ''} onClick={() => setMode(item)}>{item}</button>)}</div><span className="tool-divider"/><button className="tool-button" onClick={() => fileRef.current?.click()} disabled={busy}><Icon name="attach" size={16} /><span>Attach</span></button><input ref={fileRef} className="visually-hidden" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" multiple onChange={event => void handleFiles(event)}/>{documentLibrary.some(document => document.status === 'ready') && <select className="jurisdiction-select" aria-label="Attach an existing document" value="" onChange={event => void attachExistingDocument(event.target.value)}><option value="">Existing document</option>{documentLibrary.filter(document => document.status === 'ready').map(document => <option key={document.id} value={document.id}>{document.filename}</option>)}</select>}<select className="jurisdiction-select" aria-label="Jurisdiction" value={jurisdiction} onChange={event => void changeJurisdiction(event.target.value)}><option value="">Jurisdiction</option><option>US Federal</option><option>California</option><option>New York</option><option>Texas</option><option>Other / specify in prompt</option></select></div><button className={`send-button ${prompt.trim() && !busy ? 'send-ready' : ''}`} aria-label="Send message" disabled={!prompt.trim() || busy} onClick={() => void send()}><Icon name="send" size={17}/></button></div></div><div className="composer-foot"><span><Icon name="shield" size={13}/> AI responses use the configured OpenAI model; uploaded text is extracted locally.</span><span>Enter to send <kbd>↵</kbd></span></div></div>
      </div>
    </main>
    {notice && <div className="toast" role="status"><span className="toast-check"><Icon name="check" size={14}/></span>{notice}<button aria-label="Dismiss notification" onClick={() => setNotice('')}><Icon name="close" size={14}/></button></div>}
  </div>
}

export default App
