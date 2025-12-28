"""Excel файлов (.xlsx и .xls) парсер.

Подходит для:
- .xlsx (Excel 2007+) - читает напрямую через stdlib (zipfile + xml)
- .xls (Excel 97-2003) - конвертирует в .xlsx через Excel COM или LibreOffice

КОНВЕРТАЦИЯ:
- Попытается PowerShell COM (Windows + MS Excel)
- Затем LibreOffice soffice (если установлен)
- Понятная ошибка если ничего нет

ЭКСТРАКТ:
- Все листы в текст
- Структура таблицы сохранена
- Пустые ячейки обработаны

Исключены зависимости: pandas/openpyxl/xlrd
"""

import logging
from pathlib import Path

from app.services.file_processing.excel_reader import extract_spreadsheet

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parse Excel files (.xlsx and .xls) без внешних зависимостей."""

    def extract_text(self, file_path: Path) -> str:
        """Парсить Excel файл и вернуть текст.
        
        Args:
            file_path: Path to Excel file (.xlsx or .xls)
            
        Returns:
            Extracted text from all sheets (tab-separated values, sheet names as headers)
            
        Raises:
            ValueError: If file format is unsupported, conversion failed, or no data extracted
            FileNotFoundError: If file doesn't exist
        """
        file_name = file_path.name.lower()
        
        # Validate format from extension
        if not (file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            raise ValueError(f"Unsupported Excel format: {file_name}")
        
        # Determine format and log
        file_type = "XLSX" if file_name.endswith('.xlsx') else "XLS"
        logger.info(f"Parsing .{file_type.lower()} file: {file_path.name}")
        
        try:
            # Используем универсальный excel_reader
            # Он сам разберётся с .xls (конвертация) и .xlsx (прямое чтение)
            logger.debug(f"Starting extraction from: {file_path}")
            spreadsheet_data = extract_spreadsheet(str(file_path))
            
            if not spreadsheet_data:
                error_msg = f"Excel file {file_path.name} has no sheets or is empty"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Found {len(spreadsheet_data)} sheets to process")
            
            # Преобразуем в текст: лист за листом, tab-separated values
            all_text = []
            
            for sheet_name, rows in spreadsheet_data.items():
                logger.info(f"Processing sheet '{sheet_name}': {len(rows)} rows")
                
                # Заголовок листа
                all_text.append(f"\n=== {sheet_name} ===")
                
                # Пропускаем пустые листы
                if not rows:
                    logger.debug(f"Sheet '{sheet_name}' is empty, skipping")
                    all_text.append("[Empty sheet]")
                    continue
                
                # Строки tab-separated
                for row_idx, row in enumerate(rows, 1):
                    # Преобразуем значения в строки
                    cells = [
                        str(cell) if cell is not None else ""
                        for cell in row
                    ]
                    line = "\t".join(cells)
                    all_text.append(line)
                    
                logger.debug(f"Sheet '{sheet_name}' processed: {len(rows)} rows extracted")
            
            text = "\n".join(all_text).strip()
            
            if not text:
                error_msg = f"No data extracted from {file_path.name}"
                logger.warning(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Successfully extracted {len(text)} characters from {file_path.name}")
            return text
        
        except FileNotFoundError as e:
            logger.error(f"Excel file not found: {file_path.name}")
            raise ValueError(f"File not found: {file_path.name}") from e
        
        except RuntimeError as e:
            # Ошибка конвертации .xls
            logger.error(f"XLS conversion failed: {e}")
            error_msg = str(e)
            # Если ошибка конвертации - ломаем на пользователю
            raise ValueError(
                f"Cannot convert .xls file: {error_msg} "
                f"Install MS Excel (Windows) or LibreOffice to convert .xls files."
            ) from e
        
        except ValueError as e:
            logger.error(f"Unsupported format or corrupted file: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error parsing Excel file: {e}", exc_info=True)
            raise ValueError(f"Failed to parse Excel file {file_path.name}: {str(e)}") from e
