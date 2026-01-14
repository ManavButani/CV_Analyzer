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
    
    def __init__(self, db: Session, verbose: bool = False):
        self.db = db
        self.llm: Optional[BaseChatModel] = None
        self.provider_name: Optional[str] = None
        self.model_name: Optional[str] = None  # Store model name explicitly
        self.verbose = verbose
        self.reasoning_log: list = []  # Store model reasoning steps
        self._initialize()
    
    def _initialize(self):
        """Initialize LLM based on active provider in database"""
        from langchain_core.callbacks import CallbackManager
        from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
        
        provider = get_active_provider(self.db)
        
        if not provider:
            raise ValueError("No active LLM provider found in database")
        
        self.provider_name = provider.provider_name
        api_key = provider.api_key
        model_name = provider.model_name or self._get_default_model(provider.provider_name)
        self.model_name = model_name  # Store model name for later retrieval
        
        # Setup callbacks for verbose mode
        callbacks = []
        if self.verbose:
            callbacks.append(StreamingStdOutCallbackHandler())
        
        callback_manager = CallbackManager(callbacks) if callbacks else None
        
        if provider.provider_name == "openai":
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model_name,
                temperature=0.3,
                callbacks=callback_manager,
                verbose=self.verbose
            )
        elif provider.provider_name == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=api_key,
                model=model_name,
                temperature=0.3,
                callbacks=callback_manager,
                verbose=self.verbose
            )
        elif provider.provider_name == "grok":
            # Grok uses Anthropic API format (xAI uses similar structure)
            # Note: Adjust based on actual Grok API when available
            self.llm = ChatAnthropic(
                api_key=api_key,
                model=model_name or "claude-3-opus-20240229",
                temperature=0.3,
                callbacks=callback_manager,
                verbose=self.verbose
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
            import re
            
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
            
            # Log reasoning step
            if self.verbose:
                self.reasoning_log.append({
                    "step": "invoke_structured",
                    "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    "response_preview": content[:200] + "..." if len(content) > 200 else content,
                    "model": self.provider_name
                })
            
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
                
                # Clean up invalid characters and fix common JSON issues
                content = self._clean_json_content(content)
                
                # Try parsing with Pydantic parser first
                try:
                    parsed = parser.parse(content)
                except Exception:
                    # Fallback: try direct JSON parsing
                    try:
                        json_data = json.loads(content)
                        parsed = response_schema(**json_data)
                    except json.JSONDecodeError as e:
                        # Try to fix common JSON issues
                        fixed_content = self._fix_json_errors(content)
                        json_data = json.loads(fixed_content)
                        parsed = response_schema(**json_data)
            else:
                parsed = response_schema(**json.loads(str(content)))
            
            return parsed, 200
            
        except Exception as e:
            raise Exception(f"LLM structured parsing error: {str(e)}")
    
    def _clean_json_content(self, content: str) -> str:
        """Clean JSON content by removing invalid characters"""
        import re
        # Remove non-printable characters except newlines and tabs
        content = re.sub(r'[^\x20-\x7E\n\t]', '', content)
        # Remove trailing commas before closing brackets/braces
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        return content.strip()
    
    def _fix_json_errors(self, content: str) -> str:
        """Fix common JSON parsing errors"""
        import re
        # Remove invalid characters at end of arrays/objects
        content = re.sub(r'([\]}])\s*[^\s\]}]+(\s*[\]}])', r'\1\2', content)
        # Fix trailing commas
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        # Remove any text after the last valid JSON bracket/brace
        last_brace = max(content.rfind('}'), content.rfind(']'))
        if last_brace > 0:
            content = content[:last_brace + 1]
        return content
    
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
            "model": self.model_name or "unknown"
        }
    
    def get_reasoning_log(self) -> list:
        """Get accumulated reasoning log"""
        return self.reasoning_log.copy()
    
    def clear_reasoning_log(self):
        """Clear reasoning log"""
        self.reasoning_log = []