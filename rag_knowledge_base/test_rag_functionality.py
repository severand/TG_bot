"""Test script for RAG module functionality.

Tests all major components:
1. File processing (PDF, DOCX, TXT, Excel)
2. Text chunking
3. Embeddings generation
4. Vector storage
5. Semantic search
6. Full pipeline (add document + search)

Usage:
    python test_rag_functionality.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rag_module.services.manager import RAGManager
from rag_module.file_processing import FileConverter
from rag_module.services.chunker import Chunker
from rag_module.services.embeddings import EmbeddingService
from rag_module.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test 1: Check all imports work."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Checking imports...")
    logger.info("="*60)
    
    try:
        from rag_module.models import Document, Chunk, SearchResult
        from rag_module.exceptions import RAGException
        from rag_module.services.vector_store import ChromaVectorStore
        from rag_module.services.retriever import Retriever
        
        logger.info("✅ All imports successful!")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_config():
    """Test 2: Check configuration."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Checking configuration...")
    logger.info("="*60)
    
    try:
        settings = get_settings()
        logger.info(f"✅ Config loaded:")
        logger.info(f"   - Embedding model: {settings.EMBEDDING_MODEL}")
        logger.info(f"   - Chunk size: {settings.CHUNK_SIZE}")
        logger.info(f"   - Vector DB: {settings.VECTOR_DB_PATH}")
        logger.info(f"   - Collection: {settings.VECTOR_DB_COLLECTION}")
        return True
    except Exception as e:
        logger.error(f"❌ Config failed: {e}")
        return False


def test_file_converter():
    """Test 3: Check file converter."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Testing FileConverter...")
    logger.info("="*60)
    
    try:
        converter = FileConverter()
        
        # Test supported formats
        test_files = [
            "test.pdf", "test.docx", "test.txt", 
            "test.xlsx", "test.doc", "test.zip"
        ]
        
        for filename in test_files:
            is_supported = converter.is_supported(Path(filename))
            status = "✅" if is_supported else "❌"
            logger.info(f"   {status} {filename}: {is_supported}")
        
        logger.info("✅ FileConverter initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ FileConverter failed: {e}")
        return False


def test_chunker():
    """Test 4: Check text chunking."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Testing Chunker...")
    logger.info("="*60)
    
    try:
        chunker = Chunker(chunk_size=200, chunk_overlap=50)
        
        # Test text
        test_text = """Это тестовый документ для проверки чанкера. " * 20)
        Он содержит достаточно текста чтобы создать несколько чанков.
        RAG система должна правильно разбить этот текст на части.
        Каждый чанк должен содержать примерно 200 символов.
        " * 10
        
        chunks = chunker.chunk_text(
            text=test_text * 5,
            doc_id="test_doc",
            base_metadata={"test": True}
        )
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        logger.info(f"   - First chunk: {chunks[0].text[:50]}...")
        logger.info(f"   - Chunk size range: {min(len(c.text) for c in chunks)}-{max(len(c.text) for c in chunks)}")
        return True
    except Exception as e:
        logger.error(f"❌ Chunker failed: {e}")
        return False


def test_embeddings():
    """Test 5: Check embeddings generation."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Testing EmbeddingService...")
    logger.info("="*60)
    
    try:
        embedding_service = EmbeddingService()
        
        # Test single embedding
        text = "Это тестовый текст для проверки embeddings"
        embedding = embedding_service.embed(text)
        
        logger.info(f"✅ Embedding generated:")
        logger.info(f"   - Shape: {embedding.shape}")
        logger.info(f"   - Dimension: {len(embedding)}")
        logger.info(f"   - Sample values: {embedding[:5]}")
        
        # Test batch
        texts = ["Текст 1", "Текст 2", "Текст 3"]
        embeddings = embedding_service.embed_batch(texts)
        logger.info(f"✅ Batch embeddings: {len(embeddings)} vectors")
        
        return True
    except Exception as e:
        logger.error(f"❌ Embeddings failed: {e}")
        return False


def test_rag_manager_init():
    """Test 6: Check RAG Manager initialization."""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Testing RAG Manager initialization...")
    logger.info("="*60)
    
    try:
        manager = RAGManager()
        stats = manager.get_stats()
        
        logger.info(f"✅ RAG Manager initialized:")
        logger.info(f"   - Documents: {stats['total_documents']}")
        logger.info(f"   - Chunks: {stats['total_chunks']}")
        logger.info(f"   - Embedding dim: {stats['embedding_dimension']}")
        
        return True
    except Exception as e:
        logger.error(f"❌ RAG Manager init failed: {e}")
        return False


def test_text_document():
    """Test 7: Add and search text document."""
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Testing full pipeline with text document...")
    logger.info("="*60)
    
    try:
        manager = RAGManager()
        
        # Create test text file
        test_dir = Path(__file__).parent / "test_data"
        test_dir.mkdir(exist_ok=True)
        
        test_file = test_dir / "test_document.txt"
        test_content = """RAG Knowledge Base System
        
Это тестовый документ для проверки работы RAG системы.
Система должна корректно обработать этот текст.

Основные возможности:
1. Загрузка документов различных форматов
2. Разбиение текста на чанки
3. Генерация эмбеддингов
4. Семантический поиск
5. Хранение в векторной базе данных

Технологии:
- Python 3.9+
- ChromaDB для векторного хранилища
- Sentence-Transformers для эмбеддингов
- PyPDF2 для работы с PDF
- python-docx для DOCX файлов

Поиск работает на основе семантической схожести.
Можно искать по смыслу, а не только по ключевым словам.
"""
        
        test_file.write_text(test_content, encoding="utf-8")
        logger.info(f"📝 Created test file: {test_file}")
        
        # Add document
        logger.info("📤 Adding document to RAG...")
        doc = manager.add_document(
            file_path=test_file,
            doc_id="test_doc_001",
            metadata={"type": "test", "created": datetime.now().isoformat()}
        )
        
        logger.info(f"✅ Document added:")
        logger.info(f"   - ID: {doc.id}")
        logger.info(f"   - Chunks: {doc.chunk_count}")
        logger.info(f"   - Size: {doc.file_size} bytes")
        
        # Search
        logger.info("\n🔍 Testing search...")
        queries = [
            "возможности системы",
            "технологии и библиотеки",
            "семантический поиск"
        ]
        
        for query in queries:
            logger.info(f"\n   Query: '{query}'")
            results = manager.search(query, top_k=3)
            
            if results:
                logger.info(f"   Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    logger.info(f"   {i}. Score: {result.similarity_score:.2%}")
                    logger.info(f"      Text: {result.chunk.text[:100]}...")
            else:
                logger.warning(f"   No results found")
        
        # Cleanup
        logger.info("\n🧹 Cleaning up...")
        manager.delete_document("test_doc_001")
        test_file.unlink()
        
        logger.info("✅ Full pipeline test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "#"*60)
    logger.info("#" + " "*58 + "#")
    logger.info("#" + "  RAG MODULE FUNCTIONALITY TEST".center(58) + "#")
    logger.info("#" + " "*58 + "#")
    logger.info("#"*60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("FileConverter", test_file_converter),
        ("Chunker", test_chunker),
        ("Embeddings", test_embeddings),
        ("RAG Manager Init", test_rag_manager_init),
        ("Full Pipeline", test_text_document),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results[name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status}: {name}")
    
    logger.info("="*60)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! RAG MODULE IS READY!")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
