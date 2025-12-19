"""Common command handlers.

Handles /start, /help, and cancel operations.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command.
    
    Args:
        message: User message
        state: FSM state
    """
    await state.clear()
    
    welcome_text = (
        "👋 Welcome to *Uh Bot* - Your Document Analysis Assistant!\n\n"
        "I can analyze documents (PDF, DOCX, ZIP archives) using AI.\n\n"
        "📄 *How to use:*\n"
        "1. Upload a document (PDF, DOCX, or ZIP archive)\n"
        "2. I'll analyze it using advanced AI\n"
        "3. Get insights, summaries, or custom analysis\n\n"
        "📋 Supported formats: PDF, DOCX, TXT, ZIP\n"
        "📦 Max file size: 20 MB\n\n"
        "💡 Tip: You can upload a ZIP with multiple documents at once!\n"
        "Use /help for more information."
    )
    
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} started bot")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command.
    
    Args:
        message: User message
    """
    help_text = (
        "🤖 *Uh Bot Help*\n\n"
        "*Available Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this message\n\n"
        "*Features:*\n"
        "✨ PDF Analysis - Extract and analyze PDF documents\n"
        "✨ Word Documents - Process DOCX files\n"
        "✨ ZIP Archives - Handle multiple files at once\n"
        "✨ AI Analysis - Powered by GPT-4o/GPT-5\n"
        "✨ Smart Summarization - Get key points quickly\n\n"
        "*How to analyze:*\n"
        "1. Simply upload a file\n"
        "2. Wait for processing\n"
        "3. Get your analysis!\n\n"
        "*Tips:*\n"
        "📌 For long documents, I'll split results across messages\n"
        "📌 Very long results will be sent as Word files\n"
        "📌 ZIP archives can contain up to 500 files\n\n"
        "*Privacy:* Your files are processed securely and deleted immediately.\n"
        "No data is stored on our servers."
    )
    
    await message.answer(
        help_text,
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} requested help")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Handle /cancel command to exit current state.
    
    Args:
        message: User message
        state: FSM state
    """
    await state.clear()
    await message.answer(
        "Operation cancelled. Ready for new uploads! 📁",
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} cancelled operation")
