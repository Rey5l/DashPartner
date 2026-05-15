main_text = """
<tg-emoji emoji-id="5436197886742247260">⚡️</tg-emoji>Dash — сервис для заработка на ОП в ваших ресурсах

<tg-emoji emoji-id="5337208927908016952">❓</tg-emoji>Популярные вопросы:

<tg-emoji emoji-id="5339513551524481000">🔵</tg-emoji>Что такое Dash?
<tg-emoji emoji-id="5339513551524481000">🔵</tg-emoji>Как начать зарабатывать?
<tg-emoji emoji-id="5339513551524481000">🔵</tg-emoji>Как вывести деньги?

<tg-emoji emoji-id="5436276364384677952">➡️</tg-emoji> Наши ресурсы:
Канал: @DashPartner
Сайт: DashPartner.ru
ТП: @TPDash
"""

def render_profile_text(stats: dict) -> str:
    return f"""<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji> <b>Ваш профиль</b>

<b><tg-emoji emoji-id="5244837092042750681">📈</tg-emoji> Доходы</b>
├ Всего заработано: <code>{stats.get('total_earned', 0.0):.2f} ₽</code>
└─ Накопленный бонус: <code>{stats.get('accumulated_bonus', 0.0):.2f} ₽</code>

<b><tg-emoji emoji-id="5246762912428603768">📉</tg-emoji> Расходы</b>
├ Потрачено на трафик: <code>{stats.get('spent_on_traffic', 0.0):.2f} ₽</code>
└ Выведено: <code>{stats.get('total_withdrawn', 0.0):.2f} ₽</code>

<b><tg-emoji emoji-id="5312057711091813718">💳</tg-emoji> Состояние счёта</b>
├ Баланс: <code>{stats.get('balance', 0.0):.2f} ₽</code>
└─ Пополнено: <code>{stats.get('total_topup', 0.0):.2f} ₽</code>

<b><tg-emoji emoji-id="5201691993775818138">🛫</tg-emoji> Вывод средств</b>
└ Доступно к выплате: <code>{stats.get('available_for_withdrawal', 0.0):.2f} ₽</code>
"""


sell_traffic_text = """
<tg-emoji emoji-id="5445221832074483553">💼</tg-emoji> Выберите формат, через который хотите продавать трафик.
"""


sell_traffic_chats_text = """
💬 Продажа трафика через чаты

1. Подключите бота в нужный чат.
2. Выдайте ему права администратора на удаление сообщений.
3. Пользователи чата смогут писать только после подписки на обязательные каналы.
"""


def render_chats_list_text(chats: list[dict]) -> str:
    total_chats = len(chats)
    active_chats = sum(1 for chat in chats if chat.get('gate_enabled'))
    total_tasks = sum(chat.get('completed_tasks', 0) for chat in chats)
    total_earned = sum(float(chat.get('earned_total', 0)) for chat in chats)

    stats_block = f"""<b>Общая статистика</b>

├ Всего чатов: <code>{total_chats}</code>
├ Активных: <code>{active_chats}</code>
├ Выполнено заданий: <code>{total_tasks}</code>
└ Заработано: <code>{total_earned:.2f} ₽</code>

"""

    return f"""💬 <b>Продажа в чатах</b>

Здесь можно настроить продажу трафика через чаты.

<blockquote><tg-emoji emoji-id="5343862721307748990">📉</tg-emoji> {stats_block}</blockquote>
<b>Обязательно подключите бота в чат <tg-emoji emoji-id="5440735760208637835">⬅️</tg-emoji></b>"""

def render_chat_settings_text(chat: dict) -> str:
    title = chat.get("chat_title") or str(chat["chat_id"])
    gate_status = "<tg-emoji emoji-id='5339112148175959615'>🟢</tg-emoji> Активен" if chat.get("gate_enabled") else "<tg-emoji emoji-id='5337017423906226569'>🔴</tg-emoji> Остановлен"
    completed_tasks = chat.get('completed_tasks', 0)
    earned_total = float(chat.get('earned_total', 0))

    return f"""<b>{title}</b>
<i>Тематика</i>: {chat.get("chat_category", "не указано")}
<i>Статус</i>: {gate_status}

<tg-emoji emoji-id="5193044820154687117">👥</tg-emoji> Выполнено заданий: <b>{completed_tasks}</b>
<tg-emoji emoji-id="5197620519398052697">💵</tg-emoji> Заработано: <b>{earned_total:.2f} ₽</b>"""


def render_contests_list_text(contests: list[dict], reward_per_subscription: float = 0.0) -> str:
    active_count = sum(1 for c in contests if c.get('status') == 'active')

    # Рассчитываем общий доход
    total_income = sum(
        c.get('participants_count', 0) * c.get('subscriptions_required', 1) * reward_per_subscription
        for c in contests
    )

    return f"""<blockquote expandable><b>🎉 Управление конкурсами</b>

Создавайте розыгрыши и привлекайте аудиторию через обязательные подписки</blockquote>

<b>Быстрая статистика:</b>
├ Активных конкурсов: <code>{active_count}</code>
└ Доход: <code>{total_income:.2f} ₽</code>

<i>Выберите действие ниже:</i>"""



