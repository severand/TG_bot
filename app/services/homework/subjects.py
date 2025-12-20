"""Subject definitions and checkers.

Defines supported subjects and their metadata.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class SubjectInfo:
    """Information about a subject."""
    
    code: str
    name: str
    emoji: str
    description: str


class SubjectCheckers:
    """Registry of all supported subjects."""
    
    SUBJECTS = {
        "math": SubjectInfo(
            code="math",
            name="Математика",
            emoji="🔢",
            description="Проверка математических расчетов и методов решения"
        ),
        "russian": SubjectInfo(
            code="russian",
            name="Русский язык",
            emoji="🔤",
            description="Проверка орфографии, пунктуации и грамматики"
        ),
        "english": SubjectInfo(
            code="english",
            name="Английский язык",
            emoji="🇬🇧",
            description="Проверка грамматики и лексики английского языка"
        ),
        "physics": SubjectInfo(
            code="physics",
            name="Физика",
            emoji="⚗️",
            description="Проверка формул и физических расчетов"
        ),
        "chemistry": SubjectInfo(
            code="chemistry",
            name="Химия",
            emoji="🧪",
            description="Проверка химических уравнений и реакций"
        ),
        "cs": SubjectInfo(
            code="cs",
            name="Информатика",
            emoji="💻",
            description="Проверка кода и алгоритмов"
        ),
        "geography": SubjectInfo(
            code="geography",
            name="География",
            emoji="🌍",
            description="Проверка географических знаний и данных"
        ),
        "literature": SubjectInfo(
            code="literature",
            name="Литература",
            emoji="📖",
            description="Проверка анализа текстов и литературных знаний"
        ),
    }
    
    @classmethod
    def get_subject(cls, code: str) -> SubjectInfo:
        """Get subject info by code.
        
        Args:
            code: Subject code
            
        Returns:
            SubjectInfo
            
        Raises:
            ValueError: If subject not found
        """
        if code not in cls.SUBJECTS:
            raise ValueError(f"Unknown subject: {code}")
        return cls.SUBJECTS[code]
    
    @classmethod
    def get_all_subjects(cls) -> Dict[str, SubjectInfo]:
        """Get all subjects.
        
        Returns:
            Dictionary of code -> SubjectInfo
        """
        return cls.SUBJECTS.copy()
    
    @classmethod
    def get_subjects_list(cls) -> list[SubjectInfo]:
        """Get list of all subjects.
        
        Returns:
            List of SubjectInfo
        """
        return list(cls.SUBJECTS.values())
