"""FSM states for chat mode.

Simple state for regular conversation without documents.
"""

from aiogram.fsm.state import State, StatesGroup


class ChatStates(StatesGroup):
    """States for chat mode.
    
    States:
        chatting: User is in conversation mode
    """
    
    chatting = State()
