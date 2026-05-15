from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_panel_keyboard():
    """Главное меню админ панели"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс резерва", callback_data="admin_reserve")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_statistics")],
            [InlineKeyboardButton(text="🧾 Заявки на вывод", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="✅ Модерация ресурсов", callback_data="admin_moderation")],
            [InlineKeyboardButton(text="💬 Модерация чатов", callback_data="admin_moderation_chats")],
            [InlineKeyboardButton(text="📢 Ресурсы", callback_data="admin_resources")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        ]
    )


def get_admin_resources_keyboard():
    """Меню управления ресурсами"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ресурс", callback_data="admin_resource_add")],
            [InlineKeyboardButton(text="📋 Список ресурсов", callback_data="admin_resource_list")],
            [InlineKeyboardButton(text="📊 Статистика ресурсов", callback_data="admin_resource_stats")],
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
        ]
    )


def get_admin_settings_keyboard():
    """Меню настроек"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Цена за подписку в чате", callback_data="admin_settings_chat_price")],
            [InlineKeyboardButton(text="🎉 Цена за подписку в конкурсе", callback_data="admin_settings_contest_price")],
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
        ]
    )


def get_admin_back_keyboard():
    """Кнопка назад в админ панель"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
        ]
    )


def get_withdrawal_action_keyboard(withdrawal_id: int):
    """Кнопки действий для заявки на вывод"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin_withdrawal_approve:{withdrawal_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_withdrawal_reject:{withdrawal_id}"),
            ],
            [InlineKeyboardButton(text="К списку заявок", callback_data="admin_withdrawals")],
            [InlineKeyboardButton(text="Назад", callback_data="admin_panel")],
        ]
    )


def get_moderation_actions_keyboard(resource_id: int):
    """Клавиатура с действиями Принять/Отклонить"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"mod_accept:{resource_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_decline:{resource_id}"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_moderation")],
        ]
    )


def get_category_keyboard(resource_id: int):
    """Клавиатура с выбором категории"""
    categories = [
        ("Другое", "other"),
        ("Новости", "news"),
        ("Блоги", "blogs"),
        ("Сайты", "sites"),
        ("Полезное", "useful"),
        ("Знакомство", "dating"),
        ("Заработок", "earnings"),
        ("Общение", "communication"),
        ("Криптовалюты", "crypto"),
        ("Старсы/НФТ", "stars_nft"),
        ("Развлечения", "entertainment"),
        ("Познавательное", "educational"),
        ("Экономика", "economy"),
        ("Музыка", "music"),
        ("Технология", "technology"),
        ("Психология", "psychology"),
        ("Женское", "women"),
        ("Мужское", "men"),
        ("Творчество и дизайн", "creative"),
        ("Нейросети", "ai"),
        ("Астрология", "astrology"),
        ("Спамные", "spam"),
        ("Авто", "auto"),
        ("Здоровье", "health"),
        ("Чаты", "chats"),
        ("Путешествия", "travel"),
        ("Военное", "military"),
        ("Спорт", "sport"),
        ("Стикеры/темы", "stickers"),
        ("Игры", "games"),
        ("Кино", "cinema"),
        ("Видео", "video"),
        ("Инструменты", "tools"),
        ("Кулинария", "cooking"),
    ]

    keyboard = []
    for i in range(0, len(categories), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=categories[i][0],
            callback_data=f"mod_category:{resource_id}:{categories[i][1]}"
        ))
        if i + 1 < len(categories):
            row.append(InlineKeyboardButton(
                text=categories[i + 1][0],
                callback_data=f"mod_category:{resource_id}:{categories[i + 1][1]}"
            ))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"mod_view:{resource_id}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_chat_moderation_actions_keyboard(chat_id: int):
    """Клавиатура с действиями Принять/Отклонить для чата"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"chat_mod_accept:{chat_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"chat_mod_decline:{chat_id}"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_moderation_chats")],
        ]
    )


def get_chat_category_keyboard(chat_id: int):
    """Клавиатура с выбором категории для чата"""
    categories = [
        ("Другое", "other"),
        ("Новости", "news"),
        ("Блоги", "blogs"),
        ("Сайты", "sites"),
        ("Полезное", "useful"),
        ("Знакомство", "dating"),
        ("Заработок", "earnings"),
        ("Общение", "communication"),
        ("Криптовалюты", "crypto"),
        ("Старсы/НФТ", "stars_nft"),
        ("Развлечения", "entertainment"),
        ("Познавательное", "educational"),
        ("Экономика", "economy"),
        ("Музыка", "music"),
        ("Технология", "technology"),
        ("Психология", "psychology"),
        ("Женское", "women"),
        ("Мужское", "men"),
        ("Творчество и дизайн", "creative"),
        ("Нейросети", "ai"),
        ("Астрология", "astrology"),
        ("Спамные", "spam"),
        ("Авто", "auto"),
        ("Здоровье", "health"),
        ("Чаты", "chats"),
        ("Путешествия", "travel"),
        ("Военное", "military"),
        ("Спорт", "sport"),
        ("Стикеры/темы", "stickers"),
        ("Игры", "games"),
        ("Кино", "cinema"),
        ("Видео", "video"),
        ("Инструменты", "tools"),
        ("Кулинария", "cooking"),
    ]

    keyboard = []
    for i in range(0, len(categories), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=categories[i][0],
            callback_data=f"chat_mod_category:{chat_id}:{categories[i][1]}"
        ))
        if i + 1 < len(categories):
            row.append(InlineKeyboardButton(
                text=categories[i + 1][0],
                callback_data=f"chat_mod_category:{chat_id}:{categories[i + 1][1]}"
            ))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"chat_mod_view:{chat_id}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


