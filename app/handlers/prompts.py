"""Prompt management handlers.

Fixes 2025-12-20 17:32:
- Fixed emoji rendering in buttons and text (unicode escapes cause display issues)
- Show subject name in edit header (e.g., "Математика (math_homework)")
- Fixed "Cancel" button to return to edit options (not prompt detail)
- Improved navigation: Main → Category → Detail → Edit Options → Edit Field → Save → Back to Edit Options → Back to Detail
- All buttons now clear states properly

Fixes 2025-12-20 17:20:
- Removed 'Create new prompt' button from main menu (no custom prompt creation)
- Added 'Back' button to main menu (return to main chat/analysis)
- Only system prompts editable

Fixes 2025-12-20 16:59:
- Fixed green checkmark on ALL prompts (is_custom was always True) - now only shows on user-created prompts
- Fixed 'prompt too short' error after reload - reload prompts before displaying details
- Fixed Telegram markdown parsing error - escape asterisks in text content

Fixes 2025-12-20 16:45:
- Show FULL prompt text when editing (not truncated [:300])
- User now sees complete prompt to edit, not just first 300 characters
- Prevents confusion when editing truncated text

Fixes 2025-12-20 16:32:
- Added 'Back' button after editing prompt (returns to prompt detail screen)
- Fixed save confirmation message - shows what was changed
- Ensured update_prompt actually saves the changes

Handles user interactions for managing system prompts.
Includes menu navigation and editing of existing prompts.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.prompts.prompt_manager import PromptManager
from app.states.prompts import PromptStates

logger = logging.getLogger(__name__)

router = Router()
prompt_manager = PromptManager()


def escape_markdown(text: str) -> str:
    """Escape special markdown characters in text.
    
    Args:
        text: Text to escape
        
    Returns:
        str: Escaped text safe for markdown
    """
    # Escape markdown special characters
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def get_subject_display_name(prompt_name: str) -> str:
    """Get display name for subject prompt.
    
    Examples:
        math_homework -> Математика (math_homework)
        russian_homework -> Русский язык (russian_homework)
    
    Args:
        prompt_name: Prompt identifier
        
    Returns:
        str: Display name with subject
    """
    # Homework subjects mapping
    subjects = {
        "math_homework": "Математика (math_homework)",
        "russian_homework": "Русский язык (russian_homework)",
        "english_homework": "Английский язык (english_homework)",
        "physics_homework": "Физика (physics_homework)",
        "chemistry_homework": "Химия (chemistry_homework)",
        "cs_homework": "Информатика (cs_homework)",
        "geography_homework": "География (geography_homework)",
        "literature_homework": "Литература (literature_homework)",
        # Document analysis
        "default": "Базовый анализ (default)",
        "summarize": "Краткое резюме (summarize)",
        "extract_entities": "Извлечение данных (extract_entities)",
        "risk_analysis": "Анализ рисков (risk_analysis)",
        "legal_review": "Юридическая проверка (legal_review)",
        # Chat
        "chat_system": "Основной диалог (chat_system)",
    }
    return subjects.get(prompt_name, prompt_name)


# Inline keyboards
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main prompt menu keyboard - organized by categories with Back button."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Documents", callback_data="prompts_category_document_analysis")
    builder.button(text="Chat", callback_data="prompts_category_chat")
    builder.button(text="Homework", callback_data="prompts_category_homework")
    builder.button(text="<< Back", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()


def get_category_keyboard(user_id: int, category: str) -> InlineKeyboardMarkup:
    """Keyboard for prompts in specific category."""
    prompts = prompt_manager.get_prompt_by_category(user_id, category)
    
    builder = InlineKeyboardBuilder()
    
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        # Show description (limited length)
        button_text = f"{prompt.description[:35]}"
        builder.button(
            text=button_text,
            callback_data=f"prompt_select_{name}"
        )
    
    builder.button(text="<< Back", callback_data="prompts_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_prompt_detail_keyboard(prompt_name: str) -> InlineKeyboardMarkup:
    """Keyboard for prompt details."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Edit", callback_data=f"prompt_edit_{prompt_name}")
    builder.button(text="<< Back", callback_data="prompts_menu")
    builder.adjust(2)
    return builder.as_markup()


