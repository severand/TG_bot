"""Vector store service using ChromaDB.

Хранилище векторных представлений (embeddings) на основе ChromaDB.
Поддерживает:
- Добавление/удаление чанков с embeddings
- Семантический поиск (cosine similarity)
- Персистентное хранение на диске
- Метаданные для каждого чанка
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None

from rag_module.config import get_settings
from rag_module.models import Chunk, SearchResult
from rag_module.exceptions import RAGException

logger = logging.getLogger(__name__)


class VectorStoreError(RAGException):
    """Ошибка при работе с vector store."""


class ChromaVectorStore:
    """Векторное хранилище на основе ChromaDB.

    Использует ChromaDB для хранения и поиска embeddings.
    Поддерживает персистентность на диске и cosine similarity поиск.

    Attributes:
        collection_name: Имя коллекции ChromaDB
        persist_directory: Путь к директории хранения
    """

    DEFAULT_COLLECTION_NAME = "rag_chunks"

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[Path] = None,
    ) -> None:
        """Инициализация vector store.

        Args:
            collection_name: Имя коллекции (по умолчанию 'rag_chunks')
            persist_directory: Путь для хранения данных (из config)

        Raises:
            VectorStoreError: Если chromadb не установлен
        """
        if chromadb is None:
            raise VectorStoreError(
                "chromadb not installed. Run: pip install chromadb"
            )

        settings = get_settings()
        self.collection_name = collection_name or self.DEFAULT_COLLECTION_NAME
        self.persist_directory = persist_directory or Path(settings.VECTOR_DB_PATH)

        # Создаём директорию если нужно
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {self.persist_directory}")
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},  # cosine similarity
            )
            logger.info(f"✓ ChromaDB collection '{self.collection_name}' ready")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise VectorStoreError(f"Cannot initialize ChromaDB: {e}") from e

    # ---------- Публичный API ----------

    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Добавить чанки с embeddings в хранилище.

        Args:
            chunks: Список чанков с заполненными embeddings

        Raises:
            VectorStoreError: Если не удалось добавить чанки
        """
        if not chunks:
            return

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in chunks:
            if not chunk.embedding:
                logger.warning(f"Chunk {chunk.id} has no embedding, skipping")
                continue

            ids.append(chunk.id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.text)

            # Подготовка метаданных (все значения должны быть простыми типами)
            metadata = {
                "doc_id": chunk.doc_id,
                "position": chunk.position,
            }
            if chunk.page is not None:
                metadata["page"] = chunk.page
            if chunk.metadata:
                for k, v in chunk.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        metadata[k] = v
            metadatas.append(metadata)

        if not ids:
            logger.warning("No valid chunks to add")
            return

        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(ids)} chunks to vector store")
        except Exception as e:
            logger.error(f"Error adding chunks: {e}")
            raise VectorStoreError(f"Failed to add chunks: {e}") from e

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Поиск по сходству embeddings.

        Args:
            query_embedding: Вектор запроса
            top_k: Количество результатов
            filter_metadata: Фильтр по метаданным

        Returns:
            Список SearchResult отсортированный по similarity_score

        Raises:
            VectorStoreError: Если поиск не удался
        """
        if not query_embedding:
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            search_results = []
            if results and results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    chunk_id = results["ids"][0][i]
                    text = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i]

                    # ChromaDB возвращает distance (0=идентичные, 2=противоположные)
                    # Конвертируем в similarity (1=идентичные, 0=противоположные)
                    similarity_score = 1.0 - (distance / 2.0)

                    # Восстанавливаем Chunk из результата
                    chunk = Chunk(
                        id=chunk_id,
                        doc_id=metadata.get("doc_id", ""),
                        text=text,
                        embedding=query_embedding,  # не храним все embeddings
                        position=metadata.get("position", 0),
                        page=metadata.get("page"),
                        metadata=metadata,
                    )

                    search_result = SearchResult(
                        chunk=chunk,
                        similarity_score=similarity_score,
                        source_doc=metadata.get("doc_id", "unknown"),
                    )
                    search_results.append(search_result)

            logger.info(f"Found {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise VectorStoreError(f"Search failed: {e}") from e

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Удалить все чанки документа.

        Args:
            doc_id: ID документа

        Raises:
            VectorStoreError: Если удаление не удалось
        """
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted all chunks for doc_id: {doc_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise VectorStoreError(f"Failed to delete chunks: {e}") from e

    def clear_all(self) -> None:
        """Очистить все данные из хранилища.

        Raises:
            VectorStoreError: Если очистка не удалась
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Cleared all data from vector store")
        except Exception as e:
            logger.error(f"Error clearing store: {e}")
            raise VectorStoreError(f"Failed to clear store: {e}") from e

    def count(self) -> int:
        """Получить количество чанков в хранилище.

        Returns:
            Количество чанков
        """
        return self.collection.count()
