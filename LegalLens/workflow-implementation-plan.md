# LegalLens workflow implementation plan

## Baseline before implementation

- Intent classification is standalone in `orchestrator/`. It returns `ask`, `draft`, or `summarize` using the configured `OPENAI_MODEL` (currently defaults to `gpt-6-luna`). That does not yet implement any workflow.
- The backend persists user turns and uploaded files. A turn currently returns `awaiting_orchestration` with `assistant_message: null`; uploaded documents remain `awaiting_processing`.
- The frontend can choose Ask, Draft, or Summary and upload files. It has no existing-document picker or UI rename action.
- The integration TODO explicitly leaves orchestration, RAG, OCR/extraction, indexing, citations, and exports unimplemented.

## Version-one implementation decisions

Implementation is authorized with these local-development assumptions. These choices should be revisited before production deployment.

- Use the configured OpenAI model for intent classification and response generation. Read `OPENAI_MODEL` and `OPENAI_API_KEY` from `backend/.env`; `gpt-6-luna` is the default.
- Respect the workflow selected in the UI. Run the existing intent-classification prompt on every request; explicit UI selection wins when it differs.
- Use original prompt keywords for local lexical retrieval. No query-rewriting LLM, embedding model, vector database, or reranker is used in v1.
- Extract PDF and DOCX text locally. Scanned PDFs fail with an OCR-not-configured message; no external OCR service is called.
- Persist extracted text and citations in local SQLite. Turns run synchronously and return a complete answer; streaming, retries, and background jobs are deferred.
- Attached source text is sent to OpenAI for generation. Use synthetic or public documents in this unauthenticated demo.
- Ask supports general and document questions; Summary requires selected documents; Draft uses placeholders for missing facts. All output is a draft for professional review.

## Proposed work plan (implementation status)

### 0. Confirm product, model, and data decisions

- [x] Resolve the open questions with the version-one assumptions above.
- [x] Record the selected architecture and constraints.
- [x] Keep embeddings, query rewriting, reranking, vector storage, and external document processing out of v1.

### 1. Define workflow and API contracts

- [x] Normalize the classifier's `summarize` label with the API/UI's `summary` label.
- [x] Define synchronous completed/failed state, request errors, 120-second provider timeout, and no retries or streaming.
- [x] Define assistant message and citation schemas, including source document, page, excerpt, and stable citation identifiers.
- [x] Pass selected document IDs and jurisdiction with each turn.

### 2. Build document preparation

- [x] Extract text and page locations from supported PDF and DOCX files.
- [x] Exclude OCR; scanned PDFs receive a clear processing error.
- [x] Store extracted text and mark documents ready only after extraction succeeds.
- [x] Chunk extracted text locally with file/page metadata; cascade citations and stored document copies on deletion.

### 3. Implement Ask

- [x] Ask supports general questions and selected-document questions.
- [x] Retrieve lexical matches from selected documents and keep source passages for citation.
- [x] Exclude query rewriting and reranking from v1.
- [x] Prompt answers to disclose unsupported claims and cite retrieved source passages.

### 4. Implement Summary

- [x] Summarize only the selected, successfully processed documents.
- [ ] Define summary sections, length, treatment of conflicting terms, and source coverage.
- [x] Preserve PDF page provenance and show source excerpts in the UI.
- [x] Bound summary context by sampling up to 16 chunks across the selected documents.

### 5. Implement Draft

- [ ] Define the first draft type (for example, an internal legal memo) and required sections.
- [ ] Identify facts/documents the draft may use, how missing facts are represented, and whether citations are required.
- [ ] Label output as a draft for professional review; make it editable and persist revisions if requested.

### 6. Integrate and expose results in the UI

- [x] Connect classification and workflow generation to turn submission.
- [x] Return completed or failed status and show answers and source excerpts in the conversation.
- [x] Add existing-document selection by copying the source into the active conversation. Conversation rename controls remain deferred.
- [x] Render citations and source excerpts for document-based answers and summaries. Drafts persist as assistant messages; editing remains deferred.

### 7. Verify quality, safety, and operations

- [ ] Create synthetic golden cases for intent routing, retrieval relevance, citation support, summary coverage, and draft structure.
- [ ] Measure answer quality and latency before adding query rewriting or reranking.
- [ ] Add provider timeouts, rate limits, cost tracking, audit-safe logs, deletion behavior, and secret handling.
- [ ] Verify the three UI workflows end to end against a disposable database and synthetic documents.

## Deferred choices and constraints

- No embeddings, vector store, reranker, query rewriting, OCR, streaming, async job queue, authentication, or production database is included in this first implementation.
- Drafts are saved as assistant messages. Inline editing, revisions, and exports are not implemented.
- Summary samples up to 16 chunks across its selected document set to bound context. This can miss detail in very long documents and must be evaluated before relying on it.
- PDF citations include page numbers. DOCX extraction has no stable page map, so citations identify the file and excerpt only.
- The current `backend/.env` has no OpenAI key. Add `OPENAI_API_KEY` there before trying a workflow; `OPENAI_MODEL` defaults to `gpt-6-luna`.
- The OpenAI request path has not been exercised here. Use synthetic/public documents because this app still uses a shared demo identity and sends selected text to OpenAI.
- Implementation and docs were updated, but tests and live end-to-end checks were not run in this turn.
