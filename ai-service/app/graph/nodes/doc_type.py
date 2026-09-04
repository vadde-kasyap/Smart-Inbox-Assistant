from app.graph.state import GraphState

def doc_type_node(state: GraphState) -> GraphState:
    text_blocks = state.get("canonical_context", {}).get("text_blocks", [])
    combined = " ".join([b.get("text", "") for b in text_blocks]).lower()
    filename = state.get("filename", "").lower()

    if "cioms" in combined or "medwatch" in combined or "form" in filename or "fiche" in combined or "declaration" in filename:
        doc_type = "FORM"
    elif "article" in filename or "journal" in combined or "abstract" in combined or "doi:" in combined or "references" in combined or "literature" in filename:
        doc_type = "ARTICLE"
    else:
        doc_type = "REPORT"

    state["document_type"] = doc_type
    return state
