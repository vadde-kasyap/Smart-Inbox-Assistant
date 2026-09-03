from app.graph.state import GraphState

def doc_type_node(state: GraphState) -> GraphState:
    text_blocks = state.get("canonical_context", {}).get("text_blocks", [])
    combined = " ".join([b.get("text", "") for b in text_blocks]).lower()
    filename = state.get("filename", "").lower()

    if "cioms" in combined or "medwatch" in combined or "form" in filename:
        doc_type = "FORM"
    elif "abstract" in combined or "references" in combined or "journal" in combined or "doi:" in combined:
        doc_type = "ARTICLE"
    else:
        doc_type = "REPORT"

    state["document_type"] = doc_type
    return state
