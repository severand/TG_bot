# Technical Specification: RAG Knowledge Base Module 📄

**Version:** 1.0.0  
**Status:** Technical Specification Phase  
**Last Updated:** 2025-12-21  
**Author:** Project Owner  
**Classification:** Functional Requirements & Technical Design  

---

## 📋 Executive Summary

This document specifies the RAG (Retrieval-Augmented Generation) Knowledge Base Module - a standalone, production-ready system for document-based question answering integrated with the TG_bot Telegram chatbot.

**Key Metrics:**
- Supports 1000+ documents
- 85-90% token savings vs. naive approach
- Sub-second semantic search
- Multi-format document support (PDF, DOCX, TXT)
- Multilingual embeddings

---

## 1. FUNCTIONAL REQUIREMENTS

### 1.1 User Stories

#### US-1: Upload Documents
**As a** user  
**I want** to upload documents (PDF, DOCX, TXT, ZIP)  
**So that** I can build a searchable knowledge base

**Acceptance Criteria:**
- [ ] Accept PDF files up to 50MB
- [ ] Accept DOCX files up to 50MB
- [ ] Accept TXT files up to 10MB
- [ ] Accept ZIP containing multiple documents
- [ ] Extract text automatically
- [ ] Show progress during upload
- [ ] Confirm successful storage
- [ ] Return document ID and chunk count

#### US-2: Search Knowledge Base
**As a** user  
**I want** to search my documents with natural language questions  
**So that** I can find relevant information quickly

**Acceptance Criteria:**
- [ ] Accept free-form text queries
- [ ] Return top 5 most relevant chunks
- [ ] Show similarity scores (0-100%)
- [ ] Include source document names
- [ ] Support Russian, English, other languages
- [ ] Return results in <2 seconds
- [ ] Highlight relevant passages

#### US-3: View Document List
**As a** user  
**I want** to see all documents in my knowledge base  
**So that** I can manage what I've uploaded

**Acceptance Criteria:**
- [ ] Display all documents with metadata
- [ ] Show file size, upload date, chunk count
- [ ] Allow sorting by date, size, name
- [ ] Show total storage used
- [ ] Indicate if document is searchable

#### US-4: Delete Documents
**As a** user  
**I want** to remove documents from my knowledge base  
**So that** I can manage storage and privacy

**Acceptance Criteria:**
- [ ] Delete document by ID
- [ ] Remove all associated chunks
- [ ] Free up storage space
- [ ] Confirm before deletion
- [ ] Show deletion success message

#### US-5: Clear Knowledge Base
**As a** user  
**I want** to clear all documents at once  
**So that** I can start fresh

**Acceptance Criteria:**
- [ ] Delete all documents in one action
- [ ] Require confirmation (prevent accidents)
- [ ] Free all storage
- [ ] Show cleared notification

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Component Diagram

```
┌───────────────────────────────┐
│   TG_bot (Telegram Framework)      │
│ ┌──────────────────────────┐
│ │ app/handlers/knowledge.py       │  (Telegram Commands)
│ │ app/states/knowledge.py         │  (FSM States)
│ └──────────────────────────┘
└───────────────────────────────┘
              ↑
              ↑ imports
              ↑
┌───────────────────────────────┐
│   RAG Knowledge Base Module        │
│                                    │
│  ┌──────────────────────────┐
│  │ RAGManager (Orchestrator)      │
│  └──────────────────────────┘
│      ↑          ↑        ↑        ↑
│      ↑          ↑        ↑        ↑
│  ┌──────────────────────────┐
│  │ FileProc │ Chunker │ Embed │ Vector │
│  └──────────────────────────┘
│      ↑                             ↑
│      ↑                             ↑
│  ┌──────────────────────────┐
│  │ Retriever (Semantic Search)     │
│  └──────────────────────────┘
└───────────────────────────────┘
              ↑
              ↑
┌───────────────────────────────┐
│   External Systems                 │
│ ┌──────────────────────────┐
│ │ ChromaDB (Vector Store)         │
│ └──────────────────────────┘
│ ┌──────────────────────────┐
│ │ Sentence-Transformers (Embed)  │
│ └──────────────────────────┘
└───────────────────────────────┘
```

