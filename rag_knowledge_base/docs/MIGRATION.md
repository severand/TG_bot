# RAG Knowledge Base - Migration Guide

> Руководство по миграции между версиями  
> Версия: 1.0.0

---

## 📋 Содержание

1. [Версии и совместимость](#версии-и-совместимость)
2. [Миграция с 0.x на 1.0](#миграция-с-0x-на-10)
3. [Обновление зависимостей](#обновление-зависимостей)
4. [Миграция данных](#миграция-данных)
5. [Breaking Changes](#breaking-changes)
6. [Troubleshooting](#troubleshooting)

---

## Версии и совместимость

### Semantic Versioning

Мы используем [SemVer](https://semver.org/):
- **Major (X.0.0)**: Breaking changes
- **Minor (1.X.0)**: Новые features (backward compatible)
- **Patch (1.0.X)**: Bug fixes

### Таблица совместимости

| Версия RAG | Python | ChromaDB | Sentence-Trans |
|------------|--------|----------|----------------|
| 1.0.x | 3.9-3.11 | 0.4.x | 2.2.x |
| 0.9.x | 3.8-3.10 | 0.3.x | 2.1.x |
| 0.8.x | 3.8-3.10 | 0.3.x | 2.0.x |

---

## Миграция с 0.x на 1.0

### Что изменилось

#### 1. Структура проекта

**Было (0.x):**
```
rag/
├── rag.py
├── vector_db.py
└── embeddings.py
```

**Стало (1.0):**
```
rag_module/
├── services/
│   ├── manager.py        # Новый главный API
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   └── retriever.py
├── file_processing/      # Новый модуль
├── utils/               # Новый модуль
└── ...
```

---

#### 2. API Changes

**Было (0.x):**
```python
from rag import RAG

rag = RAG(db_path="./db")
rag.add_file("file.pdf")
results = rag.query("test")
```

**Стало (1.0):**
```python
from rag_module.services import RAGManager
from pathlib import Path

manager = RAGManager(persist_directory=Path("./db"))
manager.add_document(Path("file.pdf"), "file_001")
results = manager.search("test")
```

---

#### 3. Configuration

**Было (0.x):**
```python
rag = RAG(
    db_path="./db",
    model="miniLM",
    chunk_len=512
)
```

**Стало (1.0):**
```python
from rag_module.config import Settings

settings = Settings(
    CHUNK_SIZE=512,
    EMBEDDING_MODEL="all-MiniLM-L6-v2"
)

manager = RAGManager(
    persist_directory=Path("./db"),
    chunk_size=512
)
```

---

### Пошаговая миграция

#### Шаг 1: Backup данных

```bash
# Создать backup существующей БД
cp -r ./data/old_db ./data/old_db_backup

# Экспортировать список документов
python export_docs.py > docs_list.json
```

---

#### Шаг 2: Обновить зависимости

```bash
# Удалить старые версии
pip uninstall rag chromadb sentence-transformers

# Установить новые
pip install -r requirements.txt
```

**requirements.txt:**
```txt
chromadb>=0.4.0
sentence-transformers>=2.2.0
PyPDF2>=3.0.0
python-docx>=0.8.11
openpyxl>=3.0.0
```

---

#### Шаг 3: Миграция кода

**Скрипт миграции:**

```python
# migration_0x_to_1.py

import json
from pathlib import Path
from rag_module.services import RAGManager

def migrate():
    # 1. Загрузить старые данные
    with open("docs_list.json") as f:
        old_docs = json.load(f)
    
    # 2. Создать новый manager
    new_manager = RAGManager(
        collection_name="migrated",
        persist_directory=Path("./data/new_db")
    )
    
    # 3. Перенести документы
    for doc in old_docs:
        try:
            file_path = Path(doc["path"])
            if file_path.exists():
                new_doc = new_manager.add_document(
                    file_path=file_path,
                    doc_id=doc["id"],
                    metadata=doc.get("metadata", {})
                )
                print(f"✓ Migrated: {doc['id']}")
            else:
                print(f"✗ File not found: {file_path}")
        except Exception as e:
            print(f"✗ Error migrating {doc['id']}: {e}")
    
    print(f"\nMigration complete: {new_manager.get_stats()}")

if __name__ == "__main__":
    migrate()
```

**Запуск:**
```bash
python migration_0x_to_1.py
```

---

#### Шаг 4: Обновить код приложения

**Было:**
```python
from rag import RAG

class MyApp:
    def __init__(self):
        self.rag = RAG(db_path="./db")
    
    def add_file(self, path):
        self.rag.add_file(path)
    
    def search(self, query):
        return self.rag.query(query)
```

**Стало:**
```python
from rag_module.services import RAGManager
from pathlib import Path

class MyApp:
    def __init__(self):
        self.manager = RAGManager(
            persist_directory=Path("./db")
        )
    
    def add_file(self, path: Path, doc_id: str):
        return self.manager.add_document(path, doc_id)
    
    def search(self, query: str):
        return self.manager.search(query)
```

---

#### Шаг 5: Тестирование

```python
import pytest
from rag_module.services import RAGManager
from pathlib import Path

def test_migration():
    manager = RAGManager(
        persist_directory=Path("./data/new_db")
    )
    
    # Проверка документов
    docs = manager.list_documents()
    assert len(docs) > 0, "No documents migrated"
    
    # Проверка поиска
    results = manager.search("test query")
    assert len(results) > 0, "Search not working"
    
    print("✓ Migration tests passed")

if __name__ == "__main__":
    test_migration()
```

---

## Обновление зависимостей

### ChromaDB 0.3.x → 0.4.x

**Изменения:**
- Новый API для коллекций
- Улучшенная производительность
- HNSW индексация по умолчанию

**Migration:**
```python
# Старый код (0.3.x)
import chromadb
client = chromadb.Client()
collection = client.create_collection("docs")

# Новый код (0.4.x)
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./data/chroma"
))
collection = client.get_or_create_collection("docs")
```

---

### Sentence-Transformers 2.1.x → 2.2.x

**Изменения:**
- Новые модели
- Улучшенная точность
- Поддержка ONNX

**Migration:**
```python
# Обновление модели (опционально)
from sentence_transformers import SentenceTransformer

# Старая модель
model = SentenceTransformer('all-MiniLM-L6-v2')

# Новая модель (лучшая точность)
model = SentenceTransformer('all-mpnet-base-v2')
```

⚠️ **Важно:** Смена модели требует переиндексации всех документов!

---

## Миграция данных

### Экспорт данных из 0.x

```python
# export_old_data.py
import json
import pickle
from old_rag import RAG  # Старая версия

def export_data():
    rag = RAG(db_path="./old_db")
    
    # Получить все документы
    docs = rag.get_all_documents()
    
    export_data = []
    for doc in docs:
        export_data.append({
            "id": doc.id,
            "path": doc.path,
            "metadata": doc.metadata,
            "chunks": [
                {
                    "text": chunk.text,
                    "embedding": chunk.embedding.tolist()
                }
                for chunk in doc.chunks
            ]
        })
    
    # Сохранить в JSON
    with open("export.json", "w") as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Exported {len(export_data)} documents")

if __name__ == "__main__":
    export_data()
```

---

### Импорт в 1.0

```python
# import_to_new.py
import json
from pathlib import Path
from rag_module.services import RAGManager

def import_data():
    # Загрузить экспорт
    with open("export.json") as f:
        data = json.load(f)
    
    manager = RAGManager(
        persist_directory=Path("./new_db")
    )
    
    for doc_data in data:
        file_path = Path(doc_data["path"])
        
        if file_path.exists():
            # Переиндексировать с новой версией
            manager.add_document(
                file_path=file_path,
                doc_id=doc_data["id"],
                metadata=doc_data["metadata"]
            )
            print(f"✓ Imported: {doc_data['id']}")
        else:
            print(f"✗ File missing: {file_path}")

if __name__ == "__main__":
    import_data()
```

---

## Breaking Changes

### Version 1.0.0

#### 1. Removed methods

```python
# ❌ Удалены
rag.add_file()           # Заменён на add_document()
rag.query()              # Заменён на search()
rag.get_all()            # Заменён на list_documents()
rag.delete()             # Заменён на delete_document()

# ✅ Новые
manager.add_document()
manager.search()
manager.list_documents()
manager.delete_document()
```

---

#### 2. Changed parameters

```python
# Было
rag.query(text="query", k=5)

# Стало
manager.search(query="query", top_k=5)
```

---

#### 3. Return types

```python
# Было (0.x): dict
result = {
    "text": "...",
    "score": 0.9,
    "metadata": {}
}

# Стало (1.0): SearchResult object
result = SearchResult(
    chunk=Chunk(...),
    similarity_score=0.9,
    source_doc="file.pdf"
)

# Доступ к данным
print(result.chunk.text)
print(result.similarity_score)
print(result.source_doc)
```

---

## Troubleshooting

### Проблема: "Cannot load old database"

```python
chromadb.errors.InvalidDimensionException: Cannot load collection
```

**Решение:** Версии ChromaDB 0.3 и 0.4 несовместимы. Нужна полная переиндексация.

```bash
# 1. Экспортировать документы
python export_old_data.py

# 2. Удалить старую БД
rm -rf ./old_db

# 3. Импортировать в новую
python import_to_new.py
```

---

### Проблема: "Embeddings dimension mismatch"

```python
ValueError: Embedding dimension 384 != 768
```

**Причина:** Сменилась embedding модель.

**Решение:**
1. Использовать ту же модель:
```python
manager = RAGManager(
    embedding_model="all-MiniLM-L6-v2"  # Та же что в 0.x
)
```

2. Или переиндексировать с новой моделью:
```python
# Полная переиндексация
manager.clear_all()
for doc in old_docs:
    manager.add_document(doc.path, doc.id)
```

---

### Проблема: "Import errors"

```python
ModuleNotFoundError: No module named 'rag'
```

**Решение:** Обновить импорты:

```python
# Было
from rag import RAG
from rag.embeddings import EmbeddingService

# Стало
from rag_module.services import RAGManager
from rag_module.services.embeddings import EmbeddingService
```

---

## Rollback Plan

Если миграция не удалась:

```bash
# 1. Остановить приложение
systemctl stop myapp

# 2. Восстановить backup
rm -rf ./data/new_db
cp -r ./data/old_db_backup ./data/old_db

# 3. Откатить код
git checkout v0.9.5

# 4. Откатить зависимости
pip install -r requirements_old.txt

# 5. Запустить приложение
systemctl start myapp
```

---

## Чеклист миграции

- [ ] Backup данных создан
- [ ] Зависимости обновлены
- [ ] Код приложения обновлён
- [ ] Миграционный скрипт запущен
- [ ] Тесты пройдены
- [ ] Production проверен
- [ ] Старый backup можно удалить

---

## См. также

- [API Reference](API.md)
- [FAQ](FAQ.md)
- [Performance Guide](PERFORMANCE.md)

---

**Версия документа:** 1.0.0  
**Последнее обновление:** December 21, 2025
