from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes.format_detection import format_detection_node
from app.graph.nodes.digital_extraction import digital_extraction_node
from app.graph.nodes.ocr_vision import ocr_vision_node
from app.graph.nodes.language_detection import language_detection_node
from app.graph.nodes.translation import translation_node
from app.graph.nodes.doc_type import doc_type_node
from app.graph.nodes.article_processing import article_processing_node
from app.graph.nodes.canonical import canonical_node
from app.graph.nodes.llm_analysis import llm_analysis_node
from app.graph.nodes.validation import validation_node
from app.graph.nodes.source_validation import source_validation_node
from app.schemas.request import AIProcessRequest
from app.schemas.response import AIProcessResponse


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("format_detection", format_detection_node)
    workflow.add_node("digital_extraction", digital_extraction_node)
    workflow.add_node("ocr_vision", ocr_vision_node)
    workflow.add_node("language_detection", language_detection_node)
    workflow.add_node("translation", translation_node)      # NEW: translate non-English docs
    workflow.add_node("doc_type", doc_type_node)
    workflow.add_node("article_processing", article_processing_node)
    workflow.add_node("canonical", canonical_node)
    workflow.add_node("llm_analysis", llm_analysis_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("source_validation", source_validation_node)

    # Pipeline edges
    # format_detection ──► digital_extraction ──► ocr_vision
    #   ──► language_detection ──► translation ──► doc_type
    #   ──► article_processing ──► canonical ──► llm_analysis
    #   ──► validation ──► source_validation ──► END
    workflow.set_entry_point("format_detection")
    workflow.add_edge("format_detection", "digital_extraction")
    workflow.add_edge("digital_extraction", "ocr_vision")
    workflow.add_edge("ocr_vision", "language_detection")
    workflow.add_edge("language_detection", "translation")    # NEW edge
    workflow.add_edge("translation", "doc_type")
    workflow.add_edge("doc_type", "article_processing")
    workflow.add_edge("article_processing", "canonical")
    workflow.add_edge("canonical", "llm_analysis")
    workflow.add_edge("llm_analysis", "validation")
    workflow.add_edge("validation", "source_validation")
    workflow.add_edge("source_validation", END)

    return workflow.compile()


graph_app = build_graph()


def execute_pipeline(req: AIProcessRequest) -> dict:
    email_dict = req.email.model_dump() if req.email else {}
    doc_dict = req.document.model_dump()

    initial_state: GraphState = {
        "job_id": req.job_id,
        "email_id": req.email.email_id if req.email else None,
        "attachment_id": req.document.attachment_id,
        "filename": req.document.filename,
        "storage_reference": req.document.storage_reference,
        "email_data": email_dict,
        "document_format": "DIGITAL",
        "document_type": "REPORT",
        "language": "English",
        "translated": False,
        "translated_text": None,
        "canonical_context": None,
        "raw_classifications": [],
        "raw_extracted_fields": [],
        "raw_image_results": [],
        "raw_summary": "",
        "is_relevant": True,
        "validation_errors": [],
        "retry_count": 0,
        "metrics": {
            "total_duration_ms": 0,
            "extraction_duration_ms": 0,
            "ocr_duration_ms": 0,
            "translation_duration_ms": 0,
            "llm_duration_ms": 0,
            "validation_duration_ms": 0,
        },
        "final_response": None,
    }

    final_state = graph_app.invoke(initial_state)
    return final_state.get("final_response")
