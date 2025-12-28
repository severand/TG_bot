"""Excel reader без внешних зависимостей.

Функционал:
- Чтение .xlsx (Excel 2007+) напрямую через zipfile + XML (только stdlib)
- Конвертация .xls -> .xlsx через:
  1. PowerShell COM (если стоит MS Excel на Windows)
  2. LibreOffice soffice --headless (если стоит LibreOffice)
  3. Если ничего нет - понятная ошибка

Python 3.8+, без pandas/xlrd/openpyxl.

Использование:
    from excel_reader import extract_spreadsheet
    data = extract_spreadsheet("file.xls")  # dict: sheet_name -> list[list[values]]
"""

import logging
import os
import re
import shutil
import string
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# XML Namespaces для Excel 2007+ (.xlsx)
_XL_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XL_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"main": _XL_NS_MAIN, "rel": _XL_NS_REL}

# Cache для быстрого преобразования букв -> индекс колонки
_COL_CACHE: Dict[str, int] = {}


# ============ Utilities ============

def _col_letters_to_index(col_letters: str) -> int:
    """Преобразует буквы в индекс: A->1, Z->26, AA->27, etc."""
    if col_letters in _COL_CACHE:
        return _COL_CACHE[col_letters]
    n = 0
    for ch in col_letters:
        n = n * 26 + (ord(ch) - 64)
    _COL_CACHE[col_letters] = n
    return n


def _cell_ref_to_coords(ref: str) -> Tuple[Optional[int], Optional[int]]:
    """Разбирает ссылку на ячейку: "C5" -> (row=5, col=3)."""
    m = re.match(r"^([A-Z]+)(\d+)$", ref)
    if not m:
        return None, None
    col_letters, row_str = m.group(1), m.group(2)
    return int(row_str), _col_letters_to_index(col_letters)


# ============ XLSX Reading (stdlib only) ============

def _read_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    """Читает общую таблицу строк из xl/sharedStrings.xml."""
    strings: List[str] = []
    try:
        with zf.open("xl/sharedStrings.xml") as f:
            root = ET.parse(f).getroot()
        
        for si in root.findall("main:si", _NS):
            parts = []
            # Rich text может быть в <r>/<t> или просто в <t>
            t_nodes = si.findall("main:t", _NS)
            if not t_nodes:
                # Rich text format
                for r in si.findall("main:r", _NS):
                    t_node = r.find("main:t", _NS)
                    if t_node is not None and t_node.text:
                        parts.append(t_node.text)
            else:
                # Plain text
                for t in t_nodes:
                    if t.text:
                        parts.append(t.text)
            strings.append("".join(parts))
    except KeyError:
        # sharedStrings не обязателен
        logger.debug("No sharedStrings.xml found in Excel file")
    except Exception as e:
        logger.warning(f"Error reading sharedStrings: {e}")
    
    return strings


def _load_rels(zf: zipfile.ZipFile, rels_path: str) -> Dict[str, str]:
    """Загружает отношения (rels) между элементами Excel."""
    rels = {}
    try:
        with zf.open(rels_path) as f:
            root = ET.parse(f).getroot()
        for rel in root.findall("rel:Relationship", _NS):
            rid = rel.get("Id")
            target = rel.get("Target")
            if rid and target:
                rels[rid] = target
    except Exception as e:
        logger.debug(f"Could not load rels from {rels_path}: {e}")
    
    return rels


def _read_workbook_sheets(zf: zipfile.ZipFile) -> List[Tuple[str, str]]:
    """Возвращает список (имя_листа, путь_в_zip) в порядке вкладок."""
    sheets: List[Tuple[str, str]] = []
    try:
        with zf.open("xl/workbook.xml") as f:
            wb = ET.parse(f).getroot()
        
        rels = _load_rels(zf, "xl/_rels/workbook.xml.rels")
        
        for sheet in wb.findall("main:sheets/main:sheet", _NS):
            name = sheet.get("name")
            rid = sheet.get(f"{{{_XL_NS_REL}}}id")
            
            if name and rid:
                target = rels.get(rid, "")
                # Приводим к полному пути
                if target and not target.startswith("xl/"):
                    target = "xl/" + target
                if target:
                    sheets.append((name, target))
    except Exception as e:
        logger.error(f"Error reading workbook sheets: {e}")
    
    return sheets


