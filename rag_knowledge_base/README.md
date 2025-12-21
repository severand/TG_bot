# RAG Knowledge Base Module 🧠

**Version:** 1.0.0 (In Development)  
**Status:** 🔧 Active Development  
**Last Updated:** 2025-12-21  

---

## 📋 Module Overview

This is a **standalone, scalable RAG (Retrieval-Augmented Generation) module** designed for the TG_bot project.

### Core Capabilities
- 🔄 **Document Management** - Upload, store, retrieve documents
- 🧠 **Semantic Search** - Find relevant content using embeddings
- 💾 **Vector Storage** - ChromaDB for efficient retrieval
- 🤖 **LLM Integration** - Answer questions based on document knowledge
- 📊 **Scalability** - Designed for 1000+ documents

---

## 🎯 Purpose & Vision

### The Problem
Users repeatedly upload same documents and bots can't remember information across conversations.

### The Solution
RAG lets users upload documents ONCE and ask unlimited questions with accurate answers based on stored knowledge.

---

## 📁 Project Structure

```
rag_knowledge_base/
├── README.md                    # This file
├── ARCHITECTURE.md              # Technical design
├── DEVELOPMENT.md               # Dev guide
├── DEPLOYMENT.md                # Production guide
├── TROUBLESHOOTING.md           # Common issues
├── requirements.txt             # Dependencies
│
├── rag_module/                  # Main implementation
│   ├── __init__.py
│   ├── config.py                # Configuration
│   ├── models.py                # Data models
│   ├── exceptions.py            # Custom exceptions
│   │
│   ├── services/                # Core services
│   │   ├── __init__.py
│   │   ├── chunker.py           # Doc → Chunks
│   │   ├── embeddings.py        # Text → Vectors
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   ├── retriever.py         # Semantic search
│   │   ├── manager.py           # Orchestrator
│   │   └── file_processor.py    # Parse PDF/DOCX
│   │
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── validators.py        # Input validation
│       ├── formatters.py        # Output formatting
│       └── logger.py            # Logging setup
│
├── tests/                       # Unit & integration tests
│   ├── __init__.py
│   ├── test_chunker.py
│   ├── test_embeddings.py
│   ├── test_vector_store.py
│   ├── test_retriever.py
│   ├── test_manager.py
│   └── test_integration.py
│
├── examples/                    # Usage examples
│   ├── basic_example.py         # Simple usage
│   ├── advanced_example.py      # Advanced features
│   └── sample_documents/        # Test docs
│
└── docs/                        # Extended docs
    ├── API.md                   # API reference
    ├── FAQ.md                   # FAQs
    ├── PERFORMANCE.md           # Benchmarks
    └── MIGRATION.md             # Migration guide
```

---

## 🚀 Quick Start

```bash
cd rag_knowledge_base
pip install -r requirements.txt
```

```python
from rag_module.manager import RAGManager

# Initialize
manager = RAGManager()

# Add document
await manager.add_document(
    file_path="contract.pdf",
    doc_id="contract_2024"
)

# Search
results = await manager.search(
    query="What are payment terms?",
    top_k=3
)
```

---

## 📖 Documentation Map

1. **README.md** (you are here) - Overview
2. **ARCHITECTURE.md** - Technical design
3. **DEVELOPMENT.md** - How to develop
4. **docs/API.md** - Complete API reference
5. **tests/** - See test examples
6. **examples/** - Working code

---

## 🔧 Configuration

```bash
# Vector DB
VECTOR_DB_PATH=./data/vector_db
VECTOR_DB_PERSIST=true

# Embeddings
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Retrieval
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.3

# LLM
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7
```

---

## ✅ Phase 1 Features

### Implemented
- Document chunking (configurable)
- Embedding generation (multi-language)
- Vector store (ChromaDB)
- Semantic search
- Document CRUD

### Planned
- Hybrid search
- Document versioning
- Metadata filtering
- Batch operations

---

## 🔌 Integration with TG_bot

```python
# In main.py:
from rag_knowledge_base.rag_module.manager import RAGManager
from app.handlers import knowledge

dispatcher.include_router(knowledge.router)
```

---

## 📊 Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Vector DB | ChromaDB | Open-source, embedded, fast |
| Embeddings | Sentence-Transformers | Multilingual, reliable |
| Chunking | Custom | Full control |
| Parsing | PyPDF2, python-docx | Standard, reliable |
| Async | asyncio | Non-blocking I/O |
| Testing | pytest | Industry standard |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=rag_module

# Specific test
pytest tests/test_chunker.py -v
```

---

## 🚫 Troubleshooting

**ChromaDB not found?**  
→ `pip install chromadb`

**Vector dimension mismatch?**  
→ Check embedding model consistency

**Search returns empty?**  
→ Verify documents were added

See `TROUBLESHOOTING.md` for more.

---

## 📝 Roadmap

**Week 1 (21-27 Dec)** - Core implementation  
**Week 2 (28 Dec - 3 Jan)** - Integration & docs  
**Week 3+** - Optimization & advanced features

---

**Status:** 🔧 Active Development  
**Last Updated:** 2025-12-21  
**Maintainer:** Project Owner
