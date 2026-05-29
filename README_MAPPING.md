# AI Meeting Intelligence System

A production-shaped prototype of an AI-powered meeting intelligence platform with two integrated subsystems:
- **Subsystem 1**: Post-meeting processing pipeline (transcription → summarization → sentiment → encrypted PDF + DB storage)
- **Subsystem 2**: Per-client RAG chatbot with hard multi-tenant isolation

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Environment Configuration](#environment-configuration)
5. [Architecture Overview](#architecture-overview)
6. [Subsystem 1 — Processing Pipeline](#subsystem-1--processing-pipeline)
7. [Subsystem 2 — RAG Chatbot](#subsystem-2--rag-chatbot)
8. [Database Schema](#database-schema)
9. [Encryption Design](#encryption-design)
10. [Multi-Tenancy & Isolation](#multi-tenancy--isolation)
11. [Arabic Handling](#arabic-handling)
12. [API Reference](#api-reference)
13. [Running Tests](#running-tests)
14. [Loading Sample Data](#loading-sample-data)
15. [Demo Walkthrough](#demo-walkthrough)
16. [Technology Choices & Rationale](#technology-choices--rationale)
17. [Known Limitations](#known-limitations)

---

## Project Structure

```
/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── routers/
│   │   │   ├── meetings.py          # POST /meetings/ingest, GET /meetings/{id}/...
│   │   │   ├── clients.py           # GET /clients/{id}/meetings
│   │   │   └── chat.py              # POST /chat/query
│   │   └── dependencies.py          # Auth, DB session injection
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── ingestion.py             # Multipart upload handler, job queuing
│   │   ├── transcription.py         # Whisper STT + pyannote diarization
│   │   ├── summarization.py         # LLM summarization (structured output)
│   │   ├── sentiment.py             # Per-speaker sentiment + trajectory
│   │   └── pdf_generator.py         # WeasyPrint PDF with Arabic RTL support
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py            # Chunk + embed transcripts/summaries
│   │   ├── vector_store.py          # Qdrant client with tenant-scoped queries
│   │   ├── retriever.py             # Filtered retrieval (client_id hard filter)
│   │   └── chatbot.py               # Multi-turn conversation, citation, refusal
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── crud.py                  # DB operations
│   │   └── session.py               # DB connection pool
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── encryption.py            # AES-256-GCM encrypt/decrypt helpers
│   │   ├── key_management.py        # Key derivation, env-based key loading
│   │   └── auth.py                  # JWT validation, client_id extraction
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   └── celery_app.py            # Celery worker + task definitions
│   │
│   └── ui/
│       └── chatbot_ui.py            # Gradio interface for RAG chatbot
│
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── Dockerfile.ui
│   ├── mysql/
│   │   └── init.sql                 # Schema migrations (run on first start)
│   └── .env.example
│
├── docs/
│   ├── writeup.pdf
│   └── architecture.png
│
├── demo/
│   └── walkthrough.mp4
│
├── tests/
│   ├── test_isolation.py            # Multi-tenant isolation guarantees
│   ├── test_encryption.py           # Encryption round-trip tests
│   ├── test_pipeline.py             # End-to-end processing tests
│   └── test_rag.py                  # RAG retrieval + refusal tests
│
├── data/
│   └── sample_meetings/             # Place the 6 provided recordings here
│
├── .env.example
└── README.md
```

---

## Prerequisites

- **Docker** 24+ and **Docker Compose** v2
- **Python** 3.11+ (only needed if running outside Docker)
- At least **16 GB RAM** (Whisper large-v3 needs ~10 GB; 8 GB minimum with medium model)
- At least **20 GB disk** (models cache + encrypted file store)
- **GPU optional but recommended** for STT (CUDA 11.8+ or Apple MPS)

---

## Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd ai-meeting-intelligence

# 2. Copy env template and fill in values
cp .env.example .env
# Edit .env — see Environment Configuration section

# 3. Place the 6 sample recordings in data/sample_meetings/
#    Expected filenames (adjust in .env if different):
#    client_a_meeting_1.mp4  client_a_meeting_2.mp4  client_a_meeting_3.mp4
#    client_b_meeting_1.mp4  client_b_meeting_2.mp4  client_b_meeting_3.mp4

# 4. Start all services
docker-compose up --build

# 5. Wait for services to be healthy (~2-3 min on first run, models download)
#    Watch for: "Application startup complete" from the API container

# 6. Open the chatbot UI
open http://localhost:7860

# 7. Open the API docs
open http://localhost:8000/docs
```

---

## Environment Configuration

Copy `.env.example` to `.env` and fill in all values. **Never commit `.env`.**

```dotenv
# ── Database ──────────────────────────────────────────────
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=meeting_intelligence
MYSQL_USER=app_user
MYSQL_PASSWORD=<strong-password-here>
MYSQL_ROOT_PASSWORD=<strong-root-password-here>

# ── Encryption ────────────────────────────────────────────
# 32-byte hex key for AES-256-GCM (generate with: openssl rand -hex 32)
FIELD_ENCRYPTION_KEY=<hex-string>
# Separate key for PDF file encryption
FILE_ENCRYPTION_KEY=<hex-string>

# ── JWT Auth ──────────────────────────────────────────────
JWT_SECRET_KEY=<random-string>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ── LLM (choose one) ──────────────────────────────────────
# Option A: OpenAI API
OPENAI_API_KEY=<your-key>
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o

# Option B: Local Ollama (free, slower)
# LLM_PROVIDER=ollama
# LLM_MODEL=aya:35b        # good Arabic support

# ── STT ───────────────────────────────────────────────────
WHISPER_MODEL=large-v3     # or medium for lower RAM
WHISPER_DEVICE=cuda        # or cpu / mps (Apple Silicon)

# ── Embeddings ────────────────────────────────────────────
EMBEDDING_MODEL=intfloat/multilingual-e5-large
EMBEDDING_DEVICE=cuda      # or cpu

# ── Vector DB ─────────────────────────────────────────────
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=meetings

# ── Celery / Redis ────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Storage ───────────────────────────────────────────────
ENCRYPTED_PDF_DIR=/app/storage/pdfs

# ── Clients (pre-seeded) ─────────────────────────────────
CLIENT_A_ID=client_a
CLIENT_A_TOKEN=<jwt-token-for-client-a>
CLIENT_B_ID=client_b
CLIENT_B_TOKEN=<jwt-token-for-client-b>
```

### Generating keys and tokens

```bash
# Generate encryption keys
openssl rand -hex 32   # run twice, use for FIELD_ENCRYPTION_KEY and FILE_ENCRYPTION_KEY

# Generate JWT tokens for sample clients (run after docker-compose up)
docker-compose exec api python -c "
from src.security.auth import create_token
print('Client A:', create_token('client_a'))
print('Client B:', create_token('client_b'))
"
# Paste these into .env as CLIENT_A_TOKEN and CLIENT_B_TOKEN
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        docker-compose network                     │
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

**Request lifecycle (ingestion):**
1. Client POSTs to `/meetings/ingest` with recording + metadata
2. API validates auth, stores job in Redis via Celery, returns `{meeting_id, status: "queued"}`
3. Celery worker picks up the job and runs the pipeline sequentially:
   - STT → Diarization → Summarization → Sentiment → PDF → Encrypt → Store
4. Status updates written to MySQL `processing_status` table throughout
5. Client polls `GET /meetings/{id}/status` until `status: "complete"`

**Request lifecycle (chat):**
1. Client POSTs to `/chat/query` with `{message, conversation_id}` + JWT header
2. API extracts `client_id` from JWT (never from request body)
3. Retriever queries Qdrant with mandatory `client_id` filter — no filter = 400 error, not fallback
4. LLM generates response grounded in retrieved chunks, with source citations
5. Conversation history stored in Redis, scoped to `{client_id}:{conversation_id}`

---

## Subsystem 1 — Processing Pipeline

### Step 1: Ingestion endpoint

**Endpoint:** `POST /meetings/ingest`

Accepts multipart form data:
```
recording_file   (binary)     — audio or video file
meeting_id       (string)     — UUID, caller-provided or server-generated
client_id        (string)     — must match authenticated JWT client
meeting_title    (string)     — encrypted at rest
participants     (JSON array) — encrypted at rest
meeting_date     (ISO8601)    — plaintext (operational field)
```

Validates file type (mp3, mp4, wav, m4a, webm), queues a Celery task, returns immediately with `meeting_id` and `status`.

### Step 2: Transcription

**Model:** `openai/whisper-large-v3` via `faster-whisper` (CTranslate2 backend for speed)

**Diarization:** `pyannote/speaker-diarization-3.1` (requires HuggingFace token)

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

Code-switching within a single utterance is handled by Whisper's multilingual mode — do not force a single language. If `confidence < 0.75` on a segment, flag it in the transcript as `"low_confidence": true` rather than hallucinating content.

### Step 3: Summarization

**Model:** GPT-4o (or `aya:35b` via Ollama for offline use)

The prompt instructs the LLM to return a structured JSON object. Arabic content in the transcript is passed as-is; the LLM is prompted to respond in the same language as the meeting (or bilingual if mixed).

**Output schema:**
```json
{
  "executive_summary": "string (3-5 sentences)",
  "key_discussion_points": ["string", ...],
  "decisions_made": [
    {"decision": "string", "made_by": "SPEAKER_01", "timestamp": "00:14:32"}
  ],
  "action_items": [
    {"item": "string", "assignee": "string or null", "deadline": "date or null"}
  ],
  "open_questions": ["string", ...]
}
```

If STT confidence was flagged low on a segment that feeds into a key point, note it in the summary as `"[low confidence transcript]"`.

### Step 4: Sentiment Analysis

**Model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual` for per-segment scoring, aggregated by speaker and topic window.

**Output schema:**
```json
{
  "overall": {"positive": 0.52, "neutral": 0.33, "negative": 0.15},
  "per_speaker": {
    "SPEAKER_00": {
      "overall": {"positive": 0.60, "neutral": 0.30, "negative": 0.10},
      "trajectory": [
        {"time_window": "0-10min", "dominant": "positive", "score": 0.71},
        {"time_window": "10-20min", "dominant": "neutral",  "score": 0.50},
        {"time_window": "20-30min", "dominant": "negative", "score": 0.38}
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

**Arabic rendering requirements:**
- Font: `Noto Naskh Arabic` (bundled in Docker image — do not rely on system fonts)
- RTL direction set via CSS: `direction: rtl; unicode-bidi: embed`
- Mixed content (Arabic + English in same paragraph): use `<span dir="ltr">` for inline English within Arabic paragraphs
- Arabic text must pass through a Unicode normalization step before rendering

**PDF sections (in order):**
1. Cover page: meeting title, date, participants, client ID
2. Executive summary
3. Key discussion points
4. Decisions made
5. Action items table
6. Open questions
7. Sentiment analysis (charts rendered as SVG, embedded inline)
8. Full transcript (collapsible in HTML, always present in PDF)

### Step 6: Encryption

See [Encryption Design](#encryption-design) section below.

---

## Subsystem 2 — RAG Chatbot

### Embeddings pipeline

Runs after Subsystem 1 completes. Triggered as a Celery task chained to the ingestion job.

**Steps:**
1. Decrypt the stored PDF using `FILE_ENCRYPTION_KEY`
2. Also use the plaintext transcript and summary JSON directly (better chunking control)
3. Chunk strategy:
   - Transcript: chunk by speaker turn, max 400 tokens, 50-token overlap
   - Summary sections: each section (executive summary, action items, etc.) as its own chunk
4. Embed each chunk using `intfloat/multilingual-e5-large`
   - Prepend `"query: "` for queries, `"passage: "` for chunks (required by E5 models)
5. Store in Qdrant with payload:
   ```json
   {
     "client_id": "client_a",
     "meeting_id": "uuid",
     "meeting_title": "Q1 Planning",
     "meeting_date": "2026-02-14",
     "chunk_type": "transcript|summary|action_items",
     "speaker": "SPEAKER_01",
     "text": "chunk text",
     "timestamp_start": 842.0
   }
   ```

### Multi-tenant vector isolation

**Critical:** The `client_id` filter is applied at the Qdrant query level using a `must` condition — it is never left to the LLM prompt alone.

```python
# src/rag/retriever.py
from qdrant_client.models import Filter, FieldCondition, MatchValue

def retrieve(query_embedding, client_id: str, top_k: int = 5):
    # This filter is MANDATORY — if client_id is None, raise, never query
    if not client_id:
        raise ValueError("client_id required for retrieval")

    results = qdrant.search(
        collection_name=COLLECTION,
        query_vector=query_embedding,
        query_filter=Filter(
            must=[FieldCondition(
                key="client_id",
                match=MatchValue(value=client_id)
            )]
        ),
        limit=top_k
    )
    return results
```

### Chatbot conversation flow

```
User message
    │
    ▼
Extract client_id from JWT (never from message body)
    │
    ▼
Load conversation history from Redis (scoped to client_id:conversation_id)
    │
    ▼
Embed query with multilingual-e5-large ("query: " prefix)
    │
    ▼
Retrieve top-5 chunks from Qdrant (HARD client_id filter)
    │
    ▼
If no chunks found → return refusal: "I don't have information about that in your meetings."
    │
    ▼
Build LLM prompt:
  - System: "You are a meeting assistant for {client_id}. Answer ONLY from the provided context.
             If the answer is not in the context, say so explicitly. Never mention other clients."
  - Context: retrieved chunks with source labels
  - History: last N turns
  - User message
    │
    ▼
LLM generates response with citations (format: [Meeting: Q1 Planning, 2026-02-14])
    │
    ▼
Append turn to Redis conversation history
    │
    ▼
Return response + citations + source_meeting_ids
```

### Gradio UI

Accessible at `http://localhost:7860`

The UI has a client selector (Client A / Client B) that sets the JWT token for all requests. This simulates the authentication flow without a full login page.

---

## Database Schema

```sql
-- infra/mysql/init.sql

CREATE TABLE clients (
    client_id     VARCHAR(64)  PRIMARY KEY,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE meetings (
    meeting_id        VARCHAR(64)   PRIMARY KEY,
    client_id         VARCHAR(64)   NOT NULL,
    -- Encrypted fields (AES-256-GCM, stored as base64 with prepended IV)
    meeting_title_enc TEXT          NOT NULL,
    participants_enc  TEXT          NOT NULL,
    transcript_enc    LONGTEXT,
    summary_enc       LONGTEXT,
    sentiment_enc     LONGTEXT,
    -- Plaintext operational fields
    meeting_date      DATE,
    duration_seconds  INT,
    language_mix      JSON,
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

CREATE TABLE processing_status (
    meeting_id    VARCHAR(64)   PRIMARY KEY,
    status        ENUM('queued','transcribing','summarizing',
                       'generating_pdf','encrypting','embedding','complete','failed'),
    error_message TEXT,
    started_at    DATETIME,
    completed_at  DATETIME,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE encrypted_artifacts (
    artifact_id   VARCHAR(64)   PRIMARY KEY,
    meeting_id    VARCHAR(64)   NOT NULL,
    artifact_type ENUM('pdf','transcript_raw'),
    file_path     TEXT          NOT NULL,   -- path to encrypted file on disk
    file_iv       VARCHAR(64)   NOT NULL,   -- IV used for file encryption (NOT the key)
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);

CREATE TABLE participants (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    meeting_id    VARCHAR(64)   NOT NULL,
    speaker_label VARCHAR(32)   NOT NULL,   -- SPEAKER_00, SPEAKER_01, etc.
    name_enc      TEXT,                     -- encrypted display name if known
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);
```

---

## Encryption Design

### Algorithm: AES-256-GCM

**Why GCM:** Authenticated encryption — provides both confidentiality and integrity. Tampered ciphertext is detectable before decryption. Widely supported and well-understood.

### Database field encryption

Sensitive fields (`meeting_title`, `participants`, `transcript`, `summary_text`, `sentiment_data`) are encrypted at the application layer before being written to MySQL.

```python
# src/security/encryption.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_field(plaintext: str, key_hex: str) -> str:
    """Returns base64(iv + ciphertext + tag)"""
    key = bytes.fromhex(key_hex)
    iv = os.urandom(12)              # 96-bit IV, fresh per encryption
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, plaintext.encode(), None)
    return base64.b64encode(iv + ct).decode()

def decrypt_field(encoded: str, key_hex: str) -> str:
    raw = base64.b64decode(encoded)
    iv, ct = raw[:12], raw[12:]
    key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ct, None).decode()
```

### PDF file encryption

PDFs are encrypted before writing to disk using the same AES-256-GCM scheme. The IV is stored in the `encrypted_artifacts` table (the IV is not secret; only the key must remain secret).

### Key management

Keys live exclusively in `.env` (loaded via `python-dotenv`). In the docker-compose setup this maps to a `.env` file that is bind-mounted but never copied into the image layer.

**What is NOT acceptable (auto-fail per spec):**
- Hardcoded keys in any `.py` file
- Keys stored in MySQL alongside the encrypted data
- Keys committed to git (`.env` is in `.gitignore`)

**Path to production key management (documented, not implemented):**
For a real deployment, replace env-var keys with calls to AWS KMS or HashiCorp Vault. The `key_management.py` module is structured to make this swap straightforward — the `get_field_key()` and `get_file_key()` functions are the only callsites that need changing.

---

## Multi-Tenancy & Isolation

### Threat model

| Threat | Mitigation |
|---|---|
| Client A queries Client B data directly | JWT client_id extracted server-side; request body `client_id` is ignored |
| Semantically similar chunks from Client B rank high in retrieval | Qdrant `must` filter applied before similarity search, not after |
| Prompt injection from a document telling the LLM to ignore client scope | System prompt establishes scope; retrieved chunks are presented as data, not instructions; LLM cannot override the vector filter |
| Conversation history leakage between clients | Redis keys scoped as `{client_id}:{conversation_id}` — no cross-client key access |
| Client guesses another client's `meeting_id` | All read endpoints validate that `meeting.client_id == jwt.client_id` before returning data |

### Isolation layers (defense in depth)

```
Layer 1: JWT authentication        → client_id extracted from signed token, never request body
Layer 2: API endpoint validation   → every meeting read checks client_id ownership in MySQL
Layer 3: Vector DB query filter    → Qdrant must-filter on client_id at query time
Layer 4: LLM system prompt scope   → secondary enforcement, not primary
Layer 5: Response audit            → log client_id + meeting_ids returned per query
```

Failing Layer 3 alone (filtering only in the LLM prompt) is an automatic fail per spec.

---

## Arabic Handling

### STT

- Whisper large-v3 has strong Modern Standard Arabic (MSA) support
- For Egyptian and Levantine dialects, word error rate degrades (~15-25% vs ~8% for MSA) — documented in writeup
- Code-switching (Arabic mid-sentence into English or vice versa) is handled by Whisper's multilingual beam search — do not pass `language=` parameter to force a single language
- Low-confidence segments (below 0.75) are flagged rather than silently passed through

### Embeddings

`intfloat/multilingual-e5-large` covers 100 languages including Arabic and handles code-switched text well. AraBERT was considered but lacks English coverage, which breaks cross-lingual retrieval for mixed meetings.

### PDF rendering

- Font: Noto Naskh Arabic (bundled, not system-dependent)
- WeasyPrint handles CSS `direction: rtl` correctly
- Mixed Arabic/English paragraphs use Unicode Bidirectional Algorithm via explicit `dir` attributes
- Tested rendering pipeline: `pytest tests/test_pdf_arabic.py` generates a sample PDF for visual inspection

### LLM generation

GPT-4o handles Arabic generation well. When using Ollama, `aya:35b` (Cohere's multilingual model) is recommended over generic models for Arabic output quality.

---

## API Reference

All endpoints require `Authorization: Bearer <token>` header.

### Meetings

| Method | Path | Description |
|---|---|---|
| POST | `/meetings/ingest` | Submit a recording for processing |
| GET | `/meetings/{meeting_id}/status` | Check processing state |
| GET | `/meetings/{meeting_id}/summary` | Retrieve decrypted summary |
| GET | `/meetings/{meeting_id}/pdf` | Download decrypted PDF |
| GET | `/clients/{client_id}/meetings` | List all meetings for a client |

### Chat

| Method | Path | Description |
|---|---|---|
| POST | `/chat/query` | Send a message to the RAG chatbot |
| GET | `/chat/{conversation_id}/history` | Retrieve conversation history |
| DELETE | `/chat/{conversation_id}` | Clear conversation history |

### Example: ingest a meeting

```bash
curl -X POST http://localhost:8000/meetings/ingest \
  -H "Authorization: Bearer $CLIENT_A_TOKEN" \
  -F "recording_file=@data/sample_meetings/client_a_meeting_1.mp4" \
  -F "meeting_id=meeting-001" \
  -F "client_id=client_a" \
  -F "meeting_title=Q1 Planning Session" \
  -F "participants=[\"Ahmed\", \"Sara\", \"Khaled\"]" \
  -F "meeting_date=2026-02-14"
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
# Run all tests inside the API container
docker-compose exec api pytest tests/ -v

# Run only isolation tests (critical path)
docker-compose exec api pytest tests/test_isolation.py -v

# Run with coverage report
docker-compose exec api pytest tests/ --cov=src --cov-report=term-missing
```

### Key test scenarios covered

| Test | File | What it verifies |
|---|---|---|
| `test_client_a_cannot_see_client_b` | `test_isolation.py` | Query from Client A about Client B content returns "no information found" |
| `test_vector_filter_not_bypassed` | `test_isolation.py` | Direct Qdrant call without client_id filter raises error |
| `test_jwt_client_id_extraction` | `test_isolation.py` | Request body client_id is ignored; JWT client_id is always used |
| `test_encryption_roundtrip` | `test_encryption.py` | Encrypt → store → retrieve → decrypt returns original plaintext |
| `test_encrypted_field_unreadable` | `test_encryption.py` | Raw DB value is not human-readable without key |
| `test_refusal_on_unknown_topic` | `test_rag.py` | Returns refusal, not hallucination, when answer not in data |
| `test_cross_meeting_synthesis` | `test_rag.py` | Correctly aggregates action items across multiple meetings |
| `test_arabic_query` | `test_rag.py` | Arabic query retrieves Arabic content correctly |

---

## Loading Sample Data

After `docker-compose up`, load all 6 sample meetings:

```bash
# Uses the sample ingestion script
docker-compose exec api python -m scripts.ingest_samples

# This script:
# 1. POSTs all 6 recordings with correct client_id assignments
#    (client_a: meetings 1-3, client_b: meetings 4-6)
# 2. Polls status until all reach "complete"
# 3. Triggers the embeddings pipeline for each
# Expected time: ~10-20 min depending on hardware
```

Or ingest manually one-by-one using the curl examples above.

---

## Demo Walkthrough

For the 5-minute screen recording, cover these in order:

1. **(0:00–0:30)** `docker-compose up` — show all services starting healthy
2. **(0:30–1:30)** Ingest one meeting via API docs (`/docs`), show status polling until complete, download the PDF
3. **(1:30–2:00)** Open the PDF — show Arabic content renders correctly, action items table, sentiment section
4. **(2:00–3:30)** Open Gradio UI as Client A:
   - Factual recall: "What decisions were made in the planning meeting?"
   - Cross-meeting: "Summarize all action items assigned to Ahmed across all meetings"
   - Refusal: ask something not in any meeting
5. **(3:30–4:30)** Isolation test: switch to Client B in the UI, ask about something only Client A has — show "no information found"
6. **(4:30–5:00)** Briefly show `test_isolation.py` running green

---

## Technology Choices & Rationale

| Component | Choice | Why |
|---|---|---|
| API framework | FastAPI | Async, auto OpenAPI docs, fast |
| Task queue | Celery + Redis | Decouples long STT jobs from HTTP request lifecycle |
| STT | faster-whisper large-v3 | Best open-source Arabic/EN, CTranslate2 backend is 2-4x faster than original Whisper |
| Diarization | pyannote 3.1 | State of the art, integrates cleanly with faster-whisper timestamps |
| Summarization LLM | GPT-4o / aya:35b | GPT-4o best quality; aya:35b for offline/cost-sensitive |
| Sentiment | twitter-xlm-roberta | Multilingual, handles Arabic, lightweight enough to run on CPU |
| PDF | WeasyPrint | Best Python option for HTML→PDF with CSS RTL support |
| Embeddings | multilingual-e5-large | Covers Arabic + English + code-switching; E5 instruction format improves retrieval |
| Vector DB | Qdrant | Native payload filtering makes hard tenant isolation clean and auditable |
| DB | MySQL | Required by spec |
| Encryption | AES-256-GCM | Authenticated encryption, industry standard, no padding oracle risk |
| Chat UI | Gradio | Spec-approved, minimal setup, supports streaming |

---

## Known Limitations

- **Dialect STT accuracy:** Whisper large-v3 WER on Egyptian/Levantine Arabic is ~20-30% vs ~8% for MSA. A dialect-specific fine-tune (e.g. MGB-2 fine-tuned Whisper) would improve this significantly.
- **Diarization accuracy:** pyannote struggles when more than 4 speakers overlap frequently. Speaker labels may be inconsistent across long recordings.
- **Scalability:** Single Celery worker processes jobs serially. At scale, this needs horizontal worker scaling and a proper job queue with priorities.
- **Key rotation:** The current design has no key rotation mechanism. Rotating `FIELD_ENCRYPTION_KEY` requires re-encrypting all DB fields — a background migration job is not implemented.
- **Conversation persistence:** Redis conversation history is in-memory only. A Redis restart clears all conversation history.
- **Cost:** At GPT-4o pricing, a 1-hour meeting costs approximately $0.30-0.80 for summarization (varies with transcript length). STT is free (local Whisper). Embeddings are free (local model).
