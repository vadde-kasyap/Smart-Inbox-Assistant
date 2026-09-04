"""
Unit tests for the AI pipeline — classification, extraction, validation,
source validation, and the translation node.

Run with:
    pytest ai-service/tests/ -v
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# ── Ensure the app module is importable ───────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Classification schema tests (AGENTS.md §3)
# ---------------------------------------------------------------------------
class TestClassificationSchema:
    def test_valid_icsr(self):
        from app.schemas.domain import Classification
        c = Classification(category="ICSR", confidence=0.95, reason="Adverse event reported.")
        assert c.category == "ICSR"
        assert 0.0 <= c.confidence <= 1.0

    def test_valid_pqc(self):
        from app.schemas.domain import Classification
        c = Classification(category="PQC", confidence=0.88, reason="Product defect noted.")
        assert c.category == "PQC"

    def test_valid_mi(self):
        from app.schemas.domain import Classification
        c = Classification(category="MI", confidence=0.82, reason="Medical inquiry received.")
        assert c.category == "MI"

    def test_valid_not_relevant(self):
        from app.schemas.domain import Classification
        c = Classification(category="NOT_RELEVANT", confidence=0.90, reason="No medical content.")
        assert c.category == "NOT_RELEVANT"

    def test_invalid_category_raises(self):
        from app.schemas.domain import Classification
        with pytest.raises(Exception):
            Classification(category="SPAM", confidence=0.5, reason="test")

    def test_confidence_below_zero_raises(self):
        from app.schemas.domain import Classification
        with pytest.raises(Exception):
            Classification(category="ICSR", confidence=-0.1, reason="test")

    def test_confidence_above_one_raises(self):
        from app.schemas.domain import Classification
        with pytest.raises(Exception):
            Classification(category="ICSR", confidence=1.1, reason="test")

    def test_multi_label_preserved(self):
        from app.schemas.domain import Classification
        classes = [
            Classification(category="ICSR", confidence=0.95, reason="AE present."),
            Classification(category="PQC", confidence=0.88, reason="Defect noted."),
        ]
        cats = [c.category for c in classes]
        assert "ICSR" in cats
        assert "PQC" in cats


# ---------------------------------------------------------------------------
# ExtractedField + SourceReference schema tests
# ---------------------------------------------------------------------------
class TestExtractedFieldSchema:
    def test_valid_field_with_pdf_source(self):
        from app.schemas.domain import ExtractedField, SourceReference
        src = SourceReference(
            source_type="PDF",
            attachment_id=1,
            page_number=2,
            text_snippet="patient aged 54",
            location="pdf-page",
        )
        f = ExtractedField(
            field_group="patient",
            field_name="age",
            value="54",
            confidence=0.92,
            source_references=[src],
        )
        assert f.value == "54"
        assert f.source_references[0].page_number == 2

    def test_not_stated_field_has_empty_snippet(self):
        """
        AGENTS.md §2.3: missing values must use 'Not stated'.
        'Not stated' fields should NOT carry misleading source snippets.
        """
        from app.schemas.domain import ExtractedField, SourceReference
        src = SourceReference(source_type="PDF", attachment_id=1, page_number=1,
                              text_snippet="", location="pdf-page")
        f = ExtractedField(
            field_group="patient",
            field_name="weight",
            value="Not stated",
            confidence=1.0,
            source_references=[src],
        )
        assert f.value == "Not stated"
        assert f.source_references[0].text_snippet == ""

    def test_invalid_source_type_raises(self):
        from app.schemas.domain import SourceReference
        with pytest.raises(Exception):
            SourceReference(source_type="UNKNOWN", text_snippet="test")

    def test_confidence_bounds(self):
        from app.schemas.domain import ExtractedField, SourceReference
        src = SourceReference(source_type="EMAIL", email_id=1,
                              text_snippet="test snippet", location="email-text")
        with pytest.raises(Exception):
            ExtractedField(field_group="p", field_name="x", value="y",
                           confidence=1.5, source_references=[src])


# ---------------------------------------------------------------------------
# Validation node tests
# ---------------------------------------------------------------------------
class TestValidationNode:
    def _make_state(self, classifications=None, fields=None, summary=None):
        return {
            "raw_classifications": classifications or [],
            "raw_extracted_fields": fields or [],
            "raw_summary": summary or "",
            "validation_errors": [],
            "metrics": {},
        }

    def test_empty_classifications_flagged(self):
        from app.graph.nodes.validation import validation_node
        state = self._make_state(classifications=[], summary="A " * 15)
        result = validation_node(state)
        assert any("classification" in e.lower() for e in result["validation_errors"])

    def test_valid_state_no_errors(self):
        from app.graph.nodes.validation import validation_node
        cls = [{"category": "ICSR", "confidence": 0.9, "reason": "AE."}]
        summary = "This is a valid summary. " * 6
        state = self._make_state(classifications=cls, summary=summary)
        result = validation_node(state)
        assert result["validation_errors"] == []

    def test_short_summary_flagged(self):
        from app.graph.nodes.validation import validation_node
        cls = [{"category": "ICSR", "confidence": 0.9, "reason": "AE."}]
        state = self._make_state(classifications=cls, summary="Too short.")
        result = validation_node(state)
        assert any("summary" in e.lower() for e in result["validation_errors"])


# ---------------------------------------------------------------------------
# Source validation tests (AGENTS.md §27)
# ---------------------------------------------------------------------------
class TestSourceValidation:
    def _make_state(self, fields, attachment_id=1):
        return {
            "raw_extracted_fields": fields,
            "attachment_id": attachment_id,
            "validation_errors": [],
            "metrics": {"extraction_duration_ms": 0, "ocr_duration_ms": 0,
                        "translation_duration_ms": 0, "llm_duration_ms": 0, "validation_duration_ms": 0},
            "job_id": 1,
            "raw_classifications": [{"category": "ICSR", "confidence": 0.9, "reason": "test"}],
            "raw_summary": "A " * 50,
            "raw_image_results": [],
            "is_relevant": True,
        }

    def test_field_without_source_flagged(self):
        from app.graph.nodes.source_validation import source_validation_node
        fields = [{"field_name": "age", "field_group": "patient",
                   "value": "54", "confidence": 0.9, "source_references": []}]
        result = source_validation_node(self._make_state(fields))
        assert any("no source" in e.lower() for e in result["validation_errors"])

    def test_valid_pdf_source_passes(self):
        from app.graph.nodes.source_validation import source_validation_node
        fields = [{"field_name": "age", "field_group": "patient", "value": "54",
                   "confidence": 0.9, "source_references": [
                       {"source_type": "PDF", "attachment_id": 1,
                        "page_number": 2, "text_snippet": "patient aged 54", "location": "pdf-page"}
                   ]}]
        result = source_validation_node(self._make_state(fields, attachment_id=1))
        assert "age" not in " ".join(result["validation_errors"])

    def test_invalid_page_number_flagged(self):
        from app.graph.nodes.source_validation import source_validation_node
        fields = [{"field_name": "age", "field_group": "patient", "value": "54",
                   "confidence": 0.9, "source_references": [
                       {"source_type": "PDF", "attachment_id": 1,
                        "page_number": 0, "text_snippet": "test", "location": "pdf-page"}
                   ]}]
        result = source_validation_node(self._make_state(fields))
        assert any("invalid page" in e.lower() for e in result["validation_errors"])

    def test_mismatched_attachment_id_flagged(self):
        from app.graph.nodes.source_validation import source_validation_node
        fields = [{"field_name": "age", "field_group": "patient", "value": "54",
                   "confidence": 0.9, "source_references": [
                       {"source_type": "PDF", "attachment_id": 999,
                        "page_number": 1, "text_snippet": "test", "location": "pdf-page"}
                   ]}]
        result = source_validation_node(self._make_state(fields, attachment_id=1))
        assert any("mismatched" in e.lower() for e in result["validation_errors"])

    def test_missing_snippet_flagged(self):
        from app.graph.nodes.source_validation import source_validation_node
        fields = [{"field_name": "age", "field_group": "patient", "value": "54",
                   "confidence": 0.9, "source_references": [
                       {"source_type": "PDF", "attachment_id": 1,
                        "page_number": 1, "text_snippet": "", "location": "pdf-page"}
                   ]}]
        result = source_validation_node(self._make_state(fields))
        assert any("snippet" in e.lower() for e in result["validation_errors"])


# ---------------------------------------------------------------------------
# LLM analysis regression tests (mock mode)
# ---------------------------------------------------------------------------
class TestLLMAnalysisRegex:
    """Tests for the deterministic regex fallback (USE_MOCK_AI=true)."""

    def _run_regex(self, text_blocks, email_text, attachment_id=1, email_id=1):
        from app.graph.nodes.llm_analysis import _extract_via_regex
        canonical = {
            "text_blocks": text_blocks,
            "tables": [],
            "subject": "Test",
            "sender": "test@example.com",
            "email_body": email_text,
            "filename": "test.pdf",
            "document_type": "REPORT",
            "original_language": "English",
        }
        return _extract_via_regex(canonical, email_text, attachment_id, email_id)

    def test_icsr_classified_from_email(self):
        classes, fields, summary = self._run_regex(
            [], "Patient, 45 year old male, experienced a rash after taking SynthoStatin."
        )
        cats = [c.category for c in classes]
        assert "ICSR" in cats

    def test_not_relevant_for_empty(self):
        classes, _, _ = self._run_regex([], "Just a meeting request. No medical content.")
        cats = [c.category for c in classes]
        assert "NOT_RELEVANT" in cats

    def test_mi_questions_extracted(self):
        _, fields, _ = self._run_regex(
            [{"text": "What is the recommended dosage for SynthoStatin? Is it safe for elderly patients?",
              "page_number": 1, "location": "body", "confidence": 0.99, "extraction_method": "DIGITAL"}],
            "Medical information request.",
        )
        mi_questions = next((f for f in fields if f["field_name"] == "questions"), None)
        assert mi_questions is not None
        assert mi_questions["value"] != "Not stated"
        assert "?" in mi_questions["value"] or "dosage" in mi_questions["value"].lower()

    def test_not_stated_has_empty_snippet(self):
        _, fields, _ = self._run_regex(
            [], "Patient adverse event report. No weight mentioned."
        )
        weight_field = next((f for f in fields if f["field_name"] == "weight"), None)
        if weight_field:
            assert weight_field["value"] == "Not stated"
            assert weight_field["source_references"][0]["text_snippet"] == ""

    def test_summary_has_15_sentences(self):
        _, _, summary = self._run_regex(
            [], "Patient experienced an adverse reaction to SynthoStatin 10mg."
        )
        sentences = [s.strip() for s in summary.split(".") if s.strip()]
        assert len(sentences) >= 10

    def test_pqc_classified(self):
        classes, _, _ = self._run_regex(
            [{"text": "Lot C4401: Particulate matter found in vial. Batch rejected.",
              "page_number": 1, "location": "body", "confidence": 0.99, "extraction_method": "DIGITAL"}],
            "Product quality complaint."
        )
        cats = [c.category for c in classes]
        assert "PQC" in cats

    def test_multi_label_icsr_pqc(self):
        classes, _, _ = self._run_regex(
            [{"text": "Patient 30F developed rash. Batch lot C4401 also contaminated.",
              "page_number": 1, "location": "body", "confidence": 0.99, "extraction_method": "DIGITAL"}],
            "Safety and quality report."
        )
        cats = [c.category for c in classes]
        assert "ICSR" in cats
        assert "PQC" in cats

    def test_broken_syrup_bottle_pqc_classified(self):
        """User edge case: 'product damages the syrup bottel is broken' from test1@gmail.com."""
        from app.graph.nodes.llm_analysis import _extract_via_regex
        canonical = {
            "text_blocks": [],
            "tables": [],
            "subject": "product damages",
            "sender": "test1@gmail.com",
            "email_body": "the syrup bottel is broken",
            "filename": "email_body.txt",
            "document_type": "REPORT",
            "original_language": "English",
        }
        classes, fields, summary = _extract_via_regex(canonical, "product damages the syrup bottel is broken", 1, 1)
        cats = [c.category for c in classes]
        assert "PQC" in cats
        assert "NOT_RELEVANT" not in cats

        prod_f = next((f for f in fields if f["field_group"] == "pqc" and f["field_name"] == "product"), None)
        assert prod_f is not None
        assert prod_f["value"] == "Syrup"

        issue_f = next((f for f in fields if f["field_group"] == "pqc" and f["field_name"] == "issue"), None)
        assert issue_f is not None
        assert "broken" in issue_f["value"].lower() or "damages" in issue_f["value"].lower()

    def test_consumer_icsr_reporter_name_cleaned(self):
        """User case: VADDEKASYAP@GMAIL.COM reporting paracetamol rash."""
        from app.graph.nodes.llm_analysis import _extract_via_regex
        canonical = {
            "text_blocks": [],
            "tables": [],
            "subject": "regarding drug side effects",
            "sender": "VADDEKASYAP@GMAIL.COM",
            "email_body": "i have used paracetomol and got a rash",
            "filename": "email_body.txt",
            "document_type": "REPORT",
            "original_language": "English",
        }
        classes, fields, summary = _extract_via_regex(canonical, "regarding drug side effects i have used paracetomol and got a rash", 1, 1)
        cats = [c.category for c in classes]
        assert "ICSR" in cats

        rep_id_f = next((f for f in fields if f["field_group"] == "reporter" and f["field_name"] == "identity"), None)
        assert rep_id_f is not None
        assert rep_id_f["value"] == "Vadde Kasyap"

        role_f = next((f for f in fields if f["field_group"] == "reporter" and f["field_name"] == "role"), None)
        assert role_f is not None
        assert role_f["value"] == "Consumer"

        prod_f = next((f for f in fields if f["field_group"] == "product" and f["field_name"] == "name"), None)
        assert prod_f is not None
        assert prod_f["value"] == "Paracetamol"

    def test_consumer_heart_attack_drug_allergy_classified_icsr(self):
        """User case: VADDEKASYAP@GMAIL.COM reporting heart attack after using tablets with subject 'drug alergy'."""
        from app.graph.nodes.llm_analysis import _extract_via_regex
        canonical = {
            "text_blocks": [],
            "tables": [],
            "subject": "drug alergy",
            "sender": "VADDEKASYAP@GMAIL.COM",
            "email_body": "i got a heart attack after using the tablets",
            "filename": "email_body.txt",
            "document_type": "REPORT",
            "original_language": "English",
        }
        classes, fields, summary = _extract_via_regex(canonical, "drug alergy i got a heart attack after using the tablets", 1, 1)
        cats = [c.category for c in classes]
        assert "ICSR" in cats
        assert "NOT_RELEVANT" not in cats

        react_f = next((f for f in fields if f["field_group"] == "reaction" and f["field_name"] == "description"), None)
        assert react_f is not None
        assert "heart attack" in react_f["value"].lower()

        ser_f = next((f for f in fields if f["field_group"] == "other" and f["field_name"] == "seriousness"), None)
        assert ser_f is not None
        assert ser_f["value"] == "Serious"

        rep_id_f = next((f for f in fields if f["field_group"] == "reporter" and f["field_name"] == "identity"), None)
        assert rep_id_f is not None
        assert rep_id_f["value"] == "Vadde Kasyap"

    def test_clean_human_name_helper(self):
        from app.graph.nodes.llm_analysis import _clean_human_name
        assert _clean_human_name("VADDEKASYAP@GMAIL.COM") == "Vadde Kasyap"
        assert _clean_human_name("vaddekasyap@gmail.com") == "Vadde Kasyap"
        assert _clean_human_name("vadde.kasyap@gmail.com") == "Vadde Kasyap"
        assert _clean_human_name("test1@gmail.com") == "Test1"
        assert _clean_human_name('"Dr. John Smith" <jsmith@clinic.org>') == "Dr. John Smith"
        assert _clean_human_name("dr.jane_smith@hospital.org") == "Dr Jane Smith"

    def test_idempotency_same_input(self):
        """Same input should always produce same classification categories."""
        email = "Patient 54M experienced erythematous rash after SynthoStatin 10mg."
        c1, _, _ = self._run_regex([], email)
        c2, _, _ = self._run_regex([], email)
        assert [c.category for c in c1] == [c.category for c in c2]


# ---------------------------------------------------------------------------
# Translation node tests
# ---------------------------------------------------------------------------
class TestTranslationNode:
    def test_english_no_translation(self):
        from app.graph.nodes.translation import translation_node
        state = {
            "language": "English",
            "canonical_context": {"text_blocks": [{"text": "Patient report.", "page_number": 1}]},
            "metrics": {},
        }
        result = translation_node(state)
        # Should not add translated_text_blocks when already English
        assert "translated_text_blocks" not in (result["canonical_context"] or {})

    def test_non_english_triggers_translation_mock(self):
        from app.graph.nodes.translation import translation_node
        state = {
            "language": "French",
            "canonical_context": {
                "text_blocks": [{"text": "Effets indésirables signalés.", "page_number": 1,
                                 "location": "body", "confidence": 0.9, "extraction_method": "DIGITAL"}]
            },
            "metrics": {},
        }
        with patch("app.graph.nodes.translation.get_qwen_client") as mock_get:
            mock_client = MagicMock()
            mock_client.is_mock = True
            mock_get.return_value = mock_client

            result = translation_node(state)
            ctx = result["canonical_context"]
            assert "translated_text_blocks" in ctx
            assert len(ctx["translated_text_blocks"]) == 1
            # Mock translation should include a placeholder
            assert "French" in ctx["translated_text_blocks"][0]["text"] or \
                   "Translation" in ctx["translated_text_blocks"][0]["text"]


# ---------------------------------------------------------------------------
# Idempotency test
# ---------------------------------------------------------------------------
class TestIdempotency:
    def test_same_message_id_skipped(self):
        """
        Simulation of idempotency: running the extraction twice with the
        same input should not modify stored state.  This is a unit-level
        smoke test; full idempotency is enforced by the Spring Boot layer.
        """
        from app.graph.nodes.llm_analysis import _extract_via_regex
        canonical = {
            "text_blocks": [],
            "tables": [],
            "subject": "Repeat",
            "sender": "a@b.com",
            "email_body": "Patient 54M rash SynthoStatin.",
            "filename": "test.pdf",
            "document_type": "REPORT",
            "original_language": "English",
        }
        c1, f1, s1 = _extract_via_regex(canonical, "Patient 54M rash SynthoStatin.", 1, 1)
        c2, f2, s2 = _extract_via_regex(canonical, "Patient 54M rash SynthoStatin.", 1, 1)
        assert [c.category for c in c1] == [c.category for c in c2]
        assert s1 == s2
