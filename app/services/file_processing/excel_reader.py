"""Zero-dependency Excel reader for .xlsx and .xls files.

Reads .xlsx files directly using only stdlib (zipfile + xml.etree).
Converts .xls to .xlsx using Excel COM (Windows) or LibreOffice (any platform).

NO external dependencies:
- No pandas
- No xlrd
- No aspose-words
- Pure Python 3.8+ stdlib

REQUIREMENTS for .xls conversion:
- Windows + MS Excel: PowerShell COM (built-in)
- Any OS: LibreOffice installed with soffice in PATH
"""

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
import traceback

logger = logging.getLogger(__name__)

# Configure logger to include function name, line number, and logger name
if not logger.handlers:
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
    )
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)

# XML Namespaces for Office Open XML
_XL_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_XL_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"main": _XL_NS_MAIN, "rel": _XL_NS_REL}

# Cache for column letter conversions
_COL_CACHE = {}


def _col_letters_to_index(col_letters: str) -> int:
    """Convert column letters to index: A=1, B=2, ..., Z=26, AA=27, ..."""
    if col_letters in _COL_CACHE:
        return _COL_CACHE[col_letters]
    n = 0
    for ch in col_letters:
        n = n * 26 + (ord(ch) - 64)
    _COL_CACHE[col_letters] = n
    return n


def _cell_ref_to_coords(ref: str):
    """Convert cell reference like 'C5' to (row=5, col=3)."""
    m = re.match(r"^([A-Z]+)(\d+)$", ref)
    if not m:
        return None, None
    col_letters, row_str = m.group(1), m.group(2)
    return int(row_str), _col_letters_to_index(col_letters)


def _read_shared_strings(zf: zipfile.ZipFile):
    """Read shared strings from sharedStrings.xml."""
    strings = []
    try:
        with zf.open("xl/sharedStrings.xml") as f:
            root = ET.parse(f).getroot()
        for si in root.findall("main:si", _NS):
            parts = []
            # Handle both <t> and <r>/<t> structures
            t_nodes = si.findall("main:t", _NS)
            if not t_nodes:
                for r in si.findall("main:r", _NS):
                    t_node = r.find("main:t", _NS)
                    if t_node is not None and t_node.text:
                        parts.append(t_node.text)
            else:
                for t in t_nodes:
                    if t.text:
                        parts.append(t.text)
            strings.append("".join(parts))
        logger.debug(f"Loaded {len(strings)} shared strings")
    except KeyError:
        logger.debug("No sharedStrings.xml found")
        pass
    return strings


def _load_rels(zf: zipfile.ZipFile, rels_path: str):
    """Load relationships from .rels file."""
    rels = {}
    try:
        with zf.open(rels_path) as f:
            root = ET.parse(f).getroot()
        for rel in root.findall("rel:Relationship", _NS):
            rid = rel.get("Id")
            target = rel.get("Target")
            rels[rid] = target
        logger.debug(f"Loaded {len(rels)} relationships from {rels_path}")
        for rid, target in list(rels.items())[:5]:  # Log first 5 for debugging
            logger.debug(f"  Rel: {rid} -> {target}")
    except KeyError as e:
        logger.warning(f"Relationships file not found: {rels_path}. Error: {e}")
    return rels


