"""Prompt management handlers.

Handles user interactions for managing custom prompts.
Includes menu navigation, creation, editing, and deletion.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.prompts.prompt_manager import PromptManager
from app.states.prompts import PromptStates

logger = logging.getLogger(__name__)

router = Router()
prompt_manager = PromptManager()


# Inline keyboards
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main prompt menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Просмотреть промпты", callback_data="prompts_list")
    builder.button(text="➕ Создать новый", callback_data="prompt_create")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_prompts_list_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard with list of available prompts."""
    prompts = prompt_manager.list_prompts(user_id)
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    builder = InlineKeyboardBuilder()
    
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        is_custom = name in user_prompts
        # Убрали значки, оставили только текст
        button_text = f"{prompt.description[:30]}..."
        builder.button(
            text=button_text,
            callback_data=f"prompt_select_{name}"
        )
    
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_prompt_detail_keyboard(prompt_name: str, is_custom: bool) -> InlineKeyboardMarkup:
    """Keyboard for prompt details."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"prompt_edit_{prompt_name}")
    if is_custom:
        builder.button(text="🗑️ Удалить", callback_data=f"prompt_delete_{prompt_name}")
    builder.button(text="📝 По умолчанию", callback_data=f"prompt_set_default_{prompt_name}")
    builder.button(text="« Назад", callback_data="prompts_list")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_manage_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard for managing prompts."""
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    builder = InlineKeyboardBuilder()
    
    if user_prompts:
        builder.button(text="🗑️ Удалить промпт", callback_data="prompt_delete_menu")
    
    builder.button(text="➕ Создать новый", callback_data="prompt_create")
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


