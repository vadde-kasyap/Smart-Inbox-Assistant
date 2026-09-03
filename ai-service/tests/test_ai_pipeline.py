import os
import pytest
from app.schemas.request import AIProcessRequest, EmailContext, DocumentContext
from app.graph.pipeline import execute_pipeline

def test_pipeline_with_synthetic_pdf():
    # Use existing test synthetic PDF
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_pdf_path = os.path.join(base_dir, "..", "test-data", "pdfs", "case_report_syntho.pdf")
    test_pdf_path = os.path.abspath(test_pdf_path)

    request = AIProcessRequest(
        jobId=101,
        email=EmailContext(
            emailId=1,
            sender="safety@hospital.org",
            subject="Adverse Event Notice - SynthoStatin",
            body="Patient 54M developed rash following 20mg SynthoStatin."
        ),
        document=DocumentContext(
            attachmentId=25,
            filename="case_report_syntho.pdf",
            storageReference=test_pdf_path
        )
    )

    result = execute_pipeline(request)

    assert result is not None
    assert result["jobId"] == 101
    assert result["validationPassed"] is True
    assert len(result["classifications"]) > 0
    assert any(c["category"] == "ICSR" for c in result["classifications"])
    assert len(result["extractedFields"]) > 0

    # Verify source traceability
    for field in result["extractedFields"]:
        assert len(field["sourceReferences"]) > 0
        src = field["sourceReferences"][0]
        assert src["sourceType"] in ["PDF", "EMAIL"]
        if src["sourceType"] == "PDF":
            assert src["pageNumber"] >= 1
            assert src["attachmentId"] == 25
        assert len(src["textSnippet"]) > 0

    # Verify metrics
    metrics = result["metrics"]
    assert metrics["totalDurationMs"] >= 0
    assert len(result["summary"].split()) >= 10
