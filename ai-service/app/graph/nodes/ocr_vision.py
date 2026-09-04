"""
OCR / Vision node.

Responsibilities
----------------
1. Enumerate all embedded images in the PDF and record them as ImageResult
   objects with a VLM-generated description (or a fallback description in
   mock mode).
2. For SCANNED documents, render each page as a PIL image and ask the Qwen
   model to read the full text.  The resulting text blocks are appended to
   the canonical context so downstream nodes can extract facts from them.
   Low-confidence OCR results are flagged with ``review_required=True``.

AGENTS.md references
--------------------
§5 — Scanned/Handwritten PDFs
§5 — Images
"""

import time
import io
import os
import logging
from typing import List

import fitz  # PyMuPDF

from app.graph.state import GraphState
from app.schemas.domain import ImageResult
from app.schemas.canonical import TextBlock
from app.models.qwen_client import get_qwen_client

logger = logging.getLogger(__name__)

# Minimum OCR confidence threshold — below this the block is flagged for review
_OCR_REVIEW_THRESHOLD = 0.75

# Resolution scale for page rendering (2× = 144 dpi, good balance of quality vs speed)
_RENDER_SCALE = 2


def ocr_vision_node(state: GraphState) -> GraphState:
    start_time = time.time()
    file_path = state.get("storage_reference", "")
    doc_format = state.get("document_format", "DIGITAL")

    images_found: List[dict] = []
    client = get_qwen_client()

    if not os.path.exists(file_path):
        logger.warning("OCR node: file not found at '%s'. Skipping.", file_path)
        state["metrics"]["ocr_duration_ms"] = int((time.time() - start_time) * 1000)
        state["raw_image_results"] = images_found
        return state

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("OCR node: cannot open PDF '%s': %s", file_path, exc)
        state["metrics"]["ocr_duration_ms"] = int((time.time() - start_time) * 1000)
        state["raw_image_results"] = images_found
        return state

    try:
        for page_index, page in enumerate(doc):
            page_num = page_index + 1

            # ── A. Enumerate embedded images ─────────────────────────────
            page_images = page.get_images(full=True)
            for img_idx, img_ref in enumerate(page_images):
                description = _describe_image(client, doc, img_ref, page_num, img_idx)
                confidence = 0.90 if not client.is_mock else 0.85
                images_found.append(
                    ImageResult(
                        page_number=page_num,
                        description=description,
                        confidence=confidence,
                        review_required=True,  # always flag image evidence for review
                    ).model_dump()
                )

            # ── B. OCR for scanned pages ─────────────────────────────────
            if doc_format == "SCANNED":
                _ocr_page(client, page, page_num, state)

        doc.close()

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("OCR node: error processing PDF: %s", exc)

    duration_ms = int((time.time() - start_time) * 1000)
    state["metrics"]["ocr_duration_ms"] = duration_ms
    state["raw_image_results"] = images_found

    if "canonical_context" in state and state["canonical_context"]:
        state["canonical_context"]["images"] = images_found

    logger.info("OCR node: %d image(s) found, format=%s, %d ms", len(images_found), doc_format, duration_ms)
    return state


# ---------------------------------------------------------------------------
# Helper: describe a single embedded image
# ---------------------------------------------------------------------------
def _describe_image(client, doc: fitz.Document, img_ref: tuple, page_num: int, img_idx: int) -> str:
    """Use the VLM to generate a description of the embedded image."""
    if client.is_mock:
        return (
            f"Embedded image on page {page_num} (index {img_idx + 1}). "
            "Visual review is required."
        )

    try:
        # Extract the image bytes
        xref = img_ref[0]
        base_image = doc.extract_image(xref)
        img_bytes = base_image.get("image", b"")
        if not img_bytes:
            return f"Image on page {page_num} could not be extracted."

        from PIL import Image
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        prompt = (
            "Describe this medical/pharmaceutical image concisely in 1–2 sentences. "
            "Note any text, labels, batch numbers, product names, or visible defects. "
            "Do not diagnose."
        )
        description = client.analyze_image(pil_img, prompt, max_new_tokens=150)
        return description or f"Image on page {page_num}: visual content not interpretable."

    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Image description failed for page %d idx %d: %s", page_num, img_idx, exc)
        return f"Image on page {page_num} (index {img_idx + 1}) — description unavailable."


# ---------------------------------------------------------------------------
# Helper: OCR a scanned page
# ---------------------------------------------------------------------------
def _ocr_page(client, page: fitz.Page, page_num: int, state: GraphState) -> None:
    """
    Render a scanned page to a PIL image, call the VLM to extract text,
    and append a TextBlock to the canonical context.
    """
    if "canonical_context" not in state or not state["canonical_context"]:
        state["canonical_context"] = {"text_blocks": [], "tables": [], "images": []}

    text_blocks = state["canonical_context"].setdefault("text_blocks", [])

    if client.is_mock:
        # Mock mode: insert a clearly-labelled placeholder
        text_blocks.append(
            TextBlock(
                text=f"[Mock OCR] Scanned page {page_num} — text would be extracted by Qwen3-VL in production.",
                page_number=page_num,
                location="full-page",
                confidence=0.50,
                extraction_method="VISION_MOCK",
            ).model_dump()
        )
        return

    try:
        from PIL import Image

        # Render page to image
        mat = fitz.Matrix(_RENDER_SCALE, _RENDER_SCALE)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        prompt = (
            "Extract ALL text visible on this medical document page. "
            "Preserve line breaks and layout as much as possible. "
            "Return only the extracted text, nothing else."
        )
        ocr_text = client.analyze_image(pil_img, prompt, max_new_tokens=1024)

        if not ocr_text or not ocr_text.strip():
            ocr_text = f"[OCR: no readable text found on page {page_num}]"
            confidence = 0.30
        else:
            # Heuristic confidence: penalise very short or repeated output
            word_count = len(ocr_text.split())
            confidence = min(0.95, 0.60 + word_count * 0.005)

        review_required = confidence < _OCR_REVIEW_THRESHOLD

        text_blocks.append(
            TextBlock(
                text=ocr_text.strip(),
                page_number=page_num,
                location="full-page",
                confidence=round(confidence, 2),
                extraction_method="VISION",
            ).model_dump()
        )

        if review_required:
            logger.warning(
                "OCR confidence %.2f < %.2f on page %d — flagging review_required.",
                confidence, _OCR_REVIEW_THRESHOLD, page_num
            )
            # Surface in image results as well
            state["canonical_context"]["images"].append(
                ImageResult(
                    page_number=page_num,
                    description=f"Low-confidence OCR on page {page_num} (confidence {confidence:.0%}). Manual text verification required.",
                    confidence=confidence,
                    review_required=True,
                ).model_dump()
            )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("OCR page render failed for page %d: %s", page_num, exc)
        text_blocks.append(
            TextBlock(
                text=f"[OCR Error on page {page_num}: {exc}]",
                page_number=page_num,
                location="full-page",
                confidence=0.10,
                extraction_method="VISION_ERROR",
            ).model_dump()
        )
