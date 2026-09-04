# Clinevo Smart Inbox Assistant

A human-in-the-loop Smart Inbox Assistant for healthcare and pharmacovigilance shared mailboxes.

## Architecture

```text
Shared Mailbox / IMAP (or Mock)
            │
            ▼
   Spring Boot Backend (Java 21)
     ├── MIME Email Parser
     ├── Idempotency Check (message_id / SHA-256)
     ├── File System Storage (PDF / Attachments)
     ├── Oracle 23ai Database (Persistence & Audit)
     └── In-Process Job Queue (BlockingQueue)
            │
            ▼
    Background JobWorker
            │
            ▼
    FastAPI AI Service (Python)
            │
            ▼
    Angular Reviewer Dashboard
```

## Quick Start with Docker Compose

Ensure Docker and Docker Compose are installed and running.

```bash
# 1. Copy environment template if not already present
cp .env.example .env

# 2. Build and launch all services
docker compose up --build
```

### Services & Endpoints

| Service | Port | Endpoint |
|---|---|---|
| Reviewer UI | 4200 | `http://localhost:4200` |
| Spring Boot Backend | 8080 | `http://localhost:8080/api/emails` |
| Spring Boot Health | 8080 | `http://localhost:8080/actuator/health` |
| FastAPI AI Service | 8000 | `http://localhost:8000/health` |
| Oracle Database | 1521 | `localhost:1521/FREEPDB1` |

## AI Document Understanding & Pharmacovigilance Intelligence

The AI microservice (`:8000`) performs multi-label classification (`ICSR`, `PQC`, `MI`, `NOT_RELEVANT`), domain fact extraction, and grounded clinical summaries:

- **Primary Model**: `Qwen/Qwen2-VL-2B-Instruct` (or `Qwen3-VL-2B-Instruct`), chosen specifically for high semantic reasoning while running smoothly within laptop hardware constraints (fits within 8–16 GB system memory).
- **Execution Modes**:
  - `USE_MOCK_AI=false` (Default): Runs real Qwen model inference. Model weights are cached in the persistent Docker volume `huggingface-cache` so they only download once.
  - `AI_API_BASE`: Connects to a local OpenAI-compatible inference server (such as Ollama or vLLM at `http://host.docker.internal:11434/v1`).
  - `USE_MOCK_AI=true`: Deterministic regex/keyword fallback mode for lightweight offline testing.
- **Hardware-Aware Loading**: Automatically selects device allocation (`low_cpu_mem_usage=True`, `torch.float32` on CPU, `torch.bfloat16` on CUDA GPU).
- **Acute Clinical Safety Safeguards**: Emergency reactions (e.g. heart attacks, cardiac arrests, anaphylaxis, severe rashes) and common phonetic typos (e.g. "alergy", "paracetomol") are recognized as life-threatening `ICSR` cases and strictly protected against false classification as `NOT_RELEVANT`.

## Module 1 — Foundation Completed Capabilities

- [x] Multi-container Docker Compose infrastructure with network and persistent volumes (`oracle-data`, `document-storage`, `huggingface-cache`).
- [x] Oracle 23ai Free database schema DDL and seed scripts.
- [x] Spring Boot 3.3 backend connecting to Oracle with JPA/Hibernate.
- [x] Mailbox abstraction: `MockMailboxClient` (deterministic local tests) and `ImapMailboxClient` (live IMAP/IMAPS).
- [x] MIME/RFC822 Email parser extracting text/HTML bodies and attachments.
- [x] Attachment storage with SHA-256 integrity checks.
- [x] Idempotency: Duplicate emails with identical `message_id` are skipped without re-processing.
- [x] Processing jobs: PDF attachments produce a `ProcessingJob` with state `QUEUED`; non-PDFs are logged as `NOT_SUPPORTED`.
- [x] Transactional consistency: Job IDs are enqueued into the in-process `BlockingQueue` only after database commit.
- [x] Background `JobWorker` consuming jobs and recording state transitions (`QUEUED` -> `PROCESSING` -> `COMPLETED`).
- [x] Audit trail recording all lifecycle actions (`EMAIL_RECEIVED`, `JOB_QUEUED`, `JOB_STARTED`, `JOB_COMPLETED`).
- [x] Real Qwen2-VL inference by default with persistent volume caching and clinical safety fallback.
- [x] Automated unit and integration test suite.
