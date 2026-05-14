from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = ""
    project_id: str
    url: str
    type: str = "prd"
    description: str = ""
    version: str = ""
    status: str = "pending"
    rule_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    parsed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class DocumentRaw(BaseModel):
    id: str = ""
    document_id: str
    raw_markdown: str = ""
    content_hash: str = ""
    extracted_at: datetime = Field(default_factory=datetime.now)
