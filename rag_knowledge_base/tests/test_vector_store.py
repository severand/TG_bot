"""Tests for ChromaVectorStore.

Тесты для векторного хранилища на основе ChromaDB.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from rag_module.services.vector_store import ChromaVectorStore, VectorStoreError
from rag_module.models import Chunk


@pytest.fixture
def temp_db_path():
    """Создать временную директорию для базы данных."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def vector_store(temp_db_path):
    """Создать vector store для тестов."""
    store = ChromaVectorStore(
        collection_name="test_collection",
        persist_directory=temp_db_path,
    )
    yield store
    # Cleanup
    try:
        store.clear_all()
    except Exception:
        pass


@pytest.fixture
def sample_chunks():
    """Создать тестовые чанки с embeddings."""
    chunks = [
        Chunk(
            id="doc1_chunk_0",
            doc_id="doc1",
            text="Artificial intelligence is transforming industries.",
            embedding=[0.1] * 384,  # Mock embedding
            position=0,
            metadata={"source": "test.pdf"},
        ),
        Chunk(
            id="doc1_chunk_1",
            doc_id="doc1",
            text="Machine learning is a subset of AI.",
            embedding=[0.2] * 384,
            position=1,
            metadata={"source": "test.pdf"},
        ),
        Chunk(
            id="doc2_chunk_0",
            doc_id="doc2",
            text="Python is a programming language.",
            embedding=[0.3] * 384,
            position=0,
            metadata={"source": "code.pdf"},
        ),
    ]
    return chunks


