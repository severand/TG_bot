"""Unified menu system using single message edit.

Based on InteriorBot architecture:
- Stores menu_message_id in FSM state
- All screens edit existing message instead of creating new ones
- Uses state.set_state(None) for navigation (preserves data)
- Uses state.clear() only for full reset
"""

import logging
from typing import Optional
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class MenuManager:
    """Manages unified menu with single message.
    
    All screens edit the same message instead of creating new ones.
    """
    
    @staticmethod
    async def show_menu(
        callback: Optional[CallbackQuery] = None,
        message: Optional[Message] = None,
        state: Optional[FSMContext] = None,
        text: str = "",
        keyboard: Optional[InlineKeyboardMarkup] = None,
        screen_code: str = "main",
    ) -> bool:
        """Show or update menu.
        
        Uses existing message if available, creates new one if needed.
        
        Args:
            callback: CallbackQuery (for edits)
            message: Message (for new menu)
            state: FSM context (saves menu_message_id)
            text: Menu text
            keyboard: Inline keyboard
            screen_code: Screen identifier for tracking
            
        Returns:
            bool: Success status
        """
        menu_message_id = None
        chat_id = None
        
        try:
            # Get current menu_message_id from state
            if state:
                data = await state.get_data()
                menu_message_id = data.get("menu_message_id")
            
            # Determine source
            if callback:
                chat_id = callback.message.chat.id
                
                # Try to edit existing message
                if menu_message_id:
                    try:
                        await callback.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=menu_message_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown",
                        )
                        logger.debug(f"📝 Edited menu {screen_code}")
                        await callback.answer()
                        return True
                    
                    except Exception as e:
                        logger.warning(
                            f"Failed to edit menu {menu_message_id}: {e}. "
                            f"Creating new menu."
                        )
                        # Delete old menu if needed
                        try:
                            await callback.bot.delete_message(
                                chat_id=chat_id,
                                message_id=menu_message_id,
                            )
                        except:
                            pass
                
                # Create new message
                new_msg = await callback.message.answer(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                menu_message_id = new_msg.message_id
                
                # Update state
                if state:
                    await state.update_data(menu_message_id=menu_message_id)
                
                await callback.answer()
                logger.info(f"✅ Created new menu {menu_message_id} ({screen_code})")
                return True
            
            elif message:
                chat_id = message.chat.id
                
                # Try to edit if we have menu_message_id
                if menu_message_id:
                    try:
                        await message.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=menu_message_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="Markdown",
                        )
                        logger.debug(f"📝 Edited menu {screen_code}")
                        return True
                    except Exception as e:
                        logger.warning(
                            f"Failed to edit menu {menu_message_id}: {e}. "
                            f"Creating new menu."
                        )
                        try:
                            await message.bot.delete_message(
                                chat_id=chat_id,
                                message_id=menu_message_id,
                            )
                        except:
                            pass
                
                # Create new message
                new_msg = await message.answer(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                menu_message_id = new_msg.message_id
                
                # Update state
                if state:
                    await state.update_data(menu_message_id=menu_message_id)
                
                logger.info(f"✅ Created new menu {menu_message_id} ({screen_code})")
                return True
            
            else:
                logger.error("No callback or message provided")
                return False
        
        except Exception as e:
            logger.error(f"Error in show_menu: {e}")
            return False
    
    @staticmethod
    async def navigate(
        callback: CallbackQuery,
        state: FSMContext,
        text: str,
        keyboard: InlineKeyboardMarkup,
        new_state=None,
        screen_code: str = "menu",
        preserve_data: bool = True,
    ) -> bool:
        """Navigate to new menu screen.
        
        Uses state.set_state(None) to preserve data.
        
        Args:
            callback: CallbackQuery
            state: FSM context
            text: New menu text
            keyboard: New keyboard
            new_state: New FSM state (optional)
            screen_code: Screen identifier
            preserve_data: Whether to preserve FSM data
            
        Returns:
            bool: Success status
        """
        try:
            # Get current data before changing state
            data = await state.get_data() if preserve_data else {}
            
            # Change state
            if new_state:
                await state.set_state(new_state)
            else:
                await state.set_state(None)  # ✅ CRITICAL: set_state(None) preserves data
            
            # Restore menu_message_id and other important data
            if preserve_data:
                await state.update_data(
                    menu_message_id=data.get("menu_message_id"),
                    screen_code=screen_code,
                    # Keep other important fields
                )
            else:
                # Initialize menu_message_id for new session
                await state.update_data(
                    menu_message_id=None,
                    screen_code=screen_code,
                )
            
            # Show menu
            success = await MenuManager.show_menu(
                callback=callback,
                state=state,
                text=text,
                keyboard=keyboard,
                screen_code=screen_code,
            )
            
            if success:
                logger.info(f"✅ Navigated to {screen_code}")
            
            return success
        
        except Exception as e:
            logger.error(f"Error in navigate: {e}")
            return False
    
    @staticmethod
    async def clear_session(callback: CallbackQuery, state: FSMContext) -> None:
        """Clear entire session (use only for /start).
        
        Uses state.clear() for full reset.
        """
        try:
            # Delete old menu if exists
            data = await state.get_data()
            menu_message_id = data.get("menu_message_id")
            
            if menu_message_id:
                try:
                    await callback.bot.delete_message(
                        chat_id=callback.message.chat.id,
                        message_id=menu_message_id,
                    )
                    logger.debug(f"🗑️ Deleted menu {menu_message_id}")
                except:
                    pass
            
            # Clear state completely
            await state.clear()  # ✅ Full reset for new session
            logger.info("🔄 Session cleared")
        
        except Exception as e:
            logger.error(f"Error in clear_session: {e}")


def create_keyboard(
    buttons: list[tuple[str, str]],
    rows_per_row: int = 2,
) -> InlineKeyboardMarkup:
    """Create inline keyboard from button list.
    
    Args:
        buttons: List of (text, callback_data) tuples
        rows_per_row: How many buttons per row (1 or 2)
        
    Returns:
        InlineKeyboardMarkup: Keyboard
        
    Example:
        >>> keyboard = create_keyboard([
        ...     ("💬 Диалог", "mode_chat"),
        ...     ("📄 Анализ", "mode_analyze"),
        ...     ("🎯 Промты", "mode_prompts"),
        ... ], rows_per_row=2)
    """
    inline_keyboard = []
    row = []
    
    for text, callback_data in buttons:
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
        ))
        
        # Add row when it reaches rows_per_row buttons
        if len(row) == rows_per_row:
            inline_keyboard.append(row)
            row = []
    
    # Add remaining buttons
    if row:
        inline_keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
