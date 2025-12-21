"""RAG module utilities.

Utility modules for validation, formatting, and logging:
  - validators: Input validation and sanitization
  - formatters: Output formatting and presentation
  - logger: Structured logging configuration
"""

from rag_module.utils.validators import (
    validate_file_path,
    validate_doc_id,
    validate_query,
    validate_top_k,
    validate_similarity_threshold,
)
from rag_module.utils.formatters import (
    format_search_results,
    format_document_info,
    format_stats,
)
from rag_module.utils.logger import setup_logger, get_logger

__all__ = [
    # Validators
    "validate_file_path",
    "validate_doc_id",
    "validate_query",
    "validate_top_k",
    "validate_similarity_threshold",
    # Formatters
    "format_search_results",
    "format_document_info",
    "format_stats",
    # Logger
    "setup_logger",
    "get_logger",
]
