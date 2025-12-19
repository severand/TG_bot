"""FSM states for document analysis conversation flow.

Handles the workflow:
1. User uploads document
2. Bot confirms reception
3. User sends text commands for analysis
4. Bot analyzes based on commands
"""

from aiogram.fsm.state import State, StatesGroup


class ConversationStates(StatesGroup):
    """States for document analysis conversation.
    
    States:
        ready: Ready to receive document or command
        document_loaded: Document received, waiting for commands
        processing: Currently processing analysis
        waiting_for_command: Waiting for analysis instruction
    """
    
    ready = State()
    document_loaded = State()
    processing = State()
    waiting_for_command = State()
