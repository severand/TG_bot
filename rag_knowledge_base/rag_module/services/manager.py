"""RAG Manager - main orchestrator for RAG pipeline with async support.

Главный оркестратор всего RAG модуля. Объединяет все сервисы:
- FileConverter (парсинг документов)
- Chunker (разбиение на чанки)
- EmbeddingService (генерация embeddings)
- ChromaVectorStore (хранение векторов)
- Retriever (семантический поиск)

Основной интерфейс для работы с RAG системой:
- add_document() / add_document_async() - загружить документ
- search() / search_async() - поиск по базе знаний
- list_documents() - список документов
- delete_document() - удалить документ
- clear_all() - очистить базу
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from rag_module.config import get_config
from rag_module.models import Document, Chunk, SearchResult
from rag_module.file_processing import FileConverter
from rag_module.services.chunker import Chunker
from rag_module.services.embeddings import EmbeddingService
from rag_module.services.vector_store import ChromaVectorStore
from rag_module.services.retriever import Retriever
from rag_module.exceptions import RAGException

logger = logging.getLogger(__name__)


class RAGManagerError(RAGException):
    """Ошибка в работе RAG Manager."""


class DocumentNotFoundError(RAGException):
    """Документ не найден."""


class RAGManager:
    """Главный менеджер RAG системы.

    Координирует все компоненты RAG pipeline:
    - Парсинг документов (FileConverter)
    - Chunking (Chunker)
    - Embeddings (EmbeddingService)
    - Vector storage (ChromaVectorStore)
    - Semantic search (Retriever)

    Предоставляет синхронные и асинхронные методы.

    Attributes:
        file_converter: Конвертер файлов
        chunker: Сервис разбиения на чанки
        embedding_service: Сервис генерации embeddings
        vector_store: Векторное хранилище
        retriever: Сервис поиска
        documents_registry_path: Путь к реестру документов
    """

    REGISTRY_FILENAME = "documents_registry.json"

    def __init__(
        self,
        file_converter: Optional[FileConverter] = None,
        chunker: Optional[Chunker] = None,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[ChromaVectorStore] = None,
        retriever: Optional[Retriever] = None,
    ) -> None:
        """Инициализация RAG Manager.

        Args:
            file_converter: Конвертер файлов (создаётся автоматически)
            chunker: Чанкер (создаётся автоматически)
            embedding_service: Сервис embeddings (создаётся автоматически)
            vector_store: Векторное хранилище (создаётся автоматически)
            retriever: Retriever (создаётся автоматически)

        Raises:
            RAGManagerError: Если не удалось инициализировать компоненты
        """
        config = get_config()
        self.documents_registry_path = Path(config.vector_db_path) / self.REGISTRY_FILENAME

        try:
            logger.info("Initializing RAG Manager components...")

            # Инициализация компонентов
            self.file_converter = file_converter or FileConverter()
            self.chunker = chunker or Chunker()
            self.embedding_service = embedding_service or EmbeddingService()
            self.vector_store = vector_store or ChromaVectorStore()
            self.retriever = retriever or Retriever(
                embedding_service=self.embedding_service,
                vector_store=self.vector_store,
            )

            # Сохраняем config для использования в асинхронных методах
            self.config = config

            # Создаём директорию для реестра если нужно
            self.documents_registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Загружаем существующий реестр или создаём новый
            self._load_or_create_registry()

            logger.info("✓ RAG Manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG Manager: {e}")
            raise RAGManagerError(f"Cannot initialize RAG Manager: {e}") from e

    # ---------- Публичные API методы ----------

    def add_document(
        self,
        file_path: Path,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Добавить документ в базу знаний (синхронно).

        Полный pipeline:
        1. Парсинг файла -> текст
        2. Chunking -> список чанков
        3. Embeddings -> вектора для каждого чанка
        4. Сохранение в vector store
        5. Обновление реестра документов

        Args:
            file_path: Путь к файлу
            doc_id: Уникальный идентификатор документа
            metadata: Дополнительные метаданные

        Returns:
            Document объект с полной информацией

        Raises:
            RAGManagerError: Если не удалось обработать документ
        """
        if not file_path.exists():
            raise RAGManagerError(f"File not found: {file_path}")

        logger.info(f"Processing document: {file_path.name} (id={doc_id})")

        try:
            # 1. Парсинг документа
            logger.debug("Step 1: Extracting text...")
            text = self.file_converter.extract_text(file_path)
            if not text or not text.strip():
                raise RAGManagerError(f"No text extracted from {file_path.name}")

            # 2. Chunking
            logger.debug("Step 2: Chunking text...")
            base_metadata = metadata or {}
            base_metadata["source_file"] = file_path.name
            base_metadata["file_size"] = file_path.stat().st_size

            chunks = self.chunker.chunk_text(
                text=text,
                doc_id=doc_id,
                base_metadata=base_metadata,
            )

            if not chunks:
                raise RAGManagerError("No chunks created from document")

            logger.info(f"Created {len(chunks)} chunks")

            # 3. Генерация embeddings
            logger.debug("Step 3: Generating embeddings...")
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.embed_batch(texts)

            # Присваиваем embeddings чанкам
            for i, chunk in enumerate(chunks):
                chunk.embedding = embeddings[i].tolist()

            # 4. Сохранение в vector store
            logger.debug("Step 4: Storing in vector database...")
            self.vector_store.add_chunks(chunks)

            # 5. Создание Document объекта
            document = Document(
                id=doc_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_size=file_path.stat().st_size,
                chunk_count=len(chunks),
                created_at=datetime.now().isoformat(),
                metadata=base_metadata,
            )

            # 6. Обновление реестра
            self._add_to_registry(document)

            logger.info(
                f"✓ Document added successfully: {doc_id} "
                f"({len(chunks)} chunks, {len(text)} chars)"
            )
            return document

        except Exception as e:
            logger.error(f"Error adding document: {e}")
            # Откатываем изменения в vector store если что-то пошло не так
            try:
                self.vector_store.delete_by_doc_id(doc_id)
            except Exception:
                pass
            raise RAGManagerError(f"Failed to add document: {e}") from e

    async def add_document_async(
        self,
        file_path: Path,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Добавить документ в базу знаний (асинхронно, неблокирующе).

        Запускает синхронное add_document в thread pool.
        Отлично для работы с Telegram ботом на больших документах.

        Args:
            file_path: Путь к файлу
            doc_id: Уникальный идентификатор документа
            metadata: Дополнительные метаданные

        Returns:
            Document объект с полной информацией

        Raises:
            RAGManagerError: Если не удалось обработать документ
        """
        try:
            # Запускаем в thread pool, не блокируем event loop
            document = await asyncio.to_thread(
                self.add_document,
                file_path,
                doc_id,
                metadata,
            )
            return document
        except Exception as e:
            logger.error(f"Error adding document async: {e}")
            raise RAGManagerError(f"Failed to add document async: {e}") from e

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[SearchResult]:
        """Поиск по базе знаний (синхронно).

        Args:
            query: Текстовый запрос
            top_k: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным
            min_similarity: Минимальная схожесть (0-1)

        Returns:
            Список SearchResult отсортированный по relevance

        Raises:
            RAGManagerError: Если поиск не удался
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []

        try:
            logger.info(f"Searching: '{query[:50]}...' (top_k={top_k})")
            results = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                filter_metadata=filter_metadata,
                min_similarity=min_similarity,
            )
            logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search error: {e}")
            raise RAGManagerError(f"Search failed: {e}") from e

    async def search_async(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[SearchResult]:
        """Поиск по базе знаний (асинхронно, неблокирующе).

        Запускает синхронный search в thread pool.

        Args:
            query: Текстовый запрос
            top_k: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным
            min_similarity: Минимальная схожесть (0-1)

        Returns:
            Список SearchResult отсортированный по relevance

        Raises:
            RAGManagerError: Если поиск не удался
        """
        try:
            # Запускаем в thread pool, не блокируем event loop
            results = await asyncio.to_thread(
                self.search,
                query,
                top_k,
                filter_metadata,
                min_similarity,
            )
            return results
        except Exception as e:
            logger.error(f"Search error async: {e}")
            raise RAGManagerError(f"Search failed async: {e}") from e

    def list_documents(self) -> List[Document]:
        """Получить список всех документов.

        Returns:
            Список Document объектов
        """
        return list(self._registry.values())

    def get_document(self, doc_id: str) -> Document:
        """Получить информацию о документе.

        Args:
            doc_id: ID документа

        Returns:
            Document объект

        Raises:
            DocumentNotFoundError: Если документ не найден
        """
        if doc_id not in self._registry:
            raise DocumentNotFoundError(f"Document not found: {doc_id}")
        return self._registry[doc_id]

    def delete_document(self, doc_id: str) -> None:
        """Удалить документ из базы знаний.

        Args:
            doc_id: ID документа

        Raises:
            DocumentNotFoundError: Если документ не найден
            RAGManagerError: Если удаление не удалось
        """
        if doc_id not in self._registry:
            raise DocumentNotFoundError(f"Document not found: {doc_id}")

        try:
            logger.info(f"Deleting document: {doc_id}")

            # Удаляем из vector store
            self.vector_store.delete_by_doc_id(doc_id)

            # Удаляем из реестра
            del self._registry[doc_id]
            self._save_registry()

            logger.info(f"✓ Document deleted: {doc_id}")

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise RAGManagerError(f"Failed to delete document: {e}") from e

    def clear_all(self) -> None:
        """Очистить всю базу знаний.

        Удаляет все документы и чанки.

        Raises:
            RAGManagerError: Если очистка не удалась
        """
        try:
            logger.warning("Clearing all data...")

            # Очищаем vector store
            self.vector_store.clear_all()

            # Очищаем реестр
            self._registry = {}
            self._save_registry()

            logger.info("✓ All data cleared")

        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            raise RAGManagerError(f"Failed to clear data: {e}") from e

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику RAG системы.

        Returns:
            Словарь со статистикой
        """
        retriever_stats = self.retriever.get_stats()
        return {
            "total_documents": len(self._registry),
            "total_chunks": self.vector_store.count(),
            "embedding_dimension": retriever_stats["embedding_dimension"],
            "similarity_threshold": retriever_stats["similarity_threshold"],
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "chunks": doc.chunk_count,
                    "size": doc.file_size,
                }
                for doc in self._registry.values()
            ],
        }

    # ---------- Внутренние методы ----------

    def _load_or_create_registry(self) -> None:
        """Загружить существующий реестр или создать новый."""
        if self.documents_registry_path.exists():
            try:
                with open(self.documents_registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._registry = {
                        doc_id: Document(**doc_data)
                        for doc_id, doc_data in data.items()
                    }
                logger.info(f"Loaded {len(self._registry)} documents from registry")
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}. Creating new one.")
                self._registry = {}
        else:
            self._registry = {}
            logger.info("Created new documents registry")

    def _save_registry(self) -> None:
        """Сохранить реестр на диск."""
        try:
            data = {
                doc_id: {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at,
                    "metadata": doc.metadata,
                }
                for doc_id, doc in self._registry.items()
            }
            with open(self.documents_registry_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Registry saved")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise RAGManagerError(f"Cannot save registry: {e}") from e

    def _add_to_registry(self, document: Document) -> None:
        """Добавить документ в реестр."""
        self._registry[document.id] = document
        self._save_registry()
