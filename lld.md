# Smart Inbox Assistant — Low-Level Design (LLD)

## 1. System Overview

The **Smart Inbox Assistant** is an advisory document intelligence system for healthcare, safety, and quality review teams. It ingests clinical emails and PDF attachments, classifies them across multi-label categories (`ICSR`, `PQC`, `MI`, `NOT_RELEVANT`), extracts domain facts with 100% source traceability, and presents structured case assessments to human reviewers through an interactive review workspace.

---

## 2. Complete Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Client["1. Reviewer Client (Browser :4200)"]
        UI_Queue["Review Queue & Progress Bar"]
        UI_Exec["7-Section Case Assessment Workspace"]
        UI_Viewer["PDF Viewer & Evidence Inspector"]
        UI_Action["Review Actions (Accept / Override / Upload)"]
    end

    subgraph NginxTier["Frontend Web Tier"]
        Nginx["Nginx Reverse Proxy (:80)"]
        NginxStatic["Static Assets (HTML / CSS / JS)"]
        Nginx --> NginxStatic
        Nginx -->|/api/* proxy| Boot
    end

    subgraph Boot["2. Spring Boot Backend (:8080)"]
        EmailCtrl["EmailController & ReviewController"]
        IngestSvc["EmailIngestionService"]
        JobQ["In-Process BlockingQueue<Long>"]
        Worker["JobWorker (Async Runner)"]
        AIClient["FastAPIClient (HTTP AI Client)"]
        ResultSvc["ResultService (Persistence Transaction)"]
        AuditSvc["AuditService & MetricsService"]

        EmailCtrl --> IngestSvc
        IngestSvc --> JobQ
        JobQ --> Worker
        Worker --> AIClient
        AIClient --> ResultSvc
        ResultSvc --> AuditSvc
    end

    subgraph AIDomain["3. FastAPI AI Service (:8000)"]
        FastAPIEndpoint["POST /ai/process"]
        FormatNode["Format Detection Node"]
        ExtractNode["PyMuPDF / pdfplumber Digital Extractor"]
        OcrNode["OCR & Vision Fallback (Qwen VLM)"]
        LangNode["Language Detection & Translation"]
        DocTypeNode["Article & Document Layout Node"]
        CanonNode["Canonical Context Builder"]
        VlmNode["Qwen-VL Structured Reasoner"]
        ValNode["Pydantic & Source Validation Node"]

        FastAPIEndpoint --> FormatNode
        FormatNode -->|Digital| ExtractNode
        FormatNode -->|Scanned / Image| OcrNode
        ExtractNode --> LangNode
        OcrNode --> LangNode
        LangNode --> DocTypeNode
        DocTypeNode --> CanonNode
        CanonNode --> VlmNode
        VlmNode --> ValNode
    end

    subgraph Persistence["4. Storage & Persistence Tier"]
        OracleDB[("Oracle Database Free (:1521)<br/>10 Relational Tables")]
        VolStorage[("Shared Document Storage<br/>Original PDFs & email_body.txt")]
    end

    %% Storage Connections
    IngestSvc --> VolStorage
    IngestSvc --> OracleDB
    ResultSvc --> OracleDB
    AuditSvc --> OracleDB
    EmailCtrl <--> OracleDB
    EmailCtrl --> VolStorage
    ExtractNode --> VolStorage
    OcrNode --> VolStorage

    %% UI Connections
    UI_Queue <--> Nginx
    UI_Exec <--> Nginx
    UI_Viewer <--> Nginx
    UI_Action <--> Nginx
```

---

## 3. Repository & Package Layout

```text
smart-inbox/
├── frontend/                     # Nginx + Reviewer Workspace UI
│   ├── src/
│   │   ├── index.html            # Single Page Application & 7-section hierarchy
│   │   ├── styles.css            # Monochromatic design system tokens & layouts
│   │   └── app.js                # State management, API calls, dynamic rendering
│   ├── nginx.conf                # Nginx proxy configuration for /api and /health
│   └── Dockerfile                # Alpine Nginx container
├── backend/                      # Spring Boot 3.2 (Java 21)
│   ├── src/main/java/com/clinevo/inbox/
│   │   ├── controller/           # EmailController, ReviewController, JobController
│   │   ├── service/              # EmailService, ReviewService, ResultService, AuditService
│   │   ├── ingestion/            # EmailIngestionService, EmailParser
│   │   ├── queue/                # JobQueue (BlockingQueue), JobWorker
│   │   ├── client/               # AIClient interface & FastAPIClient implementation
│   │   ├── entity/               # JPA Entities (Email, ProcessingJob, AIResult, etc.)
│   │   ├── repository/           # Spring Data JPA Repositories
│   │   ├── dto/                  # Request/Response DTOs & ReviewDetailDto
│   │   └── exception/            # GlobalExceptionHandler & domain exceptions
│   ├── src/main/resources/       # application.yml
│   └── Dockerfile                # Multi-stage JDK 21 build
├── ai-service/                   # Python FastAPI Document Intelligence Microservice
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint, /ai/process & /health
│   │   ├── graph/                # Pipeline orchestrator & pipeline state
│   │   │   ├── pipeline.py       # Linear/graph extraction node sequence
│   │   │   └── nodes/            # Extraction, OCR, Language, Canon, VLM, Validation
│   │   ├── schemas/              # Pydantic models (Canonical, Domain, Request, Response)
│   │   └── prompts/              # System prompts & master extraction instructions
│   ├── tests/                    # Pipeline integration tests
│   └── Dockerfile                # Python 3.11 microservice container
├── database/                     # Oracle schema & initial seed scripts
├── storage/                      # Persistent storage mount for attachments
├── test-data/                    # Synthetic test emails & PDFs
├── docker-compose.yml            # Multi-container orchestration
├── .env.example                  # Environment configuration template
└── AGENTS.md                     # Safety & engineering contract
```

---

## 4. Oracle Relational Data Model (Entity-Relationship)

```mermaid
erDiagram
    EMAILS ||--o{ ATTACHMENTS : "contains"
    EMAILS ||--o{ AUDIT_LOGS : "logs"
    ATTACHMENTS ||--o{ PROCESSING_JOBS : "spawns"
    PROCESSING_JOBS ||--o| AI_RESULTS : "produces"
    PROCESSING_JOBS ||--o| PROCESSING_METRICS : "measures"
    AI_RESULTS ||--o{ CLASSIFICATIONS : "classifies"
    AI_RESULTS ||--o{ EXTRACTED_FIELDS : "extracts"
    AI_RESULTS ||--o{ IMAGE_RESULTS : "describes"
    EXTRACTED_FIELDS ||--o{ SOURCE_REFERENCES : "proven_by"

    EMAILS {
        number id PK
        string message_id UK
        string sender_email
        string subject
        string body
        string status
        timestamp received_at
    }

    ATTACHMENTS {
        number id PK
        number email_id FK
        string filename
        string sha256_hash
        string storage_path
        number file_size
        boolean is_pdf
    }

    PROCESSING_JOBS {
        number id PK
        number attachment_id FK
        string status
        number retry_count
        string error_message
        timestamp created_at
        timestamp updated_at
    }

    AI_RESULTS {
        number id PK
        number job_id FK
        string model_name
        string model_version
        string summary
        timestamp created_at
    }

    CLASSIFICATIONS {
        number id PK
        number ai_result_id FK
        string category
        number confidence
        string reason
    }

    EXTRACTED_FIELDS {
        number id PK
        number ai_result_id FK
        string field_group
        string field_name
        string field_value
        number confidence
    }

    SOURCE_REFERENCES {
        number id PK
        number extracted_field_id FK
        string source_type
        number page_number
        string text_snippet
        string bounding_box
    }

    IMAGE_RESULTS {
        number id PK
        number ai_result_id FK
        number page_number
        string image_reference
        string description
        number confidence
    }

    PROCESSING_METRICS {
        number id PK
        number job_id FK
        number total_duration_ms
        number extraction_duration_ms
        number ocr_duration_ms
        number translation_duration_ms
        number llm_duration_ms
        number validation_duration_ms
    }

    AUDIT_LOGS {
        number id PK
        number email_id FK
        string action
        string actor_id
        string actor_type
        string old_value
        string new_value
        string metadata
        timestamp created_at
    }
```

---

## 5. Job & Email Processing State Machine

```mermaid
stateDiagram-v2
    [*] --> RECEIVED : Ingest Email (IMAP / Mock / Upload)
    RECEIVED --> QUEUED : Create ProcessingJob (PDF or email_body.txt)
    
    state JobLifecycle {
        [*] --> QUEUED
        QUEUED --> PROCESSING : JobWorker Dequeues
        PROCESSING --> COMPLETED : FastAPI Returns Valid Output
        PROCESSING --> RETRYING : Error & retryCount < maxRetries
        RETRYING --> QUEUED : Exponential Backoff Re-enqueue
        PROCESSING --> REVIEW_REQUIRED : Retries Exhausted OR Hard Parse Error
        PROCESSING --> FAILED : Fatal / Unsupported Format
    }

    COMPLETED --> REVIEW_REQUIRED : Default Human Review Required
    REVIEW_REQUIRED --> REVIEWED : Reviewer Accepts OR Overrides
    REVIEW_REQUIRED --> FAILED : Job Escalation Failure
    REVIEWED --> [*]
    FAILED --> [*]
```

---

## 6. Document Understanding Pipeline (AI Microservice)

```mermaid
flowchart TD
    Start(["Input: Document Storage Path + Email Text"]) --> Detect{"Format Detection"}

    Detect -->|Digital PDF| PyMu["PyMuPDF / pdfplumber<br/>- Extract text coordinates & layout<br/>- Preserve page numbers<br/>- Extract table structures"]
    Detect -->|Scanned / Image| VisionNode["Render Page to Image<br/>- Qwen Vision OCR & Handwriting<br/>- Bounding box extraction<br/>- Low confidence sets reviewRequired"]
    Detect -->|Plain Text / Email Body| RawText["Direct Text Parser<br/>- Extract paragraphs & timestamps"]

    PyMu --> Lang{"Language Detection"}
    VisionNode --> Lang
    RawText --> Lang

    Lang -->|Non-English| Translate["Translation Node<br/>- Preserve original language text<br/>- Store English translation alongside<br/>- Maintain source page link"]
    Lang -->|English| DocType{"Document Classifier"}
    Translate --> DocType

    DocType -->|Article PDF| ArticleNode["Article Layout Processor<br/>- Filter reference/bibliography sections<br/>- Handle multi-column layout<br/>- Isolate patient case narrative"]
    DocType -->|Clinical Report / Form| CanonicalBuilder["Canonical Context Builder"]
    ArticleNode --> CanonicalBuilder

    CanonicalBuilder --> Assembly["CanonicalCaseContext<br/>- Normalized email metadata<br/>- Pages & TextBlocks with page coordinates<br/>- Tables & Image descriptions"]

    Assembly --> Prompt["Master Safety Extraction Prompt<br/>- Multi-label: ICSR, PQC, MI, NOT_RELEVANT<br/>- Safety Rule: Never guess ('Not stated')<br/>- Mandatory source references"]

    Prompt --> VLM["Qwen-VL Structured Reasoner"]

    VLM --> Validate{"Quality Gate Validator"}

    Validate -->|Pass: All sources valid & schema compliant| Output(["AIProcessResponse JSON<br/>- Multi-label classifications + reasons<br/>- Extracted fields + source refs<br/>- 10-15 sentence clinical summary<br/>- Processing metrics breakdown"])
    Validate -->|Fail: Bad JSON / missing source / hallucination| RetryCheck{"retryCount < 3?"}
    RetryCheck -->|Yes| Prompt
    RetryCheck -->|No| Fallback(["Escalate: status = REVIEW_REQUIRED"])
```

### 6.1 AI Execution Model & Clinical Safety Architecture

#### Model Selection & Laptop Resource Optimization
- **Selected Model**: `Qwen/Qwen2-VL-2B-Instruct` (or `Qwen3-VL-2B-Instruct`), chosen specifically for its high multimodal reasoning performance combined with a lightweight parameter footprint (2B) suitable for local laptop CPU/GPU execution.
- **Hardware-Aware Loading**: Configured in `QwenClient` using `low_cpu_mem_usage=True`, automatic device mapping (`device_map="cpu"` with `torch.float32` or `"auto"` with `torch.bfloat16` when CUDA is detected) to prevent out-of-memory errors on 8–16 GB RAM developer machines.
- **Persistent Model Cache**: Dedicated Docker named volume `huggingface-cache` mounted at `/root/.cache/huggingface` guarantees model weights persist across container restarts, eliminating repetitive 4.5 GB downloads.
- **External Local Server Support**: Allows seamless connection to local inference servers via `AI_API_BASE` (e.g., Ollama or vLLM at `http://host.docker.internal:11434/v1`).
- **Default Execution**: `USE_MOCK_AI=false` enabled by default in `docker-compose.yml` to ensure real model inference is actively exercised.

#### Clinical Safety & Misclassification Prevention (Fallback Engine)
- **Life-Threatening Adverse Reaction Coverage**: The clinical safety dictionary incorporates critical acute events (`"heart attack"`, `"myocardial infarction"`, `"cardiac arrest"`, `"chest pain"`, `"stroke"`, `"anaphylaxis"`) and automatically escalates their seriousness assessment to `"Serious"`.
- **Typo & Variation Tolerance**: Recognizes common misspellings (e.g. `"alergy"`, `"paracetomol"`) and pharmaceutical forms (e.g. `"tablets"`, `"capsules"`, `"syrup"`), preventing acute consumer reports from being falsely rejected as `NOT_RELEVANT`.
- **Reporter Identity Normalization**: Converts raw email senders (e.g., `VADDEKASYAP@GMAIL.COM`) into human-readable Title Case names (`"Vadde Kasyap"`) with appropriate `"Consumer"` role assignment.

---

## 7. Reviewer Workspace Interaction & Audit Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Reviewer as Human Reviewer
    participant UI as Reviewer UI (:4200)
    participant Backend as Spring Boot API (:8080)
    participant Oracle as Oracle Database (:1521)
    participant PDFStore as Shared Document Storage

    Reviewer->>UI: Selects case in Review Queue
    UI->>Backend: GET /api/review-items/{emailId}
    Backend->>Oracle: Query Email, Jobs, AI Results, Facts, Sources, Audit
    Oracle-->>Backend: Return complete entity graph
    Backend-->>UI: 200 OK (ReviewDetailDto)
    UI->>UI: Render 7-Section Hierarchy (Adaptive Domain Findings)
    UI->>Backend: GET /api/emails/{id}/attachments/{id}/content
    Backend->>PDFStore: Stream PDF or document binary
    PDFStore-->>UI: Render PDF in embedded viewer

    opt Inspect Evidence
        Reviewer->>UI: Clicks "Page X" evidence button on fact
        UI->>UI: Display verbatim snippet in Evidence Inspector
        UI->>UI: Navigate PDF frame to #page=X
    end

    alt Accept Case
        Reviewer->>UI: Clicks "Approve Findings"
        UI->>Backend: POST /api/review-items/{emailId}/accept
        Backend->>Oracle: Update status = REVIEWED, Insert AUDIT_LOG (REVIEW_ACCEPTED)
        Backend-->>UI: 200 OK (Updated detail)
        UI->>UI: Update status badge to "APPROVED BY REVIEWER"
    else Override Case
        Reviewer->>UI: Clicks "Edit Details", changes fields / categories
        UI->>Backend: POST /api/review-items/{emailId}/override
        Backend->>Oracle: Update classifications/fields, Insert AUDIT_LOG (REVIEW_OVERRIDE with diffs)
        Backend-->>UI: 200 OK (Updated detail)
        UI->>UI: Re-render updated findings & append audit timeline
    end
```

---

## 8. Ingestion, Queue & Worker Design

### 8.1 Attachment Fallback Handling
Every incoming email requires automated analysis. When an email arrives without PDF attachments:
- `EmailIngestionService` creates a synthetic attachment named `email_body.txt`.
- Saves the body content to the storage repository.
- Creates an attachment record and enqueues a `ProcessingJob`.
- Guarantees 100% processing across both email bodies and file attachments.

### 8.2 In-Process Queue & Asynchronous Worker
- **Queue Implementation**: `java.util.concurrent.BlockingQueue<Long>` (`JobQueue`) holds pending `jobId`s.
- **Worker Execution**: `JobWorker` runs a continuous background loop:
  1. Retrieves next `jobId` from queue.
  2. Updates `ProcessingJob` state to `PROCESSING`.
  3. Prepares `AIProcessRequestDto` containing document storage path and email text.
  4. Calls `FastAPIClient.process(request)`.
  5. On success: executes `ResultService.saveAIResult()` in an isolated database transaction, moving job to `COMPLETED` and email to `REVIEW_REQUIRED`.
  6. On failure: logs audit entry, triggers retry up to `maxRetries` (default 3), or escalates to `REVIEW_REQUIRED` / `FAILED`.

---

## 9. Reviewer Workspace Design (Frontend Tier)

### 9.1 Real-Time Queue & Progress Polling
- Displays queue status chips (`X in queue`) with pulsing indicators when documents are processing.
- Automatically polls `/api/review-items` every 2.5 seconds while active jobs exist.
- Shows dynamic case progress bar (15% Queued &rarr; 65% Processing &rarr; 100% Complete).

### 9.2 The 7-Section Case Assessment Hierarchy
The case view organizes critical review data into a scannable, standardized clinical workspace:

1. **Section 1: AI Assessment & Review Status**
   - **Card A (AI Assessment)**: Primary category label (e.g., `PATIENT SAFETY`), category code (`ICSR`), confidence pill (`95% confidence`), and lead clinical reason.
   - **Card B (Review Status)**: Prominent status badge (`⚠ HUMAN REVIEW REQUIRED` or `✓ APPROVED BY REVIEWER`) with operational instructions for review sign-off.
2. **Section 2: Case Snapshot**
   - Clean metadata grid: Source file, Sender, Subject, Document type, Language, and Received date.
3. **Section 3: Why This Classification?**
   - Structured list of backend reasoning for all triggered classification categories.
4. **Section 4: Classification Signals Matrix**
   - Multi-label matrix comparing all 4 standard categories (`Patient Safety (ICSR)`, `Product Quality (PQC)`, `Medical Inquiry (MI)`, and `Not Relevant`) with confidence percentages and `● Detected` vs `○ Not detected` status.
5. **Section 5: Domain-Specific Findings (Dynamic Adaptation)**
   - **ICSR**: Displays `Patient` (Age, Sex, Weight, Height, History), `Reporter` (Identity, Role, Country), `Product` (Name, Dose, Route, Dates), and `Reaction` (Description, Onset, Outcome, Seriousness, Narrative).
   - **PQC**: Displays `Product & Batch` (Product, Batch / Lot), `Quality Issue` (Complaint, Severity), and `Supporting Evidence` (Photo mentioned, Image evidence).
   - **MI**: Displays prominent `Inquiry Question(s)` callout box, `Product`, `Topic`, and `Context`.
   - **NOT_RELEVANT**: Cleanly shows `"No domain-specific case information was identified."` with *Not applicable* indicators. **Zero empty ICSR patient forms rendered.**
   - **Source Navigation**: Clicking any finding's source button (`Page 1`, `Email`) triggers `inspectSourceByFieldId`, opening the Evidence Inspector and navigating the embedded PDF viewer to that exact page.
6. **Section 6: Data Quality & Traceability**
   - Verification checklist with live calculated counters from active case fields:
     - `Total Extracted Fields`
     - `Evidence Linked`
     - `Marked "Not stated"`
7. **Section 7: Detailed AI Narrative**
   - Collapsible accordion (`[View full narrative ↓]`) revealing the full 10–15 sentence AI-generated clinical narrative summary.

---

## 10. REST API Specifications

### Review Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/review-items` | Retrieves list of inbox items. Supports query parameters `category` (`ALL`, `ICSR`, `PQC`, `MI`, `NOT_RELEVANT`, `QUEUED`) and `search`. |
| `GET` | `/api/review-items/{emailId}` | Retrieves full case detail (`ReviewDetailDto`), including attachments, AI classifications, extracted facts, source coordinates, audit history, and job status. |
| `POST` | `/api/review-items/{emailId}/accept` | Submits reviewer approval (`ReviewAcceptRequest`), updates email status to `REVIEWED`, and writes an immutable audit record. |
| `POST` | `/api/review-items/{emailId}/override`| Submits reviewer overrides (`ReviewOverrideRequest`), updating classifications and field values while preserving original values in the audit log. |

### Ingestion & Document Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/emails/upload` | Multipart upload for manual test ingestion (`sender`, `subject`, `body`, and optional file `file`). Enqueues processing job immediately. |
| `POST` | `/api/emails/poll` | Triggers manual check of configured IMAP/Mock mailbox. |
| `GET` | `/api/emails/{emailId}/attachments/{attachmentId}/content` | Streams raw attachment binary (PDF, text) for inline browser rendering and download. |

### Job & AI Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/jobs/{jobId}` | Returns processing status and metrics for a specific background job. |
| `POST` | `/api/jobs/{jobId}/retry` | Re-enqueues a failed or review-required job. |
| `POST` | `/ai/process` | Internal FastAPI endpoint processing document content into validated structured JSON. |
| `GET` | `/health` | Healthcheck endpoint for AI service and Frontend proxy. |

---

## 11. Error Handling & Resilience Strategy

| Failure Scenario | Component | Resolution Strategy |
| :--- | :--- | :--- |
| **Mailbox Connection Dropped** | Spring Boot Ingestion | Logged; polling automatically retries on subsequent schedule without dropping queued work. |
| **Transient AI Timeout / Failure** | `JobWorker` | Job is re-enqueued with incremented `retryCount`. If `retryCount >= maxRetries`, status becomes `REVIEW_REQUIRED`. |
| **Malformed / Invalid Model JSON** | AI Service & Pydantic | Pydantic validator rejects malformed responses; pipeline triggers targeted correction prompt. |
| **Corrupted / Empty PDF** | Digital Extraction Node | Catches extraction exceptions, flags document as unreadable, and marks job as `REVIEW_REQUIRED` with clear diagnostic logs. |
| **Reviewer Override Conflict** | Result Service | Transactions are executed with optimistic locking; overrides record both previous and new values in the audit trail. |
