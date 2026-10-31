# LegalLens Backend To-Do

**Status:** Initial backend implementation delivered; this plan remains the scope and decision log.  
**Scope:** Standalone FastAPI backend for persistence, conversation/document APIs, upload validation, and API documentation. No frontend integration, orchestration, or AI implementation in this phase.

## Goal and boundaries

- [ ] Build a backend that can run independently and expose stable, documented HTTP APIs for a future frontend integration.
- [ ] Use Python with FastAPI and UV, consistent with the BRD.
- [ ] Keep HTTP routing, validation, application services, persistence, and file storage behind clear module boundaries.
- [ ] Persist users/workspace ownership fields, conversations, messages/transactions, document metadata, and status using the database selected below.
- [ ] Accept conversation turns and store them, but do not invent or generate assistant answers. Return a clear `stored` / `awaiting_orchestration` status until an orchestration service exists.
- [ ] Accept and safely store eligible PDF/DOCX uploads, but do not claim they are parsed, OCR'd, indexed, or ready for RAG. Document status should remain `uploaded` / `awaiting_processing` until a later processing layer exists.
- [ ] Leave the existing React frontend and its mock-data behavior unchanged in this phase.

## Decisions and assumptions to review

- [ ] **Conversation database:** The architecture names “Escalate” as the conversation database. Confirm the exact database product/technology, connection approach, and local development setup before selecting a persistence driver. Keep a repository boundary so the implementation can honor the confirmed choice without coupling routes to it.
- [ ] **Demo identity:** BRD assumes a single-user demonstration account or isolated session and defers authentication. Propose an explicit development-only demo identity, with ownership checks in service methods and a documented warning that it is not multi-user authentication.
- [ ] **Document storage:** Confirm whether local, ignored development storage is acceptable for the standalone backend. Keep binary storage separate from conversation metadata and return only opaque document IDs.
- [ ] **NCC endpoint:** The architecture requires an NCC endpoint but does not define what NCC means or its upstream contract. Include the route boundary and OpenAPI shape only after its purpose and required fields are agreed; until then, use a clearly documented `501 capability_not_configured` response rather than guessing its behavior.
- [ ] **Turn creation behavior:** A stored user turn has no assistant result without orchestration. Keep this explicit in response status and API documentation; do not return placeholder legal advice.
- [ ] **CORS and serving mode:** Configure local development origins through settings; do not use unrestricted production CORS defaults.

## Proposed API contracts

Use `/api/v1`, JSON for API payloads, multipart form data for uploads, ISO-8601 UTC timestamps, UUID identifiers, and a shared error envelope. The exact schemas should be published by FastAPI OpenAPI and kept in examples.

### Health and service metadata

- [ ] `GET /health` → `200 { "status": "ok" }`; process liveness only, with no sensitive configuration.
- [ ] `GET /ready` → `200 { "status": "ready", "dependencies": { ... } }` when required storage is reachable, otherwise `503`; reveal no connection strings or secrets.

### Conversations and turns

- [ ] `POST /api/v1/conversations`
  - Request: `{ "title": "Optional title" }`
  - Response `201`: `{ "id": "uuid", "title": "New conversation", "created_at": "...", "updated_at": "...", "jurisdiction": null, "document_ids": [], "message_count": 0 }`
- [ ] `GET /api/v1/conversations?cursor={opaque}&limit=20`
  - Response `200`: `{ "items": [ConversationSummary], "next_cursor": null }`; validate and cap `limit`.
- [ ] `GET /api/v1/conversations/{conversation_id}`
  - Response `200`: `{ ...Conversation, "messages": [Message] }`; messages ordered by creation time.
- [ ] `PATCH /api/v1/conversations/{conversation_id}`
  - Request: `{ "title": "...", "jurisdiction": "US Federal" }` with at least one allowed field.
  - Response `200`: updated conversation; reject unknown fields and invalid jurisdiction lengths.
- [ ] `DELETE /api/v1/conversations/{conversation_id}`
  - Response `204`; implement an explicit deletion policy for associated messages, document associations, and stored files. Do not imply external-provider deletion.
- [ ] `POST /api/v1/chat/turns`
  - Request: `{ "conversation_id": "uuid or null", "message": { "content": "...", "workflow": "ask|draft|summary", "jurisdiction": "optional", "document_ids": ["uuid"] } }`
  - Response `202`: `{ "turn_id": "uuid", "conversation_id": "uuid", "user_message": Message, "status": "awaiting_orchestration", "assistant_message": null }`.
  - If `conversation_id` is null, create a conversation. Persist the user message and transaction/status atomically. No answer generation in this phase.

### Documents

