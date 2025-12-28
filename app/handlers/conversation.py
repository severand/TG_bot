"""Конверсация модел хандлеры для анализа документов.

POLNAYA PODDERZHKA:
- Word: .docx, .doc
- Excel: .xlsx, .xls  
- PDF
- Text: .txt
- Images: .jpg, .png (OCR - LOCAL TESSERACT)

UPDATED 2025-12-28 23:22:
- FIXED: /analyze now clears state BEFORE setting new state
- ADDED: Better logging for state transitions
- FIXED: Proper cancellation returns to chat mode

UPDATED 2025-12-28 22:56:
- FIXED: Text preview moved to logs ONLY (not displayed to user)
- ADDED: OCR quality check (detects gibberish/handwriting)
- IMPROVED: Better error messages for OCR failures
- FIXED: JPG detection and handling

UPDATED 2025-12-28 22:49:
- ADDED: OCR text preview (first 300 chars) before analysis
- User can see EXACTLY what OCR extracted
- Better UX - no mystery what got recognized

UPDATED 2025-12-28 22:35:
- FIXED: EASYOCR_AVAILABLE variable always defined
- FIXED: Auto-detect Tesseract path on Windows
- Added explicit path configuration for Windows

UPDATED 2025-12-28 21:52:
- REPLACED OCR.space with LOCAL Tesseract (NO SSL issues!)
- Added EasyOCR as fallback if Tesseract not installed
- 100% offline capable - no API calls needed

Handles document analysis and user prompts for interactive conversation.
"""

import logging
import uuid
import os
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, Document, File, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.states.conversation import ConversationStates
from app.states.chat import ChatStates
from app.services.file_processing.converter import FileConverter
from app.services.llm.llm_factory import LLMFactory
from app.services.prompts.prompt_manager import PromptManager
from app.utils.text_splitter import TextSplitter
from app.utils.cleanup import CleanupManager

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()
prompt_manager = PromptManager()
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)

# ============================================================================
# OCR INITIALIZATION - Try to import OCR libraries
# ============================================================================
TESSERACT_AVAILABLE = False
EASYOCR_AVAILABLE = False
_ocr_reader = None

# Try Tesseract first
try:
    import pytesseract
    from PIL import Image
    
    # Windows: Auto-detect Tesseract installation path
    if os.name == 'nt':  # Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                logger.info(f"[OCR] Found Tesseract at: {path}")
                break
    
    # Test if Tesseract actually works
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
    logger.info("[OCR] ✅ Tesseract available - will use LOCAL OCR")
except Exception as e:
    logger.warning(f"[OCR] ⚠️ Tesseract NOT available: {e}")
    TESSERACT_AVAILABLE = False

# Try EasyOCR as fallback
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    logger.info("[OCR] ✅ EasyOCR available as fallback")
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("[OCR] ⚠️ EasyOCR NOT available")

# Final status
if not TESSERACT_AVAILABLE and not EASYOCR_AVAILABLE:
    logger.error("[OCR] ❌ NO OCR ENGINE AVAILABLE!")
    logger.error("[OCR] Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
    logger.error("[OCR] Or run: pip install easyocr")


def _get_prompts_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Получить клавиатуру с ONLY документным анализ промптами - 2 кнопки в строке."""
    # Лоадим промпты пользователя
    prompt_manager.load_user_prompts(user_id)
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО промпты для анализа документов
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    logger.debug(f"User {user_id}: Loading {len(prompts)} DOCUMENT ANALYSIS prompts")
    
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки только для документных промптов
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        button_text = f"{prompt.description[:40]}"
        builder.button(
            text=button_text,
            callback_data=f"analyze_select_prompt_{name}"
        )
    
    # Кнопка отмены
    builder.button(text="« Отмена", callback_data="analyze_cancel")
    builder.adjust(2)  # 2 кнопки в ряду
    
    return builder.as_markup()


@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    """Активировать режим анализа документов.
    
    CRITICAL FIX 2025-12-28 23:22:
    - MUST clear state FIRST, then set new state
    - This prevents conflicts between modes
    """
    current_state = await state.get_state()
    user_id = message.from_user.id
    logger.info(f"User {user_id} /analyze (previous state: {current_state})")
    
    # ОЧЕРЕДНОСТЬ CRITICAL!
    # НЕ Устанавливаем сразу!
    # СНАЧАЛА очистим
    await state.clear()
    logger.debug(f"Cleared all previous states for user {user_id}")
    
    # НЕ ОЧОНЬ Устанавливаем НОВОЕ
    await state.set_state(ConversationStates.selecting_prompt)
    logger.debug(f"Set ConversationStates.selecting_prompt for user {user_id}")
    
    await start_analyze_mode(message=message, state=state)


async def start_analyze_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Начать интерактивный режим анализа документов.
    
    NEW: Показывать выбор промпта В ПЕРВЫХ, то вапросии для документа.
    ТОЛЬКО промпты для анализа документов!
    """
    if state is None:
        logger.error("state is None in start_analyze_mode")
        return
    
    user_id = message.from_user.id if message else callback.from_user.id if callback else None
    
    if not user_id:
        logger.error("Cannot determine user_id")
        return
    
    # Load user prompts
    prompt_manager.load_user_prompts(user_id)
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО промпты для документных промптов
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    await state.set_state(ConversationStates.selecting_prompt)
    
    text = (
        "📓 *Анализ документов*\n\n"
        "Шаг 1 из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов анализа*\n\n"
        "🔙 *ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ:*\n"
        "• Word: .docx, .doc\n"
        "• Excel: .xlsx, .xls\n"
        "• PDF: .pdf\n"
        "• Текст: .txt\n"
        "• Фото: JPG, PNG (OCR)\n"
        "• Архивы: ZIP\n\n"
        "👇 Выберите тип анализа:"
    )
    
    if message:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        logger.info(f"Analysis mode started for user {user_id} with {len(prompts)} document prompts")
    elif callback:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=_get_prompts_keyboard(user_id),
        )
        await callback.answer()
        logger.info(f"Analysis mode started for user {user_id} with {len(prompts)} document prompts")


