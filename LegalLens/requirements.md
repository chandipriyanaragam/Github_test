# Legal Lens — Hybrid BRD / PRD / FRD

**Document status:** Draft for discussion  
**Version:** 0.1  
**Purpose:** Define a clear, buildable scope for a classroom demonstration with production-grade engineering practices.  
**Audience:** Project team, instructor, and classmates

## 1. Overview and goals

Legal Lens is a document-focused AI assistant concept for legal professionals. It brings three workflows into one application: **Ask** questions, **Summary** of legal documents, and **Draft** legal memoranda or related material. A user can provide a prompt and, where relevant, upload a document so the application can work with its contents.

The project is being built to demonstrate product thinking and software engineering in a class. It is not intended to provide legal services, be relied on in a real matter, or handle real client information. “Production-grade” describes the quality of implementation and operational practices—such as secure configuration, validation, maintainability, error handling, and tests—not a claim that the application is approved for law-firm deployment. The demonstration should use synthetic or public sample documents.

### Objectives

- Demonstrate a coherent end-to-end AI application: browser interface, Python API, and RAG-oriented AI layer.
- Let a user complete the Ask, Summary, and Draft workflows with understandable inputs and results.
- Make document-grounded results inspectable by showing source references when available.
- Keep the first release small enough to build, explain, and demonstrate in a class setting.
- Record unresolved policy and architecture choices for later decisions rather than inventing them.

### Success signals

The demonstration is successful when a user can upload an accepted document, ask a question about it, receive an answer with relevant source references where available, request a summary, create an editable draft, and understand how to save, export, or delete the work. Quality should be reviewed on a small, representative set of synthetic or public documents. Numeric acceptance targets can be set after the team defines the demo environment and evaluation set.

## 2. Users, scope, and assumptions

### Intended users and roles

- **Primary demonstration user:** A lawyer or law student acting as a legal professional, using the interface to explore the three workflows.
- **Project administrator/developer:** Configures the application, manages secrets and runtime settings, and reviews operational logs. This is a project role, not necessarily an in-product admin console.

The initial target is practicing lawyers and small-to-mid-sized firms as a product concept. The classroom implementation will not onboard real firms or imply that it is safe for live client matters. Instructors and classmates may also use the demo to assess its workflows.

### In scope for the initial release

- A web frontend with an Ask, Summary, and Draft experience.
- Upload and use PDF and DOCX files; a proposed starting per-file limit is 25 MB, configurable by the application.
- Ask general legal questions and questions grounded in a user-provided document, with the context made visible to the user.
- Summarize contracts, pleadings, and legal memoranda as initial examples.
- Generate editable first drafts of legal memoranda and common correspondence or case-related documents from user instructions and supplied material.
- Show citations or source passage references for document-grounded answers and summaries when available. Identify placeholders or assumptions in drafts.
- Save and revisit a user's own conversations and work; export generated content as DOCX or PDF; delete saved work.
- A Python FastAPI backend, UV-managed Python dependencies, and an AI layer using a RAG approach.

### Out of scope / not promised

- Legal advice, legal research guarantees, filing-ready documents, or autonomous legal decisions.
- Real client data or production law-firm deployment in the class demonstration.
- Scanned-document OCR, broad file-format support, collaboration/sharing, billing, or enterprise administration unless later added.
- A specific vector database, embedding model, model provider, or detailed RAG design. Those belong in the technical architecture phase.
- Multi-agent AI in the initial version; it remains a possible future extension.

### Working assumptions

1. A single-user demonstration account or equivalent isolated session is sufficient initially; user identity and authentication approach remain to be decided.
2. The user selects the workflow and supplies any required prompt, jurisdiction, and documents.
3. The product should make uncertainty visible and keep a lawyer or student in control of reviewing generated output.
4. Outputs and examples are educational demonstrations. Generated content must be reviewed by a qualified person before any real-world use.
5. The initial release may depend on an external AI service, but provider, data handling terms, and deployment location have not been selected.

## 3. Product and functional requirements

Priority key: **Must** = needed for the planned demonstration; **Should** = strongly preferred if schedule permits; **Later** = follow-up scope.

### FR-1 — Application entry and navigation (Must)

The frontend shall present Legal Lens as a web application and provide clear entry points to Ask, Summary, and Draft. The user shall be able to identify the active workflow and return to or start another task without losing saved work. Empty, loading, success, and error states shall be visible and understandable.

### FR-2 — Document intake (Must)

