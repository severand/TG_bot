"""Common handlers for start, help, and navigation.

Provides welcome message and general help.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.localization import ru

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Start command. Show welcome message."""
    await state.clear()
    
    # Build main menu
    builder = InlineKeyboardBuilder()
    builder.button(text=ru.BTN_CHAT, callback_data="mode_chat")
    builder.button(text=ru.BTN_ANALYZE, callback_data="mode_analyze")
    builder.button(text=ru.BTN_VIEW_PROMPTS_MENU, callback_data="mode_prompts_menu")
    builder.adjust(2, 1)
    
    text = f"{ru.WELCOME_TITLE}\n\n{ru.WELCOME_TEXT}"
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup(),
    )
    logger.info(f"User {message.from_user.id} started bot")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Help command. Show available commands."""
    text = f"{ru.HELP_TITLE}\n\n{ru.HELP_TEXT}"
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} requested help")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel command. Exit current mode."""
    await state.clear()
    
    text = (
        "❌ Отменено.\n\n"
        "Вы можете начать снова с /start"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} cancelled operation")


@router.callback_query(F.data == "mode_chat")
async def cb_mode_chat(query, state: FSMContext) -> None:
    """Switch to chat mode."""
    # Let chat handler take over
    # Send /chat command
    await query.answer()
    # Create fake message to trigger chat handler
    # Actually just redirect to start chat
    from aiogram.types import User
    
    # Create a message that looks like /chat command
    fake_message = Message(
        message_id=query.message.message_id,
        date=query.message.date,
        chat=query.message.chat,
        from_user=query.from_user,
        text="/chat",
    )
    
    # Import and call chat handler
    from app.handlers.chat import cmd_chat
    await cmd_chat(fake_message, state)


@router.callback_query(F.data == "mode_analyze")
async def cb_mode_analyze(query, state: FSMContext) -> None:
    """Switch to analyze mode."""
    await query.answer()
    
    # Create fake message for analyze handler
    fake_message = Message(
        message_id=query.message.message_id,
        date=query.message.date,
        chat=query.message.chat,
        from_user=query.from_user,
        text="/analyze",
    )
    
    from app.handlers.conversation import cmd_analyze
    await cmd_analyze(fake_message, state)


@router.callback_query(F.data == "mode_prompts_menu")
async def cb_mode_prompts(query, state: FSMContext) -> None:
    """Switch to prompts mode."""
    await query.answer()
    
    # Create fake message for prompts handler
    fake_message = Message(
        message_id=query.message.message_id,
        date=query.message.date,
        chat=query.message.chat,
        from_user=query.from_user,
        text="/prompts",
    )
    
    from app.handlers.prompts import cmd_prompts
    await cmd_prompts(fake_message, state)
