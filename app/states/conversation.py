"""FSM states for document analysis conversation flow.

Fixes 2025-12-20:
- Added selecting_prompt state for prompt selection before document upload
- New workflow: selecting_prompt -> ready -> waiting_for_command

Handles the workflow:
1. User activates /analyze
2. User selects prompt type
3. User uploads document
4. Bot analyzes based on selected prompt
"""

from aiogram.fsm.state import State, StatesGroup


class ConversationStates(StatesGroup):
    """States for document analysis conversation.
    
    States:
        selecting_prompt: User selecting analysis prompt type
        ready: Ready to receive document or command
        document_loaded: Document received, waiting for commands
        processing: Currently processing analysis
        waiting_for_command: Waiting for analysis instruction
    """
    
    selecting_prompt = State()
    ready = State()
    document_loaded = State()
    processing = State()
    waiting_for_command = State()
