# Smart Inbox Assistant — Implementation Strategy

## 1. Objective

Build the Smart Inbox Assistant as a Dockerized, locally runnable prototype in three implementation modules:

1. **Module 1 — Foundation:** Docker infrastructure, Oracle, Spring Boot, mailbox ingestion, attachment storage, and job queue.
2. **Module 2 — AI Processing:** FastAPI, LangGraph, PyMuPDF, pdfplumber, Qwen3-VL-2B-Instruct, structured extraction, validation, and persistence.
3. **Module 3 — Review Application:** Angular review UI, source traceability, accept/override, audit, metrics, testing, and final demo.

The assignment requires a working frontend + backend + database application, PDF processing, AI classification/extraction, source traceability, audit logging, synthetic test data, and processing of at least 10–15 sample documents. Docker is used here to make the entire prototype reproducible and easy to run locally.

---

# 2. Target Docker Architecture

```text
                         Docker Compose
                              |
       +----------------------+----------------------+
       |                      |                      |
       v                      v                      v
+-------------+        +-------------+        +-------------+
|  Angular    |        | Spring Boot |        |  FastAPI    |
|  Frontend   | -----> | Backend     | -----> | AI Service  |
|  :4200      |        | :8080       |        | :8000       |
+-------------+        +------+------+        +------+------+
                              |                       |
                              |                       v
                              |                +-------------+
                              |                | Qwen3-VL-2B |
                              |                | Inference   |
                              |                +-------------+
                              |
                              v
                       +-------------+
                       |   Oracle    |
                       |   Database  |
                       +-------------+

                       +-------------+
                       | PDF Storage |
                       | Docker Vol. |
                       +-------------+
```

## Docker services

Prototype services:

```text
frontend
backend
ai-service
oracle
```

Recommended optional profile:

```text
model
```

The model can either run inside the AI service container for a simple prototype or be separated later if GPU/model serving needs require it.

---

# 3. Repository Structure

```text
clinevo-smart-inbox/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/
│
├── ai-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── storage/
│   └── .gitkeep
│
├── test-data/
│   ├── emails/
│   └── pdfs/
│
└── docs/
    ├── hld.md
    ├── lld.md
    └── implementation-strategy.md
```

---

# 4. Environment Configuration

Create:

```text
.env.example
```

Example:

```env
ORACLE_HOST=oracle
ORACLE_PORT=1521
ORACLE_SERVICE=FREEPDB1
ORACLE_USER=smart_inbox
ORACLE_PASSWORD=change_me

BACKEND_PORT=8080
AI_SERVICE_URL=http://ai-service:8000

AI_MODEL_NAME=Qwen3-VL-2B-Instruct
AI_MODEL_URL=http://model:8001
PROMPT_VERSION=v1

MAIL_HOST=imap.example.com
MAIL_PORT=993
MAIL_USERNAME=test@example.com
MAIL_PASSWORD=change_me

STORAGE_PATH=/app/storage
```

Never commit the real `.env`.

---

# 5. Docker Compose Strategy

Start with:

```text
oracle
backend
ai-service
frontend
```

A simple Compose dependency flow is:

```text
oracle
   ↓
backend
   ↓
ai-service

backend
   ↓
frontend
```

Important:

`depends_on` controls startup order but does not guarantee that a service is ready. Add health checks for Oracle and the application services.

---

# 6. Docker Network

Create one internal network:

```text
smart-inbox-network
```

Services communicate using service names rather than `localhost`.

Example:

```text
backend → http://ai-service:8000
backend → oracle:1521
frontend → backend:8080
```

Inside Docker:

```text
localhost
```

means the current container, not another service.

---

# 7. Persistent Volumes

Use Docker volumes for:

```text
Oracle data
PDF storage
```

Example:

```text
oracle-data
document-storage
```

This means:

```text
docker compose down
docker compose up
```

does not lose the prototype database/document state unless volumes are explicitly removed.

---

# MODULE 1 — FOUNDATION

# 8. Module 1 Goal

At the end of Module 1:

```text
Synthetic/Test Mailbox
        ↓
Spring Boot
        ↓
Oracle
        ↓
PDF Storage
        ↓
Processing Job
        ↓
In-Process Queue
```

No real AI is required yet.

