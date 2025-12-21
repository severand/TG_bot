#!/usr/bin/env python3
"""Простой пример использования RAG модуля.

Показывает базовые операции:
- Загрузка документа
- Поиск по базе знаний
- Просмотр статистики
"""

from pathlib import Path
from rag_module.services import RAGManager
from rag_module.utils import format_search_results, format_stats


def main():
    """Главная функция."""
    print("🚀 RAG Module - Базовый пример\n")
    
    # 1. Инициализация
    print("✅ Инициализация RAGManager...")
    manager = RAGManager()
    print("✅ Готово!\n")
    
    # 2. Просмотр статистики
    print("📊 Статистика системы:")
    stats = manager.get_stats()
    print(format_stats(stats, format="plain"))
    print()
    
    # 3. Пример добавления документа
    print("📄 Пример использования:")
    print("""
    # Добавить документ
    doc = manager.add_document(
        file_path=Path("contract.pdf"),
        doc_id="contract_001",
        metadata={"type": "contract", "year": 2025}
    )
    
    # Поиск
    results = manager.search("условия оплаты", top_k=5)
    
    # Показать результаты
    print(format_search_results(results))
    
    # Список документов
    documents = manager.list_documents()
    for doc in documents:
        print(f"📄 {doc.filename} ({doc.chunk_count} chunks)")
    """)
    
    print("\n✅ Пример завершён!")
    print("📚 См. advanced_example.py для более сложных примеров")


if __name__ == "__main__":
    main()