async def start_prompts_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Show prompts menu with instructions."""
    if state is None:
        logger.error("state is None in start_prompts_mode")
        return
    
    await state.clear()
    
    text = (
        "PROMPT MANAGEMENT\n\n"
        "System prompts available:\n"
        "* Documents: 5 prompts for analysis\n"
        "* Chat: 1 main prompt\n"
        "* Homework: 8 subject-specific prompts\n\n"
        "How to use:\n"
        "1. Select category\n"
        "2. Click prompt\n"
        "3. Click 'Edit' to edit\n"
        "4. Edit text\n"
        "5. Click 'Send' to save!\n\n"
        "Select category below:"
    )
    
    if message:
        user_id = message.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await message.answer(
            text,
            parse_mode=None,
            reply_markup=get_main_menu_keyboard(),
        )
        logger.info(f"Prompts mode started for user {user_id}")
    elif callback:
        user_id = callback.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await callback.message.answer(
            text,
            parse_mode=None,
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.answer()
        logger.info(f"Prompts mode started for user {user_id}")


@router.message(Command("prompts"))
async def cmd_prompts(message: Message, state: FSMContext) -> None:
    """Show prompts menu."""
    logger.info(f"User {message.from_user.id} activated /prompts")
    await start_prompts_mode(message=message, state=state)


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(query: CallbackQuery, state: FSMContext) -> None:
    """Back to main menu from prompts."""
    await state.clear()
    
    text = "Returned to main menu."
    
    await query.message.edit_text(
        text,
        parse_mode=None,
        reply_markup=None,
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} returned to main menu from prompts")


@router.callback_query(F.data == "prompts_menu")
async def cb_prompts_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Back to prompts menu."""
    await state.clear()
    
    text = (
        "PROMPT MANAGEMENT\n\n"
        "Select category:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode=None,
        reply_markup=get_main_menu_keyboard(),
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} returned to prompts menu")


@router.callback_query(F.data.startswith("prompts_category_"))
async def cb_prompts_category(query: CallbackQuery) -> None:
    """Show prompts in selected category."""
    user_id = query.from_user.id
    category = query.data.replace("prompts_category_", "")
    
    # Reload prompts to ensure latest data
    prompt_manager.load_user_prompts(user_id)
    prompts = prompt_manager.get_prompt_by_category(user_id, category)
    
    # Get category display name
    category_names = {
        "document_analysis": "DOCUMENTS",
        "chat": "CHAT",
        "homework": "HOMEWORK",
    }
    
    text = (
        f"{category_names.get(category, category)} ({len(prompts)})\n\n"
        f"Click prompt to edit:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode=None,
        reply_markup=get_category_keyboard(user_id, category),
    )
    await query.answer()
    logger.info(f"User {user_id} viewing category: {category}")


@router.callback_query(F.data.startswith("prompt_select_"))
async def cb_prompt_select(query: CallbackQuery) -> None:
    """Show prompt details."""
    user_id = query.from_user.id
    prompt_name = query.data.replace("prompt_select_", "")
    
    # Reload prompts to ensure latest data
    prompt_manager.load_user_prompts(user_id)
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    
    if not prompt:
        await query.answer("Prompt not found")
        return
    
    # Check if this is user-customized or system default
    user_prompts = prompt_manager.get_user_prompts(user_id)
    is_custom = prompt_name in user_prompts
    
    # Get subject display name
    subject_name = get_subject_display_name(prompt_name)
    
    # Escape markdown in prompts to avoid parsing errors
    system_escaped = escape_markdown(prompt.system_prompt[:200])
    user_escaped = escape_markdown(prompt.user_prompt_template[:200])
    
    # Show type badge
    type_badge = "[YOUR]" if is_custom else "[SYSTEM]"
    
    text = (
        f"PROMPT DETAILS\n"
        f"{subject_name}\n"
        f"{type_badge}\n"
        f"{prompt.description}\n\n"
        f"System prompt:\n{system_escaped}...\n\n"
        f"Template:\n{user_escaped}...\n\n"
        f"What do you want to do?"
    )
    
    await query.message.edit_text(
        text,
        parse_mode=None,
        reply_markup=get_prompt_detail_keyboard(prompt_name),
    )
    await query.answer()
    logger.info(f"User {user_id} viewing prompt details: {prompt_name}")


