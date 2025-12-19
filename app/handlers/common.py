"""Common handlers for start, help, and navigation.

Provides welcome message and general help.
Uses unified menu system with single message editing.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.localization import ru
from app.utils.menu import MenuManager, create_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Start command. Show welcome message with main menu."""
    # Clear old session
    await state.clear()
    
    # Create main menu keyboard (2 buttons per row)
    keyboard = create_keyboard(
        buttons=[
            (ru.BTN_CHAT, "mode_chat"),
            (ru.BTN_ANALYZE, "mode_analyze"),
            (ru.BTN_VIEW_PROMPTS_MENU, "mode_prompts_menu"),
        ],
        rows_per_row=2,
    )
    
    text = f"{ru.WELCOME_TITLE}\n\n{ru.WELCOME_TEXT}"
    
    # Show menu (creates new message and saves menu_message_id)
    await MenuManager.show_menu(
        message=message,
        state=state,
        text=text,
        keyboard=keyboard,
        screen_code="main_menu",
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
    """Cancel command. Clear session and show start menu."""
    # Clear everything
    await state.clear()
    
    # Show start menu again
    keyboard = create_keyboard(
        buttons=[
            (ru.BTN_CHAT, "mode_chat"),
            (ru.BTN_ANALYZE, "mode_analyze"),
            (ru.BTN_VIEW_PROMPTS_MENU, "mode_prompts_menu"),
        ],
        rows_per_row=2,
    )
    
    text = "❌ Отменено.\n\nНачните снова:"
    
    await MenuManager.show_menu(
        message=message,
        state=state,
        text=text,
        keyboard=keyboard,
        screen_code="main_menu",
    )
    
    logger.info(f"User {message.from_user.id} cancelled")


@router.callback_query(F.data == "mode_chat")
async def cb_mode_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to chat mode."""
    # Import chat handler
    from app.handlers.chat import start_chat_mode
    
    # Navigate to chat mode with named parameters
    await start_chat_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_analyze")
async def cb_mode_analyze(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to analyze mode."""
    # Import analyze handler
    from app.handlers.conversation import start_analyze_mode
    
    # Navigate to analyze mode with named parameters
    await start_analyze_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_prompts_menu")
async def cb_mode_prompts(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to prompts mode."""
    # Import prompts handler
    from app.handlers.prompts import start_prompts_mode
    
    # Navigate to prompts mode with named parameters
    await start_prompts_mode(callback=callback, state=state)


@router.callback_query(F.data == "back_to_main_menu")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main menu."""
    keyboard = create_keyboard(
        buttons=[
            (ru.BTN_CHAT, "mode_chat"),
            (ru.BTN_ANALYZE, "mode_analyze"),
            (ru.BTN_VIEW_PROMPTS_MENU, "mode_prompts_menu"),
        ],
        rows_per_row=2,
    )
    
    text = f"{ru.WELCOME_TITLE}\n\n{ru.WELCOME_TEXT}"
    
    # Navigate back to main menu using MenuManager
    await MenuManager.navigate(
        callback=callback,
        state=state,
        text=text,
        keyboard=keyboard,
        new_state=None,
        screen_code="main_menu",
        preserve_data=False,  # Clear dialog state
    )
