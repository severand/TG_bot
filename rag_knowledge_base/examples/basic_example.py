#!/usr/bin/env python3
"""Basic example of using RAG Knowledge Base.

Простой пример использования RAG базы знаний.

Использование:
    python basic_example.py
"""

import sys
from pathlib import Path

# Добавляем parent directory в Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_module.services import RAGManager
from rag_module.utils import format_search_results, format_stats


def main():
    """Основной пример работы с RAG."""
    
    print("🚀 RAG Knowledge Base - Basic Example")
    print("="*50)
    
    # ========== 1. Инициализация ==========
    print("\n🛠️  Step 1: Инициализация RAG Manager...")
    
    manager = RAGManager(
        collection_name="basic_demo",
        persist_directory=Path("./data/demo_db"),
    )
    
    print("✅ RAG Manager готов к работе!")
    
    # ========== 2. Добавление документов ==========
    print("\n📄 Step 2: Добавление документов...")
    
    # Проверяем есть ли sample documents
    sample_docs_dir = Path(__file__).parent / "sample_documents"
    
    if not sample_docs_dir.exists():
        print("⚠️  Sample documents не найдены. Создаём тестовый документ...")
        
        # Создаём тестовый текстовый файл
        sample_docs_dir.mkdir(parents=True, exist_ok=True)
        test_file = sample_docs_dir / "ai_basics.txt"
        
        test_content = """
Artificial Intelligence Basics

Artificial Intelligence (AI) is the simulation of human intelligence by machines.
Machine learning is a subset of AI that enables systems to learn from data.

Deep learning uses neural networks with multiple layers to process information.
Natural Language Processing (NLP) allows computers to understand human language.

AI applications include:
- Image recognition
- Speech recognition
- Recommendation systems
- Autonomous vehicles
- Medical diagnosis

The future of AI holds enormous potential for transforming industries.
"""
        
        test_file.write_text(test_content, encoding='utf-8')
        print(f"✅ Создан тестовый файл: {test_file}")
    
    # Добавляем все файлы из sample_documents/
    files_added = 0
    for file_path in sample_docs_dir.glob("*"):
        if file_path.is_file() and file_path.suffix in [".txt", ".pdf", ".docx", ".doc"]:
            try:
                doc_id = file_path.stem  # Используем имя файла как ID
                
                print(f"  📥 Добавляем: {file_path.name}...")
                
                document = manager.add_document(
                    file_path=file_path,
                    doc_id=doc_id,
                    metadata={"source": file_path.name, "type": "demo"},
                )
                
                print(f"    ✅ Добавлено: {document.chunk_count} chunks")
                files_added += 1
                
            except Exception as e:
                print(f"    ❌ Ошибка: {e}")
    
    if files_added == 0:
        print("⚠️  Нет файлов для добавления")
        return
    
    print(f"\n✅ Добавлено файлов: {files_added}")
    
    # ========== 3. Просмотр статистики ==========
    print("\n📊 Step 3: Статистика базы знаний...")
    
    stats = manager.get_stats()
    print(format_stats(stats, format="plain"))
    
    # ========== 4. Поиск по базе ==========
    print("\n🔍 Step 4: Поиск по базе знаний...")
    
    queries = [
        "What is artificial intelligence?",
        "Tell me about machine learning",
        "What are AI applications?",
    ]
    
    for query in queries:
        print(f"\n💬 Query: '{query}'")
        print("-" * 50)
        
        results = manager.search(
            query=query,
            top_k=3,
            similarity_threshold=0.3,
        )
        
        if results:
            print(format_search_results(results, format="plain", max_text_length=150))
        else:
            print("🔍 Ничего не найдено")
    
    # ========== 5. Фильтрация ==========
    print("\n🔍 Step 5: Поиск с фильтром...")
    
    query = "neural networks"
    print(f"\n💬 Query: '{query}' (filter: type=demo)")
    print("-" * 50)
    
    results = manager.search(
        query=query,
        top_k=5,
        filter_metadata={"type": "demo"},
    )
    
    if results:
        print(f"✅ Найдено: {len(results)} результатов")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. Score: {result.similarity_score:.2%} | {result.chunk.text[:100]}...")
    else:
        print("🔍 Ничего не найдено")
    
    # ========== 6. Завершение ==========
    print("\n" + "="*50)
    print("🎉 Пример завершён!")
    print("\n💡 Следующие шаги:")
    print("  - Посмотрите advanced_example.py для продвинутых фич")
    print("  - Добавьте свои документы в sample_documents/")
    print("  - Интегрируйте в свой проект!")
    print("="*50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
