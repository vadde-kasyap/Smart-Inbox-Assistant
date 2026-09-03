from app.graph.state import GraphState
from app.schemas.canonical import CanonicalCaseContext, TextBlock, TableData, ImageEvidence

def canonical_node(state: GraphState) -> GraphState:
    email_data = state.get("email_data", {})
    raw_ctx = state.get("canonical_context", {})

    context = CanonicalCaseContext(
        email_id=state.get("email_id"),
        sender=email_data.get("sender"),
        subject=email_data.get("subject"),
        email_body=email_data.get("body"),
        attachment_id=state.get("attachment_id"),
        filename=state.get("filename"),
        document_type=state.get("document_type", "REPORT"),
        original_language=state.get("language", "English"),
        translated_language="English" if state.get("translated") else None,
        text_blocks=[TextBlock(**b) for b in raw_ctx.get("text_blocks", [])],
        tables=[TableData(**t) for t in raw_ctx.get("tables", [])],
        images=[ImageEvidence(**i) for i in raw_ctx.get("images", [])]
    )

    state["canonical_context"] = context.model_dump()
    return state
