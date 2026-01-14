"""LangChain-based LLM Handler supporting multiple providers"""
from typing import Optional, Type, Any, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from logic.llm_provider import get_active_provider
import json


class LLMHandler:
    """Unified handler for multiple LLM providers using LangChain"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm: Optional[BaseChatModel] = None
        self.provider_name: Optional[str] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize LLM based on active provider in database"""
        provider = get_active_provider(self.db)
        
        if not provider:
            raise ValueError("No active LLM provider found in database")
        
        self.provider_name = provider.provider_name
        api_key = provider.api_key
        model_name = provider.model_name or self._get_default_model(provider.provider_name)
        
        if provider.provider_name == "openai":
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model_name,
                temperature=0.3
            )
        elif provider.provider_name == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=model_name,
                temperature=0.3
            )
        elif provider.provider_name == "grok":
            # Grok uses Anthropic API format (xAI uses similar structure)
            # Note: Adjust based on actual Grok API when available
            self.llm = ChatAnthropic(
                api_key=api_key,
                model=model_name or "claude-3-opus-20240229",
                temperature=0.3
            )
        else:
            raise ValueError(f"Unsupported provider: {provider.provider_name}")
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        defaults = {
            "openai": "gpt-4o",
            "gemini": "gemini-pro",
            "grok": "grok-beta"
        }
        return defaults.get(provider, "gpt-4o")
    
    async def invoke_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_schema: Type[BaseModel],
        user_content: str = ""
    ) -> tuple[BaseModel, int]:
        """
        Invoke LLM with structured output parsing
        
        Returns:
            Tuple of (parsed_response, status_code)
        """
        try:
            from langchain_core.output_parsers import PydanticOutputParser
            
            parser = PydanticOutputParser(pydantic_object=response_schema)
            format_instructions = parser.get_format_instructions()
            
            full_system = f"{system_prompt}\n\n{format_instructions}"
            full_user = f"{prompt}\n\n{user_content}" if user_content else prompt
            
            messages = [
                ("system", full_system),
                ("human", full_user)
            ]
            
            response = await self.llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse structured output
            if isinstance(content, str):
                # Try to extract JSON from markdown code blocks if present
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    if json_end > json_start:
                        content = content[json_start:json_end].strip()
                
                parsed = parser.parse(content)
            else:
                parsed = response_schema(**json.loads(str(content)))
            
            return parsed, 200
            
        except Exception as e:
            raise Exception(f"LLM structured parsing error: {str(e)}")
    
    async def invoke_text(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3
    ) -> tuple[str, int]:
        """
        Invoke LLM for text generation
        
        Returns:
            Tuple of (response_text, status_code)
        """
        try:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))
            
            response = await self.llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            return content, 200
            
        except Exception as e:
            return f"Error: {str(e)}", 400
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get current provider information"""
        return {
            "provider": self.provider_name,
            "model": self.llm.model_name if hasattr(self.llm, 'model_name') else "unknown"
        }
