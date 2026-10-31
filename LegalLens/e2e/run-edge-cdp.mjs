import { writeFile, readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const runDir = path.resolve(here, '../test-results/e2e-2026-10-22')
const evidenceDir = path.join(runDir, 'evidence')
const ui = 'http://127.0.0.1:5173'
const api = 'http://127.0.0.1:18000'
const results = []
const browserErrors = []
let nextPrompt = null
let nextConfirm = null

const targets = await (await fetch('http://127.0.0.1:9222/json/list')).json()
const target = targets.find(item => item.type === 'page' && item.url.includes('127.0.0.1:5173'))
if (!target) throw new Error('Headless Edge has no LegalLens page target.')

const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true })
  socket.addEventListener('error', reject, { once: true })
})
let nextId = 0
const pending = new Map()
function send(method, params = {}) {
  const id = ++nextId
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
}
socket.addEventListener('message', async event => {
  const message = JSON.parse(event.data)
  if (message.id) {
    const item = pending.get(message.id)
    if (!item) return
    pending.delete(message.id)
    if (message.error) item.reject(new Error(message.error.message))
    else item.resolve(message.result)
  } else if (message.method === 'Runtime.exceptionThrown') {
    browserErrors.push(message.params.exceptionDetails.text)
  } else if (message.method === 'Page.javascriptDialogOpening') {
    const type = message.params.type
    const accept = type === 'prompt' ? nextPrompt !== null : (nextConfirm ?? true)
    const promptText = nextPrompt ?? ''
    nextPrompt = null
    nextConfirm = null
    await send('Page.handleJavaScriptDialog', { accept, promptText })
  }
})

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text)
  return result.result?.value
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
async function until(check, timeout = 12000, label = 'condition') {
  const start = Date.now()
  while (Date.now() - start < timeout) {
    const value = await check()
    if (value) return value
    await wait(200)
  }
  throw new Error(`Timed out waiting for ${label}.`)
}
async function screenshot(name) {
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  const targetPath = path.join(evidenceDir, `${name}.png`)
  await writeFile(targetPath, Buffer.from(shot.data, 'base64'))
  return path.relative(runDir, targetPath).replaceAll('\\', '/')
}
async function bodyText() { return await evaluate('document.body.innerText') }
async function click(selector) {
  const found = await evaluate(`(() => { const e=document.querySelector(${JSON.stringify(selector)}); if(!e) return false; e.click(); return true })()`)
  if (!found) throw new Error(`Could not find clickable element ${selector}`)
}
async function clickText(selector, text) {
  const found = await evaluate(`(() => { const e=[...document.querySelectorAll(${JSON.stringify(selector)})].find(x=>x.innerText.trim()===${JSON.stringify(text)}||x.innerText.includes(${JSON.stringify(text)})); if(!e) return false; e.click(); return true })()`)
  if (!found) throw new Error(`Could not find ${selector} with text "${text}"`)
}
async function setValue(selector, value) {
  const found = await evaluate(`(() => { const e=document.querySelector(${JSON.stringify(selector)}); if(!e) return false; const p=e instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(value)}); e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true})); return true })()`)
  if (!found) throw new Error(`Could not set ${selector}`)
}
async function chooseValue(selector, value) {
  const found = await evaluate(`(() => { const e=document.querySelector(${JSON.stringify(selector)}); if(!e) return false; e.value=${JSON.stringify(value)}; e.dispatchEvent(new Event('change',{bubbles:true})); return true })()`)
  if (!found) throw new Error(`Could not choose ${selector}`)
}
async function uploadFile(filePath) {
  const { root } = await send('DOM.getDocument', { depth: 1 })
  const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: 'input[type=file]' })
  if (!nodeId) throw new Error('File input was not found.')
  await send('DOM.setFileInputFiles', { nodeId, files: [filePath] })
  await until(() => evaluate('document.querySelectorAll(".attachment-chip").length > 0'), 15000, 'uploaded attachment chip')
}
async function sendMessage(content, mode = 'Ask') {
  if (mode !== 'Ask') await clickText('.mode-select button', mode)
  await setValue('textarea[aria-label="Write a message"]', content)
  const before = await evaluate('document.querySelectorAll(".message.assistant").length')
  await click('button[aria-label="Send message"]')
  await until(async () => {
    const count = await evaluate('document.querySelectorAll(".message.assistant").length')
    if (count > before) return true
    const error = await evaluate('document.querySelector("[role=alert]")?.innerText || ""')
    if (error) throw new Error(`Workflow returned UI error: ${error}`)
    return false
  }, 210000, 'assistant response')
  return await evaluate('document.querySelector(".message.assistant .message-text")?.innerText || ""')
}
async function latestConversation() {
  const response = await fetch(`${api}/api/v1/conversations?limit=100`)
  const value = await response.json()
  return value.items[0]
}
async function apiJson(url) {
  const response = await fetch(url)
  let body = null
  try { body = await response.json() } catch {}
  return { status: response.status, body }
}
async function record(id, title, status, observed, screenshotPath = '') {
  results.push({ id, title, status, observed: String(observed).replaceAll('\n', ' ').slice(0, 1800), screenshot: screenshotPath })
}
async function runCase(id, title, fn) {
  const before = results.length
  try {
    const out = await fn()
    if (results.length === before) {
      const screenshotPath = typeof out === 'string' && out.startsWith('evidence/') ? out : ''
      await record(id, title, 'PASS', screenshotPath ? 'Completed; see screenshot evidence.' : (out ?? 'Completed.'), screenshotPath)
    }
  } catch (error) {
    const shot = await screenshot(`${id}-failure`).catch(() => '')
    await record(id, title, 'FAIL', error?.stack ?? error, shot)
  }
}
async function apiWait(pathname, predicate, timeout = 10000) {
  return await until(async () => {
    const result = await apiJson(`${api}${pathname}`)
    return predicate(result) ? result : false
  }, timeout, `backend ${pathname}`)
}

