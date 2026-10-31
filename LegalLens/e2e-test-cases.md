# LegalLens UI and API test cases

Executed 2026-10-19 against the React UI in headless Edge and a separate FastAPI process. The test backend used an isolated SQLite database and document directory. The existing `var/legallens.db` was not modified.

## Results

| ID | Test case | Result | Observed behavior |
|---|---|---|---|
| UI-01 | Load the workspace with the backend available | Pass | UI shows “Backend connected” and an empty conversation list in the isolated database. |
| UI-02 | Create a conversation by submitting an Ask message | Pass | Conversation and user message are persisted with the selected workflow and jurisdiction. |
| UI-03 | Get an LLM answer with citations for an Ask request | Not implemented | API returns `assistant_message: null` and `awaiting_orchestration`; there is no assistant answer or citation data. |
| UI-04 | Rename a conversation in the UI | Not implemented | No rename control is present. The backend PATCH endpoint successfully changes the title, which the UI displays after reload. |
| UI-05 | Delete a conversation, cancel once, then confirm | Pass | Cancel leaves the record intact; confirmation removes it and the API returns 404 for the deleted conversation. |
| UI-06 | Select a previously uploaded document in a new conversation | Not implemented | UI offers local file upload only; it has no existing-document library or picker. |
| UI-07 | Upload a new PDF and submit a Summary request | Partial | Upload and Summary turn are persisted with the document ID. Document status remains `awaiting_processing`; no summary is generated. |
| UI-08 | Submit a Draft request for a legal memo | Partial | Draft message is persisted with workflow `draft`; no memo is generated. |
| UI-09 | Change jurisdiction on an existing conversation | Pass | UI PATCH updates the backend value. |
| UI-10 | Reject an unsupported file extension | Pass | UI reports that only non-empty PDF/DOCX files are accepted; no upload is made. |
| UI-11 | Remove an uploaded attachment | Pass | Attachment chip disappears and the uploaded document is deleted from the test backend. |
| UI-12 | Search conversation history | Pass | Search filters the sidebar to matching conversation titles. |
| UI-13 | Use the Summary starter card | Pass | Selects Summary workflow and fills the starter prompt. |
| UI-14 | Use Ctrl+K to start a new conversation | Pass | Returns to the unsaved new-conversation view. |
| UI-15 | Copy a message | Partial | UI reports clipboard access is unavailable in the headless browser; clipboard contents could not be verified. |
| UI-16 | Use Export | Unavailable | UI reports that export is not available in this backend version. |
| BUILD-01 | Build the frontend | Pass | `npm run build` completed successfully. |

## Summary

Conversation persistence and basic workspace controls work. The requested AI behaviors—answer generation, citations, document summarization, and memo drafting—cannot pass because orchestration and document processing are not connected. Rename is available through the API but not through the UI, and the UI has no way to select an existing document.

The test conversations and synthetic document were removed. The original database remained at 2 conversations, 1 message, 1 turn, and 1 document.

## Executed UI and backend run — 2026-10-22

This run used an isolated database and synthetic DOCX files, driven through headless Edge with Chrome DevTools Protocol. A deterministic local OpenAI-compatible stub was used for workflow integration checks. This verifies the UI-to-backend path, extracted-document context, persistence, and citation plumbing; it does **not** establish answer quality from a real LLM.

| Result | Count |
|---|---:|
| Pass | 20 |
| Fail | 0 |
| Blocked | 2 |
| Unavailable | 1 |

The live provider check is blocked: the configured OpenAI credential returned HTTP 401 `invalid_api_key`, so no real model output or citation quality could be assessed. PDF extraction is blocked in this environment because `pypdf` is absent from the active backend virtual environment. Export is reported by the UI as unavailable in this backend version.

The requested workflows passed under the local stub: create a conversation, Ask with a persisted citation linked to the supporting lease excerpt, rename it, select/reuse an existing document in another conversation, summarize it, upload and summarize a new DOCX, draft a memo in a third conversation, and cancel/confirm deletion with API verification. Additional coverage includes jurisdiction, unsupported upload, removing an attachment, history search, Summary starter, Ctrl+K, copying a message, backend readiness, and frontend build.

Artifacts are in [`test-results/e2e-2026-10-22`](test-results/e2e-2026-10-22):

- [Excel results workbook](test-results/e2e-2026-10-22/LegalLens-E2E-Results.xlsx) — Summary, Test Cases, and Evidence sheets.
- [Machine-readable results](test-results/e2e-2026-10-22/results.json).
- [Browser exception capture](test-results/e2e-2026-10-22/browser-errors.json).
- [Screenshot evidence folder](test-results/e2e-2026-10-22/evidence).
- [Automation runner](e2e/run-edge-cdp.mjs) and [workbook generator](e2e/generate-report.py).

The test used only synthetic lease and policy documents. Its database and uploads are isolated under the run artifact directory; the existing application database was not used.
