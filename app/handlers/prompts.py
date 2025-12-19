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
from app.utils.menu import MenuManager

logger = logging.getLogger(__name__)

router = Router()
prompt_manager = PromptManager()


# Inline keyboards
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main prompt menu keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 View Prompts", callback_data="prompts_list")
    builder.button(text="➕ Create New", callback_data="prompt_create")
    builder.button(text="⚙️ Manage", callback_data="prompts_manage")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_prompts_list_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard with list of available prompts."""
    prompts = prompt_manager.list_prompts(user_id)
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    builder = InlineKeyboardBuilder()
    
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        is_custom = name in user_prompts
        icon = "✨" if is_custom else "📌"
        button_text = f"{icon} {name}: {prompt.description[:20]}..."
        builder.button(
            text=button_text,
            callback_data=f"prompt_select_{name}"
        )
    
    builder.button(text="« Back", callback_data="prompts_menu")
    builder.adjust(1)
    return builder.as_markup()


def get_prompt_detail_keyboard(prompt_name: str, is_custom: bool) -> InlineKeyboardMarkup:
    """Keyboard for prompt details."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data=f"prompt_edit_{prompt_name}")
    if is_custom:
        builder.button(text="🗑️ Delete", callback_data=f"prompt_delete_{prompt_name}")
    builder.button(text="📝 Use as Default", callback_data=f"prompt_set_default_{prompt_name}")
    builder.button(text="« Back", callback_data="prompts_list")
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_manage_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Keyboard for managing prompts."""
    user_prompts = prompt_manager.get_user_prompts(user_id)
    
    builder = InlineKeyboardBuilder()
    
    if user_prompts:
        builder.button(text="🗑️ Delete Custom Prompt", callback_data="prompt_delete_menu")
    
    builder.button(text="➕ Create New", callback_data="prompt_create")
    builder.button(text="💾 Export All", callback_data="prompt_export")
    builder.button(text="« Back", callback_data="prompts_menu")
    builder.adjust(1)
    return builder.as_markup()


async def start_prompts_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Show prompts menu.
    
    Can be called from menu or /prompts command.
    """
    if state is None:
        logger.error("state is None in start_prompts_mode")
        return
    
    await state.clear()
    
    if message:
        user_id = message.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        text = (
            "🎯 *Prompt Management*\n\n"
            "Manage your custom analysis prompts. Choose an option:"
        )
        
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
    elif callback:
        user_id = callback.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        text = (
            "🎯 *Prompt Management*\n\n"
            "Manage your custom analysis prompts. Choose an option:"
        )
        
        await MenuManager.navigate(
            callback=callback,
            state=state,
            text=text,
            keyboard=get_main_menu_keyboard(),
            new_state=None,
            screen_code="prompts_menu",
            preserve_data=True,
        )
    
    logger.info(f"Prompts mode started")


@router.message(Command("prompts"))
async def cmd_prompts(message: Message, state: FSMContext) -> None:
    """Show prompts menu."""
    await start_prompts_mode(message=message, state=state)


