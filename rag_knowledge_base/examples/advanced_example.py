#!/usr/bin/env python3
"""Продвинутый пример использования RAG модуля.

Показывает продвинутые возможности:
- Кастомная конфигурация
- Работа с метаданными
- Фильтрация поиска
- Различные форматы вывода
"""

from pathlib import Path
from rag_module.services import RAGManager
from rag_module.services.chunker import Chunker
from rag_module.services.embeddings import EmbeddingService
from rag_module.utils import (
    format_search_results,
    format_document_info,
    validate_query,
    validate_top_k,
)


def main():
    """Главная функция."""
    print("🚀 RAG Module - Продвинутый пример\n")
    
    # 1. Кастомная конфигурация
    print("⚙️ Кастомная конфигурация...")
    chunker = Chunker(chunk_size=300, chunk_overlap=50)
    embedding_service = EmbeddingService()
    
    print(f"✅ Chunk size: {chunker.chunk_size}")
    print(f"✅ Embedding dim: {embedding_service.get_embedding_dimension()}")
    print()
    
    # 2. Валидация входных данных
    print("✅ Валидация входных данных:")
    try:
        query = validate_query("тестовый запрос")
        top_k = validate_top_k(5)
        print(f"✓ Query: '{query}'")
        print(f"✓ Top-K: {top_k}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    print()
    
    # 3. Различные форматы вывода
    print("📊 Форматы вывода:")
    print("""
    # Markdown формат
    formatted = format_search_results(results, format="markdown")
    
    # Plain text
    formatted = format_search_results(results, format="plain")
    
    # JSON для API
    formatted = format_search_results(results, format="json")
    """)
    
    # 4. Продвинутый поиск
    print("🔍 Продвинутый поиск:")
    print("""
    # Поиск с фильтрацией по метаданным
    results = manager.search(
        query="условия",
        top_k=10,
        filter_metadata={"type": "contract"},
        min_similarity=0.5
    )
    
    # Обработка результатов
    for result in results:
        print(f"Score: {result.similarity_score:.2%}")
        print(f"Source: {result.source_doc}")
        print(f"Text: {result.chunk.text[:100]}...")
        print(f"Metadata: {result.chunk.metadata}")
    """)
    
    print("\n✅ Продвинутый пример завершён!")
    print("📚 См. документацию для большего")


if __name__ == "__main__":
    main()
