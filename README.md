# 🎯 Uh Bot - Intelligent Telegram Document Analysis Bot

**Version:** 1.1.0 | **License:** MIT | **Python:** 3.11+ | **Status:** ✅ Production-Ready

---

## 📋 Оглавление

1. [Описание проекта](#описание-проекта)
2. [Основные возможности](#основные-возможности)
3. [Технический стек](#технический-стек)
4. [Архитектура](#архитектура)
5. [Системные улучшения (Dec 21, 2025)](#системные-улучшения-dec-21-2025)
6. [Установка и запуск](#установка-и-запуск)
7. [Использование](#использование)
8. [Структура проекта](#структура-проекта)
9. [API документация](#api-документация)
10. [Конфигурация](#конфигурация)
11. [Разработка](#разработка)
12. [Тестирование](#тестирование)

---

## Описание проекта

**Uh Bot** — это интеллектуальный Telegram-бот, разработанный для анализа и обработки документов с использованием искусственного интеллекта. Бот предоставляет комплексное решение для работы с документами, ведения интеллектуального диалога, анализа домашних заданий и управления кастомизируемыми промптами.

**Целевая аудитория:**
- Студенты (проверка домашних заданий)
- Профессионалы (анализ документов)
- Преподаватели (проверка работ)
- Бизнес-пользователи (обработка информации)

---

## Основные возможности

### 🔍 Анализ документов
- **Базовый анализ**: Резюме, ключевые моменты, важные детали
- **Краткое резюме**: Сжатое изложение основной информации
- **Извлечение данных**: Люди, организации, даты, суммы, термины
- **Анализ рисков**: Выявление потенциальных проблем и зон внимания
- **Юридическая проверка**: Анализ договоров и юридических последствий

**Поддерживаемые форматы:**
- PDF документы
- Word документы (DOCX)
- **Старые Word документы (.doc)** ✅ NEW
- Текстовые файлы (TXT)
- Изображения (автоматическое извлечение текста через OCR)
- ZIP архивы (с поддержкой множественных файлов)
- Excel файлы (XLSX, XLS)

### 💬 Интеллектуальный диалог
- Общение на русском языке
- Объяснение сложных концепций
- Контекстное понимание
- Поддержка многошаговых диалогов

### 📚 Проверка домашних заданий
- **По 8 предметам:**
  - 🔢 Математика
  - 🔤 Русский язык
  - 🇬🇧 Английский язык
  - ⚡ Физика
  - 🧪 Химия
  - 💻 Информатика
  - 🌍 География
  - 📖 Литература

- Справедливая проверка
- Выявление ошибок
- Конструктивные предложения
- Мотивирующий тон

### ⚙️ Управление промптами
- **3 категории промптов:**
  - 📄 Документы (5 промптов)
  - 💬 Диалог (1 промпт)
  - 📖 Домашка (8 промптов)

- Редактирование системных промптов
- Кастомизация под пользователя
- Сохранение в локальную базу
- Интуитивный интерфейс управления

---

## Технический стек

### Backend
| Компонент | Версия | Назначение |
|-----------|--------|----------|
| **Python** | 3.11+ | Основной язык |
| **aiogram** | 3.0.0+ | Telegram Bot API framework |
| **Replicate** | 0.15.0+ | LLM API (Claude, Llama, etc) |
| **OpenAI** | 1.3.0+ | Chat API (alternative) |
| **aspose-words** | 23.0.0+ | ✅ NEW: .doc файлы |
| **python-docx** | 1.0.0+ | Word документы |
| **pypdf** | 4.0.0+ | PDF обработка |
| **openpyxl** | 3.0.10+ | Excel файлы |
| **Pydantic** | 2.0.0+ | Валидация данных |
| **python-dotenv** | 1.0.0+ | Управление переменными окружения |

### Infrastructure
- **Polling**: Базовое опрашивание API Telegram
- **File Processing**: Асинхронная обработка файлов (aiofiles)
- **Storage**: Локальная файловая система (./data/prompts)
- **OCR**: OCR.space API (облачный сервис)
- **Error Handling**: ✅ NEW: Smart retry system с exponential backoff

### Development Tools
- **pytest**: Unit и Integration тестирование
- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking
- **structlog**: Structured logging

---

## Архитектура

### 📁 Слоистая архитектура

```
┌─────────────────────────────────────────────┐
│        Telegram Bot Interface (aiogram)     │
├─────────────────────────────────────────────┤
│           Handlers Layer (app/handlers)     │
│  ├─ common.py (базовые команды)             │
│  ├─ documents.py (анализ документов)        │
│  ├─ conversation.py (/analyze команда)      │
│  ├─ chat.py (диалог)                        │
│  ├─ homework.py (проверка домашки)          │
│  └─ prompts.py (управление промптами)       │
├─────────────────────────────────────────────┤
│          Services Layer (app/services)      │
│  ├─ llm/ (LLM интеграция)                    │
│  │  ├─ llm_factory.py ✅ SMART RETRY         │
│  │  ├─ replicate_client.py (180s timeout)   │
│  │  └─ openai_client.py                     │
│  ├─ file_processing/ (обработка файлов)     │
│  │  ├─ converter.py (маршрутизация)         │
│  │  ├─ doc_parser.py ✅ ASPOSE.WORDS        │
│  │  ├─ docx_parser.py                       │
│  │  ├─ pdf_parser.py                        │
│  │  ├─ excel_parser.py                      │
│  │  └─ text_cleaner.py                      │
│  ├─ prompts/ (управление промптами)         │
│  │  └─ prompt_manager.py                    │
│  ├─ documents/ (анализ документов)          │
│  │  └─ document_analyzer.py                 │
│  ├─ homework/ (проверка домашки)            │
│  │  ├─ homework_checker.py                  │
│  │  └─ subject_checkers.py                  │
│  └─ parsing/ (обработка результатов)        │
│     └─ response_formatter.py                │
├─────────────────────────────────────────────┤
│        State Management (app/states)        │
│  ├─ documents.py (FSM для документов)       │
│  ├─ conversation.py (FSM для диалога)       │
│  ├─ chat.py (FSM для чата)                  │
│  ├─ homework.py (FSM для домашки)           │
│  └─ prompts.py (FSM для промптов)           │
├─────────────────────────────────────────────┤
│        Configuration Layer (app/config)     │
│  └─ settings.py (управление конфигурацией) │
├─────────────────────────────────────────────┤
│        Storage Layer (./data/prompts)       │
│  └─ JSON файлы кастомных промптов           │
└─────────────────────────────────────────────┘
```

### 🔄 Поток данных

1. **User Input** → Telegram Handler
2. **File Download** → Temp Directory
3. **Content Extraction** → PDF/DOCX/OCR Parser
4. **Prompt Selection** → PromptManager
5. **LLM Processing** → LLMFactory (Smart Retry) → Replicate/OpenAI API
6. **Response Parsing** → ResponseFormatter
7. **Output** → User (Telegram)

### 🧠 LLM Factory - Smart Retry System

```
Request to Primary (Replicate)
        ↓
    Timeout? → Retry 1 (wait 2s) → Timeout? → Retry 2 (wait 4s)
        ↓ (success)
    Return Result
        
    ↓ (all retries failed)
    Fallback to OpenAI
        ↓
    403 Region Error? → Return to Replicate (final retry)
        ↓ (success)
    Return Result
        
    ↓ (all failed)
    Raise Error to User
```

**Особенности:**
- ✅ 2 retry попытки с exponential backoff (2s, 4s)
- ✅ Автоматическое переключение между провайдерами
- ✅ Обнаружение 403 region errors (OpenAI)
- ✅ Сохранение контекста (документ + промпт)
- ✅ Бот НЕ падает при ошибках API

### 📦 File Processing Pipeline

```
User uploads file
        ↓
   FileConverter.extract_text()
        ↓
   By extension:
   ├─ .pdf  → PDFParser
   ├─ .docx → DOCXParser
   ├─ .doc  → DOCParser (Aspose.Words) ✅
   ├─ .xlsx → ExcelParser
   ├─ .xls  → ExcelParser
   ├─ .txt  → Direct read
   ├─ .zip  → ZIPHandler
   └─ .jpg  → OCRService
        ↓
   TextCleaner.clean_extracted_text()
        ↓
   Return normalized text
```

**Статус парсеров:**
- ✅ PDF: Полная поддержка
- ✅ DOCX: Полная поддержка (таблицы, форматирование)
- ✅ **DOC: Полная поддержка (Aspose.Words, русский текст, CP1251)** ✅ NEW
- ✅ XLSX: Полная поддержка
- ✅ XLS: Полная поддержка (xlrd)
- ✅ TXT: Полная поддержка
- ✅ ZIP: Полная поддержка
- ✅ Изображения: OCR (OCR.space API)

---

## Системные улучшения (Dec 21, 2025)

### 🔧 Критические исправления

#### 1️⃣ Парсинг старых .doc файлов
```python
# ✅ РЕШЕНИЕ: Aspose.Words (Python библиотека)
# Автоматическое определение кодировки (CP1251)
# 100% чистый русский текст без иероглифов
# Не требует LibreOffice/Antiword
# Работает в облаке через pip install
```

**Результат:**
- ✅ Файлы как Приложение_4_Проект_контракта_стулья_61_2025.doc обрабатываются идеально
- ✅ 46K+ символов без потерь
- ✅ Русский текст сохраняется точно

#### 2️⃣ Windows Event Loop Fix
```python
# ❌ БЫЛО: RuntimeError: Event loop is closed
# ✅ РЕШЕНИЕ: asyncio.run(main()) вместо manual loop
# Правильный graceful shutdown
```

#### 3️⃣ Timeout для больших документов
```python
# ❌ БЫЛО: 30s timeout (обрывался на 46K+ символов)
# ✅ РЕШЕНИЕ: 180s timeout (достаточно для большинства)
os.environ["REPLICATE_TIMEOUT"] = "180"
```

#### 4️⃣ Smart Retry System
```python
# ✅ Автоматические повторные попытки (2x с backoff)
# ✅ Определение ошибок (timeout, network, 403)
# ✅ Переключение провайдеров (Replicate ↔ OpenAI)
# ✅ Сохранение контекста при retry
# ✅ Бот продолжает работу при сбоях

LLMFactory.analyze_document(
    document_text=text,
    user_prompt=prompt,
    system_prompt=system
)  # Автоматически retry + fallback
```

#### 5️⃣ UI Flickering Fix
```python
# ❌ БЫЛО: Сообщение мигало при обработке
# ✅ РЕШЕНИЕ: Убрано промежуточное сообщение с preview
# Плавный переход: Обработка → Анализ → Результат
```

### 📊 Производительность

| Операция | Время | Статус |
|----------|-------|--------|
| .doc parsing | ~2s | ✅ Быстро |
| Анализ (Replicate) | 15-30s | ✅ Нормально |
| Анализ с retry | 30-45s | ✅ Приемлемо |
| API timeout | 180s max | ✅ Достаточно |
| Bot startup | <1s | ✅ Мгновенно |
| Bot shutdown | <1s | ✅ Чистый выход |

### 🔍 Протестировано

- ✅ .doc файл 238KB, 46633 символов
- ✅ Replicate timeout + OpenAI 403 + retry Replicate
- ✅ Windows Ctrl+C shutdown без errors
- ✅ UI workflow (без мигания)
- ✅ Russian text encoding (CP1251)

---

## Установка и запуск

### Требования
- Python 3.11+
- pip или uv
- Telegram Bot Token (от BotFather)
- API ключи (Replicate, OpenAI)

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/severand/TG_bot.git
cd TG_bot
```

### Шаг 2: Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
# с dev зависимостями
pip install -e ".[dev]"
```

### Шаг 4: Конфигурация

Создайте `.env` файл на основе `.env.example`:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram
TG_BOT_TOKEN=your_bot_token_from_botfather

# LLM API
REPLICATE_API_TOKEN=your_replicate_token
REPLICATE_MODEL=openai/gpt-4o-mini

# Alternative: OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o

# OCR
OCR_SPACE_API_KEY=K87899142591

# Directories
TEMP_DIR=./temp
```

### Шаг 5: Запуск

```bash
python main.py
```

---

## Использование

### Telegram команды

#### 📄 Анализ документов

```
/analyze - Начать анализ документа
```

**Процесс:**
1. `/analyze` → Выбрать тип анализа
2. Отправить документ (PDF/DOCX/DOC/изображение/текст)
3. Получить результат

**Типы анализа:**
- 📋 Базовый анализ
- 📝 Краткое резюме
- 🔍 Извлечение данных
- ⚠️ Анализ рисков
- ⚖️ Юридическая проверка

#### 💬 Диалог

```
/chat - Начать общение
```

**Процесс:**
1. `/chat` → Активирован режим диалога
2. Отправлять вопросы
3. Получать ответы

#### 📚 Проверка домашки

```
/homework - Проверить домашнее задание
```

**Процесс:**
1. `/homework` → Выбрать предмет
2. Отправить домашку (текст/фото/документ)
3. Получить проверку с ошибками и рекомендациями

#### ⚙️ Управление промптами

```
/prompts - Управлять промптами
```

**Категории:**
- 📄 Документы (5 промптов)
- 💬 Диалог (1 промпт)
- 📖 Домашка (8 промптов по предметам)

**Операции:**
- Просмотр промптов
- Редактирование системного промпта
- Редактирование шаблона
- Сохранение изменений

#### 📖 Справка

```
/help - Получить справку
/start - Запустить бота
```

---

## Структура проекта

### 📂 Основные директории

```
TG_bot/
├── app/                          # Основное приложение
│   ├── __init__.py
│   ├── bot.py                   # Инициализация бота
│   ├── config.py                # Конфигурация
│   ├── handlers/                # Обработчики команд
│   │   ├── __init__.py
│   │   ├── common.py            # /start, /help
│   │   ├── documents.py         # Анализ документов
│   │   ├── conversation.py      # /analyze команда
│   │   ├── chat.py              # /chat диалог
│   │   ├── homework.py          # /homework проверка
│   │   └── prompts.py           # /prompts управление
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── llm/                 # LLM интеграция
│   │   │   ├── llm_factory.py   # ✅ SMART RETRY
│   │   │   ├── replicate_client.py
│   │   │   └── openai_client.py
│   │   ├── file_processing/     # Обработка файлов
│   │   │   ├── converter.py
│   │   │   ├── doc_parser.py    # ✅ ASPOSE.WORDS
│   │   │   ├── docx_parser.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── excel_parser.py
│   │   │   ├── zip_handler.py
│   │   │   └── text_cleaner.py
│   │   ├── prompts/             # Управление промптами
│   │   │   └── prompt_manager.py
│   │   ├── documents/           # Анализ документов
│   │   │   └── document_analyzer.py
│   │   ├── homework/            # Проверка домашки
│   │   │   ├── homework_checker.py
│   │   │   └── subject_checkers.py
│   │   └── parsing/             # Обработка результатов
│   │       └── response_formatter.py
│   ├── states/                  # FSM состояния
│   │   ├── __init__.py
│   │   ├── documents.py
│   │   ├── conversation.py
│   │   ├── chat.py
│   │   ├── homework.py
│   │   └── prompts.py
│   └── utils/                   # Утилиты
│       ├── cleanup.py
│       ├── text_splitter.py
│       └── localization.py
├── data/                        # Пользовательские данные
│   └── prompts/                 # Кастомные промпты (JSON)
├── docs/                        # Документация
│   ├── PROGRESS_2025-12-21_FIXES.md  # ✅ NEW
│   ├── CONVERSATION_MODE.md
│   ├── PROMPT_MANAGEMENT.md
│   └── REPLICATE_INTEGRATION.md
├── examples/                    # Примеры использования
├── tests/                       # Тестирование
├── temp/                        # Временные файлы (git ignored)
├── main.py                      # Entry point
├── requirements.txt             # Зависимости
├── pyproject.toml              # Конфигурация проекта
├── README.md                   # Этот файл
└── .env.example                # Шаблон переменных окружения
```

---

## API документация

### PromptManager

Менеджер для управления промптами:

```python
from app.services.prompts.prompt_manager import PromptManager

# Инициализация
pm = PromptManager()

# Получить промпт
prompt = pm.get_prompt(user_id, "math_homework")

# Получить все промпты категории
prompts = pm.get_prompt_by_category(user_id, "homework")

# Обновить промпт
pm.update_prompt(
    user_id=123,
    prompt_name="math_homework",
    system_prompt="Новый системный текст"
)

# Загрузить из файла
pm.load_user_prompts(user_id)
```

### LLMFactory

✅ NEW: Smart retry system с автоматическим переключением провайдеров:

```python
from app.services.llm.llm_factory import LLMFactory

factory = LLMFactory(
    primary_provider="replicate",
    replicate_api_token="...",
    openai_api_key="..."
)

# Автоматический retry + fallback
result = await factory.analyze_document(
    document_text="...",
    user_prompt="Analyze this",
    system_prompt="..."
)
# На фоне: Replicate timeout? Retry 2x → OpenAI 403? → Replicate final
```

### FileConverter

```python
from app.services.file_processing.converter import FileConverter

converter = FileConverter()

# Автоматический выбор парсера
text = converter.extract_text(Path("document.doc"))  # ✅ Works!
text = converter.extract_text(Path("document.pdf"))
text = converter.extract_text(Path("document.xlsx"))
```

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательна |
|-----------|---------|----------|
| `TG_BOT_TOKEN` | Токен Telegram бота | ✅ Да |
| `REPLICATE_API_TOKEN` | API ключ Replicate | ❌ Опционально |
| `REPLICATE_MODEL` | Модель Replicate | ❌ Опционально |
| `OPENAI_API_KEY` | API ключ OpenAI | ❌ Опционально |
| `OPENAI_MODEL` | Модель OpenAI | ❌ Опционально |
| `OCR_SPACE_API_KEY` | API ключ OCR.space | ✅ Да (для OCR) |
| `TEMP_DIR` | Директория временных файлов | ❌ Опционально |
| `MAX_FILE_SIZE` | Максимальный размер файла (bytes) | ❌ Опционально |

### Выбор LLM провайдера

**Replicate (по умолчанию, рекомендуется):**
- Подходит для: Llama, Claude, Mistral, GPT-4o-mini
- Преимущества: Дешево, мощно, быстро
- Timeout: 180s (настроено)

**OpenAI:**
- Подходит для: GPT-4, GPT-4o, GPT-3.5
- Преимущества: Стабильно, качественно
- Осторожно: Региональные ограничения (403)

### Retry конфигурация

```python
# app/services/llm/llm_factory.py
MAX_RETRIES = 2              # Попытки перед fallback
RETRY_DELAY_BASE = 2         # Base delay в секундах (exponential)

# Результат: 2s, 4s delays между попытками
```

---

## Разработка

### Установка dev-окружения

```bash
pip install -e ".[dev]"
```

### Code Style

**Форматирование (Black):**
```bash
black app tests main.py
```

**Linting (Ruff):**
```bash
ruff check app tests main.py
```

**Type checking (mypy):**
```bash
mypy app
```

### Добавление нового handler

1. Создать файл в `app/handlers/`
2. Определить Router:
```python
from aiogram import Router
router = Router()

@router.message(Command("mycommand"))
async def handle_mycommand(message: Message):
    pass
```

3. Зарегистрировать в `main.py`:
```python
from app.handlers import myhandler
dispatcher.include_router(myhandler.router)
```

---

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Специфичный тест
pytest tests/test_documents.py::test_analyze

# С логами
pytest -v -s
```

---

## 🚀 Развертывание

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  bot:
    build: .
    environment:
      - TG_BOT_TOKEN=${TG_BOT_TOKEN}
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
    volumes:
      - ./data:/app/data
      - ./temp:/app/temp
```

---

## 📝 Лицензия

MIT License - см. LICENSE

---

## 👥 Контрибьютинг

Приветствуются Pull Request'ы! Пожалуйста:

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

---

## 📞 Поддержка

Если у вас есть вопросы:

1. Проверьте [Issues](https://github.com/severand/TG_bot/issues)
2. Проверьте [Документацию](/docs)
3. Создайте новый Issue

---

## 📚 Дополнительные ресурсы

- [aiogram документация](https://docs.aiogram.dev/)
- [Replicate API](https://replicate.com/)
- [OpenAI API](https://platform.openai.com/)
- [Telegram Bot API](https://core.telegram.org/bots)
- [Progress Report Dec 21](/docs/PROGRESS_2025-12-21_FIXES.md) ✅ NEW

---

**Спасибо за использование Uh Bot! 🎉**

**Версия 1.1.0 с критическими исправлениями и улучшениями (Dec 21, 2025)**
