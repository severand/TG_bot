"""File processing services for RAG module.

Provides file conversion, parsing, and handling for various document formats.
Copied from app/services/file_processing for RAG knowledge base.
"""

from rag_module.file_processing.converter import FileConverter
from rag_module.file_processing.pdf_parser import PDFParser
from rag_module.file_processing.docx_parser import DOCXParser
from rag_module.file_processing.zip_handler import ZIPHandler

__all__ = [
    "FileConverter",
    "PDFParser",
    "DOCXParser",
    "ZIPHandler",
]