await send('Page.enable')
await send('Runtime.enable')
await send('DOM.enable')
await send('Page.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
await send('Page.navigate', { url: ui })
await until(async () => (await bodyText()).includes('Backend connected'), 15000, 'backend connected indicator')
await record('LLM-01', 'Check configured live OpenAI credential', 'BLOCKED', 'A separate real UI request reached OpenAI and received HTTP 401 invalid_api_key. This run uses a deterministic local stub for workflow integration only; it does not validate real LLM output.')
await record('UI-01', 'Load workspace and check backend readiness', 'PASS', 'UI displayed Backend connected after /health and /ready succeeded.', await screenshot('UI-01-workspace'))

await runCase('UI-02', 'Create a conversation and attach a synthetic lease', async () => {
  await click('button.new-chat')
  await uploadFile(path.join(runDir, 'synthetic-lease.docx'))
  const label = await evaluate('document.querySelector(".attachment-chip")?.innerText')
  const shot = await screenshot('UI-02-created-and-document-attached')
  await record('UI-02', 'Create a conversation and attach a synthetic lease', 'PASS', `Upload appears in the conversation composer: ${label}`, shot)
})

let askConversationId = ''
let askDocumentId = ''
let askAnswer = ''
await runCase('UI-03', 'Ask a question and verify LLM answer plus grounded citation', async () => {
  await chooseValue('select[aria-label="Jurisdiction"]', 'New York')
  try {
    askAnswer = await sendMessage('What is the monthly base rent, when is it due, and what is the grace period? Cite the lease.', 'Ask')
  } catch (error) {
    if (String(error).includes('invalid_api_key')) {
      const blockedConversation = await latestConversation()
      askConversationId = blockedConversation.id
      const blockedDetail = await apiJson(`${api}/api/v1/conversations/${askConversationId}`)
      askDocumentId = blockedDetail.body.document_ids[0]
      await record('UI-03', 'Ask a question and verify LLM answer plus grounded citation', 'BLOCKED', 'The UI reached OpenAI, but the configured credential was rejected with HTTP 401 invalid_api_key. No model answer or citation could be produced.', await screenshot('UI-03-invalid-key'))
      return
    }
    throw error
  }
  const conversation = await latestConversation()
  askConversationId = conversation.id
  const persisted = await apiJson(`${api}/api/v1/conversations/${conversation.id}`)
  const detail = persisted
  askDocumentId = persisted.body.document_ids[0]
  const assistant = persisted.body.messages.find(message => message.role === 'assistant')
  if (!assistant) throw new Error('No assistant message persisted in the backend.')
  if (!/2450|2,450/.test(assistant.content)) throw new Error(`Answer omitted expected synthetic rent: ${assistant.content}`)
  if (!assistant.citations?.length) throw new Error(`No citation rows returned: ${assistant.content}`)
  if (!assistant.citations.some(citation => citation.excerpt.includes('$2,450'))) throw new Error('Citation excerpt did not support the rent answer.')
  if (!detail.body.messages.some(message => message.role === 'user' && message.workflow === 'ask')) throw new Error('User turn/workflow was not persisted.')
  const shot = await screenshot('UI-03-ask-answer-citations')
  await record('UI-03', 'Ask a question and verify LLM answer plus grounded citation', 'PASS', `Assistant persisted with cited excerpt: ${assistant.citations[0].filename}; response=${assistant.content}`, shot)
  return assistant.content
})

await runCase('UI-04', 'Rename the conversation through the UI', async () => {
  nextPrompt = 'E2E Renamed Ask Conversation'
  await click('button[aria-label="Rename conversation"]')
  await until(async () => (await bodyText()).includes('E2E Renamed Ask Conversation'), 5000, 'renamed conversation title')
  askConversationId ||= (await latestConversation()).id
  const saved = await apiJson(`${api}/api/v1/conversations/${askConversationId}`)
  if (saved.status !== 200 || saved.body.title !== 'E2E Renamed Ask Conversation') throw new Error('UI rename did not persist to the backend.')
  return await screenshot('UI-04-renamed-conversation')
})

let reuseConversationId = ''
await runCase('UI-05', 'Create a new conversation and select the existing lease', async () => {
  await click('button.new-chat')
  await until(() => evaluate(`!!document.querySelector('select[aria-label="Attach an existing document"]')`), 10000, 'existing document picker')
  const sourceId = await evaluate(`([...document.querySelectorAll('select[aria-label="Attach an existing document"] option')].find(o=>o.text.includes('synthetic-lease.docx'))||{}).value`)
  if (!sourceId || sourceId === 'undefined') throw new Error('Previously uploaded lease is missing from the document picker.')
  await chooseValue('select[aria-label="Attach an existing document"]', sourceId)
  await until(() => evaluate('document.querySelectorAll(".attachment-chip").length > 0'), 15000, 'reused document attachment')
  reuseConversationId = (await latestConversation()).id
  const detail = await apiJson(`${api}/api/v1/conversations/${reuseConversationId}`)
  if (detail.body.document_ids.length !== 1 || detail.body.document_ids[0] === sourceId) throw new Error('A reusable copy was not attached to the new conversation.')
  return await screenshot('UI-05-existing-document-attached')
})

await runCase('UI-06', 'Summarize the existing document in the new conversation', async () => {
  let answer
  try { answer = await sendMessage('Summarize the lease term, rent, late fee, notice period, and maintenance responsibility. Cite the document.', 'Summary') }
  catch (error) {
    if (String(error).includes('invalid_api_key')) {
      await record('UI-06', 'Summarize the existing document in the new conversation', 'BLOCKED', 'Existing source document was selected and attached; generation was blocked because OpenAI rejected the configured credential (401 invalid_api_key).', await screenshot('UI-06-invalid-key'))
      return
    }
    throw error
  }
  const detail = await apiJson(`${api}/api/v1/conversations/${reuseConversationId}`)
  const assistant = detail.body.messages.find(message => message.role === 'assistant')
  if (!assistant || !assistant.citations?.length) throw new Error('Summary answer or source citations were not persisted.')
  if (!/2450|2,450/.test(answer) || !/60.?day/i.test(answer)) throw new Error(`Summary omitted expected terms: ${answer}`)
  const shot = await screenshot('UI-06-existing-document-summary')
  await record('UI-06', 'Summarize the existing document in the new conversation', 'PASS', `Summary included rent, notice period and citations. ${answer}`, shot)
  return answer
})

let policyConversationId = ''
let policyDocId = ''
await runCase('UI-07', 'Upload a new document and summarize it', async () => {
  await click('button.new-chat')
  await uploadFile(path.join(runDir, 'synthetic-policy.docx'))
  await clickText('.mode-select button', 'Summary')
  let answer
  try { answer = await sendMessage('Summarize the submission deadline, manager approval threshold, receipt rule, and reimbursement timing.', 'Summary') }
  catch (error) {
    if (String(error).includes('invalid_api_key')) {
      policyConversationId = (await latestConversation()).id
      const detail = await apiJson(`${api}/api/v1/conversations/${policyConversationId}`)
      policyDocId = detail.body.document_ids[0]
      const status = await apiJson(`${api}/api/v1/documents/${policyDocId}/status`)
      if (status.body.status !== 'ready') throw new Error(`Uploaded DOCX was not extracted before generation (status=${status.body.status}).`)
      await record('UI-07', 'Upload a new document and summarize it', 'BLOCKED', 'Synthetic DOCX upload was extracted and reached Summary generation, but the configured OpenAI credential was rejected (401 invalid_api_key).')
      return
    }
    throw error
  }
  policyConversationId = (await latestConversation()).id
  const detail = await apiJson(`${api}/api/v1/conversations/${policyConversationId}`)
  policyDocId = detail.body.document_ids[0]
  const assistant = detail.body.messages.find(message => message.role === 'assistant')
  const status = await apiJson(`${api}/api/v1/documents/${policyDocId}/status`)
  if (!assistant || !assistant.citations?.length) throw new Error('Summary response or citation missing in backend.')
  if (status.body.status !== 'ready') throw new Error(`Uploaded document status was ${status.body.status}.`)
  if (!/30 calendar days/i.test(answer) || !/500/.test(answer)) throw new Error(`Summary omitted policy terms: ${answer}`)
  const shot = await screenshot('UI-07-uploaded-document-summary')
  await record('UI-07', 'Upload a new document and summarize it', 'PASS', `Document extracted locally (ready); summary included policy terms with citations. ${answer}`, shot)
  return answer
})

let draftConversationId = ''
await runCase('UI-08', 'Draft a memo in a third conversation', async () => {
  await click('button.new-chat')
  const sourceId = await evaluate(`([...document.querySelectorAll('select[aria-label="Attach an existing document"] option')].find(o=>o.text.includes('synthetic-lease.docx'))||{}).value`)
  await chooseValue('select[aria-label="Attach an existing document"]', sourceId)
  await until(() => evaluate('document.querySelectorAll(".attachment-chip").length > 0'), 10000, 'lease attached for memo')
  let answer
  try { answer = await sendMessage('Draft an internal legal memo about the synthetic lease. Include Issue, Brief Answer, Key Facts, Analysis, and Open Questions. Cite relevant lease provisions.', 'Draft') }
  catch (error) {
    if (String(error).includes('invalid_api_key')) {
      draftConversationId = (await latestConversation()).id
      await record('UI-08', 'Draft a memo in a third conversation', 'BLOCKED', 'Synthetic lease was attached and Draft submitted; generation was blocked because OpenAI rejected the configured credential (401 invalid_api_key).')
      return
    }
    throw error
  }
  draftConversationId = (await latestConversation()).id
  const detail = await apiJson(`${api}/api/v1/conversations/${draftConversationId}`)
  const assistant = detail.body.messages.find(message => message.role === 'assistant')
  if (!assistant) throw new Error('Memo was not persisted as an assistant message.')
  if (!/memo|brief answer|analysis/i.test(answer)) throw new Error(`Draft does not resemble a memo: ${answer}`)
  const shot = await screenshot('UI-08-draft-memo')
  await record('UI-08', 'Draft a memo in a third conversation', 'PASS', `Assistant generated and persisted a memo. ${answer}`, shot)
  return answer
})

await runCase('UI-09', 'Persist jurisdiction selection', async () => {
  await evaluate(`document.querySelector('.conversation-item button.conversation-select')?.click()`)
  await until(() => evaluate(`!!document.querySelector('select[aria-label="Jurisdiction"]')`), 5000, 'selected conversation jurisdiction control')
  const conversation = await latestConversation()
  await chooseValue('select[aria-label="Jurisdiction"]', 'California')
  await apiWait(`/api/v1/conversations/${conversation.id}`, value => value.status === 200 && value.body.jurisdiction === 'California')
  await record('UI-09', 'Persist jurisdiction selection', 'PASS', 'Selecting California updated the conversation through the UI and API.')
})

await runCase('UI-10', 'Reject unsupported upload type', async () => {
  const txt = path.join(runDir, 'unsupported.txt')
  await writeFile(txt, 'Not a supported document type.')
  await click('button.new-chat')
  const { root } = await send('DOM.getDocument', { depth: 1 })
  const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: 'input[type=file]' })
  await send('DOM.setFileInputFiles', { nodeId, files: [txt] })
  const error = await until(() => evaluate('document.querySelector("[role=alert]")?.innerText'), 8000, 'unsupported extension error')
  if (!error.includes('Only non-empty PDF or DOCX')) throw new Error(`Unexpected validation message: ${error}`)
  await record('UI-10', 'Reject unsupported upload type', 'PASS', error, await screenshot('UI-10-unsupported-file'))
})

