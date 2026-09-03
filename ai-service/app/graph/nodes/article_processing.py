from app.graph.state import GraphState

def article_processing_node(state: GraphState) -> GraphState:
    if state.get("document_type") != "ARTICLE":
        return state

    text_blocks = state.get("canonical_context", {}).get("text_blocks", [])
    filtered_blocks = []
    in_references = False

    for b in text_blocks:
        text = b.get("text", "")
        clean_lower = text.lower().strip()

        if clean_lower in ["references", "bibliography", "references:", "literature cited"]:
            in_references = True
            continue

        if not in_references:
            filtered_blocks.append(b)

    state["canonical_context"]["text_blocks"] = filtered_blocks
    return state