def _read_workbook_sheets(zf: zipfile.ZipFile):
    """Get list of sheets from workbook.xml.
    
    Resolves sheet paths from workbook relationships and returns
    list of (sheet_name, sheet_path) tuples.
    """
    try:
        with zf.open("xl/workbook.xml") as f:
            wb = ET.parse(f).getroot()
    except KeyError as e:
        logger.error(f"workbook.xml not found in archive: {e}", exc_info=True)
        return []
    
    rels = _load_rels(zf, "xl/_rels/workbook.xml.rels")
    logger.debug(f"Total relationships loaded: {len(rels)}")
    
    sheets = []
    sheet_elements = wb.findall("main:sheets/main:sheet", _NS)
    logger.debug(f"Found {len(sheet_elements)} sheet elements in workbook.xml")
    
    for idx, sheet in enumerate(sheet_elements):
        name = sheet.get("name")
        rid = sheet.get(f"{{{_XL_NS_REL}}}id")
        
        logger.debug(f"Sheet {idx}: name={name}, rid={rid}")
        
        if not rid:
            logger.warning(f"Sheet '{name}' has no relationship ID, skipping")
            continue
        
        target = rels.get(rid)
        logger.debug(f"  Looking up rid='{rid}' in rels dict: {target}")
        
        if not target:
            logger.warning(f"Sheet '{name}' (rid={rid}): relationship not found in rels. Available rids: {list(rels.keys())}")
            continue
        
        # Ensure path starts with xl/ (Office Open XML standard)
        if not target.startswith("xl/"):
            target = "xl/" + target
        
        logger.debug(f"Resolved sheet '{name}' (rid={rid}) -> {target}")
        sheets.append((name, target))
    
    logger.info(f"Successfully resolved {len(sheets)} out of {len(sheet_elements)} sheets")
    return sheets


def _read_sheet(zf: zipfile.ZipFile, sheet_path: str, shared_strings):
    """Read a sheet and return list of rows (list of lists)."""
    rows = []
    try:
        with zf.open(sheet_path) as f:
            root = ET.parse(f).getroot()
        logger.debug(f"Opened sheet: {sheet_path}")
    except KeyError as e:
        logger.error(f"Sheet path not found in archive: {sheet_path}. Error: {e}")
        return rows
    except Exception as e:
        logger.error(f"Error opening sheet {sheet_path}: {e}", exc_info=True)
        return rows
    
    try:
        row_elements = root.findall(".//main:sheetData/main:row", _NS)
        logger.debug(f"Sheet {sheet_path}: found {len(row_elements)} row elements")
        
        for row_idx, row in enumerate(row_elements):
            cells_by_col = {}
            max_col = 0
            for c in row.findall("main:c", _NS):
                ref = c.get("r")
                t = c.get("t")
                v_node = c.find("main:v", _NS)
                is_node = c.find("main:is", _NS)  # inlineStr
                value = None
                if t == "s":  # shared string
                    if v_node is not None and v_node.text is not None:
                        idx = int(v_node.text)
                        if 0 <= idx < len(shared_strings):
                            value = shared_strings[idx]
                        else:
                            logger.debug(f"Shared string index {idx} out of range (total: {len(shared_strings)})")
                            value = ""
                    else:
                        value = ""
                elif t == "inlineStr":
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
                    else:
                        value = ""
                else:
                    # Numbers, booleans, formulas
                    if v_node is not None and v_node.text is not None:
                        if t == "b":
                            value = True if v_node.text == "1" else False
                        else:
                            txt = v_node.text
                            try:
                                value = float(txt) if ((".") in txt or ("e" in txt) or ("E" in txt)) else int(txt)
                            except ValueError:
                                value = txt
                    else:
                        value = None
                if ref:
                    r_row, r_col = _cell_ref_to_coords(ref)
                    if r_col:
                        cells_by_col[r_col] = value
                        if r_col > max_col:
                            max_col = r_col
            # Form dense row from 1..max_col
            line = [None] * max_col
            for cidx, val in cells_by_col.items():
                line[cidx - 1] = val
            rows.append(line)
        
        logger.debug(f"Sheet {sheet_path}: processed {len(rows)} rows")
    except Exception as e:
        logger.error(f"Error parsing sheet {sheet_path}: {e}", exc_info=True)
    
    return rows