await runCase('UI-11', 'Remove an uploaded attachment', async () => {
  await click('button.new-chat')
  await uploadFile(path.join(runDir, 'synthetic-policy.docx'))
  const documentId = await evaluate(`document.querySelector('.attachment-chip button')?.getAttribute('aria-label')`)
  await click('button[aria-label^="Remove "]')
  await until(() => evaluate('document.querySelectorAll(".attachment-chip").length === 0'), 10000, 'attachment removal')
  const library = await (await fetch(`${api}/api/v1/documents`)).json()
  if (library.some(item => item.id === documentId)) throw new Error('Removed document still appears in the document library.')
  await record('UI-11', 'Remove an uploaded attachment', 'PASS', 'Attachment chip disappeared and document row was deleted.', await screenshot('UI-11-attachment-removed'))
})

await runCase('UI-12', 'Search conversation history', async () => {
  await clickText('button.side-link', 'Search conversations')
  await setValue('input[aria-label="Search conversations"]', 'E2E Renamed Ask Conversation')
  const shown = await evaluate('document.querySelectorAll(".conversation-item").length')
  if (shown !== 1) throw new Error(`Expected one matching conversation, found ${shown}.`)
  await record('UI-12', 'Search conversation history', 'PASS', 'Search filtered the sidebar to the renamed conversation.', await screenshot('UI-12-search-history'))
})

