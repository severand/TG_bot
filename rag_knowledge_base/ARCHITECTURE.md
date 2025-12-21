# RAG Module Architecture 📚

**Version:** 1.0.0  
**Status:** Design Phase  
**Last Updated:** 2025-12-21  

---

## 📋 Overview

The RAG (Retrieval-Augmented Generation) module is built around a **pipeline architecture** with clear separation of concerns:

```
Document Input
    ↓
[File Processor] - Extract text from PDF/DOCX/TXT
    ↓
[Chunker] - Split into semantically coherent chunks
    ↓
[Embeddings] - Convert chunks to vectors
    ↓
[Vector Store] - Store in ChromaDB
    ↓
Knowledge Base (Persisted)
    
    ↑
    ↑
    ↑

User Query
    ↓
[Embeddings] - Convert query to vector
    ↓
[Retriever] - Semantic search in ChromaDB
    ↓
[Results] - Top K similar chunks
    ↓
[LLM Integration] - Generate answer with context
    ↓
User Response
```

---

## 🔧 Core Components

### 1. File Processor (`services/file_processor.py`)

**Responsibility:** Extract text from various document formats

**Supported Formats:**
- PDF (via PyPDF2)
- DOCX (via python-docx)
- TXT (raw text)
- ZIP (batch processing)

**Key Methods:**
```python
class FileProcessor:
    def extract_from_pdf(self, file_path: Path) -> str
    def extract_from_docx(self, file_path: Path) -> str
    def extract_from_txt(self, file_path: Path) -> str
    def extract_from_zip(self, file_path: Path) -> List[Tuple[str, str]]
    def process_file(self, file_path: Path) -> str  # Auto-detect format
```

**Design Decision:**  
Reuse existing parsers from main TG_bot project (`PDFParser`, `DOCXParser`) to maintain consistency.

---

### 2. Chunker (`services/chunker.py`)

**Responsibility:** Split documents into optimal-size chunks for embedding

**Why Chunking?**
- Embeddings have token limits
- Semantic units improve search quality
- Allows retrieval of relevant sections

**Configuration:**
```python
CHUNK_SIZE = 500        # tokens/words per chunk
CHUNK_OVERLAP = 50      # overlap between chunks for context
Separators = ["\n\n", "\n", ".", " ", ""]  # Hierarchy
```

**Algorithm:**
1. Split on primary separator (paragraph breaks)
2. If chunk > CHUNK_SIZE, split on next separator
3. Add overlap to maintain context
4. Add metadata (source, page, position)

**Key Methods:**
```python
class Chunker:
    def chunk_text(self, text: str, metadata: Dict) -> List[Chunk]
    def chunk_documents(self, documents: List[Document]) -> List[Chunk]
```

---

### 3. Embeddings (`services/embeddings.py`)

**Responsibility:** Convert text to dense vectors

**Model Selection:**
- **Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Why:** Multilingual, 384-dimensional, fast, open-source
- **Size:** ~130MB (one-time download)

**Embedding Pipeline:**
```python
class EmbeddingService:
    def __init__(self, model_name: str = "...")
    
    async def embed_text(self, text: str) -> List[float]
    async def embed_batch(self, texts: List[str]) -> List[List[float]]
    
    def get_dimension(self) -> int  # Always 384
```

**Characteristics:**
- **Dimension:** 384
- **Speed:** ~1000 texts/sec (on modern GPU)
- **Memory:** ~500MB per 1000 texts
- **Multilingual:** Russian, English, Chinese, etc.

---

### 4. Vector Store (`services/vector_store.py`)

**Responsibility:** Store and manage embeddings with ChromaDB

**ChromaDB Features:**
- Embedded (no separate server needed)
- Persistent (saves to disk)
- Fast similarity search
- Metadata filtering support

**Data Model:**
```python
class ChromaDBStore:
    # Store chunks with embeddings
    async def add_chunks(
        self,
        chunks: List[Chunk],
        doc_id: str
    ) -> None
    
    # Retrieve by similarity
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        metadata_filter: Dict = None
    ) -> List[SearchResult]
    
    # Document management
    async def delete_document(self, doc_id: str) -> None
    async def list_documents(self) -> List[str]
    async def clear_all(self) -> None
```

**Storage:**
```
data/
└── vector_db/
    ├── chroma_db/          # ChromaDB data
    ├── metadata.json      # Document metadata
    └── logs/              # Operation logs
```

---

### 5. Retriever (`services/retriever.py`)

**Responsibility:** Semantic search in the vector store

**Search Algorithm:**
```
1. Convert query to embedding
2. Calculate similarity (cosine) with all stored embeddings
3. Return top K most similar chunks
4. Filter by threshold if needed
5. Re-rank by relevance (optional)
```

**Key Methods:**
```python
class Retriever:
    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[RetrievedChunk]
    
    async def search_with_filter(
        self,
        query: str,
        filters: Dict,
        top_k: int = 5
    ) -> List[RetrievedChunk]
```

**Similarity Metric:**
- **Cosine Similarity** (default)
- Values: 0 (opposite) to 1 (identical)
- Threshold: 0.3 (tunable)

---

### 6. Manager (`services/manager.py`)

**Responsibility:** Orchestrate all components, expose high-level API

**Role:** Coordinator that hides internal complexity

```python
class RAGManager:
    def __init__(self, config: RAGConfig)
    
    # Document Management
    async def add_document(
        self,
        file_path: Path,
        doc_id: str,
        metadata: Dict = None
    ) -> DocumentInfo
    
    async def remove_document(self, doc_id: str) -> bool
    
    # Search & Query
    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> SearchResult
    
    # Admin
    async def list_documents(self) -> List[DocumentInfo]
    async def get_document_stats(self, doc_id: str) -> Dict
    async def clear_all(self) -> None
    
    # Health
    async def health_check(self) -> HealthStatus
```

