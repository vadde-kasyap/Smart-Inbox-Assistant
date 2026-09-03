import fitz  # PyMuPDF
from typing import List, Tuple
from app.schemas.canonical import TextBlock

def extract_digital_pdf(file_path: str) -> Tuple[bool, int, List[TextBlock]]:
    """
    Extracts structured text blocks and layout information using PyMuPDF.
    Returns: (is_digital: bool, page_count: int, text_blocks: List[TextBlock])
    """
    doc = fitz.open(file_path)
    text_blocks: List[TextBlock] = []
    total_characters = 0

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1
        blocks = page.get_text("blocks")

        for b in blocks:
            # block format: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 is text
            if len(b) >= 5 and b[4]:
                text = b[4].strip()
                if text:
                    total_characters += len(text)
                    bbox_str = f"bbox:({round(b[0], 1)},{round(b[1], 1)},{round(b[2], 1)},{round(b[3], 1)})"
                    text_blocks.append(TextBlock(
                        text=text,
                        page_number=page_num,
                        location=bbox_str,
                        confidence=1.0,
                        extraction_method="DIGITAL_TEXT"
                    ))

    page_count = len(doc)
    doc.close()

    # If document has substantial text per page, it is digital
    is_digital = total_characters > (page_count * 20)
    return is_digital, page_count, text_blocks
