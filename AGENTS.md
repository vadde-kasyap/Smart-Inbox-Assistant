# AGENTS.md — Smart Inbox Assistant

## 0. Purpose

You are the coding agent for the Clinevo Technologies Smart Inbox Assistant assignment.

Before writing code, read these documents in this repository:

1. `AGENTS.md` — this file; treat it as the implementation contract.
2. `problem-statement.pdf` (or the supplied original assignment document) — source of truth for assignment requirements.
3. `HLD.md` — system architecture and design principles.
4. `LLD.md` — detailed data model, APIs, packages, states, and flows.
5. `IMPLEMENTATION_STRATEGY.md` — implementation order, module steps, Docker strategy, and definitions of done.

Do not silently replace requirements from the assignment with your own interpretation. If documents conflict, prefer:
1. Original assignment requirements
2. This AGENTS.md
3. LLD
4. HLD
5. Implementation strategy

If a requirement is ambiguous, make the smallest reasonable decision, document it, and keep the architecture easy to change.

---

# 1. Product Goal

Build a working Smart Inbox Assistant for a healthcare/pharma shared test mailbox.

The application must:

- ingest incoming emails;
- capture sender, subject, date, body, and attachments;
- process every PDF attachment;
- classify content into one or more supported categories;
- extract domain-specific facts;
- provide confidence for extracted facts and classifications;
- provide exact source traceability to the email or PDF page;
- generate a 10–15 sentence summary and relevance explanation;
- persist results in Oracle;
- expose results through an Angular reviewer UI;
- allow human reviewers to accept or override AI output;
- record AI and reviewer actions in an audit trail;
- record processing-time metrics;
- use synthetic test data only.

This is a human-review assistant, not an automated final pharmacovigilance decision system.

---

# 2. Non-Negotiable Safety / Data Rules

## 2.1 Synthetic data only

Never introduce real patient/client data.

Use synthetic names, products, reporters, cases, emails, and PDFs for testing.

## 2.2 Never guess

If information is absent or unsupported by source material:

`Not stated`

Do not infer:

- patient age;
- sex;
- weight;
- height;
- medical history;
- reporter identity;
- product;
- dose;
- route;
- dates;
- reaction;
- outcome;
- seriousness;
- batch/lot;
- MI question;
- or any other domain fact.

## 2.3 Traceability is mandatory

Every extracted field must contain:

- field name;
- value;
- confidence;
- one or more source references.

A final extracted field without a valid source must not be persisted as a valid final result.

For PDF sources preserve:

- attachment ID;
- page number;
- text snippet when applicable;
- location/bounding-box information when available.

For email sources preserve:

- email ID;
- relevant email text/snippet.

## 2.4 AI is advisory

AI output must always be reviewable.

Do not implement automatic final safety decisions.

---

# 3. Supported Classification

Classification is multi-label.

Supported categories are exactly:

- `ICSR`
- `PQC`
- `MI`
- `NOT_RELEVANT`

Each classification must contain:

```json
{
  "category": "ICSR",
  "confidence": 0.94,
  "reason": "Reason supported by the source material."
}
```

Confidence must be numeric and bounded between 0 and 1.

Do not collapse multi-label results into a single category.

---

# 4. Domain Extraction

## 4.1 ICSR / Safety Report

Extract:

### Patient

- age
- sex
- weight
- height
- relevant history

### Reporter

- identity
- role
- country

### Product

- name
- dose
- route
- start
- stop

### Reaction

- what happened
- onset
- outcome

### Other

- seriousness
- narrative

## 4.2 PQC / Quality Complaint

Extract:

- product
- batch / lot
- issue
- whether a photo is mentioned

## 4.3 MI / Info Request

Extract:

- actual questions as an array;
- product;
- topic.

Do not manufacture questions that were not asked.

---

# 5. PDF Processing Rules

The AI service must not use the VLM for every operation.

Use deterministic extraction first wherever reliable.

## Digital PDFs

Use:

- PyMuPDF for text, pages, layout, and source locations;
- pdfplumber for tables.

Preserve page numbers and locations.

## Scanned / Handwritten PDFs

Flow:

```text
PDF
 -> render page
 -> Qwen3-VL-2B-Instruct
 -> text / handwriting understanding
 -> confidence
```

Low-confidence visual extraction must set:

`reviewRequired = true`

## Tables

Represent tables structurally:

```text
columns[]
rows[][]
pageNumber
```

