# Replicate API Integration Guide

Uh Bot supports **Replicate API** for streaming AI analysis with multiple models including GPT-5, Mistral, and Llama.

## Overview

### What is Replicate?

[Replicate](https://replicate.com) is a platform that runs open-source and proprietary machine learning models in the cloud. It provides:

- **Streaming Support**: Get responses token-by-token in real-time
- **Multiple Models**: Access to GPT-5, Mistral, Llama, and more
- **Flexible Pricing**: Pay per API call
- **Easy Integration**: Simple HTTP API

## Setup

### 1. Get Replicate API Token

1. Visit [https://replicate.com/account](https://replicate.com/account)
2. Sign up/login
3. Copy your API token from account settings

### 2. Configure Environment

```bash
# .env file
REPLICATE_API_TOKEN=your_token_here
REPLICATE_MODEL=openai/gpt-5
LLM_PROVIDER=replicate
```

### 3. Install Library

```bash
pip install replicate>=0.15.0
```

## Usage

### Basic Configuration

```python
from app.services.llm.replicate_client import ReplicateClient

# Initialize client
client = ReplicateClient(
    api_token="your_token",
    model="openai/gpt-5"
)

# Analyze document
result = await client.analyze_document(
    document_text="Your document content...",
    user_prompt="Analyze this document"
)
print(result)
```

### Streaming (Real-time Tokens)

```python
# Get tokens as they stream
async for token in client.analyze_document_stream(
    document_text="...",
    user_prompt="..."
):
    print(token, end="", flush=True)  # Print each token immediately
```

### With Factory (Multi-Provider)

```python
from app.services.llm.llm_factory import LLMFactory

factory = LLMFactory(
    primary_provider="replicate",
    replicate_api_token="your_token",
    replicate_model="openai/gpt-5",
    openai_api_key="fallback_key",  # Optional fallback
)

# Automatic fallback to OpenAI if Replicate fails
result = await factory.analyze_document(
    document_text="...",
    user_prompt="..."
)
```

## Available Models

### Recommended for Document Analysis

#### 1. **OpenAI GPT-5** (Most Powerful)
```
model: "openai/gpt-5"
```
- Best quality analysis
- Highest cost
- Fastest for complex tasks

#### 2. **Mistral 7B** (Fast & Efficient)
```
model: "mistral-community/mistral-7b-instruct-v0.1"
```
- Good quality, lower cost
- Faster response time
- Open-source

#### 3. **Llama 2 70B** (Balanced)
```
model: "meta-llama/llama-2-70b-chat"
```
- Strong reasoning capabilities
- Good for detailed analysis
- Lower cost than GPT-5

#### 4. **Nous Hermes 2** (Specialized)
```
model: "nousresearch/nous-hermes-2-mixtral-8x7b-dpo"
```
- Optimized for instruction-following
- Good for structured outputs
- Competitive pricing

## Configuration Examples

### Primary Replicate with OpenAI Fallback

```bash
# .env
REPLICATE_API_TOKEN=r8_xxx
REPLICATE_MODEL=openai/gpt-5
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
LLM_PROVIDER=replicate
```

**Behavior:**
- Uses Replicate by default
- Falls back to OpenAI if Replicate fails
- Can switch providers at runtime

### Primary OpenAI with Replicate Fallback

```bash
# .env
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
REPLICATE_API_TOKEN=r8_xxx
REPLICATE_MODEL=mistral-community/mistral-7b-instruct-v0.1
LLM_PROVIDER=openai
```

**Behavior:**
- Uses OpenAI by default
- Falls back to Mistral if OpenAI fails
- Cost-effective backup

## Streaming Implementation

The bot automatically uses streaming for better UX:

```python
# In handlers/documents.py
analysis_result = await llm_factory.analyze_document(
    extracted_text,
    "Analyze this document...",
    use_streaming=False  # Collects all tokens first
)
```

For real-time streaming to Telegram:

```python
async for token in client.analyze_document_stream(...):
    # Send token to user immediately
    # Use typing indicator while streaming
    await message.bot.send_chat_action(chat_id, ChatAction.TYPING)
```

## Cost Comparison

| Model | Input Cost | Output Cost | Speed | Quality |
|-------|-----------|-----------|-------|----------|
| GPT-5 | $0.03/1K | $0.06/1K | Fast | Excellent |
| Mistral 7B | $0.0005/1K | $0.0015/1K | Very Fast | Good |
| Llama 2 70B | $0.001/1K | $0.003/1K | Fast | Excellent |
| Claude 3 | $0.003/1K | $0.015/1K | Medium | Excellent |

*Prices as of 2025 - check Replicate for current rates*

## Error Handling

The bot handles Replicate errors gracefully:

```python
try:
    result = await client.analyze_document(...)
except ReplicateClientError as e:
    logger.error(f"Replicate failed: {e}")
    # Falls back to OpenAI if configured
except ValueError as e:
    logger.error(f"Invalid input: {e}")
```

## Running Demo

```bash
# Set your token
export REPLICATE_API_TOKEN="your_token"

# Run streaming demo
python examples/replicate_streaming_demo.py
```

Output:
```
🤖 Uh Bot - Replicate Integration Demo

============================================================
📄 Document Analysis with Replicate Streaming
============================================================

Document: 234 characters
Provider: Replicate (openai/gpt-5)

🤖 Analysis Response (streaming):

------------------------------------------------------------
The document describes an intelligent document analysis system
with the following key features:

1. **Multi-format Support**: PDF, DOCX, TXT, ZIP files
2. **AI-Powered Analysis**: Uses advanced language models
3. **Streaming**: Real-time token streaming support
...

✅ Analysis complete!
Response length: 856 characters
```

## Monitoring

Replicate provides API usage dashboard:

1. Visit [https://replicate.com/usage](https://replicate.com/usage)
2. View API calls and costs
3. Set up billing alerts

## Troubleshooting

### "API token not found"
```bash
# Make sure REPLICATE_API_TOKEN is set
echo $REPLICATE_API_TOKEN

# Or in .env:
REPLICATE_API_TOKEN=r8_xxxxx
```

### "Model not found"
```python
# Check available models
available = ReplicateClient.get_available_models()
print(available)

# Use exact model name from Replicate
model="meta-llama/llama-2-70b-chat"
```

### "Rate limited"
```python
# Replicate has rate limits
# Solution: Implement exponential backoff
import asyncio

for attempt in range(3):
    try:
        result = await client.analyze_document(...)
        break
    except RateLimitError:
        wait_time = 2 ** attempt
        await asyncio.sleep(wait_time)
```

## Advanced Usage

### Custom System Prompts

```python
custom_prompt = (
    "You are a legal document analyst. "
    "Focus on contract clauses and legal obligations."
)

result = await client.analyze_document(
    document_text="...",
    user_prompt="Analyze this contract",
    system_prompt=custom_prompt
)
```

### Provider Switching at Runtime

```python
factory = LLMFactory(...)

# Start with primary
factory.primary_provider = "replicate"
result = await factory.analyze_document(...)

# Switch if needed
factory.set_primary_provider("openai")
result = await factory.analyze_document(...)
```

## Performance Tips

1. **Use appropriate model size**
   - 7B for quick, cheap analysis
   - 70B for complex reasoning
   - GPT-5 for best quality

2. **Batch requests**
   - Group multiple documents
   - Process in parallel

3. **Monitor tokens**
   - Long documents = higher cost
   - Summarize before analysis

4. **Cache results**
   - Store analysis for same document
   - Avoid duplicate API calls

## Security

✅ API tokens stored in environment variables
✅ No tokens in code or logs
✅ HTTPS for all API calls
✅ Data processed in-memory only

## References

- [Replicate API Docs](https://replicate.com/docs/guides/get-started-with-the-api)
- [Available Models](https://replicate.com/collections/models)
- [Pricing](https://replicate.com/pricing)
- [Community](https://replicate.com/docs/community-guide)

---

**Last Updated:** 2025-12-19
