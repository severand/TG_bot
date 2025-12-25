"""Управление промптами.

Исправление 2025-12-25 11:20:
- АРХИТЕКТУРНОЕ РЕШЕНИЕ: /prompts - это не режим (state), а просто меню
- При выборе категории дома - НЕ переключаемся на режим "проверка ДЗ"
- /homework команда ОТДЕЛЬНО переключает на HomeworkStates
- /analyze команда ОТДЕЛЬНО переключает на ConversationStates  
- /prompts - это просто меню навигации БЕЗ смены режима
- Когда пользователь закрывает /prompts, он возвращается в предыдущий режим (or default chat)

Исправление 2025-12-20 19:47:
- При нажатии "Отмена" из редактора -> явный переход в /chat
- Кнопка "Отмена" из состояния редактирования теперь активирует чат-режим
- Защита: состояние очищается перед установкой нового

Исправление 2025-12-20 17:56:
- Вернен оргинальный adjust(2) - 2 кнопки в ряду
- Кнопки автоматически расширяются на всю расположенную ширину

Исправление 2025-12-20 17:52:
- Кнопки расширены во всю ширину
- Очищена ошибка markdown при сохранении

Обрабатывает взаимодействия пользователя для управления системными промптами.
Включает навигацию и редактирование существующих промптов.
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.prompts.prompt_manager import PromptManager
from app.states.prompts import PromptStates
from app.states.chat import ChatStates

logger = logging.getLogger(__name__)

router = Router()
prompt_manager = PromptManager()


def get_subject_display_name(prompt_name: str) -> str:
    """Получить название предмета для промпта.
    
    Args:
        prompt_name: Идентификатор промпта
        
    Returns:
        str: Название с наименованием предмета
    """
    # Маппинг предметов
    subjects = {
        "math_homework": "Математика (math_homework)",
        "russian_homework": "Русский язык (russian_homework)",
        "english_homework": "Английский язык (english_homework)",
        "physics_homework": "Физика (physics_homework)",
        "chemistry_homework": "Химия (chemistry_homework)",
        "cs_homework": "Информатика (cs_homework)",
        "geography_homework": "География (geography_homework)",
        "literature_homework": "Литература (literature_homework)",
        # Анализ документов
        "default": "Базовый анализ (default)",
        "summarize": "Краткое резюме (summarize)",
        "extract_entities": "Извлечение данных (extract_entities)",
        "risk_analysis": "Анализ рисков (risk_analysis)",
        "legal_review": "Юридическая проверка (legal_review)",
        # Чат
        "chat_system": "Основной диалог (chat_system)",
    }
    return subjects.get(prompt_name, prompt_name)


# Клавиатуры навигации
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню управления промптами - 2 кнопки в ряду."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Документы", callback_data="prompts_category_document_analysis")
    builder.button(text="💬 Диалог", callback_data="prompts_category_chat")
    builder.button(text="📖 Домашка", callback_data="prompts_category_homework")
    builder.button(text="« Назад", callback_data="back_to_main")
    builder.adjust(2)  # По 2 кнопки в ряду - они расширяются автоматически
    return builder.as_markup()


def get_category_keyboard(user_id: int, category: str) -> InlineKeyboardMarkup:
    """Клавиатура для промптов в категории."""
    prompts = prompt_manager.get_prompt_by_category(user_id, category)
    
    builder = InlineKeyboardBuilder()
    
    for name in sorted(prompts.keys()):
        prompt = prompts[name]
        # Описание промпта
        button_text = f"{prompt.description[:35]}"
        builder.button(
            text=button_text,
            callback_data=f"prompt_select_{name}"
        )
    
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)  # По 2 кнопки в ряду
    return builder.as_markup()


def get_prompt_detail_keyboard(prompt_name: str) -> InlineKeyboardMarkup:
    """Клавиатура деталей промпта."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать", callback_data=f"prompt_edit_{prompt_name}")
    builder.button(text="« Назад", callback_data="prompts_menu")
    builder.adjust(2)  # По 2 кнопки в ряду
    return builder.as_markup()