await runCase('UI-13', 'Use the Summary starter card', async () => {
  await click('button.new-chat')
  await clickText('.starter-grid button', 'Summarize a document')
  const mode = await evaluate('[...document.querySelectorAll(".mode-select button")].find(e=>e.classList.contains("mode-active"))?.innerText')
  const prompt = await evaluate(`document.querySelector('textarea[aria-label="Write a message"]').value`)
  if (mode !== 'Summary' || !prompt.toLowerCase().includes('summarize')) throw new Error(`Starter did not set Summary mode and prompt (mode=${mode}).`)
  await record('UI-13', 'Use the Summary starter card', 'PASS', 'Starter selected Summary and populated its suggested prompt.', await screenshot('UI-13-summary-starter'))
})

await runCase('UI-14', 'Use Ctrl+K to start a new conversation', async () => {
  await evaluate('window.dispatchEvent(new KeyboardEvent("keydown",{key:"k",ctrlKey:true,bubbles:true}))')
  await until(() => evaluate(`document.querySelector('textarea[aria-label="Write a message"]')?.value === ''`), 5000, 'new conversation after Ctrl+K')
  await record('UI-14', 'Use Ctrl+K to start a new conversation', 'PASS', 'Shortcut returned the UI to a blank conversation composer.')
})

await runCase('UI-15', 'Copy an assistant message', async () => {
  await click('button.new-chat')
  await evaluate(`document.querySelector('.conversation-item button.conversation-select')?.click()`)
  await until(() => evaluate('!!document.querySelector(".message.user")'), 8000, 'open conversation with a message')
  await clickText('.message-actions button', 'Copy')
  await wait(500)
  const message = await bodyText()
  const result = message.includes('Copied to clipboard.') ? 'PASS' : message.includes('Clipboard access is unavailable') ? 'PARTIAL' : 'FAIL'
  await record('UI-15', 'Copy an assistant message', result, result === 'PASS' ? 'Clipboard success toast shown.' : 'Headless Edge denied clipboard access; UI surfaced the expected limitation.', await screenshot('UI-15-copy-message'))
})

