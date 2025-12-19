"""Chat mode handlers for simple AI conversation.

Allows users to have a normal conversation with AI without
needing to upload documents. Just ask questions or chat normally.

Uses unified menu system with single message editing.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.config import get_settings
from app.localization import ru
from app.states.chat import ChatStates
from app.services.llm.llm_factory import LLMFactory
from app.utils.text_splitter import TextSplitter
from app.utils.menu import MenuManager, create_keyboard

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
    """Start chat mode.
    
    User can have a normal conversation with AI.
    """
    await start_chat_mode(message=message, state=state)


async def start_chat_mode(message=None, callback=None, state: FSMContext = None) -> None:
    """Start chat mode - can be called from /chat or from menu."""
    await state.set_state(ChatStates.chatting)
    
    # Exit button
    keyboard = create_keyboard(
        buttons=[(ru.BTN_CANCEL, "chat_exit")],
        rows_per_row=1,
    )
    
    text = f"{ru.CHAT_MODE_TITLE}\n\n{ru.CHAT_MODE_TEXT}"
    
    # Show menu
    if message:
        await MenuManager.show_menu(
            message=message,
            state=state,
            text=text,
            keyboard=keyboard,
            screen_code="chat_mode",
        )
    elif callback:
        await MenuManager.navigate(
            callback=callback,
            state=state,
            text=text,
            keyboard=keyboard,
            new_state=ChatStates.chatting,
            screen_code="chat_mode",
            preserve_data=True,
        )
    
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
    
    # Delete user message
    try:
        await message.delete()
    except:
        pass
    
    # Get menu_message_id for updating
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    chat_id = message.chat.id
    
    # Show processing indicator
    if menu_message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text=ru.CHAT_PROCESSING,
                parse_mode="Markdown",
            )
        except:
            pass
    
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
            if menu_message_id:
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=ru.CHAT_ERROR,
                    parse_mode="Markdown",
                )
            return
        
        # Update menu with response
        splitter = TextSplitter()
        message_count = splitter.count_messages(response)
        
        # Prepare response text
        response_text = f"🤖 *Ответ:*\n\n{response}"
        
        # Create continue button
        keyboard = create_keyboard(
            buttons=[(ru.BTN_CANCEL, "chat_exit")],
            rows_per_row=1,
        )
        
        # Update menu
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=response_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"Failed to edit menu: {e}")
                # Create new message
                new_msg = await message.answer(
                    text=response_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                await state.update_data(menu_message_id=new_msg.message_id)
        else:
            # Create new message if no menu_message_id
            new_msg = await message.answer(
                text=response_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            await state.update_data(menu_message_id=new_msg.message_id)
        
        logger.info(f"Chat response: {len(response)} chars")
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        error_text = f"{ru.CHAT_ERROR}\n\n{str(e)[:100]}"
        
        keyboard = create_keyboard(
            buttons=[(ru.BTN_CANCEL, "chat_exit")],
            rows_per_row=1,
        )
        
        if menu_message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=menu_message_id,
                    text=error_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
            except:
                pass


@router.callback_query(F.data == "chat_exit")
async def cb_chat_exit(callback, state: FSMContext) -> None:
    """Exit chat mode and return to main menu."""
    # Use MenuManager.navigate to return to main menu
    from app.handlers.common import cb_back_to_main
    
    await cb_back_to_main(callback, state)