@router.callback_query(F.data.startswith("prompt_edit_"))
async def cb_prompt_edit(query: CallbackQuery, state: FSMContext) -> None:
    """Edit prompt - show options."""
    # Extract prompt name (handle both prompt_edit_X and prompt_edit_system_X/prompt_edit_user_X)
    if query.data.startswith("prompt_edit_system_"):
        prompt_name = query.data.replace("prompt_edit_system_", "")
        edit_type = "system"
    elif query.data.startswith("prompt_edit_user_"):
        prompt_name = query.data.replace("prompt_edit_user_", "")
        edit_type = "user"
    else:
        prompt_name = query.data.replace("prompt_edit_", "")
        edit_type = None
    
    # Reload prompts to ensure latest data
    prompt_manager.load_user_prompts(query.from_user.id)
    prompt = prompt_manager.get_prompt(query.from_user.id, prompt_name)
    
    if not prompt:
        await query.answer("Prompt not found")
        return
    
    # If edit_type is specified, show input prompt
    if edit_type:
        await state.update_data(editing_prompt=prompt_name, edit_field=edit_type)
        
        # Get subject display name
        subject_name = get_subject_display_name(prompt_name)
        
        if edit_type == "system":
            await state.set_state(PromptStates.editing_system)
            # Show FULL text - no truncation!
            text = (
                f"EDIT: {subject_name}\n\n"
                f"Current system prompt:\n{prompt.system_prompt}\n\n"
                f"Enter new text for system prompt:"
            )
        else:  # user
            await state.set_state(PromptStates.editing_user)
            # Show FULL text - no truncation!
            text = (
                f"EDIT: {subject_name}\n\n"
                f"Current template:\n{prompt.user_prompt_template}\n\n"
                f"Enter new template text:"
            )
        
        # Cancel button returns to EDIT OPTIONS (not detail)
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Cancel",
            callback_data=f"prompt_edit_{prompt_name}"
        )
        
        await query.message.edit_text(
            text,
            parse_mode=None,
            reply_markup=builder.as_markup(),
        )
    else:
        # Show edit options
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Edit System Prompt",
            callback_data=f"prompt_edit_system_{prompt_name}"
        )
        builder.button(
            text="Edit Template",
            callback_data=f"prompt_edit_user_{prompt_name}"
        )
        builder.button(
            text="<< Back",
            callback_data=f"prompt_select_{prompt_name}"
        )
        builder.adjust(2)
        
        # Get subject display name
        subject_name = get_subject_display_name(prompt_name)
        
        text = (
            f"EDIT: {subject_name}\n\n"
            f"What do you want to edit?"
        )
        
        await query.message.edit_text(
            text,
            parse_mode=None,
            reply_markup=builder.as_markup(),
        )
    
    await query.answer()
    logger.info(f"User {query.from_user.id} starting to edit: {prompt_name}")


@router.message(PromptStates.editing_system)
async def msg_edit_system(message: Message, state: FSMContext) -> None:
    """Save edited system prompt."""
    new_system = message.text
    
    if not new_system or len(new_system) < 10:
        await message.answer(
            "Text is too short.\nTry again:"
        )
        return
    
    data = await state.get_data()
    prompt_name = data["editing_prompt"]
    
    # Update prompt
    prompt_manager.update_prompt(
        user_id=message.from_user.id,
        prompt_name=prompt_name,
        system_prompt=new_system,
    )
    
    # Escape markdown for display
    display_text = escape_markdown(new_system[:100])
    
    # Get subject display name
    subject_name = get_subject_display_name(prompt_name)
    
    # Show success with back button to EDIT OPTIONS (not detail)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="<< Back to Edit Options",
        callback_data=f"prompt_edit_{prompt_name}"
    )
    
    await message.answer(
        f"SAVED!\n\n"
        f"Updated: {subject_name}\n"
        f"Text: {display_text}...",
        parse_mode=None,
        reply_markup=builder.as_markup(),
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} edited system prompt: {prompt_name}")


@router.message(PromptStates.editing_user)
async def msg_edit_user(message: Message, state: FSMContext) -> None:
    """Save edited user prompt template."""
    new_user = message.text
    
    if not new_user or len(new_user) < 10:
        await message.answer(
            "Text is too short.\nTry again:"
        )
        return
    
    data = await state.get_data()
    prompt_name = data["editing_prompt"]
    
    # Update prompt
    prompt_manager.update_prompt(
        user_id=message.from_user.id,
        prompt_name=prompt_name,
        user_prompt_template=new_user,
    )
    
    # Escape markdown for display
    display_text = escape_markdown(new_user[:100])
    
    # Get subject display name
    subject_name = get_subject_display_name(prompt_name)
    
    # Show success with back button to EDIT OPTIONS (not detail)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="<< Back to Edit Options",
        callback_data=f"prompt_edit_{prompt_name}"
    )
    
    await message.answer(
        f"SAVED!\n\n"
        f"Updated: {subject_name}\n"
        f"Text: {display_text}...",
        parse_mode=None,
        reply_markup=builder.as_markup(),
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} edited user prompt: {prompt_name}")