The objective is to prove that ingestion and persistence work independently of the AI pipeline.

---

# 9. Module 1 Step 1 — Docker Foundation

Create:

```text
docker-compose.yml
.env.example
```

Start Oracle first.

Verify:

```text
Oracle is reachable
Database user exists
Schema can be created
```

---

# 10. Module 1 Step 2 — Oracle Schema

Create:

```text
EMAIL
ATTACHMENT
PROCESSING_JOB
AI_RESULT
CLASSIFICATION
EXTRACTED_FIELD
SOURCE_REFERENCE
IMAGE_RESULT
PROCESSING_METRICS
AUDIT_LOG
```

For Module 1 initially create only:

```text
EMAIL
ATTACHMENT
PROCESSING_JOB
AUDIT_LOG
```

Add the remaining tables in Module 2.

This reduces debugging complexity.

---

# 11. Module 1 Step 3 — Spring Boot Docker Image

Use a multi-stage Dockerfile:

```text
Maven build image
        ↓
JRE runtime image
```

Conceptually:

```text
pom.xml
   ↓
mvn package
   ↓
backend.jar
   ↓
small runtime container
```

Do not install Maven into the final runtime image.

---

# 12. Module 1 Step 4 — Spring Boot Configuration

Configure:

```text
spring.datasource.url
spring.datasource.username
spring.datasource.password
```

using environment variables.

Example Docker database hostname:

```text
oracle
```

not:

```text
localhost
```

---

# 13. Module 1 Step 5 — Entities

Implement:

```text
Email
Attachment
ProcessingJob
AuditLog
```

Use JPA.

---

# 14. Module 1 Step 6 — Mailbox Abstraction

Create:

```java
public interface MailboxClient {
    List<RawEmail> fetchNewMessages();
    void markProcessed(String messageId);
}
```

Implement:

```text
MockMailboxClient
ImapMailboxClient
```

Start with:

```text
MockMailboxClient
```

for development.

It can read synthetic `.eml` files from:

```text
/test-data/emails
```

Then switch to IMAP for the actual mailbox integration.

---

# 15. Module 1 Step 7 — Email Parser

Extract:

```text
messageId
sender
subject
received date
body
attachments
```

For each attachment determine:

```text
filename
content type
size
```

---

# 16. Module 1 Step 8 — Attachment Storage

Store PDF files in:

```text
/app/storage
```

Mount this to:

```text
document-storage
```

Example:

```text
storage/
   101/
      case-report.pdf
```

Store only the storage reference in Oracle.

---

# 17. Module 1 Step 9 — Idempotency

Before saving an email:

```text
messageId exists?
     |
    YES → skip
     |
     NO → save
```

For attachments calculate:

```text
SHA-256
```

This protects against duplicate content.

---

# 18. Module 1 Step 10 — Processing Job

For every PDF:

```text
Attachment
   ↓
ProcessingJob
   ↓
QUEUED
```

Non-PDF:

```text
Attachment
   ↓
NOT_SUPPORTED
```

No AI processing yet.

---

# 19. Module 1 Step 11 — Queue

Implement:

```java
BlockingQueue<Long>
```

The queue contains:

```text
jobId
```

Flow:

```text
EmailIngestionService
        ↓
JobService
        ↓
BlockingQueue
```

---

# 20. Module 1 Step 12 — Worker

Create:

```text
JobWorker
```

Initially it only:

```text
dequeue
 ↓
mark PROCESSING
 ↓
log
 ↓
mark temporary completion
```

The actual AI call is added in Module 2.

---

# 21. Module 1 Verification

Run:

```bash
docker compose up --build
```

Verify:

```text
Oracle       ✓
Spring Boot  ✓
Frontend     ✓
AI service   ✓
```

Then ingest a synthetic email.

Expected:

```text
EMAIL row
ATTACHMENT row
PROCESSING_JOB row
PDF in volume
```

---

# 22. Module 1 Definition of Done

- [ ] Docker Compose starts the stack.
- [ ] Oracle persists data.
- [ ] Spring Boot connects to Oracle.
- [ ] Synthetic mailbox works.
- [ ] IMAP client exists.
- [ ] Email parsing works.
- [ ] PDF attachments are stored.
- [ ] Non-PDF attachments are logged.
- [ ] Duplicate emails are ignored.
- [ ] PDF jobs are created.
- [ ] Queue works.
- [ ] Worker can consume jobs.

