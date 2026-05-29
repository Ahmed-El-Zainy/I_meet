# I_meet

```
Dear Candidate, 

Please find the following task to be completed before 1/6/2026. Early submissions are appreciated.

The dataset contains 6 files (three audio and 3 video) for two clients.
Dataset URL: https://drive.google.com/drive/folders/1S9S8T-a7KbLVm9_nCUYW1zq44M42fo0r?usp=sharing
Take-Home Task: AI Meeting Intelligence System
Overview
Build a working prototype of an AI-powered meeting intelligence platform with two integrated subsystems:

Post-meeting processing pipeline — transcription, summarization, sentiment analysis, encrypted storage
Per-client RAG chatbot — conversational interface scoped to each client's own data
Deliverables: Source code, README with run instructions, short technical writeup (max 4 pages), and a 5-minute screen recording demoing both subsystems end-to-end.

System Requirements
Subsystem 1: Meeting Processing Pipeline
Build a service that ingests a meeting recording and produces structured, encrypted output.

Inputs:

A meeting recording file (audio or video)
Metadata: meeting_id, client_id, meeting_title, participants, meeting_date
Required processing:

Ingestion endpoint — REST API that accepts a recording + metadata. Simulate the Zoom/Teams/WebEx webhook flow; you don't need real integration, but the endpoint contract should be realistic (multipart upload or a URL to fetch from).
Transcription — speech-to-text with speaker diarization where possible. Must support Arabic (MSA + at least one dialect) and English, including code-switching within a single utterance. Output should include timestamps and speaker labels.
Summarization — produce a structured summary containing:
Executive summary (3–5 sentences)
Key discussion points
Decisions made
Action items (with assignee and deadline where mentioned)
Open questions / unresolved items
Sentiment analysis — per-speaker and overall meeting sentiment. Don't just output "positive/negative/neutral" — provide a breakdown that's actually useful (e.g., sentiment trajectory across the meeting, sentiment per topic or per speaker).
PDF generation — render the summary as a professional PDF document. Arabic content must render correctly (RTL, proper font shaping).
Encryption at rest:
PDF: encrypted on disk. The encryption scheme is your choice, but justify it in the writeup.
Metadata in MySQL: all sensitive fields encrypted. "Sensitive" means at minimum: meeting_title, participants, transcript, summary_text, sentiment_data. Non-sensitive operational fields (meeting_id, client_id, created_at, status) can be plaintext.
Key management strategy must be documented. Hardcoded keys in source code = automatic fail.
Database schema — design and document the MySQL schema. We expect at least: clients, meetings, participants, processing_status, encrypted artifacts references.
Required API endpoints (minimum):

POST /meetings/ingest — submit a recording for processing
GET /meetings/{meeting_id}/status — check processing state
GET /meetings/{meeting_id}/summary — retrieve decrypted summary (authenticated)
GET /clients/{client_id}/meetings — list meetings for a client
Subsystem 2: Per-Client RAG Chatbot
Build a chatbot that lets each client query only their own meeting data through natural conversation.

Required functionality:

Embeddings pipeline — extract content from the encrypted PDFs (decrypt → chunk → embed → store), build a vector database. Justify your embedding model choice, especially for Arabic.
Multi-tenant isolation — this is the critical requirement. Every retrieval and every response must be strictly scoped to the authenticated client's data. A client must never see another client's content under any circumstance, including:
Direct queries about other clients
Indirect leakage through retrieval (e.g., semantically similar chunks from other tenants ranking high)
Prompt injection attempts from within a document
Vector database queries that bypass the filter
Client identification — design the authentication/identification flow. How does the chatbot know which client is asking? Document the threat model.
Conversational interface — REST API or simple UI (Gradio/Streamlit acceptable). Must support:
Multi-turn conversation with context retention
Citation of source meetings (e.g., "from the Q1 planning meeting on 2026-02-14")
Refusal when the answer isn't in the client's data
Bilingual queries (Arabic / English / mixed)
Required test scenarios — your chatbot must correctly handle:
Factual recall: "What did we decide about the budget in last week's meeting?"
Cross-meeting synthesis: "Summarize all action items assigned to Ahmed across all my meetings."
Temporal queries: "What were the main concerns raised in meetings this month?"
Refusal: a question whose answer isn't in any meeting → must say so, not hallucinate
Isolation test: a query from client A about content that only exists in client B's meetings → must return "no information found", not leak
What We Provide
3 sample meeting recordings (mixed Arabic/English) representing data for 2 different clients (Client A: 3 meetings, Client B: 3 meeting)
Technical Constraints
Language: Python primary. Any auxiliary services in your choice of stack.
Models: open-source or API-based, your choice. Document costs if API-based.
Database: MySQL for metadata (required). Vector DB is your choice (Chroma, Qdrant, pgvector, FAISS, etc.).
Deployment: must run locally via docker-compose up. We will not debug your environment.
Secrets: use .env for configuration. Provide a .env.example.
Writeup Requirements (max 4 pages)
Cover these sections:

Architecture diagram — system components and data flow
Model and tool choices — what you picked for STT, summarization, sentiment, embeddings, LLM, and why. Tradeoffs explicitly stated.
Encryption strategy — algorithms, key management, what's encrypted and what isn't, why
Multi-tenancy design — how you guarantee client isolation at every layer
Arabic handling — what specifically you did for Arabic STT, embedding, generation, PDF rendering
Self-reported metrics — WER/CER on the reference transcript, latency breakdown (ingestion → PDF availability), chatbot response time, retrieval precision on the eval questions
Known limitations — what doesn't work, what would break at scale, what you'd fix with more time
Cost estimate — per-meeting processing cost and per-query chatbot cost at your chosen stack
Evaluation Rubric
Area	Weight	What we look for
Multi-tenant isolation	20%	Hard isolation, defense in depth, no leakage in any test case. This is a security requirement, not a feature.
Encryption correctness	15%	Sane algorithm choices, real key management, encrypted data actually unreadable without key, no hardcoded secrets
Arabic STT + summarization quality	15%	WER/CER numbers, dialect handling, code-switching, summary faithfulness
RAG quality	15%	Retrieval precision, citation accuracy, faithful answers, proper refusal
System design	10%	Clean component boundaries, sensible API contracts, scalable shape, MySQL schema quality
PDF generation	5%	Renders correctly, Arabic shaping correct, professional output
Sentiment analysis depth	5%	Goes beyond pos/neg/neutral, actually useful for a meeting context
Code quality	5%	Readable, organized, basic tests present, docker-compose works first try
Writeup honesty	5%	Acknowledges weaknesses, explains tradeoffs, no marketing language
Production thinking	5%	Logging, error handling, observability hooks, cost awareness
Pass threshold: 70% overall, with no score below 3/5 on multi-tenant isolation or encryption. Those two are hard gates — failing either is an automatic no-hire signal regardless of other scores, because they map to non-negotiable enterprise requirements.


What We're Explicitly Testing
This task is designed to surface the gap between "I've used these tools" and "I can ship a production-shaped system."

Submission Format
A private GitHub repo shared with our evaluation account, containing:

/src — application code
/infra — docker-compose, schema migrations, .env.example
/docs/writeup.pdf — the technical writeup
/docs/architecture.png — architecture diagram
/demo/walkthrough.mp4 — 5-minute screen recording
README.md — setup and run instructions
/tests — at minimum, tests covering the isolation guarantees
Anti-Patterns That Will Lower Your Score
State these explicitly in the brief so candidates can't claim they didn't know:

Hardcoded API keys, encryption keys, or DB credentials anywhere in the code
Filtering tenant data only in the LLM prompt ("the LLM will remember to only use Client A's data") — this is not isolation
Storing encryption keys in the same database as the encrypted data, unwrapped
Using one global vector index without per-tenant filtering at the query layer
Ignoring Arabic-specific concerns and assuming Whisper-base will "just work"
Hallucinating a summary when STT confidence is low instead of flagging it
A 50-page writeup that buries the tradeoffs in prose
Good Luck!

--
Best Regards
```