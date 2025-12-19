# Uh Bot - Document Analysis Telegram Bot

🤖 An intelligent Telegram bot for document analysis using OpenAI GPT-5 (with GPT-4o fallback).

## Features

✨ **Multiple Document Formats**
- PDF files
- Microsoft Word documents (DOCX)
- Plain text files
- ZIP archives (with multiple files)

🧠 **AI-Powered Analysis**
- Document summarization
- Key point extraction
- Risk and issue identification
- Named entity extraction
- Custom analysis with your prompts

📱 **Telegram Integration**
- Easy file upload via Telegram
- Real-time processing status
- Automatic message splitting for long responses
- Word document generation for very long results

🔒 **Security & Privacy**
- Automatic cleanup of temporary files
- Protection against zip bombs and malicious archives
- No data stored on servers
- Secure path traversal prevention

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/severand/TG_bot.git
cd TG_bot
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -e .
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your tokens
```

Required variables:
- `TG_BOT_TOKEN` - Your Telegram Bot Token
- `OPENAI_API_KEY` - Your OpenAI API Key

Optional variables:
- `OPENAI_MODEL` - Model to use (default: gpt-4o)
- `LOG_LEVEL` - Logging level (default: INFO)
- `MAX_FILE_SIZE` - Maximum file size in bytes (default: 20MB)
- `MAX_ARCHIVE_SIZE` - Maximum ZIP archive size (default: 100MB)
- `TEMP_DIR` - Temporary directory (default: ./temp)

## Running the Bot

### Development

```bash
python main.py
```

The bot will start polling for updates.

### Docker (with Cog)

```bash
cog push your-registry/tg-bot:latest
```

## Project Structure

```
TG_bot/
├── app/
│   ├── config.py                 # Configuration management
│   ├── bot.py                    # Bot initialization
│   ├── filters/                  # Custom filters
│   ├── handlers/
│   │   ├── common.py            # /start, /help, /cancel
│   │   └── documents.py         # File upload and analysis
│   ├── states/
│   │   └── analysis.py          # FSM states
│   ├── services/
│   │   ├── file_processing/
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── zip_handler.py
│   │   │   └── converter.py
│   │   └── llm/
│   │       └── openai_client.py
│   └── utils/
│       ├── text_splitter.py
│       └── cleanup.py
├── tests/
├── main.py                       # Entry point
├── pyproject.toml               # Dependencies and tools config
└── README.md
```

## Usage

### Start the bot
```
/start - Initialize the bot
/help - Show help information
/cancel - Cancel current operation
```

### Upload and analyze
1. Send any document (PDF, DOCX, TXT, or ZIP)
2. Bot will extract content
3. AI will analyze and provide insights
4. Results sent as text messages or Word document if too long

## API Integration

### OpenAI

The bot uses OpenAI's GPT-5 (or GPT-4o as fallback) for analysis.

- Max response tokens: 4000
- Temperature: 0.7 (balanced creativity)
- Supports system prompts for custom analysis

### Telegram

- File size limit: 20MB
- Message size limit: 4096 characters (handled automatically)
- Uses polling for updates (not webhooks)

## File Processing

### PDF
- Text extraction using pypdf
- Page-by-page processing
- Metadata extraction

### DOCX
- Text extraction from paragraphs and tables
- Formatting preservation
- Metadata extraction

### ZIP Archives
- Automatic extraction of supported formats
- Zip bomb detection and prevention
- Compression ratio validation
- Path traversal attack prevention

### Security Features

- **Zip Bomb Protection**: Validates compression ratios and extracted size
- **Path Traversal Prevention**: Normalizes file paths
- **File Size Limits**: Enforces both file and archive size limits
- **File Type Validation**: Only processes supported formats

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=app tests/

# Linting
ruff check app/

# Type checking
mypy app/
```

## Error Handling

The bot gracefully handles:
- Corrupted files
- API rate limiting
- Network timeouts
- Invalid file formats
- Oversized files
- Empty documents

## Performance

- Cold start: < 5 seconds
- File processing: 5-15 seconds (depending on file size)
- AI analysis: 10-30 seconds (depends on OpenAI)
- Total response time: < 60 seconds for most files

## Monitoring and Logging

- Structured logging with structlog
- All operations logged
- Error tracking with detailed context
- Performance metrics available

## Deployment

### Replicate (Cog)

The project includes `cog.yaml` for Replicate deployment.

```bash
cog push your-registry/tg-bot
```

### VPS / Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "main.py"]
```

### Environment-specific config

Update `.env` for your deployment:
- Development: `LOG_LEVEL=DEBUG`
- Production: `LOG_LEVEL=INFO`

## Troubleshooting

### Bot doesn't respond
1. Check `TG_BOT_TOKEN` is correct
2. Check internet connection
3. Review logs: `LOG_LEVEL=DEBUG`

### "Invalid API key" error
1. Verify `OPENAI_API_KEY` is correct
2. Check API key has access to your model
3. Verify quota/billing in OpenAI dashboard

### File processing fails
1. Ensure file format is supported
2. Check file is not corrupted
3. Verify file is under size limit
4. Check temp directory has write permissions

## Architecture

### Clean Architecture

The project follows Clean Architecture principles:

- **Handlers Layer**: User interface (Telegram)
- **Services Layer**: Business logic (file processing, AI)
- **Utils Layer**: Infrastructure (cleanup, text splitting)
- **Config Layer**: Configuration management

### Async/Await

Fully asynchronous using `asyncio`:
- Non-blocking I/O operations
- Efficient concurrent request handling
- Better scalability

### FSM (Finite State Machine)

Manages user conversation flow:
- `waiting_for_file`: Ready to receive files
- `processing`: Currently processing
- `analyzing`: Sending to AI

## Security Considerations

✅ Input validation for all file uploads
✅ Protection against zip bombs
✅ Secure temporary file handling
✅ API key stored in environment variables
✅ No logs contain sensitive data
✅ Automatic cleanup of user files

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review documentation

## Changelog

### v1.0.0 (2025-12-19)
- Initial release
- PDF, DOCX, TXT, ZIP support
- OpenAI GPT integration
- Telegram bot integration
- Security features (zip bomb protection)
- Complete error handling

---

**Made with ❤️ by the Uh Bot Team**