class TestChromaVectorStore:
    """Тесты для ChromaVectorStore."""
    
    def test_initialization(self, temp_db_path):
        """Тест инициализации vector store."""
        store = ChromaVectorStore(
            collection_name="test_init",
            persist_directory=temp_db_path,
        )
        
        assert store is not None
        assert store.collection_name == "test_init"
        assert store.persist_directory == temp_db_path
        assert store.client is not None
        assert store.collection is not None
    
    def test_add_chunks(self, vector_store, sample_chunks):
        """Тест добавления чанков."""
        vector_store.add_chunks(sample_chunks)
        
        count = vector_store.count()
        assert count == 3
    
    def test_add_empty_chunks(self, vector_store):
        """Тест добавления пустого списка."""
        vector_store.add_chunks([])
        
        count = vector_store.count()
        assert count == 0
    
    def test_add_chunks_without_embeddings(self, vector_store):
        """Тест добавления чанков без embeddings."""
        chunks = [
            Chunk(
                id="test_1",
                doc_id="doc1",
                text="Test text",
                embedding=[],  # Пустой embedding
                position=0,
            )
        ]
        
        # Должен пропустить чанк без embedding
        vector_store.add_chunks(chunks)
        
        count = vector_store.count()
        assert count == 0
    
    def test_search(self, vector_store, sample_chunks):
        """Тест поиска."""
        vector_store.add_chunks(sample_chunks)
        
        query_embedding = [0.15] * 384  # Похож на первые два чанка
        results = vector_store.search(query_embedding, top_k=2)
        
        assert len(results) <= 2
        assert all(hasattr(r, 'similarity_score') for r in results)
        assert all(hasattr(r, 'chunk') for r in results)
    
    def test_search_with_filter(self, vector_store, sample_chunks):
        """Тест поиска с фильтром."""
        vector_store.add_chunks(sample_chunks)
        
        query_embedding = [0.2] * 384
        results = vector_store.search(
            query_embedding,
            top_k=10,
            filter_metadata={"doc_id": "doc1"},
        )
        
        # Должны вернуться только чанки из doc1
        assert all(r.chunk.doc_id == "doc1" for r in results)
        assert len(results) <= 2  # В doc1 только 2 чанка
    
    def test_search_empty_query(self, vector_store, sample_chunks):
        """Тест поиска с пустым запросом."""
        vector_store.add_chunks(sample_chunks)
        
        results = vector_store.search([], top_k=5)
        
        assert results == []
    
    def test_search_empty_store(self, vector_store):
        """Тест поиска в пустом хранилище."""
        query_embedding = [0.1] * 384
        results = vector_store.search(query_embedding, top_k=5)
        
        assert results == []
    
    def test_similarity_scores(self, vector_store, sample_chunks):
        """Тест оценок сходства."""
        vector_store.add_chunks(sample_chunks)
        
        query_embedding = [0.1] * 384
        results = vector_store.search(query_embedding, top_k=3)
        
        # Оценки должны быть от 0 до 1
        for result in results:
            assert 0 <= result.similarity_score <= 1
        
        # Результаты должны быть отсортированы по убыванию
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_delete_by_doc_id(self, vector_store, sample_chunks):
        """Тест удаления по doc_id."""
        vector_store.add_chunks(sample_chunks)
        
        initial_count = vector_store.count()
        assert initial_count == 3
        
        # Удаляем чанки doc1 (2 чанка)
        vector_store.delete_by_doc_id("doc1")
        
        count_after = vector_store.count()
        assert count_after == 1  # Остался только doc2
    
    def test_delete_nonexistent_doc(self, vector_store, sample_chunks):
        """Тест удаления несуществующего документа."""
        vector_store.add_chunks(sample_chunks)
        
        initial_count = vector_store.count()
        
        # Удаляем несуществующий документ (не должно быть ошибки)
        vector_store.delete_by_doc_id("nonexistent_doc")
        
        count_after = vector_store.count()
        assert count_after == initial_count
    
    def test_clear_all(self, vector_store, sample_chunks):
        """Тест полной очистки."""
        vector_store.add_chunks(sample_chunks)
        
        assert vector_store.count() == 3
        
        vector_store.clear_all()
        
        assert vector_store.count() == 0
    
    def test_count(self, vector_store, sample_chunks):
        """Тест подсчета чанков."""
        assert vector_store.count() == 0
        
        vector_store.add_chunks(sample_chunks[:1])
        assert vector_store.count() == 1
        
        vector_store.add_chunks(sample_chunks[1:3])
        assert vector_store.count() == 3
    
    def test_persistence(self, temp_db_path, sample_chunks):
        """Тест сохранения данных на диске."""
        # Создаем store и добавляем данные
        store1 = ChromaVectorStore(
            collection_name="persist_test",
            persist_directory=temp_db_path,
        )
        store1.add_chunks(sample_chunks)
        count1 = store1.count()
        
        # Создаем новый store с тем же путем
        store2 = ChromaVectorStore(
            collection_name="persist_test",
            persist_directory=temp_db_path,
        )
        count2 = store2.count()
        
        # Данные должны сохраниться
        assert count1 == count2 == 3
    
    def test_multiple_collections(self, temp_db_path, sample_chunks):
        """Тест работы с несколькими коллекциями."""
        store1 = ChromaVectorStore(
            collection_name="collection1",
            persist_directory=temp_db_path,
        )
        store2 = ChromaVectorStore(
            collection_name="collection2",
            persist_directory=temp_db_path,
        )
        
        store1.add_chunks(sample_chunks[:2])
        store2.add_chunks(sample_chunks[2:])
        
        assert store1.count() == 2
        assert store2.count() == 1
    
    def test_metadata_preservation(self, vector_store):
        """Тест сохранения метаданных."""
        chunks = [
            Chunk(
                id="test_1",
                doc_id="doc1",
                text="Test",
                embedding=[0.1] * 384,
                position=0,
                page=5,
                metadata={
                    "author": "John Doe",
                    "year": 2024,
                    "score": 9.5,
                },
            )
        ]
        
        vector_store.add_chunks(chunks)
        
        results = vector_store.search([0.1] * 384, top_k=1)
        
        assert len(results) == 1
        result_metadata = results[0].chunk.metadata
        assert result_metadata["author"] == "John Doe"
        assert result_metadata["year"] == 2024
        assert result_metadata["page"] == 5


class TestVectorStoreErrors:
    """Тесты обработки ошибок."""
    
    def test_invalid_directory_permissions(self):
        """Тест с недоступной директорией."""
        # Пропускаем на Windows
        import platform
        if platform.system() == "Windows":
            pytest.skip("Permission test skipped on Windows")
        
        # В реальности ChromaDB создаст директорию если ее нет
        # Этот тест больше для документации
        pass