Do not flatten important tables into an untraceable text blob.

## Images

For meaningful images:

```text
image
 -> Qwen3-VL-2B-Instruct
 -> description
 -> confidence
 -> reviewRequired
```

Do not perform deep medical image diagnosis.

## Article PDFs

Handle:

- multi-column layout;
- reference section removal;
- general discussion/reference filtering;
- patient-case extraction.

Use deterministic layout processing where possible and Qwen3-VL-2B-Instruct for semantic patient-case identification.

## Non-English PDFs

Preserve:

```text
original content
+
English translation when needed
+
original page/source reference
```

Never discard the original source.

---

# 6. AI Model Strategy

Primary prototype model:

`Qwen3-VL-2B-Instruct`

The model must be configurable.

Example:

```env
AI_MODEL_NAME=Qwen3-VL-2B-Instruct
```

Do not hardcode model names throughout the application.

The architecture must remain model-agnostic so the model can later be replaced.

The Spring Boot backend must communicate with an AI abstraction such as:

```java
public interface AIClient {
    AIProcessResponse process(AIProcessRequest request);
    boolean healthCheck();
}
```

The concrete implementation should communicate with the FastAPI AI service.

The Spring application must not embed the model.

---

# 7. Architecture

Use the following logical architecture:

```text
Shared Test Mailbox / IMAP
          |
          v
Spring Boot Backend
          |
          +--> Oracle
          |
          +--> PDF/File Storage
          |
          +--> In-process Job Queue
                    |
                    v
              FastAPI AI Service
                    |
                    +--> Format Detection
                    +--> PyMuPDF
                    +--> pdfplumber
                    +--> OCR/Vision
                    +--> Language Detection
                    +--> Translation
                    +--> Article Processing
                    +--> Canonical Context
                    +--> Qwen3-VL-2B
                    +--> Pydantic Validation
                    +--> Source Validation
                    |
                    v
                 Spring Boot
                    |
                    v
                  Oracle
                    |
                    v
                 Angular UI
```

Keep these responsibilities separate:

- Angular = presentation/reviewer workflow.
- Spring Boot = API, ingestion, orchestration, state, persistence, queue, audit.
- Python/FastAPI = document processing and AI.
- Oracle = durable application state/results/audit/metrics.
- File storage = original PDF attachments.

---

# 8. Docker-First Requirement

The application must be runnable through Docker Compose.

Expected services:

```text
oracle
backend
ai-service
frontend
```

Optional:

```text
model
```

only if separating model runtime materially improves implementation.

Use a shared Docker network, for example:

`smart-inbox-network`

Use persistent volumes for:

- Oracle data;
- document/PDF storage.

Inside Docker, use service names rather than `localhost`.

Examples:

```text
backend -> http://ai-service:8000
backend -> oracle:1521
```

The final clean-run target is:

```bash
docker compose up --build
```

The system must remain usable without requiring Docker-specific logic inside business code.

If GPU support is available, keep NVIDIA/GPU configuration isolated to the AI service. Do not make Angular or Spring depend on GPU availability.

---

# 9. Repository Structure

Use this structure unless there is a strong implementation reason to change it:

```text
smart-inbox/
├── frontend/
├── backend/
├── ai-service/
├── database/
├── documents/
├── tests/
├── docker-compose.yml
├── .env.example
├── README.md
├── HLD.md
├── LLD.md
├── IMPLEMENTATION_STRATEGY.md
├── AGENTS.md
└── problem-statement.pdf
```

Spring packages:

```text
backend/src/main/java/com/clinevo/inbox/
├── controller/
├── service/
├── ingestion/
├── queue/
├── client/
├── validation/
├── entity/
├── repository/
├── dto/
├── mapper/
└── exception/
```

Python structure:

```text
ai-service/
├── app/
│   ├── main.py
│   ├── api/
│   ├── graph/
│   │   ├── pipeline.py
│   │   ├── state.py
│   │   └── nodes/
│   ├── schemas/
│   ├── extraction/
│   ├── prompts/
│   └── models/
└── tests/
```

Angular should be organized by feature rather than one giant component.

---

# 10. Oracle Data Model

Implement the logical model defined by the LLD:

