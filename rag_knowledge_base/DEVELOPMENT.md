# Development Guide for RAG Module 🔨

**Version:** 1.0.0  
**Status:** In Development  
**Last Updated:** 2025-12-21  

---

## 🚀 Getting Started

### 1. Setup Development Environment

```bash
# Clone repo
git clone https://github.com/severand/TG_bot.git
cd TG_bot

# Create feature branch
git checkout feature/rag-knowledge-base

# Setup Python env
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install RAG dependencies
cd rag_knowledge_base
pip install -r requirements.txt
pip install -e .  # Install module in editable mode

# Verify setup
python -c "import rag_module; print('✅ RAG module ready')"
```

### 2. Project Structure Reference

```
rag_knowledge_base/
├── rag_module/              # Main module
│   ├── services/            # Core services
│   ├── utils/               # Utilities
│   ├── config.py            # Configuration
│   ├── models.py            # Data models
│   └── exceptions.py        # Custom exceptions
├── tests/                   # Unit & integration tests
├── examples/                # Usage examples
├── docs/                    # Extended documentation
├── ARCHITECTURE.md          # Technical design
├── DEVELOPMENT.md           # This file
└── requirements.txt         # Dependencies
```

---

## 📘 Implementation Phases

### Phase 1: Core Services (Days 1-2)

**Goal:** Build the RAG pipeline

#### Day 1: Foundation

1. **Create base structures**
   ```bash
   touch rag_module/__init__.py
   touch rag_module/config.py
   touch rag_module/models.py
   touch rag_module/exceptions.py
   mkdir -p rag_module/services
   mkdir -p rag_module/utils
   ```

2. **Implement `config.py`**
   - Load from environment variables
   - Provide sensible defaults
   - Validate on startup

3. **Implement `models.py`**
   - Define dataclasses: Document, Chunk, SearchResult
   - Add validation methods
   - Add serialization helpers

4. **Implement `exceptions.py`**
   - Base RAGException
   - Specific exceptions for each service

5. **Write tests** (`tests/test_models.py`)
   - Test data model creation
   - Test serialization
   - Test validation

#### Day 2: Core Services

1. **`services/chunker.py`**
   - Text splitting algorithm
   - Metadata attachment
   - Overlap handling
   - Test with `tests/test_chunker.py`

2. **`services/embeddings.py`**
   - Load Sentence-Transformers model
   - Single text embedding
   - Batch embedding
   - Dimension validation
   - Test with `tests/test_embeddings.py`

3. **`services/vector_store.py`**
   - ChromaDB initialization
   - Add/delete/search operations
   - Metadata handling
   - Test with `tests/test_vector_store.py`

4. **`services/file_processor.py`**
   - PDF text extraction (use existing PDFParser)
   - DOCX extraction (use existing DOCXParser)
   - TXT support
   - Error handling
   - Test with `tests/test_file_processor.py`

### Phase 2: Integration (Days 3-4)

1. **`services/retriever.py`**
   - Combine embeddings + vector store
   - Semantic search implementation
   - Filtering support
   - Test with `tests/test_retriever.py`

2. **`services/manager.py`**
   - Orchestrate all services
   - High-level API
   - Error handling
   - Logging
   - Test with `tests/test_manager.py` + integration tests

3. **Integration with TG_bot**
   - Create `app/handlers/knowledge.py`
   - Create `app/states/knowledge.py`
   - Update `main.py` to register handler
   - Update `requirements.txt` in main project

### Phase 3: Documentation & Examples (Day 5)

1. Write API documentation (`docs/API.md`)
2. Create usage examples (`examples/`)
3. Write FAQ (`docs/FAQ.md`)
4. Performance benchmarks (`docs/PERFORMANCE.md`)

---

## 🔬 Code Standards

### Style Guide

**Use:** Python 3.10+ type hints

```python
# ✅ Good
async def add_document(
    self,
    file_path: Path,
    doc_id: str,
    metadata: Dict[str, Any] | None = None
) -> DocumentInfo:
    """Add document to knowledge base.
    
    Args:
        file_path: Path to document file
        doc_id: Unique document identifier
        metadata: Optional metadata dict
        
    Returns:
        Information about added document
        
    Raises:
        FileNotFoundError: If file doesn't exist
        RAGException: If processing fails
    """
    pass

# ❌ Bad
async def add_document(file_path, doc_id, metadata=None):
    # Missing type hints and docstring
    pass
```

### Docstring Format

Use Google-style docstrings:

```python
def process_chunk(text: str, size: int = 500) -> List[str]:
    """Split text into chunks of specified size.
    
    Args:
        text: Input text to chunk
        size: Max size of each chunk (default 500)
        
    Returns:
        List of text chunks
        
    Raises:
        ValueError: If size <= 0
    """
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# ✅ Use structured logging
logger.info("Document added", extra={
    "doc_id": doc_id,
    "chunk_count": len(chunks),
    "duration_ms": elapsed_ms
})

# ❌ Avoid string interpolation in log messages
logger.info(f"Document {doc_id} added")  # Bad - can't filter
```

---

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=rag_module --cov-report=html

# Specific test file
pytest tests/test_chunker.py -v

# Specific test
pytest tests/test_chunker.py::TestChunker::test_chunk_text -v

# Watch mode (auto-rerun on change)
pytest-watch tests/
```

### Test Structure

```python
# tests/test_chunker.py
import pytest
from rag_module.services.chunker import Chunker
from rag_module.models import Chunk

