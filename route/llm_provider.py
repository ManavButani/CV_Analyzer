"""Routes for managing LLM provider configuration"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from core.database import get_db
from logic.auth import get_current_active_user
from logic.llm_provider import (
    create_or_update_provider, get_active_provider,
    set_active_provider, get_all_providers
)
from schema.user import User

router = APIRouter()


class LLMProviderRequest(BaseModel):
    provider_name: str  # "openai", "gemini", "grok"
    api_key: str
    model_name: Optional[str] = ""
    is_active: bool = False


@router.post("/configure/")
async def configure_provider(
    provider: LLMProviderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Configure an LLM provider"""
    if provider.provider_name not in ["openai", "gemini", "grok"]:
        raise HTTPException(
            status_code=400,
            detail="Provider must be one of: openai, gemini, grok"
        )
    
    result = create_or_update_provider(
        db=db,
        provider_name=provider.provider_name,
        api_key=provider.api_key,
        model_name=provider.model_name,
        is_active=provider.is_active
    )
    
    # If setting as active, deactivate others
    if provider.is_active:
        set_active_provider(db, provider.provider_name)
    
    return {
        "message": f"Provider {provider.provider_name} configured",
        "provider": provider.provider_name,
        "is_active": result.is_active
    }


@router.post("/activate/{provider_name}/")
async def activate_provider(
    provider_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Activate a provider (deactivates others)"""
    success = set_active_provider(db, provider_name)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Provider {provider_name} not found"
        )
    
    return {
        "message": f"Provider {provider_name} activated",
        "provider": provider_name
    }


@router.get("/status/")
async def get_provider_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get status of all providers"""
    active = get_active_provider(db)
    all_providers = get_all_providers(db)
    
    return {
        "active_provider": active.provider_name if active else None,
        "providers": all_providers
    }