async def start_prompts_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Show prompts menu.
    
    Can be called from menu or /prompts command.
    """
    if state is None:
        logger.error("state is None in start_prompts_mode")
        return
    
    await state.clear()
    
    text = (
        "🎯 *Управление промптами*\n\n"
        "Управляйте своими промптами для анализа. Выберите действие:"
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
        
        # Просто отправляем новое сообщение
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
        "Управляйте своими промптами для анализа. Выберите действие:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )
    await query.answer()


@router.callback_query(F.data == "prompts_list")
async def cb_prompts_list(query: CallbackQuery) -> None:
    """Show list of prompts."""
    user_id = query.from_user.id
    prompts = prompt_manager.list_prompts(user_id)
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    text = (
        f"📝 *Доступные промпты* (всего: {len(prompts)})\n\n"
        f"Выберите промпт для просмотра деталей:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_prompts_list_keyboard(user_id),
    )
    await query.answer()


@router.callback_query(F.data.startswith("prompt_select_"))
async def cb_prompt_select(query: CallbackQuery) -> None:
    """Show prompt details."""
    user_id = query.from_user.id
    prompt_name = query.data.replace("prompt_select_", "")
    
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    if not prompt:
        await query.answer("❌ Промпт не найден")
        return
    
    is_custom = prompt_name in prompt_manager.get_user_prompts(user_id)
    
    text = (
        f"📝 *{prompt.name.upper()}*\n\n"
        f"_{prompt.description}_\n\n"
        f"*Системный промпт:*\n`{prompt.system_prompt[:200]}...`\n\n"
        f"*Промпт пользователя:*\n`{prompt.user_prompt_template[:200]}...`"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_prompt_detail_keyboard(prompt_name, is_custom),
    )
    await query.answer()


@router.callback_query(F.data == "prompt_create")
async def cb_prompt_create(query: CallbackQuery, state: FSMContext) -> None:
    """Start creating new prompt."""
    await state.set_state(PromptStates.entering_name)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 1️⃣ из 3\n\n"
        "Введите имя промпта (например: 'my_analyzer', 'contract_review'):"
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
            "❌ Неверное имя. Должно быть 1-30 символов.\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(prompt_name=name)
    await state.set_state(PromptStates.entering_system_prompt)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 2️⃣ из 3\n\n"
        "Введите *системный промпт* (инструкции для ИИ):\n\n"
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
            "❌ Системный промпт слишком короткий (минимум 10 символов).\n"
            "Попробуйте снова:"
        )
        return
    
    await state.update_data(system_prompt=system_prompt)
    await state.set_state(PromptStates.entering_user_prompt)
    
    text = (
        "➕ *Создать новый промпт*\n\n"
        "Шаг 3️⃣ из 3\n\n"
        "Введите *шаблон промпта пользователя*:\n\n"
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
            "❌ Промпт пользователя слишком короткий (минимум 10 символов).\n"
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
        description=f"Пользовательский промпт: {prompt_name}",
    )
    
    text = (
        f"✅ *Промпт создан!*\n\n"
        f"Имя: `{prompt_name}`\n"
        f"Системный: {system_prompt[:50]}...\n"
        f"Пользовательский: {user_prompt[:50]}...\n\n"
        f"Ваш промпт готов к использованию!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    await state.clear()
    logger.info(f"User {message.from_user.id} created prompt: {prompt_name}")


@router.callback_query(F.data.startswith("prompt_delete_"))
async def cb_prompt_delete(query: CallbackQuery, state: FSMContext) -> None:
    """Delete prompt with confirmation."""
    if query.data == "prompt_delete_menu":
        # Show menu to select which custom prompt to delete
        user_prompts = prompt_manager.get_user_prompts(query.from_user.id)
        
        builder = InlineKeyboardBuilder()
        for name in user_prompts.keys():
            builder.button(
                text=f"🗑️ {name}",
                callback_data=f"prompt_delete_confirm_{name}"
            )
        builder.button(text="« Отмена", callback_data="prompts_manage")
        builder.adjust(2)  # 2 кнопки в ряд
        
        text = "🗑️ *Выберите промпт для удаления:*"
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    else:
        # Confirm deletion
        prompt_name = query.data.replace("prompt_delete_confirm_", "")
        
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✅ Да, удалить",
            callback_data=f"prompt_delete_final_{prompt_name}"
        )
        builder.button(text="❌ Отмена", callback_data="prompts_manage")
        builder.adjust(2)
        
        text = f"⚠️ Удалить '{prompt_name}'? Это нельзя отменить!"
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    
    await query.answer()


@router.callback_query(F.data.startswith("prompt_delete_final_"))
async def cb_prompt_delete_final(query: CallbackQuery) -> None:
    """Final deletion of prompt."""
    prompt_name = query.data.replace("prompt_delete_final_", "")
    
    if prompt_manager.delete_prompt(query.from_user.id, prompt_name):
        text = f"✅ Промпт '{prompt_name}' удалён!"
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="prompts_manage")]]
            ),
        )
        logger.info(f"User {query.from_user.id} deleted prompt: {prompt_name}")
    else:
        await query.answer("❌ Промпт не найден")
    
    await query.answer()


@router.callback_query(F.data.startswith("prompt_edit_"))
async def cb_prompt_edit(query: CallbackQuery, state: FSMContext) -> None:
    """Edit prompt."""
    prompt_name = query.data.replace("prompt_edit_", "")
    prompt = prompt_manager.get_prompt(query.from_user.id, prompt_name)
    
    if not prompt:
        await query.answer("❌ Промпт не найден")
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Системный промпт",
        callback_data=f"prompt_edit_system_{prompt_name}"
    )
    builder.button(
        text="✏️ Промпт пользователя",
        callback_data=f"prompt_edit_user_{prompt_name}"
    )
    builder.button(text="« Назад", callback_data=f"prompt_select_{prompt_name}")
    builder.adjust(2)  # 2 кнопки в ряд
    
    text = f"✏️ *Редактировать промпт: {prompt_name}*\n\nВыберите, что редактировать:"
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup(),
    )
    await query.answer()


@router.callback_query(F.data.startswith("prompt_set_default_"))
async def cb_prompt_set_default(query: CallbackQuery, state: FSMContext) -> None:
    """Set prompt as default for document analysis."""
    prompt_name = query.data.replace("prompt_set_default_", "")
    
    await state.update_data(default_prompt=prompt_name)
    
    text = (
        f"✅ Установлен '{prompt_name}' по умолчанию!\n\n"
        f"Этот промпт будет использоваться для всех будущих анализов документов."
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="prompts_list")]]
        ),
    )
    logger.info(f"User {query.from_user.id} set default prompt: {prompt_name}")
    await query.answer()


@router.callback_query(F.data == "prompts_manage")
async def cb_prompts_manage(query: CallbackQuery) -> None:
    """Show manage prompts menu."""
    user_id = query.from_user.id
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    text = (
        f"⚙️ *Управление промптами*\n\n"
        f"Пользовательские промпты: {len(user_prompts)}\n\n"
        f"Выберите действие:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_manage_keyboard(user_id),
    )
    await query.answer()
