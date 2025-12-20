"""Main homework checking service.

Fixes 2025-12-20 17:11:
- check_homework now accepts system_prompt parameter
- Allows users to use custom homework evaluation prompts
- Falls back to default if not provided
- Integrates with PromptManager for manageable prompts

Integrates with LLM to evaluate homework assignments
based on subject-specific criteria.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.services.llm.replicate_client import ReplicateClient
from app.services.homework.rubric import SUBJECT_RUBRICS, GradingRubric

logger = logging.getLogger(__name__)


@dataclass
class HomeworkResult:
    """Result of homework evaluation."""
    
    grade: int  # 1-5
    points: int
    max_points: int
    correct_items: list[str]
    incorrect_items: list[str]
    feedback: str
    advice: str
    subject: str


class HomeworkChecker:
    """Checks homework using LLM."""
    
    def __init__(self, llm_service: ReplicateClient):
        """Initialize checker.
        
        Args:
            llm_service: LLM service for evaluation
        """
        self.llm = llm_service
    
    async def check_homework(
        self,
        content: str,
        subject: str,
        file_type: str = "text",
        system_prompt: Optional[str] = None
    ) -> HomeworkResult:
        """Check homework and return evaluation.
        
        Args:
            content: Homework content (text from file or image)
            subject: Subject code (math, russian, english, etc.)
            file_type: Type of file (text, image, pdf)
            system_prompt: Custom system prompt for evaluation (optional)
            
        Returns:
            HomeworkResult with evaluation
            
        Raises:
            ValueError: If subject not supported
        """
        # Validate subject
        if subject not in SUBJECT_RUBRICS:
            raise ValueError(f"Unknown subject: {subject}")
        
        rubric = SUBJECT_RUBRICS[subject]
        
        # Create evaluation prompt
        prompt = self._create_evaluation_prompt(
            content, 
            subject, 
            rubric,
            system_prompt=system_prompt
        )
        
        # Get LLM response
        try:
            response = await self.llm.analyze_document(
                document_text=content,
                user_prompt=prompt
            )
        except Exception as e:
            logger.error(f"LLM error during homework check: {e}")
            raise
        
        # Parse response
        result = self._parse_evaluation_response(response, rubric, subject)
        
        return result
    
    def _create_evaluation_prompt(
        self, 
        content: str, 
        subject: str, 
        rubric: GradingRubric,
        system_prompt: Optional[str] = None
    ) -> str:
        """Create evaluation prompt for LLM.
        
        Args:
            content: Homework content
            subject: Subject name
            rubric: Grading rubric
            system_prompt: Custom system prompt (optional)
            
        Returns:
            Formatted prompt
        """
        criteria_text = "\n".join(
            f"- {c.name} ({c.max_points} points): {c.description}"
            for c in rubric.criteria
        )
        
        # Use custom system prompt if provided, otherwise use default
        if system_prompt:
            base_instruction = system_prompt
        else:
            base_instruction = (
                f"Повторяю: ты опытный оцениватель домашних заданий по {rubric.subject}. "
                "Оценивай справедливо и конструктивно."
            )
        
        prompt = f"""{base_instruction}

Критерии оценки:
{criteria_text}

Предоставьте оценку в формате JSON:
{{
    "points": <всего набранных баллов>,
    "correct_items": [<список правильных ответов/частей>],
    "incorrect_items": [<список неправильных ответов/частей>],
    "feedback": "<подробный отзыв на русском>",
    "advice": "<конструктивный совет для улучшения на русском>"
}}

Оценивайте строго по критериям. Все комментарии должны быть на РУССКОМ языке!"""
        
        return prompt
    
    def _parse_evaluation_response(self, response: str, rubric: GradingRubric, subject: str) -> HomeworkResult:
        """Parse LLM response into structured result.
        
        Args:
            response: LLM response
            rubric: Grading rubric
            subject: Subject code
            
        Returns:
            Parsed HomeworkResult
        """
        import json
        
        try:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}")
            
            if start >= 0 and end > start:
                json_str = response[start:end+1]
                data = json.loads(json_str)
            else:
                # Fallback: create minimal result
                data = {
                    "points": 0,
                    "correct_items": [],
                    "incorrect_items": [],
                    "feedback": response,
                    "advice": ""
                }
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            data = {
                "points": 0,
                "correct_items": [],
                "incorrect_items": [],
                "feedback": response,
                "advice": ""
            }
        
        # Validate points
        points = int(data.get("points", 0))
        max_points = sum(c.max_points for c in rubric.criteria)
        points = min(points, max_points)  # Ensure points don't exceed max
        
        # Calculate grade
        grade = rubric.calculate_grade(points)
        
        # Create result
        return HomeworkResult(
            grade=grade,
            points=points,
            max_points=max_points,
            correct_items=data.get("correct_items", []),
            incorrect_items=data.get("incorrect_items", []),
            feedback=data.get("feedback", ""),
            advice=data.get("advice", ""),
            subject=rubric.subject
        )
