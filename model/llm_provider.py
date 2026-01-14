from sqlalchemy import Column, Integer, String, Boolean
from core.database import Base


class LLMProviderConfig(Base):
    __tablename__ = "llm_provider_config"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, unique=True, index=True)  # "openai", "gemini", "grok"
    api_key = Column(String)
    is_active = Column(Boolean, default=False)
    model_name = Column(String, default="")  # e.g., "gpt-4o", "gemini-pro", "grok-beta"
