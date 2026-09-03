import time
import os
from app.graph.state import GraphState
from app.extraction.digital import extract_digital_pdf
from app.extraction.tables import extract_tables_from_pdf

def digital_extraction_node(state: GraphState) -> GraphState:
    start_time = time.time()
    file_path = state["storage_reference"]

    if os.path.exists(file_path):
        is_digital, page_count, text_blocks = extract_digital_pdf(file_path)
        tables = extract_tables_from_pdf(file_path)
    else:
        text_blocks = []
        tables = []

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["extraction_duration_ms"] = state["metrics"].get("extraction_duration_ms", 0) + duration_ms

    # Store extracted elements in state for canonical builder
    state["canonical_context"] = {
        "text_blocks": [tb.model_dump() for tb in text_blocks],
        "tables": [t.model_dump() for t in tables],
        "images": []
    }
    return state
