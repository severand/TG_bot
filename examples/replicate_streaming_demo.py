#!/usr/bin/env python3
"""Demo script showing Replicate streaming integration.

Usage:
    python examples/replicate_streaming_demo.py

Requires:
    - REPLICATE_API_TOKEN environment variable
    - replicate>=0.15.0 library installed
"""

import asyncio
import os
from app.services.llm.replicate_client import ReplicateClient


async def demo_replicate_streaming() -> None:
    """Demo Replicate streaming for document analysis."""
    
    # Get API token
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("❌ REPLICATE_API_TOKEN not set")
        return
    
    # Initialize client
    print("Initializing Replicate client...")
    client = ReplicateClient(
        api_token=api_token,
        model="openai/gpt-5",  # or use mistral-7b, llama-2-70b, etc.
    )
    
    # Sample document
    document_text = """
    The project aims to develop an intelligent document analysis system.
    It should support multiple file formats including PDF, DOCX, and text files.
    The system uses advanced AI models for analysis and provides insights.
    Key features include streaming support, multi-provider fallback, and security.
    """
    
    print("\n" + "="*60)
    print("📄 Document Analysis with Replicate Streaming")
    print("="*60 + "\n")
    
    print(f"Document: {len(document_text)} characters")
    print(f"Provider: Replicate (openai/gpt-5)\n")
    
    print("🤖 Analysis Response (streaming):\n")
    print("-" * 60)
    
    try:
        # Stream the analysis
        response_text = ""
        async for token in client.analyze_document_stream(
            document_text,
            "Analyze this document and provide key insights:",
        ):
            print(token, end="", flush=True)
            response_text += token
        
        print("\n" + "-" * 60)
        print(f"\n✅ Analysis complete!")
        print(f"Response length: {len(response_text)} characters\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}\n")


async def demo_replicate_comparison() -> None:
    """Demo comparison of different Replicate models."""
    
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        print("❌ REPLICATE_API_TOKEN not set")
        return
    
    models = [
        "openai/gpt-5",
        # Uncomment to test other models:
        # "mistral-community/mistral-7b-instruct-v0.1",
        # "meta-llama/llama-2-70b-chat",
    ]
    
    document_text = "Summarize: AI is transforming the world."
    
    print("\n" + "="*60)
    print("🔍 Model Comparison Demo")
    print("="*60 + "\n")
    
    for model_name in models:
        print(f"Testing: {model_name}")
        try:
            client = ReplicateClient(
                api_token=api_token,
                model=model_name,
            )
            
            result = await client.analyze_document(
                document_text,
                "Provide a concise summary:",
            )
            
            print(f"Response: {result[:100]}...\n")
        
        except Exception as e:
            print(f"❌ Error: {e}\n")


async def main() -> None:
    """Run all demos."""
    print("🤖 Uh Bot - Replicate Integration Demo\n")
    
    # Demo 1: Streaming
    await demo_replicate_streaming()
    
    # Demo 2: Model comparison (optional)
    # await demo_replicate_comparison()


if __name__ == "__main__":
    asyncio.run(main())