---

## 🔄 Data Flow

### Adding a Document

```
User uploads contract.pdf
↓
FileProcessor.process_file()
  → Extract all text from PDF
  → Return: str (full text)
↓
Chunker.chunk_text()
  → Split into 500-token chunks
  → Add metadata (source, position)
  → Return: List[Chunk]
↓
EmbeddingService.embed_batch()
  → Convert chunks to vectors
  → Return: List[List[float]] (384-dim each)
↓
VectorStore.add_chunks()
  → Store in ChromaDB
  → Persist to disk
↓
Done! Document searchable immediately
```

### Searching

```
User: "What are payment terms?"
↓
EmbeddingService.embed_text()
  → Convert query to 384-dim vector
↓
Retriever.search()
  → Find top 5 similar chunks in ChromaDB
  → Return with similarity scores
↓
LLM Integration (in Handler)
  → Pass chunks + query to LLM
  → Generate answer with context
↓
User gets answer with sources
```

---

## 📄 Data Models

### Document
```python
@dataclass
class Document:
    doc_id: str              # Unique ID
    title: str               # Human-readable name
    file_path: Path          # Original file location
    file_type: str           # pdf, docx, txt
    file_size: int           # Bytes
    content: str             # Full text
    created_at: datetime     # Upload time
    updated_at: datetime
    metadata: Dict           # Custom metadata
```

### Chunk
```python
@dataclass
class Chunk:
    chunk_id: str            # Unique ID (doc_id:position)
    doc_id: str              # Parent document
    text: str                # Chunk content
    position: int            # Position in document
    page_number: int         # For PDFs
    embedding: List[float]   # 384-dimensional vector
    metadata: Dict           # Source info, position, etc.
```

### SearchResult
```python
@dataclass
class SearchResult:
    chunk_id: str
    text: str
    similarity_score: float  # 0-1
    source_doc: str
    page_number: int
    metadata: Dict
```

---

## 💾 Persistence Strategy

### What Gets Persisted?
1. **ChromaDB Data** - Embeddings + chunks
   - Location: `data/vector_db/chroma_db/`
   - Format: Binary (ChromaDB format)
   - Auto-persisted on every add/update

2. **Metadata** - Document info
   - Location: `data/vector_db/metadata.json`
   - Format: JSON
   - Updated on add/remove/update

3. **Logs** - Operation logs (optional)
   - Location: `data/vector_db/logs/`
   - Format: Text logs
   - For debugging & audit

### Recovery
- If ChromaDB corrupted: Regenerate from original files
- If metadata lost: Scan ChromaDB to rebuild
- Graceful degradation: Missing metadata doesn't break search

---

## 🔌 Configuration

### Environment Variables
```bash
# Paths
VECTOR_DB_PATH=./data/vector_db          # Where to store DB
TEMP_DIR=./temp                          # Temp file location

# Embeddings
EMBEDDING_MODEL=sentence-transformers/...
EMBEDDING_DEVICE=auto                    # cpu, cuda, auto

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Retrieval
TOP_K_RESULTS=5                          # Default results
SIMILARITY_THRESHOLD=0.3                 # Min score

# LLM
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7
```

### Runtime Configuration
```python
@dataclass
class RAGConfig:
    # Paths
    vector_db_path: Path = Path("./data/vector_db")
    
    # Embeddings
    embedding_model: str = "sentence-transformers/..."
    embedding_batch_size: int = 32
    
    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Retrieval
    top_k: int = 5
    similarity_threshold: float = 0.3
    
    # Performance
    use_cache: bool = True
    cache_size: int = 1000
```

---

## 🔧 Error Handling Strategy

### Exception Hierarchy
```python
RAGException (base)
  ├─ FileProcessingError
  ├─ ChunkingError
  ├─ EmbeddingError
  ├─ VectorStoreError
  ├─ RetrieverError
  ├─ ConfigurationError
  └─ IntegrationError
```

### Recovery Strategies
1. **File not found** → Graceful error to user
2. **Embedding failure** → Retry with smaller batch
3. **ChromaDB locked** → Wait & retry (with timeout)
4. **Memory exhaustion** → Process in smaller batches
5. **Invalid config** → Use defaults with warning

---

## 💡 Design Decisions

### 1. Why ChromaDB?
- **Pros:** Embedded, persistent, fast, open-source
- **Cons:** Not distributed (OK for single server)
- **Alternative considered:** Pinecone (requires API, $$)

### 2. Why Sentence-Transformers?
- **Pros:** Multilingual, fast, small model
- **Cons:** Not fine-tuned for domain
- **Future:** Allow custom models via config

### 3. Why Async/Await?
- **Pros:** Non-blocking I/O, scales better
- **Cons:** Slightly more complex
- **Reason:** Large documents = slow parsing

### 4. Why Separate Module?
- **Pros:** Scalable, testable, reusable
- **Cons:** More files to manage
- **Benefit:** Can use in other projects

---

## 🔍 Testing Strategy

### Unit Tests
- Test each service independently
- Mock dependencies
- Test error cases

### Integration Tests
- Test full pipeline (upload → search)
- Use sample documents
- Verify persistence

### Performance Tests
- Benchmark document processing
- Measure embedding speed
- Test with 1000+ documents

---

## 🚀 Deployment Considerations

### Single Server
- ChromaDB runs in-process
- Data stored locally
- Simple, no dependencies

### Multi-Server (Future)
- Shared vector DB needed
- Consider Weaviate or Qdrant
- External embedding service

### Scaling
- **Reads:** Cache embeddings
- **Writes:** Batch processing
- **Storage:** Archive old documents

---

**Last Updated:** 2025-12-21  
**Next Review:** After Phase 1 implementation