Do not proceed to UI polish before this works.

---

# MODULE 2 — AI PROCESSING

# 23. Module 2 Goal

At the end of Module 2:

```text
Processing Job
      ↓
FastAPI
      ↓
PDF Detection
      ↓
Extraction
      ↓
Qwen3-VL-2B
      ↓
Structured Result
      ↓
Validation
      ↓
Source Validation
      ↓
Spring Boot
      ↓
Oracle
```

---

# 24. Module 2 Step 1 — FastAPI Container

Create:

```text
ai-service/Dockerfile
requirements.txt
```

Install:

```text
fastapi
uvicorn
pydantic
langgraph
pymupdf
pdfplumber
transformers
torch
Pillow
```

Add other model/runtime dependencies only when required.

---

# 25. Module 2 Step 2 — AI Service Health

Implement:

```text
GET /health
```

Response:

```json
{
  "status": "UP"
}
```

The backend should be able to check this endpoint.

---

# 26. Module 2 Step 3 — Model Strategy

Use:

```text
Qwen3-VL-2B-Instruct
```

The model is configured through environment variables.

Do not hardcode the model throughout the application.

Example:

```text
AI_MODEL_NAME=Qwen3-VL-2B-Instruct
```

---

# 27. Module 2 Step 4 — Local Model Runtime

For the first working prototype:

```text
FastAPI container
     ↓
Load Qwen3-VL-2B
     ↓
Inference
```

If local GPU support is available, configure the AI container for GPU access.

If GPU inference is impractical, keep the AI service interface unchanged and use a smaller/CPU-compatible inference configuration for development.

The architecture must not depend on the model being embedded into the Spring application.

---

# 28. Module 2 Step 5 — PDF Processing

Implement:

```text
FormatDetectionNode
DigitalExtractionNode
OCRVisionNode
```

---

# 29. Module 2 Step 6 — Digital PDF

Use:

```text
PyMuPDF
```

for:

```text
text
pages
layout/location
```

Use:

```text
pdfplumber
```

for:

```text
tables
```

Every output keeps:

```text
pageNumber
location
source
```

---

# 30. Module 2 Step 7 — Scanned/Handwritten

Flow:

```text
PDF
 ↓
Render page
 ↓
Qwen3-VL-2B
 ↓
Text / handwriting
 ↓
Confidence
```

If confidence is low:

```text
reviewRequired = true
```

---

# 31. Module 2 Step 8 — Images

For meaningful images:

```text
Image
 ↓
Qwen3-VL-2B
 ↓
Description
 ↓
Confidence
 ↓
Review Required
```

Do not attempt deep medical diagnosis.

---

# 32. Module 2 Step 9 — Language

Detect language.

For non-English:

```text
Original
+
English translation
+
original page reference
```

Never discard the original source.

---

# 33. Module 2 Step 10 — Article PDFs

Implement:

```text
article parser
multi-column handling
reference removal
patient-case extraction
```

Then use Qwen3-VL-2B for semantic patient-case identification.

---

# 34. Module 2 Step 11 — Canonical Context

Create:

```python
CanonicalCaseContext
```

Containing:

```text
email
documents
pages
textBlocks
tables
images
sourceLocations
language
```

Every evidence item must preserve its origin.

---

# 35. Module 2 Step 12 — Pydantic Schema

Define:

```text
Classification
ExtractedField
SourceReference
ImageResult
AIProcessResponse
```

Example:

```python
class ExtractedField(BaseModel):
    field_group: str
    field_name: str
    value: str
    confidence: float
    source_references: list[SourceReference]
```

---

# 36. Module 2 Step 13 — Master Prompt

Prompt rules:

```text
You are a healthcare document extraction assistant.

Rules:
1. Never guess.
2. If information is absent, return "Not stated".
3. Every extracted field requires confidence.
4. Every extracted field requires a source.
5. Source must identify email or PDF page.
6. Multiple categories may be returned.
7. Give a one-line reason for each classification.
8. Produce a 10–15 sentence summary.
9. Extract only information supported by the provided evidence.
```

---

