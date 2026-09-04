from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class Classification(BaseModel):
    category: Literal["ICSR", "PQC", "MI", "NOT_RELEVANT"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reason: str = Field(..., min_length=1, description="Concise reason grounded in the source material")

class SourceReference(BaseModel):
    source_type: Literal["PDF", "EMAIL"] = Field(..., alias="sourceType")
    email_id: Optional[int] = Field(None, alias="emailId")
    attachment_id: Optional[int] = Field(None, alias="attachmentId")
    page_number: Optional[int] = Field(None, alias="pageNumber")
    text_snippet: Optional[str] = Field(None, alias="textSnippet")
    location: Optional[str] = None

    class Config:
        populate_by_name = True

class ExtractedField(BaseModel):
    field_group: str = Field(..., description="e.g., patient, reporter, product, reaction, pqc, mi", alias="fieldGroup")
    field_name: str = Field(..., description="e.g., age, sex, name, batch_lot, questions", alias="fieldName")
    value: str = Field(..., description="Extracted value or 'Not stated' if missing")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_references: List[SourceReference] = Field(default_factory=list, alias="sourceReferences")

    class Config:
        populate_by_name = True

class ImageResult(BaseModel):
    page_number: int
    description: str
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    review_required: bool = True

class ProcessingMetrics(BaseModel):
    total_duration_ms: int = Field(0, alias="totalDurationMs")
    extraction_duration_ms: int = Field(0, alias="extractionDurationMs")
    ocr_duration_ms: int = Field(0, alias="ocrDurationMs")
    translation_duration_ms: int = Field(0, alias="translationDurationMs")
    llm_duration_ms: int = Field(0, alias="llmDurationMs")
    validation_duration_ms: int = Field(0, alias="validationDurationMs")

    class Config:
        populate_by_name = True
