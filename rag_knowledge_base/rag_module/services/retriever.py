"""Retriever service for semantic search.

Сервис семантического поиска. Объединяет EmbeddingService и VectorStore
для получения end-to-end поиска по текстовому запросу.

Основной флоу:
1. Получаем текстовый запрос
2. Генерируем embedding запроса (EmbeddingService)
3. Ищем похожие чанки (VectorStore)
4. Фильтруем по threshold, сортируем, возвращаем SearchResult
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from rag_module.config import get_settings
from rag_module.models import SearchResult
from rag_module.services.embeddings import EmbeddingService
from rag_module.services.vector_store import ChromaVectorStore
from rag_module.exceptions import RAGException

logger = logging.getLogger(__name__)


class RetrieverError(RAGException):
    """Ошибка при выполнении поиска."""


class Retriever:
    """Сервис семантического поиска.

    Объединяет embeddings и vector store для поиска по текстовым запросам.
    Поддерживает фильтрацию по similarity_threshold и metadata.

    Attributes:
        embedding_service: Сервис генерации embeddings
        vector_store: Хранилище векторов
        similarity_threshold: Минимальная схожесть для отбора результатов
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[ChromaVectorStore] = None,
        similarity_threshold: Optional[float] = None,
    ) -> None:
        """Инициализация retriever.

        Args:
            embedding_service: Сервис embeddings (создаётся автоматически если не передан)
            vector_store: Векторное хранилище (создаётся автоматически)
            similarity_threshold: Минимальная схожесть (из config)

        Raises:
            RetrieverError: Если не удалось инициализировать
        """
        settings = get_settings()
        self.similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD

        try:
            self.embedding_service = embedding_service or EmbeddingService()
            self.vector_store = vector_store or ChromaVectorStore()
            logger.info(
                f"✓ Retriever initialized with threshold={self.similarity_threshold}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Retriever: {e}")
            raise RetrieverError(f"Cannot initialize Retriever: {e}") from e

    # ---------- Публичный API ----------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[SearchResult]:
        """Поиск по текстовому запросу.

        Args:
            query: Текстовый запрос
            top_k: Максимальное количество результатов
            filter_metadata: Фильтр по метаданным
            min_similarity: Минимальная схожесть (переопределяет threshold)

        Returns:
            Список SearchResult, отсортированный по similarity_score (от большего к меньшему)

        Raises:
            RetrieverError: Если поиск не удался
        """
        if not query or not query.strip():
            logger.warning("Empty query provided")
            return []

        threshold = min_similarity if min_similarity is not None else self.similarity_threshold

        try:
            # 1. Генерируем embedding запроса
            logger.debug(f"Embedding query: {query[:50]}...")
            query_embedding = self.embedding_service.embed_text(query)

            # 2. Поиск в vector store
            logger.debug(f"Searching vector store (top_k={top_k})")
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_metadata=filter_metadata,
            )

            # 3. Фильтруем по threshold
            filtered_results = [
                result for result in results if result.similarity_score >= threshold
            ]

            # 4. Сортируем по similarity_score (от большего к меньшему)
            filtered_results.sort(key=lambda x: x.similarity_score, reverse=True)

            logger.info(
                f"Found {len(filtered_results)} results above threshold {threshold:.2f} "
                f"(out of {len(results)} total)"
            )
            return filtered_results

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            raise RetrieverError(f"Retrieval failed: {e}") from e

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику retriever.

        Returns:
            Словарь с статистикой
        """
        return {
            "similarity_threshold": self.similarity_threshold,
            "embedding_dimension": self.embedding_service.get_embedding_dimension(),
            "total_chunks": self.vector_store.count(),
        }
