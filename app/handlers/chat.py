"""Chat mode handlers for simple AI conversation.

Allows users to have a normal conversation with AI without
needing to upload documents. This is the DEFAULT mode.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

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


@router.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext) -> None:
    """Activate chat mode explicitly.
    
    Note: Chat mode is active by default after /start.
    This command just confirms it.
    """
    await state.clear()
    await state.set_state(ChatStates.chatting)
    
    text = (
        "💬 *Режим диалога активен*\n\n"
        "Пишите мне свои вопросы, я готов помочь!"
    )
    
    await message.answer(
        text,
        parse_mode="Markdown",
    )
    
    logger.info(f"Chat mode activated for user {message.from_user.id}")


async def start_chat_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Start chat mode (legacy function for compatibility)."""
    if state is None:
        logger.error("state is None in start_chat_mode")
        return
    
    await state.set_state(ChatStates.chatting)
    
    text = (
        "💬 *Режим диалога активен*\n\n"
        "Пишите мне свои вопросы, я готов помочь!"
    )
    
    if message:
        await message.answer(
            text,
            parse_mode="Markdown",
        )
    elif callback:
        await callback.message.answer(
            text,
            parse_mode="Markdown",
        )
        await callback.answer()
    
    logger.info(f"Chat mode started")


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
    
    # Show "typing..." indicator AND status message
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    # Send visual progress message
    progress_msg = await message.answer(
        "🤔 Думаю над вопросом...",
        parse_mode="Markdown",
    )
    
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
        
        # Delete progress message
        await progress_msg.delete()
        
        if not response:
            await message.answer(ru.CHAT_ERROR)
            return
        
        # Split long messages (Telegram limit is 4096 chars)
        splitter = TextSplitter(max_length=4000)
        chunks = splitter.split(response)
        
        # Send response in chunks
        if len(chunks) == 1:
            # Single message
            try:
                await message.answer(
                    response,
                    parse_mode="Markdown",
                )
            except Exception as e:
                # If markdown fails, send as plain text
                logger.warning(f"Markdown failed: {e}, sending as plain text")
                await message.answer(response)
        else:
            # Multiple messages
            for i, chunk in enumerate(chunks, 1):
                try:
                    prefix = f"*[Часть {i}/{len(chunks)}]*\n\n"
                    await message.answer(
                        f"{prefix}{chunk}",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    # If markdown fails, send as plain text
                    logger.warning(f"Markdown failed: {e}, sending as plain text")
                    await message.answer(f"[Часть {i}/{len(chunks)}]\n\n{chunk}")
        
        logger.info(f"Chat response: {len(response)} chars in {len(chunks)} messages")
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        # Delete progress message on error
        try:
            await progress_msg.delete()
        except:
            pass
        
        await message.answer(
            f"{ru.CHAT_ERROR}\n\nОшибка: {str(e)[:100]}",
        )


@router.callback_query(F.data == "chat_exit")
async def cb_chat_exit(callback: CallbackQuery, state: FSMContext) -> None:
    """Exit chat mode (legacy - not used in new design)."""
    from app.handlers.common import cb_back_to_main
    await cb_back_to_main(callback, state)
