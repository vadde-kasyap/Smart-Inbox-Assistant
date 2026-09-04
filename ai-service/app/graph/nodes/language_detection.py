import time
from app.graph.state import GraphState

FRENCH_MARKERS = ["effets indésirables", "effet indésirable", "médicament", "signalement", "éruption cutanée", "pharmacovigilance", "cher département", "patiente"]
GERMAN_MARKERS = ["nebenwirkung", "nebenwirkungen", "arzneimittel", "meldung", "hautausschlag", "unerwünschte", "patientenbericht", "sehr geehrte"]
SPANISH_MARKERS = ["efectos adversos", "reacción adversa", "medicamento", "notificación", "erupción cutánea", "farmacovigilancia", "estimado"]

def language_detection_node(state: GraphState) -> GraphState:
    start_time = time.time()
    
    text_blocks = state.get("canonical_context", {}).get("text_blocks", [])
    email_data = state.get("email_data", {}) or {}
    email_text = (email_data.get("subject", "") or "") + " " + (email_data.get("body", "") or "")
    combined_text = (" ".join([b.get("text", "") for b in text_blocks]) + " " + email_text + " " + state.get("filename", "")).lower()
    
    detected = "English"
    if any(m in combined_text for m in FRENCH_MARKERS):
        detected = "French"
    elif any(m in combined_text for m in GERMAN_MARKERS):
        detected = "German"
    elif any(m in combined_text for m in SPANISH_MARKERS):
        detected = "Spanish"

    state["language"] = detected
    state["translated"] = (detected != "English")

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["translation_duration_ms"] = state["metrics"].get("translation_duration_ms", 0) + duration_ms
    return state