The user shall be able to select and upload a PDF or DOCX document. The application shall validate file type and configured size limit, show upload and processing status, and explain rejected files in plain language. A document shall be associated with the user's current work so it can be used in the selected workflow. Processing failures shall not be presented as successful ingestion.

### FR-3 — Ask workflow (Must)

The user shall be able to submit a natural-language question through a prompt field. The user shall be able to choose or see whether the question is general or based on an uploaded document. Where relevant, the interface shall collect jurisdiction or allow the user to state it in the prompt. The response shall identify its context; document-grounded answers should cite passages or pages when available and say when the supplied material does not support an answer. General answers shall not be represented as verified legal research.

### FR-4 — Summary workflow (Must)

The user shall be able to request a summary of an uploaded document. The result should be structured for readability and include source references when available. The interface shall identify the document summarized and communicate processing or generation errors. Initial examples should focus on contracts, pleadings, and legal memoranda; the application shall not imply that every document type has been validated.

### FR-5 — Draft workflow (Must)

The user shall be able to provide instructions and relevant source material to generate an editable first draft, initially targeting legal memoranda and common correspondence or case-related documents. The result shall distinguish supplied facts from missing information, placeholders, or assumptions to the extent supported by the AI workflow. The user shall be able to review and edit the result before export. The application shall label output as a draft requiring professional review.

### FR-6 — Conversation and work management (Should)

The user should be able to save and revisit their own conversations, uploaded-document tasks, summaries, and drafts. The interface shall provide a way to delete saved work. Export should be available for generated content in DOCX and PDF where feasible. Sharing between users is deferred until identity, authorization, and access controls are designed.

### FR-7 — API and service behavior (Must)

The frontend shall communicate with backend capabilities through documented FastAPI endpoints. The backend shall validate incoming requests, return consistent success and error responses, and avoid exposing internal exceptions or secrets. Long-running upload and generation steps shall provide a usable status or completion response. The API design shall keep user interface concerns separate from AI orchestration and document-processing responsibilities.

### FR-8 — RAG-oriented AI behavior (Must)

For document-grounded tasks, the AI layer shall use retrieved content from the provided document as context for generation. It shall preserve enough source metadata to present references to the user. If relevant supporting content is not found, the system should say so instead of inventing document support. Model, embeddings, vector store, retrieval strategy, chunking, and provider are architecture decisions to document separately.

### FR-9 — Feedback and evaluation (Should)

The user should be able to indicate whether an output was useful and optionally identify an issue. The project team shall maintain a small evaluation set of representative, non-sensitive documents and questions to review answer relevance, source accuracy, summary usefulness, and draft quality. Evaluation should include human review; automated scores alone are insufficient for legal-context quality.

## 4. Non-functional and quality requirements

### Security and privacy

- Do not place API keys, credentials, or private configuration in frontend code or source control; load secrets through environment-specific configuration.
- Validate uploads and requests on the server, restrict accepted types and sizes, and use safe temporary-file handling.
- Apply authentication and per-user access controls before enabling persistent multi-user use. If the demo omits authentication, document that limitation and keep its data synthetic.
- Protect traffic with HTTPS in any hosted environment. Restrict access to stored documents and generated work to the owning user.
- Define retention and deletion behavior, including temporary files, application storage, and any external AI provider retention. Do not claim complete deletion until all relevant stores and provider behavior are addressed.
- Do not use user documents or prompts for model training unless an explicit, informed policy and applicable provider controls permit it.

### Reliability and error handling

- Handle invalid files, extraction failures, unavailable AI services, timeouts, and malformed requests with clear user-facing messages and safe retry guidance.
- Do not silently lose work during a visible operation; communicate whether a task failed or completed.
- Use structured application logs for diagnosis while avoiding document contents, prompts, secrets, and unnecessary personal data in logs.

### Performance and capacity

- The interface should remain responsive while uploads and AI tasks run and provide progress or a clear waiting state.
- Establish measurable response-time and concurrency targets after the hosting environment and expected class demo load are known. Avoid claiming real-time performance before it is measured.
- Enforce configurable upload and request limits to prevent accidental resource exhaustion.

### Usability and accessibility

- Use clear labels, keyboard-operable controls, readable contrast, and accessible status/error messages.
- Explain which document and context are being used, and keep citations navigable or easy to inspect.
- Make generated content easy to review and edit; do not hide uncertainty or placeholders in dense text.

### Maintainability and portability

- Keep frontend, API, document handling, and AI orchestration responsibilities understandable and separable.
- Pin and manage Python dependencies with UV; document setup, configuration, and run instructions.
- Keep architecture choices replaceable where practical, especially the model provider and RAG storage components.
- Provide automated tests for core API, validation, and workflow behavior; use synthetic fixtures and mock AI services where needed.