def _read_sheet(zf: zipfile.ZipFile, sheet_path: str, shared_strings: List[str]) -> List[List[Any]]:
    """Читает один лист из xlsx и возвращает список строк."""
    rows: List[List[Any]] = []
    
    try:
        with zf.open(sheet_path) as f:
            root = ET.parse(f).getroot()
        
        for row_elem in root.findall(".//main:sheetData/main:row", _NS):
            cells_by_col: Dict[int, Any] = {}
            max_col = 0
            
            for c in row_elem.findall("main:c", _NS):
                ref = c.get("r")  # "C5"
                t = c.get("t")    # тип: "s"=string, "b"=bool, "inlineStr"=inline string
                v_node = c.find("main:v", _NS)
                is_node = c.find("main:is", _NS)
                value: Any = None
                
                if t == "s":
                    # Shared string reference
                    if v_node is not None and v_node.text is not None:
                        try:
                            idx = int(v_node.text)
                            if 0 <= idx < len(shared_strings):
                                value = shared_strings[idx]
                        except (ValueError, IndexError):
                            pass
                
                elif t == "inlineStr":
                    # Inline string (rich text)
                    if is_node is not None:
                        parts = []
                        t_nodes = is_node.findall("main:t", _NS)
                        if not t_nodes:
                            for r in is_node.findall("main:r", _NS):
                                t2 = r.find("main:t", _NS)
                                if t2 is not None and t2.text:
                                    parts.append(t2.text)
                        else:
                            for t2 in t_nodes:
                                if t2.text:
                                    parts.append(t2.text)
                        value = "".join(parts)
                
                elif t == "b":
                    # Boolean
                    if v_node is not None and v_node.text is not None:
                        value = v_node.text == "1"
                
                else:
                    # Number or general
                    if v_node is not None and v_node.text is not None:
                        txt = v_node.text
                        try:
                            # Float если есть точка/экспонента, иначе int
                            if ("." in txt) or ("e" in txt.lower()):
                                value = float(txt)
                            else:
                                value = int(txt)
                        except ValueError:
                            value = txt
                
                if ref:
                    r_row, r_col = _cell_ref_to_coords(ref)
                    if r_col:
                        cells_by_col[r_col] = value
                        if r_col > max_col:
                            max_col = r_col
            
            # Сформировать плотную строку
            if max_col > 0:
                line = [None] * max_col
                for cidx, val in cells_by_col.items():
                    line[cidx - 1] = val
                rows.append(line)
    
    except Exception as e:
        logger.error(f"Error reading sheet {sheet_path}: {e}")
    
    return rows


def read_xlsx(path: str) -> Dict[str, List[List[Any]]]:
    """Читает .xlsx в структуру dict: sheet_name -> list[list[values]].
    
    Использует только stdlib (zipfile + xml.etree).
    
    Args:
        path: Путь к файлу .xlsx
        
    Returns:
        Словарь: имя_листа -> список строк (каждая строка = список значений)
        
    Raises:
        FileNotFoundError: Если файл не найден
        zipfile.BadZipFile: Если не валидный ZIP (испорченный .xlsx)
    """
    out: Dict[str, List[List[Any]]] = {}
    
    try:
        with zipfile.ZipFile(path) as zf:
            shared = _read_shared_strings(zf)
            sheets = _read_workbook_sheets(zf)
            
            for name, spath in sheets:
                if not spath:
                    continue
                out[name] = _read_sheet(zf, spath, shared)
                logger.debug(f"Read sheet '{name}': {len(out[name])} rows")
    
    except zipfile.BadZipFile as e:
        logger.error(f"Invalid or corrupted XLSX file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error reading XLSX: {e}")
        raise
    
    return out


# ============ XLS Conversion (PowerShell COM / LibreOffice) ============

