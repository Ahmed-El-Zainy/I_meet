# I_meet — AI Meeting Intelligence System

A production-shaped prototype of an AI-powered meeting intelligence platform with two integrated subsystems:

- **Subsystem 1** — Post-meeting processing pipeline: transcription, summarization, sentiment analysis, encrypted PDF generation, and MySQL storage
- **Subsystem 2** — Per-client RAG chatbot: conversational interface with hard multi-tenant isolation, scoped strictly to each client's own meeting data

Supports **Arabic** (MSA and dialects) and **English**, including code-switching within a single utterance.

---

## Features at a Glance

- REST API for meeting ingestion with realistic webhook-style multipart upload
- Speech-to-text with speaker diarization (Whisper + pyannote)
- Structured LLM summarization (executive summary, decisions, action items, open questions)
- Per-speaker sentiment analysis with trajectory and topic breakdown
- Professional PDF reports with correct Arabic RTL rendering
- AES-256-GCM encryption at rest for sensitive DB fields and PDF files
- Per-client RAG chatbot with citation, refusal, and bilingual query support
- Defense-in-depth multi-tenant isolation (JWT, API, vector DB, prompt scope)
- Runs locally via `docker compose up`

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Service Endpoints](#service-endpoints)
5. [Environment Configuration](#environment-configuration)
6. [Sample Data Setup](#sample-data-setup)
7. [Architecture Overview](#architecture-overview)
8. [Subsystem 1 — Meeting Processing Pipeline](#subsystem-1--meeting-processing-pipeline)
9. [Subsystem 2 — RAG Chatbot](#subsystem-2--rag-chatbot)
10. [Database Schema](#database-schema)
11. [Encryption Design](#encryption-design)
12. [Multi-Tenancy and Isolation](#multi-tenancy-and-isolation)
13. [Arabic Handling](#arabic-handling)
14. [API Reference](#api-reference)
15. [Running Tests](#running-tests)
16. [Loading Sample Data](#loading-sample-data)
17. [Demo Walkthrough](#demo-walkthrough)
18. [Technology Stack](#technology-stack)
19. [Known Limitations](#known-limitations)
20. [Documentation and Deliverables](#documentation-and-deliverables)
21. [Troubleshooting](#troubleshooting)
22. [Submission Checklist](#submission-checklist)

---

## Project Structure

```
I_meet/
├── src/
│   ├── api/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── dependencies.py          # Auth, DB session injection
│   │   └── routers/
│   │       ├── meetings.py          # POST /meetings/ingest, GET /meetings/{id}/...
│   │       ├── clients.py           # GET /clients/{id}/meetings
│   │       └── chat.py              # POST /chat/query
│   ├── pipeline/
│   │   ├── ingestion.py             # Multipart upload handler, job queuing
│   │   ├── transcription.py         # Whisper STT + pyannote diarization
│   │   ├── summarization.py         # LLM summarization (structured output)
│   │   ├── sentiment.py             # Per-speaker sentiment + trajectory
│   │   └── pdf_generator.py         # WeasyPrint PDF with Arabic RTL support
│   ├── rag/
│   │   ├── embeddings.py            # Chunk + embed transcripts/summaries
│   │   ├── vector_store.py          # Qdrant client with tenant-scoped queries
│   │   ├── retriever.py             # Filtered retrieval (client_id hard filter)
│   │   └── chatbot.py               # Multi-turn conversation, citation, refusal
│   ├── db/
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── crud.py                  # DB operations
│   │   └── session.py               # DB connection pool
│   ├── security/
│   │   ├── encryption.py            # AES-256-GCM encrypt/decrypt helpers
│   │   ├── key_management.py        # Key derivation, env-based key loading
│   │   └── auth.py                  # JWT validation, client_id extraction
│   ├── workers/
│   │   └── celery_app.py            # Celery worker + task definitions
│   └── ui/
│       └── chatbot_ui.py            # Gradio interface for RAG chatbot
├── infra/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── Dockerfile.ui
│   └── mysql/
│       └── init.sql                 # Schema (run on first MySQL start)
├── docs/
│   ├── writeup.pdf                  # Technical writeup (submission)
│   └── architecture.png             # Architecture diagram (submission)
├── demo/
│   └── walkthrough.mp4              # 5-minute demo recording (submission)
├── tests/
│   ├── test_isolation.py            # Multi-tenant isolation guarantees
│   ├── test_encryption.py           # Encryption round-trip tests
│   ├── test_pipeline.py             # Processing + PDF generation tests
│   └── test_rag.py                  # RAG retrieval + refusal tests
├── scripts/
│   └── ingest_samples.py            # Batch-ingest all 6 sample meetings
├── data/
│   └── sample_meetings/             # Place renamed sample recordings here
├── docker-compose.yml               # Root compose file — use this to start
├── .env.example
└── README.md
```

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Docker | 24+ |
| Docker Compose | v2 (`docker compose`) |
| RAM | 16 GB recommended (Whisper large-v3 ~10 GB; 8 GB minimum with `medium` model) |
| Disk | 20 GB+ (model cache + encrypted file store) |
| GPU | Optional but recommended for STT (CUDA 11.8+) |
| HuggingFace account | Required for pyannote speaker diarization — set `HF_TOKEN` in `.env` |
| OpenAI API key | Required if using `LLM_PROVIDER=openai` (default) |

> **Security notice:** Never commit `.env`. Generate encryption keys with `openssl rand -hex 32`. Hardcoded keys in source code are an automatic evaluation failure.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd I_meet

# 2. Copy the environment template and fill in all values
cp .env.example .env
# Edit .env — see Environment Configuration below

# 3. Prepare sample recordings (see Sample Data Setup)
#    Place 6 files under data/sample_meetings/

# 4. Start all services
docker compose up --build

# 5. Wait for services to become healthy (~2–3 min on first run; models download on first job)
#    Look for "Application startup complete" in the API container logs

# 6. Verify the API is running
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# 7. Generate JWT tokens for sample clients (after stack is up)
docker compose exec api python -c "
from src.security.auth import create_token
print('Client A:', create_token('client_a'))
print('Client B:', create_token('client_b'))
"
# Paste output into .env as CLIENT_A_TOKEN and CLIENT_B_TOKEN, then restart api + ui:
# docker compose restart api ui

# 8. Open in your browser
#    Chat UI:    http://localhost:7860
#    API docs:   http://localhost:8000/docs

# 9. (Optional) Batch-ingest all sample meetings
docker compose exec api python -m scripts.ingest_samples
```

---

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | REST backend |
| Health check | http://localhost:8000/health | Smoke test (no auth) |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Chat UI | http://localhost:7860 | Gradio client selector + chat |
| Qdrant | http://localhost:6333 | Vector DB (internal) |
| MySQL | localhost:3306 | Metadata DB (internal, not exposed by default) |
| Redis | localhost:6379 | Celery broker (internal) |

---

## Environment Configuration

Copy [`.env.example`](.env.example) to `.env` and fill in every value before starting.

| Variable | Description |
|----------|-------------|
| `MYSQL_HOST` | Database host (`mysql` inside Docker) |
| `MYSQL_PORT` | Database port (default `3306`) |
| `MYSQL_DATABASE` | Database name |
| `MYSQL_USER` / `MYSQL_PASSWORD` | Application DB credentials |
| `MYSQL_ROOT_PASSWORD` | MySQL root password |
| `FIELD_ENCRYPTION_KEY` | 32-byte hex key for AES-256-GCM field encryption |
| `FILE_ENCRYPTION_KEY` | Separate 32-byte hex key for PDF file encryption |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens |
| `JWT_ALGORITHM` | JWT algorithm (default `HS256`) |
| `JWT_EXPIRE_MINUTES` | Token expiry (default `60`) |
| `OPENAI_API_KEY` | OpenAI API key (when `LLM_PROVIDER=openai`) |
| `LLM_PROVIDER` | `openai` or `ollama` |
| `LLM_MODEL` | e.g. `gpt-4o` or `aya:35b` |
| `WHISPER_MODEL` | e.g. `large-v3` (or `medium` for lower RAM) |
| `WHISPER_DEVICE` | `cuda`, `cpu`, or `mps` |
| `EMBEDDING_MODEL` | e.g. `intfloat/multilingual-e5-large` |
| `EMBEDDING_DEVICE` | `cuda` or `cpu` |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant connection |
| `QDRANT_COLLECTION` | Collection name (default `meetings`) |
| `REDIS_URL` | Celery broker URL |
| `ENCRYPTED_PDF_DIR` | Path for encrypted PDF storage |
| `CLIENT_A_ID` / `CLIENT_B_ID` | Pre-seeded tenant IDs |
| `CLIENT_A_TOKEN` / `CLIENT_B_TOKEN` | JWT tokens for sample clients |
| `HF_TOKEN` | HuggingFace token for pyannote diarization model access |

### Generating keys and tokens

```bash
# Generate encryption keys (run twice — one for each key variable)
openssl rand -hex 32

# Generate JWT tokens (after docker compose up)
docker compose exec api python -c "
from src.security.auth import create_token
print('Client A:', create_token('client_a'))
print('Client B:', create_token('client_b'))
"
```

For CPU-only machines, set in `.env`:

```dotenv
WHISPER_DEVICE=cpu
EMBEDDING_DEVICE=cpu
WHISPER_MODEL=medium
```

---

## Sample Data Setup

The provided dataset contains **6 recordings** for **2 clients** (Client A: 3 meetings, Client B: 3 meetings).

Dataset URL: https://drive.google.com/drive/folders/1S9S8T-a7KbLVm9_nCUYW1zq44M42fo0r?usp=sharing

Files may arrive with mixed names. The batch ingest script ([`scripts/ingest_samples.py`](scripts/ingest_samples.py)) expects them under `data/sample_meetings/` with standardized names:

| Provided file (typical name) | Tenant | Expected path for ingest script |
|------------------------------|--------|--------------------------------|
| `client1_meet_1.wav` | client_a | `data/sample_meetings/client_a_meeting_1.wav` |
| `client1_meet2.wav` | client_a | `data/sample_meetings/client_a_meeting_2.wav` |
| `client1_meet3.wav` | client_a | `data/sample_meetings/client_a_meeting_3.wav` |
| `Client 2 Meeting 1.mp4` | client_b | `data/sample_meetings/client_b_meeting_1.mp4` |
| `Client 2 Meeting 2.mp4` | client_b | `data/sample_meetings/client_b_meeting_2.mp4` |
| `Client 2 Meeting 3.mp4` | client_b | `data/sample_meetings/client_b_meeting_3.mp4` |

### Prepare files on Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force -Path data\sample_meetings

Copy-Item "data\client1_meet_1.wav"  "data\sample_meetings\client_a_meeting_1.wav"
Copy-Item "data\client1_meet2.wav"   "data\sample_meetings\client_a_meeting_2.wav"
Copy-Item "data\client1_meet3.wav"   "data\sample_meetings\client_a_meeting_3.wav"
Copy-Item "data\Client 2 Meeting 1.mp4" "data\sample_meetings\client_b_meeting_1.mp4"
Copy-Item "data\Client 2 Meeting 2.mp4" "data\sample_meetings\client_b_meeting_2.mp4"
Copy-Item "data\Client 2 Meeting 3.mp4" "data\sample_meetings\client_b_meeting_3.mp4"
```

### Prepare files on Linux / macOS

```bash
mkdir -p data/sample_meetings

cp "data/client1_meet_1.wav"       "data/sample_meetings/client_a_meeting_1.wav"
cp "data/client1_meet2.wav"        "data/sample_meetings/client_a_meeting_2.wav"
cp "data/client1_meet3.wav"        "data/sample_meetings/client_a_meeting_3.wav"
cp "data/Client 2 Meeting 1.mp4"   "data/sample_meetings/client_b_meeting_1.mp4"
cp "data/Client 2 Meeting 2.mp4"   "data/sample_meetings/client_b_meeting_2.mp4"
cp "data/Client 2 Meeting 3.mp4"   "data/sample_meetings/client_b_meeting_3.mp4"
```

> **Note:** Update [`scripts/ingest_samples.py`](scripts/ingest_samples.py) file extensions (`.wav` vs `.mp4`) if your copies use different formats than the script defaults.

Alternatively, ingest meetings one at a time using the [curl examples](#example-ingest-a-meeting) below.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        docker compose network                     │
│                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │  FastAPI  │   │  Celery  │   │  Gradio  │   │    MySQL     │  │
│  │  :8000   │──▶│  Worker  │   │   :7860  │   │   :3306      │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘  │
│       │               │               │                           │
│       │         ┌─────┴──────┐        │        ┌──────────────┐  │
│       └────────▶│   Redis    │        │        │    Qdrant    │  │
│                 │   :6379    │        └───────▶│    :6333     │  │
│                 └────────────┘                 └──────────────┘  │
│                                                                    │
│  Volumes: mysql_data, qdrant_data, pdf_storage, model_cache       │
└──────────────────────────────────────────────────────────────────┘
```

### Ingestion lifecycle

1. Client `POST`s to `/meetings/ingest` with recording + metadata + JWT
2. API validates auth, stores job via Celery, returns `{meeting_id, status: "queued"}`
3. Celery worker runs the pipeline: STT → diarization → summarization → sentiment → PDF → encrypt → store → embed
4. Status updates written to MySQL `processing_status` throughout
5. Client polls `GET /meetings/{id}/status` until `status: "complete"`

### Chat lifecycle

1. Client `POST`s to `/chat/query` with `{message, conversation_id}` + JWT header
2. API extracts `client_id` from JWT (never from request body)
3. Retriever queries Qdrant with mandatory `client_id` filter
4. LLM generates a grounded response with source citations
5. Conversation history stored in Redis, scoped to `{client_id}:{conversation_id}`

See also [`docs/architecture.png`](docs/architecture.png) for the full diagram in the technical writeup.

---

## Subsystem 1 — Meeting Processing Pipeline

### Step 1: Ingestion endpoint

**Endpoint:** `POST /meetings/ingest`

Accepts multipart form data:

| Field | Type | Notes |
|-------|------|-------|
| `recording_file` | binary | Audio or video (mp3, mp4, wav, m4a, webm) |
| `meeting_id` | string | Optional UUID; server-generated if omitted |
| `client_id` | string | Ignored if it differs from JWT — JWT always wins |
| `meeting_title` | string | Encrypted at rest |
| `participants` | JSON array string | Encrypted at rest |
| `meeting_date` | ISO8601 date | Plaintext operational field |

Validates file type, queues a Celery task, returns immediately with `meeting_id` and `status: "queued"`.

### Step 2: Transcription

**Model:** `openai/whisper-large-v3` via `faster-whisper` (CTranslate2 backend)

**Diarization:** `pyannote/speaker-diarization-3.1` (requires `HF_TOKEN`)

**Output format:**

```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "speaker": "SPEAKER_00",
      "text": "Good morning everyone, let's get started.",
      "language": "en",
      "confidence": 0.97
    },
    {
      "start": 4.5,
      "end": 9.1,
      "speaker": "SPEAKER_01",
      "text": "صباح الخير، هل انتهيتم من مراجعة التقرير؟",
      "language": "ar",
      "confidence": 0.91
    }
  ],
  "language_mix": {"en": 0.6, "ar": 0.4},
  "duration_seconds": 1842
}
```

Code-switching is handled by Whisper's multilingual mode — do not force a single language. Segments with `confidence < 0.75` are flagged as `"low_confidence": true` rather than silently passed through.

### Step 3: Summarization

**Model:** GPT-4o (OpenAI) or `aya:35b` via Ollama for offline use

Returns structured JSON:

```json
{
  "executive_summary": "string (3-5 sentences)",
  "key_discussion_points": ["string"],
  "decisions_made": [
    {"decision": "string", "made_by": "SPEAKER_01", "timestamp": "00:14:32"}
  ],
  "action_items": [
    {"item": "string", "assignee": "string or null", "deadline": "date or null"}
  ],
  "open_questions": ["string"]
}
```

### Step 4: Sentiment Analysis

**Model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`

```json
{
  "overall": {"positive": 0.52, "neutral": 0.33, "negative": 0.15},
  "per_speaker": {
    "SPEAKER_00": {
      "overall": {"positive": 0.60, "neutral": 0.30, "negative": 0.10},
      "trajectory": [
        {"time_window": "0-10min", "dominant": "positive", "score": 0.71},
        {"time_window": "10-20min", "dominant": "neutral",  "score": 0.50}
      ]
    }
  },
  "topic_sentiment": [
    {"topic": "budget proposal", "sentiment": "negative", "score": 0.22}
  ],
  "notable_moments": [
    {"timestamp": "00:22:14", "speaker": "SPEAKER_00", "note": "sharp negative shift"}
  ]
}
```

### Step 5: PDF Generation

**Library:** WeasyPrint 60+

**Sections:** cover page, executive summary, key points, decisions, action items table, open questions, sentiment charts (SVG), full transcript.

Arabic uses `Noto Naskh Arabic` (bundled in Docker image) with `direction: rtl` CSS. Mixed Arabic/English paragraphs use explicit `dir` attributes.

### Step 6: Encryption and storage

Sensitive fields encrypted in MySQL; PDF encrypted on disk. See [Encryption Design](#encryption-design).

---

## Subsystem 2 — RAG Chatbot

### Embeddings pipeline

Runs after Subsystem 1 completes (chained Celery task):

1. Decrypt stored PDF using `FILE_ENCRYPTION_KEY`
2. Chunk transcript (by speaker turn, max 400 tokens, 50-token overlap) and summary sections
3. Embed with `intfloat/multilingual-e5-large` (`"passage: "` prefix for chunks)
4. Store in Qdrant with payload including `client_id`, `meeting_id`, `chunk_type`, `text`, timestamps

### Multi-tenant vector isolation

The `client_id` filter is applied at the **Qdrant query level** using a `must` condition — never left to the LLM prompt alone.

```python
# src/rag/retriever.py — simplified
def retrieve(query_embedding, client_id: str, top_k: int = 5):
    if not client_id:
        raise ValueError("client_id required for retrieval")
    # Qdrant search with mandatory Filter(must=[FieldCondition(key="client_id", ...)])
```

### Conversation flow

```
User message
    → Extract client_id from JWT (never from message body)
    → Load history from Redis (scoped to client_id:conversation_id)
    → Embed query ("query: " prefix)
    → Retrieve top-5 chunks (HARD client_id filter)
    → If no chunks → refusal: "I don't have information about that in your meetings."
    → LLM generates response with citations
    → Append turn to Redis history
    → Return response + citations + source_meeting_ids
```

### Gradio UI

Open http://localhost:7860. Select Client A or Client B to set the JWT token for all requests (simulates authentication without a full login page).

### Required test scenarios

| Scenario | Example query | Expected behavior |
|----------|---------------|-------------------|
| Factual recall | "What did we decide about the budget?" | Answer with citation |
| Cross-meeting synthesis | "Summarize all action items assigned to Ahmed" | Aggregates across meetings |
| Temporal query | "What were the main concerns this month?" | Filters by date context |
| Refusal | Question not in any meeting | Explicit "no information" — no hallucination |
| Isolation | Client A asks about Client B content | "No information found" — no leakage |

---

## Database Schema

Defined in [`infra/mysql/init.sql`](infra/mysql/init.sql):

```sql
CREATE TABLE clients (
    client_id  VARCHAR(64) PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meetings (
    meeting_id        VARCHAR(64)  PRIMARY KEY,
    client_id         VARCHAR(64)  NOT NULL,
    meeting_title_enc TEXT         NOT NULL,
    participants_enc  TEXT         NOT NULL,
    transcript_enc    LONGTEXT,
    summary_enc       LONGTEXT,
    sentiment_enc     LONGTEXT,
    meeting_date      DATE,
    duration_seconds  INT,
    language_mix      JSON,
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE processing_status (
    meeting_id    VARCHAR(64) PRIMARY KEY,
    status        ENUM('queued','transcribing','summarizing',
                       'generating_pdf','encrypting','embedding','complete','failed'),
    error_message TEXT,
    started_at    DATETIME,
    completed_at  DATETIME,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE encrypted_artifacts (
    artifact_id   VARCHAR(64) PRIMARY KEY,
    meeting_id    VARCHAR(64) NOT NULL,
    artifact_type ENUM('pdf','transcript_raw'),
    file_path     TEXT        NOT NULL,
    file_iv       VARCHAR(64) NOT NULL,
    created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE participants (
    id            INT         AUTO_INCREMENT PRIMARY KEY,
    meeting_id    VARCHAR(64) NOT NULL,
    speaker_label VARCHAR(32) NOT NULL,
    name_enc      TEXT,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);
```

Pre-seeded clients: `client_a`, `client_b`.

---

## Encryption Design

### Algorithm: AES-256-GCM

Authenticated encryption provides confidentiality and integrity. Tampered ciphertext is detected before decryption.

### Database field encryption

Sensitive fields (`meeting_title`, `participants`, `transcript`, `summary`, `sentiment`) are encrypted at the application layer before MySQL write. Each encryption uses a fresh 96-bit IV prepended to the ciphertext (base64-encoded for storage).

### PDF file encryption

PDFs are encrypted before writing to disk. The IV is stored in `encrypted_artifacts.file_iv` (the IV is not secret; only the key must remain secret).

### Key management

| Rule | Detail |
|------|--------|
| Keys live in `.env` only | Loaded via `python-dotenv`; never baked into Docker image layers |
| Separate keys | `FIELD_ENCRYPTION_KEY` and `FILE_ENCRYPTION_KEY` are distinct |
| Never acceptable | Hardcoded keys, keys in MySQL alongside ciphertext, keys in git |

**Production path (documented, not implemented):** Replace env-var keys with AWS KMS or HashiCorp Vault. Only `get_field_key()` and `get_file_key()` in [`src/security/key_management.py`](src/security/key_management.py) need changing.

---

## Multi-Tenancy and Isolation

### Threat model

| Threat | Mitigation |
|--------|------------|
| Client A queries Client B data directly | JWT `client_id` extracted server-side; body `client_id` ignored |
| Cross-tenant retrieval via semantic similarity | Qdrant `must` filter applied **before** similarity ranking |
| Prompt injection from document content | Chunks presented as data, not instructions; vector filter cannot be overridden by LLM |
| Conversation history leakage | Redis keys scoped as `{client_id}:{conversation_id}` |
| Guessed `meeting_id` from another tenant | All read endpoints verify `meeting.client_id == jwt.client_id` |

### Isolation layers (defense in depth)

```
Layer 1: JWT authentication        → client_id from signed token, never request body
Layer 2: API endpoint validation   → every meeting read checks client_id ownership
Layer 3: Vector DB query filter    → Qdrant must-filter on client_id at query time
Layer 4: LLM system prompt scope   → secondary enforcement, not primary
Layer 5: Response audit            → log client_id + meeting_ids returned per query
```

Filtering tenant data **only in the LLM prompt** is not isolation and fails the evaluation criteria.

---

## Arabic Handling

### Speech-to-text

- Whisper large-v3 has strong MSA support; dialect WER is higher (~15–25% vs ~8% for MSA)
- Code-switching handled by multilingual beam search — do not pass `language=` to force one language
- Low-confidence segments flagged rather than silently passed through

### Embeddings

`intfloat/multilingual-e5-large` covers 100+ languages including Arabic and handles code-switched text. AraBERT was considered but lacks English coverage needed for mixed meetings.

### PDF rendering

- Font: Noto Naskh Arabic (bundled in Docker image)
- WeasyPrint CSS `direction: rtl` with explicit `dir` attributes for mixed paragraphs
- Verified by `test_pdf_generates_bytes` in [`tests/test_pipeline.py`](tests/test_pipeline.py)

### LLM generation

GPT-4o handles Arabic well. For Ollama, use `aya:35b` for better Arabic output quality.

---

## API Reference

All endpoints except `/health` require:

```
Authorization: Bearer <token>
```

### Meetings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth) |
| POST | `/meetings/ingest` | Submit a recording for processing |
| GET | `/meetings/{meeting_id}/status` | Check processing state |
| GET | `/meetings/{meeting_id}/summary` | Retrieve decrypted summary |
| GET | `/meetings/{meeting_id}/pdf` | Download decrypted PDF |
| GET | `/clients/{client_id}/meetings` | List all meetings for a client |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat/query` | Send a message to the RAG chatbot |
| GET | `/chat/{conversation_id}/history` | Retrieve conversation history |
| DELETE | `/chat/{conversation_id}` | Clear conversation history |

Interactive documentation: http://localhost:8000/docs

### Example: ingest a meeting

```bash
curl -X POST http://localhost:8000/meetings/ingest \
  -H "Authorization: Bearer $CLIENT_A_TOKEN" \
  -F "recording_file=@data/sample_meetings/client_a_meeting_1.wav" \
  -F "meeting_id=meeting-001" \
  -F "client_id=client_a" \
  -F "meeting_title=Q1 Planning Session" \
  -F 'participants=["Ahmed", "Sara", "Khaled"]' \
  -F "meeting_date=2026-02-14"
```

### Example: check status

```bash
curl http://localhost:8000/meetings/meeting-001/status \
  -H "Authorization: Bearer $CLIENT_A_TOKEN"
```

### Example: chat query

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Authorization: Bearer $CLIENT_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What action items were assigned to Ahmed?",
    "conversation_id": "conv-001"
  }'
```

---

## Running Tests

```bash
# All tests
docker compose exec api pytest tests/ -v

# Isolation tests only (critical path)
docker compose exec api pytest tests/test_isolation.py -v

# With coverage
docker compose exec api pytest tests/ --cov=src --cov-report=term-missing
```

### Test coverage matrix

| Test | File | Verifies |
|------|------|----------|
| `test_client_a_cannot_see_client_b` | `test_isolation.py` | Client A cannot retrieve Client B content |
| `test_vector_filter_not_bypassed` | `test_isolation.py` | Qdrant query without `client_id` raises error |
| `test_jwt_client_id_not_from_request_body` | `test_isolation.py` | Body `client_id` ignored; JWT always used |
| `test_cross_client_meeting_access_denied` | `test_isolation.py` | Meeting read blocked across tenants |
| `test_field_roundtrip` | `test_encryption.py` | Encrypt → decrypt returns original |
| `test_field_encrypted_is_not_plaintext` | `test_encryption.py` | Raw DB value unreadable without key |
| `test_tampered_ciphertext_raises` | `test_encryption.py` | GCM integrity verification works |
| `test_refusal_on_unknown_topic` | `test_rag.py` | Refusal instead of hallucination |
| `test_cross_meeting_synthesis` | `test_rag.py` | Aggregates action items across meetings |
| `test_arabic_query` | `test_rag.py` | Arabic query retrieves Arabic content |
| `test_pdf_generates_bytes` | `test_pipeline.py` | PDF generation produces valid output |

---

## Loading Sample Data

After `docker compose up` and JWT tokens are configured:

```bash
docker compose exec api python -m scripts.ingest_samples
```

This script:

1. POSTs all 6 recordings with correct `client_id` assignments (client_a: 1–3, client_b: 4–6)
2. Polls status until each reaches `"complete"`
3. Triggers the embeddings pipeline for each

Expected time: **10–20 minutes** depending on hardware (longer on CPU-only).

Or ingest manually using the [curl examples](#example-ingest-a-meeting) above.

---

## Demo Walkthrough

For the 5-minute screen recording ([`demo/walkthrough.mp4`](demo/walkthrough.mp4)), cover:

| Time | Action |
|------|--------|
| 0:00–0:30 | `docker compose up` — show all services starting healthy |
| 0:30–1:30 | Ingest one meeting via `/docs`, poll status until complete, download PDF |
| 1:30–2:00 | Open PDF — show Arabic RTL, action items table, sentiment section |
| 2:00–3:30 | Gradio UI as Client A: factual recall, cross-meeting synthesis, refusal test |
| 3:30–4:30 | Switch to Client B, ask about Client A-only content — show isolation |
| 4:30–5:00 | Run `pytest tests/test_isolation.py -v` — all green |

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| API framework | FastAPI | Async, auto OpenAPI docs |
| Task queue | Celery + Redis | Decouples long STT jobs from HTTP lifecycle |
| STT | faster-whisper large-v3 | Best open-source Arabic/EN; 2–4× faster than original Whisper |
| Diarization | pyannote 3.1 | State of the art; integrates with Whisper timestamps |
| Summarization | GPT-4o / aya:35b | Quality vs offline tradeoff |
| Sentiment | twitter-xlm-roberta | Multilingual, lightweight on CPU |
| PDF | WeasyPrint | HTML→PDF with CSS RTL support |
| Embeddings | multilingual-e5-large | Arabic + English + code-switching; E5 instruction format |
| Vector DB | Qdrant | Native payload filtering for tenant isolation |
| DB | MySQL 8.0 | Required by spec |
| Encryption | AES-256-GCM | Authenticated encryption, industry standard |
| Chat UI | Gradio | Spec-approved, minimal setup |

---

## Known Limitations

- **Dialect STT accuracy:** Whisper WER on Egyptian/Levantine Arabic ~20–30% vs ~8% for MSA. Dialect fine-tuning would help significantly.
- **Diarization:** pyannote struggles with 4+ overlapping speakers; labels may drift on long recordings.
- **Scalability:** Single Celery worker processes jobs serially; horizontal scaling and job priorities not implemented.
- **Key rotation:** No rotation mechanism; changing `FIELD_ENCRYPTION_KEY` requires re-encrypting all DB fields.
- **Conversation persistence:** Redis history lost on Redis restart.
- **Cost:** GPT-4o summarization ~$0.30–0.80 per 1-hour meeting. STT and embeddings are local (free).

---

## Documentation and Deliverables

| Artifact | Path | Description |
|----------|------|-------------|
| Source code | `/src` | Application code |
| Infrastructure | `/infra` | Dockerfiles, MySQL schema |
| Technical writeup | [`docs/writeup.pdf`](docs/writeup.pdf) | Architecture, model choices, encryption, metrics (max 4 pages) |
| Architecture diagram | [`docs/architecture.png`](docs/architecture.png) | System components and data flow |
| Demo recording | [`demo/walkthrough.mp4`](demo/walkthrough.mp4) | 5-minute end-to-end walkthrough |
| Tests | `/tests` | Isolation, encryption, pipeline, RAG |
| Environment template | [`.env.example`](.env.example) | All required configuration variables |

The writeup covers: architecture diagram, model/tool choices, encryption strategy, multi-tenancy design, Arabic handling, self-reported metrics, known limitations, and cost estimates.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Worker fails on first job with HuggingFace error | Missing or invalid `HF_TOKEN` | Create token at https://huggingface.co/settings/tokens; accept pyannote model license |
| API container OOM / worker killed | Whisper large-v3 needs ~10 GB RAM | Set `WHISPER_MODEL=medium` and `WHISPER_DEVICE=cpu` |
| `SKIP (not found)` in ingest script | Sample files not in expected paths | Follow [Sample Data Setup](#sample-data-setup) |
| Chat UI returns 401 | JWT tokens not set or expired | Regenerate tokens and update `.env`; restart `api` and `ui` |
| First job very slow | Models downloading to `model_cache` volume | Normal on first run; subsequent jobs are faster |
| PDF Arabic renders as boxes | Font not loaded in container | Rebuild images: `docker compose up --build` |
| Qdrant healthcheck failing | Container still starting | Wait 30–60 s; check `docker compose ps` |
| CUDA not detected in worker | No GPU passed to container | Set `WHISPER_DEVICE=cpu` and `EMBEDDING_DEVICE=cpu` |
| OpenAI errors during summarization | Missing or invalid `OPENAI_API_KEY` | Set key in `.env`; or switch to `LLM_PROVIDER=ollama` |

### View logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f ui
```

### Reset all data

```bash
docker compose down -v   # WARNING: deletes mysql_data, qdrant_data, pdf_storage volumes
docker compose up --build
```

---

## Submission Checklist

Before sharing the private GitHub repo with evaluators:

- [ ] [`README.md`](README.md) — setup and run instructions (this file)
- [ ] `/src` — complete application code
- [ ] `/infra` — docker-compose, Dockerfiles, schema, `.env.example`
- [ ] [`docs/writeup.pdf`](docs/writeup.pdf) — technical writeup (≤ 4 pages)
- [ ] [`docs/architecture.png`](docs/architecture.png) — architecture diagram
- [ ] [`demo/walkthrough.mp4`](demo/walkthrough.mp4) — 5-minute demo
- [ ] `/tests` — isolation, encryption, pipeline, and RAG tests
- [ ] `.env.example` — all variables documented, no real secrets
- [ ] `docker compose up --build` works on a fresh clone with only `.env` configured
- [ ] No hardcoded API keys, encryption keys, or DB credentials in source code

---

## License

Private submission for evaluation. All rights reserved unless otherwise specified by the repository owner.

<!-- CHECKPOINT id="ckpt_mps96dj5_6q1v4f" time="2026-05-30T11:13:55.457Z" note="auto" fixes=0 questions=0 highlights=0 sections="" -->

<!-- CHECKPOINT id="ckpt_mps9j8i4_e408bi" time="2026-05-30T11:23:55.468Z" note="auto" fixes=0 questions=0 highlights=0 sections="" -->

<!-- CHECKPOINT id="ckpt_mps9w3h1_091sjj" time="2026-05-30T11:33:55.477Z" note="auto" fixes=0 questions=0 highlights=0 sections="" -->
