from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Профиль", callback_data="profile")],
            [
                InlineKeyboardButton(text="Продать трафик", callback_data="sell_traffic"),
                InlineKeyboardButton(text="Купить трафик", callback_data="buy_traffic"),
            ],
            [InlineKeyboardButton(text="Кабинет", callback_data="cabinet")],
        ]
    )
    return keyboard


def get_profile_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Вывод", callback_data="withdraw"), InlineKeyboardButton(text="Пополнить", callback_data="topup")],
            [InlineKeyboardButton(text="Мои транзакции", callback_data="my_transanctions")],
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ]
    )
    return keyboard


def get_sell_traffic_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Чаты", callback_data="sell_traffic_chats", icon_custom_emoji_id="5443038326535759644", style='primary')],
            [InlineKeyboardButton(text="Боты", callback_data="sell_traffic_bots", icon_custom_emoji_id="5332724926216428039")],
            [InlineKeyboardButton(text="Конкурсы", callback_data="sell_traffic_contests", icon_custom_emoji_id="5305699699204837855")],
            [InlineKeyboardButton(text="Назад", callback_data="back", icon_custom_emoji_id="5386716938619604706")],
        ]
    )
    return keyboard


def get_sell_traffic_chats_keyboard(bot_username: str | None):
    inline_keyboard = []

    if bot_username:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="Подключить бота в чат",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ]
        )

    inline_keyboard.append(
        [InlineKeyboardButton(text="Назад", callback_data="sell_traffic")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    return keyboard


def get_chats_list_keyboard(chats: list[dict], bot_username: str | None):
    inline_keyboard = []

    if bot_username:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text="Подключить бота в чат",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ]
        )

    for chat in chats:
        title = chat.get("chat_title") or str(chat.get("chat_id"))
        status = "🟢" if chat.get("gate_enabled") else "🔴"
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{title} {status}",
                    callback_data=f"chat_card:{chat['chat_id']}",
                )
            ]
        )

    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_chat_settings_keyboard(chat_id: int, gate_enabled: bool):
    toggle_text = "Остановить" if gate_enabled else "Запустить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data=f"chat_card:{chat_id}")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"chat_settings:{chat_id}")],
            [
                InlineKeyboardButton(
                    text=f"⏸️ {toggle_text}" if gate_enabled else f"▶️ {toggle_text}",
                    style="danger" if gate_enabled else "success",
                    callback_data=f"toggle_chat_gate:{chat_id}",
                )
            ],
            [InlineKeyboardButton(text="Назад", callback_data="sell_traffic")],
        ]
    )


def get_contests_list_keyboard(contests: list[dict]):
    inline_keyboard = [
        [InlineKeyboardButton(text="Создать конкурс", callback_data="contest_create", style="success", icon_custom_emoji_id="5443127283898405358")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="contest_stats")],
        [InlineKeyboardButton(text="📋 Список конкурсов", callback_data="contest_list")],
        [InlineKeyboardButton(text="📢 Мои ресурсы", callback_data="my_resources")]
    ]

    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_resources_list_keyboard(resources: list[dict]):
    inline_keyboard = [
        [InlineKeyboardButton(text="➕ Добавить ресурс", callback_data="resource_add")]
    ]

    for resource in resources:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🟢 {resource['title']}",
                    callback_data=f"resource_view:{resource['id']}",
                )
            ]
        )

    inline_keyboard.append([InlineKeyboardButton(text="К конкурсам", callback_data="sell_traffic_contests")])
    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_resource_manage_keyboard(resource_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"resource_delete:{resource_id}")],
            [InlineKeyboardButton(text="К списку ресурсов", callback_data="my_resources")],
            [InlineKeyboardButton(text="Назад", callback_data="sell_traffic")]
        ]
    )


def get_contests_manage_list_keyboard(contests: list[dict]):
    inline_keyboard = []

    # Фильтруем только активные конкурсы
    active_contests = [c for c in contests if c.get('status') == 'active']

    for contest in active_contests:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{contest['title']} ({contest['participants_count']})",
                    callback_data=f"contest_view:{contest['id']}",
                )
            ]
        )

    inline_keyboard.append([InlineKeyboardButton(text="К конкурсам", callback_data="sell_traffic_contests")])
    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_contests_completed_list_keyboard(contests: list[dict]):
    inline_keyboard = []

    # Фильтруем только завершенные конкурсы
    completed_contests = [c for c in contests if c.get('status') == 'completed']

    for contest in completed_contests:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{contest['title']} ({contest['participants_count']})",
                    callback_data=f"contest_view:{contest['id']}",
                )
            ]
        )

    inline_keyboard.append([InlineKeyboardButton(text="К конкурсам", callback_data="sell_traffic_contests")])
    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_contests_stats_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="К списку конкурсов", callback_data="sell_traffic_contests")],
            [InlineKeyboardButton(text="Назад", callback_data="sell_traffic")]
        ]
    )


