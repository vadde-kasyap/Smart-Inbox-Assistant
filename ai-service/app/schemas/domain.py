from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class Classification(BaseModel):
    category: Literal["ICSR", "PQC", "MI", "NOT_RELEVANT"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., min_length=1, description="Concise reason grounded in the source material")

class SourceReference(BaseModel):
    source_type: Literal["PDF", "EMAIL"]
    email_id: Optional[int] = None
    attachment_id: Optional[int] = None
    page_number: Optional[int] = None
    text_snippet: Optional[str] = None
    location: Optional[str] = None

class ExtractedField(BaseModel):
    field_group: str = Field(..., description="e.g., patient, reporter, product, reaction, pqc, mi")
    field_name: str = Field(..., description="e.g., age, sex, name, batch_lot, questions")
    value: str = Field(..., description="Extracted value or 'Not stated' if missing")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_references: List[SourceReference] = Field(default_factory=list)

class ImageResult(BaseModel):
    page_number: int
    description: str
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    review_required: bool = True

class ProcessingMetrics(BaseModel):
    total_duration_ms: int = 0
    extraction_duration_ms: int = 0
    ocr_duration_ms: int = 0
    translation_duration_ms: int = 0
    llm_duration_ms: int = 0
    validation_duration_ms: int = 0
