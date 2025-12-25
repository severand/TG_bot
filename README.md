# 🎯 Uh Bot - Intelligent Telegram Document Analysis Bot

**Version:** 1.1.0 | **License:** MIT | **Python:** 3.11+

---

## 📋 Оглавление

1. [Описание проекта](#описание-проекта)
2. [Основные возможности](#основные-возможности)
3. [Технический стек](#технический-стек)
4. [Архитектура](#архитектура)
5. [Установка и запуск](#установка-и-запуск)
6. [Использование](#использование)
7. [Структура проекта](#структура-проекта)
8. [API документация](#api-документация)
9. [Конфигурация](#конфигурация)
10. [Разработка](#разработка)
11. [Тестирование](#тестирование)

---

## Описание проекта

**Uh Bot** — это интеллектуальный Telegram-бот, разработанный для анализа и обработки документов с использованием искусственного интеллекта. Бот предоставляет комплексное решение для работы с документами, ведения интеллектуального диалога, анализа домашних заданий, управления кастомизируемыми промптами и **умную базу знаний с технологией RAG (Retrieval-Augmented Generation)**.

**Целевая аудитория:**
- Студенты (проверка домашних заданий, учебная база знаний)
- Профессионалы (анализ документов, база знаний компании)
- Преподаватели (проверка работ)
- Бизнес-пользователи (обработка информации, контракты, регламенты)

---

## Основные возможности

### 🧠 RAG База Знаний (NEW! 🆕)
- **Semantic Search**: Умный поиск по смыслу, а не по ключевым словам
- **Множественные документы**: Загрузи один раз - ищи много раз
- **In-memory storage**: Работает без ChromaDB (71% функционал реализован)
- **Работает на Windows**: Нет зависимостей от ChromaDB
- **384D embeddings**: Sentence-transformers для векторизации
- **Cosine similarity**: Точный поиск релевантных фрагментов

**Идеально для:**
- 📚 База знаний компании (регламенты, инструкции, FAQ)
- 📋 Проектная документация (ТЗ, требования, спецификации)
- ⚖️ Юридические документы (множественные контракты)
- 🎓 Учебные материалы (учебники, конспекты, лекции)
- 💼 HR документы (резюме, политики)

**Поддерживаемые форматы:**
- PDF, DOCX, DOC, TXT
- Excel (XLSX, XLS)
- ZIP архивы с документами

### 🔍 Анализ документов
- **Базовый анализ**: Резюме, ключевые моменты, важные детали
- **Краткое резюме**: Сжатое изложение основной информации
- **Извлечение данных**: Люди, организации, даты, суммы, термины
- **Анализ рисков**: Выявление потенциальных проблем и зон внимания
- **Юридическая проверка**: Анализ договоров и юридических последствий

**Поддерживаемые форматы:**
- PDF документы
- Word документы (DOCX)
- Текстовые файлы (TXT)
- Изображения (автоматическое извлечение текста через OCR)

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

## 🆚 Сравнение команд: /analyze vs /homework vs /rag

| Критерий | `/analyze` | `/homework` | `/rag` 🆕 |
|---------|-----------|------------|-----------|
| **Назначение** | Разовый анализ | Проверка домашки | База знаний |
| **Документов** | 1 за раз | 1 за раз | Много сразу |
| **Анализ** | ИИ анализ всего документа | ИИ проверка с оценкой | Semantic search по фрагментам |
| **Результат** | Полный разбор | Оценка + ошибки | Релевантные фрагменты |
| **Сохранение** | ❌ Не сохраняется | ❌ Не сохраняется | ✅ Сохраняется в базе |
| **Повторный доступ** | ❌ Загружай заново | ❌ Загружай заново | ✅ Всегда доступно |
| **Выбор промпта** | ✅ Да (5 типов анализа) | ✅ Да (8 предметов) | ❌ Нет, автоматический поиск |
| **Скорость** | Медленно (полный анализ) | Медленно (полная проверка) | Быстро (поиск по индексу) |

### 🎯 Простое правило выбора:

```
1 документ + 1 вопрос = /analyze
1 домашка + проверка = /homework
Много документов + много вопросов = /rag 🆕
```

📖 **Подробное руководство:** [User Guide RAG](docs/USER_GUIDE_RAG.md)

---

## Технический стек

### Backend
| Компонент | Версия | Назначение |
|-----------|--------|----------|
| **Python** | 3.11+ | Основной язык |
| **aiogram** | 3.0.0+ | Telegram Bot API framework |
| **Replicate** | 0.15.0+ | LLM API (Claude, Llama, etc) |
| **OpenAI** | 1.3.0+ | Chat API (alternative) |
| **python-docx** | 1.0.0+ | Word документы |
| **pypdf** | 4.0.0+ | PDF обработка |
| **Pydantic** | 2.0.0+ | Валидация данных |
| **python-dotenv** | 1.0.0+ | Управление переменными окружения |

### RAG Components 🆕
| Компонент | Версия | Назначение |
|-----------|--------|----------|
| **sentence-transformers** | 2.2.0+ | Embeddings generation (384D vectors) |
| **numpy** | 1.24.0+ | Cosine similarity calculations |
| **In-memory storage** | - | Document chunks storage (no DB needed) |
| **openpyxl** | 3.1.0+ | Excel files processing |

### Infrastructure
- **Polling**: Базовое опрашивание API Telegram
- **File Processing**: Асинхронная обработка файлов (aiofiles)
- **Storage**: 
  - Локальная файловая система (./data/prompts)
  - In-memory RAG storage (no ChromaDB) 🆕
- **OCR**: OCR.space API (облачный сервис)

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
│  ├─ prompts.py (управление промптами)       │
│  └─ rag.py (RAG база знаний) 🆕             │
├─────────────────────────────────────────────┤
│          Services Layer (app/services)      │
│  ├─ llm/ (LLM интеграция)                    │
│  │  ├─ replicate_client.py                  │
│  │  └─ openai_client.py                     │
│  ├─ file_processing/ (обработка файлов)     │
│  │  ├─ ocr_service.py                       │
│  │  ├─ pdf_parser.py                        │
│  │  └─ docx_parser.py                       │
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
│         RAG Module (rag_knowledge_base) 🆕  │
│  ├─ file_processing.py (text extraction)   │
│  └─ services.py (Chunker, EmbeddingService) │
├─────────────────────────────────────────────┤
│        State Management (app/states)        │
│  ├─ documents.py (FSM для документов)       │
│  ├─ conversation.py (FSM для диалога)       │
│  ├─ chat.py (FSM для чата)                  │
│  ├─ homework.py (FSM для домашки)           │
│  ├─ prompts.py (FSM для промптов)           │
│  └─ rag.py (FSM для RAG) 🆕                 │
├─────────────────────────────────────────────┤
│        Configuration Layer (app/config)     │
│  └─ settings.py (управление конфигурацией) │
├─────────────────────────────────────────────┤
│        Storage Layer (./data/prompts)       │
│  └─ JSON файлы кастомных промптов           │
└─────────────────────────────────────────────┘
```

### 🔄 Поток данных

#### Традиционный анализ (/analyze, /homework)
1. **User Input** → Telegram Handler
2. **File Download** → Temp Directory
3. **Content Extraction** → PDF/DOCX/OCR Parser
4. **Prompt Selection** → PromptManager
5. **LLM Processing** → Replicate/OpenAI API
6. **Response Parsing** → ResponseFormatter
7. **Output** → User (Telegram)

#### RAG Knowledge Base (/rag) 🆕
1. **User Upload Documents** → Telegram Handler
2. **File Download** → Temp Directory
3. **Text Extraction** → PDF/DOCX/Excel Parser
4. **Chunking** → Chunker (512 tokens, 50 overlap)
5. **Vectorization** → EmbeddingService (384D vectors)
6. **Storage** → In-memory dict {doc_id: chunks}
7. **User Query** → Query Vectorization
8. **Similarity Search** → Cosine similarity calculation
9. **Top-K Results** → Relevant fragments
10. **Output** → User (Telegram)

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
pip install -e .
# или с dev зависимостями
pip install -e ".[dev]"

# Для RAG модуля 🆕
pip install -r rag_knowledge_base/requirements.txt
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
REPLICATE_MODEL=meta/llama-2-70b-chat:2796ee1dca3f3236cbba7651544d4c40fed8150cf29fc2e9318c7bfa5f28d605

# Alternative: OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4-turbo-preview

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

#### 🧠 RAG База Знаний 🆕

```
/rag - Умная база знаний с semantic search
```

**Процесс:**
1. `/rag` → Главное меню
2. 📤 **Загрузить** документы (PDF, DOCX, TXT, Excel, ZIP)
3. 🔍 **Поиск** - задавать вопросы на естественном языке
4. Получать релевантные фрагменты из **ВСЕХ** документов сразу

**Кнопки:**
- 📤 Загрузить - добавить документ в базу
- 🔍 Поиск - найти информацию
- 📊 Статистика - посмотреть что в базе
- 🗑️ Очистить - удалить все документы
- « Назад - выход из RAG режима

**Отличие от /analyze:**
- `/analyze` = 1 документ → полный анализ ИИ
- `/rag` = много документов → быстрый поиск по фрагментам

**Примеры использования:**
- Юридический отдел: 20 договоров → найти условия штрафов
- HR: 50 резюме → кандидаты с опытом Python
- Студент: учебник + конспекты → закон Ома
- Менеджер: ТЗ + требования + спеки → сроки API

📖 **Подробное руководство:** [User Guide RAG](docs/USER_GUIDE_RAG.md)

#### 📄 Анализ документов

```
/analyze - Начать анализ документа
```

**Процесс:**
1. `/analyze` → Выбрать тип анализа
2. Отправить документ (PDF/DOCX/изображение/текст)
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
│   │   ├── prompts.py           # /prompts управление
│   │   └── rag.py               # /rag база знаний 🆕
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── llm/                 # LLM интеграция
│   │   │   ├── replicate_client.py
│   │   │   └── openai_client.py
│   │   ├── file_processing/     # Обработка файлов
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   └── ocr_service.py
│   │   ├── prompts/             # Управление промптами
│   │   │   └── prompt_manager.py
│   │   ├── documents/           # Анализ документов
│   │   │   └── document_analyzer.py
│   │   ├── homework/            # Проверка домашки
│   │   │   ├── homework_checker.py
│   │   │   └── subject_checkers.py
│   │   └── parsing/             # Обработка результатов
│   │       └── response_formatter.py
│   └── states/                  # FSM состояния
│       ├── __init__.py
│       ├── documents.py
│       ├── conversation.py
│       ├── chat.py
│       ├── homework.py
│       ├── prompts.py
│       └── rag.py               # RAG FSM states 🆕
├── rag_knowledge_base/          # RAG module 🆕
│   ├── rag_module/
│   │   ├── __init__.py
│   │   ├── file_processing.py  # Document text extraction
│   │   └── services.py         # Chunker, EmbeddingService
│   └── requirements.txt        # RAG dependencies
├── data/                        # Пользовательские данные
│   └── prompts/                 # Кастомные промпты (JSON)
├── docs/                        # Документация
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── USER_GUIDE_RAG.md       # RAG User Guide 🆕
├── examples/                    # Примеры использования
│   ├── prompt_examples.md
│   └── usage_scenarios.md
├── tests/                       # Тестирование
│   ├── test_documents.py
│   ├── test_homework.py
│   ├── test_prompts.py
│   └── conftest.py
├── temp/                        # Временные файлы
├── main.py                      # Entry point
├── requirements.txt             # Зависимости
├── pyproject.toml              # Конфигурация проекта
├── README.md                   # Этот файл
└── .env.example                # Шаблон переменных окружения
```

---

## API документация

### RAG Knowledge Base 🆕

```python
from rag_knowledge_base.rag_module.services import (
    Chunker, 
    EmbeddingService
)
from rag_knowledge_base.rag_module.file_processing import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
    extract_text_from_excel
)

# Извлечение текста
text = extract_text_from_pdf("document.pdf")

# Chunking
chunker = Chunker(chunk_size=512, overlap=50)
chunks = chunker.chunk_text(text, doc_id="doc1", filename="document.pdf")

# Embeddings
embedding_service = EmbeddingService()
for chunk in chunks:
    chunk.embedding = embedding_service.get_embedding(chunk.text)

# Поиск
query_embedding = embedding_service.get_embedding("ваш вопрос")
results = embedding_service.search(
    query_embedding=query_embedding,
    chunks=chunks,
    top_k=3
)
```

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

### DocumentAnalyzer

Анализ документов:

```python
from app.services.documents.document_analyzer import DocumentAnalyzer

analyzer = DocumentAnalyzer(llm_client)
result = await analyzer.analyze(
    content="Текст документа",
    analysis_type="risk_analysis",
    system_prompt="..."
)
```

### HomeworkChecker

Проверка домашки:

```python
from app.services.homework.homework_checker import HomeworkChecker

checker = HomeworkChecker(llm_client)
result = await checker.check_homework(
    content="Решение задачи",
    subject="math",
    system_prompt="..."
)
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

### Выбор LLM провайдера

**Replicate (по умолчанию):**
- Подходит для: Llama, Claude, Mistral
- Преимущества: Дешево, мощно, быстро

**OpenAI:**
- Подходит для: GPT-4, GPT-3.5
- Преимущества: Стабильно, качественно

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

### Добавление новой FSM

1. Создать в `app/states/`:
```python
from aiogram.fsm.state import State, StatesGroup

class MyStates(StatesGroup):
    waiting_for_input = State()
    processing = State()
```

2. Использовать в handler:
```python
await state.set_state(MyStates.waiting_for_input)
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

### Структура тестов

```bash
tests/
├── test_documents.py      # Тесты анализа документов
├── test_homework.py       # Тесты проверки домашки
├── test_prompts.py        # Тесты управления промптами
├── conftest.py           # Fixtures и конфигурация
└── fixtures/             # Тестовые данные
    ├── documents/
    └── prompts/
```

### Пример теста

```python
import pytest
from app.services.prompts.prompt_manager import PromptManager

@pytest.mark.asyncio
async def test_get_prompt():
    pm = PromptManager()
    prompt = pm.get_prompt(123, "default")
    assert prompt is not None
    assert prompt.name == "default"
```

---

## 🚀 Развертывание

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY rag_knowledge_base/requirements.txt ./rag_requirements.txt
RUN pip install -r rag_requirements.txt
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

### Systemd Service (Linux)

```ini
[Unit]
Description=Uh Bot Telegram Service
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/uh-bot
ExecStart=/opt/uh-bot/venv/bin/python main.py
Restart=always
EnvironmentFile=/opt/uh-bot/.env

[Install]
WantedBy=multi-user.target
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
2. Создайте новый Issue
3. Свяжитесь: team@example.com

---

## 📚 Дополнительные ресурсы

- [aiogram документация](https://docs.aiogram.dev/)
- [Replicate API](https://replicate.com/)
- [OpenAI API](https://platform.openai.com/)
- [Telegram Bot API](https://core.telegram.org/bots)
- [RAG User Guide](docs/USER_GUIDE_RAG.md) 🆕
- [Sentence Transformers](https://www.sbert.net/)

---

**Спасибо за использование Uh Bot! 🎉**