def get_contest_manage_keyboard(contest_id: int, invite_url: str | None, contest_status: str = 'active'):
    inline_keyboard = []
    if invite_url:
        inline_keyboard.append([InlineKeyboardButton(text="Ссылка участия", url=invite_url)])

    if contest_status == 'active':
        inline_keyboard.append([InlineKeyboardButton(text="🏁 Завершить вручную", callback_data=f"contest_draw:{contest_id}", style="danger")])

    inline_keyboard.append([InlineKeyboardButton(text="К списку конкурсов", callback_data="sell_traffic_contests")])
    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="sell_traffic")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_contest_join_keyboard(contest_id: int, channels: list[dict], already_joined: bool):
    inline_keyboard = []
    for channel in channels:
        inline_keyboard.append([InlineKeyboardButton(text=channel["title"], url=channel["url"])])

    if already_joined:
        inline_keyboard.append([InlineKeyboardButton(text="Вы уже участвуете", callback_data="contest_joined_info")])
    else:
        inline_keyboard.append([InlineKeyboardButton(text="Проверить подписки и участвовать", callback_data=f"contest_join:{contest_id}")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_subscription_keyboard(tasks: list[dict[str, str]]):
    inline_keyboard = []

    # Группируем задания по две кнопки в ряд
    for i in range(0, len(tasks), 2):
        row = []
        for j in range(2):
            if i + j < len(tasks):
                task = tasks[i + j]
                action_text = "Подписаться" if task.get("target_type") == "channel" else "Перейти"
                row.append(InlineKeyboardButton(text=action_text, url=task["url"], icon_custom_emoji_id="5271604874419647061"))
        inline_keyboard.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    return keyboard


def get_chat_settings_menu_keyboard(chat_id: int):
    """Клавиатура меню настроек чата"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Макс. количество спонсоров", callback_data=f"chat_choose_sponsors:{chat_id}")],
            [InlineKeyboardButton(text="⏱ Время сброса подписки", callback_data=f"chat_choose_reset:{chat_id}")],
            [InlineKeyboardButton(text="🗑 Удаление сообщения бота", callback_data=f"chat_choose_delete:{chat_id}")],
            [InlineKeyboardButton(text="Назад к чату", callback_data=f"chat_card:{chat_id}")],
        ]
    )


def get_chat_sponsors_keyboard(chat_id: int, current_value: int):
    """Клавиатура выбора количества спонсоров"""
    inline_keyboard = []

    row = []
    for i in range(1, 11):
        marker = "✅" if i == current_value else ""
        row.append(InlineKeyboardButton(text=f"{i} {marker}", callback_data=f"chat_sponsors:{chat_id}:{i}"))
        if len(row) == 5:
            inline_keyboard.append(row)
            row = []

    if row:
        inline_keyboard.append(row)

    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data=f"chat_settings:{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_chat_reset_time_keyboard(chat_id: int, current_minutes: int):
    """Клавиатура выбора времени сброса подписки"""
    options = [
        (15, "15 минут"),
        (30, "30 минут"),
        (60, "1 час"),
        (180, "3 часа"),
        (360, "6 часов"),
        (720, "12 часов"),
    ]

    inline_keyboard = []
    for minutes, label in options:
        marker = "✅" if minutes == current_minutes else ""
        inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{label} {marker}",
                callback_data=f"chat_reset:{chat_id}:{minutes}"
            )
        ])

    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data=f"chat_settings:{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_chat_bot_delete_keyboard(chat_id: int, current_seconds: int):
    """Клавиатура выбора времени удаления сообщения бота"""
    options = [
        (20, "20 секунд"),
        (30, "30 секунд"),
        (40, "40 секунд"),
        (60, "1 минута"),
        (90, "1.5 минуты"),
        (120, "2 минуты"),
    ]

    inline_keyboard = []
    for seconds, label in options:
        marker = "✅" if seconds == current_seconds else ""
        inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{label} {marker}",
                callback_data=f"chat_delete:{chat_id}:{seconds}"
            )
        ])

    inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data=f"chat_settings:{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


def get_contest_cancel_keyboard():
    """Клавиатура с кнопкой отмены создания конкурса"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
        ]
    )
