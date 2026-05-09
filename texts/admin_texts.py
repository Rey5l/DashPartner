admin_panel_text = """
🔐 <b>Админ панель</b>

Выберите раздел для управления:
"""


def render_admin_reserve_text(reserve: float) -> str:
    return f"""
💰 <b>Резерв системы</b>

Текущий резерв: <code>{reserve:.2f} ₽</code>

<i>Резерв рассчитывается как сумма всех балансов пользователей</i>
"""


def render_admin_statistics_text(stats: dict) -> str:
    return f"""
📊 <b>Статистика системы</b>

👥 Всего пользователей: <code>{stats['total_users']}</code>
💬 Подключено чатов: <code>{stats['connected_chats']}</code>
🎉 Активных конкурсов: <code>{stats['active_contests']}</code>

<i>Обновлено: {stats.get('updated_at', 'только что')}</i>
"""


def render_admin_withdrawals_text(withdrawals: list[dict]) -> str:
    if not withdrawals:
        return """
💸 <b>Заявки на вывод</b>

Нет активных заявок на вывод
"""

    lines = []
    for w in withdrawals:
        username = f"@{w['username']}" if w.get('username') else f"ID: {w['user_id']}"
        lines.append(
            f"<b>#{w['id']}</b> | {username} | <code>{w['amount']:.2f} ₽</code>"
        )

    withdrawals_list = "\n".join(lines)

    return f"""
💸 <b>Заявки на вывод</b>

{withdrawals_list}

<i>Нажмите на заявку для просмотра деталей</i>
"""


def render_admin_withdrawal_detail_text(withdrawal: dict) -> str:
    username = f"@{withdrawal['username']}" if withdrawal.get('username') else "не указан"
    full_name = withdrawal.get('full_name') or "не указано"

    return f"""
💸 <b>Заявка на вывод #{withdrawal['id']}</b>

<b>Пользователь:</b>
├ ID: <code>{withdrawal['user_id']}</code>
├ Username: {username}
└ Имя: {full_name}

<b>Сумма:</b> <code>{withdrawal['amount']:.2f} ₽</code>
<b>Статус:</b> <code>{withdrawal['status']}</code>
<b>Создана:</b> <code>{withdrawal['created_at']}</code>

<i>Выберите действие:</i>
"""


def render_admin_resources_text() -> str:
    return """
📢 <b>Управление ресурсами</b>

Здесь вы можете управлять партнерскими ресурсами системы

<i>Выберите действие:</i>
"""


def render_admin_resource_list_text(resources: list[dict]) -> str:
    if not resources:
        return """
📋 <b>Список ресурсов</b>

Ресурсы пока не добавлены
"""

    lines = []
    for resource in resources:
        lines.append(
            f"📢 <b>{resource['title']}</b>\n"
            f"   ├ URL: <code>{resource['url']}</code>\n"
            f"   └ Владелец: ID {resource['owner_user_id']}"
        )

    resources_list = "\n\n".join(lines)

    return f"""
📋 <b>Список ресурсов</b>

{resources_list}
"""


def render_admin_resource_stats_text(stats: dict) -> str:
    return f"""
📊 <b>Статистика ресурсов</b>

📢 Всего ресурсов: <code>{stats['total_resources']}</code>
👥 Уникальных владельцев: <code>{stats['unique_owners']}</code>

<i>Обновлено: только что</i>
"""


def render_admin_settings_text(chat_price: float, contest_price: float) -> str:
    return f"""
⚙️ <b>Настройки системы</b>

💵 Цена за подписку в чате: <code>{chat_price:.2f} ₽</code>
🎉 Цена за подписку в конкурсе: <code>{contest_price:.2f} ₽</code>

<i>Выберите параметр для изменения:</i>
"""


admin_settings_chat_price_text = """
💵 <b>Изменение цены за подписку в чате</b>

Отправьте новую цену в рублях (например: 0.8)
"""


admin_settings_contest_price_text = """
🎉 <b>Изменение цены за подписку в конкурсе</b>

Отправьте новую цену в рублях (например: 0.5)
"""


admin_resource_add_text = """
➕ <b>Добавление ресурса</b>

Отправьте название ресурса
"""
