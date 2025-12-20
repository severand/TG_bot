"""Result visualization for homework evaluation.

Generates formatted text output for homework results.
"""

import logging
from app.services.homework.checker import HomeworkResult

logger = logging.getLogger(__name__)


class ResultVisualizer:
    """Visualizes homework evaluation results."""
    
    GRADE_EMOJIS = {
        5: "🌟",  # ⭐
        4: "🌟🌟",  # ⭐⭐
        3: "🌟🌟🌟",  # ⭐⭐⭐
        2: "⚠️",  # ⚠️
        1: "😤",  # 😤
    }
    
    GRADE_WORDS = {
        5: "😀🎊 Отлично!",
        4: "😊 Хорошо!",
        3: "😐 Удовлетворительно",
        2: "🙁 Плохо",
        1: "😣 Очень плохо",
    }
    
    @staticmethod
    def format_result(result: HomeworkResult) -> str:
        """Format homework result as Telegram message.
        
        Args:
            result: HomeworkResult
            
        Returns:
            Formatted string for Telegram
        """
        percentage = (result.points / result.max_points * 100) if result.max_points > 0 else 0
        
        lines = []
        
        # Header with subject and grade
        lines.append(f"\n{'='*50}")
        lines.append(f"{ResultVisualizer.GRADE_EMOJIS[result.grade]} Проверка: {result.subject}")
        lines.append(f"{'='*50}\n")
        
        # Grade section
        lines.append(f"⚡ Оценка: {ResultVisualizer.GRADE_WORDS[result.grade]}")
        lines.append(f"   Оценка: {result.grade} из 5\n")
        
        # Points section
        lines.append(f"💯 Баллы: {result.points}/{result.max_points} ({percentage:.0f}%)")
        
        # Progress bar
        bar_length = 20
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        lines.append(f"   [{bar}]\n")
        
        # Correct items
        if result.correct_items:
            lines.append("✅ Что правильно:")
            for item in result.correct_items[:5]:  # Max 5 items
                lines.append(f"   ✓ {item}")
            if len(result.correct_items) > 5:
                lines.append(f"   ... и еще {len(result.correct_items) - 5}")
            lines.append("")
        
        # Incorrect items
        if result.incorrect_items:
            lines.append("❌ Ошибки:")
            for item in result.incorrect_items[:5]:  # Max 5 items
                lines.append(f"   ✗ {item}")
            if len(result.incorrect_items) > 5:
                lines.append(f"   ... и еще {len(result.incorrect_items) - 5}")
            lines.append("")
        
        # Feedback
        if result.feedback:
            lines.append("📚 Подробно:")
            lines.append(f"   {result.feedback}\n")
        
        # Advice
        if result.advice:
            lines.append("💭 Совет для улучшения:")
            lines.append(f"   {result.advice}\n")
        
        lines.append("="*50)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_short_result(result: HomeworkResult) -> str:
        """Format short result for quick display.
        
        Args:
            result: HomeworkResult
            
        Returns:
            Short formatted string
        """
        percentage = (result.points / result.max_points * 100) if result.max_points > 0 else 0
        
        return (
            f"{ResultVisualizer.GRADE_EMOJIS[result.grade]} "
            f"{result.grade}/5 ({percentage:.0f}%) - {result.subject}\n"
            f"{ResultVisualizer.GRADE_WORDS[result.grade]}"
        )