def _convert_xls_via_excel_com(xls_path: str, out_xlsx_path: str) -> bool:
    """Конвертирует .xls -> .xlsx через PowerShell COM (требует MS Excel на Windows).
    
    Args:
        xls_path: Полный путь к .xls файлу
        out_xlsx_path: Куда сохранить .xlsx
        
    Returns:
        True если успешно, False если не удалось
    """
    try:
        xls_abs = str(Path(xls_path).resolve())
        xlsx_abs = str(Path(out_xlsx_path).resolve())
        
        ps_script = f"""
$ErrorActionPreference = 'Stop'
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {{
    $wb = $excel.Workbooks.Open('{xls_abs}', $false, $true)
    $wb.SaveAs('{xlsx_abs}', 51)
    $wb.Close($false)
    Write-Host "OK"
}} finally {{
    $excel.Quit()
}}
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and os.path.exists(out_xlsx_path):
            logger.info(f"Successfully converted {Path(xls_path).name} via Excel COM")
            return True
        else:
            logger.debug(f"Excel COM conversion failed: {result.stderr}")
            return False
    
    except Exception as e:
        logger.debug(f"Excel COM conversion error: {e}")
        return False


def _convert_xls_via_libreoffice(xls_path: str, out_dir: str) -> bool:
    """Конвертирует .xls -> .xlsx через LibreOffice (требует soffice в PATH).
    
    Args:
        xls_path: Полный путь к .xls файлу
        out_dir: Директория для вывода
        
    Returns:
        True если успешно, False если не удалось
    """
    try:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "xlsx", "--outdir", out_dir, xls_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            expected_xlsx = os.path.join(out_dir, Path(xls_path).stem + ".xlsx")
            if os.path.exists(expected_xlsx):
                logger.info(f"Successfully converted {Path(xls_path).name} via LibreOffice")
                return True
            logger.debug(f"LibreOffice: Expected file not found: {expected_xlsx}")
            return False
        else:
            logger.debug(f"LibreOffice conversion failed: {result.stderr}")
            return False
    
    except FileNotFoundError:
        logger.debug("soffice not found in PATH")
        return False
    except Exception as e:
        logger.debug(f"LibreOffice conversion error: {e}")
        return False


def convert_xls_to_xlsx(xls_path: str) -> str:
    """Конвертирует .xls в .xlsx.
    
    Пытается методы в порядке:
    1. PowerShell COM (Windows + MS Excel)
    2. LibreOffice soffice (любая ОС)
    3. Ошибка, если ничего не сработало
    
    Args:
        xls_path: Полный путь к .xls файлу
        
    Returns:
        Путь к конвертированному .xlsx файлу (во временной папке)
        
    Raises:
        RuntimeError: Если конвертация не удалась
    """
    tmp_dir = tempfile.mkdtemp(prefix="xls2xlsx_")
    out_path = os.path.join(tmp_dir, Path(xls_path).stem + ".xlsx")
    
    logger.info(f"Converting .xls to .xlsx: {Path(xls_path).name}")
    
    # Попытка 1: PowerShell COM
    if _convert_xls_via_excel_com(xls_path, out_path):
        return out_path
    
    # Попытка 2: LibreOffice
    if _convert_xls_via_libreoffice(xls_path, tmp_dir):
        return out_path
    
    # Очистка и ошибка
    shutil.rmtree(tmp_dir, ignore_errors=True)
    
    raise RuntimeError(
        f"Failed to convert {Path(xls_path).name}: "
        "Neither Excel COM (Windows + MS Excel) nor LibreOffice (soffice) are available. "
        "Please install one of them or fix pip to install pandas/xlrd."
    )


# ============ Public API ============

def extract_spreadsheet(path: str) -> Dict[str, List[List[Any]]]:
    """Универсально читает Excel файлы (.xls или .xlsx).
    
    Возвращает структуру:
        {
            "sheet_name_1": [
                [col1_val, col2_val, col3_val, ...],
                [col1_val, col2_val, col3_val, ...],
                ...
            ],
            "sheet_name_2": [...],
        }
    
    Для .xlsx: читает напрямую из ZIP (stdlib).
    Для .xls: конвертирует в .xlsx через Excel/LibreOffice, потом читает.
    
    Args:
        path: Путь к файлу .xls или .xlsx
        
    Returns:
        dict: sheet_name -> list of rows
        
    Raises:
        ValueError: Неподдерживаемое расширение
        FileNotFoundError: Файл не найден
        RuntimeError: Ошибка при обработке файла
        
    Example:
        >>> data = extract_spreadsheet("report.xlsx")
        >>> for sheet_name, rows in data.items():
        ...     print(f"Sheet: {sheet_name}, Rows: {len(rows)}")
        ...     for row in rows[:3]:
        ...         print("  ", row)
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    ext = path_obj.suffix.lower()
    
    if ext == ".xlsx":
        logger.info(f"Reading Excel file: {path_obj.name} (XLSX format)")
        return read_xlsx(str(path_obj))
    
    if ext == ".xls":
        logger.info(f"Reading Excel file: {path_obj.name} (XLS format, converting to XLSX)")
        xlsx_path = convert_xls_to_xlsx(str(path_obj))
        try:
            return read_xlsx(xlsx_path)
        finally:
            # Очистка временной папки
            try:
                shutil.rmtree(Path(xlsx_path).parent, ignore_errors=True)
                logger.debug(f"Cleaned up temporary directory: {Path(xlsx_path).parent}")
            except Exception:
                pass
    
    raise ValueError(f"Unsupported file extension: {ext}. Expected .xls or .xlsx")