async def start_prompts_mode(callback: CallbackQuery = None, message: Message = None, state: FSMContext = None) -> None:
    """Показать меню управления промптами.
    
    АРХИТЕКТУРНО ВАЖНО:
    /prompts это НЕ режим (state), а просто интерактивное меню.
    Мы НЕ переключаемся на PromptStates - это было бы ошибкой.
    Пользователь остается в своем текущем режиме (chat, homework, analyze).
    """
    if state is None:
        logger.error("Ошибка: state is None in start_prompts_mode")
        return
    
    # КРИТИЧЕСКОЕ: Сохраняем текущее состояние, чтобы вернуться после закрытия меню
    data = await state.get_data()
    current_state = await state.get_state()
    
    logger.debug(f"Opening prompts menu for user, current state was: {current_state}")
    
    text = (
        "🎛️ *Управление промптами*\n\n"
        "📌 *Доступные промпты:*\n"
        "• 📄 Документы: 5 промптов анализа\n"
        "• 💬 Диалог: 1 основной промпт\n"
        "• 📖 Домашка: 8 промптов по предметам\n\n"
        "📝 *Как это использовать:*\n"
        "1️⃣ Выберите категорию\n"
        "2️⃣ Нажмите на промпт\n"
        "3️⃣ Кликните 'Редактировать'\n"
        "4️⃣ Отредактируйте\n"
        "5️⃣ Нажмите 'Отправить' - сохранится!\n\n"
        "👇 Выберите категорию:"
    )
    
    if message:
        user_id = message.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        logger.info(f"Пользователь {user_id} начал работу с промптами")
    elif callback:
        user_id = callback.from_user.id
        prompt_manager.load_user_prompts(user_id)
        
        await callback.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.answer()
        logger.info(f"Пользователь {user_id} начал работу с промптами")


@router.message(Command("prompts"))
async def cmd_prompts(message: Message, state: FSMContext) -> None:
    """Отображение меню редактирования промптов.
    
    АРХИТЕКТУРНО: /prompts это меню, которое НЕ меняет режим работы бота.
    Пользователь может быть в чате, нажать /prompts, отредактировать промпт,
    и вернуться к предыдущей деятельности.
    """
    logger.info(f"Пользователь {message.from_user.id} активировал /prompts")
    await start_prompts_mode(message=message, state=state)


@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(query: CallbackQuery, state: FSMContext) -> None:
    """Вернуться в главное меню (выход из /prompts меню).
    
    АРХИТЕКТУРНО: При выходе из меню, возвращаемся в CHAT MODE (default).
    Это гарантирует, что пользователь не застрянет в PromptStates.
    """
    user_id = query.from_user.id
    
    # Очищаем PromptStates если был
    current_state = await state.get_state()
    if current_state and current_state.startswith("PromptStates"):
        await state.clear()
        logger.debug(f"Cleared PromptStates for user {user_id}")
    
    # Устанавливаем chat mode как default
    await state.set_state(ChatStates.chatting)
    logger.debug(f"Set ChatStates.chatting for user {user_id}")
    
    text = "💬 *Вернулись в режим диалога*\n\nПишите свой вопрос или используйте команды!"
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=None,
    )
    await query.answer()
    logger.info(f"Пользователь {user_id} вышел из меню промптов и вернулся в чат")


