"""Common handlers for start, help, and navigation.

Fixes 2025-12-20:
- Updated /analyze description: now users select prompt BEFORE uploading document
- Reflects new workflow: /analyze -> Select prompt -> Upload doc -> Analyze

Provides welcome message and general help.
Simple command-based navigation - no inline buttons.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.localization import ru
from app.states.chat import ChatStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Start command. Show welcome and activate chat mode by default."""
    # Clear old session
    await state.clear()
    
    # Set chat mode as default
   # await state.set_state(ChatStates.chatting)
    
    # Simple welcome text without buttons
    text = (
        "👋 *Добро пожаловать в Promt Bot!*\n\n"
        "🚀 Я готов помочь вам с:\n"
        "• Обычным диалогом\n"
        "• Анализом документов (с выбором типа анализа)\n"
        "• Проверкой домашних заданий\n"
        "• Настройкой промптов\n\n"
        "💬 *По умолчанию активен режим диалога.*\n"
        "Просто напишите мне свой вопрос!\n\n"
        "📝 *Доступные команды в меню:*\n"
        "• /chat - Режим диалога\n"
        "• /analyze - Анализ документов\n"
        "• /homework - Проверка домашки\n"
        "• /prompts - Управление промптами\n"
        "• /help - Справка"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    
    logger.info(f"User {message.from_user.id} started bot (chat mode by default)")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Help command. Show available commands and usage."""
    text = (
        "❓ *Справка по боту*\n\n"
        "📝 *Основные команды:*\n\n"
        "💬 */chat* - Режим диалога\n"
        "Просто общайтесь с ботом. Задавайте вопросы, получайте ответы.\n\n"
        "📊 */analyze* - Анализ документов\n"
        "1️⃣ Выберите тип анализа (промпт)\n"
        "2️⃣ Загрузите документ (PDF, DOCX, TXT, ZIP) или фото\n"
        "3️⃣ Получите результат анализа\n"
        "Поддерживаются фото документов с автоматическим распознаванием текста (OCR).\n\n"
        "📚 */homework* - Проверка домашних заданий\n"
        "Отправьте свою домашку, выберите предмет и получите оценку с разбором ошибок.\n\n"
        "🎯 */prompts* - Управление промптами\n"
        "Создавайте и редактируйте свои промпты для анализа документов.\n\n"
        "❓ */help* - Показать эту справку\n\n"
        "🔑 *Подсказка:*\n"
        "По умолчанию бот в режиме диалога. Просто пишите сообщения!\n"
        "Для других функций используйте команды из меню."
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    logger.info(f"User {message.from_user.id} requested help")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Cancel command. Clear session and return to chat mode."""
    # Clear everything
    await state.clear()
    
    # Return to chat mode
    await state.set_state(ChatStates.chatting)
    
    text = (
        "❌ *Отменено*\n\n"
        "Возвращаемся в режим диалога.\n"
        "Пишите мне свои вопросы!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    
    logger.info(f"User {message.from_user.id} cancelled")


# Keep callback handlers for backward compatibility
# But they're not used in new design
@router.callback_query(F.data == "mode_chat")
async def cb_mode_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to chat mode (legacy)."""
    from app.handlers.chat import start_chat_mode
    await start_chat_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_analyze")
async def cb_mode_analyze(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to analyze mode (legacy)."""
    from app.handlers.conversation import start_analyze_mode
    await start_analyze_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_prompts_menu")
async def cb_mode_prompts(callback: CallbackQuery, state: FSMContext) -> None:
    """Switch to prompts mode (legacy)."""
    from app.handlers.prompts import start_prompts_mode
    await start_prompts_mode(callback=callback, state=state)


@router.callback_query(F.data == "back_to_main_menu")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main menu (legacy)."""
    await state.clear()
    await state.set_state(ChatStates.chatting)
    
    text = (
        "🏠 *Главное меню*\n\n"
        "Режим диалога активен.\n"
        "Пишите мне свои вопросы!\n\n"
        "Используйте команды из меню для других функций."
    )
    
    await callback.message.answer(
        text,
        parse_mode="Markdown",
    )
    await callback.answer()
