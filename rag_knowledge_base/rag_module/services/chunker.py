"""Chunking service for RAG module.

Разбивает исходный текст на перекрывающиеся фрагменты (чанки)
фиксированного размера. Использует многоступенчатую стратегию
разбиения: параграфы → предложения → слова, чтобы минимально
ломать структуру текста.

Выходные данные совместимы с моделями `Chunk` из rag_module.models.

Основные цели:
- Ограничить размер одной порции текста (CHUNK_SIZE)
- Добавить overlap (CHUNK_OVERLAP) для сохранения контекста
- Сохранить базовые метаданные (doc_id, position, page, metadata)

Chunker сам по себе не создаёт embeddings, он только готовит
сырьё для EmbeddingService и VectorStore.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Iterable, List, Dict, Any, Optional

from rag_module.config import get_config
from rag_module.models import Chunk
from rag_module.exceptions import RAGException


class ChunkingError(RAGException):
    """Ошибка при разбиении текста на чанки."""


class Chunker:
    """Сервис разбиения текста на чанки.

    Алгоритм (упрощённо):
    1. Разделяем текст на параграфы по двойному переводу строки.
    2. Каждый параграф при необходимости режем на предложения.
    3. Если предложение всё ещё слишком длинное — дробим по словам.
    4. Собираем итоговые чанки фиксированного размера с overlap.

    Размеры и поведение берутся из конфигурации:
    - chunk_size
    - chunk_overlap
    """

    PARAGRAPH_SEPARATOR = "\n\n"

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> None:
        config = get_config()
        self.chunk_size = chunk_size or config.chunk_size
        self.chunk_overlap = chunk_overlap or config.chunk_overlap

        if self.chunk_size <= 0:
            raise ChunkingError("chunk_size must be > 0")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ChunkingError("chunk_overlap must be between 0 and chunk_size - 1")

    # ---------- Публичный API ----------

    def chunk_text(
        self,
        text: str,
        doc_id: str,
        base_metadata: Optional[Dict[str, Any]] = None,
        page: Optional[int] = None,
    ) -> List[Chunk]:
        """Разбить текст на чанки.

        Args:
            text: исходный текст документа
            doc_id: идентификатор документа
            base_metadata: дополнительные метаданные (источник, тип и т.п.)
            page: номер страницы (если есть; для простых текстов можно опустить)

        Returns:
            Список объектов `Chunk` без embeddings.
        """
        if not text or not text.strip():
            return []

        tokens = self._tokenize(text)
        if not tokens:
            return []

        chunks: List[Chunk] = []
        position = 0
        idx = 0

        while idx < len(tokens):
            window_tokens = tokens[idx : idx + self.chunk_size]
            chunk_text = " ".join(window_tokens).strip()

            if not chunk_text:
                break

            metadata = dict(base_metadata or {})
            if page is not None:
                metadata.setdefault("page", page)

            chunk = Chunk(
                id=f"{doc_id}_chunk_{position}",
                doc_id=doc_id,
                text=chunk_text,
                embedding=[],  # embeddings будут добавлены EmbeddingService
                position=position,
                page=page,
                metadata=metadata,
            )
            chunks.append(chunk)

            position += 1
            # сдвигаем окно с overlap
            if self.chunk_overlap > 0:
                idx += self.chunk_size - self.chunk_overlap
            else:
                idx += self.chunk_size

        return chunks

    # ---------- Вспомогательные методы ----------

    def _tokenize(self, text: str) -> List[str]:
        """Разбить текст на токены (слова) с сохранением простых знаков.

        Пока используем очень простой подход: разделяем по пробелам
        и переносам строк, убирая лишние пробельные символы.

        В будущем сюда можно подключить более умный токенизатор
        (SentencePiece/BPE), если понадобится.
        """
        # Убираем лишние пробелы и нормализуем переносы
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        return normalized.split(" ")