@router.callback_query(F.data == "prompts_menu")
async def cb_prompts_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Открыть меню управления промптами.
    
    АРХИТЕКТУРНО: Это просто показ меню, НЕ смена режима.
    """
    # Очищаем PromptStates если был, но НЕ трогаем основное состояние
    current_state = await state.get_state()
    if current_state and current_state.startswith("PromptStates"):
        await state.clear()
        await state.set_state(ChatStates.chatting)
    
    text = (
        "🎛️ *Управление промптами*\n\n"
        "👇 Выберите категорию:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(),
    )
    await query.answer()
    logger.info(f"Пользователь {query.from_user.id} вернулся в меню управления")


@router.callback_query(F.data.startswith("prompts_category_"))
async def cb_prompts_category(query: CallbackQuery) -> None:
    """Навигация к выбранной категории.
    
    АРХИТЕКТУРНО: Просто показываем список промптов в категории.
    НЕ меняем режим работы (state).
    """
    user_id = query.from_user.id
    category = query.data.replace("prompts_category_", "")
    
    # Обновляем данные пользователя
    prompt_manager.load_user_prompts(user_id)
    prompts = prompt_manager.get_prompt_by_category(user_id, category)
    
    # Читаем название категории
    category_names = {
        "document_analysis": "📄 Документы",
        "chat": "💬 Диалог",
        "homework": "📖 Домашка",
    }
    
    text = (
        f"*{category_names.get(category, category)}* ({len(prompts)})\n\n"
        f"👇 Где кликать для редактирования:"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_category_keyboard(user_id, category),
    )
    await query.answer()
    logger.info(f"Пользователь {user_id} на категории: {category}")


@router.callback_query(F.data.startswith("prompt_select_"))
async def cb_prompt_select(query: CallbackQuery) -> None:
    """Отображение деталей промпта.
    
    АРХИТЕКТУРНО: Просто показываем информацию, НЕ меняем состояние.
    """
    user_id = query.from_user.id
    prompt_name = query.data.replace("prompt_select_", "")
    
    # Обновляем данные
    prompt_manager.load_user_prompts(user_id)
    prompt = prompt_manager.get_prompt(user_id, prompt_name)
    
    if not prompt:
        await query.answer("❌ Промпт не найден")
        return
    
    # Проверяем статус
    user_prompts = prompt_manager.get_user_prompts(user_id)
    is_custom = prompt_name in user_prompts
    
    # Получаем название
    subject_name = get_subject_display_name(prompt_name)
    
    # НЕ экранируем - отображаем как есть
    system_text = prompt.system_prompt[:200]
    user_text = prompt.user_prompt_template[:200]
    
    # Ток либо свой, либо системный
    type_badge = "👤 Ваш" if is_custom else "🤖 Системный"
    
    text = (
        f"🎯 *{subject_name}*\n"
        f"{type_badge}\n"
        f"_{prompt.description}_\n\n"
        f"*Системный промпт:*\n`{system_text}...`\n\n"
        f"*Шаблон:*\n`{user_text}...`\n\n"
        f"👇 Что сделать?"
    )
    
    await query.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_prompt_detail_keyboard(prompt_name),
    )
    await query.answer()
    logger.info(f"Пользователь {user_id} на деталях: {prompt_name}")


@router.callback_query(F.data.startswith("prompt_edit_"))
async def cb_prompt_edit(query: CallbackQuery, state: FSMContext) -> None:
    """Начало редактирования - выбор варианта."""
    # Выделяем название промпта
    if query.data.startswith("prompt_edit_system_"):
        prompt_name = query.data.replace("prompt_edit_system_", "")
        edit_type = "system"
    elif query.data.startswith("prompt_edit_user_"):
        prompt_name = query.data.replace("prompt_edit_user_", "")
        edit_type = "user"
    else:
        prompt_name = query.data.replace("prompt_edit_", "")
        edit_type = None
    
    # Обновляем данные
    prompt_manager.load_user_prompts(query.from_user.id)
    prompt = prompt_manager.get_prompt(query.from_user.id, prompt_name)
    
    if not prompt:
        await query.answer("❌ Промпт не найден")
        return
    
    # Если это редактирование поля
    if edit_type:
        await state.update_data(editing_prompt=prompt_name, edit_field=edit_type)
        
        # Получаем название
        subject_name = get_subject_display_name(prompt_name)
        
        if edit_type == "system":
            await state.set_state(PromptStates.editing_system)
            # На скрин внеси ПОЛНЫЙ текст!
            text = (
                f"✏️ *Редактировать: {subject_name}*\n\n"
                f"*Текущий системный промпт:*\n`{prompt.system_prompt}`\n\n"
                f"Внесите новый текст для системного промпта:"
            )
        else:  # user
            await state.set_state(PromptStates.editing_user)
            # На скрин внеси ПОЛНЫЙ текст!
            text = (
                f"✏️ *Редактировать: {subject_name}*\n\n"
                f"*Текущий шаблон:*\n`{prompt.user_prompt_template}`\n\n"
                f"Внесите новый текст для шаблона:"
            )
        
        # Кнопка отмены -> переход в чат (FIX: была "Назад в редактор")
        builder = InlineKeyboardBuilder()
        builder.button(
            text="❌ Отмена -> Диалог",
            callback_data="cancel_edit_go_to_chat"
        )
        builder.adjust(2)  # По 2 кнопки
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    else:
        # Показываем варианты
        builder = InlineKeyboardBuilder()
        builder.button(
            text="📝 Системный промпт",
            callback_data=f"prompt_edit_system_{prompt_name}"
        )
        builder.button(
            text="📝 Шаблон",
            callback_data=f"prompt_edit_user_{prompt_name}"
        )
        builder.button(
            text="« Назад",
            callback_data=f"prompt_select_{prompt_name}"
        )
        builder.adjust(2)  # По 2 кнопки
        
        # Получаем название
        subject_name = get_subject_display_name(prompt_name)
        
        text = (
            f"✏️ *Редактировать: {subject_name}*\n\n"
            f"Что вы хотите отредактировать?"
        )
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
    
    await query.answer()
    logger.info(f"Пользователь {query.from_user.id} начал редактирование: {prompt_name}")


@router.callback_query(F.data == "cancel_edit_go_to_chat")
async def cb_cancel_edit_go_to_chat(query: CallbackQuery, state: FSMContext) -> None:
    """Отмена редактирования и явный переход в режим чата.
    
    КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 2025-12-20 19:47:
    - Сначала ПОЛНАЯ очистка состояния
    - Затем установка ChatStates.chatting
    - Затем удаление сообщения редактора и активация чата
    """
    user_id = query.from_user.id
    
    # Шаг 1: ПОЛНАЯ очистка состояния - убираем ВСЕ старые флаги
    await state.clear()
    logger.debug(f"State cleared for user {user_id}")
    
    # Шаг 2: Установка состояния чата
    await state.set_state(ChatStates.chatting)
    logger.debug(f"Set ChatStates.chatting for user {user_id}")
    
    # Шаг 3: Удаляем старое сообщение редактора
    await query.message.delete()
    
    # Шаг 4: Отправляем активационное сообщение чата
    text = (
        "💬 *Режим диалога активен*\n\n"
        "Пишите мне свои вопросы, я готов помочь!"
    )
    
    await query.message.answer(
        text,
        parse_mode="Markdown",
    )
    
    await query.answer()
    logger.info(f"User {user_id} cancelled editing and returned to chat mode")


@router.message(PromptStates.editing_system)
async def msg_edit_system(message: Message, state: FSMContext) -> None:
    """Охрана отредактированного системного промпта."""
    new_system = message.text
    
    if not new_system or len(new_system) < 10:
        await message.answer(
            "❌ Текст слишком короткий.\n\nПотори еще:"
        )
        return
    
    data = await state.get_data()
    prompt_name = data["editing_prompt"]
    
    # Охраняем
    prompt_manager.update_prompt(
        user_id=message.from_user.id,
        prompt_name=prompt_name,
        system_prompt=new_system,
    )
    
    # Получаем название
    subject_name = get_subject_display_name(prompt_name)
    
    # Окраживаем двужные символы для текста
    display_text = new_system[:100]
    # Удаляем `` квадратные скобки чтобы не сломать markdown
    display_text = display_text.replace("[", "").replace("]", "")
    display_text = display_text.replace("*", "")
    
    # Кнопка возврата в опции редактирования
    builder = InlineKeyboardBuilder()
    builder.button(
        text="« Назад в опции редактирования",
        callback_data=f"prompt_edit_{prompt_name}"
    )
    builder.adjust(2)  # По 2 кнопки
    
    await message.answer(
        f"✅ Охранено!\n\n"
        f"Обновлено: {subject_name}\n"
        f"Текст: {display_text}...",
        parse_mode=None,  # без markdown!
        reply_markup=builder.as_markup(),
    )
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} осохранил системный промпт: {prompt_name}")


@router.message(PromptStates.editing_user)
async def msg_edit_user(message: Message, state: FSMContext) -> None:
    """Охрана отредактированного пользовательского шаблона."""
    new_user = message.text
    
    if not new_user or len(new_user) < 10:
        await message.answer(
            "❌ Текст слишком короткий.\n\nПотори еще:"
        )
        return
    
    data = await state.get_data()
    prompt_name = data["editing_prompt"]
    
    # Охраняем
    prompt_manager.update_prompt(
        user_id=message.from_user.id,
        prompt_name=prompt_name,
        user_prompt_template=new_user,
    )
    
    # Получаем название
    subject_name = get_subject_display_name(prompt_name)
    
    # Окраживаем двужные символы для текста
    display_text = new_user[:100]
    # Удаляем `` квадратные скобки чтобы не сломать markdown
    display_text = display_text.replace("[", "").replace("]", "")
    display_text = display_text.replace("*", "")
    
    # Кнопка возврата в опции редактирования
    builder = InlineKeyboardBuilder()
    builder.button(
        text="« Назад в опции редактирования",
        callback_data=f"prompt_edit_{prompt_name}"
    )
    builder.adjust(2)  # По 2 кнопки
    
    await message.answer(
        f"✅ Охранено!\n\n"
        f"Обновлено: {subject_name}\n"
        f"Текст: {display_text}...",
        parse_mode=None,  # без markdown!
        reply_markup=builder.as_markup(),
    )
    await state.clear()
    logger.info(f"Пользователь {message.from_user.id} осохранил шаблон: {prompt_name}")
