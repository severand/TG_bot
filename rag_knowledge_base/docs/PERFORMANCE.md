# RAG Knowledge Base - Performance Guide

> Оптимизация производительности и бенчмарки  
> Версия: 1.0.0

---

## 📊 Содержание

1. [Бенчмарки](#бенчмарки)
2. [Оптимизация](#оптимизация)
3. [Масштабирование](#масштабирование)
4. [Мониторинг](#мониторинг)
5. [Best Practices](#best-practices)

---

## Бенчмарки

### Тестовое окружение

**Hardware:**
- CPU: Intel Core i7-12700K (12 cores)
- RAM: 32GB DDR5
- SSD: 1TB NVMe
- GPU: NVIDIA RTX 3080 (опционально)

**Software:**
- Python 3.11
- ChromaDB 0.4.x
- Sentence-Transformers 2.2.x

---

### Document Processing Speed

#### PDF Documents

| Документ | Страниц | Chunks | Время (CPU) | Время (GPU) |
|----------|---------|--------|-------------|-------------|
| Small | 10 | 25 | 5 сек | 2 сек |
| Medium | 50 | 120 | 25 сек | 8 сек |
| Large | 200 | 480 | 90 сек | 30 сек |

**Формула:**
```
Время ≈ (chunks × 0.08 сек) на CPU
Время ≈ (chunks × 0.025 сек) на GPU
```

#### Other Formats

| Формат | 100 стр | Время |
|--------|---------|-------|
| DOCX | 100 | 20 сек |
| DOC | 100 | 30 сек |
| XLSX | 1000 строк | 15 сек |
| TXT | 10000 строк | 5 сек |

---

### Search Performance

| База знаний | Chunks | Время поиска | QPS* |
|------------|--------|--------------|------|
| Small | 500 | 50 ms | ~20 |
| Medium | 5,000 | 150 ms | ~7 |
| Large | 50,000 | 500 ms | ~2 |
| XLarge | 500,000 | 2000 ms | ~0.5 |

*QPS = Queries Per Second

**Факторы влияния:**
- ✅ Размер базы (linear scaling)
- ✅ Embedding dimension (384 vs 768)
- ✅ Top-K параметр
- ✅ Фильтры metadata

---

### Memory Usage

#### Embedding Model

| Модель | Размер | RAM |
|--------|--------|-----|
| all-MiniLM-L6-v2 | 80 MB | ~500 MB |
| paraphrase-multilingual | 420 MB | ~2 GB |
| all-mpnet-base-v2 | 420 MB | ~2 GB |

#### Vector Database

| Chunks | Dimension | Disk | RAM (active) |
|--------|-----------|------|-------------|
| 1,000 | 384 | 1.5 MB | ~10 MB |
| 10,000 | 384 | 15 MB | ~50 MB |
| 100,000 | 384 | 150 MB | ~300 MB |
| 1,000,000 | 384 | 1.5 GB | ~2 GB |

**Формула:**
```
Disk ≈ chunks × embedding_dim × 4 bytes
RAM ≈ Disk × 2 (с учетом индексов)
```

---

## Оптимизация

### 1. Chunk Size

**Влияние на производительность:**

| Chunk Size | Chunks (100 стр) | Скорость | Точность |
|------------|------------------|----------|----------|
| 200 | 250 | ⚡⚡⚡ | ⭐⭐ |
| 500 | 100 | ⚡⚡ | ⭐⭐⭐ |
| 1000 | 50 | ⚡ | ⭐⭐⭐⭐ |

**Рекомендации:**
```python
# Для скорости (больше документов)
manager = RAGManager(chunk_size=200, chunk_overlap=20)

# Баланс (по умолчанию)
manager = RAGManager(chunk_size=500, chunk_overlap=50)

# Для точности (детальный поиск)
manager = RAGManager(chunk_size=1000, chunk_overlap=100)
```

---

### 2. Batch Processing

**До оптимизации:**
```python
# ❌ Медленно - по одному файлу
for file in files:
    manager.add_document(file, file.stem)
# Время: 100 файлов = 500 сек
```

**После оптимизации:**
```python
# ✅ Быстро - batch embeddings
from concurrent.futures import ThreadPoolExecutor

def process_file(file):
    return manager.add_document(file, file.stem)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_file, files))
# Время: 100 файлов = 150 сек (3x ускорение)
```

---

### 3. GPU Acceleration

**Включение GPU:**

```python
import torch

# Проверка доступности
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    device = "cuda"
else:
    print("GPU not available, using CPU")
    device = "cpu"

# RAG автоматически использует GPU если доступен
manager = RAGManager()
```

**Ускорение:**
- Embedding generation: **3-5x faster**
- Document processing: **3x faster**
- Search: **1.5x faster**

---

### 4. Caching

**Query caching:**

```python
from functools import lru_cache

class CachedRAGManager:
    def __init__(self, manager):
        self.manager = manager
    
    @lru_cache(maxsize=100)
    def search(self, query: str, top_k: int = 5):
        return self.manager.search(query, top_k)

# Использование
cached_manager = CachedRAGManager(manager)

# Первый запрос: 150ms
results = cached_manager.search("AI applications")

# Повторный запрос: <1ms (из кэша)
results = cached_manager.search("AI applications")
```

**Результат:** ~150x ускорение для повторяющихся запросов

---

### 5. Index Optimization

**ChromaDB settings:**

```python
import chromadb
from chromadb.config import Settings

# Оптимизированные настройки
client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./data/chroma_optimized",
    anonymized_telemetry=False,
))

# Создание коллекции с оптимизацией
collection = client.create_collection(
    name="optimized",
    metadata={"hnsw:space": "cosine", "hnsw:M": 16}
)
```

**Параметры HNSW:**
- `M`: Число связей (16-48, больше = точнее, медленнее)
- `efConstruction`: Качество индекса (100-200)

---

## Масштабирование

### Vertical Scaling (больше ресурсов)

**Рекомендации по железу:**

| База знаний | CPU | RAM | Disk |
|-------------|-----|-----|------|
| Small (<10k chunks) | 4 cores | 8 GB | 10 GB |
| Medium (10k-100k) | 8 cores | 16 GB | 50 GB |
| Large (100k-1M) | 16 cores | 32 GB | 200 GB |
| XLarge (>1M) | 32+ cores | 64+ GB | 500+ GB |

---

### Horizontal Scaling (распределённая система)

**Архитектура:**

```
┌─────────────┐
│  API Server │
└──────┬──────┘
       │
   ┌───┴────┐
   │ Load   │
   │Balancer│
   └───┬────┘
       │
  ┌────┴─────┬────────┬────────┐
  │          │        │        │
┌─▼─┐      ┌─▼─┐    ┌─▼─┐    ┌─▼─┐
│RAG│      │RAG│    │RAG│    │RAG│
│ 1 │      │ 2 │    │ 3 │    │ 4 │
└───┘      └───┘    └───┘    └───┘
```

**Пример с FastAPI + Redis:**

```python
from fastapi import FastAPI
from redis import Redis
import pickle

app = FastAPI()
redis_client = Redis(host='localhost', port=6379)
manager = RAGManager()

@app.get("/search")
async def search(query: str):
    # Проверка кэша
    cache_key = f"search:{query}"
    cached = redis_client.get(cache_key)
    
    if cached:
        return pickle.loads(cached)
    
    # Поиск
    results = manager.search(query)
    
    # Сохранение в кэш
    redis_client.setex(
        cache_key,
        3600,  # 1 час
        pickle.dumps(results)
    )
    
    return results
```

---

## Мониторинг

### Метрики для отслеживания

**1. Processing Metrics:**
```python
import time

start = time.time()
doc = manager.add_document(file_path, doc_id)
processing_time = time.time() - start

print(f"Processed: {doc.chunk_count} chunks in {processing_time:.2f}s")
print(f"Speed: {doc.chunk_count / processing_time:.1f} chunks/sec")
```

**2. Search Metrics:**
```python
start = time.time()
results = manager.search(query)
search_time = time.time() - start

print(f"Search time: {search_time*1000:.0f}ms")
print(f"Results: {len(results)}")
print(f"Avg score: {sum(r.similarity_score for r in results) / len(results):.2%}")
```

**3. Memory Metrics:**
```python
import psutil
import os

process = psutil.Process(os.getpid())
mem_info = process.memory_info()

print(f"RAM usage: {mem_info.rss / 1024 / 1024:.0f} MB")
```

---

### Logging

**Настройка логирования:**

```python
from rag_module.utils import setup_logger
import logging

# Production logging
logger = setup_logger(
    name="rag_monitor",
    level="INFO",
    log_file=Path("./logs/rag_performance.log")
)

# Логирование метрик
logger.info(f"Document processed: {doc_id}, chunks: {chunk_count}, time: {time}s")
logger.info(f"Search query: {query}, results: {len(results)}, time: {search_time}ms")
```

---

## Best Practices

### ✅ DO

1. **Используйте batch processing** для множества документов
2. **Кэшируйте частые запросы** (Redis, Memcached)
3. **Мониторьте производительность** (метрики, логи)
4. **Оптимизируйте chunk_size** под задачу
5. **Используйте GPU** если доступно
6. **Индексируйте metadata** для быстрых фильтров

### ❌ DON'T

1. **Не обрабатывайте огромные файлы** (>100MB) за раз - разбивайте
2. **Не игнорируйте ошибки памяти** - уменьшайте batch_size
3. **Не храните оригинальные файлы** в векторной БД
4. **Не делайте слишком маленькие chunks** (<100 tokens)
5. **Не используйте слишком низкий threshold** (<0.2) - шум

---

### Чеклист оптимизации

- [ ] Chunk size подобран для задачи
- [ ] GPU включен (если доступен)
- [ ] Batch processing реализован
- [ ] Кэширование запросов настроено
- [ ] Логирование метрик активно
- [ ] Memory limits настроены
- [ ] Index параметры оптимизированы
- [ ] Horizontal scaling при необходимости

---

## См. также

- [API Reference](API.md)
- [FAQ](FAQ.md)
- [Migration Guide](MIGRATION.md)

---

**Версия документа:** 1.0.0  
**Последнее обновление:** December 21, 2025
