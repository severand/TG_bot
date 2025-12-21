"""Pytest configuration and fixtures for RAG tests."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    Это тестовый документ для проверки RAG системы.
    
    RAG (Retrieval-Augmented Generation) - это подход, который объединяет
    поиск релевантной информации с генерацией ответов.
    
    Система работает следующим образом:
    1. Загружает документы
    2. Разбивает на чанки
    3. Создаёт embeddings
    4. Сохраняет в векторную базу
    5. Выполняет семантический поиск
    
    Преимущества RAG:
    - Точные ответы на основе документов
    - Экономия токенов
    - Масштабируемость
    """


@pytest.fixture
def sample_doc_id():
    """Sample document ID."""
    return "test_doc_001"


@pytest.fixture
def sample_metadata():
    """Sample metadata."""
    return {
        "type": "test",
        "author": "pytest",
        "year": 2025,
    }