def render_contests_manage_list_text(contests: list[dict]) -> str:
    # Фильтруем только активные конкурсы
    active_contests = [c for c in contests if c.get('status') == 'active']

    if not active_contests:
        return """<blockquote><b>📋 Активные конкурсы</b>

У вас пока нет активных конкурсов</blockquote>

<i>Создайте первый конкурс, чтобы начать привлекать аудиторию!</i>"""

    return """<blockquote><b>📋 Активные конкурсы</b>

Управляйте своими активными розыгрышами</blockquote>

<i>Выберите конкурс из списка ниже</i>"""


def render_contests_completed_list_text(contests: list[dict]) -> str:
    # Фильтруем только завершенные конкурсы
    completed_contests = [c for c in contests if c.get('status') == 'completed']

    if not completed_contests:
        return """<blockquote><b>✅ Завершенные конкурсы</b>

У вас пока нет завершенных конкурсов</blockquote>

<i>Завершенные конкурсы будут отображаться здесь</i>"""

    lines = []
    for idx, contest in enumerate(completed_contests, 1):
        lines.append(
            f"✅ <b>{contest['title']}</b>\n"
            f"   └ Участников: <code>{contest['participants_count']}</code>"
        )

    contests_list = "\n\n".join(lines)

    return f"""<blockquote><b>✅ Завершенные конкурсы</b>

Архив завершенных розыгрышей</blockquote>

{contests_list}

<i>Нажмите на конкурс для просмотра</i>"""


def render_contests_stats_text(contests: list[dict], reward_per_subscription: float = 0.0) -> str:
    if not contests:
        return """<b>📊 Статистика конкурсов</b>

У вас пока нет конкурсов

<i>Создайте первый конкурс, чтобы увидеть статистику!</i>"""

    total_participants = sum(contest.get('participants_count', 0) for contest in contests)
    total_winners = sum(contest.get('winners_count', 0) for contest in contests)
    active_contests = sum(1 for contest in contests if contest.get('status') == 'active')
    completed_contests = sum(1 for contest in contests if contest.get('status') == 'completed')

    # Рассчитываем общее количество подписок (участники * обязательные подписки)
    total_subscriptions = sum(
        contest.get('participants_count', 0) * contest.get('subscriptions_required', 1)
        for contest in contests
    )

    # Рассчитываем доход: участники * количество обязательных подписок * ставка
    total_income = sum(
        contest.get('participants_count', 0) * contest.get('subscriptions_required', 1) * reward_per_subscription
        for contest in contests
    )

    lines = []
    for contest in contests:
        status_emoji = "🟢" if contest.get('status') == 'active' else "✅"
        subscriptions = contest.get('participants_count', 0) * contest.get('subscriptions_required', 1)
        income = subscriptions * reward_per_subscription
        lines.append(
            f"{status_emoji} <b>{contest['title']}</b>\n"
            f"   ├ Участников: <code>{contest['participants_count']}</code>\n"
            f"   ├ Победителей: <code>{contest['winners_count']}</code>\n"
            f"   ├ Каналов: <code>{contest['channels_required_count']}</code>\n"
            f"   ├ Подписок: <code>{subscriptions}</code>\n"
            f"   └ Доход: <code>{income:.2f} ₽</code>"
        )

    contests_list = "\n\n".join(lines)

    return f"""<b><tg-emoji emoji-id="5343862721307748990">📊</tg-emoji> Статистика конкурсов</b>

Полная аналитика по всем розыгрышам

<blockquote><b>Общая статистика:</b>
├ Всего конкурсов: <code>{len(contests)}</code>
├ Активных: <code>{active_contests}</code>
├ Завершенных: <code>{completed_contests}</code>
├ Всего участников: <code>{total_participants}</code>
├ Заданий выполнено: <code>{total_subscriptions}</code>
└ 💰 <b>Общий доход: <code>{total_income:.2f} ₽</code></b></blockquote>

"""


