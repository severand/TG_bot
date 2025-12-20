"""States for homework checking workflow.

Defines FSM states for homework mode:
- Subject selection
- File upload and processing
- Result visualization
"""

from aiogram.fsm.state import State, StatesGroup


class HomeworkStates(StatesGroup):
    """FSM states for homework checking."""
    
    # Initial state - waiting for subject selection
    selecting_subject = State()
    
    # File upload state - waiting for document/image
    waiting_for_file = State()
    
    # Processing state
    processing = State()
    
    # Result display state
    showing_result = State()