def read_xlsx(path: str):
    """Read .xlsx file and return dict: sheet_name -> list[list[values]]."""
    logger.info(f"[read_xlsx] Starting to read .xlsx: {Path(path).name}")
    try:
        with zipfile.ZipFile(path) as zf:
            logger.debug(f"[read_xlsx] Opened ZIP file: {path}")
            
            shared = _read_shared_strings(zf)
            logger.debug(f"[read_xlsx] Read {len(shared)} shared strings")
            
            sheets = _read_workbook_sheets(zf)
            logger.debug(f"[read_xlsx] Found {len(sheets)} sheets in workbook")
            
            if not sheets:
                logger.warning(f"[read_xlsx] No sheets found or all sheets were skipped!")
                return {}
            
            out = {}
            for name, spath in sheets:
                logger.debug(f"[read_xlsx] Reading sheet: {name} from {spath}")
                out[name] = _read_sheet(zf, spath, shared)
                row_count = len(out[name])
                logger.info(f"[read_xlsx] Sheet '{name}': {row_count} rows extracted")
            
            logger.info(f"[read_xlsx] Successfully read {len(out)} sheets from {Path(path).name}")
            return out
    except zipfile.BadZipFile as e:
        logger.error(f"[read_xlsx] File is not a valid ZIP/XLSX: {e}", exc_info=True)
        raise ValueError(f"Invalid XLSX file: {Path(path).name}") from e
    except Exception as e:
        logger.error(f"[read_xlsx] Unexpected error: {e}", exc_info=True)
        raise


