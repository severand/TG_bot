"""Prompt management handlers.

Fixes 2025-12-20 17:08:
- Unified prompt menu showing all 3 categories: Document Analysis, Chat, Homework
- Each category shows prompts with edit/default status
- All prompts editable through same interface
- Chat and homework prompts now manageable via /prompts
- Organized by category in main menu

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

Handles user interactions for managing custom prompts.
Includes menu navigation, creation, editing, and deletion.
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


# Inline keyboards
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main prompt menu keyboard - organized by categories."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Документы", callback_data="prompts_category_document_analysis")
    builder.button(text="💬 Диалог", callback_data="prompts_category_chat")
    builder.button(text="📖 Домашка", callback_data="prompts_category_homework")
    builder.button(text="➕ Новый промпт", callback_data="prompt_create")
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
    
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_prompt_detail_keyboard(prompt_name: str, is_editable: bool) -> InlineKeyboardMarkup:
    """Keyboard for prompt details."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"prompt_edit_{prompt_name}")
    # Only allow custom prompts to be deleted
    # System prompts can be reset to default by re-editing
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)
    return builder.as_markup()


async def start_prompts_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Show prompts menu with instructions."""
    if state is None:
        logger.error("state is None in start_prompts_mode")
        return
    
    await state.clear()
    
    text = (
        "🎯 *Управление промптами*\n\n"
        "💡 *Новое:* Теперь вы можете редактировать \*все\* промпты:\n"
        "• Документы для анализа\n"
        "• Промпт для диалога\n"
        "• Промпт для проверки домашки\n\n"
        "📝 *Как работать:*\n"
        "1️⃣ Выберите категорию (документы, диалог, домашка)\n"
        "2️⃣ Выберите промпт из списка\n"
        "3️⃣ Открыте редактор и измените текст\n"
        "4️⃣ Сохранится автоматически!\n\n"
        "🎯 *Базовые промпты* \- НЕ могут быть удалены, но могут быть \*отредактированы\*\n\n"
        "👇 Выберите категорию:"
    )
    
    if message:
        user_id = message.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        logger.info(f"Prompts mode started for user {user_id}")
    elif callback:
        user_id = callback.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.answer()
        logger.info(f"Prompts mode started for user {user_id}")


@router.message(Command("prompts"))
async def cmd_prompts(message: Message, state: FSMContext) -> None:
    """Show prompts menu."""
    logger.info(f"User {message.from_user.id} activated /prompts")
    await start_prompts_mode(message=message, state=state)


@router.callback_query(F.data == "prompts_menu")
async def cb_prompts_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Back to prompts menu."""
    await state.clear()
    
    text = (
        "🎯 *Управление промптами*\n\n"
        "👇 Выберите категорию:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )
    await query.answer()


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
        "document_analysis": "📄 Документы",
        "chat": "💬 Диалог",
        "homework": "📖 Домашка",
    }
    
    text = (
        f"{category_names.get(category, category)} *\({len(prompts)})\*\n\n"
        f"👉 Нажмите на промпт чтобы редактировать:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_category_keyboard(user_id, category),
    )
    await query.answer()


@router.callback_query(F.data.startswith("prompt_select_"))
async def cb_prompt_select(query: CallbackQuery) -> None:
    """Show prompt details."""
    user_id = query.from_user.id
    prompt_name = query.data.replace("prompt_select_", "")
    
    # Reload prompts to ensure latest data
    prompt_manager.load_user_prompts(user_id)
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    
    if not prompt:
        await query.answer("❌ Промпт не найден")
        return
    
    # Check if this is user-created or system default
    user_prompts = prompt_manager.get_user_prompts(user_id)
    is_custom = prompt_name in user_prompts
    
    # Escape markdown in prompts to avoid parsing errors
    system_escaped = escape_markdown(prompt.system_prompt[:200])
    user_escaped = escape_markdown(prompt.user_prompt_template[:200])
    
    # Show type badge
    type_badge = "👤 Ваш" if is_custom else "🔖 Системный"
    
    text = (
        f"🎯 *{prompt.name.upper()}*\n"
        f"{type_badge}\n"
        f"_{prompt.description}_\n\n"
        f"*Системный промпт:*\n`{system_escaped}...`\n\n"
        f"*Темплейт:*\n`{user_escaped}...`\n\n"
        f"👇 Что хотите сделать?"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_prompt_detail_keyboard(prompt_name, is_custom),
    )
    await query.answer()


@router.callback_query(F.data == "prompt_create")
async def cb_prompt_create(query: CallbackQuery, state: FSMContext) -> None:
    """Start creating new custom prompt."""
    await state.set_state(PromptStates.entering_name)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 1️⃣ из 3\n\n"
        "Введите имя промпта \(например: 'my_analyzer', 'contract_review'):"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data="prompts_menu")]]
        ),
    )
    await query.answer()


