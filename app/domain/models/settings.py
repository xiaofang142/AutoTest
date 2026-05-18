from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    extraction_model: str = "gpt-4o"
    analysis_model: str = "gpt-4o-mini"
    status: str = "disconnected"
    connected_at: Optional[datetime] = None


class SystemSettings(BaseModel):
    id: str = "default"
    llm: LLMProviderConfig = LLMProviderConfig()
    log_level: str = "INFO"
    storage_backend: str = "local"
    executor_mode: str = "real"
    updated_at: datetime = Field(default_factory=datetime.now)
