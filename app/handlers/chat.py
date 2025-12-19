"""Chat mode handlers for simple AI conversation.

Allows users to have a normal conversation with AI without
needing to upload documents. Just ask questions or chat normally.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import get_settings
from app.localization import ru
from app.states.chat import ChatStates
from app.services.llm.llm_factory import LLMFactory
from app.utils.text_splitter import TextSplitter

logger = logging.getLogger(__name__)

router = Router()
config = get_settings()
llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,
    openai_api_key=config.OPENAI_API_KEY or None,
    openai_model=config.OPENAI_MODEL,
    replicate_api_token=config.REPLICATE_API_TOKEN or None,
    replicate_model=config.REPLICATE_MODEL,
)


def get_chat_menu() -> InlineKeyboardMarkup:
    """Simple chat menu."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=ru.BTN_CANCEL,
        callback_data="chat_exit",
    )
    return builder.as_markup()


@router.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext) -> None:
    """Start chat mode.
    
    User can have a normal conversation with AI.
    """
    await state.clear()
    await state.set_state(ChatStates.chatting)
    
    text = (
        f"{ru.CHAT_MODE_TITLE}\n\n"
        f"{ru.CHAT_MODE_TEXT}"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_chat_menu(),
    )
    logger.info(f"User {message.from_user.id} started chat mode")


@router.message(ChatStates.chatting, F.text)
async def handle_chat_message(message: Message, state: FSMContext) -> None:
    """Handle user message in chat mode.
    
    Process the message and respond with AI.
    """
    user_message = message.text.strip()
    
    if not user_message:
        await message.answer(ru.CHAT_EMPTY)
        return
    
    # Skip commands
    if user_message.startswith("/"):
        return
    
    # Show processing indicator
    status_msg = await message.answer(ru.CHAT_PROCESSING)
    
    try:
        # Generate response from LLM
        response = await llm_factory.chat(
            user_message=user_message,
            system_prompt=(
                "Помощник для объяснения комплексных тем. "
                "На весь русском. "
                "Будь подробным, будь полным, будь полезным."
            ),
            use_streaming=False,
        )
        
        if not response:
            await message.answer(ru.CHAT_ERROR)
            await status_msg.delete()
            return
        
        # Delete status message
        await status_msg.delete()
        
        # Send response
        splitter = TextSplitter()
        message_count = splitter.count_messages(response)
        
        if message_count <= 3:
            # Send as text messages
            chunks = splitter.split(response)
            for chunk in chunks:
                await message.answer(
                    chunk,
                    parse_mode="Markdown",
                )
        else:
            # Too long, send summary or file
            await message.answer(
                response[:1000] + "...\n\n📄 Ответ слишком длинный для вывода текстом.",
                parse_mode="Markdown",
            )
        
        logger.info(
            f"Chat response for user {message.from_user.id}: "
            f"{len(response)} chars"
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        await message.answer(f"{ru.CHAT_ERROR}\n\n{str(e)[:100]}")
        await status_msg.delete()


@router.callback_query(F.data == "chat_exit")
async def cb_chat_exit(query, state: FSMContext) -> None:
    """Exit chat mode."""
    await state.clear()
    
    text = (
        "💬 Ниж\n\n"
        "Вы вышли из режима диалога.\n"
        "Можно использовать другие режимы."
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
    )
    await query.answer()
    logger.info(f"User {query.from_user.id} exited chat mode")
