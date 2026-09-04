"""
Translation node — translates non-English document text to English.

Strategy
--------
1. If the document is already in English, this node is a no-op.
2. For other languages, the Qwen model is asked to translate the extracted
   text blocks.  Each block is translated individually (preserving page
   numbers and locations).
3. The original text blocks are preserved; a parallel list of translated
   blocks is stored under ``canonical_context["translated_text_blocks"]``.
4. In mock mode (no model), a placeholder translation is inserted so the
   pipeline can still run.
"""

import time
import logging
from typing import List, Dict, Any

from app.graph.state import GraphState
from app.models.qwen_client import get_qwen_client

logger = logging.getLogger(__name__)

# Maximum characters to translate in one model call (avoids context overflow)
_MAX_CHARS_PER_CALL = 2000


def translation_node(state: GraphState) -> GraphState:
    start_time = time.time()

    language = state.get("language", "English")
    canonical = state.get("canonical_context", {}) or {}
    text_blocks: List[Dict[str, Any]] = canonical.get("text_blocks", [])

    if language == "English" or not text_blocks:
        # Nothing to translate
        state["metrics"]["translation_duration_ms"] = int((time.time() - start_time) * 1000)
        return state

    client = get_qwen_client()
    translated_blocks: List[Dict[str, Any]] = []

    # Combine all text, keeping track of page boundaries so we can re-split
    for block in text_blocks:
        original_text = block.get("text", "").strip()
        if not original_text:
            translated_blocks.append({**block, "text": original_text, "extraction_method": "TRANSLATED"})
            continue

        # Truncate very long blocks to avoid context overflow
        chunk = original_text[:_MAX_CHARS_PER_CALL]
        translated_text = _translate_chunk(client, chunk, language)

        translated_blocks.append({
            **block,
            "text": translated_text,
            "original_text": original_text,  # preserve original
            "extraction_method": "TRANSLATED",
        })

    # Store translated blocks alongside originals in the canonical context
    canonical["translated_text_blocks"] = translated_blocks
    # Replace the active text blocks with translated ones for downstream analysis
    canonical["original_text_blocks"] = list(text_blocks)
    canonical["text_blocks"] = translated_blocks
    state["canonical_context"] = canonical

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["translation_duration_ms"] = state["metrics"].get("translation_duration_ms", 0) + duration_ms
    logger.info("Translation node: translated %d block(s) from %s in %d ms",
                len(translated_blocks), language, duration_ms)
    return state


def _translate_chunk(client, text: str, source_language: str) -> str:
    """Call the model to translate `text` from `source_language` to English."""
    if client.is_mock:
        # Mock mode: return a clearly-labelled placeholder that keeps the flow working
        return f"[Translation from {source_language}] {text}"

    prompt = (
        f"Translate the following {source_language} medical document text into English.\n"
        "Return ONLY the English translation, without any preamble or explanation.\n\n"
        f"{text}"
    )

    translated = client.analyze_text(prompt, max_new_tokens=512)
    if not translated:
        logger.warning("Translation returned empty — keeping original text.")
        return text

    return translated.strip()
