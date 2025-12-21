"""Logging configuration for RAG module.

Настройка структурированного логирования для RAG модуля.
Поддерживает различные уровни логирования, форматы и вывод в файл/консоль.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Цветной форматтер для консольного вывода."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str = "rag_module",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
    colored: bool = True,
) -> logging.Logger:
    """Настроить логгер для RAG модуля.
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов (опционально)
        console: Выводить ли в консоль
        colored: Использовать ли цвета в консоли
        
    Returns:
        logging.Logger: Настроенный логгер
        
    Example:
        >>> logger = setup_logger("rag_module", level="DEBUG")
        >>> logger.info("Система запущена")
    """
    logger = logging.getLogger(name)
    
    # Убираем старые handlers
    logger.handlers.clear()
    
    # Устанавливаем уровень
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Формат логов
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        if colored and sys.stdout.isatty():
            formatter = ColoredFormatter(log_format, datefmt=date_format)
        else:
            formatter = logging.Formatter(log_format, datefmt=date_format)
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        
        # Для файла не используем цвета
        formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Предотвращаем распространение логов на root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Получить логгер по имени.
    
    Args:
        name: Имя логгера (по умолчанию "rag_module")
        
    Returns:
        logging.Logger: Логгер
        
    Example:
        >>> logger = get_logger("rag_module.services")
        >>> logger.debug("Отладочное сообщение")
    """
    if name is None:
        name = "rag_module"
    return logging.getLogger(name)


def configure_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    console: bool = True,
) -> None:
    """Настроить логирование для всего RAG модуля.
    
    Создаёт логгеры для всех компонентов.
    
    Args:
        level: Уровень логирования
        log_dir: Директория для логов
        console: Выводить ли в консоль
    """
    # Главный логгер
    log_file = None
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"rag_{timestamp}.log"
    
    # Настройка главного логгера
    setup_logger(
        name="rag_module",
        level=level,
        log_file=log_file,
        console=console,
    )
    
    # Настройка логгеров для компонентов
    components = [
        "rag_module.file_processing",
        "rag_module.services",
        "rag_module.utils",
    ]
    
    for component in components:
        logger = logging.getLogger(component)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))


class LoggerContext:
    """Контекстный менеджер для временного изменения уровня логирования."""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper(), logging.INFO)
        self.old_level = logger.level
    
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


def with_log_level(logger: logging.Logger, level: str) -> LoggerContext:
    """Временно изменить уровень логирования.
    
    Args:
        logger: Логгер
        level: Новый уровень
        
    Returns:
        LoggerContext: Контекстный менеджер
        
    Example:
        >>> logger = get_logger()
        >>> with with_log_level(logger, "DEBUG"):
        ...     logger.debug("Это покажется")
    """
    return LoggerContext(logger, level)