## 5. Acceptance, risks, and open decisions

### Demonstration acceptance checklist

The first demonstration is ready when:

1. A user can navigate to all three workflows and submit input.
2. A valid PDF or DOCX within the configured limit can be uploaded; invalid or oversized files receive a clear error.
3. Ask can answer a question using uploaded content and show source references when the pipeline supplies them; lack of supporting content is communicated.
4. Summary returns a readable result for a supported sample document.
5. Draft returns editable text with visible placeholders/assumptions and a review label.
6. The user can save/revisit and delete work if persistence is included in the demo; export behavior is demonstrated if included.
7. Failure states are understandable, secrets are not exposed in the frontend or logs, and the demo uses non-sensitive data.
8. The team can explain the three-layer architecture and the limits of the AI results.

### Key risks and responses

- **Unsupported or incorrect legal output:** Limit claims, show source support and uncertainty, label drafts, and require human review.
- **Hallucinated or weak citations:** Evaluate source references against sample documents; do not display a citation as verified unless it maps to a real source location.
- **Sensitive data exposure:** Use synthetic/public documents, minimize logging, define retention, and review provider data handling before any real data is considered.
- **Scope expansion:** Prioritize the three workflows and core document path; defer OCR, collaboration, and multi-agent behavior.
- **Unclear evaluation:** Define representative tasks and human review criteria before claiming success.

### Questions for the next clarification pass

Answering these will let the document move from a recommendation draft to an agreed baseline. “Use the proposed default” is a valid answer.

1. **Demo audience:** Will the people using the demo be students, lawyers, or both? Should the interface explicitly call itself an educational prototype?
2. **Jurisdiction:** Which jurisdiction should examples use (for example, a specific US state, US federal, or another country), and should jurisdiction be required for general legal questions?
3. **Ask scope:** For general questions, do you want answers from the model's general knowledge, from a curated knowledge source, or should the first release focus only on uploaded documents?
4. **Document limits:** Are PDF and DOCX with a 25 MB limit acceptable? Should scanned PDFs be rejected or supported through OCR?
5. **Multi-document work:** Should users be able to upload several documents and ask across all of them, or only work with one document at a time?
6. **Draft types:** Which one or two draft templates should be demonstrated first (for example, legal memo, case brief, client letter, motion outline)?
7. **Output formats:** Is on-screen text sufficient initially, or are DOCX/PDF exports required for the class demonstration?
8. **Accounts and persistence:** Should users sign in and have saved history, or should the first demo use temporary/session-only work? If saved, what retention period is expected?
9. **Hosting:** Will this run locally on a laptop, in a classroom network, or as a hosted web application? This affects authentication, HTTPS, and deployment requirements.
10. **AI provider:** Is there a preferred or already available model/API provider, and are there cost or rate limits for the demonstration?
11. **Data handling:** Can any data leave the local environment for AI processing, or must the demo operate with local/mock services? Regardless, will the demo be restricted to synthetic/public documents?
12. **Citations:** Is page-level citation enough, or should the interface show quoted passages and let a user open the source location?
13. **Editing:** Should users be able to revise prompts and regenerate, edit generated text in the app, or both?
14. **Accessibility and browser support:** Are there required accessibility targets or browsers/devices for the class presentation?
15. **Success criteria:** What would make the project a successful class demonstration: completing all three workflows, architecture explanation, quality on a test set, UI polish, or a particular rubric?
16. **Document ownership and deletion:** Should deleting a conversation also delete its uploaded files and derived content? Should users have a “delete everything” action?
17. **Timeline and team:** What is the deadline, team size, and expected individual contribution? This will help set Must versus Should scope.
18. **Document format:** Do you want this kept as Markdown in the project, or should it later be formatted as a Word/PDF deliverable?

## 6. Proposed delivery sequence

1. **Frontend foundation:** Build navigation, upload controls, prompt entry, workflow-specific result views, and user-visible states using a selected JavaScript framework.
2. **Backend foundation:** Add FastAPI endpoints, validation, configuration, persistence choice, and documented API behavior.
3. **AI integration:** Implement the RAG workflow behind a replaceable service boundary, preserve source metadata, and connect Ask, Summary, and Draft behaviors.
4. **Hardening and demonstration:** Add automated checks, sample data, error-path handling, setup documentation, and a guided end-to-end demo.

This sequence is a planning aid; the implementation may iterate across layers as interfaces are proven.