# 37. Module 2 Step 14 — Classification

Categories:

```text
ICSR
PQC
MI
NOT_RELEVANT
```

Multiple categories are allowed.

Example:

```json
{
  "classifications": [
    {
      "category": "ICSR",
      "confidence": 0.96,
      "reason": "..."
    },
    {
      "category": "PQC",
      "confidence": 0.84,
      "reason": "..."
    }
  ]
}
```

---

# 38. Module 2 Step 15 — ICSR

Extract:

```text
Patient:
age
sex
weight
height
history

Reporter:
identity
role
country

Product:
name
dose
route
start
stop

Reaction:
what happened
onset
outcome

Seriousness
Narrative
```

Missing:

```text
Not stated
```

---

# 39. Module 2 Step 16 — PQC

Extract:

```text
product
batch/lot
issue
photoMentioned
```

---

# 40. Module 2 Step 17 — MI

Extract:

```text
questions[]
product
topic
```

---

# 41. Module 2 Step 18 — Summary

Generate:

```text
10–15 sentences
```

Include:

```text
what the document says
why it is relevant/not relevant
important facts
uncertainties
```

---

# 42. Module 2 Step 19 — Source Validation

For every extracted field verify:

```text
source exists
source type is valid
page exists
snippet exists where applicable
```

Invalid:

```text
field without source
```

must not be persisted as a valid final result.

---

# 43. Module 2 Step 20 — Spring AI Client

Create:

```java
public interface AIClient {
    AIProcessResponse process(AIProcessRequest request);
    boolean healthCheck();
}
```

Implementation:

```text
FastAPIClient
```

---

# 44. Module 2 Step 21 — Result Persistence

One successful AI job creates:

```text
AI_RESULT
CLASSIFICATION
EXTRACTED_FIELD
SOURCE_REFERENCE
IMAGE_RESULT
PROCESSING_METRICS
```

Use one transaction for the result persistence operation.

---

# 45. Module 2 Step 22 — Metrics

Record:

```text
totalDurationMs
extractionDurationMs
ocrDurationMs
translationDurationMs
llmDurationMs
validationDurationMs
```

---

# 46. Module 2 Step 23 — Retry

```text
AI failure
 ↓
retryCount < maxRetries?
 ├── YES → RETRYING → Queue
 └── NO  → REVIEW_REQUIRED
```

Keep retry count in `PROCESSING_JOB`.

---

# 47. Module 2 Step 24 — Audit

Record:

```text
AI_STARTED
AI_COMPLETED
AI_FAILED
CLASSIFICATION_CREATED
FACT_EXTRACTED
VALIDATION_FAILED
```

Store:

```text
timestamp
jobId
emailId
actorType
metadata
```

---

# 48. Module 2 Definition of Done

- [ ] FastAPI runs in Docker.
- [ ] AI health endpoint works.
- [ ] Qwen3-VL-2B is configurable.
- [ ] Digital PDFs work.
- [ ] Scanned PDFs work.
- [ ] Handwritten PDFs work.
- [ ] Article PDFs work.
- [ ] Non-English PDFs work.
- [ ] Tables are structured.
- [ ] Images are described.
- [ ] Multi-label classification works.
- [ ] ICSR extraction works.
- [ ] PQC extraction works.
- [ ] MI extraction works.
- [ ] Not Relevant works.
- [ ] Missing fields return `Not stated`.
- [ ] Every field has confidence.
- [ ] Every field has a source.
- [ ] Pydantic validation works.
- [ ] Results persist in Oracle.
- [ ] Retry works.
- [ ] Metrics are recorded.
- [ ] Audit entries are created.

---

# MODULE 3 — REVIEW APPLICATION

# 49. Module 3 Goal

Turn the backend/AI pipeline into a usable reviewer workflow.

```text
Angular
 ↓
Review Queue
 ↓
Review Detail
 ↓
Evidence
 ↓
Accept / Override
 ↓
Audit
```

---

# 50. Module 3 Step 1 — Angular Container

Create:

```text
frontend/Dockerfile
nginx.conf
```

Recommended production-style prototype:

```text
Angular build
 ↓
static files
 ↓
Nginx container
```

Development can use:

```bash
ng serve
```

but the final demo should also work through Docker.

---

