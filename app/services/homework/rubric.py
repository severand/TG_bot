"""Grading rubric for homework evaluation.

Defines grading criteria and scales for different subjects.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GradingCriteria:
    """Single grading criterion."""
    
    name: str
    description: str
    max_points: int


@dataclass
class GradingRubric:
    """Complete rubric for a subject."""
    
    subject: str
    criteria: List[GradingCriteria]
    grade_scale: Dict[int, str]  # points -> grade (5,4,3,2,1)
    
    def calculate_grade(self, points: int) -> int:
        """Calculate grade from points.
        
        Args:
            points: Total points earned
            
        Returns:
            Grade from 1-5
        """
        max_points = sum(c.max_points for c in self.criteria)
        percentage = (points / max_points * 100) if max_points > 0 else 0
        
        if percentage >= 90:
            return 5
        elif percentage >= 75:
            return 4
        elif percentage >= 60:
            return 3
        elif percentage >= 45:
            return 2
        else:
            return 1
    
    def get_grade_description(self, grade: int) -> str:
        """Get textual description of grade.
        
        Args:
            grade: Numeric grade 1-5
            
        Returns:
            Grade description
        """
        descriptions = {
            5: "Отлично!",
            4: "Хорошо!",
            3: "Удовлетворительно",
            2: "Плохо",
            1: "Очень плохо",
        }
        return descriptions.get(grade, "Неизвестно")


# Subject-specific rubrics
MATH_RUBRIC = GradingRubric(
    subject="Математика",
    criteria=[
        GradingCriteria("Правильность расчетов", "Все вычисления верны", 40),
        GradingCriteria("Метод решения", "Использован правильный подход", 30),
        GradingCriteria("Оформление", "Решение аккуратно оформлено", 20),
        GradingCriteria("Полнота", "Все задачи решены", 10),
    ],
    grade_scale={}
)

RUSSIAN_RUBRIC = GradingRubric(
    subject="Русский язык",
    criteria=[
        GradingCriteria("Орфография", "Нет орфографических ошибок", 25),
        GradingCriteria("Пунктуация", "Правильное использование знаков", 25),
        GradingCriteria("Грамматика", "Нет грамматических ошибок", 25),
        GradingCriteria("Содержание", "Ответ полный и логичный", 25),
    ],
    grade_scale={}
)

ENGLISH_RUBRIC = GradingRubric(
    subject="Английский язык",
    criteria=[
        GradingCriteria("Грамматика", "Правильное использование грамматики", 30),
        GradingCriteria("Лексика", "Правильный выбор слов", 25),
        GradingCriteria("Произношение", "Правильное написание", 20),
        GradingCriteria("Полнота", "Полный ответ на вопрос", 25),
    ],
    grade_scale={}
)

PHYSICS_RUBRIC = GradingRubric(
    subject="Физика",
    criteria=[
        GradingCriteria("Формулы", "Правильно применены формулы", 35),
        GradingCriteria("Расчеты", "Все вычисления верны", 35),
        GradingCriteria("Единицы", "Правильно указаны единицы измерения", 15),
        GradingCriteria("Объяснение", "Ясное объяснение решения", 15),
    ],
    grade_scale={}
)

CHEMISTRY_RUBRIC = GradingRubric(
    subject="Химия",
    criteria=[
        GradingCriteria("Уравнения", "Уравнения составлены правильно", 35),
        GradingCriteria("Расчеты", "Расчеты выполнены верно", 35),
        GradingCriteria("Стехиометрия", "Соблюдены стехиометрические соотношения", 15),
        GradingCriteria("Объяснение", "Логичное объяснение процесса", 15),
    ],
    grade_scale={}
)

CS_RUBRIC = GradingRubric(
    subject="Информатика",
    criteria=[
        GradingCriteria("Синтаксис", "Правильный синтаксис кода", 30),
        GradingCriteria("Логика", "Правильная логика решения", 35),
        GradingCriteria("Эффективность", "Оптимальное решение", 20),
        GradingCriteria("Стиль", "Чистый и читаемый код", 15),
    ],
    grade_scale={}
)

GEOGRAPHY_RUBRIC = GradingRubric(
    subject="География",
    criteria=[
        GradingCriteria("Точность", "Точные географические данные", 30),
        GradingCriteria("Полнота", "Полный ответ на вопрос", 30),
        GradingCriteria("Структура", "Логичная структура ответа", 20),
        GradingCriteria("Примеры", "Конкретные примеры и факты", 20),
    ],
    grade_scale={}
)

LITERATURE_RUBRIC = GradingRubric(
    subject="Литература",
    criteria=[
        GradingCriteria("Анализ", "Глубокий анализ текста", 35),
        GradingCriteria("Цитирование", "Правильное использование цитат", 25),
        GradingCriteria("Аргументация", "Убедительные доказательства", 25),
        GradingCriteria("Стиль", "Грамотное изложение", 15),
    ],
    grade_scale={}
)

# Registry of all rubrics
SUBJECT_RUBRICS = {
    "math": MATH_RUBRIC,
    "russian": RUSSIAN_RUBRIC,
    "english": ENGLISH_RUBRIC,
    "physics": PHYSICS_RUBRIC,
    "chemistry": CHEMISTRY_RUBRIC,
    "cs": CS_RUBRIC,
    "geography": GEOGRAPHY_RUBRIC,
    "literature": LITERATURE_RUBRIC,
}
