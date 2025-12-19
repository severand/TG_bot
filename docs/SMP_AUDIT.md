# 🔍 SMP AUDIT - Проверка соответствия Single Menu Pattern

**Дата:** 2025-12-19  
**Версия кода:** 1.0  
**Технология:** Single Menu Pattern (SMP)  

---

## 📊 РЕЗУЛЬТАТЫ АУДИТА

### Статус: ⚠️ ЧАСТИЧНОЕ СООТВЕТСТВИЕ (70%)

**Что реализовано правильно:**
- ✅ Единое меню (menu_message_id)
- ✅ edit_message_text вместо message.answer
- ✅ Сохранение состояния в FSM
- ✅ Навигация между экранами

**Что нужно исправить:**
- ❌ Нет специализированного класса SingleMenuManager
- ❌ Нет таблицы chat_menus в БД
- ❌ Нет обработки устаревших кнопок (stale buttons)
- ❌ Нет screen_code в логировании и БД
- ❌ Нет fallback-восстановления после перезапуска бота

---

## 🎯 ПРОБЛЕМЫ И РЕШЕНИЯ

### Проблема 1: MenuManager vs SingleMenuManager

**ТЕКУЩИЙ КОД:**
```python
# app/utils/menu.py
class MenuManager:
    async def show_menu(...)  # ✅ Хорошо
    async def navigate(...)   # ✅ Хорошо
    async def clear_session(...) # ✅ Хорошо
```

**ТРЕБУЕТ SMP:**
```python
# core/single_menu.py
class SingleMenuManager:
    async def navigate(...)  # ✨ БОЛЬШЕ функций
    async def _find_menu_id(...)  # Поиск в FSM + БД
    async def _try_edit(...)  # Обработка ошибок
    async def _create_new_menu(...)  # Fallback
    async def _save_menu_state(...)  # В БД + FSM
    async def delete_menu(...)  # Полное удаление
```

**РЕШЕНИЕ:**
Обновить `MenuManager` добавив недостающие методы и логику.

---

### Проблема 2: Отсутствие таблицы chat_menus

**ТЕКУЩАЯ БД:**
```sql
-- Есть таблицы для документов, платежей, итд
-- НО нет таблицы для состояния меню!
```

**ТРЕБУЕТ SMP:**
```sql
CREATE TABLE chat_menus (
    chat_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    menu_message_id INTEGER NOT NULL,
    screen_code TEXT DEFAULT 'main_menu',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**РЕШЕНИЕ:**
Добавить миграцию и класс MenuDatabase.

---

### Проблема 3: Нет обработки устаревших кнопок

**ТЕКУЩИЙ КОД:**
```python
# Если пользователь нажимает кнопку после перезапуска бота
# - FSM пусто
# - menu_message_id потерян
# - Бот падает или ошибка
```

**ТРЕБУЕТ SMP:**
```python
class StaleButtonHandler:
    @staticmethod
    async def handle(
        callback,
        state,
        required_fsm_keys=['product'],
        menu_manager=menu_manager,
        fallback_handler=show_main_menu
    ):
        # Проверяет наличие данных
        # Если FSM пусто -> fallback
        # Если есть в БД -> восстанавливает
```

**РЕШЕНИЕ:**
Добавить StaleButtonHandler и использовать в callback_query.

---

### Проблема 4: Нет screen_code в логах

**ТЕКУЩИЙ КОД:**
```python
logger.debug(f"🔍 [DEBUG] menu_message_id={data.get('menu_message_id')}")
# Не информативно, какой экран активен
```

**ТРЕБУЕТ SMP:**
```python
logger.info(f"✅ [SMP] Edited menu {menu_id} → chat_mode")
logger.info(f"🆕 [SMP] Created new menu {new_menu_id} → {screen_code}")
logger.info(f"🔄 [SMP] Stale session reset: missing {missing_keys}")
```

**РЕШЕНИЕ:**
Добавить screen_code во все методы и логи.

---

### Проблема 5: Нет автовосстановления после перезапуска

**ТЕКУЩИЙ КОД:**
```python
# При перезапуске бота:
data = await state.get_data()
menu_message_id = data.get("menu_message_id")  # None!
# Меню потеряно
```

**ТРЕБУЕТ SMP:**
```python
# При перезапуске бота:
menu_info = await self.db.get_menu(chat_id)  # ✅ Есть в БД!
if menu_info:
    menu_id = menu_info[2]  # message_id
    await state.update_data(menu_message_id=menu_id)  # Восстановлено!
```

**РЕШЕНИЕ:**
Использовать БД как источник истины для menu_message_id.

---

## 🔧 ПЛАН ИСПРАВЛЕНИЙ

### Шаг 1: Обновить MenuManager → SingleMenuManager

```python
# Переименовать и расширить app/utils/menu.py