### 2.2 Data Flow Pipeline

#### Add Document Flow
```
User Upload
    ↓
[Validation] ✓ File exists, format ok, size < 50MB
    ↓
[FileProcessor] Extract text from PDF/DOCX/TXT
    ↓
[Chunker] Split into 500-token chunks with 50-token overlap
    ↓
[Embeddings] Generate 384-dim vectors for each chunk
    ↓
[VectorStore] Store in ChromaDB with metadata
    ↓
[Manager] Update document metadata
    ↓
Success ✓ Document searchable
```

#### Search Flow
```
User Query: "What are payment terms?"
    ↓
[Embeddings] Convert query to 384-dim vector
    ↓
[Retriever] Find 5 most similar chunks (cosine similarity)
    ↓
[Ranking] Sort by relevance score
    ↓
[LLM] Pass chunks + query to LLM for synthesis (future)
    ↓
Response ✓ "According to contract #123 (page 5): ..."
```

---

## 3. TECHNICAL SPECIFICATIONS

### 3.1 File Processing

**Input Formats:**
- PDF: Via PyPDF2, text extraction
- DOCX: Via python-docx, preserves structure
- TXT: Raw text files
- ZIP: Batch processing (future)

**Output:**
- Extracted text string
- Metadata (pages, structure)

**Constraints:**
- Max file size: 50MB
- Max documents: 10,000
- Supported languages: All (UTF-8)

### 3.2 Document Chunking

**Algorithm:**
1. Split on paragraph breaks (\n\n)
2. If chunk > 500 tokens, split on sentences
3. If chunk > 500 tokens, split on words
4. Add 50-token overlap for context
5. Attach metadata (source, position, page)

**Configuration:**
```python
CHUNK_SIZE = 500        # tokens/words
CHUNK_OVERLAP = 50      # overlap between chunks
SEPARATORS = [
    "\n\n",  # Paragraph
    "\n",    # Line
    ".",     # Sentence
    " ",     # Word
    ""       # Character
]
```

### 3.3 Embedding Generation

**Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Dimension: 384
- Speed: ~1000 texts/sec
- Multilingual: Russian, English, Chinese, etc.
- Download size: ~130MB

**Pipeline:**
```python
text → Tokenize → Transformer → 384-dim vector
```

**Batch Processing:**
- Batch size: 32 (configurable)
- Reduces memory usage
- Faster than sequential embedding

### 3.4 Vector Storage (ChromaDB)

**Database:** ChromaDB (embedded)

**Collections:**
```
chroma_db/
├── chunk_embeddings      # Main collection
│   ├── vectors.pkl       # Embeddings
│   ├── metadata.parquet  # Metadata
│   └── index.bin         # Index
├── doc_metadata.json    # Document info
└── logs/               # Operation logs
```

**Similarity Search:**
- Metric: Cosine similarity (default)
- Range: 0 (opposite) to 1 (identical)
- Threshold: > 0.3 (configurable)
- Top K: 5 results (configurable)

### 3.5 Semantic Search (Retriever)

**Algorithm:**
1. Embed query with same model as documents
2. Calculate cosine similarity with all stored embeddings
3. Return top K results above threshold
4. Add source information

**Performance:**
- Query time: <100ms (typical)
- Index size: ~1KB per chunk
- Search: O(n) with n=chunks

---

## 4. NON-FUNCTIONAL REQUIREMENTS

### 4.1 Performance

| Operation | Target | Actual* |
|-----------|--------|----------|
| Upload 1MB PDF | <5s | - |
| Generate embeddings | ~100ms per chunk | - |
| Semantic search | <200ms | - |
| Return top 5 results | <500ms total | - |
| Handle 10,000 documents | <2GB memory | - |

*To be measured during Phase 2

