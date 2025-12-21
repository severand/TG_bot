"""Output formatting utilities for RAG module.

Форматирование выходных данных для удобного представления
результатов пользователям. Поддержка Markdown, plain text, JSON.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from rag_module.models import Document, SearchResult


def format_search_results(
    results: List[SearchResult],
    format: str = "markdown",
    max_text_length: int = 500,
    show_metadata: bool = True,
) -> str:
    """Форматировать результаты поиска.
    
    Args:
        results: Список результатов поиска
        format: Формат вывода (markdown, plain, json)
        max_text_length: Максимальная длина текста
        show_metadata: Показывать ли метаданные
        
    Returns:
        str: Форматированные результаты
    """
    if not results:
        return "🔍 Ничего не найдено"
    
    if format == "json":
        return _format_json(results)
    elif format == "plain":
        return _format_plain(results, max_text_length, show_metadata)
    else:  # markdown
        return _format_markdown(results, max_text_length, show_metadata)


def _format_markdown(
    results: List[SearchResult],
    max_text_length: int,
    show_metadata: bool,
) -> str:
    """Форматировать результаты в Markdown."""
    lines = []
    lines.append(f"# 🔍 Найдено результатов: {len(results)}\n")
    
    for idx, result in enumerate(results, 1):
        score_percent = int(result.similarity_score * 100)
        score_bar = "⭐" * (score_percent // 20)  # 5 stars max
        
        lines.append(f"## {idx}. 📄 {result.source_doc}")
        lines.append(f"**Схожесть:** {score_percent}% {score_bar}\n")
        
        # Текст
        text = result.chunk.text
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        lines.append(f"> {text}\n")
        
        # Метаданные
        if show_metadata and result.chunk.metadata:
            lines.append("**Метаданные:**")
            for key, value in result.chunk.metadata.items():
                if key not in ["doc_id", "position"]:
                    lines.append(f"  - {key}: {value}")
            lines.append("")
        
        lines.append("---\n")
    
    return "\n".join(lines)


def _format_plain(
    results: List[SearchResult],
    max_text_length: int,
    show_metadata: bool,
) -> str:
    """Форматировать результаты в plain text."""
    lines = []
    lines.append(f"🔍 Найдено: {len(results)} результатов\n")
    
    for idx, result in enumerate(results, 1):
        score_percent = int(result.similarity_score * 100)
        
        lines.append(f"[{idx}] {result.source_doc} ({score_percent}%)")
        
        text = result.chunk.text
        if len(text) > max_text_length:
            text = text[:max_text_length] + "..."
        lines.append(text)
        
        if show_metadata and result.chunk.metadata:
            meta_str = ", ".join(
                f"{k}={v}" for k, v in result.chunk.metadata.items()
                if k not in ["doc_id", "position"]
            )
            if meta_str:
                lines.append(f"  ({meta_str})")
        
        lines.append("")
    
    return "\n".join(lines)


def _format_json(results: List[SearchResult]) -> str:
    """Форматировать результаты в JSON."""
    data = []
    for result in results:
        data.append({
            "source": result.source_doc,
            "similarity": round(result.similarity_score, 4),
            "text": result.chunk.text,
            "metadata": result.chunk.metadata,
        })
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_document_info(
    document: Document,
    format: str = "markdown",
) -> str:
    """Форматировать информацию о документе.
    
    Args:
        document: Документ
        format: Формат вывода
        
    Returns:
        str: Форматированная информация
    """
    if format == "json":
        return json.dumps({
            "id": document.id,
            "filename": document.filename,
            "file_size": document.file_size,
            "chunk_count": document.chunk_count,
            "created_at": document.created_at,
            "metadata": document.metadata,
        }, ensure_ascii=False, indent=2)
    
    elif format == "plain":
        size_mb = document.file_size / 1024 / 1024
        return (
            f"📄 {document.filename}\n"
            f"ID: {document.id}\n"
            f"Размер: {size_mb:.2f} MB\n"
            f"Чанков: {document.chunk_count}\n"
            f"Загружен: {document.created_at}"
        )
    
    else:  # markdown
        size_mb = document.file_size / 1024 / 1024
        lines = [
            f"## 📄 {document.filename}",
            "",
            f"- **ID:** `{document.id}`",
            f"- **Размер:** {size_mb:.2f} MB",
            f"- **Чанков:** {document.chunk_count}",
            f"- **Загружен:** {document.created_at}",
        ]
        
        if document.metadata:
            lines.append("\n**Метаданные:**")
            for key, value in document.metadata.items():
                lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines)


def format_stats(
    stats: Dict[str, Any],
    format: str = "markdown",
) -> str:
    """Форматировать статистику RAG системы.
    
    Args:
        stats: Словарь со статистикой
        format: Формат вывода
        
    Returns:
        str: Форматированная статистика
    """
    if format == "json":
        return json.dumps(stats, ensure_ascii=False, indent=2)
    
    elif format == "plain":
        lines = [
            "📊 Статистика RAG:",
            f"Документов: {stats.get('total_documents', 0)}",
            f"Чанков: {stats.get('total_chunks', 0)}",
            f"Embedding dimension: {stats.get('embedding_dimension', 0)}",
            f"Similarity threshold: {stats.get('similarity_threshold', 0)}",
        ]
        return "\n".join(lines)
    
    else:  # markdown
        lines = [
            "# 📊 Статистика RAG Системы",
            "",
            f"- **Документов:** {stats.get('total_documents', 0)}",
            f"- **Чанков:** {stats.get('total_chunks', 0)}",
            f"- **Embedding Dimension:** {stats.get('embedding_dimension', 0)}",
            f"- **Similarity Threshold:** {stats.get('similarity_threshold', 0)}",
        ]
        
        documents = stats.get('documents', [])
        if documents:
            lines.append("\n## 📂 Документы\n")
            for doc in documents:
                size_mb = doc['size'] / 1024 / 1024
                lines.append(
                    f"- **{doc['filename']}** "
                    f"({size_mb:.2f}MB, {doc['chunks']} chunks)"
                )
        
        return "\n".join(lines)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Усечь текст до максимальной длины.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс (обычно "...")
        
    Returns:
        str: Усечённый текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Форматировать размер файла.
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        str: Человекопонятный размер
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
