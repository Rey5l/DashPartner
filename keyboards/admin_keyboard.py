from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_panel_keyboard():
    """Главное меню админ панели"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс резерва", callback_data="admin_reserve")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_statistics")],
            [InlineKeyboardButton(text="🧾 Заявки на вывод", callback_data="admin_withdrawals")],
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