class TestChunker:
    """Test suite for Chunker service."""
    
    @pytest.fixture
    def chunker(self):
        """Create chunker instance for tests."""
        return Chunker(chunk_size=500, overlap=50)
    
    def test_chunk_simple_text(self, chunker):
        """Test chunking simple text."""
        text = "Hello world. This is a test."
        chunks = chunker.chunk_text(text, {"source": "test"})
        
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
        assert sum(len(c.text) for c in chunks) >= len(text)
    
    def test_chunk_respects_size_limit(self, chunker):
        """Test that chunks don't exceed max size."""
        text = " ".join(["word"] * 1000)
        chunks = chunker.chunk_text(text, {})
        
        for chunk in chunks:
            assert len(chunk.text) <= 500 + 50  # size + overlap buffer
    
    @pytest.mark.asyncio
    async def test_chunk_async(self, chunker):
        """Test async chunking."""
        text = "Sample text" * 100
        chunks = await chunker.chunk_text_async(text, {})
        assert len(chunks) > 0
```

### Test Coverage Requirements

- **Services:** >80% coverage
- **Utils:** >70% coverage
- **Models:** >90% coverage (critical)
- **Overall:** >75% target

---

## 🖥️ Git Workflow

### Branch Strategy

```
feature/rag-knowledge-base          # Main feature branch
  ├── feature/rag-chunker          # Individual services
  ├── feature/rag-embeddings
  ├── feature/rag-vector-store
  ├── feature/rag-retriever
  ├── feature/rag-manager
  └── feature/rag-integration      # TG_bot integration
```

### Commit Messages

Use conventional commits:

```
feat(rag/chunker): implement text chunking algorithm
  - Support configurable chunk size
  - Add overlap handling
  - Add unit tests

fix(rag/embeddings): handle large batch sizes
  - Memory optimization for batches > 1000
  - Add batch size validation
  - Update tests

docs(rag): update API documentation
  - Add examples for each service
  - Clarify error handling

test(rag): add integration tests
  - Full pipeline test (upload -> search)
  - Performance benchmarks
```

### Pull Request Process

1. **Create feature branch** from `feature/rag-knowledge-base`
2. **Develop** - implement, test, document
3. **Run tests** - ensure >75% coverage
4. **Self-review** - check code quality
5. **Push** and create PR
6. **Address feedback** if any
7. **Merge** to `feature/rag-knowledge-base`
8. **Delete** feature branch

---

## 🔧 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in config
DEBUG = True
```

### Common Issues

**Issue:** ChromaDB import fails
```bash
# Solution
pip install chromadb --upgrade
```

**Issue:** Embedding model download stuck
```bash
# Solution: Pre-download model
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# This caches the model
```

**Issue:** Out of memory with large documents
```python
# Solution: Process in batches
for batch in chunks_in_batches(all_chunks, batch_size=100):
    await vector_store.add_chunks(batch)
```

---

## 📚 IDE Setup

### VS Code

**Extensions:**
```
Python
Pylance
Pytest
Python Docstring Generator
Magic Python
```

**.vscode/settings.json:**
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. Open project
2. File → Settings → Project → Python Interpreter
3. Select venv
4. Run → Edit Configurations → Add pytest
5. Set working directory to `rag_knowledge_base`

---

## 📃 Key Files to Study

When starting:

1. **`ARCHITECTURE.md`** - Understand the design
2. **`rag_module/models.py`** - See data structures
3. **`rag_module/config.py`** - Configuration system
4. **`tests/test_chunker.py`** - Test examples
5. **`examples/basic_example.py`** - Usage example

---

## 🚅 Performance Tips

### Optimization Checklist

- [ ] Use async/await for I/O operations
- [ ] Batch embeddings (not single texts)
- [ ] Cache embeddings if possible
- [ ] Use appropriate chunk sizes (test with benchmarks)
- [ ] Monitor memory with large document sets
- [ ] Profile hot paths with cProfile

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... your code ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(20)
```

---

## 📄 Documentation Guidelines

### When to Document

- [ ] Every public function/class
- [ ] Complex algorithms
- [ ] Non-obvious design decisions
- [ ] Error conditions
- [ ] Performance characteristics

### Documentation Levels

1. **Docstrings** - For code (what does it do)
2. **README** - For project overview
3. **ARCHITECTURE** - For system design
4. **Examples** - For usage
5. **API docs** - For detailed API reference

---

## 🐛 Troubleshooting

### Dependencies won't install

```bash
# Update pip
pip install --upgrade pip

# Clear cache
pip install --no-cache-dir -r requirements.txt

# Or use requirements with specific versions
pip install chromadb==0.5.0 sentence-transformers==3.0.1
```

### Tests fail

```bash
# Run with verbose output
pytest tests/ -vv

# Run single test
pytest tests/test_chunker.py::TestChunker::test_chunk_simple_text -vv

# Show print statements
pytest tests/ -s
```

### Import errors

```bash
# Ensure module is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e .
```

---

## 💡 Tips & Tricks

### Quick Test of Changes

```python
# In Python REPL
from rag_module.manager import RAGManager

manager = RAGManager()
# Try your changes here
```

### Generate Documentation

```bash
# From rag_module source code
pydoc -w rag_module.services.chunker

# Or use sphinx (if set up)
make -C docs html
```

### Clean Build

```bash
rm -rf *.egg-info dist build
pip install -e .
```

---

## 🗑️ Getting Help

When stuck:

1. Check **TROUBLESHOOTING.md**
2. Review **docs/FAQ.md**
3. Look at similar tests for examples
4. Check ARCHITECTURE.md for design decisions
5. Create GitHub issue with details

---

**Happy coding! 🚀**

**Last Updated:** 2025-12-21  
**Maintainer:** Project Owner
