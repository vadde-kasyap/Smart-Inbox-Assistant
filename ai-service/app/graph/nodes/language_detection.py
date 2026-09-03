import time
from app.graph.state import GraphState

FRENCH_MARKERS = ["patient", "effets indésirables", "médicament", "signalement", "réaction"]
GERMAN_MARKERS = ["patient", "nebenwirkung", "arzneimittel", "meldung", "reaktion"]
SPANISH_MARKERS = ["paciente", "efectos adversos", "medicamento", "notificación", "reacción"]

def language_detection_node(state: GraphState) -> GraphState:
    start_time = time.time()
    
    # Analyze text blocks
    text_blocks = state.get("canonical_context", {}).get("text_blocks", [])
    combined_text = " ".join([b.get("text", "") for b in text_blocks]).lower()
    
    detected = "English"
    if any(m in combined_text for m in FRENCH_MARKERS):
        if "effets indésirables" in combined_text or "signalement" in combined_text:
            detected = "French"
    elif any(m in combined_text for m in GERMAN_MARKERS):
        if "nebenwirkung" in combined_text or "arzneimittel" in combined_text:
            detected = "German"
    elif any(m in combined_text for m in SPANISH_MARKERS):
        if "efectos adversos" in combined_text or "notificación" in combined_text:
            detected = "Spanish"

    state["language"] = detected
    state["translated"] = (detected != "English")

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["translation_duration_ms"] = state["metrics"].get("translation_duration_ms", 0) + duration_ms
    return state
