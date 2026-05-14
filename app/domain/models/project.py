from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlatformEntry(BaseModel):
    platform: str
    url: Optional[str] = None
    viewport: Optional[dict] = None
    app_package: Optional[str] = None
    app_activity: Optional[str] = None


class DocumentRef(BaseModel):
    id: str = ""
    url: str
    type: str = "prd"
    description: str = ""
    version: str = ""
    status: str = "pending"


class ProjectConfig(BaseModel):
    timeout_ms: int = 30000
    retry_max: int = 3
    retry_delay_s: int = 10
    screenshot_on_error: bool = True


class Project(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    status: str = "created"
    platforms: list[str] = ["web"]
    entries: list[PlatformEntry] = []
    document_refs: list[DocumentRef] = []
    config: ProjectConfig = ProjectConfig()
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: Optional[datetime] = None
