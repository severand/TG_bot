"""Main entry point for Uh Bot.

Starts the Telegram bot polling and handles graceful shutdown.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Dispatcher

from app.bot import create_bot, create_dispatcher, setup_bot_commands
from app.config import get_settings
from app.handlers import common, documents, prompts

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main bot entry point.
    
    Initializes configuration, creates bot and dispatcher,
    registers handlers, and starts polling.
    
    Raises:
        ValueError: If required environment variables are missing
    """
    logger.info("Starting Uh Bot...")
    
    # Load configuration
    try:
        config = get_settings()
        logger.info(f"Configuration loaded (model: {config.OPENAI_MODEL})")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Create temp directory
    temp_dir = Path(config.TEMP_DIR)
    temp_dir.mkdir(exist_ok=True)
    logger.info(f"Temp directory: {temp_dir}")
    
    # Create data directory for prompts
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    logger.info(f"Data directory: {data_dir}")
    
    # Create bot and dispatcher
    try:
        bot = create_bot(config.TG_BOT_TOKEN)
        dispatcher = create_dispatcher()
        logger.info("Bot and dispatcher created")
    except Exception as e:
        logger.error(f"Failed to create bot: {e}")
        sys.exit(1)
    
    # Setup bot commands
    try:
        await setup_bot_commands(bot)
    except Exception as e:
        logger.warning(f"Failed to setup bot commands: {e}")
    
    # Register handlers
    dispatcher.include_router(common.router)
    dispatcher.include_router(documents.router)
    dispatcher.include_router(prompts.router)
    logger.info("Handlers registered")
    
    # Start polling
    logger.info("Bot polling started...")
    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    # Run bot
    asyncio.run(main())
