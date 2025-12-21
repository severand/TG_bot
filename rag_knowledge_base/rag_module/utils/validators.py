"""Input validation utilities for RAG module.

Проверка и валидация входных данных для предотвращения ошибок и
повышения безопасности. Все функции возвращают валидированные данные
или выбрасывают исключения с понятными сообщениями.
"""

import re
from pathlib import Path
from typing import Optional

from rag_module.exceptions import RAGException


class ValidationError(RAGException):
    """Ошибка валидации входных данных."""


def validate_file_path(file_path: Path, must_exist: bool = True) -> Path:
    """Валидация пути к файлу.
    
    Args:
        file_path: Путь к файлу
        must_exist: Должен ли файл существовать
        
    Returns:
        Path: Валидированный путь
        
    Raises:
        ValidationError: Если путь невалиден
    """
    if not isinstance(file_path, Path):
        try:
            file_path = Path(file_path)
        except Exception as e:
            raise ValidationError(f"Invalid file path: {e}") from e
    
    if must_exist and not file_path.exists():
        raise ValidationError(f"File not found: {file_path}")
    
    if must_exist and not file_path.is_file():
        raise ValidationError(f"Path is not a file: {file_path}")
    
    # Проверка размера файла (если существует)
    if must_exist:
        max_size = 100 * 1024 * 1024  # 100MB
        size = file_path.stat().st_size
        if size > max_size:
            raise ValidationError(
                f"File too large: {size / 1024 / 1024:.1f}MB > {max_size / 1024 / 1024}MB"
            )
        
        if size == 0:
            raise ValidationError("File is empty")
    
    return file_path


def validate_doc_id(doc_id: str) -> str:
    """Валидация document ID.
    
    Args:
        doc_id: Идентификатор документа
        
    Returns:
        str: Валидированный doc_id
        
    Raises:
        ValidationError: Если doc_id невалиден
    """
    if not doc_id or not isinstance(doc_id, str):
        raise ValidationError("doc_id must be a non-empty string")
    
    doc_id = doc_id.strip()
    
    if not doc_id:
        raise ValidationError("doc_id cannot be empty or whitespace")
    
    if len(doc_id) > 255:
        raise ValidationError(f"doc_id too long: {len(doc_id)} > 255 characters")
    
    # Разрешены только буквы, цифры, дефисы, подчеркивания
    if not re.match(r'^[a-zA-Z0-9_-]+$', doc_id):
        raise ValidationError(
            f"doc_id contains invalid characters: '{doc_id}'. "
            "Only letters, numbers, hyphens, and underscores allowed"
        )
    
    return doc_id


def validate_query(query: str, min_length: int = 1, max_length: int = 1000) -> str:
    """Валидация поискового запроса.
    
    Args:
        query: Поисковый запрос
        min_length: Минимальная длина
        max_length: Максимальная длина
        
    Returns:
        str: Валидированный запрос
        
    Raises:
        ValidationError: Если запрос невалиден
    """
    if not query or not isinstance(query, str):
        raise ValidationError("Query must be a non-empty string")
    
    query = query.strip()
    
    if not query:
        raise ValidationError("Query cannot be empty or whitespace")
    
    if len(query) < min_length:
        raise ValidationError(
            f"Query too short: {len(query)} < {min_length} characters"
        )
    
    if len(query) > max_length:
        raise ValidationError(
            f"Query too long: {len(query)} > {max_length} characters"
        )
    
    return query


def validate_top_k(top_k: int, min_value: int = 1, max_value: int = 100) -> int:
    """Валидация параметра top_k.
    
    Args:
        top_k: Количество результатов
        min_value: Минимальное значение
        max_value: Максимальное значение
        
    Returns:
        int: Валидированное значение
        
    Raises:
        ValidationError: Если значение невалидно
    """
    if not isinstance(top_k, int):
        try:
            top_k = int(top_k)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"top_k must be an integer: {e}") from e
    
    if top_k < min_value:
        raise ValidationError(f"top_k too small: {top_k} < {min_value}")
    
    if top_k > max_value:
        raise ValidationError(f"top_k too large: {top_k} > {max_value}")
    
    return top_k


def validate_similarity_threshold(
    threshold: float,
    min_value: float = 0.0,
    max_value: float = 1.0,
) -> float:
    """Валидация порога схожести.
    
    Args:
        threshold: Порог схожести (0-1)
        min_value: Минимальное значение
        max_value: Максимальное значение
        
    Returns:
        float: Валидированное значение
        
    Raises:
        ValidationError: Если значение невалидно
    """
    if not isinstance(threshold, (int, float)):
        try:
            threshold = float(threshold)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"similarity_threshold must be a number: {e}"
            ) from e
    
    threshold = float(threshold)
    
    if threshold < min_value:
        raise ValidationError(
            f"similarity_threshold too small: {threshold} < {min_value}"
        )
    
    if threshold > max_value:
        raise ValidationError(
            f"similarity_threshold too large: {threshold} > {max_value}"
        )
    
    return threshold


def validate_metadata(metadata: dict) -> dict:
    """Валидация метаданных документа.
    
    Args:
        metadata: Словарь метаданных
        
    Returns:
        dict: Валидированные метаданные
        
    Raises:
        ValidationError: Если метаданные невалидны
    """
    if not isinstance(metadata, dict):
        raise ValidationError("Metadata must be a dictionary")
    
    # Проверка размера
    if len(metadata) > 100:
        raise ValidationError(f"Too many metadata fields: {len(metadata)} > 100")
    
    # Проверка ключей и значений
    validated = {}
    for key, value in metadata.items():
        # Ключи должны быть строками
        if not isinstance(key, str):
            raise ValidationError(f"Metadata key must be string, got: {type(key)}")
        
        # Ключи не должны быть пустыми
        if not key.strip():
            raise ValidationError("Metadata key cannot be empty")
        
        # Значения должны быть простыми типами
        if not isinstance(value, (str, int, float, bool, type(None))):
            raise ValidationError(
                f"Metadata value for '{key}' must be str/int/float/bool/None, "
                f"got: {type(value)}"
            )
        
        # Строковые значения не должны быть слишком длинными
        if isinstance(value, str) and len(value) > 1000:
            raise ValidationError(
                f"Metadata value for '{key}' too long: {len(value)} > 1000 characters"
            )
        
        validated[key.strip()] = value
    
    return validated
