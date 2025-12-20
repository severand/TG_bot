"""Excel file parser for .xlsx and .xls formats.

Extracts text from Excel spreadsheets using openpyxl.
Handles multiple sheets and cell values.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parser for extracting text from Excel files.
    
    Supports: .xlsx, .xls (via openpyxl)
    Extracts text from all sheets and cells.
    """
    
    def extract_text(self, file_path: Path) -> str:
        """Extract text from Excel file.
        
        Reads all sheets and combines text from cells.
        Skips empty cells and organizes by sheet.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            str: Extracted text from all sheets
            
        Raises:
            ImportError: If openpyxl is not installed
            Exception: If file cannot be parsed
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            logger.error("openpyxl not installed. Install with: pip install openpyxl")
            raise ImportError("openpyxl is required for Excel file support")
        
        try:
            logger.info(f"Extracting text from Excel: {file_path.name}")
            
            # Load workbook
            workbook = load_workbook(file_path)
            all_text: list[str] = []
            
            # Process each sheet
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                logger.info(f"Processing sheet: {sheet_name}")
                
                sheet_text: list[str] = []
                sheet_text.append(f"=== Sheet: {sheet_name} ===")
                
                # Extract text from cells
                for row in sheet.iter_rows(values_only=True):
                    row_values = []
                    for cell_value in row:
                        if cell_value is not None:
                            row_values.append(str(cell_value).strip())
                    
                    if row_values:  # Skip empty rows
                        sheet_text.append(" | ".join(row_values))
                
                if len(sheet_text) > 1:  # Only add if sheet has content
                    all_text.append("\n".join(sheet_text))
            
            workbook.close()
            
            result = "\n\n".join(all_text)
            logger.info(f"Successfully extracted {len(result)} chars from Excel")
            return result
        
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path.name}: {e}")
            raise