# 51. Module 3 Step 2 — Review Queue API

Implement:

```text
GET /api/review-items
```

Return:

```text
emailId
sender
subject
receivedAt
classification
confidence
summary
status
```

---

# 52. Module 3 Step 3 — Queue UI

Display:

```text
Sender
Subject
Date
Classification
Confidence
Status
Summary
```

Add:

```text
search
filter
sort
```

---

# 53. Module 3 Step 4 — Review Detail

Display:

```text
Email
Classification
Summary
Extracted Facts
PDF
Images
Sources
Audit
```

---

# 54. Module 3 Step 5 — Facts Table

Example:

```text
Field       Value        Confidence       Source
--------------------------------------------------
Age         54           91%              PDF p2
Product     Drug X       98%              PDF p1
Reaction    Rash         95%              Email
```

---

# 55. Module 3 Step 6 — Source Viewer

Click:

```text
Age = 54
```

Then:

```text
PDF page 2
```

For an email source:

```text
Show relevant email text
```

This is a high-value demo feature because it visibly proves traceability.

---

# 56. Module 3 Step 7 — PDF Viewer

The backend exposes the stored PDF.

The frontend opens:

```text
attachment
+
page number
```

When a source is clicked:

```text
PdfViewer.goToPage(pageNumber)
```

---

# 57. Module 3 Step 8 — Accept

Endpoint:

```text
POST /api/review-items/{emailId}/accept
```

Transaction:

```text
update review state
+
write audit
```

---

# 58. Module 3 Step 9 — Override

Endpoint:

```text
POST /api/review-items/{emailId}/override
```

Payload contains:

```text
changed classification
changed fields
reviewer
```

Persist:

```text
old value
new value
timestamp
```

---

# 59. Module 3 Step 10 — Audit Timeline

Display:

```text
Email received
Processing started
AI classification
Facts extracted
Validation
Reviewer override
Review accepted
```

---

# 60. Module 3 Step 11 — Error UI

Show:

```text
REVIEW_REQUIRED
FAILED
LOW_CONFIDENCE
```

The reviewer should be able to understand why an item needs attention.

---

# 61. Module 3 Step 12 — End-to-End Dataset

Create the required synthetic dataset:

```text
10+ emails
5+ digital PDFs
2+ scanned/handwritten PDFs
5+ article PDFs
2+ non-English PDFs
2+ PQC-only
2+ MI-only
1+ irrelevant
```

---

# 62. Module 3 Step 13 — Batch Test

Process 10–15 documents.

Record:

```text
filename
document type
classification
processing time
success/failure
```

Example:

```text
document       type        time       result
------------------------------------------------
case01.pdf     digital     7.2s       ICSR
case02.pdf     scanned     13.4s      ICSR
case03.pdf     article     10.8s      ICSR
pqc01.pdf      digital     6.3s       PQC
mi01.pdf       digital     5.9s       MI
```

---

# 63. Module 3 Step 14 — Failure Testing

Test:

```text
duplicate email
broken PDF
empty PDF
unreadable handwriting
missing patient age
missing reporter
PQC + ICSR
non-English
invalid AI JSON
AI timeout
```

Expected:

```text
No guessing
No silent failures
Retry where appropriate
Review Required when necessary
```

---

# 64. Module 3 Step 15 — Docker End-to-End Test

From a clean environment:

```bash
docker compose down -v
docker compose up --build
```

Then verify:

```text
Frontend → Backend → Oracle
                 ↓
              FastAPI
                 ↓
            Qwen3-VL-2B
```

A reviewer should be able to clone the repo and run the application with documented setup steps.

---

# 65. Docker Compose Development Strategy

During development:

```text
Phase 1
docker compose up oracle backend

Phase 2
docker compose up oracle backend ai-service

Phase 3
docker compose up
```

This allows each module to be debugged independently.

For final submission:

```bash
docker compose up --build
```

should start the complete stack.

---

# 66. Docker GPU Strategy

If Qwen3-VL-2B is run locally with GPU acceleration:

```text
AI container
    ↓
NVIDIA Container Toolkit
    ↓
GPU
    ↓
Qwen3-VL-2B
```

Keep GPU-specific configuration isolated to the AI service.

The Spring Boot and Angular containers remain hardware-independent.

