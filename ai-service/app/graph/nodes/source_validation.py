import time
from app.graph.state import GraphState
from app.schemas.response import AIProcessResponse
from app.schemas.domain import ProcessingMetrics

def source_validation_node(state: GraphState) -> GraphState:
    start_time = time.time()
    errors = []

    fields = state.get("raw_extracted_fields", [])
    current_att_id = state.get("attachment_id")

    for f in fields:
        fname = f.get("field_name")
        sources = f.get("source_references", [])
        if not sources:
            errors.append(f"Field '{fname}' has no source reference.")
            continue

        for s in sources:
            stype = s.get("source_type")
            if stype not in ["PDF", "EMAIL"]:
                errors.append(f"Field '{fname}' has invalid source type: {stype}")
            if stype == "PDF":
                pg = s.get("page_number")
                if pg is None or pg < 1:
                    errors.append(f"Field '{fname}' has invalid page number: {pg}")
                att_id = s.get("attachment_id")
                if current_att_id is not None and att_id is not None and att_id != current_att_id:
                    errors.append(f"Field '{fname}' references mismatched attachment ID {att_id}")
            snippet = s.get("text_snippet")
            if not snippet or not snippet.strip():
                errors.append(f"Field '{fname}' is missing source text snippet.")

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["validation_duration_ms"] = state["metrics"].get("validation_duration_ms", 0) + duration_ms
    state["validation_errors"].extend(errors)

    # Compute total duration
    m = state["metrics"]
    total = (m.get("extraction_duration_ms", 0) +
             m.get("ocr_duration_ms", 0) +
             m.get("translation_duration_ms", 0) +
             m.get("llm_duration_ms", 0) +
             m.get("validation_duration_ms", 0))
    m["total_duration_ms"] = total

    validation_passed = (len(state["validation_errors"]) == 0)

    # Build final response
    final_resp = AIProcessResponse(
        job_id=state["job_id"],
        model_name="Qwen3-VL-2B-Instruct",
        model_version="v1.0",
        prompt_version="v1",
        summary=state.get("raw_summary", "No summary generated."),
        relevant=state.get("is_relevant", True),
        classifications=state.get("raw_classifications", []),
        extracted_fields=state.get("raw_extracted_fields", []),
        image_results=state.get("raw_image_results", []),
        metrics=ProcessingMetrics(**state["metrics"]),
        validation_passed=validation_passed
    )

    state["final_response"] = final_resp.model_dump(by_alias=True)
    return state
