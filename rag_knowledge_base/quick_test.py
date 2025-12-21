"""Quick test script - tests basic functionality without ChromaDB.

Tests:
1. Basic imports
2. Configuration
3. FileConverter
4. Chunker
5. Embeddings

Skips ChromaDB-dependent tests to avoid DLL issues.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("QUICK RAG TEST (without ChromaDB)")
print("="*60)

# Test 1: Imports
print("\nTEST 1: Basic imports...")
try:
    from rag_module.models import Document, Chunk, SearchResult
    from rag_module.config import get_config
    from rag_module.exceptions import RAGException
    print("✅ PASSED - All imports successful")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Config
print("\nTEST 2: Configuration...")
try:
    config = get_config()
    print(f"✅ PASSED")
    print(f"   - Model: {config.embedding_model}")
    print(f"   - Chunk size: {config.chunk_size}")
    print(f"   - Top K: {config.top_k}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 3: FileConverter
print("\nTEST 3: FileConverter...")
try:
    from rag_module.file_processing import FileConverter
    converter = FileConverter()
    
    test_files = ["test.pdf", "test.docx", "test.txt", "test.xlsx"]
    for filename in test_files:
        is_supported = converter.is_supported(Path(filename))
        status = "✅" if is_supported else "❌"
        print(f"   {status} {filename}: {is_supported}")
    
    print("✅ PASSED - FileConverter initialized")
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Chunker
print("\nTEST 4: Chunker...")
try:
    from rag_module.services.chunker import Chunker
    chunker = Chunker(chunk_size=200, chunk_overlap=50)
    
    test_text = "This is a test document for chunking. " * 100
    chunks = chunker.chunk_text(test_text, "test_doc", {"test": True})
    
    print(f"✅ PASSED")
    print(f"   - Created {len(chunks)} chunks")
    print(f"   - First chunk length: {len(chunks[0].text)} chars")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Embeddings
print("\nTEST 5: Embeddings...")
try:
    from rag_module.services.embeddings import EmbeddingService
    print("   Loading model (this may take a minute)...")
    embedding_service = EmbeddingService()
    
    # Single embedding
    embedding = embedding_service.embed("test text for embedding")
    print(f"✅ PASSED")
    print(f"   - Embedding dimension: {len(embedding)}")
    print(f"   - Sample values: {embedding[:3]}")
    
    # Batch
    embeddings = embedding_service.embed_batch(["text 1", "text 2", "text 3"])
    print(f"   - Batch embeddings: {len(embeddings)} vectors")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print("✅ PASSED: Imports")
print("✅ PASSED: Configuration")
print("✅ PASSED: FileConverter")
print("✅ PASSED: Chunker")
print("✅ PASSED: Embeddings")
print("⚠️  SKIPPED: ChromaDB tests (DLL issue on Windows)")
print("⚠️  SKIPPED: RAG Manager tests (requires ChromaDB)")
print("="*60)
print("\n🎉 5/7 CORE TESTS PASSED!")
print("\n👉 To fix ChromaDB issue:")
print("   1. Install Visual C++ Redistributable:")
print("      https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist")
print("   2. Or try: pip install onnxruntime==1.16.3")
print("="*60)
