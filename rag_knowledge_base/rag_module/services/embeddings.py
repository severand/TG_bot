"""Embedding service for RAG module.

Генерирует векторные представления (embeddings) текстов с помощью
Sentence-Transformers. Использует модель paraphrase-multilingual-MiniLM-L12-v2
для многоязычной поддержки (русский, английский и др.).

Выходные векторы: 384 dimensions.
Поддерживает как одиночные тексты, так и батчи для эффективности.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from rag_module.config import get_settings
from rag_module.exceptions import RAGException

logger = logging.getLogger(__name__)


class EmbeddingError(RAGException):
    """Ошибка при генерации embeddings."""


class EmbeddingService:
    """Сервис генерации embeddings через Sentence-Transformers.

    Использует предобученную модель для создания векторных представлений текста.
    Поддерживает batch processing для оптимизации производительности.

    Attributes:
        model_name: Название модели Sentence-Transformers
        device: Устройство для вычислений (cpu/cuda/mps)
        batch_size: Размер батча для batch encoding
        embedding_dim: Размерность выходных векторов (384 для MiniLM)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """Инициализация embedding сервиса.

        Args:
            model_name: Название модели (по умолчанию из config)
            device: Устройство (cpu/cuda/mps, по умолчанию auto)
            batch_size: Размер батча (по умолчанию из config)

        Raises:
            EmbeddingError: Если sentence-transformers не установлен
        """
        if SentenceTransformer is None:
            raise EmbeddingError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )

        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

        logger.info(f"Loading embedding model: {self.model_name} on device: {self.device}")
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(
                f"✓ Model loaded successfully. Embedding dimension: {self.embedding_dim}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingError(f"Cannot load model {self.model_name}: {e}") from e

    # ---------- Публичный API ----------

    def embed_text(self, text: str) -> List[float]:
        """Создать embedding для одного текста.

        Args:
            text: Исходный текст

        Returns:
            Вектор embeddings (список float размером embedding_dim)

        Raises:
            EmbeddingError: Если не удалось создать embedding
        """
        if not text or not text.strip():
            # Для пустого текста возвращаем нулевой вектор
            return [0.0] * self.embedding_dim

        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            raise EmbeddingError(f"Failed to embed text: {e}") from e

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Создать embeddings для батча текстов.

        Более эффективно, чем вызывать embed_text в цикле.

        Args:
            texts: Список текстов

        Returns:
            Матрица embeddings размером (len(texts), embedding_dim)

        Raises:
            EmbeddingError: Если не удалось создать embeddings
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.embedding_dim)

        # Фильтруем пустые тексты, запоминаем индексы
        non_empty_texts = []
        non_empty_indices = []
        for idx, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text)
                non_empty_indices.append(idx)

        # Создаём матрицу embeddings
        result = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

        if non_empty_texts:
            try:
                embeddings = self.model.encode(
                    non_empty_texts,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                # Заполняем результат только для непустых текстов
                for i, idx in enumerate(non_empty_indices):
                    result[idx] = embeddings[i]
            except Exception as e:
                logger.error(f"Error encoding batch: {e}")
                raise EmbeddingError(f"Failed to embed batch: {e}") from e

        return result

    def get_embedding_dimension(self) -> int:
        """Получить размерность выходных embeddings.

        Returns:
            Размерность embedding вектора
        """
        return self.embedding_dim
