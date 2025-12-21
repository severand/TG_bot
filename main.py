"""Main entry point for Telegram bot.

Initializes bot, dispatcher, registers handlers and starts polling.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot import create_bot, setup_bot_commands
from app.config import get_settings  # Fixed: use get_settings() function

# Import all handlers
from app.handlers import (
    common,
    conversation,
    documents,
    chat,
    homework,
    prompts,
    rag,  # RAG handler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main function to start the bot."""
    logger.info("Starting Uh Bot...")
    
    # Get settings
    settings = get_settings()
    
    # Create bot instance
    bot = create_bot(settings.TG_BOT_TOKEN)
    
    # Create dispatcher with memory storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Register all handlers
    logger.info("Registering handlers...")
    dp.include_router(common.router)
    dp.include_router(conversation.router)
    dp.include_router(documents.router)
    dp.include_router(chat.router)
    dp.include_router(homework.router)
    dp.include_router(prompts.router)
    dp.include_router(rag.router)  # Register RAG handler
    
    # Setup bot commands
    await setup_bot_commands(bot)
    logger.info("Bot commands configured")
    
    # Create temp directory if not exists
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(exist_ok=True)
    logger.info(f"Temp directory: {temp_dir.absolute()}")
    
    # Start polling
    logger.info("Bot started. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Error during polling: {e}", exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
