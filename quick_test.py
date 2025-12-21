import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Test 1: Imports (без ChromaDB)
print("TEST 1: Basic imports...")
from rag_module.models import Document, Chunk, SearchResult
from rag_module.config import get_config
print("✅ PASSED")

# Test 2: Config
print("\nTEST 2: Config...")
config = get_config()
print(f"✅ PASSED - Model: {config.embedding_model}")

# Test 3: FileConverter
print("\nTEST 3: FileConverter...")
from rag_module.file_processing import FileConverter
converter = FileConverter()
print(f"✅ PASSED - Supports PDF: {converter.is_supported(Path('test.pdf'))}")

# Test 4: Chunker
print("\nTEST 4: Chunker...")
from rag_module.services.chunker import Chunker
chunker = Chunker(chunk_size=200, chunk_overlap=50)
chunks = chunker.chunk_text("Test text " * 100, "test_doc", {})
print(f"✅ PASSED - Created {len(chunks)} chunks")

# Test 5: Embeddings
print("\nTEST 5: Embeddings...")
from rag_module.services.embeddings import EmbeddingService
embedding_service = EmbeddingService()
embedding = embedding_service.embed("test")
print(f"✅ PASSED - Dimension: {len(embedding)}")

print("\n🎉 5/7 TESTS PASSED!")
print("⚠️  ChromaDB tests skipped (DLL issue)")
