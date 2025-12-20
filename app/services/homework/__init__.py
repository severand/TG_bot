"""Homework checking service.

Provides functionality for checking homework assignments:
- Subject-specific grading logic
- Rubric-based evaluation
- Feedback generation
- Result visualization
"""

from app.services.homework.checker import HomeworkChecker
from app.services.homework.subjects import SubjectCheckers
from app.services.homework.rubric import GradingRubric
from app.services.homework.visualizer import ResultVisualizer

__all__ = [
    "HomeworkChecker",
    "SubjectCheckers",
    "GradingRubric",
    "ResultVisualizer",
]