If GPU is unavailable, the architecture should still run with a CPU-compatible development configuration or a configured model endpoint.

---

# 67. Recommended Implementation Order

Do not build all three modules simultaneously.

Use this exact sequence:

```text
MODULE 1
│
├── Docker
├── Oracle
├── Spring Boot
├── Entities
├── Mailbox
├── Parser
├── Storage
├── Jobs
└── Queue
        ↓
   PROVE INGESTION
        ↓
MODULE 2
│
├── FastAPI
├── PyMuPDF
├── pdfplumber
├── Qwen3-VL-2B
├── LangGraph
├── Canonical Context
├── Prompt
├── Classification
├── Extraction
├── Validation
├── Sources
├── Persistence
├── Retry
└── Metrics
        ↓
   PROVE AI PIPELINE
        ↓
MODULE 3
│
├── Angular
├── Review Queue
├── Detail
├── PDF Viewer
├── Source Viewer
├── Accept
├── Override
├── Audit
└── Benchmark
        ↓
   PROVE COMPLETE DEMO
```

---

# 68. Suggested Git Commit Strategy

Keep commits small and demonstrable.

```text
01-init-project
02-add-docker-compose
03-add-oracle-schema
04-add-spring-entities
05-add-mailbox-client
06-add-email-parser
07-add-attachment-storage
08-add-processing-queue
09-add-fastapi-service
10-add-pdf-extraction
11-add-qwen-vl
12-add-canonical-context
13-add-ai-schema
14-add-classification
15-add-domain-extraction
16-add-source-validation
17-add-ai-persistence
18-add-angular-review-queue
19-add-review-detail
20-add-source-viewer
21-add-review-actions
22-add-audit-timeline
23-add-benchmark
24-add-documentation
```

---

# 69. Development Rule

At every stage maintain a runnable system.

After Module 1:

```text
docker compose up
→ email appears in Oracle
```

After Module 2:

```text
docker compose up
→ email gets AI result
```

After Module 3:

```text
docker compose up
→ reviewer can review and approve result
```

Never allow the project to reach the final day with all components only partially implemented.

---

# 70. Final Demo Flow

Use one representative synthetic ICSR + PQC document.

```text
1. Start Docker Compose
       ↓
2. Show mailbox/email
       ↓
3. Show processing job
       ↓
4. Show AI classification
       ↓
5. Show confidence
       ↓
6. Show extracted facts
       ↓
7. Click source
       ↓
8. PDF opens at exact page
       ↓
9. Show summary
       ↓
10. Show image/table if applicable
       ↓
11. Override one field
       ↓
12. Show audit timeline
       ↓
13. Show Oracle persistence
       ↓
14. Show batch processing metrics
       ↓
15. Explain model/architecture trade-offs
```

---

# 71. Priority if Time Is Limited

Priority order:

```text
P0 — Must work
    Email ingestion
    PDF processing
    Classification
    ICSR/PQC/MI extraction
    Oracle persistence
    Source references
    Review UI

P1 — Strong scoring
    Scanned/handwritten
    Tables
    Non-English
    Images
    Audit
    Metrics
    Retry

P2 — Polish
    Better UI
    Advanced filtering
    Better error messages

P3 — Bonus
    Literature screening
```

Do not implement the optional literature-screening extension until the core workflow is working.

---

# 72. Definition of Complete

The project is complete when this single flow works end-to-end:

```text
Synthetic Email
      ↓
Dockerized Mailbox/Mock
      ↓
Spring Boot
      ↓
Oracle
      ↓
PDF Storage
      ↓
Processing Queue
      ↓
FastAPI
      ↓
PyMuPDF / pdfplumber
      ↓
Qwen3-VL-2B
      ↓
Canonical Context
      ↓
Structured JSON
      ↓
Pydantic Validation
      ↓
Source Validation
      ↓
Spring Boot
      ↓
Oracle
      ↓
Angular
      ↓
Human Reviewer
      ↓
Accept / Override
      ↓
Audit Log
```

The final repository should be reproducible from a clean machine using Docker and should include:

- source code
- Docker configuration
- `.env.example`
- database schema
- synthetic test data
- README
- HLD
- LLD
- sample JSON output
- screenshots/recording
- per-document processing metrics