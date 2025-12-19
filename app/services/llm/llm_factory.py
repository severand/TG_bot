"""LLM provider factory for flexible AI backend selection.

Supports multiple LLM providers with fallback mechanism.
Allows dynamic provider switching.
"""

import logging
from typing import Union, Optional, AsyncIterator

from app.services.llm.openai_client import OpenAIClient
from app.services.llm.replicate_client import ReplicateClient

logger = logging.getLogger(__name__)


class LLMProvider:
    """Abstract provider interface."""
    
    async def analyze_document(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Analyze document.
        
        Args:
            document_text: Document content
            user_prompt: Analysis request
            system_prompt: Optional system prompt
            
        Returns:
            str: Analysis result
        """
        raise NotImplementedError


class LLMFactory:
    """Factory for creating and managing LLM clients.
    
    Supports multiple providers with fallback mechanism.
    Allows switching providers at runtime.
    """
    
    # Provider types
    PROVIDER_OPENAI = "openai"
    PROVIDER_REPLICATE = "replicate"
    
    def __init__(
        self,
        primary_provider: str = PROVIDER_OPENAI,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o",
        replicate_api_token: Optional[str] = None,
        replicate_model: str = "openai/gpt-5",
    ) -> None:
        """Initialize LLM factory.
        
        Args:
            primary_provider: Primary provider to use (openai or replicate)
            openai_api_key: OpenAI API key
            openai_model: OpenAI model name
            replicate_api_token: Replicate API token
            replicate_model: Replicate model identifier
        """
        self.primary_provider = primary_provider
        self.openai_client: Optional[OpenAIClient] = None
        self.replicate_client: Optional[ReplicateClient] = None
        
        # Initialize OpenAI
        if openai_api_key:
            try:
                self.openai_client = OpenAIClient(
                    api_key=openai_api_key,
                    model=openai_model,
                )
                logger.info(f"OpenAI client initialized (model: {openai_model})")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize Replicate
        if replicate_api_token:
            try:
                self.replicate_client = ReplicateClient(
                    api_token=replicate_api_token,
                    model=replicate_model,
                )
                logger.info(f"Replicate client initialized (model: {replicate_model})")
            except Exception as e:
                logger.warning(f"Failed to initialize Replicate client: {e}")
    
    async def analyze_document(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        use_streaming: bool = False,
    ) -> Union[str, AsyncIterator[str]]:
        """Analyze document using primary or fallback provider.
        
        Tries primary provider first, falls back to secondary if needed.
        
        Args:
            document_text: Document content
            user_prompt: Analysis request
            system_prompt: Optional system prompt
            use_streaming: Return streaming iterator (Replicate only)
            
        Returns:
            Union[str, AsyncIterator[str]]: Analysis result or stream
            
        Raises:
            ValueError: If no providers available
            
        Example:
            >>> factory = LLMFactory(
            ...     openai_api_key="sk-...",
            ...     replicate_api_token="..."
            ... )
            >>> result = await factory.analyze_document(
            ...     "Document...",
            ...     "Analyze this"
            ... )
        """
        primary = self._get_primary_client()
        fallback = self._get_fallback_client()
        
        if not primary and not fallback:
            raise ValueError(
                "No LLM providers available. "
                "Configure OpenAI or Replicate API keys."
            )
        
        # Try primary provider
        try:
            if use_streaming and hasattr(primary, "analyze_document_stream"):
                logger.info(f"Using {self.primary_provider} with streaming")
                return primary.analyze_document_stream(
                    document_text,
                    user_prompt,
                    system_prompt,
                )
            else:
                logger.info(f"Using {self.primary_provider}")
                return await primary.analyze_document(
                    document_text,
                    user_prompt,
                    system_prompt,
                )
        
        except Exception as e:
            logger.warning(
                f"Primary provider ({self.primary_provider}) failed: {e}. "
                f"Trying fallback..."
            )
            
            if fallback:
                try:
                    logger.info(f"Using fallback provider")
                    return await fallback.analyze_document(
                        document_text,
                        user_prompt,
                        system_prompt,
                    )
                except Exception as e2:
                    logger.error(f"Fallback provider also failed: {e2}")
                    raise
            else:
                raise
    
    async def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        use_streaming: bool = False,
    ) -> str:
        """Simple chat without documents.
        
        For general conversation and Q&A.
        
        Args:
            user_message: User's message
            system_prompt: Optional system prompt
            use_streaming: Return streaming (not supported for chat)
            
        Returns:
            str: AI response
            
        Raises:
            ValueError: If no providers available
            
        Example:
            >>> factory = LLMFactory(openai_api_key="sk-...")
            >>> response = await factory.chat(
            ...     "Explain quantum computing"
            ... )
        """
        primary = self._get_primary_client()
        fallback = self._get_fallback_client()
        
        if not primary and not fallback:
            raise ValueError(
                "No LLM providers available. "
                "Configure OpenAI or Replicate API keys."
            )
        
        # Build messages for chat
        messages = [
            {
                "role": "system",
                "content": system_prompt or "You are a helpful assistant.",
            },
            {"role": "user", "content": user_message},
        ]
        
        # Try primary provider
        try:
            logger.info(f"Chat using {self.primary_provider}")
            
            if hasattr(primary, "chat"):
                return await primary.chat(messages)
            else:
                # Fallback to analyze_document if chat not available
                return await primary.analyze_document(
                    "",
                    user_message,
                    system_prompt,
                )
        
        except Exception as e:
            logger.warning(
                f"Primary provider ({self.primary_provider}) failed: {e}. "
                f"Trying fallback..."
            )
            
            if fallback:
                try:
                    logger.info(f"Chat using fallback provider")
                    if hasattr(fallback, "chat"):
                        return await fallback.chat(messages)
                    else:
                        return await fallback.analyze_document(
                            "",
                            user_message,
                            system_prompt,
                        )
                except Exception as e2:
                    logger.error(f"Fallback provider also failed: {e2}")
                    raise
            else:
                raise
    
    def set_primary_provider(self, provider: str) -> None:
        """Change primary provider at runtime.
        
        Args:
            provider: Provider name (openai or replicate)
            
        Raises:
            ValueError: If provider not available
        """
        if provider == self.PROVIDER_OPENAI and not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        if provider == self.PROVIDER_REPLICATE and not self.replicate_client:
            raise ValueError("Replicate client not initialized")
        
        self.primary_provider = provider
        logger.info(f"Primary provider changed to {provider}")
    
    def get_available_providers(self) -> list[str]:
        """Get list of available providers.
        
        Returns:
            list[str]: List of initialized providers
        """
        providers = []
        if self.openai_client:
            providers.append(self.PROVIDER_OPENAI)
        if self.replicate_client:
            providers.append(self.PROVIDER_REPLICATE)
        return providers
    
    def _get_primary_client(self):
        """Get primary client.
        
        Returns:
            Client instance or None
        """
        if self.primary_provider == self.PROVIDER_OPENAI:
            return self.openai_client
        elif self.primary_provider == self.PROVIDER_REPLICATE:
            return self.replicate_client
        return None
    
    def _get_fallback_client(self):
        """Get fallback client.
        
        Returns:
            Client instance or None
        """
        if self.primary_provider == self.PROVIDER_OPENAI:
            return self.replicate_client
        elif self.primary_provider == self.PROVIDER_REPLICATE:
            return self.openai_client
        return None
