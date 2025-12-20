"""PDF processing service for extracting text from PDFs."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def process_pdf(file_path: str) -> str:
    """Extract text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If PDF cannot be processed
    """
    try:
        import pypdf
    except ImportError:
        logger.error("pypdf not installed")
        raise ValueError(
            "PDF support requires pypdf library. "
            "Install with: pip install pypdf"
        )
    
    try:
        path = Path(file_path)
        
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")
        
        if not path.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF: {file_path}")
        
        # Extract text from PDF
        text_content = []
        
        with open(path, 'rb') as pdf_file:
            pdf_reader = pypdf.PdfReader(pdf_file)
            
            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                raise ValueError("PDF has no pages")
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                except Exception as e:
                    logger.warning(
                        f"Error extracting text from page {page_num + 1}: {e}"
                    )
        
        if not text_content:
            raise ValueError("Could not extract any text from PDF")
        
        return "\n".join(text_content)
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise ValueError(f"Failed to process PDF: {str(e)}")


def validate_pdf(file_path: str) -> bool:
    """Validate if file is a readable PDF.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file is valid PDF, False otherwise
    """
    try:
        import pypdf
    except ImportError:
        return False
    
    try:
        path = Path(file_path)
        
        if not path.exists() or not path.suffix.lower() == '.pdf':
            return False
        
        with open(path, 'rb') as pdf_file:
            pypdf.PdfReader(pdf_file)
        
        return True
    
    except Exception:
        return False
