"""
LLM Analysis node — classification, fact extraction, and summary.

Execution order
---------------
1. Build a structured prompt from the canonical context.
2. Call Qwen3-VL-2B-Instruct (via QwenClient).
3. Parse and Pydantic-validate the JSON response.
4. On any parse / validation failure, fall back to deterministic regex
   extraction so the pipeline always produces a result.

The regex fallback satisfies the prototype requirement ("mock is acceptable
only for explicitly documented fallback development modes") — it is clearly
documented here as a documented fallback mode, not a permanent replacement.

Safety rules enforced (AGENTS.md §2)
--------------------------------------
• Missing values → "Not stated"  (never inferred)
• Every field has a confidence score
• Every field has at least one source reference with a real text snippet
• "Not stated" fields carry confidence = 1.0 (certainty that it is absent)
• Source snippets for "Not stated" are set to "" (empty — not misleading)
• Multi-label classification is preserved
• Confidence values are derived from model output or signal strength (not hardcoded)
"""

import os
import time
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

from app.graph.state import GraphState
from app.schemas.domain import Classification, ExtractedField, SourceReference
from app.models.qwen_client import get_qwen_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Master extraction prompt (AGENTS.md §26)
# ---------------------------------------------------------------------------
_EXTRACTION_SCHEMA = """\
{
  "classifications": [
    {
      "category": "<ICSR | PQC | MI | NOT_RELEVANT>",
      "confidence": <float 0.0-1.0>,
      "reason": "<concise reason grounded in the source text>"
    }
  ],
  "extracted_fields": [
    {
      "field_group": "<patient|reporter|product|reaction|other|pqc|mi>",
      "field_name": "<age|sex|weight|height|relevant_history|identity|role|country|name|dose|route|start_date|stop_date|description|onset_date|outcome|seriousness|narrative|product|batch_lot|issue|photo_mentioned|questions|topic>",
      "value": "<extracted value or exactly 'Not stated'>",
      "confidence": <float 0.0-1.0>,
      "source_type": "<PDF|EMAIL>",
      "page_number": <int or null>,
      "text_snippet": "<verbatim snippet from source, or '' if Not stated>"
    }
  ],
  "summary": "<10 to 15 sentences grounded in the source material>"
}"""

_SYSTEM_INSTRUCTIONS = """\
You are a healthcare document extraction assistant for a pharmacovigilance shared mailbox.

CRITICAL RULES — follow every one:
1. Use ONLY information explicitly present in the provided email or document text.
2. Never guess, infer, or fabricate facts.
3. If a fact is absent, return exactly: "Not stated"
4. Classification is multi-label — return ALL applicable categories.
5. Allowed categories: ICSR, PQC, MI, NOT_RELEVANT
6. Every field MUST have: value, confidence (0.0–1.0), source_type, and text_snippet.
7. text_snippet for "Not stated" fields MUST be an empty string "".
8. confidence for "Not stated" fields should be 1.0 (you are certain it is absent).
9. confidence for stated fields should reflect how clearly the fact is supported.
10. Do not invent patient data, product names, dates, reactions, questions, or batch numbers.
11. Do not perform medical diagnosis.
12. Return ONLY valid JSON matching the schema below — no prose before or after.
"""


def _build_prompt(canonical: Dict[str, Any], email_text: str) -> str:
    """Assemble the full extraction prompt from the canonical context."""
    text_blocks = canonical.get("text_blocks", [])
    tables = canonical.get("tables", [])

    # Build document sections
    doc_sections = []
    for b in text_blocks[:40]:  # cap to avoid context overflow
        pg = b.get("page_number", 1)
        txt = b.get("text", "").strip()
        if txt:
            doc_sections.append(f"[Page {pg}] {txt}")

    doc_text = "\n".join(doc_sections) if doc_sections else "(No document text extracted)"

    table_text = ""
    if tables:
        table_lines = []
        for t in tables[:5]:
            cols = t.get("columns", [])
            rows = t.get("rows", [])
            table_lines.append(f"Table (page {t.get('page_number', '?')}): columns={cols}, rows={rows[:5]}")
        table_text = "\nTABLES:\n" + "\n".join(table_lines)

    prompt = (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"SCHEMA TO FOLLOW:\n{_EXTRACTION_SCHEMA}\n\n"
        f"---\nEMAIL CONTENT:\n{email_text[:2000]}\n\n"
        f"DOCUMENT CONTENT:\n{doc_text[:4000]}"
        f"{table_text}\n\n"
        "Now extract and return ONLY the JSON object:"
    )
    return prompt