@router.callback_query(F.data == "prompts_menu")
async def cb_prompts_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Back to prompts menu."""
    await state.clear()
    
    text = (
        "🎯 *Prompt Management*\n\n"
        "Manage your custom analysis prompts. Choose an option:"
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
        f"📋 *Available Prompts* ({len(prompts)} total)\n\n"
        f"✨ = Custom prompts\n"
        f"📌 = Default prompts\n\n"
        f"Select a prompt to view details:"
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
        await query.answer("❌ Prompt not found")
        return
    
    is_custom = prompt_name in prompt_manager.get_user_prompts(user_id)
    
    text = (
        f"{'\u2728' if is_custom else '\ud83d\udccc'} *{prompt.name.upper()}*\n\n"
        f"_{prompt.description}_\n\n"
        f"*System Prompt:*\n`{prompt.system_prompt[:200]}...`\n\n"
        f"*User Prompt:*\n`{prompt.user_prompt_template[:200]}...`"
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
        "➕ *Create New Prompt*\n\n"
        "Step 1️⃣ of 3\n\n"
        "Enter a name for your prompt (e.g., 'my_analyzer', 'contract_review'):"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Cancel", callback_data="prompts_menu")]]
        ),
    )
    await query.answer()


@router.message(PromptStates.entering_name)
async def msg_prompt_name(message: Message, state: FSMContext) -> None:
    """Save prompt name and ask for system prompt."""
    name = message.text.strip().lower().replace(" ", "_")
    
    if not name or len(name) > 30:
        await message.answer(
            "❌ Invalid name. Must be 1-30 characters.\n"
            "Try again:"
        )
        return
    
    await state.update_data(prompt_name=name)
    await state.set_state(PromptStates.entering_system_prompt)
    
    text = (
        "➕ *Create New Prompt*\n\n"
        "Step 2️⃣ of 3\n\n"
        "Enter the *system prompt* (instructions for AI):\n\n"
        "_Example:_ 'You are a legal expert. Review contracts carefully.'"
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
            "❌ System prompt too short (min 10 chars).\n"
            "Try again:"
        )
        return
    
    await state.update_data(system_prompt=system_prompt)
    await state.set_state(PromptStates.entering_user_prompt)
    
    text = (
        "➕ *Create New Prompt*\n\n"
        "Step 3️⃣ of 3\n\n"
        "Enter the *user prompt template*:\n\n"
        "_Example:_ 'Analyze this contract and identify risks:'"
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
            "❌ User prompt too short (min 10 chars).\n"
            "Try again:"
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
        description=f"Custom prompt: {prompt_name}",
    )
    
    text = (
        f"✅ *Prompt Created!*\n\n"
        f"Name: `{prompt_name}`\n"
        f"System: {system_prompt[:50]}...\n"
        f"User: {user_prompt[:50]}...\n\n"
        f"Your prompt is ready to use!"
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
        builder.button(text="« Cancel", callback_data="prompts_manage")
        builder.adjust(1)
        
        text = "🗑️ *Select prompt to delete:*"
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
            text="✅ Yes, Delete",
            callback_data=f"prompt_delete_final_{prompt_name}"
        )
        builder.button(text="❌ Cancel", callback_data="prompts_manage")
        builder.adjust(2)
        
        text = f"⚠️ Delete '{prompt_name}'? This cannot be undone!"
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
        text = f"✅ Prompt '{prompt_name}' deleted!"
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="« Back", callback_data="prompts_manage")]]
            ),
        )
        logger.info(f"User {query.from_user.id} deleted prompt: {prompt_name}")
    else:
        await query.answer("❌ Prompt not found")
    
    await query.answer()


@router.callback_query(F.data.startswith("prompt_edit_"))
async def cb_prompt_edit(query: CallbackQuery, state: FSMContext) -> None:
    """Edit prompt."""
    prompt_name = query.data.replace("prompt_edit_", "")
    prompt = prompt_manager.get_prompt(query.from_user.id, prompt_name)
    
    if not prompt:
        await query.answer("❌ Prompt not found")
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Edit System Prompt",
        callback_data=f"prompt_edit_system_{prompt_name}"
    )
    builder.button(
        text="✏️ Edit User Prompt",
        callback_data=f"prompt_edit_user_{prompt_name}"
    )
    builder.button(text="« Back", callback_data=f"prompt_select_{prompt_name}")
    builder.adjust(1)
    
    text = f"✏️ *Edit Prompt: {prompt_name}*\n\nChoose what to edit:"
    
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
        f"✅ Set '{prompt_name}' as default!\n\n"
        f"This prompt will be used for all future document analyses."
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="« Back", callback_data="prompts_list")]]
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
        f"⚙️ *Manage Prompts*\n\n"
        f"Custom prompts: {len(user_prompts)}\n\n"
        f"Choose an action:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_manage_keyboard(user_id),
    )
    await query.answer()
