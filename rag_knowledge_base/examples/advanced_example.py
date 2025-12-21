"""Advanced RAG usage example.

Продвинутый пример с использованием всех возможностей:
- Множественные документы
- Фильтрация по метаданным
- Настройка similarity threshold
- Batch обработка
- Управление документами
"""

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_module.services import RAGManager
from rag_module.models import SearchResult
from rag_module.utils import (
    format_search_results,
    format_document_info,
    format_stats,
)


def main():
    """Главная функция продвинутого примера."""
    print("🚀 Advanced RAG Example - Продвинутый пример\n")
    
    # Инициализация с кастомными параметрами
    print("⚙️ Инициализация с кастомными параметрами...")
    manager = RAGManager(
        persist_directory=Path("./rag_data_advanced"),
        collection_name="advanced_example",
        chunk_size=400,  # Меньшие чанки
        chunk_overlap=100,  # Больше overlap
        similarity_threshold=0.6,  # Ниже порог
    )
    print("✅ Готово!\n")
    
    # Пример 1: Добавление нескольких документов с метаданными
    example_1_multiple_documents(manager)
    
    # Пример 2: Поиск с фильтрацией
    example_2_filtered_search(manager)
    
    # Пример 3: Настройка similarity threshold
    example_3_custom_threshold(manager)
    
    # Пример 4: Форматирование результатов
    example_4_formatting(manager)
    
    # Пример 5: Управление документами
    example_5_document_management(manager)
    
    print("\n\n✨ Продвинутый пример завершен!")


def example_1_multiple_documents(manager: RAGManager):
    """Пример 1: Добавление нескольких документов."""
    print("📚 Пример 1: Добавление нескольких документов\n")
    
    from rag_module.models import Chunk
    
    # Документ 1: AI/ML
    ai_chunks = [
        Chunk(
            id="ai_1",
            doc_id="ai_guide",
            text="Искусственный интеллект (AI) революционизирует индустрии.",
            position=0,
            metadata={"category": "AI", "language": "ru", "year": 2024},
        ),
        Chunk(
            id="ai_2",
            doc_id="ai_guide",
            text="Machine learning enables systems to learn from data automatically.",
            position=1,
            metadata={"category": "AI", "language": "en", "year": 2024},
        ),
    ]
    
    # Документ 2: Python
    python_chunks = [
        Chunk(
            id="py_1",
            doc_id="python_guide",
            text="Python is a high-level programming language known for simplicity.",
            position=0,
            metadata={"category": "Programming", "language": "en", "year": 2024},
        ),
        Chunk(
            id="py_2",
            doc_id="python_guide",
            text="NumPy and Pandas are essential libraries for data science in Python.",
            position=1,
            metadata={"category": "Programming", "language": "en", "year": 2024},
        ),
    ]
    
    # Добавляем чанки
    manager.retriever.add_chunks(ai_chunks + python_chunks)
    
    print(f"  ✅ Добавлено 2 документа ({len(ai_chunks + python_chunks)} чанков)\n")


def example_2_filtered_search(manager: RAGManager):
    """Пример 2: Поиск с фильтрацией по метаданным."""
    print("🔍 Пример 2: Поиск с фильтрацией\n")
    
    query = "programming language"
    
    # Поиск только в категории Programming
    print(f"  💬 Query: '{query}'")
    print("  🏷️ Filter: category='Programming'")
    
    results = manager.search(
        query=query,
        top_k=5,
        filter_metadata={"category": "Programming"},
    )
    
    print(f"  ✅ Найдено: {len(results)} результатов")
    for r in results:
        print(f"    - {r.chunk.text[:60]}... ({r.similarity_score:.0%})")
    
    print()


def example_3_custom_threshold(manager: RAGManager):
    """Пример 3: Настройка similarity threshold."""
    print("🎯 Пример 3: Настройка threshold\n")
    
    query = "data science"
    
    # Поиск с разными thresholds
    for threshold in [0.3, 0.6, 0.8]:
        results = manager.search(
            query=query,
            top_k=10,
            similarity_threshold=threshold,
        )
        print(f"  Threshold {threshold}: {len(results)} результатов")
    
    print()


def example_4_formatting(manager: RAGManager):
    """Пример 4: Разные форматы вывода."""
    print("🎨 Пример 4: Форматирование результатов\n")
    
    query = "artificial intelligence"
    results = manager.search(query, top_k=2)
    
    # Markdown format
    print("  📝 Markdown format:")
    markdown_output = format_search_results(results, format="markdown", max_text_length=80)
    print(markdown_output[:200] + "...\n")
    
    # JSON format
    print("  📦 JSON format:")
    json_output = format_search_results(results, format="json")
    print(json_output[:200] + "...\n")


def example_5_document_management(manager: RAGManager):
    """Пример 5: Управление документами."""
    print("📋 Пример 5: Управление документами\n")
    
    # Получение статистики
    stats = manager.get_stats()
    print("  📊 Текущая статистика:")
    print(f"    - Документов: {stats['total_documents']}")
    print(f"    - Чанков: {stats['total_chunks']}")
    print(f"    - Embedding dim: {stats['embedding_dimension']}")
    
    # Удаление документа
    print("\n  🗑️ Удаление документа 'ai_guide'...")
    manager.delete_document("ai_guide")
    
    stats_after = manager.get_stats()
    print(f"  ✅ Осталось чанков: {stats_after['total_chunks']}")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️ Пример прерван")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
