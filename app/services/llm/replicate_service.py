"""Replicate LLM service for homework checking."""

import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class ReplicateService:
    """Service for interacting with Replicate API."""

    def __init__(self, api_key: str):
        """Initialize Replicate service.
        
        Args:
            api_key: Replicate API key
        """
        self.api_key = api_key
        self.base_url = "https://api.replicate.com/v1"
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Token {api_key}"}
        )

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """Generate text using Replicate model.
        
        Args:
            model: Model identifier (e.g., 'meta/llama-2-7b')
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            # Create prediction
            response = await self.client.post(
                f"{self.base_url}/predictions",
                json={
                    "version": model,
                    "input": {
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                }
            )
            response.raise_for_status()
            
            prediction = response.json()
            prediction_id = prediction["id"]
            
            # Poll for completion
            while True:
                status_response = await self.client.get(
                    f"{self.base_url}/predictions/{prediction_id}"
                )
                status_response.raise_for_status()
                
                result = status_response.json()
                
                if result["status"] == "succeeded":
                    # Extract text from output
                    output = result.get("output", [])
                    if isinstance(output, list):
                        return "".join(output)
                    return str(output)
                
                elif result["status"] == "failed":
                    raise RuntimeError(
                        f"Prediction failed: {result.get('error', 'Unknown error')}"
                    )
                
                # Wait before polling again
                import asyncio
                await asyncio.sleep(1)
        
        except httpx.HTTPError as e:
            logger.error(f"Replicate API error: {e}")
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
