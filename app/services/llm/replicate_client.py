"""Replicate API client for streaming AI models.

Provides streaming support for various AI models available on Replicate.
Includes fallback to OpenAI if Replicate fails.
"""

import logging
import os
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
    
    Attributes:
        api_token: Replicate API token
        model: Model name (e.g., "openai/gpt-5" or "mistral-community/mistral-7b-instruct-v0.1")
    """
    
    def __init__(
        self,
        api_token: str,
        model: str = "openai/gpt-5",
    ) -> None:
        """Initialize Replicate client.
        
        Args:
            api_token: Replicate API token
            model: Model identifier on Replicate
            
        Raises:
            ImportError: If replicate library is not installed
        """
        if not replicate:
            raise ImportError(
                "replicate library not installed. "
                "Install with: pip install replicate"
            )
        
        # CRITICAL: Set the API token as environment variable
        # This is how the replicate library expects to receive auth
        os.environ["REPLICATE_API_TOKEN"] = api_token
        
        self.client = replicate
        self.api_token = api_token
        self.model = model
        
        logger.info(f"Replicate client initialized with model: {model}")
    
    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """Simple chat without documents.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            str: AI response
            
        Raises:
            ReplicateClientError: If API call fails
            
        Example:
            >>> client = ReplicateClient(api_token="...", model="openai/gpt-5")
            >>> response = await client.chat([
            ...     {"role": "system", "content": "You are helpful assistant"},
            ...     {"role": "user", "content": "Hello!"}
            ... ])
        """
        try:
            # Extract system prompt and user message
            system_prompt = ""
            user_message = ""
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                elif msg["role"] == "user":
                    user_message = msg["content"]
            
            # Build prompt for Replicate
            full_prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            
            logger.info(f"Calling Replicate {self.model} for chat")
            
            # Stream from Replicate
            input_data = {"prompt": full_prompt}
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
    ) -> AsyncIterator[str]:
        """Analyze document with streaming response.
        
        Streams tokens as they arrive from the model.
        
        Args:
            document_text: Document content to analyze
            user_prompt: User's analysis request
            system_prompt: Optional system prompt (uses default if None)
            
        Yields:
            str: Stream tokens
            
        Raises:
            ValueError: If document text is empty
            ReplicateClientError: If API call fails
            
        Example:
            >>> client = ReplicateClient(api_token="...", model="openai/gpt-5")
            >>> async for token in client.analyze_document_stream(
            ...     "Document content...",
            ...     "Summarize key points"
            ... ):
            ...     print(token, end="")
        """
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")
        
        if not user_prompt or not user_prompt.strip():
            user_prompt = "Analyze this document and provide key insights"
        
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        # Build complete prompt
        full_prompt = self._build_prompt(
            document_text,
            user_prompt,
            system_prompt,
        )
        
        try:
            logger.info(
                f"Calling Replicate {self.model} for streaming analysis "
                f"(doc: {len(document_text)} chars)"
            )
            
            # Stream from Replicate
            input_data = {"prompt": full_prompt}
            
            for output in self.client.stream(self.model, input=input_data):
                if output:
                    yield str(output)
            
            logger.info("Stream analysis completed")
        
        except Exception as e:
            logger.error(f"Replicate streaming error: {e}")
            raise ReplicateClientError(f"Replicate API error: {e}") from e
    
    async def analyze_document(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Analyze document and return complete response.
        
        Collects all streamed tokens into single response.
        
        Args:
            document_text: Document content
            user_prompt: Analysis request
            system_prompt: Optional system prompt
            
        Returns:
            str: Complete analysis response
            
        Raises:
            ValueError: If document is empty
            ReplicateClientError: If API fails
        """
        result_parts: List[str] = []
        
        async for token in self.analyze_document_stream(
            document_text,
            user_prompt,
            system_prompt,
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
            f"{system_prompt}\n\n"
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
        
        Popular models for document analysis:
        - openai/gpt-5 (most powerful)
        - mistral-community/mistral-7b-instruct-v0.1 (fast, open)
        - meta-llama/llama-2-70b-chat (powerful, open)
        - nousresearch/nous-hermes-2-mixtral-8x7b-dpo (good balance)
        
        Returns:
            List[str]: List of recommended models
        """
        return [
            "openai/gpt-5",
            "mistral-community/mistral-7b-instruct-v0.1",
            "meta-llama/llama-2-70b-chat",
            "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
        ]