```text
EMAIL
 |
 +-- ATTACHMENT
       |
       +-- PROCESSING_JOB
              |
              +-- PROCESSING_METRICS
              |
              +-- AI_RESULT
                     |
                     +-- CLASSIFICATION
                     |
                     +-- EXTRACTED_FIELD
                     |      |
                     |      +-- SOURCE_REFERENCE
                     |
                     +-- IMAGE_RESULT
 |
 +-- AUDIT_LOG
```

Core entities:

- `EMAIL`
- `ATTACHMENT`
- `PROCESSING_JOB`
- `AI_RESULT`
- `CLASSIFICATION`
- `EXTRACTED_FIELD`
- `SOURCE_REFERENCE`
- `IMAGE_RESULT`
- `PROCESSING_METRICS`
- `AUDIT_LOG`

Use foreign keys and appropriate indexes.

Important idempotency rules:

- `EMAIL.message_id` must be unique.
- Attachment SHA-256 should be stored.
- Do not create duplicate active processing for the same attachment.

One PDF attachment = one processing job.

A successful job produces one final AI result containing:

- classifications;
- extracted fields;
- source references;
- image results;
- metrics.

---

# 11. Processing State

Use explicit states.

Recommended job lifecycle:

```text
QUEUED
   |
   v
PROCESSING
   |
   +--> COMPLETED
   |
   +--> RETRYING -> PROCESSING
   |
   +--> REVIEW_REQUIRED
   |
   +--> FAILED
```

Do not silently discard failed jobs.

Persist failure information.

Retry count belongs to `PROCESSING_JOB`.

After maximum retries:

`REVIEW_REQUIRED`

or `FAILED` when the failure is not recoverable.

---

# 12. Transaction Rules

## Ingestion transaction

Persist:

- email;
- attachments;
- processing jobs.

Only enqueue work after the database transaction successfully commits.

## AI result transaction

Persist together:

- AI result;
- classifications;
- extracted fields;
- source references;
- image results;
- processing metrics;
- job status;
- relevant email/review status.

## Reviewer transaction

Accept/override must persist:

- review state;
- changed values;
- audit record;

in one transaction.

---

# 13. Backend APIs

Implement these APIs:

```text
GET  /api/review-items
GET  /api/review-items/{emailId}

POST /api/review-items/{emailId}/accept
POST /api/review-items/{emailId}/override

GET  /api/emails/{emailId}
GET  /api/emails/{emailId}/attachments

GET  /api/jobs/{jobId}
POST /api/jobs/{jobId}/retry
```

AI service:

```text
POST /ai/process
GET  /health
```

Do not invent alternate API names unless required by an implementation constraint. If an API contract is expanded, update the LLD and frontend/backend clients consistently.

---

# 14. Canonical AI Context

Normalize all document types into a canonical representation before final LLM analysis.

Conceptually:

```text
CanonicalCaseContext
├── email
├── documents[]
│   ├── attachmentId
│   ├── filename
│   ├── documentType
│   ├── originalLanguage
│   └── pages[]
│       ├── pageNumber
│       └── textBlocks[]
├── tables[]
├── images[]
└── sourceLocations[]
```

Every evidence item must preserve its origin.

This prevents the model from needing to understand every PDF flavor independently.

---

# 15. Pydantic AI Response Contract

At minimum support:

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

Validate:

- response structure;
- enums;
- confidence range;
- nested objects;
- required fields;
- source references.

Then run business validation.

Business validation must verify:

- missing values use `Not stated`;
- every field has confidence;
- every field has a source;
- source page exists;
- classification has a reason;
- summary exists;
- multi-label results are preserved;
- unsupported fields are rejected.

Invalid output must not be treated as a successful final result.

---

# 16. Summary Requirements

Generate a meaningful:

- 10–15 sentence summary;
- relevance explanation.

Do not pad the summary with repetitive sentences just to reach the count.

The summary must be grounded in the source material.

---

# 17. Audit Requirements

Audit every important AI and reviewer action.

At minimum support actions such as:

```text
AI_STARTED
AI_COMPLETED
AI_FAILED
CLASSIFICATION_CREATED
FACT_EXTRACTED
VALIDATION_FAILED
REVIEW_ACCEPTED
REVIEW_OVERRIDE
```

Store:

- timestamp;
- email ID;
- job ID when applicable;
- actor type;
- actor ID when applicable;
- metadata;
- old value/new value for reviewer changes.

Reviewer overrides must preserve the previous AI value.

---

# 18. Metrics

Record at minimum:

```text
totalDurationMs
extractionDurationMs
ocrDurationMs
translationDurationMs
llmDurationMs
validationDurationMs
```

For the assignment benchmark, process 10–15 documents and report:

- filename;
- document type;
- classification;
- processing time;
- success/failure.

---

# 19. Reviewer UI

The Angular application must provide:

## Review Queue

Display:

- sender;
- subject;
- date;
- classification;
- confidence;
- status;
- summary.

Support:

- search;
- filter;
- sort.

## Review Detail

Display:

- email;
- classification;
- summary;
- extracted facts;
- PDF;
- images;
- source evidence;
- audit timeline.

## Facts table

Example:

```text
Field       Value        Confidence       Source
--------------------------------------------------
Age         54           91%              PDF p2
Product     Drug X       98%              PDF p1
Reaction    Rash         95%              Email
```

## Source navigation

Clicking a source must navigate to:

- the correct PDF page; or
- the relevant email text.

For PDF sources:

```text
PdfViewer.goToPage(pageNumber)
```

## Review actions

Provide:

- Accept;
- Override.

Override must allow changed classification and/or fields and must record the reviewer and audit details.

## Error states

Clearly show:

- `REVIEW_REQUIRED`
- `FAILED`
- `LOW_CONFIDENCE`

---

# 20. Mailbox Strategy

Create a mailbox abstraction:

```text
MailboxClient
├── MockMailboxClient
└── ImapMailboxClient
```

The mock implementation is important for deterministic development and tests.

The IMAP implementation should be configurable through environment variables.

Do not hardcode credentials.

The ingestion process must be idempotent.

Other non-PDF attachments must be logged according to the assignment but do not need to enter the PDF processing pipeline.

---

# 21. Test Dataset

Create synthetic test data covering at least:

- 10 emails;
- 5 digital PDFs;
- 2 scanned/handwritten PDFs;
- 5 article PDFs;
- 2 non-English PDFs;
- 2 PQC-only examples;
- 2 MI-only examples;
- 1 irrelevant example.

Also create failure/edge cases for:

- duplicate email;
- broken PDF;
- empty PDF;
- unreadable handwriting;
- missing patient age;
- missing reporter;
- ICSR + PQC;
- non-English document;
- invalid AI JSON;
- AI timeout.

---

# 22. Implementation Order

Do not attempt to build everything at once.

## Module 1 — Foundation

Implement in this order:

1. Docker Compose foundation.
2. Oracle service/schema.
3. Spring Boot application.
4. Entities and repositories.
5. Mailbox abstraction.
6. Mock mailbox.
7. IMAP mailbox.
8. Email parser.
9. Attachment storage.
10. Idempotency.
11. Processing jobs.
12. In-process queue.
13. Worker.
14. Health checks.
15. Tests.

### Module 1 definition of done

- Docker starts.
- Oracle starts.
- Spring Boot starts.
- Mailbox ingestion works.
- Email is persisted.
- PDF is persisted.
- Processing job is created.
- Queue works.
- Duplicate email does not duplicate processing.
- Tests pass.

Do not proceed to Module 2 until this works.

---

# 23. Module 2 — AI Pipeline

Implement in this order:

1. FastAPI container.
2. `/health`.
3. Configurable Qwen3-VL-2B-Instruct.
4. PDF format detection.
5. PyMuPDF digital extraction.
6. pdfplumber tables.
7. scanned/handwritten processing.
8. image processing.
9. language detection.
10. translation while preserving original.
11. article processing.
12. canonical context.
13. Pydantic schemas.
14. master prompt.
15. classification.
16. ICSR extraction.
17. PQC extraction.
18. MI extraction.
19. summary/relevance.
20. validation.
21. source validation.
22. Spring AI client.
23. result persistence.
24. metrics.
25. retry.
26. audit.
27. tests.

### Module 2 definition of done

- FastAPI runs in Docker.
- AI health endpoint works.
- Model is configurable.
- Digital PDFs work.
- Scanned PDFs work.
- Handwritten PDFs work.
- Article PDFs work.
- Non-English PDFs work.
- Tables are structured.
- Images are described.
- Multi-label classification works.
- ICSR extraction works.
- PQC extraction works.
- MI extraction works.
- Not Relevant works.
- Missing fields return `Not stated`.
- Every field has confidence.
- Every field has a source.
- Pydantic validation works.
- Results persist in Oracle.
- Retry works.
- Metrics are recorded.
- Audit entries are created.