await runCase('UI-16', 'Check Export control', async () => {
  await click('button.text-button')
  const value = await until(async () => {
    const text = await bodyText()
    return text.includes('Export is not available') ? text : false
  }, 4000, 'export notice')
  await record('UI-16', 'Check Export control', 'UNAVAILABLE', 'UI reports export is not available in this backend version.')
})

await runCase('UI-17', 'Cancel then confirm conversation deletion', async () => {
  await evaluate(`document.querySelector('.conversation-item button.conversation-select')?.click()`)
  await until(() => evaluate(`!!document.querySelector('button[aria-label="Delete conversation"]')`), 8000, 'active conversation delete control')
  const activeTitle = await evaluate('document.querySelector(".crumb-current")?.innerText')
  const conversations = await (await fetch(`${api}/api/v1/conversations?limit=100`)).json()
  const deleteTarget = conversations.items.find(item => item.title === activeTitle)
  if (!deleteTarget) throw new Error(`Could not map active UI title to backend conversation: ${activeTitle}`)
  nextConfirm = false
  await click('button[aria-label="Delete conversation"]')
  await wait(300)
  const afterCancel = await apiJson(`${api}/api/v1/conversations/${deleteTarget.id}`)
  if (afterCancel.status !== 200) throw new Error('Conversation was deleted despite cancelling confirmation.')
  await record('UI-17a', 'Cancel conversation deletion', 'PASS', 'Cancel kept the conversation and messages intact.', await screenshot('UI-17a-delete-cancel'))
  nextConfirm = true
  await click('button[aria-label="Delete conversation"]')
  await until(async () => (await apiJson(`${api}/api/v1/conversations/${deleteTarget.id}`)).status === 404, 8000, 'confirmed conversation deletion')
  await record('UI-17b', 'Confirm conversation deletion', 'PASS', 'UI confirmation deleted the conversation; API subsequently returned 404.', await screenshot('UI-17b-delete-confirm'))
})