def _convert_xls_via_excel_com(xls_path: str, out_xlsx_path: str):
    """Convert .xls to .xlsx using Excel COM (Windows only)."""
    logger.info(f"[_convert_xls_via_excel_com] Attempting conversion via Excel COM")
    xls_full = str(Path(xls_path).resolve())
    out_full = str(Path(out_xlsx_path).resolve())
    logger.debug(f"[_convert_xls_via_excel_com] Source: {xls_full}")
    logger.debug(f"[_convert_xls_via_excel_com] Output: {out_full}")
    ps = rf"""
$ErrorActionPreference = 'Stop'
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {{
    $wb = $excel.Workbooks.Open('{xls_full}', $false, $true)
    $wb.SaveAs('{out_full}', 51)
    $wb.Close($false)
}} finally {{
    $excel.Quit()
}}
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            logger.error(f"[_convert_xls_via_excel_com] PowerShell failed (code {result.returncode}): {error_msg}")
            raise RuntimeError(f"PowerShell Excel COM failed: {error_msg}")
        logger.info("[_convert_xls_via_excel_com] Conversion successful")
    except FileNotFoundError:
        logger.warning("[_convert_xls_via_excel_com] powershell not found on system")
        raise RuntimeError("PowerShell not available")
    except subprocess.TimeoutExpired:
        logger.error("[_convert_xls_via_excel_com] Conversion timed out (120s)")
        raise RuntimeError("Excel COM conversion timeout")


def _convert_xls_via_libreoffice(xls_path: str, out_dir: str):
    """Convert .xls to .xlsx using LibreOffice soffice command."""
    logger.info(f"[_convert_xls_via_libreoffice] Attempting conversion via soffice")
    logger.debug(f"[_convert_xls_via_libreoffice] Source: {xls_path}")
    logger.debug(f"[_convert_xls_via_libreoffice] Output dir: {out_dir}")
    try:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "xlsx", "--outdir", out_dir, xls_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            logger.error(f"[_convert_xls_via_libreoffice] soffice failed (code {result.returncode}): {error_msg}")
            raise RuntimeError(f"LibreOffice conversion failed: {error_msg}")
        logger.info("[_convert_xls_via_libreoffice] Conversion successful")
    except FileNotFoundError:
        logger.warning("[_convert_xls_via_libreoffice] soffice not found in PATH")
        raise RuntimeError("LibreOffice soffice not available")
    except subprocess.TimeoutExpired:
        logger.error("[_convert_xls_via_libreoffice] Conversion timed out (120s)")
        raise RuntimeError("LibreOffice conversion timeout")


def convert_xls_to_xlsx(xls_path: str) -> str:
    """Convert .xls to .xlsx.
    
    Tries Excel COM first (Windows+Excel), then LibreOffice (any platform).
    Returns path to converted .xlsx file.
    
    IMPORTANT: Caller is responsible for cleanup of temp directory.
    
    Raises RuntimeError if neither available.
    """
    logger.info(f"[convert_xls_to_xlsx] Converting .xls to .xlsx: {Path(xls_path).name}")
    tmp_dir = tempfile.mkdtemp(prefix="xls2xlsx_")
    logger.debug(f"[convert_xls_to_xlsx] Created temp directory: {tmp_dir}")
    out_path = os.path.join(tmp_dir, Path(xls_path).stem + ".xlsx")
    
    # Try Excel COM first
    try:
        _convert_xls_via_excel_com(xls_path, out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            logger.info(f"[convert_xls_to_xlsx] Conversion successful: {out_path}")
            return out_path
        else:
            logger.warning(f"[convert_xls_to_xlsx] Excel COM output file not created or empty: {out_path}")
    except Exception as e:
        logger.debug(f"[convert_xls_to_xlsx] Excel COM failed: {e}")
    
    # Try LibreOffice
    try:
        _convert_xls_via_libreoffice(xls_path, tmp_dir)
        cand = os.path.join(tmp_dir, Path(xls_path).stem + ".xlsx")
        if os.path.exists(cand) and os.path.getsize(cand) > 0:
            logger.info(f"[convert_xls_to_xlsx] Conversion successful: {cand}")
            return cand
        else:
            logger.warning(f"[convert_xls_to_xlsx] LibreOffice output file not created or empty: {cand}")
    except Exception as e:
        logger.debug(f"[convert_xls_to_xlsx] LibreOffice failed: {e}")
    
    # Both failed - cleanup and raise
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.debug(f"[convert_xls_to_xlsx] Cleaned up temp directory: {tmp_dir}")
    except Exception as e:
        logger.warning(f"[convert_xls_to_xlsx] Could not cleanup temp dir {tmp_dir}: {e}")
    
    error_msg = (
        "Cannot convert .xls to .xlsx.\n"
        "Options:\n"
        "  1. Install Microsoft Excel on this machine\n"
        "  2. Install LibreOffice and ensure soffice is in PATH\n"
        "  3. Manually convert .xls to .xlsx and upload .xlsx"
    )
    logger.error(f"[convert_xls_to_xlsx] {error_msg}")
    raise RuntimeError(error_msg)


def extract_spreadsheet(path: str):
    """Read .xlsx or .xls file and return structured data.
    
    Args:
        path: Path to Excel file (.xlsx or .xls)
        
    Returns:
        dict: sheet_name -> list of rows (list[list[cell_values]])
        
    Raises:
        ValueError: Unsupported file format or file is corrupted
        RuntimeError: .xls conversion failed (no Excel/LibreOffice available)
    """
    path = str(path)
    ext = Path(path).suffix.lower()
    
    if ext == ".xlsx":
        logger.debug(f"[extract_spreadsheet] Processing .xlsx file: {Path(path).name}")
        return read_xlsx(path)
    
    if ext == ".xls":
        logger.info(f"[extract_spreadsheet] Processing .xls file: {Path(path).name}")
        xlsx_path = convert_xls_to_xlsx(path)
        tmp_dir = Path(xlsx_path).parent
        
        try:
            result = read_xlsx(xlsx_path)
            logger.info(f"[extract_spreadsheet] Successfully extracted {len(result)} sheets from converted XLS")
            return result
        except Exception as e:
            logger.error(f"[extract_spreadsheet] Failed to read converted XLSX: {e}", exc_info=True)
            raise
        finally:
            # Clean up temp directory after successful or failed conversion
            try:
                shutil.rmtree(str(tmp_dir), ignore_errors=True)
                logger.debug(f"[extract_spreadsheet] Cleaned up temp directory: {tmp_dir}")
            except Exception as e:
                logger.warning(f"[extract_spreadsheet] Could not cleanup temp dir {tmp_dir}: {e}")
    
    raise ValueError(f"Unsupported file format: {ext}. Expected .xls or .xlsx")