### 4.2 Scalability

- **Documents:** Up to 10,000
- **Chunks:** Up to 1,000,000
- **Storage:** ~1MB per 10 documents
- **Memory:** ~2GB per 100,000 chunks

### 4.3 Reliability

- **Uptime:** 99.5% (during bot operation)
- **Data persistence:** Automatic to disk
- **Recovery:** Graceful degradation if components fail
- **Backup:** Manual export (future)

### 4.4 Security

- **Access:** User-isolated knowledge bases
- **Privacy:** Documents stored locally (no cloud)
- **Encryption:** Future enhancement
- **Validation:** Input validation on all endpoints

---

## 5. ERROR HANDLING

### 5.1 Exception Hierarchy

```python
RAGException
  ├─ FileProcessingError
  ├─ ChunkingError
  ├─ EmbeddingError
  ├─ VectorStoreError
  ├─ RetrieverError
  ├─ ConfigurationError
  ├─ DocumentNotFoundError
  └─ ValidationError
```

### 5.2 Recovery Strategies

| Error | Strategy | Result |
|-------|----------|--------|
| File not found | User error message | Graceful fail |
| Embedding failure | Retry with smaller batch | Continue or fail cleanly |
| ChromaDB locked | Wait with timeout | Recover or timeout |
| Memory exhaustion | Process in batches | Success (slower) |
| Invalid config | Use defaults + warn | Continue with defaults |

---

## 6. CONFIGURATION

### 6.1 Environment Variables

```bash
# Paths
VECTOR_DB_PATH=./data/vector_db              # DB location
TEMP_DIR=./temp                              # Temp files

# Embeddings
EMBEDDING_MODEL=sentence-transformers/...   # Model name
EMBEDDING_DEVICE=auto                        # cpu/cuda/mps
EMBEDDING_BATCH_SIZE=32                      # Batch size

# Chunking
CHUNK_SIZE=500                               # Chunk size
CHUNK_OVERLAP=50                             # Overlap

# Retrieval
TOP_K_RESULTS=5                              # Max results
SIMILARITY_THRESHOLD=0.3                     # Min score

# Logging
DEBUG=false                                  # Debug mode
LOG_LEVEL=INFO                               # Logging level
```

---

## 7. TESTING STRATEGY

### 7.1 Test Coverage

- **Unit Tests:** >80% of services
- **Integration Tests:** Full pipeline
- **Performance Tests:** Benchmark all operations
- **Security Tests:** Input validation

### 7.2 Test Cases

**Chunker:**
- [ ] Simple text chunking
- [ ] Overlap handling
- [ ] Metadata attachment
- [ ] Empty text handling
- [ ] Large text handling

**Embeddings:**
- [ ] Single text embedding
- [ ] Batch embedding
- [ ] Dimension validation
- [ ] Different languages
- [ ] Out of memory handling

**Vector Store:**
- [ ] Add chunks
- [ ] Search by similarity
- [ ] Delete document
- [ ] Clear all
- [ ] Persistence

---

## 8. DEPLOYMENT

### 8.1 Requirements

- Python 3.10+
- 2GB RAM minimum
- 5GB disk space (for 1000 docs)
- Internet (for model download)

### 8.2 Installation

```bash
pip install -r requirements.txt
```

### 8.3 Verification

```python
from rag_module.manager import RAGManager
manager = RAGManager()
print("RAG module ready")
```

---

## 9. ROADMAP

### Phase 1 (Week 1)
- [x] Project setup & documentation
- [ ] Core services implementation
- [ ] Unit tests

### Phase 2 (Week 2)
- [ ] Integration with TG_bot
- [ ] Handler implementation
- [ ] Integration tests

### Phase 3 (Week 3+)
- [ ] Performance optimization
- [ ] Advanced features
- [ ] Production hardening

---

**Document Status:** Technical Specification  
**Last Updated:** 2025-12-21  
**Next Review:** After Phase 1 implementation  
**Owner:** Project Owner
