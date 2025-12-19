"""FSM states for prompt management workflow.

Defines state machine for prompt creation and editing.
"""

from aiogram.fsm.state import State, StatesGroup


class PromptStates(StatesGroup):
    """States for prompt management workflow.
    
    States:
        entering_name: Waiting for prompt name input
        entering_system_prompt: Waiting for system prompt
        entering_user_prompt: Waiting for user prompt template
        editing_system: Editing system prompt
        editing_user: Editing user prompt
    """
    
    entering_name = State()
    entering_system_prompt = State()
    entering_user_prompt = State()
    editing_system = State()
    editing_user = State()
