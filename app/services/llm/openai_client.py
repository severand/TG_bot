"""OpenAI GPT client module.

Handles communication with OpenAI API for document analysis.
Includes prompt management and response handling.
"""

import logging
from typing import Optional, List, Dict, Any

from openai import AsyncOpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI GPT models.
    
    Provides document analysis using GPT-4o or other supported models.
    Handles API errors and rate limiting gracefully.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        """Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4o, gpt-4, gpt-3.5-turbo, etc.)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = 4000  # Slightly less than 4096 to be safe
    
    async def chat(self, messages: List[Dict[str, Any]]) -> str:
        """Simple chat without documents.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            str: AI response
            
        Raises:
            APIError: If OpenAI API call fails
            
        Example:
            >>> client = OpenAIClient(api_key="sk-...")
            >>> response = await client.chat([
            ...     {"role": "system", "content": "You are helpful assistant"},
            ...     {"role": "user", "content": "Hello!"}
            ... ])
        """
        try:
            logger.info(f"Calling OpenAI {self.model} for chat")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=self.max_tokens,
                temperature=0.7,
            )
            
            result = response.choices[0].message.content
            if not result:
                raise ValueError("Empty response from API")
            
            logger.info(f"Chat completed ({len(result)} chars)")
            return result
        
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise APIError("API rate limit exceeded. Please try again later.") from e
        
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def analyze_document(
        self,
        document_text: str,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> str:
        """Analyze document using GPT.
        
        Args:
            document_text: Extracted document content
            user_prompt: User's analysis request
            system_prompt: Optional system prompt (uses default if None)
            user_id: Optional user ID for logging context
            
        Returns:
            str: Analysis result from GPT
            
        Raises:
            ValueError: If document text is empty
            APIError: If OpenAI API call fails
            
        Example:
            >>> client = OpenAIClient(api_key="sk-...")
            >>> result = await client.analyze_document(
            ...     "Document content...",
            ...     "Summarize the key points",
            ...     user_id=12345
            ... )
        """
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")
        
        if not user_prompt or not user_prompt.strip():
            user_prompt = "Analyze this document and provide key insights"
        
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{user_prompt}\n\n---DOCUMENT---\n{document_text}"
            },
        ]
        
        try:
            log_prefix = f"User {user_id}" if user_id else "Unknown user"
            logger.info(
                f"[LLM TEXT] {log_prefix}: Calling OpenAI {self.model} for analysis "
                f"(doc: {len(document_text)} chars)"
            )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=self.max_tokens,
                temperature=0.7,
            )
            
            result = response.choices[0].message.content
            if not result:
                raise ValueError("Empty response from API")
            
            logger.info(f"[LLM TEXT] {log_prefix}: Analysis completed ({len(result)} chars)")
            return result
        
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise APIError("API rate limit exceeded. Please try again later.") from e
        
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for document analysis.
        
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
    
    async def extract_entities(
        self,
        document_text: str,
        user_id: Optional[int] = None,
    ) -> str:
        """Extract named entities and important information from document.
        
        Args:
            document_text: Document content
            user_id: Optional user ID for logging context
            
        Returns:
            str: Extracted entities in structured format
        """
        prompt = (
            "Extract and list all important entities from this document:\n"
            "- People (names, roles)\n"
            "- Organizations\n"
            "- Dates\n"
            "- Numbers/monetary amounts\n"
            "- Technical terms\n"
            "- Key concepts\n\n"
            "Format as a clear, organized list."
        )
        
        return await self.analyze_document(document_text, prompt, user_id=user_id)
    
    async def summarize(
        self,
        document_text: str,
        max_length: int = 500,
        user_id: Optional[int] = None,
    ) -> str:
        """Create concise summary of document.
        
        Args:
            document_text: Document content
            max_length: Maximum summary length in words
            user_id: Optional user ID for logging context
            
        Returns:
            str: Document summary
        """
        prompt = (
            f"Create a concise summary of this document in no more than "
            f"{max_length} words. Focus on the most important points."
        )
        
        return await self.analyze_document(document_text, prompt, user_id=user_id)
    
    async def find_risks_and_issues(
        self,
        document_text: str,
        user_id: Optional[int] = None,
    ) -> str:
        """Identify risks, issues, and potential problems in document.
        
        Useful for contract analysis, audit reports, etc.
        
        Args:
            document_text: Document content
            user_id: Optional user ID for logging context
            
        Returns:
            str: Analysis of risks and issues
        """
        prompt = (
            "Analyze this document and identify:\n"
            "1. Potential risks or issues\n"
            "2. Areas of concern\n"
            "3. Missing information\n"
            "4. Inconsistencies\n"
            "5. Recommendations for mitigation\n\n"
            "Be thorough and specific."
        )
        
        return await self.analyze_document(document_text, prompt, user_id=user_id)