def render_contest_card_text(contest: dict, invite_url: str | None = None) -> str:
    channel_lines = "\n".join(
        f"   ├ {channel['title']}"
        for channel in contest.get("channels", [])
    ) or "   └ Каналы пока не добавлены"

    # Добавляем последний канал с другим символом
    if contest.get("channels"):
        channels = contest.get("channels", [])
        channel_lines = "\n".join(
            f"   {'├' if i < len(channels) - 1 else '└'} {channel['title']}"
            for i, channel in enumerate(channels)
        )

    status_emoji = "🟢" if contest.get('status') == 'active' else "✅"
    winners = contest.get("winners") or []

    if winners:
        winners_line = "\n".join(
            f"   {'├' if i < len(winners) - 1 else '└'} {winner.get('participant_full_name') or winner.get('participant_user_id')}"
            for i, winner in enumerate(winners)
        )
    else:
        winners_line = "   └ Победители еще не выбраны"

    # Определяем условие завершения
    completion_type = contest.get('completion_type', 'manual')
    if completion_type == 'timer':
        time_hours = contest.get('time_limit_minutes', 1440) // 60
        time_minutes = contest.get('time_limit_minutes', 1440) % 60
        if time_hours > 0 and time_minutes > 0:
            completion_display = f"⏱ По таймеру ({time_hours}ч {time_minutes}м)"
        elif time_hours > 0:
            completion_display = f"⏱ По таймеру ({time_hours}ч)"
        else:
            completion_display = f"⏱ По таймеру ({time_minutes}м)"
    elif completion_type == 'participants':
        completion_display = f"👥 По участникам ({contest.get('participants_limit', 0)} чел.)"
    else:
        completion_display = "—"

    share_block = f"\n\n<blockquote><b>🔗 Ссылка для участия:</b>\n<code>{invite_url}</code></blockquote>" if invite_url else ""

    return f"""<blockquote expandable><b>🎉 {contest['title']}</b>

Управление розыгрышем</blockquote>

<b>Основная информация:</b>
├ Статус: {status_emoji} <code>{contest['status']}</code>
├ Участников: <code>{contest['participants_count']}</code>
├ Победителей: <code>{contest['winners_count']}</code>
├ Требуемых подписок: <code>{contest.get('subscriptions_required', 1)}</code>
├ Завершение: <code>{completion_display}</code>
└ Обязательных каналов: <code>{contest['channels_required_count']}</code>

<b>Победители:</b>
{winners_line}{share_block}"""


def render_contest_join_text(contest: dict, already_joined: bool) -> str:
    status_line = "Вы уже участвуете в этом конкурсе." if already_joined else "Подпишитесь на каналы ниже и подтвердите участие."
    return f"""
🎉 {contest['title']}

Победителей: {contest['winners_count']}
Участников сейчас: {contest['participants_count']}
Статус: {contest['status']}

{status_line}
"""


def render_resources_list_text(resources: list[dict]) -> str:
    if not resources:
        return """<blockquote><b>📢 Мои ресурсы</b>

У вас пока нет добавленных ресурсов</blockquote>

<i>Добавьте свои каналы, чтобы использовать их при создании конкурсов!</i>"""

    return """<blockquote><b>📢 Мои ресурсы</b>

Управляйте своими каналами для конкурсов</blockquote>

<i>Выберите ресурс из списка ниже</i>"""


def render_resource_card_text(resource: dict) -> str:
    return f"""<blockquote><b>📢 {resource['title']}</b>

Информация о ресурсе</blockquote>

<b>Ссылка:</b> <code>{resource['url']}</code>
<b>Добавлен:</b> <code>{resource['created_at'][:10]}</code>"""


contest_create_intro_text = """
Создание конкурса началось.

Отправьте название конкурса. Это название будет видно 
"""

contest_create_post_text = """
Теперь отправьте ссылку на пост с конкурсом в канале.
"""

contest_create_winners_text = """
Сколько победителей будет в конкурсе? Отправьте число.
"""

contest_create_channels_count_text = """
Сколько обязательных каналов нужно для подписки? Отправьте число.

Бот автоматически подберет нужное количество каналов с сервера заданий.
"""


subscription_required_text = """
Чтобы писать в этом чате, сначала подпишитесь на обязательные каналы ниже.

После подписки нажмите «Проверить подписку».
"""


subscription_success_text = """
Подписка подтверждена. Теперь вы можете писать в чат.
"""


def render_chat_tasks_text(user_name: str, user_id: int) -> str:
    return f"""<tg-emoji emoji-id="5472279086657199080">📢</tg-emoji> <a href="tg://user?id={user_id}"><b>{user_name}</b></a>, подпишитесь на спонсоров ниже, чтобы писать в чат.
"""


cabinet_text = """<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji> <b>Кабинет</b>

Выберите нужный раздел."""


def render_referral_text(user_id: int, referrals_count: int = 0, referral_earnings: float = 0.0, referral_link: str = "") -> str:
    return f"""👥 <b>Реферальная программа</b>

Приглашайте новых владельцев чатов и получайте 5% от их заработка!
Бонус начисляется автоматически при выводе и пополнении средств рефералом.

📈 <b>Ваша статистика:</b>
├ Приглашено: <code>{referrals_count}</code> чел.
└ Заработано: <code>{referral_earnings:.2f} ₽</code>

🔗 <b>Ваша ссылка:</b>
<code>{referral_link}</code>"""


about_service_text = """🌐 <b>О сервисе</b>

Piar Flow — экосистема для продвижения в Telegram. Сервис объединяет рекламодателей и исполнителей, помогает запускать рекламные задания и получать целевой трафик для Telegram-проектов.

Цель сервиса — сделать продвижение доступным, прозрачным и автоматизированным.

Выберите нужный раздел."""

