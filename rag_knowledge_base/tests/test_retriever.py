"""Tests for Retriever.

Тесты для сервиса поиска и извлечения релевантных чанков.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

from rag_module.services.retriever import Retriever, RetrieverError
from rag_module.services.embeddings import EmbeddingService
from rag_module.services.vector_store import ChromaVectorStore
from rag_module.models import Chunk, SearchResult


@pytest.fixture
def temp_db_path():
    """Временная директория для базы."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def retriever(temp_db_path):
    """Создать Retriever с реальными зависимостями."""
    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore(
        collection_name="test_retriever",
        persist_directory=temp_db_path,
    )
    
    retriever = Retriever(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    
    yield retriever
    
    # Cleanup
    try:
        vector_store.clear_all()
    except Exception:
        pass


@pytest.fixture
def sample_chunks():
    """Тестовые чанки с реальным текстом."""
    # Используем чанки без embeddings - они будут сгенерированы retriever
    chunks = [
        Chunk(
            id="doc1_chunk_0",
            doc_id="doc1",
            text="Artificial intelligence is revolutionizing technology.",
            position=0,
            metadata={"source": "ai.pdf"},
        ),
        Chunk(
            id="doc1_chunk_1",
            doc_id="doc1",
            text="Machine learning algorithms improve with data.",
            position=1,
            metadata={"source": "ai.pdf"},
        ),
        Chunk(
            id="doc2_chunk_0",
            doc_id="doc2",
            text="Python is a popular programming language for data science.",
            position=0,
            metadata={"source": "python.pdf"},
        ),
        Chunk(
            id="doc3_chunk_0",
            doc_id="doc3",
            text="The weather is nice today.",
            position=0,
            metadata={"source": "weather.txt"},
        ),
    ]
    return chunks


class TestRetriever:
    """Тесты для Retriever."""
    
    def test_initialization(self, retriever):
        """Тест инициализации."""
        assert retriever is not None
        assert retriever.embedding_service is not None
        assert retriever.vector_store is not None
        assert retriever.similarity_threshold > 0
    
    def test_add_chunks(self, retriever, sample_chunks):
        """Тест добавления чанков."""
        retriever.add_chunks(sample_chunks)
        
        # Проверяем что чанки добавлены в vector store
        count = retriever.vector_store.count()
        assert count == len(sample_chunks)
    
    def test_search_relevant_results(self, retriever, sample_chunks):
        """Тест поиска релевантных результатов."""
        retriever.add_chunks(sample_chunks)
        
        # Поиск по AI/ML
        query = "What is artificial intelligence?"
        results = retriever.search(query, top_k=3)
        
        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        
        # Первый результат должен быть про AI
        top_result = results[0]
        assert "artificial intelligence" in top_result.chunk.text.lower() or \
               "machine learning" in top_result.chunk.text.lower()
    
    def test_search_with_threshold(self, retriever, sample_chunks):
        """Тест поиска с порогом схожести."""
        retriever.add_chunks(sample_chunks)
        
        # Поиск с высоким порогом
        query = "machine learning"
        results = retriever.search(query, top_k=10, similarity_threshold=0.7)
        
        # Все результаты должны превышать порог
        for result in results:
            assert result.similarity_score >= 0.7
    
    def test_search_empty_query(self, retriever, sample_chunks):
        """Тест поиска с пустым запросом."""
        retriever.add_chunks(sample_chunks)
        
        results = retriever.search("", top_k=5)
        
        assert results == []
    
    def test_search_empty_store(self, retriever):
        """Тест поиска в пустом хранилище."""
        results = retriever.search("test query", top_k=5)
        
        assert results == []
    
    def test_search_top_k(self, retriever, sample_chunks):
        """Тест ограничения top_k."""
        retriever.add_chunks(sample_chunks)
        
        query = "programming"
        results = retriever.search(query, top_k=2)
        
        # Не должно быть больше top_k
        assert len(results) <= 2
    
    def test_search_with_filter(self, retriever, sample_chunks):
        """Тест поиска с фильтром по метаданным."""
        retriever.add_chunks(sample_chunks)
        
        query = "learning"
        results = retriever.search(
            query,
            top_k=10,
            filter_metadata={"doc_id": "doc1"},
        )
        
        # Все результаты должны быть из doc1
        for result in results:
            assert result.chunk.doc_id == "doc1"
    
    def test_similarity_scores_ordering(self, retriever, sample_chunks):
        """Тест сортировки по схожести."""
        retriever.add_chunks(sample_chunks)
        
        query = "technology"
        results = retriever.search(query, top_k=5)
        
        # Результаты должны быть отсортированы по убыванию схожести
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_russian_query(self, retriever):
        """Тест поиска на русском языке."""
        russian_chunks = [
            Chunk(
                id="ru_1",
                doc_id="doc_ru",
                text="Искусственный интеллект изменяет мир.",
                position=0,
            ),
            Chunk(
                id="ru_2",
                doc_id="doc_ru",
                text="Машинное обучение - это часть AI.",
                position=1,
            ),
        ]
        
        retriever.add_chunks(russian_chunks)
        
        query = "Что такое искусственный интеллект?"
        results = retriever.search(query, top_k=2)
        
        assert len(results) > 0
        # Должен найти русский текст
        assert any("интеллект" in r.chunk.text.lower() for r in results)
    
    def test_multilingual_search(self, retriever):
        """Тест мультиязычного поиска."""
        multilang_chunks = [
            Chunk(
                id="en_1",
                doc_id="doc_en",
                text="Artificial intelligence",
                position=0,
            ),
            Chunk(
                id="ru_1",
                doc_id="doc_ru",
                text="Искусственный интеллект",
                position=0,
            ),
        ]
        
        retriever.add_chunks(multilang_chunks)
        
        # Английский запрос должен найти оба текста
        results = retriever.search("AI", top_k=2)
        assert len(results) == 2
    
    def test_delete_chunks(self, retriever, sample_chunks):
        """Тест удаления чанков."""
        retriever.add_chunks(sample_chunks)
        
        initial_count = retriever.vector_store.count()
        assert initial_count == len(sample_chunks)
        
        # Удаляем документ
        retriever.delete_document("doc1")
        
        # Должно удалиться 2 чанка из doc1
        count_after = retriever.vector_store.count()
        assert count_after == initial_count - 2
    
    def test_clear_all(self, retriever, sample_chunks):
        """Тест полной очистки."""
        retriever.add_chunks(sample_chunks)
        
        assert retriever.vector_store.count() > 0
        
        retriever.clear_all()
        
        assert retriever.vector_store.count() == 0
    
    def test_custom_threshold(self, temp_db_path):
        """Тест кастомного порога схожести."""
        retriever = Retriever(
            embedding_service=EmbeddingService(),
            vector_store=ChromaVectorStore(
                collection_name="custom_threshold",
                persist_directory=temp_db_path,
            ),
            similarity_threshold=0.8,
        )
        
        assert retriever.similarity_threshold == 0.8


class TestRetrieverEdgeCases:
    """Тесты краевых случаев."""
    
    def test_very_long_query(self, retriever, sample_chunks):
        """Тест очень длинного запроса."""
        retriever.add_chunks(sample_chunks)
        
        long_query = " ".join(["word"] * 500)
        results = retriever.search(long_query, top_k=3)
        
        # Должен работать без ошибок
        assert isinstance(results, list)
    
    def test_special_characters_query(self, retriever, sample_chunks):
        """Тест запроса со спецсимволами."""
        retriever.add_chunks(sample_chunks)
        
        query = "@#$%^&*() ♥☆☃"
        results = retriever.search(query, top_k=3)
        
        # Должен обработать без ошибок
        assert isinstance(results, list)
    
    def test_duplicate_chunks(self, retriever):
        """Тест добавления дубликатов."""
        chunk = Chunk(
            id="dup_1",
            doc_id="doc1",
            text="Same text",
            position=0,
        )
        
        # Добавляем дважды
        retriever.add_chunks([chunk])
        retriever.add_chunks([chunk])
        
        # Должен перезаписать (или игнорировать)
        count = retriever.vector_store.count()
        # ChromaDB перезаписывает по ID
        assert count == 1


class TestRetrieverPerformance:
    """Тесты производительности."""
    
    def test_large_batch_add(self, retriever):
        """Тест добавления большого количества чанков."""
        # Генерируем 50 чанков
        chunks = [
            Chunk(
                id=f"chunk_{i}",
                doc_id="doc_large",
                text=f"This is test chunk number {i} with unique content.",
                position=i,
            )
            for i in range(50)
        ]
        
        # Должно работать быстро (батчинг)
        retriever.add_chunks(chunks)
        
        assert retriever.vector_store.count() == 50
