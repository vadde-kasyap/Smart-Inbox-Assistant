import time
from app.graph.state import GraphState
from app.schemas.domain import Classification, ExtractedField

def validation_node(state: GraphState) -> GraphState:
    start_time = time.time()
    errors = []

    # 1. Validate classifications
    raw_classes = state.get("raw_classifications", [])
    if not raw_classes:
        errors.append("At least one classification is required.")
    for c in raw_classes:
        try:
            Classification(**c)
        except Exception as e:
            errors.append(f"Invalid classification {c}: {e}")

    # 2. Validate extracted fields
    raw_fields = state.get("raw_extracted_fields", [])
    for f in raw_fields:
        try:
            ExtractedField(**f)
        except Exception as e:
            errors.append(f"Invalid extracted field {f}: {e}")

    # 3. Validate summary
    summary = state.get("raw_summary", "")
    if not summary or len(summary.split()) < 10:
        errors.append("Narrative summary is too short or missing.")

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["validation_duration_ms"] = state["metrics"].get("validation_duration_ms", 0) + duration_ms
    state["validation_errors"].extend(errors)

    return state
