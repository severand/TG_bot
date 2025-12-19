"""FSM states for document analysis workflow.

Defines state machine for user interactions with the bot.
"""

from aiogram.fsm.state import State, StatesGroup


class DocumentAnalysisStates(StatesGroup):
    """States for document analysis workflow.
    
    States:
        waiting_for_file: Waiting for user to upload a file
        processing: Currently processing the uploaded file
        analyzing: Sending to AI for analysis
        waiting_for_prompt: Waiting for user to provide custom analysis prompt
    """
    
    waiting_for_file = State()
    processing = State()
    analyzing = State()
    waiting_for_prompt = State()
