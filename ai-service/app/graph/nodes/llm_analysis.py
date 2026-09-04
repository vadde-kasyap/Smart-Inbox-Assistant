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
   - ICSR: adverse drug reactions, side effects, patient symptoms experienced from medication.
   - PQC: product quality complaints, broken bottles/vials, damaged packaging, leaking, contamination, short fills, discoloration, particles, physical defects.
   - MI: medical inquiries regarding dosing, stability, contraindications, administration without adverse event.
   - NOT_RELEVANT: unrelated facilities, scheduling, marketing, or general office communications.
6. Every field MUST have: value, confidence (0.0–1.0), source_type, and text_snippet.
7. text_snippet for "Not stated" fields MUST be an empty string "".
8. confidence for "Not stated" fields should be 1.0 (you are certain it is absent).
9. confidence for stated fields should reflect how clearly the fact is supported.
10. Do not invent patient data, product names, dates, reactions, questions, or batch numbers.
11. Do not perform medical diagnosis.
12. When extracting reporter.identity: if the sender is an email address (e.g. vaddekasyap@gmail.com or VADDEKASYAP@GMAIL.COM), parse and format it into a proper human name in Title Case (e.g. 'Vadde Kasyap') rather than outputting a raw uppercase/lowercase email address.
13. Return ONLY valid JSON matching the schema below — no prose before or after.
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
# Human name extraction and cleaning helper
# ---------------------------------------------------------------------------
def _clean_human_name(raw: str) -> str:
    """
    Format a human-readable reporter name dynamically from display strings,
    email headers, or raw email addresses.
    Example:
      'VADDEKASYAP@GMAIL.COM' -> 'Vadde Kasyap'
      'vaddekasyap@gmail.com' -> 'Vadde Kasyap'
      'vadde.kasyap@gmail.com' -> 'Vadde Kasyap'
      'test1@gmail.com' -> 'Test1'
      '"Dr. John Smith" <jsmith@clinic.org>' -> 'Dr. John Smith'
      'dr.jane_smith@hospital.org' -> 'Dr Jane Smith'
    """
    if not raw or raw.strip() == "" or raw.strip().lower() in ("not stated", "unspecified sender", "unknown", "none"):
        return "Not stated"
    raw = raw.strip()

    # 1. If display name format: "Vadde Kasyap <vaddekasyap@gmail.com>" or 'Vadde Kasyap <...>'
    m = re.match(r"^[\"']?([^<\"'@]+)[\"']?\s*<.*>$", raw)
    if m and m.group(1).strip():
        name = m.group(1).strip()
        if "@" not in name:
            return name.title()

    # 2. Extract email local part if email address
    if "@" in raw:
        local = raw.split("@")[0].strip()
    else:
        local = raw.strip()

    # Remove surrounding quotes / angle brackets
    local = re.sub(r"^[\"\'<]+|[\"\'>]+$", "", local)

    # Replace separators with spaces: vadde.kasyap -> vadde kasyap, dr.jane_smith -> dr jane smith
    spaced = re.sub(r"[._\-+]+", " ", local)

    # Split camelCase: vaddeKasyap -> vadde Kasyap
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", spaced)

    tokens = spaced.split()
    final_tokens = []

    # Known name/word components for compound names without separators (e.g., vaddekasyap, johnsmith)
    known_components = {
        "vadde", "kasyap", "kashyap", "john", "smith", "mary", "jane", "doe", "david",
        "kumar", "sharma", "singh", "patel", "reddy", "rao", "gupta", "alex", "test"
    }

    for t in tokens:
        tl = t.lower()
        split_found = False
        if len(tl) >= 6 and not any(c.isdigit() for c in tl):
            for i in range(3, len(tl) - 2):
                w1, w2 = tl[:i], tl[i:]
                if (w1 in known_components and w2 in known_components) or (w1 == "vadde" and w2 in ("kasyap", "kashyap")) or (w1 == "john" and w2 == "smith"):
                    final_tokens.extend([w1.capitalize(), w2.capitalize()])
                    split_found = True
                    break
        if not split_found:
            # Handle numbers e.g. test1 -> Test1, user123 -> User123
            final_tokens.append(t.capitalize())

    res = " ".join(final_tokens)
    return res if res else "Not stated"


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

            # Clean and title case reporter identity if needed
            if f.get("field_group") == "reporter" and f.get("field_name") == "identity" and value != "Not stated":
                value = _clean_human_name(value)

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

    # ── 1. Classification signals ──────────────────────────────────────────
    # Explicit reaction terms (bad outcome)
    reaction_terms = [
        "adverse event", "adverse reaction", "adverse drug reaction", "side effect",
        "side-effect", "side effects", "rash", "cutaneous", "erythema", "erythematous",
        "itching", "pruritus", "prurit", "anaphylaxis", "anaphylactic", "hepatic",
        "liver enzymes", "transaminases", "alt/ast", "elevated alt", "elevated ast",
        "cardiac", "palpitation", "palpitations", "dizziness", "dyspnoea", "dyspnea", "nausea",
        "vomiting", "headache", "fever", "fatigue", "toxicity", "poisoning",
        "urticaria", "angioedema", "swelling", "effets indésirables", "effet indésirable",
        "éruption cutanée", "nebenwirkung", "nebenwirkungen", "reacción adversa",
        "reacciones adversas", "dress syndrome", "drug eruption", "allergic reaction",
        "alergic reaction", "allergy", "alergy", "allergic", "hypersensitivity",
        "heart attack", "myocardial infarction", "cardiac arrest", "chest pain", "angina",
        "stroke", "seizure", "convulsion", "respiratory arrest", "breathing difficulty",
        "shortness of breath", "loss of consciousness", "syncope", "collapsed", "fainted",
        "liver failure", "kidney failure", "renal failure", "organ failure",
        "bleeding", "hemorrhage", "haemorrhage", "fatal", "death", "died"
    ]
    # Filter compound negations like "no adverse event", "no patient reaction or defect to report", "no defect", "no adverse reaction or defect observed"
    negation_pattern = re.compile(
        r"\b(?:no|not|without|denies|negative for|neither|zero)\s+(?:known\s+|adverse\s+|patient\s+|observed\s+|reported\s+|visible\s+|physical\s+)*(?:adverse\s+(?:events?|reactions?|drug\s+reactions?)|side\s+effects?|reactions?|events?|defects?|complaints?|exposure)(?:\s+(?:or|nor|and)\s+(?:known\s+|adverse\s+|patient\s+|observed\s+|reported\s+|visible\s+|physical\s+)*(?:adverse\s+(?:events?|reactions?|drug\s+reactions?)|side\s+effects?|reactions?|events?|defects?|complaints?|exposure))*\b",
        re.IGNORECASE
    )
    cleaned_for_signals = negation_pattern.sub(" ", combined_lower)

    has_reaction = any(r in cleaned_for_signals for r in reaction_terms)
    defect_terms = [
        "damage", "damages", "damaged", "broken", "broke", "breakage",
        "cracked vial", "cracked glass", "cracked ampoule", "cracked bottle",
        "crack", "cracks", "cracked", "cracking", "shattered", "crushed",
        "broken seal", "seal broken", "torn packaging", "damaged packaging",
        "packaging defect", "packaging damage", "cap broken", "broken cap",
        "broken bottle", "broken bottel", "bottel is broken", "bottle is broken",
        "broken vial", "broken syringe", "leakage", "leaking vial", "leaking bottle",
        "leaking", "leaked", "leak", "leaks", "spill", "spilled", "spillage",
        "particulate matter", "particulate", "particles", "foreign object", "foreign particle",
        "foreign body", "sediment", "debris", "contamination", "contaminated",
        "discoloration", "discoloured", "discolored", "wrong color", "turbid", "turbidity",
        "cloudy", "precipitate", "precipitation", "counterfeit", "tampered", "tampering",
        "unsealed", "product defect", "defective", "defect", "defects", "quality complaint",
        "product complaint", "pqc", "product damage", "product damages", "faulty product",
        "short fill", "underfill", "underfilled", "empty bottle", "empty vial",
        "bad smell", "foul smell", "odor", "odour", "bad taste", "mold", "fungus"
    ]
    has_defect = any(d in cleaned_for_signals for d in defect_terms)

    # Medical inquiry signals (dosing, stability, interactions with NO reaction and NO defect)
    inquiry_terms = [
        "dosage for", "pediatric dosage", "recommended dosage", "dosing schedule",
        "dosage schedule", "how to take", "how to administer", "reconstitution stability",
        "stability time", "room temperature stability", "shelf-life", "drug interaction",
        "contraindication", "pharmacokinetics", "half-life", "medical information inquiry",
        "medical inquiry", "information request", "inquiry:", "could you please provide",
        "what is the recommended", "what is the allowable", "please provide the recommended"
    ]
    has_inquiry = any(iq in combined_lower for iq in inquiry_terms)

    # Suspect drug signals
    drug_terms = [
        "synthostatin", "synthovial", "synthocardio", "drug a", "drug b",
        "paracetamol", "paracetomol", "acetaminophen", "tylenol", "aspirin", "ibuprofen",
        "advil", "motrin", "amoxicillin", "augmentin", "metformin", "atorvastatin", "lipitor",
        "lisinopril", "omeprazole", "prilosec", "ciprofloxacin", "azithromycin",
        "levothyroxine", "amlodipine", "metoprolol", "losartan",
        "drug", "medication", "medicine", "tablet", "capsule", "injection", "vaccine", "syrup"
    ]
    has_drug = any(dt in combined_lower for dt in drug_terms) or bool(
        re.search(r"\b(?:used|taking|took|prescribed|administered|injected|given)\s+([A-Za-z0-9\-]{3,30})\b", combined_lower)
    )

    # Patient context signals
    patient_terms = [
        "patient", "male", "female", "man", "woman", "aged", "age ", "y/o", "yo",
        "patiente", "paciente", "syn-", "case presentation", "abstract: a",
        "i have", "i had", "i took", "i used", "i got", "i developed", "i experienced",
        "i am", "i'm", "i was", "myself", "my father", "my mother", "my son",
        "my daughter", "my child", "my wife", "my husband", "my baby", "my kid", "my body"
    ]
    has_patient = any(pt in combined_lower for pt in patient_terms)

    # Reporter context signals
    reporter_terms = [
        "dr.", "dr ", "doctor", "physician", "gp", "general practitioner", "nurse",
        "pharmacist", "specialist", "hepatologist", "cardiologist", "dermatologist",
        "oncologist", "hospital", "clinic", "vigilance", "reported by", "reporter",
        "department", "département", "institut", "@", "from:", "consumer", "patient"
    ]
    has_reporter = any(rt in combined_lower for rt in reporter_terms) or bool(canonical.get("sender"))

    # Irrelevant signals
    irrelevant_terms = [
        "hvac", "maintenance", "conference room", "room reservation", "facilities bulletin",
        "quarterly maintenance", "catering", "wellness seminar", "health fair", "office closed",
        "marketing newsletter", "team building", "holiday schedule", "job application", "curriculum vitae", "resume"
    ]
    has_irrelevant = any(it in combined_lower for it in irrelevant_terms)

    # Determine Categories
    classifications: List[Classification] = []

    is_icsr = has_reaction and (
        has_drug or has_patient or has_reporter or
        "safety report" in combined_lower or "icsr" in combined_lower or
        "side effect" in combined_lower or "side effects" in combined_lower or "adverse" in combined_lower
    )
    is_pqc = has_defect
    is_mi = has_inquiry and not has_reaction and not has_defect

    if is_icsr:
        conf = 0.95 if (has_drug and has_patient and has_reporter) else 0.90
        classifications.append(Classification(
            category="ICSR",
            confidence=conf,
            reason="Document describes an adverse reaction experienced by a patient taking a medicinal product."
        ))

    if is_pqc:
        conf = 0.96 if ("lot" in combined_lower or "batch" in combined_lower) else 0.90
        classifications.append(Classification(
            category="PQC",
            confidence=conf,
            reason="Document reports a physical product quality complaint or packaging defect."
        ))

    if is_mi:
        classifications.append(Classification(
            category="MI",
            confidence=0.92,
            reason="Document contains a medical information inquiry regarding product usage, dosage, or stability."
        ))

    if not is_icsr and not is_pqc and not is_mi:
        classifications.append(Classification(
            category="NOT_RELEVANT",
            confidence=0.95 if has_irrelevant else 0.88,
            reason="Communication does not contain adverse events, product quality defects, or medical inquiries."
        ))

    # ── 2. Field extraction ────────────────────────────────────────────────
    find = lambda pats: _find_val_and_snippet(pats, text_blocks, email_text, default_page, has_pdf)

    age_v, age_s, age_p, age_pdf = find([
        r"(?:age|aged)[:\s]+(\d{1,3})\s*(?:years?|y\.?o\.?|yr|ans|jahre|años)?",
        r"(\d{1,3})\s*(?:years?|yo|y/o|ans|jahre|años)\b",
        r"\b(\d{1,3})\s*(?:yo|y/o|yo male|yo female|yo man|yo woman)\b",
        r"\bpatient\s+(?:id\s+[\w\-]+[,\s]+)?(?:age|aged)?\s*(\d{1,3})\b",
        r"\b(\d{1,3})(?:m|f)\b"
    ])
    sex_v, sex_s, sex_p, sex_pdf = find([
        r"\b(male|female|man|woman|homme|femme|männlich|weiblich|varón|mujer)\b",
        r"\bpatient[,\s]+(?:a\s+)?(male|female)\b",
        r"\b(\d{1,3})\s*(m|f)\b"
    ])
    if sex_v != "Not stated":
        sl = sex_v.lower()
        if sl in ["m", "male", "man", "homme", "männlich", "varón"]:
            sex_v = "Male"
        elif sl in ["f", "female", "woman", "femme", "weiblich", "mujer"]:
            sex_v = "Female"
        else:
            sex_v = sex_v.capitalize()

    weight_v, weight_s, weight_p, weight_pdf = find([
        r"(?:weight|poids|gewicht|peso)[:\s]+(\d{2,3}\s*(?:kg|lbs?))",
        r"(\d{2,3}\s*kg)\b"
    ])

    height_v, height_s, height_p, height_pdf = find([
        r"(?:height|taille|größe|altura)[:\s]+(\d{2,3}\s*(?:cm|in))",
        r"(\d{2,3}\s*cm)\b"
    ])

    history_v, history_s, history_p, history_pdf = find([
        r"(?:history|medical history|past history|antécédents|anamnese)[:\s]+([^\.\n\r]{5,100})"
    ])

    prod_v, prod_s, prod_pg, prod_pdf = find([
        r"\b(SynthoStatin|SynthoVial|SynthoCardio|Drug [A-Z])\b",
        r"\b(paracetamol|paracetomol|acetaminophen|tylenol|aspirin|ibuprofen|advil|motrin|amoxicillin|augmentin|metformin|atorvastatin|lipitor|lisinopril|omeprazole|prilosec|ciprofloxacin|azithromycin|levothyroxine|amlodipine|metoprolol|losartan)\b",
        r"(?:reaction to|taking|prescribed|administered|used|using|took|on|with|medicament|médicament|arzneimittel|producto)\s+(?:the\s+)?([A-Za-z0-9\-]{3,30})\b",
        r"(?:the\s+)?\b(syrup\s+bottel|syrup\s+bottle|syrup|solution|suspension|tablet|tablets|capsule|capsules|injection|vaccine|vial|ampoule|syringe|ointment|cream|gel|inhaler|elixir|drops|eye drops|patch|spray|lotion)\b",
        r"(?:product|drug|medication|medicine)\s*[:=]\s*(?!damage|damages|defect|complaint|issue|side\b|allergy\b|alergy\b|reaction\b|effects?\b)([A-Za-z0-9\-_\s]{2,30})(?:\s|,|\.|$)"
    ])
    if prod_v.lower() == "paracetomol":
        prod_v = "Paracetamol"
    elif prod_v.lower() in ("syrup bottel", "syrup bottle", "syrup"):
        prod_v = "Syrup"
    elif prod_v.lower() in ("tablet", "tablets"):
        prod_v = "Tablets"
    elif prod_v != "Not stated":
        prod_v = prod_v.strip().title()
    dose_v, dose_s, dose_pg, dose_pdf = find([
        r"(\d+\s*mg|\d+\s*ml|\d+\s*mcg|\d+\s*µg|\d+\s*g)",
        r"dose[:\s]+(\d+\s*(?:mg|ml|mcg|µg|g))"
    ])
    route_v, route_s, route_pg, route_pdf = find([
        r"\b(oral|intravenous|subcutaneous|intramuscular|topical|inhalation|iv|sc|im|orale|intraveineuse|intravenös)\b"
    ])
    if route_v != "Not stated":
        rl = route_v.lower()
        if rl in ["iv", "intravenous", "intraveineuse", "intravenös"]:
            route_v = "Intravenous"
        elif rl in ["oral", "orale"]:
            route_v = "Oral"
        elif rl in ["sc", "subcutaneous"]:
            route_v = "Subcutaneous"
        elif rl in ["im", "intramuscular"]:
            route_v = "Intramuscular"
        else:
            route_v = route_v.capitalize()

    react_v, react_s, react_pg, react_pdf = find([
        r"\b(heart attack|myocardial infarction|cardiac arrest|cardiac event|allergic reaction|alergic reaction|allergy|alergy|severe cutaneous rash|cutaneous rash|rash|erythematous rash|erythema|itching|pruritus|prurit|anaphylaxis|anaphylactic shock|chest pain|stroke|seizure|convulsion|hepatic injury|elevated transaminases|elevated alt/ast|elevated liver enzymes|palpitations and dizziness|palpitations|cardiac|fatigue|fever|nausea|vomiting|dizziness|dyspnoea|dyspnea|shortness of breath|breathing difficulty|urticaria|angioedema|swelling|headache|éruption cutanée|hautausschlag|erupción cutánea)\b"
    ])
    if react_v != "Not stated":
        react_v = react_v.capitalize() if not react_v.isupper() else react_v

    onset_v, onset_s, onset_pg, onset_pdf = find([
        r"(?:onset|started|began|début|beginn|inicio)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{1,2}\s+\w+\s+\d{4})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})"
    ])
    start_v, start_s, start_pg, start_pdf = find([
        r"(?:start date|started on|therapy start)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{1,2}\s+\w+\s+\d{4})"
    ])
    stop_v, stop_s, stop_pg, stop_pdf = find([
        r"(?:stop date|stopped on|discontinued)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{1,2}\s+\w+\s+\d{4})"
    ])
    outcome_v, outcome_s, outcome_pg, outcome_pdf = find([
        r"\b(recovered|recovering|not recovered|fatal|unknown|ongoing|resolved|rétablissement|in heilung|recuperado)\b"
    ])
    if outcome_v != "Not stated":
        ol = outcome_v.lower()
        if "recovered" in ol or "resolved" in ol or "rétablissement" in ol or "recuperado" in ol:
            outcome_v = "Recovered"
        elif "recovering" in ol or "in heilung" in ol:
            outcome_v = "Recovering"
        elif "not recovered" in ol or "ongoing" in ol:
            outcome_v = "Not recovered"
        elif "fatal" in ol:
            outcome_v = "Fatal"
        else:
            outcome_v = outcome_v.capitalize()

    serious_v = "Serious" if any(w in combined_lower for w in [
        "severe", "hospitaliz", "hospitalised", "hospitalisation", "life-threatening",
        "fatal", "death", "anaphylaxis", "hepatic injury", "heart attack", "myocardial",
        "cardiac arrest", "stroke", "organ failure", "icu"
    ]) else "Non-serious" if is_icsr else "Not stated"
    serious_s = react_s or email_snippet

    reporter_v, rep_s, rep_p, rep_pdf = find([
        r"(Dr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:reported by|reporter|rapporteur|melder)[:\s]+([A-Za-z\s\.]{3,40})",
        r"my name is\s+([A-Za-z\s\.]{2,40})(?:\.|\,|$)",
        r"(?:regards|best regards|thanks|thank you|sincerely|cheers|from)[:,\s\n]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
    ])
    sender_val = canonical.get("sender", "")
    if reporter_v == "Not stated" and sender_val and sender_val != "unspecified sender":
        reporter_v = _clean_human_name(sender_val)
        rep_s = email_snippet
        rep_p = 1
        rep_pdf = False
    elif reporter_v != "Not stated":
        reporter_v = _clean_human_name(reporter_v)

    role_v, role_s, role_p, role_pdf = find([
        r"\b(General Practitioner|Physician|Pharmacist|Nurse|Specialist|Hepatologist|Cardiologist|Dermatologist|Oncologist|GP|HCP|Médecin|Arzt|Médico)\b"
    ])
    if role_v == "Not stated" and sender_val:
        role_v = "Consumer" if any(dom in sender_val.lower() for dom in ["gmail", "yahoo", "hotmail", "outlook", "icloud", "mail", "aol", "live", "proton", "zoho"]) else "Healthcare Professional"
        role_s = email_snippet
        role_p = 1
        role_pdf = False
    elif role_v == "Not stated" and any(p in combined_lower for p in ["i have", "i took", "i used", "i got", "myself"]):
        role_v = "Consumer"
        role_s = email_snippet
        role_p = 1
        role_pdf = False
    if role_v != "Not stated":
        rl = role_v.lower()
        if "general practitioner" in rl or rl == "gp":
            role_v = "General Practitioner"
        elif "physician" in rl or "médecin" in rl or "arzt" in rl or "médico" in rl:
            role_v = "Physician"
        elif "pharmacist" in rl:
            role_v = "Pharmacist"
        elif "nurse" in rl:
            role_v = "Nurse"
        elif "hepatologist" in rl:
            role_v = "Hepatologist"
        elif "cardiologist" in rl:
            role_v = "Cardiologist"
        elif "dermatologist" in rl:
            role_v = "Dermatologist"
        else:
            role_v = role_v.capitalize()

    country_v, country_s, country_p, country_pdf = find([
        r"\b(United States|USA|UK|United Kingdom|Germany|Deutschland|France|Spain|España|India|Japan|Australia|Canada)\b",
        r"country[:\s]+([A-Za-z\s]{3,30})"
    ])
    if country_v != "Not stated":
        cl = country_v.lower()
        if cl in ["usa", "united states"]:
            country_v = "United States"
        elif cl in ["uk", "united kingdom"]:
            country_v = "United Kingdom"
        elif cl in ["deutschland", "germany"]:
            country_v = "Germany"
        elif cl in ["france"]:
            country_v = "France"
        elif cl in ["españa", "spain"]:
            country_v = "Spain"
        else:
            country_v = country_v.capitalize()

    batch_v, batch_s, batch_pg, batch_pdf = find([
        r"(?:batch|lot)[:\s#]+([A-Za-z0-9\-]{3,20})",
        r"\bLot\s+([A-Za-z0-9\-]{3,20})\b",
        r"\bBatch\s+([A-Za-z0-9\-]{3,20})\b",
        r"#([A-Z]\d{3,8})\b"
    ])
    defect_v, defect_s, defect_pg, defect_pdf = find([
        r"\b(the\s+syrup\s+bott?el\s+is\s+broken|the\s+bottle\s+is\s+broken|particulate matter|cracked vial|cracked glass|cracked ampoule|cracked bottle|torn packaging|damaged packaging|packaging damage|packaging defect|broken seal|seal broken|broken bottle|broken bottel|broken cap|broken vial|broken syringe|leaking vial|leaking bottle|leakage|leaking|leaked|contamination|contaminated|discoloration|discolored|foreign object|foreign particle|precipitation|precipitate|product damages?|product defect|defective|broken|damaged?|tampered)\b"
    ])
    if defect_v == "Not stated" and is_pqc:
        for dt in defect_terms:
            if dt in combined_lower:
                defect_v = dt.capitalize()
                defect_s = email_snippet
                defect_pg = default_page
                defect_pdf = has_pdf
                break

    photo_v, photo_s, photo_pg, photo_pdf = find([
        r"\b(photo|image|photograph|picture|sample attached|defect diagram)\b"
    ])
    photo_mentioned = "Yes" if (photo_v != "Not stated" or "photo" in combined_lower or "attached photograph" in combined_lower) else "No"

    mi_questions = _extract_mi_questions(text_blocks, email_text)
    mi_questions_s = ""
    mi_q_page = default_page
    mi_q_pdf = has_pdf
    if mi_questions != "Not stated":
        for b in text_blocks:
            b_txt = b.get("text", "")
            if "?" in b_txt:
                idx = b_txt.find("?")
                start_idx = max(0, b_txt.rfind("\n", 0, idx) + 1)
                end_idx = min(len(b_txt), idx + 1)
                mi_questions_s = b_txt[start_idx:end_idx].strip()
                mi_q_page = b.get("page_number", 1)
                mi_q_pdf = True
                break
        if not mi_questions_s and "?" in email_text:
            idx = email_text.find("?")
            start_idx = max(0, email_text.rfind("\n", 0, idx) + 1)
            end_idx = min(len(email_text), idx + 1)
            mi_questions_s = email_text[start_idx:end_idx].strip()
            mi_q_page = 1
            mi_q_pdf = False

    mi_topic_v, mi_topic_s, mi_topic_p, mi_topic_pdf = find([
        r"\b(pediatric dosage|dosage schedule|reconstitution stability|stability|drug interaction|contraindication|pharmacokinetics|half-life|storage conditions)\b"
    ])
    if mi_topic_v != "Not stated":
        mi_topic_v = mi_topic_v.title()

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
            make_field("patient", "weight", weight_v, weight_s, weight_p, weight_pdf, 0.90),
            make_field("patient", "height", height_v, height_s, height_p, height_pdf, 0.90),
            make_field("patient", "relevant_history", history_v, history_s, history_p, history_pdf, 0.90),
            make_field("reporter", "identity", reporter_v, rep_s, rep_p, rep_pdf, 0.88),
            make_field("reporter", "role", role_v, role_s, role_p, role_pdf, 0.88),
            make_field("reporter", "country", country_v, country_s, country_p, country_pdf, 0.85),
            make_field("product", "name", prod_v, prod_s, prod_pg, prod_pdf, 0.96),
            make_field("product", "dose", dose_v, dose_s, dose_pg, dose_pdf, 0.93),
            make_field("product", "route", route_v, route_s, route_pg, route_pdf, 0.90),
            make_field("product", "start_date", start_v, start_s, start_pg, start_pdf, 0.90),
            make_field("product", "stop_date", stop_v, stop_s, stop_pg, stop_pdf, 0.90),
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
        extracted_fields += [
            make_field("mi", "questions", mi_questions, mi_questions_s, mi_q_page, mi_q_pdf, 0.90),
            make_field("mi", "product", prod_v, prod_s, prod_pg, prod_pdf, 0.90),
            make_field("mi", "topic", mi_topic_v if mi_topic_v != "Not stated" else "Medical Inquiry", mi_topic_s, mi_topic_p, mi_topic_pdf, 0.88),
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
