# RAG Knowledge Base - API Reference

> Полный справочник по API RAG модуля  
> Версия: 1.0.0  
> Дата: December 2025

---

## 📚 Содержание

1. [RAGManager](#ragmanager) - Главный API
2. [Document Operations](#document-operations)
3. [Search Operations](#search-operations)
4. [Utilities](#utilities)
5. [Configuration](#configuration)
6. [Exceptions](#exceptions)

---

## RAGManager

### Инициализация

```python
from rag_module.services import RAGManager
from pathlib import Path

manager = RAGManager(
    collection_name="my_knowledge_base",
    persist_directory=Path("./data/rag_db"),
    similarity_threshold=0.5,
    chunk_size=500,
    chunk_overlap=50,
)
```

#### Параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `collection_name` | `str` | `"knowledge_base"` | Имя коллекции в векторной БД |
| `persist_directory` | `Path` | `"./data/chroma_db"` | Путь к папке с БД |
| `similarity_threshold` | `float` | `0.5` | Порог схожести (0-1) |
| `chunk_size` | `int` | `500` | Размер чанка в токенах |
| `chunk_overlap` | `int` | `50` | Перекрытие между чанками |

---

## Document Operations

### add_document()

Добавить документ в базу знаний.

```python
document = manager.add_document(
    file_path=Path("contract.pdf"),
    doc_id="contract_2024_001",
    metadata={
        "type": "legal",
        "year": 2024,
        "department": "sales"
    }
)
```

#### Параметры

- **file_path** (`Path`): Путь к файлу
- **doc_id** (`str`): Уникальный ID документа
- **metadata** (`dict`, optional): Метаданные

#### Возвращает

`Document` объект:

```python
{
    "id": "contract_2024_001",
    "filename": "contract.pdf",
    "file_size": 1024000,
    "chunk_count": 15,
    "created_at": "2024-12-21T10:30:00",
    "metadata": {...}
}
```

#### Поддерживаемые форматы

- ✅ PDF (`.pdf`)
- ✅ Word DOCX (`.docx`)
- ✅ Word DOC (`.doc`) - старый формат
- ✅ Excel (`.xlsx`, `.xls`)
- ✅ Text (`.txt`)
- ✅ ZIP архивы (`.zip`)

#### Исключения

- `FileNotFoundError`: Файл не найден
- `ParsingError`: Ошибка парсинга
- `ValidationError`: Невалидный doc_id или metadata

---

### get_document()

Получить информацию о документе.

```python
doc = manager.get_document("contract_2024_001")
```

#### Параметры

- **doc_id** (`str`): ID документа

#### Возвращает

`Document` объект или `None` если не найден.

---

### delete_document()

Удалить документ из базы.

```python
manager.delete_document("contract_2024_001")
```

#### Параметры

- **doc_id** (`str`): ID документа

#### Возвращает

`bool`: `True` если удалён, `False` если не найден

---

### list_documents()

Получить список всех документов.

```python
docs = manager.list_documents()
# Возвращает: List[Document]
```

---

## Search Operations

### search()

Поиск по базе знаний.

```python
results = manager.search(
    query="условия оплаты по договору",
    top_k=5,
    similarity_threshold=0.6,
    filter_metadata={"type": "legal", "year": 2024}
)
```

#### Параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `query` | `str` | **required** | Поисковый запрос |
| `top_k` | `int` | `5` | Количество результатов |
| `similarity_threshold` | `float` | из config | Минимальная схожесть |
| `filter_metadata` | `dict` | `None` | Фильтр по метаданным |

#### Возвращает

`List[SearchResult]`:

```python
[
    SearchResult(
        chunk=Chunk(...),
        similarity_score=0.89,
        source_doc="contract.pdf"
    ),
    ...
]
```

#### Пример использования

```python
# Простой поиск
results = manager.search("machine learning")

# С фильтром
results = manager.search(
    query="AI applications",
    filter_metadata={"department": "research"}
)

# Высокий порог качества
results = manager.search(
    query="deep learning",
    top_k=10,
    similarity_threshold=0.8
)
```

---

## Utilities

### get_stats()

Получить статистику базы знаний.

```python
stats = manager.get_stats()
```

#### Возвращает

```python
{
    "total_documents": 15,
    "total_chunks": 342,
    "embedding_dimension": 384,
    "similarity_threshold": 0.5,
    "documents": [
        {
            "id": "doc_001",
            "filename": "report.pdf",
            "chunks": 25,
            "size": 1024000
        },
        ...
    ]
}
```

---

### clear_all()

Очистить всю базу знаний (ОПАСНО!).

```python
manager.clear_all()
```

⚠️ **Предупреждение**: Удаляет все документы безвозвратно!

---

## Configuration

### Settings

```python
from rag_module.config import Settings, get_settings

# Получить текущие настройки
settings = get_settings()

# Создать кастомные настройки
custom_settings = Settings(
    CHUNK_SIZE=1000,
    CHUNK_OVERLAP=100,
    EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    SIMILARITY_THRESHOLD=0.7,
)
```

#### Параметры конфигурации

| Параметр | Тип | По умолчанию |
|----------|-----|--------------|
| `CHUNK_SIZE` | `int` | `500` |
| `CHUNK_OVERLAP` | `int` | `50` |
| `EMBEDDING_MODEL` | `str` | `"all-MiniLM-L6-v2"` |
| `SIMILARITY_THRESHOLD` | `float` | `0.5` |
| `MAX_FILE_SIZE` | `int` | `100 * 1024 * 1024` |

---

## Exceptions

### Иерархия исключений

```
RAGException (base)
├── ParsingError
│   ├── PDFParsingError
│   ├── DOCXParsingError
│   └── ExcelParsingError
├── EmbeddingError
├── VectorStoreError
├── RetrieverError
└── ValidationError
```

### Обработка ошибок

```python
from rag_module.exceptions import RAGException, ParsingError

try:
    doc = manager.add_document(file_path, "doc_001")
except ParsingError as e:
    print(f"Ошибка парсинга: {e}")
except ValidationError as e:
    print(f"Ошибка валидации: {e}")
except RAGException as e:
    print(f"Общая ошибка RAG: {e}")
```

---

## Примеры использования

### Полный пример

```python
from rag_module.services import RAGManager
from pathlib import Path

# 1. Инициализация
manager = RAGManager(
    collection_name="company_docs",
    persist_directory=Path("./data/kb"),
)

# 2. Добавление документов
for file in Path("./documents").glob("*.pdf"):
    doc = manager.add_document(
        file_path=file,
        doc_id=file.stem,
        metadata={"type": "report"},
    )
    print(f"Added: {doc.filename} ({doc.chunk_count} chunks)")

# 3. Поиск
query = "What are the quarterly sales figures?"
results = manager.search(query, top_k=5)

# 4. Вывод результатов
for result in results:
    print(f"[{result.similarity_score:.2%}] {result.chunk.text[:200]}")

# 5. Статистика
stats = manager.get_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Total chunks: {stats['total_chunks']}")
```

---

## Best Practices

### 1. Именование doc_id

```python
# ✅ ХОРОШО
doc_id = "contract_2024_Q4_001"
doc_id = "report-sales-2024-12"

# ❌ ПЛОХО
doc_id = "doc1"  # Неинформативно
doc_id = "My Document!"  # Спецсимволы
```

### 2. Использование метаданных

```python
# ✅ ХОРОШО - структурированные метаданные
metadata = {
    "type": "contract",
    "year": 2024,
    "department": "sales",
    "priority": "high",
}

# ❌ ПЛОХО - неструктурированные данные
metadata = {
    "info": "some contract from 2024",  # Неструктурировано
}
```

### 3. Обработка ошибок

```python
# ✅ ХОРОШО
try:
    doc = manager.add_document(file_path, doc_id)
except ParsingError as e:
    logger.error(f"Failed to parse {file_path}: {e}")
    # Обработка ошибки
except ValidationError as e:
    logger.error(f"Invalid input: {e}")
    # Обработка ошибки

# ❌ ПЛОХО
try:
    doc = manager.add_document(file_path, doc_id)
except Exception:  # Слишком общее
    pass  # Игнорирование ошибок
```

---

## См. также

- [FAQ](FAQ.md) - Частые вопросы
- [PERFORMANCE](PERFORMANCE.md) - Оптимизация производительности
- [MIGRATION](MIGRATION.md) - Миграция версий

---

**Версия документа:** 1.0.0  
**Последнее обновление:** December 21, 2025
