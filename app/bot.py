"""Bot core module.

Initializes Aiogram bot, dispatcher, and router.
Handles middleware registration and plugin loading.
"""

import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="👋 Запустить бота"),
        BotCommand(command="chat", description="💬 Режим диалога"),
        BotCommand(command="analyze", description="📊 Анализ документов"),
        BotCommand(command="homework", description="📚 Проверка домашки"),
        BotCommand(command="prompts", description="🎯 Управление промптами"),
        BotCommand(command="rag", description="🧠 RAG База знаний"),  # ДОБАВЬ ЭТУ СТРОКУ
        BotCommand(command="help", description="❓ Справка"),
    ]



def create_bot(token: str) -> Bot:
    """Create and return bot instance.
    
    Args:
        token: Telegram bot token
        
    Returns:
        Bot: Initialized bot instance
    """
    bot = Bot(token=token)
    logger.info("Bot instance created")
    return bot


def create_dispatcher() -> Dispatcher:
    """Create and return dispatcher instance.
    
    Returns:
        Dispatcher: Initialized dispatcher with memory storage
    """
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    logger.info("Dispatcher created with memory storage")
    return dispatcher


def create_router() -> Router:
    """Create router for handlers.
    
    Returns:
        Router: Initialized router
    """
    router = Router()
    logger.info("Router created")
    return router