@router.callback_query(F.data.startswith("analyze_select_prompt_"))
async def cb_select_prompt(query: CallbackQuery, state: FSMContext) -> None:
    """Обработать выбор промпта - перейти в состояние загружки документа."""
    prompt_name = query.data.replace("analyze_select_prompt_", "")
    user_id = query.from_user.id
    
    # Verify prompt exists
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    if not prompt:
        await query.answer("❌ Промпт не найден", show_alert=True)
        return
    
    # Save prompt to state
    await state.update_data(selected_prompt_name=prompt_name)
    
    # Move to document upload state
    await state.set_state(ConversationStates.ready)
    
    logger.info(f"User {user_id} selected prompt: {prompt_name}")
    
    text = (
        f"✅ *Промпт выбран!*\n\n"
        f"📄 *Тип анализа:* `{prompt_name}`\n"
        f"_{prompt.description}_\n\n"
        f"📂 *Шаг 2 из 2:* Отправьте документ\n\n"
        f"🌟 *ПОДДЕРЖИВАЕМЫЕ:*\n"
        f".doc, .docx, .xls, .xlsx, .pdf, .txt, images (OCR), ZIP\n\n"
        f"📁 Отправьте ЛЮБОЙ файл!"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="analyze_back_to_prompts")]]
        ),
    )
    
    await query.answer()


@router.callback_query(F.data == "analyze_back_to_prompts")
async def cb_back_to_prompts(query: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к выбору промпта."""
    user_id = query.from_user.id
    
    # ИСПРАВЛЕНО: Получаем ТОЛЬКО документные промпты
    prompts = prompt_manager.get_prompt_by_category(user_id, "document_analysis")
    
    text = (
        "📓 *Анализ документов*\n\n"
        "Шаг 1 из 2: *Выберите тип анализа*\n\n"
        f"📄 *Доступно: {len(prompts)} промптов*\n\n"
        "🌟 *ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ:*\n"
        ".doc, .docx, .xls, .xlsx, .pdf, .txt, images, ZIP\n\n"
        "👇 Выберите тип анализа:"
    )
    
    await state.set_state(ConversationStates.selecting_prompt)
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=_get_prompts_keyboard(user_id),
    )
    await query.answer()


@router.callback_query(F.data == "analyze_cancel")
async def cb_analyze_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Отменить режим анализа и ВЕРНУТСЯ В ЗАГОВОР.
    
    CRITICAL FIX:
    - Must clear state
    - Must set ChatStates.chatting
    - This is essential for mode switching!
    """
    user_id = query.from_user.id
    logger.info(f"User {user_id} cancelled analyze mode")
    
    # ОЧЕРЕДНОСТЬ CRITICAL!
    # ОЧИстим бывшее состояние
    await state.clear()
    
    # Устанавливаем режим диалога
    await state.set_state(ChatStates.chatting)
    logger.debug(f"Cleared analyze state and set ChatStates.chatting for user {user_id}")
    
    text = "❌ *Отменено*\n\nВозвращаемся в режим диалога."
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
    )
    await query.answer()


# NOTE: All other handlers (handle_document_upload, handle_photo_upload, etc.) are omitted here
# but should remain in the actual file. Only showing the state management fixes for /analyze command
# and cancellation flow which were the core issues.
