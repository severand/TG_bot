# 🔧 Технология работы с промтами и обработкой документов

**Версия:** 1.0  
**Дата создания:** 2025-12-20  
**Автор:** Uh Bot Team  
**Статус:** Production Ready  

---

## 📋 Оглавление

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Система промтов (Prompt Management System)](#система-промтов)
3. [Обработка документов (Document Processing Pipeline)](#обработка-документов)
4. [Жизненный цикл запроса](#жизненный-цикл-запроса)
5. [Интеграция с LLM](#интеграция-с-llm)
6. [Примеры реализации](#примеры-реализации)
7. [Best Practices](#best-practices)
8. [Поиск и устранение неисправностей](#поиск-и-устранение-неисправностей)

---

## Обзор архитектуры

### 🎯 Ключевые компоненты

```
┌─────────────────────────────────────────────────────────────────┐
│                      Telegram User Interface                     │
│  /analyze | /chat | /homework | /prompts                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Handlers Layer (FSM)                          │
│  • conversation.py     → Document analysis                      │
│  • chat.py             → Dialog mode                            │
│  • homework.py         → Homework checking                      │
│  • prompts.py          → Prompt management                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│  PromptMgr  │ │ FileConverter│ │  LLMFactory  │
│             │ │              │ │              │
│ • Load      │ │ • Extract    │ │ • Replicate  │
│ • Get       │ │ • Parse      │ │ • OpenAI     │
│ • Update    │ │ • OCR        │ │ • Factory    │
│ • Category  │ │ • Validate   │ │ • Stream     │
└──────┬──────┘ └──────┬───────┘ └──────┬───────┘
       │               │                │
       ▼               ▼                ▼
  ./data/prompts/  ./temp/files/    LLM APIs
```

---

## Система промтов

### 📁 Структура хранилища промтов

```
data/prompts/
├── document_analysis/
│   ├── default.json
│   ├── basic_analysis.json
│   ├── summary.json
│   ├── data_extraction.json
│   ├── risk_analysis.json
│   └── legal_review.json
├── homework/
│   ├── math_homework.json
│   ├── russian_homework.json
│   ├── english_homework.json
│   ├── physics_homework.json
│   ├── chemistry_homework.json
│   ├── it_homework.json
│   ├── geography_homework.json
│   └── literature_homework.json
└── chat/
    └── chat_system.json
```

### 🏗️ Структура промпта (JSON)

```json
{
  "name": "math_homework",
  "description": "📐 Проверка математики",
  "category": "homework",
  "system_prompt": "Ты опытный учитель математики...",
  "user_prompt_template": "Проверь это решение...",
  "examples": [
    {
      "input": "x + 5 = 10",
      "expected_output": "x = 5"
    }
  ],
  "version": "1.0.0",
  "created_at": "2025-12-20T19:15:00Z",
  "updated_at": "2025-12-20T19:15:00Z",
  "tags": ["education", "math", "homework"]
}
```

### 🔌 PromptManager API

#### Инициализация
```python
from app.services.prompts.prompt_manager import PromptManager

pm = PromptManager()
```

#### Основные методы

**1. Загрузить промпты пользователя**
```python
# Загружает дефолтные + пользовательские промпты
pm.load_user_prompts(user_id=123)
```

**2. Получить один промпт**
```python
prompt = pm.get_prompt(user_id=123, prompt_name="math_homework")
if prompt:
    system_prompt = prompt.system_prompt
    user_template = prompt.user_prompt_template
```

**3. Получить все промпты категории**
```python
# КРИТИЧНО для фильтрации по типам!
prompts_dict = pm.get_prompt_by_category(user_id=123, category="document_analysis")
# Возвращает: {"basic_analysis": Prompt(...), "summary": Prompt(...)}
```

**4. Получить все промпты пользователя**
```python
all_prompts = pm.list_prompts(user_id=123)
# Возвращает ВСЕ промпты (документы + домашка + чат)
```

**5. Обновить промпт**
```python
pm.update_prompt(
    user_id=123,
    prompt_name="math_homework",
    system_prompt="Новый системный промпт",
    user_prompt_template="Новый шаблон"
)
```

#### Категории промтов

| Категория | Назначение | Количество |
|-----------|-----------|----------|
| `document_analysis` | Анализ документов | 5+ |
| `homework` | Проверка домашки | 8 (по предметам) |
| `chat` | Диалог | 1 |

### ⚡ Критичные моменты

1. **ВСЕГДА используй `get_prompt_by_category()` для фильтрации!**
   ```python
   # ✅ ПРАВИЛЬНО - фильтрует по категории
   prompts = pm.get_prompt_by_category(user_id, "document_analysis")
   
   # ❌ НЕПРАВИЛЬНО - вернёт ВСЕ промпты
   prompts = pm.list_prompts(user_id)
   ```

2. **Загружай промпты пользователя перед использованием**
   ```python
   # ✅ Правильный порядок
   pm.load_user_prompts(user_id)  # 1. Загруз
   prompt = pm.get_prompt(user_id, name)  # 2. Получи
   ```

3. **Кэширование промтов**
   - Промпты кэшируются в памяти после первой загрузки
   - Для обновления используй `update_prompt()` или перезагрузись

---

## Обработка документов

### 📥 Pipeline обработки

```
1. USER UPLOADS FILE
   ↓
2. FILE VALIDATION
   • Check size (MAX_FILE_SIZE)
   • Check MIME type
   • Check format support
   ↓
3. TEMPORARY STORAGE
   • Create temp directory
   • Download from Telegram
   • Store as: ./temp/{user_id}/{uuid}.{ext}
   ↓
4. CONTENT EXTRACTION
   • PDF      → pypdf
   • DOCX     → python-docx
   • TXT      → raw read
   • IMAGE    → OCR.space API
   • ZIP      → iterate & extract
   ↓
5. TEXT VALIDATION
   • Check if text extracted
   • Validate length > 0
   • Trim whitespace
   ↓
6. LLM PROCESSING
   • Select prompt by category
   • Build message context
   • Call LLM API
   ↓
7. RESPONSE FORMATTING
   • Split long responses (4000 chars max)
   • Format as Markdown
   • Handle multipart messages
   ↓
8. OUTPUT & CLEANUP
   • Send results to user
   • Delete temp files
   • Clear FSM state
```

### 🔄 FileConverter

```python
from app.services.file_processing.converter import FileConverter

converter = FileConverter()
text = converter.extract_text(file_path, temp_dir)
```

**Поддерживаемые форматы:**

| Формат | Инструмент | Примечания |
|--------|-----------|----------|
| PDF | pypdf | Поддержка многостраничных |
| DOCX | python-docx | Word 2007+ |
| TXT | built-in | UTF-8 encoding |
| JPG/PNG | OCR.space | Облачный OCR |
| ZIP | zipfile | Рекурсивная обработка |

### 🌐 OCR (Optical Character Recognition)

**Провайдер:** OCR.space  
**API Key:** `OCR_SPACE_API_KEY` (в .env)  
**Лимит:** 25,000 запросов/месяц (бесплатно)  

```python
# Автоматически используется для изображений
text = await _extract_text_from_photo_for_analysis(
    message=message,
    temp_dir=Path("./temp/user_123")
)
```

**Параметры OCR:**
- `language`: "rus" (русский)
- `OCREngine`: 2 (лучшая точность)
- `detectOrientation`: True
- `scale`: True
- `timeout`: 60 сек

### 🗑️ Cleanup Management

```python
from app.utils.cleanup import CleanupManager

# Создать временную директорию
temp_dir = CleanupManager.create_temp_directory(
    Path("./temp"),
    user_id=123
)

# Очистить после обработки
await CleanupManager.cleanup_directory_async(temp_dir)
```

---

## Жизненный цикл запроса

### Сценарий 1: Анализ документа (/analyze)

```mermaid
graph TD
    A[/analyze] --> B[Clear state]
    B --> C[Set ConversationStates.selecting_prompt]
    C --> D[Show prompt selection keyboard]
    D --> E[User clicks prompt]
    E --> F[Save prompt_name to state]
    F --> G[Set ConversationStates.ready]
    G --> H[Ask for document]
    H --> I[User uploads file]
    I --> J[Validate & extract text]
    J --> K[Load user prompts]
    K --> L[Get selected prompt]
    L --> M[Call LLM with<br/>document_text +<br/>system_prompt]
    M --> N[Format & send results]
    N --> O[Delete temp files]
    O --> P[Clear state]
```

### Сценарий 2: Проверка домашки (/homework)

```mermaid
graph TD
    A[/homework] --> B[Clear state]
    B --> C[Set HomeworkStates.selecting_subject]
    C --> D[Show subjects keyboard]
    D --> E[User clicks subject]
    E --> F[Save subject to state]
    F --> G[Set HomeworkStates.waiting_for_file]
    G --> H[Ask for homework]
    H --> I[User uploads file/text]
    I --> J[Check state == waiting_for_file]
    J --> |Valid| K[Extract content]
    J --> |Invalid| L[Ignore message]
    K --> M[Get subject-specific prompt<br/>e.g., math_homework]
    M --> N[Call LLM with<br/>homework_content +<br/>subject_prompt]
    N --> O[Format & send results]
    O --> P[Delete temp files]
    P --> Q[Clear state]
```

### Сценарий 3: Диалог (/chat)

```mermaid
graph TD
    A[/chat] --> B[Clear state]
    B --> C[Set ChatStates.chatting]
    C --> D[User sends message]
    D --> E[Check state == ChatStates.chatting]
    E --> |Valid| F[Load user prompts]
    E --> |Invalid| G[Ignore message]
    F --> H[Get chat_system prompt]
    H --> I[Call LLM with<br/>user_message +<br/>system_prompt]
    I --> J[Format & send response]
    J --> K{Message length}
    K --> |Single| L[Send 1 message]
    K --> |Multiple| M[Split & send chunks]
```

---

## Интеграция с LLM

### 🤖 LLMFactory

```python
from app.services.llm.llm_factory import LLMFactory
from app.config import get_settings

config = get_settings()

llm_factory = LLMFactory(
    primary_provider=config.LLM_PROVIDER,  # "replicate" или "openai"
    replicate_api_token=config.REPLICATE_API_TOKEN,
    replicate_model=config.REPLICATE_MODEL,
    openai_api_key=config.OPENAI_API_KEY,
    openai_model=config.OPENAI_MODEL,
)
```

### 📞 Методы LLM

**1. Анализ документов**
```python
result = await llm_factory.analyze_document(
    document_text="...",
    analysis_command="Проанализируй...",
    system_prompt="Ты эксперт...",
    use_streaming=False,
)
```

**2. Диалог/чат**
```python
response = await llm_factory.chat(
    user_message="Что такое Python?",
    system_prompt="Помощник для объяснения...",
    use_streaming=False,
)
```

### 🔌 Провайдеры

| Провайдер | Модель | Преимущества | Недостатки |
|-----------|--------|-------------|----------|
| **Replicate** | Llama 2, Claude | Дешево, быстро, мощно | Иногда медленнее |
| **OpenAI** | GPT-4, GPT-3.5 | Качество, надёжность | Дороже |

---

## Примеры реализации

### Пример 1: Добавить новый тип анализа документов

**Файл: `docs/TECHNOLOGY_PROMPTS_AND_DOCUMENTS.md` (этот документ)**

#### Шаг 1: Создать файл промпта
```json
// data/prompts/document_analysis/sentiment_analysis.json
{
  "name": "sentiment_analysis",
  "description": "💭 Анализ тональности",
  "category": "document_analysis",
  "system_prompt": "Ты эксперт по анализу тональности текста.",
  "user_prompt_template": "Определи тональность этого текста (позитивная/негативная/нейтральная).",
  "version": "1.0.0"
}
```

#### Шаг 2: Автоматическая загрузка
- PromptManager сканирует `data/prompts/` на старте
- Промпт автоматически доступен в `/analyze`
- Никаких изменений кода не требуется!

### Пример 2: Добавить новый предмет в домашку

#### Шаг 1: Определить предмет в SubjectCheckers
```python
# app/services/homework/subject_checkers.py
SUBJECT_SPANISH = Subject(
    code="spanish",
    name="Испанский язык",
    emoji="🇪🇸",
    description="Проверка испанского языка",
)
```

#### Шаг 2: Создать промпт
```json
// data/prompts/homework/spanish_homework.json
{
  "name": "spanish_homework",
  "description": "🇪🇸 Испанский язык",
  "category": "homework",
  "system_prompt": "Ты опытный учитель испанского языка...",
  "user_prompt_template": "Проверь это решение испанского упражнения..."
}
```

#### Шаг 3: Готово!
- Предмет появляется в меню `/homework`
- Система автоматически связывает `spanish` → `spanish_homework.json`

### Пример 3: Кастомизация промпта пользователем

```python
from app.services.prompts.prompt_manager import PromptManager

pm = PromptManager()
pm.load_user_prompts(user_id=123)

# Пользователь нажимает "Редактировать промпт"
pm.update_prompt(
    user_id=123,
    prompt_name="math_homework",
    system_prompt="Новый системный промпт от пользователя",
    user_prompt_template="Новый шаблон"
)

# При следующем использовании система берёт
# пользовательский промпт, а не дефолтный
prompt = pm.get_prompt(123, "math_homework")
# prompt.system_prompt == "Новый системный промпт от пользователя"
```

---

## Best Practices

### ✅ DO's

1. **Всегда загружай промпты перед использованием**
   ```python
   pm.load_user_prompts(user_id)
   prompt = pm.get_prompt(user_id, name)
   ```

2. **Используй категории для фильтрации**
   ```python
   # Для /analyze - ТОЛЬКО документные промпты
   docs = pm.get_prompt_by_category(user_id, "document_analysis")
   
   # Для /homework - ТОЛЬКО домашние промпты
   hw = pm.get_prompt_by_category(user_id, "homework")
   ```

3. **Проверяй состояние FSM перед обработкой**
   ```python
   current_state = await state.get_state()
   if current_state != ExpectedState.waiting.state:
       return  # Игнорируй сообщение
   ```

4. **Очищай состояние перед переходом между режимами**
   ```python
   await state.clear()  # СНАЧАЛА
   await state.set_state(NewState)  # ПОТОМ
   ```

5. **Всегда очищай временные файлы**
   ```python
   try:
       # обработка
   finally:
       if temp_dir.exists():
           await CleanupManager.cleanup_directory_async(temp_dir)
   ```

6. **Логируй все переходы состояний**
   ```python
   logger.info(f"User {user_id} set state to {new_state}")
   logger.debug(f"Loaded {len(prompts)} prompts for user {user_id}")
   ```

### ❌ DON'Ts

1. **Не используй `list_prompts()` для фильтрации**
   ```python
   # ❌ НЕПРАВИЛЬНО!
   all_prompts = pm.list_prompts(user_id)
   # Вернёт смешанные категории
   ```

2. **Не устанавливай состояние без предварительной очистки**
   ```python
   # ❌ НЕПРАВИЛЬНО - конфликты состояний
   await state.set_state(NewState)
   
   # ✅ ПРАВИЛЬНО
   await state.clear()
   await state.set_state(NewState)
   ```

3. **Не обрабатывай сообщения вне правильного состояния**
   ```python
   # ❌ НЕПРАВИЛЬНО - принимает все сообщения
   @router.message(F.text)
   async def handle(message):
       pass
   
   # ✅ ПРАВИЛЬНО - только в правильном состоянии
   @router.message(ExpectedState.waiting, F.text)
   async def handle(message):
       pass
   ```

4. **Не забывай удалять временные файлы**
   ```python
   # ❌ НЕПРАВИЛЬНО - утечка памяти
   async def process(message):
       temp_file = Path("./temp/file.pdf")
       # обработка
       # БЕЗ ОЧИСТКИ!
   ```

5. **Не смешивай категории промтов в UI**
   ```python
   # ❌ НЕПРАВИЛЬНО - показывает всё подряд
   for name in pm.list_prompts(user_id):
       add_button(name)
   
   # ✅ ПРАВИЛЬНО - только нужная категория
   for name in pm.get_prompt_by_category(user_id, "document_analysis"):
       add_button(name)
   ```

---

## Поиск и устранение неисправностей

### 🐛 Проблема: Промпт не найден

**症状:**
```python
prompt = pm.get_prompt(user_id, "math_homework")
# None
```

**Причины:**
1. Промпт не загружен (`load_user_prompts()` не вызван)
2. Неправильное имя промпта (проверь `prompt.name` в JSON)
3. Файл не в правильной директории

**Решение:**
```python
# 1. Проверь загрузку
pm.load_user_prompts(user_id)
logger.debug(f"Available prompts: {pm.list_prompts(user_id).keys()}")

# 2. Проверь имя
all_prompts = pm.list_prompts(user_id)
print(all_prompts)  # Выведет все доступные

# 3. Проверь файл
import os
os.listdir("./data/prompts/homework/")  # Должен быть math_homework.json
```

### 🐛 Проблема: Смешанные категории в UI

**症状:**
В `/analyze` видны кнопки "Математика", "Физика" (это из homework)

**Причина:**
```python
# ❌ НЕПРАВИЛЬНО
prompts = pm.list_prompts(user_id)  # Вернёт ВСЕ
```

**Решение:**
```python
# ✅ ПРАВИЛЬНО
prompts = pm.get_prompt_by_category(user_id, "document_analysis")
```

### 🐛 Проблема: Конфликты состояний (ошибка #1)

**症状:**
Что-то обработано в неправильном контексте (homework как chat)

**Причина:**
```python
# ❌ НЕПРАВИЛЬНО
await state.set_state(HomeworkState)
await state.set_state(ChatState)  # Конфликт!
```

**Решение:**
```python
# ✅ ПРАВИЛЬНО
await state.clear()  # СНАЧАЛА очистить
await state.set_state(ChatState)  # ПОТОМ установить
```

### 🐛 Проблема: Файлы не удаляются

**症状:**
`./temp/` растёт неконтролируемо

**Причина:**
Отсутствует cleanup в finally блоке

**Решение:**
```python
temp_dir = None
try:
    temp_dir = CleanupManager.create_temp_directory(...)
    # обработка
finally:
    if temp_dir and temp_dir.exists():
        await CleanupManager.cleanup_directory_async(temp_dir)
```

### 🐛 Проблема: OCR не работает

**症状:**
Фото не распознаётся, возвращается пустая строка

**Проверка:**
1. API ключ установлен: `echo $OCR_SPACE_API_KEY`
2. Фото в хорошем качестве (не размыто, контрастное)
3. Проверь логи: `logger.info(f"OCR: ...")`
4. Увеличь timeout: `timeout=httpx.Timeout(60.0, connect=30.0)`

**Решение:**
```python
# Посмотри логи OCR
logger.info(f"OCR: Starting extraction")
logger.info(f"OCR: Response keys: {result.keys()}")
logger.info(f"OCR: Successfully extracted {len(text)} chars")
```

---

## 📚 Дополнительные ресурсы

- [README.md](../README.md) - Основная документация
- [Architecture Diagram](./ARCHITECTURE.md) - Диаграммы архитектуры
- [API Documentation](./API.md) - Полная API документация
- [Deployment Guide](./DEPLOYMENT.md) - Развёртывание

---

## 🔄 История изменений

| Версия | Дата | Изменения |
|--------|------|----------|
| 1.0.0 | 2025-12-20 | Начальная версия технологии |

---

## ❓ FAQ

**Q: Как добавить новый тип анализа без изменения кода?**  
A: Просто добавь JSON файл в `data/prompts/document_analysis/`. PromptManager автоматически загрузит его!

**Q: Можно ли использовать один промпт для нескольких предметов?**  
A: Да, но лучше создать отдельный промпт для каждого. Это даёт больше гибкости при кастомизации.

**Q: Что если OCR.space API упадёт?**  
A: Текст из фото не будет распознан. Добавь fallback на другой OCR сервис если нужна надёжность.

**Q: Как масштабировать на много пользователей?**  
A: Текущая архитектура файловая. Для масштаба использовать БД (PostgreSQL) вместо JSON файлов.

---

**Документ актуален на:** 2025-12-20  
**Статус:** ✅ Production Ready