- [ ] `POST /api/v1/documents` (multipart `file`, optional `conversation_id`)
  - Accept PDF and DOCX only; enforce configurable 25 MB default; validate extension and file signature, generate opaque names, and store outside source control.
  - Response `202`: `{ "id": "uuid", "filename": "original-name.pdf", "media_type": "application/pdf", "size_bytes": 1234, "status": "awaiting_processing", "conversation_id": "uuid or null", "created_at": "..." }`.
- [ ] `GET /api/v1/documents/{document_id}/status`
  - Response `200`: `{ "id": "uuid", "status": "awaiting_processing|failed|deleted", "detail": null }`; never label a stored file as extracted or indexed.
- [ ] `DELETE /api/v1/documents/{document_id}`
  - Response `204`; verify ownership, remove binary and metadata safely, and handle missing/partially deleted files idempotently.

### NCC and exports

- [ ] Reserve `/api/v1/ncc` pending the NCC definition; document a stable error shape for unavailable/unconfigured functionality instead of a fabricated successful response.
- [ ] Defer `POST /api/v1/exports` until the desired export inputs and formats are defined. If included in the first backend release, return an explicit `501 export_not_configured` rather than pretending to create a DOCX/PDF.

### Shared error response

- [ ] Use a consistent shape such as `{ "error": { "code": "validation_error", "message": "The request could not be accepted.", "request_id": "...", "details": [] } }`.
- [ ] Cover at minimum `400` malformed request, `401/403` when auth is enabled, `404` not found, `413` upload too large, `415` unsupported media, `422` schema validation, `429` request limit, and `500` safe generic error.
- [ ] Do not reveal stack traces, disk paths, credentials, SQL, or raw file contents in errors.

## Implementation sequence after approval

### 1. Service foundation

- [ ] Create a standalone `backend/` Python project with `pyproject.toml`, UV setup, FastAPI entry point, settings loaded from environment, and `.env.example` containing placeholders only.
- [ ] Add versioned API router, request/response schemas, structured logging with request IDs, centralized exception mapping, and configurable CORS.
- [ ] Add startup/shutdown lifecycle handling and health/readiness endpoints.

### 2. Persistence and conversation APIs

- [ ] Implement the confirmed database connection and schema/migrations for conversation, message/transaction, and document metadata records.
- [ ] Add repository/service functions with ownership filters at every read, update, and delete boundary.
- [ ] Implement conversation CRUD, cursor pagination, and `/chat/turns`; ensure turn persistence and status updates are transaction-safe.
- [ ] Keep the interface replaceable for a later orchestration worker/API without importing orchestration code into FastAPI routes.

### 3. Document API and safe local storage

- [ ] Add configurable upload validation, safe temporary-file handling, unique file keys, file metadata persistence, and cleanup on failed database writes.
- [ ] Implement document status and deletion routes. Keep document binary content out of API logs and generic conversation responses.
- [ ] Mark upload as awaiting processing; later ingestion can own OCR, layout extraction, chunking, and indexing.

### 4. API documentation and operational handoff

- [ ] Add a backend README with UV install/run commands, environment variables, database setup, local data locations, and current capability limits.
- [ ] Add OpenAPI examples and a concise contract document for frontend integration, including status codes, errors, pagination, and upload limits.
- [ ] Document deletion/retention behavior, demo identity limitations, and which routes intentionally return `501` until NCC/export behavior is defined.

## Security, privacy, and quality requirements

- [ ] Keep secrets out of source control; load credentials from environment or an approved secret source.
- [ ] Use synthetic/public example content only. Never log prompts, message bodies, document contents, or secrets.
- [ ] Apply strict file size/type validation, opaque storage keys, path traversal protection, and per-record ownership checks.
- [ ] Make storage, retention, and deletion configurable/documented; make no broad confidentiality or complete-deletion claims before the actual database and storage behavior is known.
- [ ] Keep runtime errors safe and useful, and make readiness reflect real storage availability.
- [ ] After approval and implementation, verify API contracts and core behavior with automated tests using temporary data and synthetic files; keep external AI calls absent.

## Definition of done

- [ ] Backend starts independently using documented UV commands and serves `/docs` and OpenAPI.
- [ ] Conversation history and message transactions persist to the confirmed database and can be listed, retrieved, updated where allowed, and deleted.
- [ ] The turn endpoint stores user input and reports that orchestration is pending without producing an AI answer.
- [ ] Upload endpoints safely accept only allowed files and sizes, persist metadata, return truthful pending-processing status, and support deletion.
- [ ] Validation, not-found, oversized, unsupported file, and internal error responses follow the shared error contract.
- [ ] No route depends on the React UI, orchestration, or AI layer.
- [ ] NCC, export, and unresolved database choices are either confirmed and implemented to contract or clearly left unavailable with documented responses.
