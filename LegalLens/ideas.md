# Legal Lens — Collected Ideas

## Product concept

Legal Lens is an AI application for lawyers and attorneys. It should help legal professionals work with legal questions and documents through a conversational interface.

## Initial capabilities

The first version is centered on three features:

1. **Ask** — Let a lawyer ask legal questions, including questions about an uploaded document.
2. **Summary** — Summarize a legal document.
3. **Draft** — Help draft a legal case document or legal memo.

## User experience ideas

- Provide a prompt or search bar for asking questions and giving instructions.
- Let users upload a document and ask questions about its contents.
- Include the document in the interaction so the user can ask questions grounded in that document.
- Build the frontend to collect questions, instructions, and document uploads from users.
- The initial frontend can use HTML, CSS, and a JavaScript framework. React or Angular are both acceptable; there is no preference yet.

## Planned implementation phases

Development is expected to proceed in three phases:

1. **Frontend** — Build the user-facing application and input flows.
2. **Backend** — Connect the frontend to backend services.
3. **AI layer** — Add the AI capabilities that support Ask, Summary, and Draft.

## Current technology preferences

- **Frontend:** HTML, CSS, and a JavaScript framework; React or Angular may be selected later.
- **Backend:** Python with FastAPI.
- **Python package and dependency management:** UV.
- **AI approach:** Retrieval-augmented generation (RAG) for the initial AI layer.

## Decisions to defer

The following AI architecture decisions are intentionally open for the later technical architecture phase:

- Vector database
- Embedding model
- Specific RAG design and implementation details

The AI layer may be extended to a multi-agent approach or upgraded later. Those are future possibilities, not requirements for the initial version.

## First planning deliverable

The first planning step is to prepare a **Business Requirements Document (BRD)**. It should describe functional and non-functional requirements and other relevant business details. Detailed AI and infrastructure choices can be addressed during technical architecture planning.

## Proposed answers for the BRD

These are practical starting recommendations for the first release. They should be confirmed with intended users and legal or security stakeholders before they become final requirements.

- **Intended users:** Start with practicing lawyers and small-to-mid-sized law firms. This gives the initial product a clear professional audience while leaving room to expand to in-house legal teams later.
- **Document formats and limits:** Support PDF and DOCX first, with a configurable per-file size limit (a proposed initial limit is 25 MB) and clear upload feedback. Consider TXT as a low-effort addition. Defer scanned-document OCR and other formats until validated as needed.
- **Scope of Ask:** Support both general legal questions and questions about uploaded documents, but make the selected context clear. For document questions, ground answers in the uploaded material and indicate when it does not contain enough information. For general legal questions, ask the user to specify jurisdiction and make the jurisdiction of the response explicit.
- **Initial Summary and Draft types:** Prioritize summarizing contracts, pleadings, and legal memoranda. For drafting, begin with legal memoranda and first drafts of common correspondence or case-related documents based on user instructions and provided source materials. Treat generated text as an editable draft for lawyer review.
- **Citations and source links:** Include citations or references to source passages for document-grounded answers and summaries wherever possible, so users can check the supporting text. Drafts should identify supplied sources and distinguish sourced facts from placeholders or assumptions.
- **Jurisdiction, confidentiality, privacy, and retention:** Capture jurisdiction as an explicit input when relevant. Treat uploaded materials and prompts as confidential; define access controls, encryption, retention/deletion behavior, and whether customer data may be used for model training before launch. The applicable obligations should be reviewed with counsel and security stakeholders based on the launch markets and customer setup.
- **Work management:** Let users save and revisit their conversations and documents, export generated content (DOCX and PDF are useful initial targets), and delete their saved work. Sharing can be deferred until there is a defined access-control model.
- **Initial evaluation:** Run a pilot with practicing lawyers. Measure task completion and time saved, answer and citation accuracy based on lawyer review, usefulness of summaries and drafts, user satisfaction, and serious error or privacy incidents. Set numeric targets after collecting a baseline and defining the pilot's representative tasks.
