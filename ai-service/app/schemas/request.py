from typing import Optional
from pydantic import BaseModel, Field

class EmailContext(BaseModel):
    email_id: Optional[int] = Field(None, alias="emailId")
    sender: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

    class Config:
        populate_by_name = True

class DocumentContext(BaseModel):
    attachment_id: Optional[int] = Field(None, alias="attachmentId")
    filename: str
    content_type: Optional[str] = Field("application/pdf", alias="contentType")
    storage_reference: str = Field(..., alias="storageReference")

    class Config:
        populate_by_name = True

class AIProcessRequest(BaseModel):
    job_id: int = Field(..., alias="jobId")
    email: Optional[EmailContext] = None
    document: DocumentContext

    class Config:
        populate_by_name = True
