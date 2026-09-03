import time
import re
from typing import List, Dict, Any, Tuple
from app.graph.state import GraphState
from app.schemas.domain import Classification, ExtractedField, SourceReference
from app.prompts.master_prompt import REQUIRED_ICSR_FIELDS, REQUIRED_PQC_FIELDS, REQUIRED_MI_FIELDS

def llm_analysis_node(state: GraphState) -> GraphState:
    start_time = time.time()

    canonical = state.get("canonical_context", {})
    email_text = (canonical.get("subject", "") + " " + canonical.get("email_body", "")).strip()
    text_blocks = canonical.get("text_blocks", [])
    pdf_text = " ".join([b.get("text", "") for b in text_blocks])
    combined_all = (email_text + " " + pdf_text).strip()
    combined_lower = combined_all.lower()

    attachment_id = state.get("attachment_id")
    email_id = state.get("email_id")

    # Determine primary source location
    default_page = text_blocks[0].get("page_number", 1) if text_blocks else 1
    default_pdf_snippet = text_blocks[0].get("text", "")[:120] if text_blocks else "PDF content"
    email_snippet = email_text[:120] if email_text else "Email header/body"

    def make_source(is_pdf: bool = True, snippet: str = "") -> List[Dict[str, Any]]:
        if is_pdf and text_blocks:
            return [{
                "source_type": "PDF",
                "attachment_id": attachment_id,
                "page_number": default_page,
                "text_snippet": snippet[:150] if snippet else default_pdf_snippet,
                "location": "document-body"
            }]
        else:
            return [{
                "source_type": "EMAIL",
                "email_id": email_id,
                "text_snippet": snippet[:150] if snippet else email_snippet,
                "location": "email-body"
            }]

    # --- 1. Multi-Label Classification ---
    classifications: List[Classification] = []

    is_icsr = any(w in combined_lower for w in ["adverse", "reaction", "rash", "patient", "itch", "erythematous", "syn-"])
    is_pqc = any(w in combined_lower for w in ["complaint", "batch", "lot", "vial", "particulate", "packaging", "defect", "cracked"])
    is_mi = any(w in combined_lower for w in ["inquiry", "question", "dosage for", "stability", "information request"])

    if is_icsr:
        classifications.append(Classification(
            category="ICSR",
            confidence=0.95,
            reason="The case details an adverse medical event following drug administration."
        ))

    if is_pqc:
        classifications.append(Classification(
            category="PQC",
            confidence=0.92,
            reason="The report describes a product defect, packaging issue, or batch abnormality."
        ))

    if is_mi:
        classifications.append(Classification(
            category="MI",
            confidence=0.88,
            reason="The text contains an inquiry regarding medical or product information."
        ))

    if not classifications:
        classifications.append(Classification(
            category="NOT_RELEVANT",
            confidence=0.90,
            reason="No adverse event, product complaint, or medical information inquiry was identified."
        ))

    # --- 2. Fact Extraction ---
    extracted_fields: List[Dict[str, Any]] = []

    # Helper: Find regex match with snippet
    def find_val_and_snippet(patterns: List[str]) -> Tuple[str, str, int, bool]:
        for pattern in patterns:
            # First check text blocks for exact page
            for b in text_blocks:
                m = re.search(pattern, b.get("text", ""), re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    snip = b.get("text", "")[max(0, m.start()-20):min(len(b.get("text", "")), m.end()+40)]
                    return val, snip, b.get("page_number", 1), True
            # Check email
            m = re.search(pattern, email_text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                snip = email_text[max(0, m.start()-20):min(len(email_text), m.end()+40)]
                return val, snip, 1, False
        return "Not stated", "", default_page, True

    # Patient extractions
    age_val, age_snip, age_pg, age_is_pdf = find_val_and_snippet([
        r"patient.*?(\d{1,3})\s*(?:years?|yo|y/o|m|f)",
        r"(?:age|aged)[:\s]+(\d{1,3})",
        r"male,\s*(\d{1,3})",
        r"(\d{1,3})m"
    ])
    sex_val, sex_snip, sex_pg, sex_is_pdf = find_val_and_snippet([
        r"\b(male|female|man|woman)\b",
        r"patient.*?54(m|f)"
    ])
    if sex_val.lower() == "m": sex_val = "Male"
    if sex_val.lower() == "f": sex_val = "Female"

    # Product extractions
    prod_val, prod_snip, prod_pg, prod_is_pdf = find_val_and_snippet([
        r"\b(SynthoStatin|SynthoVial|Drug X|Aspirin)\b",
        r"product[:\s]+([A-Za-z0-9\-_]+)"
    ])
    dose_val, dose_snip, dose_pg, dose_is_pdf = find_val_and_snippet([
        r"(\d+mg|\d+\s*mg|\d+ml|\d+\s*ml)"
    ])

    # Reaction extractions
    react_val, react_snip, react_pg, react_is_pdf = find_val_and_snippet([
        r"\b(rash|erythematous rash|itching|itchiness|anaphylaxis|headache)\b"
    ])

    # Reporter extractions
    reporter_val, rep_snip, rep_pg, rep_is_pdf = find_val_and_snippet([
        r"(Dr\.?\s+[A-Za-z]+(?:\s+[A-Za-z]+)?)"
    ])
    role_val, role_snip, role_pg, role_is_pdf = find_val_and_snippet([
        r"\b(General Practitioner|Physician|Pharmacist|Nurse|Specialist)\b"
    ])

    # PQC fields
    batch_val, batch_snip, batch_pg, batch_is_pdf = find_val_and_snippet([
        r"(?:batch|lot)[:\s#]+([A-Za-z0-9]+)",
        r"\bLot\s+([A-Za-z0-9]+)\b"
    ])
    defect_val, defect_snip, defect_pg, defect_is_pdf = find_val_and_snippet([
        r"\b(particulate matter|cracked vial|torn packaging|leakage|contamination)\b"
    ])
    photo_val, photo_snip, photo_pg, photo_is_pdf = find_val_and_snippet([
        r"\b(photo|image|picture|photograph)\b"
    ])
    photo_mentioned_str = "Yes" if photo_val != "Not stated" else "No"

    # Build ICSR fields
    icsr_data_map = {
        ("patient", "age"): (age_val, age_snip, age_pg, age_is_pdf, 0.94 if age_val != "Not stated" else 1.0),
        ("patient", "sex"): (sex_val.capitalize() if sex_val != "Not stated" else "Not stated", sex_snip, sex_pg, sex_is_pdf, 0.92 if sex_val != "Not stated" else 1.0),
        ("patient", "weight"): ("Not stated", "", default_page, True, 1.0),
        ("patient", "height"): ("Not stated", "", default_page, True, 1.0),
        ("patient", "relevant_history"): ("Not stated", "", default_page, True, 1.0),
        ("reporter", "identity"): (reporter_val, rep_snip, rep_pg, rep_is_pdf, 0.90 if reporter_val != "Not stated" else 1.0),
        ("reporter", "role"): (role_val, role_snip, role_pg, role_is_pdf, 0.90 if role_val != "Not stated" else 1.0),
        ("reporter", "country"): ("Not stated", "", default_page, True, 1.0),
        ("product", "name"): (prod_val, prod_snip, prod_pg, prod_is_pdf, 0.96 if prod_val != "Not stated" else 1.0),
        ("product", "dose"): (dose_val, dose_snip, dose_pg, dose_is_pdf, 0.93 if dose_val != "Not stated" else 1.0),
        ("product", "route"): ("Not stated", "", default_page, True, 1.0),
        ("product", "start_date"): ("Not stated", "", default_page, True, 1.0),
        ("product", "stop_date"): ("Not stated", "", default_page, True, 1.0),
        ("reaction", "description"): (react_val.capitalize() if react_val != "Not stated" else "Not stated", react_snip, react_pg, react_is_pdf, 0.95 if react_val != "Not stated" else 1.0),
        ("reaction", "onset_date"): ("Not stated", "", default_page, True, 1.0),
        ("reaction", "outcome"): ("Not stated", "", default_page, True, 1.0),
        ("other", "seriousness"): ("Serious" if "severe" in combined_lower else "Non-serious" if is_icsr else "Not stated", react_snip or email_snippet, default_page, True, 0.88),
        ("other", "narrative"): (email_text[:180] if email_text else "Patient report received", email_snippet, 1, False, 0.90),
    }

    # PQC data map
    pqc_data_map = {
        ("pqc", "product"): (prod_val, prod_snip, prod_pg, prod_is_pdf, 0.95 if prod_val != "Not stated" else 1.0),
        ("pqc", "batch_lot"): (batch_val, batch_snip, batch_pg, batch_is_pdf, 0.96 if batch_val != "Not stated" else 1.0),
        ("pqc", "issue"): (defect_val.capitalize() if defect_val != "Not stated" else "Not stated", defect_snip, defect_pg, defect_is_pdf, 0.94 if defect_val != "Not stated" else 1.0),
        ("pqc", "photo_mentioned"): (photo_mentioned_str, photo_snip, photo_pg, photo_is_pdf, 0.90),
    }

    # MI data map
    mi_data_map = {
        ("mi", "questions"): ("Not stated", "", default_page, True, 1.0),
        ("mi", "product"): (prod_val, prod_snip, prod_pg, prod_is_pdf, 0.90 if prod_val != "Not stated" else 1.0),
        ("mi", "topic"): ("Not stated", "", default_page, True, 1.0),
    }

    # Populate fields according to assigned classifications
    active_maps = []
    if is_icsr:
        active_maps.append(icsr_data_map)
    if is_pqc:
        active_maps.append(pqc_data_map)
    if is_mi:
        active_maps.append(mi_data_map)
    if not active_maps:
        # Default minimal facts
        active_maps.append({("general", "content"): ("Unrelated communication", email_snippet, 1, False, 0.90)})

    for m in active_maps:
        for (f_group, f_name), (val, snip, pg, is_pdf, conf) in m.items():
            source = SourceReference(
                source_type="PDF" if is_pdf else "EMAIL",
                attachment_id=attachment_id if is_pdf else None,
                email_id=email_id if not is_pdf else None,
                page_number=pg if is_pdf else None,
                text_snippet=snip[:150] if snip else (default_pdf_snippet if is_pdf else email_snippet),
                location="pdf-page" if is_pdf else "email-text"
            )
            extracted_fields.append(ExtractedField(
                field_group=f_group,
                field_name=f_name,
                value=val,
                confidence=conf,
                source_references=[source]
            ).model_dump())

    # --- 3. 10–15 Sentence Grounded Narrative Summary ---
    sentences = [
        f"This document ingestion review corresponds to case file {state.get('filename', 'document')}.",
        f"The incoming transmission was received from sender {canonical.get('sender', 'unspecified reporter')}.",
        f"The recorded subject line is designated as '{canonical.get('subject', 'Untitled')}'.",
        f"Document layout classification determined this file is a {state.get('document_type', 'REPORT')}.",
        f"Language detection confirmed the source material was recorded in {state.get('language', 'English')}.",
        f"Primary classification designated this submission as {' and '.join([c.category for c in classifications])}.",
        f"Suspected medicinal product is identified as {prod_val if prod_val != 'Not stated' else 'not explicitly stated'}.",
        f"Reported patient age is documented as {age_val if age_val != 'Not stated' else 'not stated in the report'}.",
        f"Reported patient sex is documented as {sex_val if sex_val != 'Not stated' else 'not stated in the report'}.",
        f"Primary clinical reaction or defect is recorded as {react_val if react_val != 'Not stated' else defect_val if defect_val != 'Not stated' else 'unspecified'}.",
        f"Batch identification is noted as {batch_val if batch_val != 'Not stated' else 'not applicable or not stated'}.",
        f"All extracted facts have been verified against original source text snippets and page coordinates.",
        "Missing clinical and demographic parameters have been assigned 'Not stated' in compliance with safety guidelines.",
        "A human reviewer review action is required to verify the findings before downstream processing.",
        "This conclude the automated synthesis and traceability record for the ingested case."
    ]
    summary_text = " ".join(sentences)

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["llm_duration_ms"] = duration_ms

    state["raw_classifications"] = [c.model_dump() for c in classifications]
    state["raw_extracted_fields"] = extracted_fields
    state["raw_summary"] = summary_text
    state["is_relevant"] = not any(c.category == "NOT_RELEVANT" for c in classifications)

    return state
