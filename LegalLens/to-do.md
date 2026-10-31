# LegalLens Frontend To-Do

**Status:** Proposal for review  
**Scope:** User-facing UI only. No backend, orchestration, or AI implementation. Use realistic local mock data and browser state so the experience can be explored before services exist.

## Product and UX baseline

- [ ] Treat LegalLens as a calm, professional workspace for legal professionals: light warm-neutral surfaces, deep ink text, restrained navy/teal accents, clear typography, and deliberate spacing. Avoid a dark-first interface and avoid copying another product's branding.
- [ ] Use a familiar chat workspace pattern: persistent conversation sidebar, focused conversation canvas, and composer anchored at the bottom of the active conversation.
- [ ] Keep workflow, document context, and jurisdiction visible so users can tell what the assistant is being asked to do and what material it can use.
- [ ] Make outputs easy to inspect and revise. Show citations and source locations as first-class UI elements; label generated drafts as editable and requiring professional review.
- [ ] Make every important state legible: new/empty chat, selected conversation, upload in progress, document ready/failed, assistant working, response with citations, and recoverable error.

## Proposed frontend foundation

- [ ] After approval, create a self-contained `frontend/` app using React, TypeScript, and Vite, with small reusable components and CSS design tokens. This is a proposed implementation choice; no frontend scaffold exists yet.
- [ ] Keep mock data and UI state behind a small client-side data layer so it can later be replaced by API calls without coupling the components to a backend.
- [ ] Use local, synthetic legal examples only. Do not put real client or confidential matter information in fixtures.
- [ ] Add only the packages needed for the interface; keep the initial app straightforward to run locally.

## Implementation plan

### 1. App shell and visual system

- [ ] Establish responsive page layout, typography, spacing, colors, borders, elevation, focus rings, and button/input styles.
- [ ] Build the application header with LegalLens identity, current workspace context, and accessible account/help affordances (mocked where needed).
- [ ] Build a collapsible conversation sidebar with New chat, search/filter, recent conversations grouped by date, selected state, and a compact mobile drawer.
- [ ] Add clear hover, focus, active, disabled, and loading states; ensure controls are keyboard-operable and contrast is readable.

### 2. Conversation and composer

- [ ] Build the conversation canvas with welcome/empty state, user and assistant message styles, timestamps/status where useful, and a readable long-answer measure.
- [ ] Build a prompt composer with multiline input, submit action, workflow selector (**Ask**, **Draft**, **Summary**), and document attachment affordance.
- [ ] Show selected documents and removable attachment chips near the composer; communicate accepted formats and the proposed 25 MB limit from the BRD.
- [ ] Include jurisdiction/context entry for legal questions and make the active context visible without crowding the prompt area.
- [ ] Mock submit, working/streaming, completion, retry, and error states. Keep the demo deterministic and clearly simulated.

### 3. Document interaction

- [ ] Create a document picker/drop zone with type/size validation feedback, upload progress, processing state, ready state, and extraction failure state.
- [ ] Show document identity and processing status in the active conversation so users know which source is in scope.
- [ ] Use mock statuses only; do not imply an actual upload or scan has taken place.

### 4. Results and legal-work affordances

- [ ] Render document-grounded answers with inline citation markers and a source panel showing page/section and a short excerpt from fixtures.
- [ ] Create a source-preview interaction so selecting a citation reveals the associated mock excerpt and location.
- [ ] Create a structured summary presentation that remains readable for longer documents.
- [ ] Create a draft presentation with editable content, visible placeholders/assumptions, a “Draft — review before use” label, and mocked copy/export controls.
- [ ] Add lightweight response feedback controls and clear confirmation before destructive conversation deletion.

### 5. Mock data and interactions

- [ ] Seed a small set of synthetic conversations covering a general legal question, a document-grounded Ask, a contract Summary, and a Draft with missing-information placeholders.
- [ ] Implement client-side conversation selection, new conversation, search/filter, prompt submission, workflow switching, attachment selection/removal, citation preview, draft editing, and delete confirmation.
- [ ] Keep data in memory or local browser storage for the demo; make reset behavior easy to understand.
- [ ] Keep mock actions clearly local: no network calls, no real model output, no real persistence guarantee, and no functioning document export unless separately approved.

### 6. Responsive polish and handoff

- [ ] Check desktop, tablet, and narrow mobile layouts, including sidebar open/closed and composer visibility.
- [ ] Review keyboard navigation, visible focus, semantic labels, status announcements, and reduced-motion behavior.
- [ ] Add a concise `frontend/README.md` with install/run instructions and a note that all interactions use mock data.
- [ ] Walk through the main demo path: open seeded conversation → inspect citation → start a new chat → choose a workflow → attach a sample document → submit → inspect result → edit draft or delete conversation.

## Proposed acceptance checklist

- [ ] A user can understand the three workflows and start each from the same conversation workspace.
- [ ] The sidebar makes prior conversations easy to scan, search, open, and delete.
- [ ] The composer clearly communicates workflow, prompt, attachment, and jurisdiction/context.
- [ ] Mock document states and response states are coherent, including errors and unsupported/extraction-failure cases.
- [ ] Ask and Summary examples make source support inspectable; Draft examples visibly mark editable placeholders and review expectations.
- [ ] The UI remains usable on desktop and mobile, supports keyboard navigation, and uses a light professional visual theme.
- [ ] The frontend makes no claim that a backend, AI model, real document processing, or persistent storage is connected.

## Explicitly out of scope for this UI pass

- Backend/API implementation, NCC endpoint wiring, authentication, orchestration, model calls, RAG/search/indexing, OCR, database integration, real document storage, and real export generation.
- Choosing a production model provider, vector database, or conversation database technology.
- Production security/compliance claims or use of live client data.
