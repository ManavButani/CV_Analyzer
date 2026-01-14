"""Database operations for LLM provider configuration"""
from sqlalchemy.orm import Session
from model.llm_provider import LLMProviderConfig
from typing import Optional, Dict


def get_active_provider(db: Session) -> Optional[LLMProviderConfig]:
    """Get the currently active LLM provider"""
    return db.query(LLMProviderConfig).filter(LLMProviderConfig.is_active == True).first()


def get_provider_by_name(db: Session, provider_name: str) -> Optional[LLMProviderConfig]:
    """Get provider by name"""
    return db.query(LLMProviderConfig).filter(LLMProviderConfig.provider_name == provider_name).first()


def set_active_provider(db: Session, provider_name: str) -> bool:
    """Set a provider as active (deactivates others)"""
    # Deactivate all providers
    db.query(LLMProviderConfig).update({"is_active": False})
    
    # Activate the specified provider
    provider = get_provider_by_name(db, provider_name)
    if provider:
        provider.is_active = True
        db.commit()
        return True
    return False


def create_or_update_provider(
    db: Session,
    provider_name: str,
    api_key: str,
    model_name: str = "",
    is_active: bool = False
) -> LLMProviderConfig:
    """Create or update a provider configuration"""
    provider = get_provider_by_name(db, provider_name)
    
    if provider:
        provider.api_key = api_key
        provider.model_name = model_name
        provider.is_active = is_active
    else:
        provider = LLMProviderConfig(
            provider_name=provider_name,
            api_key=api_key,
            model_name=model_name,
            is_active=is_active
        )
        db.add(provider)
    
    db.commit()
    db.refresh(provider)
    return provider


def get_all_providers(db: Session) -> Dict[str, bool]:
    """Get all providers with their active status"""
    providers = db.query(LLMProviderConfig).all()
    return {p.provider_name: p.is_active for p in providers}
