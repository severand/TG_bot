"""Examples of using the homework checking service.

This file demonstrates how to use the homework checker
in different scenarios.
"""

import asyncio
from app.services.homework import HomeworkChecker, SubjectCheckers, ResultVisualizer
from app.services.llm.replicate_service import ReplicateService


async def example_1_simple_math():
    """Пример 1: Простая проверка математики."""
    
    # Initialize LLM
    llm = ReplicateService(api_key="YOUR_REPLICATE_API_KEY")
    checker = HomeworkChecker(llm)
    
    # Sample homework
    homework_content = """
    Таска 1: 2 + 2 = 4
    Таска 2: 5 х 3 = 15
    Таска 3: 10 – 4 = 7  (ОШИБКА!)
    """
    
    # Check homework
    result = await checker.check_homework(
        content=homework_content,
        subject="math"
    )
    
    # Display result
    formatted = ResultVisualizer.format_result(result)
    print(formatted)
    print(f"\nGrade: {result.grade}/5")
    print(f"Points: {result.points}/{result.max_points}")


async def example_2_russian_text():
    """Пример 2: Проверка снег работы по Русскому."""
    
    llm = ReplicateService(api_key="YOUR_REPLICATE_API_KEY")
    checker = HomeworkChecker(llm)
    
    essay = """
    В этом сочинении мы рассмотрим тему жизни и смерти. 
    Персонажи романа осто раскрывают эти философские глубины.
    """
    
    result = await checker.check_homework(
        content=essay,
        subject="russian"
    )
    
    print(ResultVisualizer.format_result(result))


async def example_3_get_all_subjects():
    """Пример 3: Узнать все поддерживаемые предметы."""
    
    print("📖 Список всех предметов:\n")
    
    for subject in SubjectCheckers.get_subjects_list():
        print(f"{subject.emoji} {subject.name} ({subject.code})")
        print(f"   {subject.description}\n")


async def example_4_english_task():
    """Пример 4: Проверка английского языка."""
    
    llm = ReplicateService(api_key="YOUR_REPLICATE_API_KEY")
    checker = HomeworkChecker(llm)
    
    english_homework = """
    Question 1: What is the capital of France?
    Answer: Paris
    
    Question 2: Translate "dog" to Russian
    Answer: sobaka
    
    Question 3: Write a sentence about the weather
    Answer: The weather is very good today.
    """
    
    result = await checker.check_homework(
        content=english_homework,
        subject="english"
    )
    
    print(ResultVisualizer.format_result(result))


async def example_5_short_format():
    """Пример 5: Короткий вывод результата."""
    
    llm = ReplicateService(api_key="YOUR_REPLICATE_API_KEY")
    checker = HomeworkChecker(llm)
    
    homework = "2+2=4, 3+3=6, 5+5=10"
    
    result = await checker.check_homework(
        content=homework,
        subject="math"
    )
    
    # Use short format for quick display
    short = ResultVisualizer.format_short_result(result)
    print(short)


async def main():
    """Рун алл ексамплес."""
    
    print("🙋 НУ стоп до понимания эксамплов.\n")
    print("Установите YOUR_REPLICATE_API_KEY в примерах для работы.\n")
    
    # Example 3 doesn't require API
    print("Пример 3: Все предметы")
    await example_3_get_all_subjects()
    
    print("\n" + "="*50)
    print("Для запуска других примеров установите API ключ.")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
