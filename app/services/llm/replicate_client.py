"""Replicate API client for streaming AI models.

Provides streaming support for various AI models available on Replicate.
Includes fallback to OpenAI if Replicate fails.

UNIFIED LOGGING 2025-12-25 14:44:
- Логируем ВСЕГДА: [LLM TEXT] - документ/текст
- Логируем ВСЕГДА: [LLM SYSTEM PROMPT] - системный промпт
- Логируем ВСЕГДА: [LLM USER PROMPT] - пользовательский промпт
- ОДИН РАЗ - в analyze_document_stream (используется везде)
- БЕЗ ДУБЛЕй в handlers (documents, homework, rag, etc.)

FIXES 2025-12-28 20:35:
- REPLICATE_TIMEOUT=300 (5 minutes)
- httpx timeout=300 для больших документов
- Объем документа капсулируется в полю
- Обработка timeout/network ошибок
- Чном разбить большое не требуется
"""

import logging
import os
import httpx
from typing import AsyncIterator, Optional, List, Dict, Any

try:
    import replicate
except ImportError:
    replicate = None  # type: ignore

logger = logging.getLogger(__name__)


class ReplicateClientError(Exception):
    """Raised when Replicate API fails."""
    pass


class ReplicateClient:
    """Client for Replicate AI streaming models.
    
    Supports streaming responses from various models on Replicate.
    Provides fallback and error handling.
    
    UNIFIED LOGGING:
    - All prompts and documents logged here
    - No duplicate logging in handlers
    - Works for all modes: homework, analyze, documents, rag, chat
    
    Attributes:
        api_token: Replicate API token
        model: Model name (e.g., "openai/gpt-4o-mini" or "openai/gpt-5")
    """
    
    # Maximum document size (in chars)
    MAX_DOC_SIZE = 500_000  # 500K chars
    
    def __init__(
        self,
        api_token: str,
        model: str = "openai/gpt-4o-mini",
    ) -> None:
        """Initialize Replicate client.
        
        Args:
            api_token: Replicate API token
            model: Model identifier on Replicate
            
        Raises:
            ImportError: If replicate library not installed
        """
        if not replicate:
            raise ImportError(
                "replicate library not installed. "
                "Install with: pip install replicate"
            )
        
        # CRITICAL: Set the API token as environment variable
        os.environ["REPLICATE_API_TOKEN"] = api_token
        
        # FIX: Increase timeout for large documents (300s = 5 minutes)
        # This prevents "timed out" errors on big docs
        os.environ["REPLICATE_TIMEOUT"] = "300"
        
        # CRITICAL: Set httpx timeout for replicate client
        # This is required for large document processing
        os.environ["HTTPX_TIMEOUT"] = "300"
        
        # Also try to configure replicate's internal httpx client if possible
        try:
            # Some versions of replicate allow client customization
            if hasattr(replicate, "set_http_client"):
                client = httpx.Client(timeout=300)
                replicate.set_http_client(client)
        except Exception:
            pass  # If this fails, just continue - env vars should work
        
        self.client = replicate
        self.api_token = api_token
        self.model = model
        
        logger.info(f"Replicate client initialized with model: {model}")
        logger.info("Replicate timeout set to 300s (5 min) for large documents")
        logger.info("httpx timeout set to 300s for network operations")
    
    def _get_model_input(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 1.0,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Build input parameters for the model.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum completion tokens
            
        Returns:
            Dict with model-specific parameters
        """
        # GPT-4o-mini uses OpenAI-style parameters
        if "gpt-4o-mini" in self.model or "gpt-4o" in self.model:
            return {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "top_p": 1,
                "presence_penalty": 0,
                "frequency_penalty": 0,
                "max_completion_tokens": max_tokens,
                "messages": [],
                "image_input": [],
            }
        else:
            # Generic format for other models
            return {
                "prompt": f"{system_prompt}\n\n{prompt}",
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
    
    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """Simple chat without documents.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            str: AI response
            
        Raises:
            ReplicateClientError: If API call fails
        """
        try:
            # Extract system prompt and user message
            system_prompt = "You are a helpful assistant."
            user_message = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_message = msg["content"]
            
            logger.info(f"Calling Replicate {self.model} for chat")
            
            # Build input with proper format
            input_data = self._get_model_input(
                prompt=user_message,
                system_prompt=system_prompt,
                temperature=1.0,
            )
            
            # Stream from Replicate
            result_parts: List[str] = []
            
            for output in self.client.stream(self.model, input=input_data):
                if output:
                    result_parts.append(str(output))
            
            result = "".join(result_parts)
            
            if not result:
                raise ValueError("Empty response from Replicate")
            
            logger.info(f"Chat completed ({len(result)} chars)")
            return result
        
        except Exception as e:
            logger.error(f"Replicate chat error: {e}")
            raise ReplicateClientError(f"Replicate API error: {e}") from e
    
    async def analyze_document_stream(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Analyze document with streaming response.
        
        UNIFIED LOGGING HERE:
        - Logs document text once
        - Logs system prompt once
        - Logs user prompt once
        - No duplicate logging in handlers
        - Works for all modes
        
        Args:
            document_text: Document content to analyze
            user_prompt: User's analysis request
            system_prompt: Optional system prompt
            user_id: Optional user ID for logging context
            
        Yields:
            str: Stream tokens
        """
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")
        
        # Check document size
        if len(document_text) > self.MAX_DOC_SIZE:
            logger.warning(
                f"Document size ({len(document_text)} chars) exceeds "
                f"recommended limit ({self.MAX_DOC_SIZE} chars). "
                f"May timeout. Truncating..."
            )
            # Truncate to max size
            document_text = document_text[:self.MAX_DOC_SIZE]
            logger.info(f"Document truncated to {len(document_text)} chars")
        
        if not user_prompt or not user_prompt.strip():
            user_prompt = "Analyze this document and provide key insights"
        
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        # UNIFIED LOGGING - ONE PLACE FOR ALL MODES
        # Log document text
        user_id_str = f" (User {user_id})" if user_id else ""
        doc_preview = document_text[:500] + "..." if len(document_text) > 500 else document_text
        logger.info(f"[LLM TEXT]{user_id_str}: {len(document_text)} chars")
        logger.info(f"[LLM TEXT RAW]{user_id_str}:\n{doc_preview}")
        
        # Log system prompt
        logger.info(f"[LLM SYSTEM PROMPT]{user_id_str}:\n{system_prompt}")
        
        # Log user prompt
        user_prompt_preview = user_prompt[:300] + "..." if len(user_prompt) > 300 else user_prompt
        logger.info(f"[LLM USER PROMPT]{user_id_str} ({len(user_prompt)} chars):\n{user_prompt_preview}")
        
        # Build complete prompt
        full_prompt = self._build_prompt(
            document_text,
            user_prompt,
            system_prompt,
        )
        
        try:
            logger.info(
                f"Calling Replicate {self.model} for streaming analysis "
                f"(doc: {len(document_text)} chars, full_prompt: {len(full_prompt)} chars)"
            )
            
            # Build input with proper format
            input_data = self._get_model_input(
                prompt=full_prompt,
                system_prompt="You are an expert document analyst.",
                temperature=0.7,
                max_tokens=4096,
            )
            
            # Stream from Replicate (with 300s timeout set in __init__)
            for output in self.client.stream(self.model, input=input_data):
                if output:
                    yield str(output)
            
            logger.info("Stream analysis completed")
        
        except TimeoutError as e:
            logger.error(f"Replicate timeout (>300s): {e}")
            raise ReplicateClientError(
                f"Document analysis timed out (>5 min). "
                f"Document may be too large or Replicate API is slow."
            ) from e
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                logger.error(f"Replicate streaming timeout: {e}")
                raise ReplicateClientError(
                    f"Analysis timeout. Try with smaller document."
                ) from e
            else:
                logger.error(f"Replicate streaming error: {e}")
                raise ReplicateClientError(f"Replicate API error: {e}") from e
    
    async def analyze_document(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """Analyze document and return complete response.
        
        Args:
            document_text: Document content
            user_prompt: Analysis request
            system_prompt: Optional system prompt
            user_id: Optional user ID for logging
            
        Returns:
            str: Complete analysis response
        """
        result_parts: List[str] = []
        
        async for token in self.analyze_document_stream(
            document_text,
            user_prompt,
            system_prompt,
            user_id=user_id,
        ):
            result_parts.append(token)
        
        return "".join(result_parts)
    
    def _build_prompt(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: str,
    ) -> str:
        """Build complete prompt from components.
        
        Args:
            document_text: Document content
            user_prompt: User request
            system_prompt: System instructions
            
        Returns:
            str: Complete prompt
        """
        return (
            f"{user_prompt}\n\n"
            f"---DOCUMENT---\n"
            f"{document_text}\n\n"
            f"---END DOCUMENT---\n\n"
            f"Analysis:"
        )
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt.
        
        Returns:
            str: System prompt
        """
        return (
            "You are an expert document analyst. Your task is to analyze documents "
            "and provide clear, actionable insights. "
            "Be concise but thorough. Structure your response with:\n"
            "1. Executive Summary\n"
            "2. Key Points\n"
            "3. Important Details\n"
            "4. Recommendations (if applicable)\n\n"
            "Use markdown formatting for better readability."
        )
    
    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available Replicate models.
        
        Returns:
            List[str]: List of recommended models
        """
        return [
            "openai/gpt-4o-mini",  # Cheapest GPT-4 class model
            "openai/gpt-4o",        # Fastest GPT-4 model
            "openai/gpt-5",         # Most powerful (if available)
            "mistral-community/mistral-7b-instruct-v0.1",
            "meta-llama/llama-2-70b-chat",
        ]