class SingleMenuManager:
    def __init__(self, bot: Bot, db_manager):
        self.bot = bot
        self.db = db_manager
    
    async def navigate(
        self,
        callback: CallbackQuery,
        state: FSMContext,
        screen_code: str,  # 🆕 ДОБАВИТЬ
        text: str,
        keyboard: InlineKeyboardMarkup | None = None,
        parse_mode: str = "Markdown",
        save_to_fsm: bool = True
    ) -> int:
        """Универсальная навигация"""
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        
        # 🆕 ДОБАВИТЬ: Поиск menu_id в FSM + БД
        menu_id = await self._find_menu_id(chat_id, state)
        
        if menu_id:
            # 🆕 ДОБАВИТЬ: Обработка ошибок
            edited = await self._try_edit(
                chat_id, menu_id, text, keyboard, parse_mode
            )
            if edited:
                await self._save_menu_state(
                    chat_id, user_id, menu_id, screen_code, state, save_to_fsm
                )
                logger.debug(f"✅ [SMP] Edited menu {menu_id} → {screen_code}")
                return menu_id
            else:
                await self.db.delete_menu(chat_id)
        
        # 🆕 ДОБАВИТЬ: Создание нового меню
        new_menu_id = await self._create_new_menu(
            callback.message, text, keyboard, parse_mode
        )
        await self._save_menu_state(
            chat_id, user_id, new_menu_id, screen_code, state, save_to_fsm
        )
        logger.info(f"🆕 [SMP] Created new menu {new_menu_id} → {screen_code}")
        return new_menu_id
    
    async def _find_menu_id(self, chat_id: int, state: FSMContext) -> int | None:
        """🆕 Поиск menu_id в FSM или БД"""
        # Сначала FSM
        data = await state.get_data()
        menu_id = data.get('menu_message_id')
        if menu_id:
            return menu_id
        
        # Потом БД (автовосстановление)
        menu_record = await self.db.get_menu(chat_id)
        if menu_record:
            menu_id = menu_record[2]
            await state.update_data(menu_message_id=menu_id)
            return menu_id
        
        return None
    
    async def _try_edit(self, chat_id: int, message_id: int, text: str, 
                       keyboard: InlineKeyboardMarkup | None, 
                       parse_mode: str) -> bool:
        """🆕 Попытка редактировать существующее меню"""
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=parse_mode
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return True  # OK, контент не изменился
            logger.warning(f"⚠️ [SMP] Failed to edit menu {message_id}: {e}")
            return False
    
    async def _create_new_menu(self, message: Message, text: str,
                              keyboard: InlineKeyboardMarkup | None,
                              parse_mode: str) -> int:
        """🆕 Создание нового меню (fallback)"""
        new_message = await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )
        return new_message.message_id
    
    async def _save_menu_state(self, chat_id: int, user_id: int, 
                              message_id: int, screen_code: str,
                              state: FSMContext, save_to_fsm: bool):
        """🆕 Сохранение состояния в БД + FSM"""
        # В БД (основной источник)
        await self.db.save_menu(chat_id, user_id, message_id, screen_code)
        
        # В FSM (для быстрого доступа)
        if save_to_fsm:
            await state.update_data(menu_message_id=message_id)
    
    async def delete_menu(self, chat_id: int, message_id: int | None = None):
        """🆕 Удаление меню"""
        if message_id:
            try:
                await self.bot.delete_message(chat_id, message_id)
            except:
                pass
        await self.db.delete_menu(chat_id)
```

### Шаг 2: Создать MenuDatabase

```python
# core/menu_database.py