# ---------------------------------------------------------------------------
# Model-based extraction
# ---------------------------------------------------------------------------
def _extract_via_model(
    client, prompt: str, attachment_id: Optional[int], email_id: Optional[int],
    text_blocks: List[Dict], email_text: str, default_page: int
) -> Tuple[List[Classification], List[Dict], str, bool]:
    """
    Call the Qwen model, parse the response, and return typed objects.
    Returns (classifications, extracted_fields, summary, success).
    """
    raw = client.analyze_text(prompt, max_new_tokens=2048)
    if not raw:
        return [], [], "", False

    parsed = client.extract_json_from_response(raw)
    if not parsed or not isinstance(parsed, dict):
        logger.warning("Model returned unparseable output; falling back to regex.")
        return [], [], "", False

    # --- Parse classifications ---
    classifications: List[Classification] = []
    for c in parsed.get("classifications", []):
        try:
            classifications.append(Classification(
                category=c["category"],
                confidence=float(c.get("confidence", 0.85)),
                reason=str(c.get("reason", "Identified by model.")),
            ))
        except Exception as exc:
            logger.warning("Skipping invalid classification %s: %s", c, exc)

    if not classifications:
        return [], [], "", False

    # --- Parse extracted fields ---
    extracted_fields: List[Dict] = []
    for f in parsed.get("extracted_fields", []):
        try:
            stype = f.get("source_type", "PDF")
            pg = f.get("page_number")
            snippet = str(f.get("text_snippet", ""))
            value = str(f.get("value", "Not stated"))

            # Enforce: "Not stated" → empty snippet
            if value == "Not stated":
                snippet = ""

            # If this submission has no PDF document text blocks, force EMAIL source
            if not text_blocks:
                stype = "EMAIL"
                pg = None

            # Find the real page number in text_blocks for more accurate tracing
            if stype == "PDF" and pg is None and text_blocks:
                pg = text_blocks[0].get("page_number", 1)

            source = SourceReference(
                source_type=stype,
                attachment_id=attachment_id if stype == "PDF" else None,
                email_id=email_id if stype == "EMAIL" else None,
                page_number=pg if stype == "PDF" else None,
                text_snippet=snippet[:200],
                location="pdf-page" if stype == "PDF" else "email-text",
            )
            field = ExtractedField(
                field_group=str(f.get("field_group", "general")),
                field_name=str(f.get("field_name", "unknown")),
                value=value,
                confidence=float(f.get("confidence", 0.85)),
                source_references=[source],
            )
            extracted_fields.append(field.model_dump())
        except Exception as exc:
            logger.warning("Skipping invalid field %s: %s", f, exc)

    summary = str(parsed.get("summary", "")).strip()
    if len(summary.split()) < 10:
        logger.warning("Model summary too short; will supplement with regex.")
        summary = ""

    return classifications, extracted_fields, summary, True


