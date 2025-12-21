"""Basic RAG usage example.

Простой пример использования RAG модуля для новичков.
Показывает базовые операции: добавление документов и поиск.
"""

import sys
from pathlib import Path

# Добавляем RAG модуль в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_module.services import RAGManager
from rag_module.utils import format_search_results, format_stats


def main():
    """Главная функция примера."""
    print("✨ RAG Basic Example - Простой пример\n")
    
    # Шаг 1: Инициализация RAG Manager
    print("🚀 Шаг 1: Инициализация RAG Manager...")
    manager = RAGManager(
        persist_directory=Path("./rag_data"),  # Где хранить данные
        collection_name="basic_example",  # Имя коллекции
    )
    print("✅ RAG Manager готов!\n")
    
    # Шаг 2: Добавление документа
    print("📄 Шаг 2: Добавление тестового документа...")
    
    # Проверяем есть ли тестовые файлы
    sample_dir = Path(__file__).parent / "sample_documents"
    
    if sample_dir.exists():
        # Ищем PDF файлы
        pdf_files = list(sample_dir.glob("*.pdf"))
        if pdf_files:
            doc_path = pdf_files[0]
            print(f"  Используем файл: {doc_path.name}")
            
            document = manager.add_document(
                file_path=doc_path,
                doc_id="sample_doc_001",
                metadata={
                    "source": "example",
                    "type": "tutorial",
                },
            )
            
            print(f"  ✅ Документ добавлен: {document.filename}")
            print(f"  📂 Создано чанков: {document.chunk_count}\n")
        else:
            print("  ⚠️ PDF файлы не найдены. Создаем тестовый документ...\n")
            create_test_document(manager)
    else:
        print("  ⚠️ Папка sample_documents не найдена. Создаем тестовый документ...\n")
        create_test_document(manager)
    
    # Шаг 3: Поиск
    print("🔍 Шаг 3: Поиск по базе знаний...")
    
    queries = [
        "Что такое искусственный интеллект?",
        "What is machine learning?",
        "Как работает RAG?",
    ]
    
    for query in queries:
        print(f"\n💬 Запрос: '{query}'")
        
        results = manager.search(
            query=query,
            top_k=3,  # Вернуть топ-3 результата
        )
        
        if results:
            print(f"  ✅ Найдено: {len(results)} результатов")
            
            for idx, result in enumerate(results, 1):
                print(f"\n  [{idx}] 📊 Relevance: {result.similarity_score:.1%}")
                print(f"      📄 Source: {result.source_doc}")
                print(f"      📝 Text: {result.chunk.text[:150]}...")
        else:
            print("  ❌ Ничего не найдено")
    
    # Шаг 4: Статистика
    print("\n\n📊 Шаг 4: Статистика системы")
    stats = manager.get_stats()
    print(format_stats(stats, format="plain"))
    
    print("\n\n✨ Пример завершен!")
    print("💡 Tip: Измените запросы и запустите снова!")


def create_test_document(manager: RAGManager):
    """Создать тестовый документ из текста."""
    from rag_module.models import Document, Chunk
    from datetime import datetime
    
    # Создаем тестовый документ с чанками
    test_texts = [
        "Искусственный интеллект (AI) - это область компьютерных наук, которая занимается созданием интеллектуальных машин.",
        "Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed.",
        "RAG (Retrieval-Augmented Generation) - это метод комбинирования поиска информации с генерацией ответов.",
        "Vector embeddings are numerical representations of text that capture semantic meaning.",
        "Семантический поиск позволяет находить документы по смыслу, а не только по ключевым словам.",
    ]
    
    chunks = []
    for idx, text in enumerate(test_texts):
        chunk = Chunk(
            id=f"test_chunk_{idx}",
            doc_id="test_document",
            text=text,
            position=idx,
            metadata={"source": "generated"},
        )
        chunks.append(chunk)
    
    # Добавляем чанки напрямую
    manager.retriever.add_chunks(chunks)
    
    print(f"  ✅ Создан тестовый документ с {len(chunks)} чанками\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️ Пример прерван")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