class MenuDatabase:
    async def init_db(self):
        """Создать таблицу chat_menus"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_menus (
                chat_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                menu_message_id INTEGER NOT NULL,
                screen_code TEXT DEFAULT 'main_menu',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def save_menu(self, chat_id, user_id, message_id, screen_code):
        """Сохранить/обновить меню"""
        await db.execute("""
            INSERT INTO chat_menus (chat_id, user_id, menu_message_id, screen_code, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                menu_message_id = excluded.menu_message_id,
                screen_code = excluded.screen_code,
                updated_at = CURRENT_TIMESTAMP
        """, (chat_id, user_id, message_id, screen_code))
    
    async def get_menu(self, chat_id):
        """Получить меню из БД"""
        return await db.fetchone(
            "SELECT * FROM chat_menus WHERE chat_id = ?",
            (chat_id,)
        )
    
    async def delete_menu(self, chat_id):
        """Удалить меню"""
        await db.execute(
            "DELETE FROM chat_menus WHERE chat_id = ?",
            (chat_id,)
        )
```

### Шаг 3: Создать StaleButtonHandler

```python
# core/single_menu.py или отдельный файл

class StaleButtonHandler:
    @staticmethod
    async def handle(
        callback: CallbackQuery,
        state: FSMContext,
        required_fsm_keys: list[str],
        menu_manager: SingleMenuManager,
        fallback_handler,
        alert_text: str = "⚠️ Сессия устарела. Начните заново."
    ) -> bool:
        """Обработка устаревших кнопок"""
        data = await state.get_data()
        missing_keys = [key for key in required_fsm_keys if not data.get(key)]
        
        if missing_keys:
            try:
                await callback.answer(alert_text, show_alert=True)
            except:
                pass
            
            await state.clear()
            await fallback_handler(callback, state)
            logger.info(f"🔄 [SMP] Stale session reset: missing {missing_keys}")
            return True
        
        return False
```

### Шаг 4: Обновить handlers

```python
# app/handlers/common.py

# Вместо MenuManager -> используем SingleMenuManager
from core.single_menu import SingleMenuManager, StaleButtonHandler

menu_manager = SingleMenuManager(bot, db)

@router.callback_query(F.data == "mode_chat")
async def cb_mode_chat(callback, state):
    keyboard = create_keyboard(...)
    
    # 🆕 Добавить screen_code
    await menu_manager.navigate(
        callback=callback,
        state=state,
        screen_code='chat_mode',  # 🆕
        text="💬 Режим Диалога",
        keyboard=keyboard,
    )
```

### Шаг 5: Обработка устаревших кнопок

```python
# app/handlers/chat.py

@router.callback_query(F.data == "product_")  # Пример
async def handle_stale_product(callback, state):
    # Проверяем есть ли данные
    is_stale = await StaleButtonHandler.handle(
        callback=callback,
        state=state,
        required_fsm_keys=['product', 'chat_id'],
        menu_manager=menu_manager,
        fallback_handler=show_main_menu,
        alert_text="⚠️ Сессия истекла. Начните заново."
    )
    
    if not is_stale:
        # Есть данные, обработка продолжается
        await callback.answer()
```

---

## 📋 ЧЕКЛИСТ МИГРАЦИИ

### Фаза 1: Подготовка
- [ ] Прочитать документ SMP полностью
- [ ] Создать git branch `feature/smp-implementation`
- [ ] Создать core/single_menu.py
- [ ] Создать core/menu_database.py

### Фаза 2: БД
- [ ] Добавить миграцию для chat_menus
- [ ] Инициализировать MenuDatabase при запуске
- [ ] Протестировать save/get/delete

### Фаза 3: Менеджер
- [ ] Переименовать MenuManager → SingleMenuManager
- [ ] Добавить методы _find_menu_id, _try_edit, _create_new_menu
- [ ] Добавить обработку ошибок TelegramBadRequest
- [ ] Добавить screen_code во все методы

### Фаза 4: Обработчики
- [ ] Обновить common.py с screen_code
- [ ] Обновить chat.py с screen_code
- [ ] Добавить StaleButtonHandler
- [ ] Обновить все callback_query обработчики

### Фаза 5: Тестирование
- [ ] Тест: Создание меню
- [ ] Тест: Редактирование меню
- [ ] Тест: Навигация между экранами
- [ ] Тест: Перезапуск бота (восстановление из БД)
- [ ] Тест: Устаревшие кнопки
- [ ] Тест: Edge cases (удаленное сообщение, итд)

### Фаза 6: Документация
- [ ] Обновить UNIFIED_MENU.md
- [ ] Добавить примеры с screen_code
- [ ] Создать миграцию инструкции

---

## ⚡ БЫСТРАЯ МИГРАЦИЯ (1-2 часа)

Если нужно быстро:

1. Скопировать код SMP из документа
2. Добавить миграцию БД
3. Обновить handlers с screen_code
4. Протестировать

---

## 📈 РЕЗУЛЬТАТ ПОСЛЕ МИГРАЦИИ

### Статус: ✅ ПОЛНОЕ СООТВЕТСТВИЕ (100%)

**Получим:**
- ✅ Одно меню без дублей
- ✅ Автовосстановление после перезапуска
- ✅ Обработка устаревших кнопок
- ✅ screen_code для отладки
- ✅ Масштабируемая архитектура
- ✅ Production-ready код

**Улучшения:**
- 🎯 Меньше ошибок
- 📊 Лучше логирование
- 🚀 Быстрее разработка новых экранов
- 🐛 Легче отлаживать
- 💾 Меньше нагрузки на API Telegram

---

**Next: Начинать фазу 1 - создание core/single_menu.py**