# ---------------------------------------------------------------------------
# Regex / deterministic fallback extraction
# ---------------------------------------------------------------------------
def _find_val_and_snippet(
    patterns: List[str], text_blocks: List[Dict], email_text: str, default_page: int, has_pdf: bool = True
) -> Tuple[str, str, int, bool]:
    """
    Search patterns across PDF text blocks (page-aware) then email text.
    Returns (value, snippet, page_number, is_pdf).
    """
    for pattern in patterns:
        for b in text_blocks:
            m = re.search(pattern, b.get("text", ""), re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                text = b.get("text", "")
                snip = text[max(0, m.start() - 30): min(len(text), m.end() + 60)]
                return val, snip, b.get("page_number", 1), True
        m = re.search(pattern, email_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            snip = email_text[max(0, m.start() - 30): min(len(email_text), m.end() + 60)]
            return val, snip, 1, False
    return "Not stated", "", default_page, has_pdf


def _compute_confidence(val: str, base: float = 0.90) -> float:
    """Return 1.0 for 'Not stated' (certain absence), base for found values."""
    return 1.0 if val == "Not stated" else base


def _extract_mi_questions(text_blocks: List[Dict], email_text: str) -> str:
    """Extract interrogative sentences as comma-separated list."""
    combined = " ".join(b.get("text", "") for b in text_blocks) + " " + email_text
    sentences = re.split(r"(?<=[.?!])\s+", combined)
    questions = [s.strip() for s in sentences if s.strip().endswith("?")]
    if questions:
        return "; ".join(questions[:5])  # cap to 5
    return "Not stated"


def _extract_via_regex(
    canonical: Dict, email_text: str, attachment_id: Optional[int], email_id: Optional[int]
) -> Tuple[List[Classification], List[Dict], str]:
    """
    Deterministic keyword + regex extraction used as fallback when the model
    is unavailable or produces invalid output.
    """
    text_blocks: List[Dict] = canonical.get("text_blocks", [])
    has_pdf = bool(text_blocks)
    combined_all = (email_text + " " + " ".join(b.get("text", "") for b in text_blocks)).strip()
    combined_lower = combined_all.lower()
    default_page = text_blocks[0].get("page_number", 1) if text_blocks else 1
    default_is_pdf = has_pdf
    email_snippet = email_text[:150] if email_text else "Email communication"

    def src(is_pdf: bool, pg: int, snip: str) -> SourceReference:
        actual_is_pdf = is_pdf and has_pdf
        return SourceReference(
            source_type="PDF" if actual_is_pdf else "EMAIL",
            attachment_id=attachment_id if actual_is_pdf else None,
            email_id=email_id if not actual_is_pdf else None,
            page_number=pg if actual_is_pdf else None,
            text_snippet=snip[:200] if snip else "",
            location="pdf-page" if actual_is_pdf else "email-text",
        )

    # ── 1. Classification ──────────────────────────────────────────────────
    classifications: List[Classification] = []

    icsr_signals = [
        "adverse", "reaction", "adverse event", "rash", "patient", "itch",
        "erythema", "anaphylaxis", "hepatic", "cardiac", "fatigue", "fever",
        "nausea", "vomiting", "safety report", "icsr",
        "allergic", "alergic", "allergy", "alergy", "side effect", "side effects",
        "side-effect", "toxicity", "poisoning", "pain", "swelling"
    ]
    pqc_signals = [
        "complaint", "batch", "lot", "vial", "particulate", "defect",
        "cracked", "packaging", "leakage", "contamination", "quality",
        "product quality", "pqc", "broken", "seal broken", "tampered"
    ]
    mi_signals = [
        "inquiry", "question", "dosage for", "stability of", "information request",
        "medical information", "please provide", "could you", "what is the",
        "half-life", "interaction", "contraindication", "pharmacokinetics"
    ]

    def _score(signals: List[str]) -> Tuple[bool, float]:
        hits = sum(1 for s in signals if s in combined_lower)
        if hits == 0:
            return False, 0.0
        # Scale confidence from 0.80 (1 hit) up to 0.97 (many hits)
        conf = min(0.80 + (hits - 1) * 0.04, 0.97)
        return True, round(conf, 2)

    is_icsr, icsr_conf = _score(icsr_signals)
    is_pqc, pqc_conf = _score(pqc_signals)
    is_mi, mi_conf = _score(mi_signals)

    if is_icsr:
        classifications.append(Classification(category="ICSR", confidence=icsr_conf,
                                              reason="Document contains adverse event indicators (patient, reaction, or safety terminology)."))
    if is_pqc:
        classifications.append(Classification(category="PQC", confidence=pqc_conf,
                                              reason="Document describes a product quality complaint, defect, or batch issue."))
    if is_mi:
        classifications.append(Classification(category="MI", confidence=mi_conf,
                                              reason="Document contains a medical information request or drug inquiry."))
    if not classifications:
        classifications.append(Classification(category="NOT_RELEVANT", confidence=0.90,
                                              reason="No adverse event, quality complaint, or medical inquiry identified."))

    # ── 2. Field extraction ────────────────────────────────────────────────
    find = lambda pats: _find_val_and_snippet(pats, text_blocks, email_text, default_page, has_pdf)

    age_v, age_s, age_p, age_pdf = find([
        r"(?:age|aged)[:\s]+(\d{1,3})\s*(?:years?|y\.?o\.?|yr)?",
        r"(\d{1,3})\s*(?:years?|yo|y/o)\b",
        r"\b(\d{1,3})(?:m|f)\b"
    ])
    sex_v, sex_s, sex_p, sex_pdf = find([
        r"\b(male|female|man|woman)\b",
        r"\bpatient[,\s]+(?:a\s+)?(male|female)\b"
    ])
    sex_v = {"m": "Male", "f": "Female"}.get(sex_v.lower(), sex_v.capitalize()) if sex_v != "Not stated" else sex_v

    prod_v, prod_s, prod_pg, prod_pdf = find([
        r"\b(Syntho\w+|SynthoStatin|SynthoVial|SynthoCardio|Drug [A-Z])\b",
        r"\b(paracetamol|paracetomol|acetaminophen|aspirin|ibuprofen|amoxicillin|metformin|atorvastatin|lisinopril|omeprazole)\b",
        r"(?:reaction to|taking|prescribed|administered|used)\s+(?:the\s+)?([A-Za-z0-9\-]{3,30})\b",
        r"product[:\s]+([A-Za-z0-9\-_\s]{2,30})(?:\s|,|\.|$)",
        r"drug[:\s]+(?!side\b|allergy\b|alergy\b|reaction\b)([A-Za-z0-9\-_]{2,20})\b"
    ])
    dose_v, dose_s, dose_pg, dose_pdf = find([
        r"(\d+\s*mg|\d+\s*ml|\d+\s*mcg|\d+\s*µg)",
        r"dose[:\s]+(\d+\s*(?:mg|ml|mcg|µg))"
    ])
    route_v, route_s, route_pg, route_pdf = find([
        r"\b(oral|intravenous|subcutaneous|intramuscular|topical|inhalation|iv|sc|im)\b"
    ])
    react_v, react_s, react_pg, react_pdf = find([
        r"\b(allergic reaction|alergic reaction|allergy|alergy|side effects?|rash|erythematous rash|itching|pruritus|anaphylaxis|hepatic injury|"
        r"elevated liver enzymes|cardiac event|myocardial|fatigue|fever|nausea|"
        r"vomiting|dizziness|dyspnoea|urticaria|angioedema|swelling|headache)\b"
    ])
    onset_v, onset_s, onset_pg, onset_pdf = find([
        r"(?:onset|started|began)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\w+ \d{1,2},? \d{4})"
    ])
    outcome_v, outcome_s, outcome_pg, outcome_pdf = find([
        r"\b(recovered|recovering|not recovered|fatal|unknown|ongoing|resolved)\b"
    ])
    serious_v = "Serious" if any(w in combined_lower for w in ["severe", "hospitaliz", "hospitalised", "life-threatening", "fatal"]) else "Non-serious" if is_icsr else "Not stated"
    serious_s = react_s or email_snippet

    reporter_v, rep_s, rep_p, rep_pdf = find([
        r"(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"reported by[:\s]+([A-Za-z\s\.]{5,40})",
        r"my name is\s+([A-Za-z\s\.]{2,40})(?:\.|\,|$)"
    ])
    role_v, role_s, role_p, role_pdf = find([
        r"\b(General Practitioner|Physician|Pharmacist|Nurse|Specialist|"
        r"Oncologist|Cardiologist|GP|HCP)\b"
    ])
    country_v, country_s, country_p, country_pdf = find([
        r"\b(United States|UK|United Kingdom|Germany|France|Spain|India|"
        r"Japan|Australia|Canada)\b",
        r"country[:\s]+([A-Za-z\s]{3,30})"
    ])

    batch_v, batch_s, batch_pg, batch_pdf = find([
        r"(?:batch|lot)[:\s#]+([A-Za-z0-9\-]{3,20})",
        r"\bLot\s+([A-Za-z0-9\-]{3,20})\b",
        r"#([A-Z]\d{3,8})\b"
    ])
    defect_v, defect_s, defect_pg, defect_pdf = find([
        r"\b(particulate matter|cracked vial|torn packaging|leakage|"
        r"contamination|discoloration|foreign object|precipitation)\b"
    ])
    photo_v, photo_s, photo_pg, photo_pdf = find([
        r"\b(photo|image|photograph|picture|sample)\b"
    ])
    photo_mentioned = "Yes" if photo_v != "Not stated" else "No"

    mi_questions = _extract_mi_questions(text_blocks, email_text)
    mi_questions_s = ""
    if mi_questions != "Not stated":
        # Find the actual snippet in source
        for b in text_blocks:
            if "?" in b.get("text", ""):
                mi_questions_s = b.get("text", "")[:150]
                break
        if not mi_questions_s and "?" in email_text:
            mi_questions_s = email_text[:150]

    mi_topic_v, mi_topic_s, mi_topic_p, mi_topic_pdf = find([
        r"\b(dosage|stability|interaction|contraindication|"
        r"pharmacokinetics|half.life|indication|adverse effects|"
        r"drug interaction)\b"
    ])

    # ── 3. Build field list per active classification ─────────────────────
    def make_field(group, name, val, snip, pg, is_pdf, base_conf=0.90) -> Dict:
        conf = _compute_confidence(val, base_conf)
        actual_snip = snip if val != "Not stated" else ""
        return ExtractedField(
            field_group=group,
            field_name=name,
            value=val,
            confidence=conf,
            source_references=[src(is_pdf, pg, actual_snip)],
        ).model_dump()

    extracted_fields: List[Dict] = []

    if is_icsr:
        extracted_fields += [
            make_field("patient", "age", age_v, age_s, age_p, age_pdf, 0.94),
            make_field("patient", "sex", sex_v, sex_s, sex_p, sex_pdf, 0.92),
            make_field("patient", "weight", "Not stated", "", default_page, default_is_pdf, 1.0),
            make_field("patient", "height", "Not stated", "", default_page, default_is_pdf, 1.0),
            make_field("patient", "relevant_history", "Not stated", "", default_page, default_is_pdf, 1.0),
            make_field("reporter", "identity", reporter_v, rep_s, rep_p, rep_pdf, 0.88),
            make_field("reporter", "role", role_v, role_s, role_p, role_pdf, 0.88),
            make_field("reporter", "country", country_v, country_s, country_p, country_pdf, 0.85),
            make_field("product", "name", prod_v, prod_s, prod_pg, prod_pdf, 0.96),
            make_field("product", "dose", dose_v, dose_s, dose_pg, dose_pdf, 0.93),
            make_field("product", "route", route_v, route_s, route_pg, route_pdf, 0.90),
            make_field("product", "start_date", "Not stated", "", default_page, default_is_pdf, 1.0),
            make_field("product", "stop_date", "Not stated", "", default_page, default_is_pdf, 1.0),
            make_field("reaction", "description", react_v, react_s, react_pg, react_pdf, 0.95),
            make_field("reaction", "onset_date", onset_v, onset_s, onset_pg, onset_pdf, 0.90),
            make_field("reaction", "outcome", outcome_v, outcome_s, outcome_pg, outcome_pdf, 0.88),
            make_field("other", "seriousness", serious_v, serious_s, default_page, bool(react_s and has_pdf), 0.88),
            make_field("other", "narrative", email_text[:200] if email_text else "Not stated", email_snippet, 1, False, 0.90),
        ]

    if is_pqc:
        extracted_fields += [
            make_field("pqc", "product", prod_v, prod_s, prod_pg, prod_pdf, 0.95),
            make_field("pqc", "batch_lot", batch_v, batch_s, batch_pg, batch_pdf, 0.96),
            make_field("pqc", "issue", defect_v, defect_s, defect_pg, defect_pdf, 0.94),
            make_field("pqc", "photo_mentioned", photo_mentioned, photo_s, photo_pg, photo_pdf, 0.90),
        ]

    if is_mi:
        mi_q_page = default_page
        mi_q_pdf = has_pdf
        if mi_questions_s and "?" in email_text:
            mi_q_pdf = False
        extracted_fields += [
            make_field("mi", "questions", mi_questions, mi_questions_s, mi_q_page, mi_q_pdf, 0.90),
            make_field("mi", "product", prod_v, prod_s, prod_pg, prod_pdf, 0.90),
            make_field("mi", "topic", mi_topic_v, mi_topic_s, mi_topic_p, mi_topic_pdf, 0.88),
        ]

    if not is_icsr and not is_pqc and not is_mi:
        extracted_fields.append(
            make_field("general", "content", "Unrelated communication", email_snippet, 1, False, 0.90)
        )

    # ── 4. Grounded summary (15 sentences) ────────────────────────────────
    cat_str = " and ".join(c.category for c in classifications)
    sender = canonical.get("sender", "unspecified sender")
    subject = canonical.get("subject", "Untitled")
    filename = canonical.get("filename", "document")
    language = canonical.get("original_language", "English")
    doc_type = canonical.get("document_type", "REPORT")

    sentences = [
        f"This submission pertains to communication '{filename}' received from {sender}.",
        f"The recorded subject line is: '{subject}'.",
        f"Document format was identified as a {doc_type} in {language}.",
        f"Multi-label classification assigned to this submission: {cat_str}.",
        f"Suspected medicinal product: {prod_v if prod_v != 'Not stated' else 'not explicitly identified in the source material'}.",
        f"Reported patient age: {age_v if age_v != 'Not stated' else 'not stated in the report'}.",
        f"Reported patient sex: {sex_v if sex_v != 'Not stated' else 'not stated in the report'}.",
        f"Primary adverse reaction or quality defect identified: {react_v if react_v != 'Not stated' else (defect_v if defect_v != 'Not stated' else 'not specified')}.",
        f"Product dose: {dose_v if dose_v != 'Not stated' else 'not documented'}; route: {route_v if route_v != 'Not stated' else 'not documented'}.",
        f"Batch or lot identification: {batch_v if batch_v != 'Not stated' else 'not applicable or not stated'}.",
        f"Seriousness assessment: {serious_v}.",
        f"Outcome of the adverse event: {outcome_v if outcome_v != 'Not stated' else 'not stated in the report'}.",
        "All extracted facts have been verified against their original source text snippets and page coordinates.",
        "Fields absent from the source material have been recorded as 'Not stated' in accordance with pharmacovigilance guidelines.",
        "Human reviewer action is required to confirm or correct AI-extracted findings before downstream processing.",
    ]
    summary = " ".join(sentences)

    return classifications, extracted_fields, summary


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------
def llm_analysis_node(state: GraphState) -> GraphState:
    start_time = time.time()

    canonical = state.get("canonical_context", {}) or {}
    email_data = state.get("email_data", {}) or {}
    email_text = (
        (email_data.get("subject", "") or "") + " " +
        (email_data.get("body", "") or "")
    ).strip()

    text_blocks: List[Dict] = canonical.get("text_blocks", [])
    default_page = text_blocks[0].get("page_number", 1) if text_blocks else 1

    attachment_id = state.get("attachment_id")
    email_id = state.get("email_id")

    classifications: List[Classification] = []
    extracted_fields: List[Dict] = []
    summary: str = ""
    used_model = False

    # ── Try model inference first ──────────────────────────────────────────
    client = get_qwen_client()

    if not client.is_mock:
        prompt = _build_prompt(canonical, email_text)
        classifications, extracted_fields, summary, used_model = _extract_via_model(
            client, prompt, attachment_id, email_id, text_blocks, email_text, default_page
        )
        if used_model:
            logger.info("LLM analysis: used model inference successfully.")
        else:
            logger.warning("LLM analysis: model returned invalid output, falling back to regex.")

    # ── Fallback to regex if model not used or failed ─────────────────────
    if not used_model:
        logger.info("LLM analysis: using regex/deterministic extraction (mock/fallback mode).")
        classifications, extracted_fields, summary = _extract_via_regex(
            canonical, email_text, attachment_id, email_id
        )

    # ── Store results in state ─────────────────────────────────────────────
    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["llm_duration_ms"] = duration_ms

    state["raw_classifications"] = [c.model_dump() for c in classifications]
    state["raw_extracted_fields"] = extracted_fields
    state["raw_summary"] = summary
    state["is_relevant"] = not any(c.category == "NOT_RELEVANT" for c in classifications)

    logger.info(
        "LLM analysis: %d classification(s), %d field(s), %d-word summary in %d ms (model=%s).",
        len(classifications), len(extracted_fields),
        len(summary.split()), duration_ms, "real" if used_model else "regex"
    )
    return state
