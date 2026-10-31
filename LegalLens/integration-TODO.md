# Frontend and Backend Integration TODO

## Goal

Connect the LegalLens React app to its standalone FastAPI backend while keeping the existing interface usable. The backend currently persists conversations, user turns, and uploaded document metadata/files. It does **not** generate assistant responses, process or index documents, provide citations, or perform exports.

## Current state

- The frontend in `frontend/src/App.tsx` is a single component with seeded sample conversations, mock assistant replies, mock uploads, and `localStorage` persistence under `legallens-demo-conversations`.
- The backend exposes health/readiness endpoints and versioned conversation, turn, and document APIs under `/api/v1`.
- `POST /api/v1/chat/turns` persists the user message and responds with `status: "awaiting_orchestration"` and `assistant_message: null`. It does not provide a reply.
- `POST /api/v1/documents` stores validated PDF/DOCX files and reports `awaiting_processing`; extraction and indexing are not configured.
- Backend CORS already allows the default Vite origins `http://localhost:5173` and `http://127.0.0.1:5173`.

## Integration tasks

### 1. Define the frontend/backend contract

- [x] Use `/api/v1` as the API prefix and configure the frontend API base URL through `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`.
- [x] Add TypeScript types for conversation summaries/details, messages, turn requests/responses, documents, and backend errors.
- [x] Map frontend workflow names (`Ask`, `Draft`, `Summary`) to backend values (`ask`, `draft`, `summary`); map timestamps and nullable fields.
- [x] Add an API client for JSON, multipart uploads, non-2xx responses, and the backend error envelope.
- [x] Add frontend environment documentation and confirm local Vite origins match backend `LEGALLENS_CORS_ORIGINS`.

### 2. Replace mock conversation persistence

- [x] Load the conversation list from `GET /api/v1/conversations` on startup, with loading, empty, and unavailable-backend states; check `/health` and `/ready`.
- [x] Load selected conversation details/messages from `GET /api/v1/conversations/{id}` and map role, workflow, and timestamp.
- [x] Create conversations via the first `POST /api/v1/chat/turns` and adopt its returned conversation ID.
- [x] Remove seeded conversations and replies from connected mode.
- [x] Remove `localStorage` conversation persistence; saved conversation data comes from the backend.
- [x] Follow all pages using the backend cursor and a page size of 100.

### 3. Connect sending a turn and represent backend limits accurately

- [x] Send turns with conversation ID, content, lowercase workflow, jurisdiction, and uploaded document IDs.
- [x] Adopt the returned conversation ID and refresh saved detail/list.
- [x] Remove fabricated replies/citations and identify `awaiting_orchestration` clearly.
- [x] Keep composer enabled and preserve the user's draft when the request fails.
- [x] Save jurisdiction using PATCH for existing conversations and the turn payload for a new one.
- [x] Ask/Draft/Summary requests are saved, with a clear awaiting-orchestration state; no mock response mode is retained.

### 4. Connect document attachment lifecycle

- [x] Upload PDF/DOCX files with multipart POST, associated with the active conversation when available.
- [x] Store document IDs and submit those IDs with turns.
- [x] Show upload errors and `awaiting_processing`; do not imply analysis/citations.
- [x] Read document status from the backend when loading a conversation.
- [x] Delete uploaded files through the document DELETE endpoint and refresh state.
- [x] Allow pre-conversation uploads; the first turn associates their IDs with the new conversation.

### 5. Connect conversation deletion and remaining UI actions

- [x] Delete conversations through the backend and refresh the list after success.
- [x] Mark export unavailable.
- [x] Remove citation/source affordances while the API has no assistant/citation output.
- [x] Update identity/security copy to describe shared development identity and lack of authentication.

### 6. Verify the integration

- [ ] Run the backend and frontend locally, then exercise the connected UI flows and failure states.
- [x] Add `/health` and `/ready` startup checks and UI states for empty history/backend unavailable; backend API errors are shown in the UI.
- [x] TypeScript check and production bundle pass. The sandbox blocks Vite's default esbuild config loader, so the installed Vite `runner` config loader was used for the successful production build.
- [x] Update the frontend README with environment setup, start commands, connected functionality, and backend limitations.

## Suggested implementation order

1. API types/client and Vite API configuration.
2. Conversation list/detail/create/delete backed by the API.
3. Turn submission and explicit `awaiting_orchestration` UX.
4. Uploads, document IDs, status, and deletion.
5. Remove misleading mock-only UI and update documentation.
6. End-to-end verification against the local backend.

## Decisions made

- Remove seeded mock conversations and assistant replies from the connected experience.
- Allow users to save turns while orchestration is unavailable and show the awaiting state.
- Call the backend directly using `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`; no Vite proxy is configured.

