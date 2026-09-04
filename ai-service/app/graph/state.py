from typing import TypedDict, Optional, List, Dict, Any

class GraphState(TypedDict):
    job_id: int
    email_id: Optional[int]
    attachment_id: Optional[int]
    filename: str
    storage_reference: str
    email_data: Dict[str, Any]
    document_format: str  # DIGITAL, SCANNED, HYBRID
    document_type: str    # REPORT, FORM, ARTICLE
    language: str
    translated: bool
    translated_text: Optional[str]  # English translation of non-English content
    canonical_context: Optional[Dict[str, Any]]
    raw_classifications: List[Dict[str, Any]]
    raw_extracted_fields: List[Dict[str, Any]]
    raw_image_results: List[Dict[str, Any]]
    raw_summary: str
    is_relevant: bool
    validation_errors: List[str]
    retry_count: int
    metrics: Dict[str, int]
    final_response: Optional[Dict[str, Any]]
