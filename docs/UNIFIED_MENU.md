# Единое Меню - Unified Menu System

Описание системы единого меню для Uh Bot.

Основано на архитектуре InteriorBot.

---

## Основное Отрицание

**НЕ нести множества меню в чате** - одно меню для редактирования!

```
✅ CORRECT (One menu, editing it)
Меню 1
Ответ клик [Кнопка]
Меню 2 (edited)
Ответ клик [Кнопка]

❌ WRONG (Multiple menus)
Меню 1
Ответ клик
МЕНУ 2 (NEW)
Ответ клик
МЕНУ 3 (NEW)
```

---

## Ключевые Концепции

### 1. menu_message_id

**Критическая переменная** для хранения ID главного меню.

Хранится в FSM state:
```python
await state.update_data(menu_message_id=message_id)
```

### 2. state.set_state(None) vs state.clear()

**ПРИ НАВИГАЦИИ:**
```python
await state.set_state(None)  # ✅ Оставляет menu_message_id
```

**ПРИ ПОЛНОМ СБРОСЕ:**
```python
await state.clear()  # ✅ Удаляет всё
```

**ОШИБКА:**
```python
await state.clear()  # ❌ Теряются данные двигаются
```

### 3. edit_message_text vs message.answer

**ПРИ НАВИГАЦИИ:**
```python
await message.bot.edit_message_text(  # ✅ Обновляет старое меню
    chat_id=chat_id,
    message_id=menu_message_id,
    text=text,
    reply_markup=keyboard
)
```

**ОШИБКА:**
```python
await message.answer(text)  # ❌ Новое сообщение внизу!
```

---

## API MenuManager

### show_menu()

Показать или обновить меню.

```python
await MenuManager.show_menu(
    callback=callback,  # ор message
    state=state,
    text="Меню",
    keyboard=keyboard,
    screen_code="chat_mode",  # для отладки
)
```

**Что эта функция:**
- Пытается отредактировать старое меню
- Эсли не найдено - создает новое
- Обновляет `menu_message_id` в FSM

### navigate()

Перейти на другое меню.

```python
await MenuManager.navigate(
    callback=callback,
    state=state,
    text="Новое меню",
    keyboard=new_keyboard,
    new_state=ChatStates.chatting,  # новое состояние
    screen_code="chat_mode",
    preserve_data=True,  # сохранять данные
)
```

**Что эта функция:**
- Использует `set_state(None)` - сохраняет данные
- Эсли `preserve_data=True` - восстанавливает `menu_message_id`
- Цель: бесятная навигация

### clear_session()

Полный сброс.

```python
await MenuManager.clear_session(callback, state)
```

**Когда использовать:**
- Команда `/start`
- Полные экстренные выходы

### create_keyboard()

На рюсе состав кнопок.

```python
keyboard = create_keyboard(
    buttons=[
        ("💬 Диалог", "mode_chat"),
        ("📄 Анализ", "mode_analyze"),
        ("🎯 Промты", "mode_prompts"),
    ],
    rows_per_row=2,  # 2 кнопки в ряде
)
```

**Пример:**
```
BTN1  BTN2
BTN3
✅ Нормально!
```

---

## Примеры

### Пример 1: Показать постоянное меню

```python
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    # Очистить старую сессию
    await state.clear()
    
    # Составить клавиатуру
    keyboard = create_keyboard([
        ("💬 Чат", "chat"),
        ("📄 Документы", "docs"),
    ], rows_per_row=2)
    
    # Показать меню
    await MenuManager.show_menu(
        message=message,
        state=state,
        text="Навигация:",
        keyboard=keyboard,
    )
```

### Пример 2: Ответить на сообщение в одном меню

```python
@router.message(ChatStates.waiting_input)
async def process_input(message: Message, state: FSMContext):
    # 1. Очистить сообщение пользователя
    try:
        await message.delete()
    except:
        pass
    
    # 2. Получить menu_message_id
    data = await state.get_data()
    menu_message_id = data.get("menu_message_id")
    
    # 3. Обновить одно меню
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=menu_message_id,
        text=f"Ответ: {message.text}",
        reply_markup=keyboard,
    )
```

### Пример 3: Переход бет ссылки на выборба

```python
@router.callback_query(F.data == "go_to_chat")
async def go_to_chat(callback: CallbackQuery, state: FSMContext):
    # Перейти на чат, сохраняя данные
    keyboard = create_keyboard([("Exit", "back")], rows_per_row=1)
    
    await MenuManager.navigate(
        callback=callback,
        state=state,
        text="Чат открыт",
        keyboard=keyboard,
        new_state=ChatStates.chatting,
        preserve_data=True,
    )
```

---

## ОШИБки КОТОРЫЕ МОГУТ Произойти

### Ошибка 1: Множественные меню

**Проблема:**
```python
# Каждые раз посылается новое меню!
await message.answer(text)
await message.answer(text)
await message.answer(text)
```

**Правка:**
```python
# Обновлять существующее меню
await MenuManager.show_menu(
    message=message,
    state=state,
    text=text,
    keyboard=keyboard,
)
```

### Ошибка 2: Не сохраняется menu_message_id

**Проблема:**
```python
await state.clear()  # ❌ Удаляет всё
```

**Правка:**
```python
await state.set_state(None)  # ✅ Оставляет данные
```

---

## чЕКЛИСТ ПЕРЕД КОМИТом

- [ ] Все навигации через `MenuManager.navigate()`
- [ ] Все обновления меню через `MenuManager.show_menu()`
- [ ] `state.set_state(None)` на навигацию
- [ ] `state.clear()` только для /start
- [ ] `menu_message_id` не теряется при навигации
- [ ] Кнопки составляются через `create_keyboard()`
- [ ] rows_per_row=2 для двух ряда

---

## Отладка

### Добавить логи

```python
data = await state.get_data()
logger.debug(f"menu_message_id={data.get('menu_message_id')}")
```

### Проверить что троется

1. После обновления меню - это то же меню?
2. Не создается новое меню внизу?
3. menu_message_id сохранился после навигации?

---

**Ласт Апдейт: 2025-12-19**
