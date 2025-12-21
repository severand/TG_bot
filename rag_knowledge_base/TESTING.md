# RAG Module - Инструкция по тестированию

> Полное руководство по проверке работоспособности RAG модуля

---

## 📊 Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Автоматическое тестирование](#автоматическое-тестирование)
3. [Ручное тестирование](#ручное-тестирование)
4. [Unit тесты](#unit-тесты)
5. [Что проверяем](#что-проверяем)
6. [Troubleshooting](#troubleshooting)

---

## Быстрый старт

### Шаг 1: Установка зависимостей

```bash
cd rag_knowledge_base/
pip install -r requirements.txt
```

**Основные зависимости:**
- `chromadb>=0.4.0` - векторная БД
- `sentence-transformers>=2.2.0` - embeddings
- `PyPDF2>=3.0.0` - PDF парсинг
- `python-docx>=0.8.11` - DOCX парсинг
- `openpyxl>=3.0.0` - Excel парсинг

---

### Шаг 2: Запуск тестового скрипта

```bash
python test_rag_functionality.py
```

**Ожидаемый результат:**
```
############################################################
#                                                          #
#              RAG MODULE FUNCTIONALITY TEST               #
#                                                          #
############################################################

============================================================
TEST 1: Checking imports...
============================================================
✅ All imports successful!

============================================================
TEST 2: Checking configuration...
============================================================
✅ Config loaded:
   - Embedding model: all-MiniLM-L6-v2
   - Chunk size: 500
   - Vector DB: ./data/chroma_db
   - Collection: rag_documents

...

============================================================
TEST SUMMARY
============================================================
✅ PASSED: Imports
✅ PASSED: Configuration
✅ PASSED: FileConverter
✅ PASSED: Chunker
✅ PASSED: Embeddings
✅ PASSED: RAG Manager Init
✅ PASSED: Full Pipeline
============================================================
TOTAL: 7/7 tests passed
🎉 ALL TESTS PASSED! RAG MODULE IS READY!
```

---

## Автоматическое тестирование

### Что проверяет `test_rag_functionality.py`?

| # | Тест | Проверяет |
|---|------|------------|
| 1 | **Imports** | Все модули импортируются |
| 2 | **Configuration** | Конфигурация загружается |
| 3 | **FileConverter** | Парсер поддерживает форматы |
| 4 | **Chunker** | Разбиение текста на чанки |
| 5 | **Embeddings** | Генерация векторов |
| 6 | **RAG Manager Init** | Инициализация менеджера |
| 7 | **Full Pipeline** | Полный цикл: загрузка + поиск |

---

### Детали теста "Full Pipeline"

Этот тест проверяет **всю цепочку** обработки:

1. Создаёт тестовый файл `test_document.txt`
2. Добавляет его в RAG через `add_document()`
3. Выполняет 3 тестовых запроса:
   - "возможности системы"
   - "технологии и библиотеки"
   - "семантический поиск"
4. Проверяет качество результатов
5. Удаляет тестовые данные

---

## Ручное тестирование

### Пример 1: Добавление документа

```python
from pathlib import Path
from rag_module.services import RAGManager

# Инициализация
manager = RAGManager()

# Добавить документ
doc = manager.add_document(
    file_path=Path("my_document.pdf"),
    doc_id="doc_001",
    metadata={"type": "manual", "author": "test"}
)

print(f"✅ Документ добавлен: {doc.id}")
print(f"   - Чанков: {doc.chunk_count}")
print(f"   - Размер: {doc.file_size} байт")
```

---

### Пример 2: Поиск

```python
# Поиск
results = manager.search(
    query="условия оплаты",
    top_k=5,
    min_similarity=0.5
)

for i, result in enumerate(results, 1):
    print(f"\n{i}. Score: {result.similarity_score:.2%}")
    print(f"   Source: {result.source_doc}")
    print(f"   Text: {result.chunk.text[:200]}...")
```

---

### Пример 3: Статистика

```python
# Получить статистику
stats = manager.get_stats()

print(f"📊 Статистика:")
print(f"   - Документов: {stats['total_documents']}")
print(f"   - Чанков: {stats['total_chunks']}")
print(f"   - Embedding dimension: {stats['embedding_dimension']}")

# Список документов
docs = manager.list_documents()
for doc in docs:
    print(f"   - {doc.id}: {doc.filename} ({doc.chunk_count} chunks)")
```

---

## Unit тесты

### Запуск pytest

```bash
# Все тесты
pytest tests/ -v

# Конкретный модуль
pytest tests/test_file_processing/ -v
pytest tests/test_services/ -v

# С coverage
pytest tests/ --cov=rag_module --cov-report=html
```

---

### Структура тестов

```
tests/
├── test_file_processing/
│   ├── test_converter.py       # Тесты FileConverter
│   ├── test_pdf_parser.py      # Тесты PDF парсера
│   ├── test_docx_parser.py     # Тесты DOCX парсера
│   └── test_excel_parser.py    # Тесты Excel парсера
│
├── test_services/
│   ├── test_chunker.py         # Тесты Chunker
│   ├── test_embeddings.py      # Тесты EmbeddingService
│   ├── test_vector_store.py    # Тесты ChromaVectorStore
│   ├── test_retriever.py       # Тесты Retriever
│   └── test_manager.py         # Тесты RAGManager
│
└── test_integration.py         # Интеграционные тесты
```

---

## Что проверяем

### ✅ File Processing

- [x] **PDF парсинг** - извлечение текста из PDF
- [x] **DOCX парсинг** - параграфы + таблицы
- [x] **DOC парсинг** - старый формат Word
- [x] **Excel парсинг** - XLSX + XLS
- [x] **TXT файлы** - UTF-8 + fallback
- [x] **ZIP архивы** - распаковка + обработка

---

### ✅ Services

- [x] **Chunker** - разбиение на чанки с overlap
- [x] **EmbeddingService** - генерация 384D векторов
- [x] **ChromaVectorStore** - сохранение + поиск
- [x] **Retriever** - semantic search с фильтрами
- [x] **RAGManager** - оркестрация всех компонентов

---

### ✅ Integration

- [x] **Полный pipeline** - от файла до поиска
- [x] **Метаданные** - сохранение + фильтрация
- [x] **Удаление** - документов из БД
- [x] **Реестр** - сохранение + загрузка

---

## Troubleshooting

### Проблема 1: Ошибка импорта

```python
ModuleNotFoundError: No module named 'rag_module'
```

**Решение:**
```bash
# Убедитесь что вы в правильной директории
cd rag_knowledge_base/
python test_rag_functionality.py

# Или добавьте в PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/TG_bot/rag_knowledge_base"
```

---

### Проблема 2: ChromaDB ошибка

```python
chromadb.errors.InvalidDimensionException
```

**Решение:**
```bash
# Очистить старую БД
rm -rf ./data/chroma_db
python test_rag_functionality.py
```

---

### Проблема 3: Нет GPU

```python
WARNING: CUDA not available, using CPU
```

**Не проблема!** CPU режим работает отлично, просто медленнее.

Если нужен GPU:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

### Проблема 4: Out of Memory

```python
OSError: [Errno 12] Cannot allocate memory
```

**Решение:**
```python
# Уменьшить batch size в config.py
class Settings(BaseSettings):
    EMBEDDING_BATCH_SIZE: int = 8  # Вместо 32
```

---

## Чеклист тестирования

### Перед production:

- [ ] Все 7 тестов `test_rag_functionality.py` прошли
- [ ] Unit тесты pytest прошли
- [ ] Проверены все форматы файлов
- [ ] Поиск возвращает релевантные результаты
- [ ] Метаданные сохраняются правильно
- [ ] Удаление работает
- [ ] Реестр документов восстанавливается

---

## См. также

- [README.md](README.md) - Общий обзор
- [DEVELOPMENT.md](DEVELOPMENT.md) - Гайд разработчика
- [docs/FAQ.md](docs/FAQ.md) - Частые вопросы
- [docs/PERFORMANCE.md](docs/PERFORMANCE.md) - Оптимизация

---

**Версия документа:** 1.0.0  
**Последнее обновление:** December 21, 2025
