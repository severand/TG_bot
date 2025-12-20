# 📚 Homework Checking Service

Full-featured homework evaluation system with subject-specific rubrics and AI-powered checking.

## Features

✓ **8 Subjects** - Mathematics, Russian, English, Physics, Chemistry, Computer Science, Geography, Literature
✓ **Smart Evaluation** - AI-powered grading with detailed feedback
✓ **Multiple Formats** - Support for text, PDF, DOCX, and TXT files
✓ **Rubric System** - Subject-specific grading criteria
✓ **Visual Results** - Beautiful formatted output with progress bars and emojis
✓ **Detailed Feedback** - Specific errors, suggestions, and areas for improvement

## Architecture

### Module Structure

```
app/services/homework/
├── __init__.py              # Package initialization
├── checker.py              # Main evaluation engine
├── subjects.py             # Subject definitions and metadata
├── rubric.py               # Grading rubrics and criteria
├── visualizer.py           # Result formatting and display
└── README.md               # This file
```

### Handler

```
app/handlers/
└── homework.py             # Telegram command handler
```

### States

```
app/states/
└── homework.py             # FSM states for workflow
```

## Usage

### From User Perspective

1. Send `/homework` command
2. Select subject (8 options available)
3. Upload file (text, PDF, DOCX) or paste text
4. Get instant evaluation with:
   - Grade (1-5 stars)
   - Points breakdown
   - Correct answers highlighted
   - Errors with explanations
   - Constructive advice for improvement

### From Developer Perspective

```python
from app.services.homework import HomeworkChecker
from app.services.llm.replicate_service import ReplicateService

# Initialize
llm = ReplicateService(api_key="...")
checker = HomeworkChecker(llm)

# Check homework
result = await checker.check_homework(
    content="User's homework text",
    subject="math"  # or: russian, english, physics, chemistry, cs, geography, literature
)

# Use result
from app.services.homework import ResultVisualizer

formatted = ResultVisualizer.format_result(result)
print(formatted)  # Beautiful formatted output
```

## Supported Subjects

| Code | Subject | Emoji | Focus Areas |
|------|---------|-------|-------------|
| math | Математика | 🔢 | Calculations, methods, formatting |
| russian | Русский язык | 🔤 | Spelling, punctuation, grammar |
| english | Английский | 🇬🇧 | Grammar, vocabulary, pronunciation |
| physics | Физика | ⚗️ | Formulas, calculations, explanations |
| chemistry | Химия | 🧪 | Equations, reactions, stoichiometry |
| cs | Информатика | 💻 | Code syntax, logic, efficiency |
| geography | География | 🌍 | Facts, structure, examples |
| literature | Литература | 📖 | Analysis, citations, argumentation |

## Grading Scale

- **5 🌟** - Excellent! (90-100%)
- **4 🌟🌟** - Good! (75-89%)
- **3 🌟🌟🌟** - Satisfactory (60-74%)
- **2 ⚠️** - Poor (45-59%)
- **1 😤** - Very Poor (<45%)

## Example Output

```
==================================================
🌟🌟🌟🌟🌟 Проверка: Математика
==================================================

⚡ Оценка: 😀🎊 Отлично!
   Оценка: 5 из 5

💯 Токи: 95/100 (95%)
   [███████████████████░]

✅ Что правильно:
   ✓ Таск 1 - молодец!
   ✓ Таск 3 - отлично!

❌ Ошибки:
   ✗ Таск 2 - ошибка в счете
     Правильно: 2+2=4
     У тебя: 2+2=5

📚 Подробно:
   Вы направились в направлении...

💭 Совет для иловравления:
   Проверьте счет...

==================================================
```

## Cost Estimation

Per homework check:
- Text file: ~$0.001-0.002 (GPT-4o-mini)
- Image (vision): ~$0.02 (GPT-4o-mini with vision)

100 checks/month: ~$0.10-$2.00

## Future Enhancements

- [ ] Image/photo processing with OCR
- [ ] Handwriting recognition
- [ ] Batch processing (multiple students)
- [ ] Progress tracking and history
- [ ] Custom grading rubrics
- [ ] Teacher dashboard
- [ ] Student statistics
- [ ] Parent notifications
- [ ] Integration with LMS

## Integration Points

### LLM Service
- Uses `ReplicateService` for evaluation
- Compatible with any LLM via abstraction

### File Processing
- Integrates with `PDFProcessor` for PDF files
- Works with `python-docx` for Word documents
- Plain text processing built-in

### State Management
- FSM-based workflow using Aiogram states
- User context preservation
- Multi-step interaction flow

## Error Handling

Graceful error handling for:
- Unsupported file formats
- LLM service failures
- Content extraction issues
- Invalid subject selection

## Notes

- All grading is consistent and objective
- Subject-specific evaluation criteria ensure relevance
- Beautiful formatting makes results easy to understand
- Completely independent from other bot modules
- Can be easily removed without affecting other features