@router.message(PromptStates.entering_name)
async def msg_prompt_name(message: Message, state: FSMContext) -> None:
    """Save prompt name and ask for system prompt."""
    name = message.text.strip().lower().replace(" ", "_")
    
    if not name or len(name) > 30:
        await message.answer(
            "❌ Неверное имя. Должно быть 1\-30 символов.\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(prompt_name=name)
    await state.set_state(PromptStates.entering_system_prompt)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 2️⃣ из 3\n\n"
        "Введите *системный промпт* \(инструкции для ИИ):\n\n"
        "_Пример:_ 'Ты юридический эксперт. Внимательно проверяй договора.'"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    logger.debug(f"User {message.from_user.id} creating prompt: {name}")


@router.message(PromptStates.entering_system_prompt)
async def msg_system_prompt(message: Message, state: FSMContext) -> None:
    """Save system prompt and ask for user prompt."""
    system_prompt = message.text
    
    if not system_prompt or len(system_prompt) < 10:
        await message.answer(
            "❌ Системный промпт слишком короткий \(минимум 10 символов).\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(system_prompt=system_prompt)
    await state.set_state(PromptStates.entering_user_prompt)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 3️⃣ из 3\n\n"
        "Введите *темплейт для установки по умолчанию*:\n\n"
        "_Пример:_ 'Проанализируй этот договор и выяви риски:'"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )


@router.message(PromptStates.entering_user_prompt)
async def msg_user_prompt(message: Message, state: FSMContext) -> None:
    """Save user prompt and finalize creation."""
    user_prompt = message.text
    
    if not user_prompt or len(user_prompt) < 10:
        await message.answer(
            "❌ Темплейт слишком короткий \(минимум 10 символов).\n"
            "Попробуйте снова:"
        )
        return
    
    data = await state.get_data()
    prompt_name = data["prompt_name"]
    system_prompt = data["system_prompt"]
    
    # Save prompt
    prompt_manager.save_prompt(
        user_id=message.from_user.id,
        prompt_name=prompt_name,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt,
        description=f"👤 {prompt_name}",
    )
    
    text = (
        f"✅ *Промпт создан!*\n\n"
        f"Имя: `{prompt_name}`\n"
        f"Ваш промпт готов к использованию!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} created prompt: {prompt_name}")


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
        await query.answer("❌ Промпт не найден")
        return
    
    # If edit_type is specified, show input prompt
    if edit_type:
        await state.update_data(editing_prompt=prompt_name, edit_field=edit_type)
        
        if edit_type == "system":
            await state.set_state(PromptStates.editing_system)
            # Show FULL text - no truncation!
            text = (
                f"✏️ *Редактировать: {prompt_name}*\n\n"
                f"Текущий системный промпт:\n`{prompt.system_prompt}`\n\n"
                f"Введите новый текст для системного промпта:"
            )
        else:  # user
            await state.set_state(PromptStates.editing_user)
            # Show FULL text - no truncation!
            text = (
                f"✏️ *Редактировать: {prompt_name}*\n\n"
                f"Текущий темплейт:\n`{prompt.user_prompt_template}`\n\n"
                f"Введите новый темплейт:"
            )
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="« Отмена", callback_data=f"prompt_select_{prompt_name}")]]
            ),
        )
    else:
        # Show edit options
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🖣️ Системный промпт",
            callback_data=f"prompt_edit_system_{prompt_name}"
        )
        builder.button(
            text="🖣️ Темплейт",
            callback_data=f"prompt_edit_user_{prompt_name}"
        )
        builder.button(text="« Назад", callback_data=f"prompt_select_{prompt_name}")
        builder.adjust(2)
        
        text = f"🖣️ *Редактировать: {prompt_name}*\n\nОт чего это?"
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    
    await query.answer()


@router.message(PromptStates.editing_system)
async def msg_edit_system(message: Message, state: FSMContext) -> None:
    """Save edited system prompt."""
    new_system = message.text
    
    if not new_system or len(new_system) < 10:
        await message.answer(
            "❌ Текст слишком короткий.\nПопробуйте снова:"
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
    
    # Show success with back button to prompt detail
    await message.answer(
        f"✅ *Готово!*\n\n"
        f"Обновлен: `{prompt_name}`\n"
        f"Текст: {display_text}...",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Назад к промпту", callback_data=f"prompt_select_{prompt_name}")]]
        ),
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} edited system prompt: {prompt_name}")


@router.message(PromptStates.editing_user)
async def msg_edit_user(message: Message, state: FSMContext) -> None:
    """Save edited user prompt template."""
    new_user = message.text
    
    if not new_user or len(new_user) < 10:
        await message.answer(
            "❌ Текст слишком короткий.\nПопробуйте снова:"
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
    
    # Show success with back button to prompt detail
    await message.answer(
        f"✅ *Готово!*\n\n"
        f"Обновлен: `{prompt_name}`\n"
        f"Текст: {display_text}...",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Назад к промпту", callback_data=f"prompt_select_{prompt_name}")]]
        ),
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} edited user prompt: {prompt_name}")
