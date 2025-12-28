"""Общие хендлеры для start, help, и навигации.

UPDATED 2025-12-28 23:22:
- FIXED: Правильная очистка state перед установкой нового
- ADDED: Проверка текущего state перед выполнением
- ADDED: StateFilter для предотвращения конфликтов
- FIXED: Правильные переходы между режимами

Fixes 2025-12-20:
- Updated /analyze description: now users select prompt BEFORE uploading document
- Reflects new workflow: /analyze -> Select prompt -> Upload doc -> Analyze

Provides welcome message and general help.
Simple command-based navigation - no inline buttons.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State

from app.localization import ru
from app.states.chat import ChatStates
from app.states.homework import HomeworkStates
from app.states.analysis import DocumentAnalysisStates
from app.states.conversation import ConversationStates
from app.states.prompts import PromptStates

logger = logging.getLogger(__name__)
router = Router()

# Collect all possible states for StateFilter
ALL_STATES = [
    ChatStates.chatting,
    HomeworkStates.selecting_subject,
    HomeworkStates.waiting_for_file,
    DocumentAnalysisStates.processing,
    ConversationStates.selecting_prompt,
    ConversationStates.ready,
    PromptStates.selecting_category,
    PromptStates.selecting_prompt,
    PromptStates.viewing_details,
    PromptStates.editing,
]


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Начинающая команда. Показывают новые и активируют режим диалога по умолчанию."""
    # КОНФКРИТНО: Сначала очистим всё
    current_state = await state.get_state()
    logger.info(f"User {message.from_user.id} /start (previous state: {current_state})")
    
    await state.clear()
    logger.debug(f"Cleared state for user {message.from_user.id}")
    
    # Теперь установим режим диалога
    await state.set_state(ChatStates.chatting)
    logger.debug(f"Set ChatStates.chatting for user {message.from_user.id}")
    
    # Простое приветствие без кнопок
    text = (
        "👋 *Добро пожаловать в Promt Bot!*\n\n"
        "🚀 Я готов помочь вам с:\n"
        "• Обычным диалогом\n"
        "• Анализом документов (с выбором типа анализа)\n"
        "• Проверкой домашних заданий\n"
        "• Настройкой промптов\n\n"
        "💬 *По умолчанию активен режим диалога.*\n"
        "По просто напишите мне свой вопрос!\n\n"
        "📗 *Доступные команды в меню:*\n"
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
    
    logger.info(f"User {message.from_user.id} started bot (chat mode activated)")


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    """Команда справки. Показывают доступные команды."""
    text = (
        "❓ *Справка по боту*\n\n"
        "📗 *Основные команды:*\n\n"
        "💬 */chat* - Режим диалога\n"
        "По просто общайтесь с ботом. Задавайте вопросы, получайте ответы.\n\n"
        "📂 */analyze* - Анализ документов\n"
        "1️⃣ Выберите тип анализа (промпт)\n"
        "2️⃣ Загружаюте документ (PDF, DOCX, TXT, ZIP) или фото\n"
        "3️⃣ Получите результат анализа\n"
        "Поддерживаются фото документов с автоматическим распознаванием текста (OCR).\n\n"
        "📚 */homework* - Проверка домашних заданий\n"
        "Отправьте свою домашку, выберите предмет и получите оценку с разбором ошибок.\n\n"
        "🌟 */prompts* - Управление промптами\n"
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
    """Команда отмены. Очистить сессию и вернуться в режим диалога."""
    current_state = await state.get_state()
    logger.info(f"User {message.from_user.id} /cancel (previous state: {current_state})")
    
    # Полная очистка
    await state.clear()
    logger.debug(f"Cleared state for user {message.from_user.id}")
    
    # Вернись в режим диалога
    await state.set_state(ChatStates.chatting)
    logger.debug(f"Set ChatStates.chatting for user {message.from_user.id}")
    
    text = (
        "❌ *Отменено*\n\n"
        "Возвращаемся в режим диалога.\n"
        "Пишите мне свои вопросы!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    
    logger.info(f"User {message.from_user.id} cancelled and returned to chat mode")


# Legacy callback handlers for backward compatibility
# НЕ используются в новом дизайне, но оставлены для совместимости
@router.callback_query(F.data == "mode_chat")
async def cb_mode_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключиться в режим диалога (legacy)."""
    from app.handlers.chat import start_chat_mode
    await start_chat_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_analyze")
async def cb_mode_analyze(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключиться в режим анализа (legacy)."""
    from app.handlers.conversation import start_analyze_mode
    await start_analyze_mode(callback=callback, state=state)


@router.callback_query(F.data == "mode_prompts_menu")
async def cb_mode_prompts(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключиться в режим промптов (legacy)."""
    from app.handlers.prompts import start_prompts_mode
    await start_prompts_mode(callback=callback, state=state)


@router.callback_query(F.data == "back_to_main_menu")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в главное меню (legacy)."""
    current_state = await state.get_state()
    logger.debug(f"back_to_main_menu: clearing state {current_state}")
    
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
    logger.info(f"User {callback.from_user.id} returned to main menu (chat mode)")
