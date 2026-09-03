from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.domain import Classification, ExtractedField, ImageResult, ProcessingMetrics

class AIProcessResponse(BaseModel):
    job_id: int = Field(..., alias="jobId")
    model_name: str = Field(..., alias="modelName")
    model_version: str = Field("v1.0", alias="modelVersion")
    prompt_version: str = Field("v1", alias="promptVersion")
    summary: str
    relevant: bool = True
    classifications: List[Classification] = Field(default_factory=list)
    extracted_fields: List[ExtractedField] = Field(default_factory=list, alias="extractedFields")
    image_results: List[ImageResult] = Field(default_factory=list, alias="imageResults")
    metrics: ProcessingMetrics = Field(default_factory=ProcessingMetrics)
    validation_passed: bool = Field(True, alias="validationPassed")

    class Config:
        populate_by_name = True
