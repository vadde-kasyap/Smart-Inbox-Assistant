"""
Master Prompt and extraction templates for Healthcare / Pharmacovigilance Inbox Assistant.
Enforces non-negotiable safety rules:
1. Synthetic data only.
2. Never guess or infer missing facts (return exactly 'Not stated').
3. Every field must have numeric confidence and a valid source reference.
4. Multi-label classification supported (ICSR, PQC, MI, NOT_RELEVANT).
5. Meaningful 10-15 sentence summary and relevance rationale.
"""

MASTER_SYSTEM_PROMPT = """You are a healthcare and pharmacovigilance document extraction assistant.

Your task is to analyze the provided email and attached document evidence, classify the content, and extract domain facts with exact source traceability.

NON-NEGOTIABLE SAFETY RULES:
1. Never guess or infer missing facts. If an item is not explicitly stated in the source text, you MUST return exactly "Not stated".
2. Every extracted field MUST have:
   - A numeric confidence score between 0.0 and 1.0.
   - At least one source reference containing the exact source type (PDF or EMAIL), page number, and relevant text snippet.
3. Classification is MULTI-LABEL. Allowed categories:
   - ICSR (Individual Case Safety Report / Adverse Event)
   - PQC (Product Quality Complaint / Defect)
   - MI (Medical Information Request / Inquiry)
   - NOT_RELEVANT (Unrelated communication)
   Provide a clear, grounded reason for each classification.
4. Provide a grounded 10–15 sentence narrative summary explaining what the document states, key facts, uncertainties, and relevance.
5. Do NOT perform medical diagnosis. Extract only what is written.
"""

REQUIRED_ICSR_FIELDS = [
    ("patient", "age"),
    ("patient", "sex"),
    ("patient", "weight"),
    ("patient", "height"),
    ("patient", "relevant_history"),
    ("reporter", "identity"),
    ("reporter", "role"),
    ("reporter", "country"),
    ("product", "name"),
    ("product", "dose"),
    ("product", "route"),
    ("product", "start_date"),
    ("product", "stop_date"),
    ("reaction", "description"),
    ("reaction", "onset_date"),
    ("reaction", "outcome"),
    ("other", "seriousness"),
    ("other", "narrative"),
]

REQUIRED_PQC_FIELDS = [
    ("pqc", "product"),
    ("pqc", "batch_lot"),
    ("pqc", "issue"),
    ("pqc", "photo_mentioned"),
]

REQUIRED_MI_FIELDS = [
    ("mi", "questions"),
    ("mi", "product"),
    ("mi", "topic"),
]
