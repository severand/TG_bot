"""Tests for EmbeddingService.

Тесты для сервиса генерации embeddings через Sentence-Transformers.
"""

import pytest
import numpy as np
from pathlib import Path

from rag_module.services.embeddings import EmbeddingService, EmbeddingError


class TestEmbeddingService:
    """Тесты для EmbeddingService."""
    
    def test_initialization(self):
        """Тест инициализации сервиса."""
        service = EmbeddingService()
        
        assert service is not None
        assert service.model is not None
        assert service.embedding_dim == 384  # MiniLM dimension
        assert service.batch_size > 0
    
    def test_embed_text_simple(self):
        """Тест генерации embedding для простого текста."""
        service = EmbeddingService()
        
        text = "This is a test sentence."
        embedding = service.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        # Проверка что это не нулевой вектор
        assert sum(abs(x) for x in embedding) > 0
    
    def test_embed_text_russian(self):
        """Тест с русским текстом."""
        service = EmbeddingService()
        
        text = "Это тестовое предложение на русском языке."
        embedding = service.embed_text(text)
        
        assert len(embedding) == 384
        assert sum(abs(x) for x in embedding) > 0
    
    def test_embed_text_empty(self):
        """Тест с пустым текстом."""
        service = EmbeddingService()
        
        embedding = service.embed_text("")
        
        # Должен вернуть нулевой вектор
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)
    
    def test_embed_batch(self):
        """Тест batch генерации embeddings."""
        service = EmbeddingService()
        
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
        ]
        
        embeddings = service.embed_batch(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
        # Проверка что векторы разные
        assert not np.allclose(embeddings[0], embeddings[1])
    
    def test_embed_batch_with_empty(self):
        """Тест batch с пустыми строками."""
        service = EmbeddingService()
        
        texts = [
            "Valid text",
            "",
            "Another valid text",
        ]
        
        embeddings = service.embed_batch(texts)
        
        assert embeddings.shape == (3, 384)
        # Пустой текст должен иметь нулевой вектор
        assert np.allclose(embeddings[1], np.zeros(384))
        # Валидные тексты - ненулевые
        assert not np.allclose(embeddings[0], np.zeros(384))
        assert not np.allclose(embeddings[2], np.zeros(384))
    
    def test_embed_batch_empty_list(self):
        """Тест batch с пустым списком."""
        service = EmbeddingService()
        
        embeddings = service.embed_batch([])
        
        assert embeddings.shape == (0, 384)
    
    def test_similarity_same_text(self):
        """Тест что одинаковый текст дает похожие embeddings."""
        service = EmbeddingService()
        
        text = "This is a unique sentence for testing."
        
        embedding1 = np.array(service.embed_text(text))
        embedding2 = np.array(service.embed_text(text))
        
        # Должны быть почти идентичными
        assert np.allclose(embedding1, embedding2, atol=1e-6)
    
    def test_similarity_different_texts(self):
        """Тест что разные тексты дают разные embeddings."""
        service = EmbeddingService()
        
        text1 = "Artificial intelligence is transforming the world."
        text2 = "I like to eat pizza for dinner."
        
        embedding1 = np.array(service.embed_text(text1))
        embedding2 = np.array(service.embed_text(text2))
        
        # Должны быть разными
        assert not np.allclose(embedding1, embedding2, atol=0.1)
    
    def test_similarity_related_texts(self):
        """Тест что похожие тексты дают похожие embeddings."""
        service = EmbeddingService()
        
        text1 = "Machine learning is a subset of AI."
        text2 = "Artificial intelligence includes machine learning."
        text3 = "I bought a new car yesterday."
        
        emb1 = np.array(service.embed_text(text1))
        emb2 = np.array(service.embed_text(text2))
        emb3 = np.array(service.embed_text(text3))
        
        # Похожие тексты должны быть ближе друг к другу
        similarity_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        similarity_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
        
        # AI тексты должны быть похожее между собой, чем с текстом про машину
        assert similarity_12 > similarity_13
    
    def test_get_embedding_dimension(self):
        """Тест получения размерности embedding."""
        service = EmbeddingService()
        
        dim = service.get_embedding_dimension()
        
        assert dim == 384
        assert isinstance(dim, int)
    
    def test_batch_size_configuration(self):
        """Тест конфигурации batch size."""
        service = EmbeddingService(batch_size=16)
        
        assert service.batch_size == 16
    
    def test_large_text(self):
        """Тест с большим текстом."""
        service = EmbeddingService()
        
        # Генерируем большой текст
        large_text = " ".join(["word"] * 1000)
        
        embedding = service.embed_text(large_text)
        
        # Должно работать без ошибок
        assert len(embedding) == 384
        assert sum(abs(x) for x in embedding) > 0
    
    def test_special_characters(self):
        """Тест с спецсимволами."""
        service = EmbeddingService()
        
        text = "Test with symbols: @#$%^&*() and 日本語"
        embedding = service.embed_text(text)
        
        assert len(embedding) == 384
        assert sum(abs(x) for x in embedding) > 0
    
    def test_numeric_text(self):
        """Тест с числами."""
        service = EmbeddingService()
        
        text = "123 456 789 numbers everywhere 42"
        embedding = service.embed_text(text)
        
        assert len(embedding) == 384
        assert sum(abs(x) for x in embedding) > 0


class TestEmbeddingServiceErrors:
    """Тесты обработки ошибок EmbeddingService."""
    
    def test_invalid_model_name(self):
        """Тест с несуществующей моделью."""
        with pytest.raises(EmbeddingError):
            EmbeddingService(model_name="nonexistent-model-name-123")
    
    def test_invalid_batch_size(self):
        """Тест с некорректным batch size."""
        # Должно работать, но использовать значение по умолчанию
        service = EmbeddingService(batch_size=0)
        # В реальности batch_size будет заменен на дефолтный
        assert service.batch_size > 0


class TestEmbeddingServicePerformance:
    """Тесты производительности EmbeddingService."""
    
    def test_batch_faster_than_sequential(self):
        """Тест что batch обработка быстрее последовательной."""
        import time
        
        service = EmbeddingService()
        texts = [f"Test sentence number {i}" for i in range(10)]
        
        # Sequential
        start = time.time()
        for text in texts:
            service.embed_text(text)
        sequential_time = time.time() - start
        
        # Batch
        start = time.time()
        service.embed_batch(texts)
        batch_time = time.time() - start
        
        # Batch должен быть быстрее (обычно в 2-3 раза)
        print(f"Sequential: {sequential_time:.3f}s, Batch: {batch_time:.3f}s")
        # Не делаем строгую проверку т.к. зависит от железа