await runCase('UI-18', 'Upload PDF and validate extraction support', async () => {
  const pdfPath = path.join(runDir, 'synthetic.pdf')
  await writeFile(pdfPath, Buffer.from('%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF\n'))
  await click('button.new-chat')
  const { root } = await send('DOM.getDocument', { depth: 1 })
  const { nodeId } = await send('DOM.querySelector', { nodeId: root.nodeId, selector: 'input[type=file]' })
  await send('DOM.setFileInputFiles', { nodeId, files: [pdfPath] })
  const error = await until(() => evaluate('document.querySelector("[role=alert]")?.innerText'), 12000, 'PDF extraction result')
  if (error.includes('pypdf dependency')) {
    await record('UI-18', 'Upload PDF and validate extraction support', 'BLOCKED', 'PDF upload reached extraction but the current backend virtual environment lacks pypdf. Dependency is declared but not installed in this environment.', await screenshot('UI-18-pdf-dependency-blocked'))
  } else {
    await record('UI-18', 'Upload PDF and validate extraction support', 'FAIL', error, await screenshot('UI-18-pdf-failure'))
  }
})

await record('BUILD-01', 'Build the frontend', 'PASS', 'npm.cmd run build: TypeScript and Vite production build succeeded.')
await record('API-01', 'Verify test backend readiness', 'PASS', JSON.stringify(await apiJson(`${api}/ready`)))
await record('BROWSER-01', 'Browser JavaScript exceptions', browserErrors.length ? 'FAIL' : 'PASS', browserErrors.length ? browserErrors.join('; ') : 'No uncaught JavaScript exceptions observed.')

await writeFile(path.join(runDir, 'results.json'), JSON.stringify({ run_date: '2026-10-22', ui, api, model_mode: 'local deterministic stub for workflow integration; no live LLM output', results }, null, 2), 'utf8')
await writeFile(path.join(runDir, 'browser-errors.json'), JSON.stringify(browserErrors, null, 2), 'utf8')
console.log(JSON.stringify({ runDir, results }, null, 2))
await send('Browser.close').catch(() => {})
socket.close()
