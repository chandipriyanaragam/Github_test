# LegalLens Backend

FastAPI service for LegalLens conversations, local PDF/DOCX text extraction, lexical source retrieval, and Ask, Draft, and Summary workflows.

## Run locally

From the repository root in PowerShell, start the backend with:

```powershell
.\LegalLens\backend\run-backend.cmd
```

The launcher changes to the backend project directory, synchronizes dependencies, and starts `app.start:app` on `http://127.0.0.1:8000`. Press **Ctrl+C** in that terminal to stop it. To launch manually, first run `cd "C:\Users\Owner\TEST FOLDER\LegalLens\backend"`, then `uv sync` and `uv run uvicorn app.start:app --reload --host 127.0.0.1 --port 8000`.

Interactive API docs are at `/docs`; the OpenAPI document is at `/openapi.json`.

## Configuration

Settings load from environment variables and, for local use, an optional `.env` file beside `pyproject.toml`.

| Variable | Default | Meaning |
|---|---|---|
| `LEGALLENS_DB_PATH` | `var/legallens.db` | SQLite file path for local standalone persistence |
| `LEGALLENS_STORAGE_DIR` | `var/documents` | Directory for opaque document files |
| `LEGALLENS_MAX_UPLOAD_BYTES` | `26214400` | Maximum upload size (25 MiB) |
| `LEGALLENS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Exact browser origins allowed by CORS |
| `LEGALLENS_DEMO_USER_ID` | `demo-user` | Development-only owner scope, not authentication |
| `OPENAI_API_KEY` | empty | OpenAI credential required to classify and generate workflow responses |
| `OPENAI_MODEL` | `gpt-6-luna` | OpenAI chat model used for classification and generation |

SQLite is the current local persistence adapter. Extracted document text and citations are stored with conversation metadata. Startup upgrades databases created by the earlier API-only implementation.

## API overview

All request/response timestamps are UTC ISO-8601 values. IDs are UUID strings. Errors use:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request could not be accepted.",
    "request_id": "...",
    "details": [{ "field": "message.content", "message": "..." }]
  }
}
```

| Method and path | Purpose | Success |
|---|---|---|
| `GET /health` | Process liveness | `200` |
| `GET /ready` | SQLite and file-storage readiness | `200` or `503` |
| `POST /api/v1/conversations` | Create a conversation | `201` |
| `GET /api/v1/conversations?cursor=&limit=` | Cursor-paginated conversation list | `200` |
| `GET /api/v1/conversations/{id}` | Conversation, messages, and document IDs | `200` |
| `PATCH /api/v1/conversations/{id}` | Change title or jurisdiction | `200` |
| `DELETE /api/v1/conversations/{id}` | Delete conversation, messages, transactions, associated documents and their files | `204` |
| `POST /api/v1/chat/turns` | Classify and run Ask, Draft, or Summary; creates a conversation if omitted | `200` |
| `POST /api/v1/documents` | Validate, extract and store PDF/DOCX; optionally associate a conversation | `202` |
| `GET /api/v1/documents` | List the local document library | `200` |
| `POST /api/v1/documents/{id}/copy?conversation_id=...` | Attach a reusable copy to another conversation | `201` |
| `GET /api/v1/documents/{id}/status` | Read extraction status | `200` |
| `DELETE /api/v1/documents/{id}` | Delete document metadata and stored file | `204` |
| `POST /api/v1/ncc` | Reserved integration boundary | `501 capability_not_configured` |
| `POST /api/v1/exports` | Deferred export capability | `501 capability_not_configured` |

### Create a turn

```json
{
  "conversation_id": null,
  "message": {
    "content": "Review the termination notice period.",
    "workflow": "ask",
    "jurisdiction": "California",
    "document_ids": []
  }
}
```

The response includes `turn_id`, `conversation_id`, `user_message`, `status: "completed"`, and the generated `assistant_message` with any page citations and excerpts. Workflow failures return an error response and mark the turn failed.

### Upload a document

Send multipart form data with a `file` part and optional `conversation_id` form field. Only PDF and DOCX are accepted, up to the configured limit. The server checks extension, MIME type, file signature, and DOCX package structure, then extracts text locally. A successful response reports `status: "ready"`. Scanned PDFs are rejected because OCR is not configured.

## Current limitations

- Demo identity is not authentication or multi-user access control. Ownership scoping exists in database queries but every request currently resolves to the same configured demo identity.
- Local SQLite is intended for development. Configure a per-environment data path; do not share the default file across deployments.
- NCC's meaning and upstream request/response contract are undefined, so its route intentionally returns `501`.
- There is no streaming or background job queue. A workflow request waits for the model response before returning.
- Stored document files are removed on explicit document deletion or conversation deletion. There is no retention scheduler or backup lifecycle yet.
- Upload validation is not a substitute for malware scanning; use synthetic/public documents only.

## Project layout

- `app/start.py` — FastAPI app, middleware, health/readiness, and startup.
- `app/routers/api.py` — Versioned HTTP routes and upload handling.
- `app/schemas.py` — Request and response models.
- `app/repositories.py` — SQLite persistence adapter functions.
- `app/database.py` — Connection, schema, and startup upgrades.
- `app/workflows.py` — Local extraction, lexical retrieval, classification, and model calls.
- `app/errors.py` — Safe, consistent API error format.
- `app/settings.py` — Environment-backed settings.

## Workflow behavior and limits

- The workflow selected in the UI is authoritative. Intent classification runs using the configured OpenAI model and existing prompt; its `summarize` output maps to the API's `summary` workflow.
- Ask and Draft can run without documents. Summary requires one or more documents attached to the conversation.
- PDF and DOCX text is extracted on the backend. Scanned PDFs are rejected because OCR has not been configured.
- Retrieval uses local keyword counts over extracted text. There is no query rewriting, embedding model, vector store, or reranker in this version.
- OpenAI receives the user prompt and selected source text. Do not use confidential client documents in this unauthenticated development app.
- Responses run synchronously. Drafts use placeholders for missing facts and are for professional review.