Do not proceed to final UI integration until this works.

---

# 24. Module 3 — Reviewer Application

Implement:

1. Angular Docker build.
2. Nginx serving.
3. Review queue.
4. Search/filter/sort.
5. Review detail.
6. Email display.
7. Classification display.
8. Facts table.
9. PDF viewer.
10. Source viewer.
11. Source navigation.
12. Image evidence.
13. Accept.
14. Override.
15. Audit timeline.
16. Error states.
17. End-to-end dataset.
18. Batch benchmark.
19. Failure tests.
20. Final documentation.

### Module 3 definition of done

A reviewer can:

```text
open queue
 -> open email
 -> inspect AI result
 -> inspect extracted facts
 -> click source
 -> navigate to PDF/email evidence
 -> accept OR override
 -> see audit history
```

---

# 25. Coding Agent Rules

## Rule 1 — Inspect before modifying

Before coding a module:

- inspect existing repository;
- inspect relevant source files;
- identify what already exists;
- avoid duplicate implementations.

## Rule 2 — Small changes

Prefer small, testable commits/changes.

Do not rewrite unrelated code.

## Rule 3 — Do not fake functionality

Do not create UI buttons that do nothing.

Do not return hardcoded AI results from production paths.

Mocks are acceptable only for:

- mailbox development;
- deterministic tests;
- explicitly documented fallback development modes.

## Rule 4 — Do not hide failures

Errors must be:

- logged appropriately;
- represented in job state;
- retried where appropriate;
- surfaced to the reviewer when required.

## Rule 5 — Validate AI output

Never persist unchecked LLM output as a final result.

## Rule 6 — Preserve evidence

Never strip source/page information during transformations.

## Rule 7 — Keep model logic isolated

Do not scatter Qwen-specific code through Spring services or Angular components.

## Rule 8 — Configuration over hardcoding

Use environment/configuration for:

- database URL;
- database credentials;
- mailbox credentials;
- AI service URL;
- model name;
- storage path;
- retry count;
- timeouts.

Provide `.env.example`.

Never commit secrets.

## Rule 9 — Tests are part of implementation

For every significant backend/AI feature, add tests.

At minimum:

- unit tests for parsing;
- validation tests;
- source validation tests;
- classification schema tests;
- idempotency tests;
- retry tests;
- API tests;
- end-to-end smoke tests.

## Rule 10 — Keep the prototype appropriately scoped

Do not add:

- Kubernetes;
- Kafka;
- complex distributed microservices;
- production IAM;
- elaborate observability stacks;

unless specifically required.

The assignment is a prototype and explicitly favors a simple in-process queue.

---

# 26. AI Prompt Rules

The master extraction prompt must instruct the model:

```text
You are a healthcare document extraction assistant.

Use only information explicitly supported by the provided email/document context.

Never guess or infer missing facts.

If a requested fact is absent, return exactly:
"Not stated"

For every extracted field return:
- value
- confidence
- source reference

Classification is multi-label.

Allowed categories:
ICSR
PQC
MI
NOT_RELEVANT

Give a concise reason for every classification.

Do not invent patient information, reporter information,
product information, dates, reactions, outcomes, questions,
batch numbers, or other facts.

Do not perform medical diagnosis.

Return structured output matching the provided schema.
```

The actual prompt can be refined during implementation, but these rules are mandatory.

---

# 27. Source Validation Rules

For every extracted field:

```text
source exists
source type is valid
source belongs to the current email/document
page exists when source is PDF
snippet exists where applicable
```

Reject:

```text
field without source
invalid page
source from another attachment
unsupported source type
```

Source validation is a hard quality gate.

---

# 28. Retry Strategy

Retry recoverable failures such as:

- temporary AI timeout;
- transient AI service failure;
- invalid structured output;
- source validation failure caused by model output.

Do not retry indefinitely.

Use configurable maximum retries.

Example:

```text
AI failure
   |
   v
retryCount < maxRetries?
   | yes
   v
RETRYING -> QUEUED
   |
   no
   v
REVIEW_REQUIRED
```

---

# 29. Local Development

Support:

```bash
docker compose up --build
```

Also make individual services runnable locally when practical.

Do not make local development and Docker development use fundamentally different business logic.

Use environment variables.

---

# 30. Verification Protocol

After each module:

1. Build.
2. Run unit tests.
3. Run service tests.
4. Start Docker.
5. Check health endpoints.
6. Execute a real flow.
7. Inspect persisted data.
8. Inspect logs.
9. Fix failures.
10. Only then move forward.

Final verification must include:

```text
Docker clean start
Mailbox ingestion
PDF storage
AI processing
Oracle persistence
Angular review
Source navigation
Accept
Override
Audit
Retry
Metrics
10–15 document benchmark
```

---

# 31. Demo Path

The primary demo should be short and deterministic:

```text
Synthetic email
    |
    v
Mailbox ingestion
    |
    v
Spring Boot
    |
    +--> Oracle
    +--> PDF storage
    |
    v
Processing Queue
    |
    v
FastAPI
    |
    +--> PDF extraction
    +--> Qwen3-VL-2B
    +--> classification
    +--> extraction
    +--> summary
    +--> validation
    +--> source validation
    |
    v
Oracle
    |
    v
Angular Review Queue
    |
    v
Review Detail
    |
    +--> evidence/source
    +--> PDF page
    |
    v
Accept / Override
    |
    v
Audit Timeline
```

Choose demo documents that visibly demonstrate:

- ICSR;
- source traceability;
- a missing field returning `Not stated`;
- multi-label classification if available;
- reviewer override;
- audit history.

---

# 32. Performance / Model Constraints

The primary model is intentionally lightweight.

Do not compensate for model limitations by moving all processing into the VLM.

Prefer:

```text
deterministic extraction
    +
targeted multimodal inference
    +
structured validation
```

over:

```text
send entire PDF blindly to LLM
```

Record processing timings so the assignment can report per-document performance.

---

# 33. Production Evolution

Do not implement these unless necessary for the prototype, but keep boundaries that allow future evolution:

```text
IMAP / Microsoft Graph
        |
Durable Message Queue
        |
Spring Boot
        |
Object Storage
        |
Dedicated AI Workers
        |
Model Gateway
        |
Oracle
        |
Angular
```

Potential future components:

- durable message broker;
- object storage;
- scalable AI workers;
- model gateway;
- dedicated OCR;
- authentication/authorization;
- secrets manager;
- distributed tracing;
- centralized logging;
- monitoring;
- dead-letter queues.

Prototype simplicity is intentional.

---

# 34. Documentation Requirements

Keep documentation updated as implementation changes.

README must explain:

- architecture;
- prerequisites;
- environment variables;
- Docker setup;
- how to start;
- how to run tests;
- mailbox configuration;
- AI model configuration;
- test dataset;
- API endpoints;
- known limitations;
- model/cloud tradeoff;
- benchmark results;
- reviewer workflow.

Do not claim a feature works unless it has been verified.

---

# 35. Change Management

When making a design change:

1. Explain why the change is needed.
2. Check HLD/LLD consistency.
3. Update affected documentation.
4. Update tests.
5. Implement.
6. Verify end-to-end.

Do not allow code and design documents to drift.

---

# 36. Priority Order

If time is limited, prioritize:

```text
P0 — MUST WORK
├── Docker
├── Oracle
├── Email ingestion
├── PDF storage
├── Processing queue
├── Digital PDF extraction
├── AI classification
├── ICSR/PQC/MI extraction
├── Not stated rule
├── Confidence
├── Source traceability
├── Oracle persistence
├── Review UI
├── Accept/Override
└── Audit

P1 — IMPORTANT
├── Scanned PDFs
├── Handwriting
├── Tables
├── Article PDFs
├── Non-English
├── Images
├── Retry
└── Metrics

P2 — POLISH
├── Search/filter/sort
├── Better PDF navigation
├── UI polish
├── Benchmark visualization
└── Optional extensions
```

Never sacrifice source traceability, the `Not stated` rule, validation, or human review merely to add cosmetic features.

---

# 37. Final Instruction to the Coding Agent

Build incrementally.

Do not generate a giant speculative codebase.

At the start of each phase:

```text
1. Read the relevant requirements.
2. Inspect the repository.
3. State the implementation plan briefly.
4. Implement the smallest coherent slice.
5. Run tests.
6. Run Docker verification where applicable.
7. Fix failures.
8. Report what is complete and what remains.
```

Do not proceed to the next module until the current module's definition of done is substantially satisfied.

The objective is not merely to produce code.

The objective is to produce a **working, demonstrable, traceable Smart Inbox Assistant** that can survive a 15–20 minute technical walkthrough.
