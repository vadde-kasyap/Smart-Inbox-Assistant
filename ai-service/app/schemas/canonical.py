from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field

class TextBlock(BaseModel):
    text: str
    page_number: int
    location: Optional[str] = None
    confidence: float = 1.0
    extraction_method: str = "DIGITAL_TEXT"

class TableData(BaseModel):
    columns: List[str]
    rows: List[List[str]]
    page_number: int

class ImageEvidence(BaseModel):
    page_number: int
    description: str
    confidence: float = 0.85
    review_required: bool = True

class CanonicalCaseContext(BaseModel):
    email_id: Optional[int] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    email_body: Optional[str] = None
    attachment_id: Optional[int] = None
    filename: Optional[str] = None
    document_type: str = "REPORT" # REPORT, FORM, ARTICLE
    original_language: str = "English"
    translated_language: Optional[str] = None
    text_blocks: List[TextBlock] = Field(default_factory=list)
    tables: List[TableData] = Field(default_factory=list)
    images: List[ImageEvidence] = Field(default_factory=list)
