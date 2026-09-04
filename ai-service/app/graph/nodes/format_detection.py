import time
import os
import fitz
from app.graph.state import GraphState

def format_detection_node(state: GraphState) -> GraphState:
    start_time = time.time()
    file_path = state.get("storage_reference", "")
    filename = (state.get("filename", "") or "").lower()

    if not os.path.exists(file_path):
        state["document_format"] = "DIGITAL"
        return state

    try:
        doc = fitz.open(file_path)
        total_text_len = 0
        total_images = 0
        page_count = len(doc)

        for page in doc:
            text = page.get_text()
            total_text_len += len(text.strip())
            total_images += len(page.get_images())

        doc.close()

        if "scanned" in filename or "handwritten" in filename:
            doc_format = "SCANNED"
        elif total_text_len > (page_count * 20):
            doc_format = "DIGITAL"
        elif total_images > 0:
            doc_format = "SCANNED"
        else:
            doc_format = "DIGITAL"

    except Exception:
        doc_format = "DIGITAL"

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["extraction_duration_ms"] = state["metrics"].get("extraction_duration_ms", 0) + duration_ms
    state["document_format"] = doc_format
    return state
