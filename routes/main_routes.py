import os
import asyncio
from urllib.parse import urlparse

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus

from keyboards.main_keyboard import (
    get_chat_settings_keyboard,
    get_chat_settings_menu_keyboard,
    get_chat_sponsors_keyboard,
    get_chat_reset_time_keyboard,
    get_chat_bot_delete_keyboard,
    get_chats_list_keyboard,
    get_contest_join_keyboard,
    get_contest_manage_keyboard,
    get_contests_list_keyboard,
    get_contests_manage_list_keyboard,
    get_contests_stats_keyboard,
    get_contest_cancel_keyboard,
    get_main_keyboard,
    get_profile_keyboard,
    get_resource_manage_keyboard,
    get_resources_list_keyboard,
    get_sell_traffic_keyboard,
    get_subscription_keyboard,
)
from keyboards.reply_keyboard import get_admin_reply_keyboard, get_user_reply_keyboard
from config import ADMIN_IDS
from services.database_service import DatabaseService
from services.partner_store import PartnerStore
from services.task_service import get_aggregated_tasks
from services.subscription_checker import subscription_checker
from texts.main_texts import (
    render_chat_tasks_text,
    main_text,
    render_chat_settings_text,
    render_chats_list_text,
    render_contest_card_text,
    render_contest_join_text,
    render_contests_list_text,
    render_contests_manage_list_text,
    render_contests_stats_text,
    render_profile_text,
    render_resource_card_text,
    render_resources_list_text,
    sell_traffic_text,
    subscription_success_text,
)

router = Router()
partner_store = PartnerStore()
database = DatabaseService()


class ContestCreateStates(StatesGroup):
    waiting_title = State()
    waiting_post_text = State()
    waiting_media = State()
    waiting_button_text = State()
    waiting_entry_filter = State()
    waiting_unsubscribe_action = State()
    waiting_winners_count = State()
    waiting_completion_type = State()
    waiting_channel = State()


class ResourceAddStates(StatesGroup):
    waiting_url = State()


async def get_flyer_tasks_for_user(user_id: int, language_code: str | None):
    tasks = await get_aggregated_tasks(
        user_id=user_id,
        language_code=language_code or "ru",
        store=partner_store,
    )
    print(
        f"[ROUTES] aggregated tasks for user_id={user_id}, language_code={language_code}: "
        f"count={len(tasks)}"
    )
    prepared_tasks = []
    for task in tasks:
        if not task.get("url"):
            continue

        source = task.get("source")
        task_key = None
        if source == "tgrass":
            task_key = task.get("offer_id") or task.get("id")
        elif source == "flyer":
            task_key = task.get("signature") or task.get("id")
        elif source == "local":
            task_key = task.get("id")

        prepared_tasks.append(
            {
                "title": task.get("title") or "Открыть задание",
                "url": task.get("url"),
                "signature": task.get("signature"),
                "offer_id": task.get("offer_id"),
                "target_type": task.get("target_type"),
                "source": source,
                "task_key": str(task_key) if task_key is not None else None,
            }
        )

    return prepared_tasks


async def is_user_subscribed(user_id: int, language_code: str | None) -> bool:
    tasks = await get_flyer_tasks_for_user(user_id, language_code)
    print(
        f"[ROUTES] subscription check for user_id={user_id}, language_code={language_code}: "
        f"pending_tasks={len(tasks)}"
    )
    return len(tasks) == 0


async def grant_chat_access(chat_id: int, member_user_id: int) -> tuple[bool, bool]:
    access_created = database.approve_member(chat_id=chat_id, member_user_id=member_user_id)
    print(
        f"[DB] grant_chat_access: chat_id={chat_id}, member_user_id={member_user_id}, "
        f"access_created={access_created}"
    )
    return access_created, False


async def get_bot_username(callback: CallbackQuery) -> str | None:
    bot_username = os.getenv("BOT_USERNAME")
    if bot_username:
        return bot_username

    me = await callback.bot.get_me()
    return me.username


async def show_user_chats(callback: CallbackQuery) -> None:
    chats = database.list_owner_chats(callback.from_user.id)
    bot_username = await get_bot_username(callback)
    await callback.message.edit_text(
        text=render_chats_list_text(chats),
        parse_mode="HTML",
        reply_markup=get_chats_list_keyboard(chats, bot_username),
    )


async def get_bot_start_url(message_or_callback: Message | CallbackQuery, start_param: str) -> str | None:
    bot_username = os.getenv("BOT_USERNAME")
    if not bot_username:
        bot = message_or_callback.bot if isinstance(message_or_callback, CallbackQuery) else message_or_callback.bot
        me = await bot.get_me()
        bot_username = me.username

    if not bot_username:
        return None

    return f"https://t.me/{bot_username}?start={start_param}"


async def show_user_contests(callback: CallbackQuery) -> None:
    contests = database.list_owner_contests(callback.from_user.id)
    user_stats = database.get_user_stats(callback.from_user.id)
    reward_per_subscription = user_stats.get('reward_per_subscription', 0.0)
    await callback.message.edit_text(
        text=render_contests_list_text(contests, reward_per_subscription),
        parse_mode="HTML",
        reply_markup=get_contests_list_keyboard(contests),
    )


async def show_user_contests_manage_list(callback: CallbackQuery) -> None:
    contests = database.list_owner_contests(callback.from_user.id)
    print(f"[CONTEST] show_user_contests_manage_list: user_id={callback.from_user.id}, contests_count={len(contests)}")
    for c in contests:
        print(f"[CONTEST]   - ID: {c['id']}, Title: {c['title']}, Status: {c['status']}")
    await callback.message.edit_text(
        text=render_contests_manage_list_text(contests),
        parse_mode="HTML",
        reply_markup=get_contests_manage_list_keyboard(contests),
    )


def parse_telegram_target(url: str) -> str | int | None:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return None

    parts = [part for part in path.split("/") if part]
    if not parts:
        return None

    if parts[0] == "c" and len(parts) >= 2:
        return int(f"-100{parts[1]}")

    if parts[0].startswith("+"):
        return None

    return f"@{parts[0]}"


def parse_telegram_post(url: str) -> tuple[str | int | None, int | None]:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return None, None

    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return None, None

    try:
        message_id = int(parts[-1])
    except ValueError:
        return None, None

    if parts[0] == "c" and len(parts) >= 3:
        return int(f"-100{parts[1]}"), message_id

    return f"@{parts[0]}", message_id


async def publish_contest_button(target: Message | CallbackQuery, contest: dict, invite_url: str | None) -> bool:
    if not invite_url:
        return False

    # Try using new fields first (contest_channel_id and posted_message_id)
    if contest.get("contest_channel_id") and contest.get("posted_message_id"):
        try:
            channel_id = contest["contest_channel_id"]
            message_id = contest["posted_message_id"]
            
            await target.bot.edit_message_reply_markup(
                chat_id=channel_id,
                message_id=message_id,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Участвовать", url=invite_url)]]
                ),
            )
            return True
        except Exception as error:
            print(
                f"[CONTEST] failed to update contest button: contest_id={contest['id']}, "
                f"channel_id={contest.get('contest_channel_id')}, message_id={contest.get('posted_message_id')}, error={error}"
            )
            return False
    
    # Fallback to old post_url method for backwards compatibility
    if contest.get("post_url"):
        chat_ref, message_id = parse_telegram_post(contest["post_url"])
        if chat_ref is None or message_id is None:
            return False

        try:
            await target.bot.edit_message_reply_markup(
                chat_id=chat_ref,
                message_id=message_id,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="Участвовать", url=invite_url)]]
                ),
            )
            return True
        except Exception as error:
            print(
                f"[CONTEST] failed to publish contest button: contest_id={contest['id']}, "
                f"chat_ref={chat_ref}, message_id={message_id}, error={error}"
            )
            return False
    
    return False


async def verify_contest_channels(bot, contest: dict, user_id: int) -> tuple[bool, list[dict]]:
    not_joined = []

    # Check if user is subscribed to required contest channels
    for channel in contest.get("channels", []):
        url = channel["url"]

        # Пропускаем не-Telegram каналы
        if not (url.startswith("@") or "t.me/" in url or "telegram.me/" in url):
            print(f"[CONTEST] skipping non-telegram channel: {url}")
            continue

        target = parse_telegram_target(url)
        if target is None:
            print(f"[CONTEST] failed to parse telegram target: {url}")
            continue

        try:
            member = await bot.get_chat_member(chat_id=target, user_id=user_id)
            if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
                not_joined.append(channel)
        except Exception as error:
            print(
                f"[CONTEST] failed to verify contest channel: contest_id={contest['id']}, "
                f"user_id={user_id}, channel={url}, error={error}"
            )
            not_joined.append(channel)

    return len(not_joined) == 0, not_joined


def get_context_chat_id(target: Message | CallbackQuery) -> int | None:
    if isinstance(target, CallbackQuery):
        return target.message.chat.id if target.message else None
    return target.chat.id


def is_group_chat_id(chat_id: int | None) -> bool:
    return chat_id is not None and chat_id < 0


async def sync_tasks_for_chat_user(chat_id: int | None, member_user_id: int, tasks: list[dict]) -> None:
    if not is_group_chat_id(chat_id):
        return

    synced = database.register_task_assignments(chat_id=chat_id, member_user_id=member_user_id, tasks=tasks)
    print(
        f"[DB] synced task assignments: chat_id={chat_id}, member_user_id={member_user_id}, synced={synced}"
    )


async def reward_completed_chat_tasks(chat_id: int | None, member_user_id: int, pending_tasks: list[dict]) -> dict:
    if not is_group_chat_id(chat_id):
        return {"count": 0, "amount": 0.0}

    result = database.reward_tasks_not_in_pending(
        chat_id=chat_id,
        member_user_id=member_user_id,
        pending_tasks=pending_tasks,
    )
    print(
        f"[DB] reward_completed_chat_tasks: chat_id={chat_id}, member_user_id={member_user_id}, "
        f"count={result['count']}, amount={result['amount']}"
    )
    return result


async def handle_subscription_update(user_id: int, language_code: str | None, remaining_tasks: list[dict]):
    print(
        f"[ROUTES] subscription update: user_id={user_id}, remaining_tasks={len(remaining_tasks)}"
    )

    if not remaining_tasks:
        print(f"[ROUTES] all tasks completed for user_id={user_id}")


async def delete_message_after_delay(message: Message, delay_seconds: int):
    """Удаляет сообщение через заданное количество секунд"""
    try:
        await asyncio.sleep(delay_seconds)
        await message.delete()
        print(f"[ROUTES] Deleted message {message.message_id} after {delay_seconds} seconds")
    except Exception as e:
        print(f"[ROUTES] Failed to delete message {message.message_id}: {e}")


async def send_chat_subscription_tasks(target: Message | CallbackQuery, user_id: int, language_code: str | None):
    chat_id = get_context_chat_id(target)

    # Получаем настройки чата для ограничения количества заданий
    chat_settings = None
    if chat_id and is_group_chat_id(chat_id):
        # Находим владельца чата
        chat_runtime = database.get_chat_runtime(chat_id)
        if chat_runtime:
            chat_settings = database.get_chat_settings(chat_runtime['owner_user_id'], chat_id)

    tasks = await get_flyer_tasks_for_user(user_id, language_code)

    # Ограничиваем количество заданий согласно настройкам чата
    if chat_settings and chat_settings.get('max_sponsors'):
        max_sponsors = chat_settings['max_sponsors']
        tasks = tasks[:max_sponsors]

    print(
        f"[ROUTES] sending chat subscription tasks: user_id={user_id}, "
        f"language_code={language_code}, count={len(tasks)}"
    )
    await sync_tasks_for_chat_user(
        chat_id=chat_id,
        member_user_id=user_id,
        tasks=tasks,
    )

    if not tasks:
        if isinstance(target, CallbackQuery):
            await target.message.answer(subscription_success_text, parse_mode="HTML")
        else:
            await target.answer(subscription_success_text, parse_mode="HTML")
        return True

    # Получаем имя пользователя
    user = target.from_user if isinstance(target, Message) else target.from_user
    user_name = user.full_name or user.first_name or f"@{user.username}" if user.username else "Пользователь"

    if isinstance(target, CallbackQuery):
        sent_message = await target.message.answer(
            text=render_chat_tasks_text(user_name, user_id),
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(tasks),
        )
    else:
        sent_message = await target.answer(
            text=render_chat_tasks_text(user_name, user_id),
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(tasks),
        )

    # Удаляем сообщение через заданное время
    if chat_settings and chat_settings.get('bot_message_delete_seconds'):
        delete_seconds = chat_settings['bot_message_delete_seconds']
        asyncio.create_task(delete_message_after_delay(sent_message, delete_seconds))

    async def on_check_complete(uid: int, lang: str | None, remaining: list[dict]):
        chat_id = get_context_chat_id(target)

        await reward_completed_chat_tasks(
            chat_id=chat_id,
            member_user_id=uid,
            pending_tasks=remaining,
        )

        await sync_tasks_for_chat_user(
            chat_id=chat_id,
            member_user_id=uid,
            tasks=remaining,
        )

        if not remaining:
            if chat_id and is_group_chat_id(chat_id):
                await grant_chat_access(chat_id=chat_id, member_user_id=uid)

            try:
                await sent_message.reply(subscription_success_text, parse_mode="HTML")
            except Exception as e:
                print(f"[ROUTES] failed to send completion message: {e}")

    asyncio.create_task(
        subscription_checker.start_checking(
            user_id=user_id,
            language_code=language_code,
            tasks=tasks,
            on_complete=on_check_complete,
        )
    )

    return False


@router.message(Command("start"))
async def start(message: Message):
    start_parts = (message.text or "").split(maxsplit=1)
    if len(start_parts) > 1 and start_parts[1].startswith("contest_"):
        raw_contest_id = start_parts[1].split("contest_", 1)[1]
        try:
            contest_id = int(raw_contest_id)
        except ValueError:
            await message.answer("Некорректная ссылка конкурса.")
            return

        contest = database.get_contest(contest_id)
        if contest is None or contest.get("status") != "active":
            await message.answer("Конкурс не найден или уже недоступен.")
            return

        already_joined = database.is_contest_participant(contest_id, message.from_user.id)
        if already_joined:
            await message.answer(
                text=render_contest_join_text(contest, already_joined=True),
                parse_mode="HTML",
            )
            return

        # Получаем партнерские задания для этого участника
        channels = await get_flyer_tasks_for_user(
            user_id=message.from_user.id,
            language_code=message.from_user.language_code,
        )

        # Фильтруем только Telegram-каналы
        contest_channels = []
        for item in channels:
            if item.get("target_type") == "channel" and item.get("url"):
                url = item["url"]
                # Проверяем, что это действительно Telegram-канал
                if url.startswith("@") or "t.me/" in url or "telegram.me/" in url:
                    contest_channels.append({"title": item["title"], "url": url})

        # Берем нужное количество каналов согласно subscriptions_required
        subscriptions_required = contest.get("subscriptions_required", 1)
        contest_channels = contest_channels[:subscriptions_required]

        if not contest_channels:
            await message.answer("В данный момент нет доступных заданий для участия в конкурсе. Попробуйте позже.")
            return

        await message.answer(
            f"<tg-emoji emoji-id='5339151799314034719'>⌛</tg-emoji> Для участия подпишитесь на спонсоров ниже:\n",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(
                [{"title": ch["title"], "url": ch["url"], "target_type": "channel"} for ch in contest_channels]
            )
        )

        await message.answer(
            "После подписок на спонсоров нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Проверить и участвовать",
                        callback_data=f"contest_subscribe_check:{contest_id}",
                        icon_custom_emoji_id="5337160532216526521"
                    )
                ]]
            )
        )
        return

    # Определяем reply клавиатуру в зависимости от роли пользователя
    reply_keyboard = get_admin_reply_keyboard() if message.from_user.id in ADMIN_IDS else get_user_reply_keyboard()

    await message.answer(text=main_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    await message.answer("Выберите действие:", reply_markup=reply_keyboard)


@router.my_chat_member()


@router.my_chat_member()
async def bot_added_to_chat(event: ChatMemberUpdated):
    if event.chat.type not in {"group", "supergroup"}:
        return

    new_status = event.new_chat_member.status
    if new_status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}:
        return

    actor = event.from_user
    if actor is None or actor.is_bot:
        return

    full_name = " ".join(part for part in [actor.first_name, actor.last_name] if part).strip() or str(actor.id)
    database.register_chat_owner(
        chat_id=event.chat.id,
        owner_user_id=actor.id,
        owner_username=actor.username,
        owner_full_name=full_name,
        chat_title=event.chat.title,
    )
    print(
        f"[DB] chat owner registered: chat_id={event.chat.id}, owner_user_id={actor.id}, "
        f"chat_title={event.chat.title!r}"
    )


@router.message(Command("tasks"))
async def tasks_command(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    print(
        f"[ROUTES] /tasks command: chat_id={message.chat.id}, user_id={message.from_user.id}, "
        f"chat_type={message.chat.type}"
    )

    if await is_user_subscribed(message.from_user.id, message.from_user.language_code):
        await message.answer(subscription_success_text, parse_mode="HTML")
        return

    await send_chat_subscription_tasks(
        target=message,
        user_id=message.from_user.id,
        language_code=message.from_user.language_code,
    )


@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    await callback.answer()
    stats = database.get_user_profile_stats(callback.from_user.id)
    await callback.message.edit_text(
        text=render_profile_text(stats),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard(),
    )


@router.message(F.text == "👤 Профиль")
async def profile_button(message: Message):
    """Обработчик кнопки Профиль"""
    stats = database.get_user_profile_stats(message.from_user.id)
    await message.answer(
        text=render_profile_text(stats),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard(),
    )


@router.message(F.text == "🏠 Главное меню")
async def main_menu_button(message: Message):
    """Обработчик кнопки Главное меню"""
    await message.answer(
        text=main_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.callback_query(F.data == "sell_traffic")
async def sell_traffic_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        text=sell_traffic_text,
        parse_mode="HTML",
        reply_markup=get_sell_traffic_keyboard(),
    )


@router.callback_query(F.data == "sell_traffic_chats")
async def sell_traffic_chats_callback(callback: CallbackQuery):
    await callback.answer()
    await show_user_chats(callback)


@router.callback_query(F.data.startswith("chat_card:"))
async def chat_card_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    try:
        await callback.message.edit_text(
            text=render_chat_settings_text(chat),
            parse_mode="HTML",
            reply_markup=get_chat_settings_keyboard(chat_id=chat_id, gate_enabled=bool(chat.get("gate_enabled"))),
        )
    except Exception as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("toggle_chat_gate:"))
async def toggle_chat_gate_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    new_enabled = not bool(chat.get("gate_enabled"))
    updated = database.set_chat_gate_enabled(
        owner_user_id=callback.from_user.id,
        chat_id=chat_id,
        enabled=new_enabled,
    )
    if not updated:
        await callback.message.answer("Не удалось обновить настройки чата.")
        return

    refreshed_chat = database.get_chat_settings(callback.from_user.id, chat_id)
    await callback.message.edit_text(
        text=render_chat_settings_text(refreshed_chat),
        parse_mode="HTML",
        reply_markup=get_chat_settings_keyboard(chat_id=chat_id, gate_enabled=bool(refreshed_chat.get("gate_enabled"))),
    )


@router.callback_query(F.data.startswith("chat_settings:"))
async def chat_settings_menu_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    await callback.message.edit_text(
        text=f"<b>⚙️ Настройки чата</b>\n\n"
             f"<b>{chat.get('chat_title') or chat['chat_id']}</b>\n\n"
             f"Текущие настройки:\n"
             f"├ Макс. спонсоров: <code>{chat.get('max_sponsors', 3)}</code>\n"
             f"├ Сброс подписки: <code>{chat.get('subscription_reset_minutes', 60)} мин</code>\n"
             f"└ Удаление сообщения: <code>{chat.get('bot_message_delete_seconds', 60)} сек</code>",
        parse_mode="HTML",
        reply_markup=get_chat_settings_menu_keyboard(chat_id),
    )


@router.callback_query(F.data.startswith("chat_sponsors:"))
async def chat_sponsors_update_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    try:
        chat_id = int(parts[1])
        max_sponsors = int(parts[2])
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    if not (1 <= max_sponsors <= 10):
        await callback.answer("Количество должно быть от 1 до 10.", show_alert=True)
        return

    updated = database.update_chat_max_sponsors(callback.from_user.id, chat_id, max_sponsors)
    if not updated:
        await callback.answer("Не удалось обновить настройки.", show_alert=True)
        return

    await callback.answer(f"✅ Установлено: {max_sponsors} спонсоров")

    # Обновляем сообщение с новым значением
    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    await callback.message.edit_text(
        text=f"<b>📊 Максимальное количество спонсоров</b>\n\n"
             f"Выберите количество обязательных каналов для подписки (от 1 до 10).\n\n"
             f"✅ Текущее значение: <b>{chat.get('max_sponsors', 3)}</b>",
        parse_mode="HTML",
        reply_markup=get_chat_sponsors_keyboard(chat_id, chat.get('max_sponsors', 3)),
    )


@router.callback_query(F.data.startswith("chat_choose_sponsors:"))
async def chat_set_sponsors_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    await callback.message.edit_text(
        text=f"<b>📊 Максимальное количество спонсоров</b>\n\n"
             f"Выберите количество обязательных каналов для подписки (от 1 до 10).\n\n"
             f"✅ Текущее значение: <b>{chat.get('max_sponsors', 3)}</b>",
        parse_mode="HTML",
        reply_markup=get_chat_sponsors_keyboard(chat_id, chat.get('max_sponsors', 3)),
    )


@router.callback_query(F.data.startswith("chat_reset:"))
async def chat_reset_update_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    try:
        chat_id = int(parts[1])
        reset_minutes = int(parts[2])
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    updated = database.update_chat_subscription_reset(callback.from_user.id, chat_id, reset_minutes)
    if not updated:
        await callback.answer("Не удалось обновить настройки.", show_alert=True)
        return

    await callback.answer(f"✅ Установлено: {reset_minutes} минут")

    # Обновляем сообщение с новым значением
    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    await callback.message.edit_text(
        text=f"<b>⏱ Время сброса подписки</b>\n\n"
             f"Через какое время пользователю снова появятся каналы для подписки.\n\n"
             f"✅ Текущее значение: <b>{chat.get('subscription_reset_minutes', 60)} мин</b>",
        parse_mode="HTML",
        reply_markup=get_chat_reset_time_keyboard(chat_id, chat.get('subscription_reset_minutes', 60)),
    )


@router.callback_query(F.data.startswith("chat_choose_reset:"))
async def chat_set_reset_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    await callback.message.edit_text(
        text=f"<b>⏱ Время сброса подписки</b>\n\n"
             f"Через какое время пользователю снова появятся каналы для подписки.\n\n"
             f"✅ Текущее значение: <b>{chat.get('subscription_reset_minutes', 60)} мин</b>",
        parse_mode="HTML",
        reply_markup=get_chat_reset_time_keyboard(chat_id, chat.get('subscription_reset_minutes', 60)),
    )


@router.callback_query(F.data.startswith("chat_delete:"))
async def chat_delete_update_callback(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    try:
        chat_id = int(parts[1])
        delete_seconds = int(parts[2])
    except ValueError:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    updated = database.update_chat_bot_message_delete(callback.from_user.id, chat_id, delete_seconds)
    if not updated:
        await callback.answer("Не удалось обновить настройки.", show_alert=True)
        return

    await callback.answer(f"✅ Установлено: {delete_seconds} секунд")

    # Обновляем сообщение с новым значением
    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    await callback.message.edit_text(
        text=f"<b>🗑 Удаление сообщения бота</b>\n\n"
             f"Через какое время будет удалено сообщение бота с заданиями.\n\n"
             f"✅ Текущее значение: <b>{chat.get('bot_message_delete_seconds', 60)} сек</b>",
        parse_mode="HTML",
        reply_markup=get_chat_bot_delete_keyboard(chat_id, chat.get('bot_message_delete_seconds', 60)),
    )


@router.callback_query(F.data.startswith("chat_choose_delete:"))
async def chat_set_delete_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_chat_id = callback.data.partition(":")
    try:
        chat_id = int(raw_chat_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор чата.")
        return

    chat = database.get_chat_settings(callback.from_user.id, chat_id)
    if chat is None:
        await callback.message.answer("Чат не найден или не принадлежит вам.")
        return

    await callback.message.edit_text(
        text=f"<b>🗑 Удаление сообщения бота</b>\n\n"
             f"Через какое время будет удалено сообщение бота с заданиями.\n\n"
             f"✅ Текущее значение: <b>{chat.get('bot_message_delete_seconds', 60)} сек</b>",
        parse_mode="HTML",
        reply_markup=get_chat_bot_delete_keyboard(chat_id, chat.get('bot_message_delete_seconds', 60)),
    )


@router.callback_query(F.data == "sell_traffic_bots")
async def sell_traffic_bots_callback(callback: CallbackQuery):
    await callback.answer("Раздел ботов пока в разработке.", show_alert=True)


@router.callback_query(F.data == "sell_traffic_contests")
async def sell_traffic_contests_callback(callback: CallbackQuery):
    await callback.answer()
    await show_user_contests(callback)


@router.callback_query(F.data == "contest_stats")
async def contest_stats_callback(callback: CallbackQuery):
    await callback.answer()
    contests = database.list_owner_contests(callback.from_user.id)
    stats = database.get_owner_stats(callback.from_user.id)
    await callback.message.edit_text(
        text=render_contests_stats_text(contests, stats['reward_per_subscription']),
        parse_mode="HTML",
        reply_markup=get_contests_stats_keyboard(),
    )


@router.callback_query(F.data == "contest_list")
async def contest_list_callback(callback: CallbackQuery):
    await callback.answer()
    await show_user_contests_manage_list(callback)


@router.callback_query(F.data == "my_resources")
async def my_resources_callback(callback: CallbackQuery):
    await callback.answer()
    resources = database.list_user_resources(callback.from_user.id)
    await callback.message.edit_text(
        text=render_resources_list_text(resources),
        parse_mode="HTML",
        reply_markup=get_resources_list_keyboard(resources),
    )


@router.callback_query(F.data == "resource_add")
async def resource_add_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(ResourceAddStates.waiting_url)
    await callback.message.answer(
        "📢 <b>Добавление ресурса</b>\n\n"
        "Отправьте ссылку на канал.\n\n"
        "Примеры:\n"
        "• @my_channel\n"
        "• https://t.me/my_channel\n\n"
        "⚠️ <b>Важно:</b> Бот должен быть добавлен в канал и назначен администратором со всеми правами.",
        parse_mode="HTML"
    )


@router.message(ResourceAddStates.waiting_url)
async def resource_add_url(message: Message, state: FSMContext):
    url = (message.text or "").strip()
    if not url:
        await message.answer("Ссылка не может быть пустой.")
        return

    # Проверяем, что это Telegram-канал
    if not (url.startswith("@") or "t.me/" in url or "telegram.me/" in url):
        await message.answer(
            "❌ Это не похоже на ссылку на Telegram-канал.\n\n"
            "Используйте формат:\n"
            "• @my_channel\n"
            "• https://t.me/my_channel"
        )
        return

    # Извлекаем название канала из ссылки
    if url.startswith("@"):
        title = url
    elif "t.me/" in url or "telegram.me/" in url:
        # Извлекаем последнюю часть URL как название
        parsed = urlparse(url)
        title = parsed.path.strip("/") or url
    else:
        title = url

    # Добавляем ресурс
    added = database.add_user_resource(
        owner_user_id=message.from_user.id,
        title=title,
        url=url
    )

    await state.clear()

    if added:
        await message.answer(
            f"✅ Ресурс <b>{title}</b> успешно добавлен!\n\n"
            "Теперь вы можете использовать его при создании конкурсов.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Не удалось добавить ресурс. Возможно, он уже существует.",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("resource_view:"))
async def resource_view_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_resource_id = callback.data.partition(":")
    try:
        resource_id = int(raw_resource_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор ресурса.")
        return

    resources = database.list_user_resources(callback.from_user.id)
    resource = next((r for r in resources if r['id'] == resource_id), None)

    if resource is None:
        await callback.message.answer("Ресурс не найден или не принадлежит вам.")
        return

    await callback.message.edit_text(
        text=render_resource_card_text(resource),
        parse_mode="HTML",
        reply_markup=get_resource_manage_keyboard(resource_id),
    )


@router.callback_query(F.data.startswith("resource_delete:"))
async def resource_delete_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_resource_id = callback.data.partition(":")
    try:
        resource_id = int(raw_resource_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор ресурса.")
        return

    deleted = database.delete_user_resource(callback.from_user.id, resource_id)

    if deleted:
        await callback.message.answer("✅ Ресурс удален.")
    else:
        await callback.message.answer("⚠️ Не удалось удалить ресурс.")

    # Возвращаемся к списку ресурсов
    resources = database.list_user_resources(callback.from_user.id)
    await callback.message.edit_text(
        text=render_resources_list_text(resources),
        parse_mode="HTML",
        reply_markup=get_resources_list_keyboard(resources),
    )


@router.callback_query(F.data == "contest_create")
async def contest_create_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.message.chat.type != "private":
        await callback.message.answer("Создавать конкурсы пока можно только в личном чате с ботом.")
        return

    await state.clear()
    await state.set_state(ContestCreateStates.waiting_title)
    await callback.message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "1/8 · Название\n\n"
        "Отправьте название розыгрыша (будет видно только вам в списке конкурсов).",
        parse_mode="HTML",
        reply_markup=get_contest_cancel_keyboard()
    )


@router.callback_query(F.data == "contest_create_cancel")
async def contest_create_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "❌ Создание конкурса отменено.",
        parse_mode="HTML"
    )


@router.message(ContestCreateStates.waiting_title)
async def contest_create_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Отправьте название розыгрыша.")
        return

    await state.update_data(contest_title=title)
    await state.set_state(ContestCreateStates.waiting_post_text)
    await message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "2/8 · Пост\n\n"
        "Отправьте текст розыгрыша. Можно сразу отправить или переслать пост с фото, видео или GIF.",
        parse_mode="HTML",
        reply_markup=get_contest_cancel_keyboard()
    )


@router.message(ContestCreateStates.waiting_post_text)
async def contest_create_post_text(message: Message, state: FSMContext):
    post_text = message.text or message.caption or ""
    post_text = post_text.strip()

    if not post_text:
        await message.answer("Текст не может быть пустым. Отправьте текст розыгрыша.")
        return

    media_file_id = None
    media_type = None

    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_file_id = message.animation.file_id
        media_type = "animation"

    await state.update_data(
        post_text=post_text,
        media_file_id=media_file_id,
        media_type=media_type
    )

    if media_file_id:
        await state.set_state(ContestCreateStates.waiting_button_text)
        await message.answer(
            "🧩 <b>Новый розыгрыш</b>\n"
            "4/8 · Кнопка\n\n"
            "Выберите текст кнопки участия или введите свой вариант.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Оставить «Участвовать»", callback_data="contest_button_default")]]
            )
        )
    else:
        await state.set_state(ContestCreateStates.waiting_media)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.answer(
            "🧩 <b>Новый розыгрыш</b>\n"
            "3/8 · Обложка\n\n"
            "Отправьте фото, видео или GIF для поста. Если обложка не нужна, нажмите «Без медиа».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Без медиа", callback_data="contest_skip_media")],
                    [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
                ]
            )
        )


@router.callback_query(F.data == "contest_skip_media")
async def contest_skip_media_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ContestCreateStates.waiting_button_text)
    await callback.message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "4/8 · Кнопка\n\n"
        "Выберите текст кнопки участия или введите свой вариант.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оставить «Участвовать»", callback_data="contest_button_default")],
                [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
            ]
        )
    )


@router.callback_query(F.data == "contest_button_default")
async def contest_button_default_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(button_text="Участвовать")
    await state.set_state(ContestCreateStates.waiting_entry_filter)

    await callback.message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "5/8 · Фильтр входа\n\n"
        "Отправьте количество заданий, которое должен выполнить участник (от 1 до 10).",
        parse_mode="HTML",
        reply_markup=get_contest_cancel_keyboard()
    )


@router.message(ContestCreateStates.waiting_media)
async def contest_create_media(message: Message, state: FSMContext):
    media_file_id = None
    media_type = None

    if message.photo:
        media_file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_file_id = message.video.file_id
        media_type = "video"
    elif message.animation:
        media_file_id = message.animation.file_id
        media_type = "animation"
    else:
        await message.answer("Отправьте фото, видео или GIF, либо нажмите «Без медиа».")
        return

    await state.update_data(media_file_id=media_file_id, media_type=media_type)
    await state.set_state(ContestCreateStates.waiting_button_text)
    await message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "4/8 · Кнопка\n\n"
        "Выберите текст кнопки участия или введите свой вариант.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оставить «Участвовать»", callback_data="contest_button_default")],
                [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
            ]
        )
    )


@router.message(ContestCreateStates.waiting_button_text)
async def contest_create_button_text(message: Message, state: FSMContext):
    button_text = (message.text or "").strip()
    if not button_text:
        await message.answer("Текст кнопки не может быть пустым.")
        return

    await state.update_data(button_text=button_text)
    await state.set_state(ContestCreateStates.waiting_entry_filter)

    await message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "5/8 · Фильтр входа\n\n"
        "Отправьте количество заданий, которое должен выполнить участник (от 1 до 10).",
        parse_mode="HTML",
        reply_markup=get_contest_cancel_keyboard()
    )


@router.message(ContestCreateStates.waiting_entry_filter)
async def contest_create_entry_filter(message: Message, state: FSMContext):
    try:
        filter_count = int((message.text or "").strip())
    except ValueError:
        await message.answer("Введите число от 1 до 10")
        return

    if filter_count < 1 or filter_count > 10:
        await message.answer("Количество заданий должно быть от 1 до 10.")
        return

    await state.update_data(entry_filter=str(filter_count))
    await state.set_state(ContestCreateStates.waiting_unsubscribe_action)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "6/8 · Отписка\n\n"
        "Что делать, если участник после входа отпишется от задания или задание будет откачено?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Исключить из розыгрыша", callback_data="contest_unsub:exclude")],
                [InlineKeyboardButton(text="Оставить в розыгрыше", callback_data="contest_unsub:keep")],
                [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
            ]
        )
    )


@router.callback_query(F.data.startswith("contest_unsub:"))
async def contest_unsubscribe_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, _, action = callback.data.partition(":")

    await state.update_data(unsubscribe_action=action)
    await state.set_state(ContestCreateStates.waiting_winners_count)

    await callback.message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "7/8 · Победители\n\n"
        "Отправьте количество победителей.",
        parse_mode="HTML",
        reply_markup=get_contest_cancel_keyboard()
    )


@router.message(ContestCreateStates.waiting_winners_count)
async def contest_create_winners_count(message: Message, state: FSMContext):
    try:
        winners_count = int((message.text or "").strip())
    except ValueError:
        await message.answer("Введите число, например: 3")
        return

    if winners_count <= 0:
        await message.answer("Количество победителей должно быть больше нуля.")
        return

    await state.update_data(winners_count=winners_count)
    await state.set_state(ContestCreateStates.waiting_completion_type)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.answer(
        "🧩 <b>Новый розыгрыш</b>\n"
        "8/8 · Завершение\n\n"
        "Выберите, как завершать розыгрыш.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="По таймеру", callback_data="contest_complete:timer")],
                [InlineKeyboardButton(text="По количеству участников", callback_data="contest_complete:participants")],
                [InlineKeyboardButton(text="❌ Отменить создание", callback_data="contest_create_cancel")]
            ]
        )
    )


@router.callback_query(F.data.startswith("contest_complete:"))
async def contest_completion_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, _, completion_type = callback.data.partition(":")

    await state.update_data(completion_type=completion_type)

    if completion_type == "timer":
        from datetime import datetime, timezone, timedelta
        # Получаем текущее время в МСК (UTC+3)
        current_time_utc = datetime.now(timezone.utc)
        moscow_offset = timedelta(hours=3)
        current_time_msk = current_time_utc + moscow_offset
        example_date = current_time_msk.strftime("%d.%m.%Y %H:%M")

        await callback.message.answer(
            f"⏱️ Отправьте дату и время завершения конкурса в формате:\n"
            f"<code>ДД.ММ.ГГГГ ЧЧ:ММ</code> (время МСК)\n\n"
            f"Пример: <code>{example_date}</code>\n\n"
            f"Текущее время (МСК): <code>{example_date}</code>",
            parse_mode="HTML"
        )
    elif completion_type == "participants":
        await callback.message.answer(
            "👥 Отправьте количество участников, при достижении которого конкурс завершится автоматически:",
            parse_mode="HTML"
        )
    else:
        await state.update_data(time_limit_minutes=0, participants_limit=None)
        # Показываем выбор канала из ресурсов
        await show_channel_selection(callback.message, state, callback.from_user.id)


@router.message(ContestCreateStates.waiting_completion_type)
async def contest_create_timer_or_participants(message: Message, state: FSMContext):
    data = await state.get_data()
    completion_type = data.get("completion_type")

    if completion_type == "timer":
        # Парсим дату в формате ДД.ММ.ГГГГ ЧЧ:ММ
        date_str = (message.text or "").strip()

        try:
            from datetime import datetime, timezone, timedelta
            # Парсим дату как локальное время (без timezone)
            end_date_naive = datetime.strptime(date_str, "%d.%m.%Y %H:%M")

            # Получаем текущее время UTC
            current_date_utc = datetime.now(timezone.utc)

            # Предполагаем, что пользователь вводит время в UTC+3 (Москва)
            # Конвертируем введенное время в UTC
            moscow_offset = timedelta(hours=3)
            end_date_utc = end_date_naive.replace(tzinfo=timezone.utc) - moscow_offset

            # Проверяем, что дата в будущем
            if end_date_utc <= current_date_utc:
                await message.answer(
                    "❌ Дата завершения должна быть в будущем.\n\n"
                    f"Текущее время (МСК): <code>{(current_date_utc + moscow_offset).strftime('%d.%m.%Y %H:%M')}</code>\n"
                    "Попробуйте еще раз.",
                    parse_mode="HTML"
                )
                return

            # Вычисляем разницу в минутах
            time_diff = end_date_utc - current_date_utc
            time_limit_minutes = int(time_diff.total_seconds() / 60)

            # Проверяем минимальное время (хотя бы 1 минута)
            if time_limit_minutes < 1:
                await message.answer(
                    "❌ Конкурс должен длиться минимум 1 минуту.\n"
                    "Попробуйте еще раз.",
                    parse_mode="HTML"
                )
                return

            await state.update_data(
                time_limit_minutes=time_limit_minutes,
                participants_limit=None,
                end_date_str=date_str
            )

            # Показываем подтверждение
            hours = time_limit_minutes // 60
            minutes = time_limit_minutes % 60
            duration_str = f"{hours}ч {minutes}м" if hours > 0 else f"{minutes}м"

            await message.answer(
                f"✅ Конкурс завершится: <code>{date_str}</code> (МСК)\n"
                f"Длительность: <code>{duration_str}</code>",
                parse_mode="HTML"
            )

        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n\n"
                "Используйте формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
                "Пример: <code>05.05.2026 18:30</code>\n\n"
                "Попробуйте еще раз.",
                parse_mode="HTML"
            )
            return

    elif completion_type == "participants":
        try:
            value = int((message.text or "").strip())
        except ValueError:
            await message.answer("Введите число")
            return

        if value <= 0:
            await message.answer("Количество участников должно быть больше нуля.")
            return

        await state.update_data(participants_limit=value, time_limit_minutes=0)

    # Показываем выбор канала из ресурсов
    await show_channel_selection(message, state, message.from_user.id)


@router.message(ContestCreateStates.waiting_channel)
async def contest_create_channel(message: Message, state: FSMContext):
    channel_link = (message.text or "").strip()
    if not channel_link:
        await message.answer("Ссылка не может быть пустой.")
        return

    channel_id = parse_telegram_target(channel_link)
    if channel_id is None:
        await message.answer(
            "Некорректная ссылка на канал.\n\n"
            "Примеры правильных ссылок:\n"
            "• @my_channel\n"
            "• https://t.me/my_channel"
        )
        return

    await state.update_data(channel_id=channel_id)
    await finalize_contest_creation(message, state)


async def show_channel_selection(message: Message, state: FSMContext, user_id: int):
    """Показывает выбор канала из ресурсов пользователя"""
    resources = database.list_user_resources(user_id)

    if not resources:
        await message.answer(
            "❌ <b>У вас нет добавленных ресурсов</b>\n\n"
            "Сначала добавьте канал в разделе «Мои ресурсы», чтобы использовать его для публикации конкурса.\n\n"
            "Создание конкурса отменено.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    await state.set_state(ContestCreateStates.waiting_channel)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    inline_keyboard = []

    for resource in resources:
        inline_keyboard.append([
            InlineKeyboardButton(
                text=resource['title'],
                callback_data=f"contest_select_channel:{resource['id']}"
            )
        ])

    await message.answer(
        "📢 <b>Выберите канал для публикации</b>\n\n"
        "Выберите канал из ваших ресурсов, где будет опубликован розыгрыш.\n\n"
        "⚠️ <b>Важно:</b> Бот должен быть администратором выбранного канала!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    )


@router.callback_query(F.data.startswith("contest_select_channel:"))
async def contest_select_channel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, _, raw_resource_id = callback.data.partition(":")
    try:
        resource_id = int(raw_resource_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор ресурса.")
        return

    # Получаем ресурс
    resources = database.list_user_resources(callback.from_user.id)
    resource = next((r for r in resources if r['id'] == resource_id), None)

    if resource is None:
        await callback.message.answer("Ресурс не найден.")
        await state.clear()
        return

    # Парсим channel_id из URL ресурса
    channel_id = parse_telegram_target(resource['url'])
    if channel_id is None:
        await callback.message.answer("Не удалось определить ID канала из ресурса.")
        await state.clear()
        return

    await state.update_data(channel_id=channel_id)
    await callback.message.answer(f"✅ Выбран канал: <b>{resource['title']}</b>", parse_mode="HTML")
    await finalize_contest_creation(callback.message, state, callback.from_user.id)


async def finalize_contest_creation(message: Message, state: FSMContext, user_id: int | None = None):
    data = await state.get_data()

    # Конкурс создается без проверки партнерских заданий
    # Задания будут проверяться индивидуально для каждого участника при вступлении

    # Используем переданный user_id или берем из message
    owner_user_id = user_id if user_id is not None else message.from_user.id

    print(f"[CONTEST] Creating contest for user {owner_user_id}")
    print(f"[CONTEST] Contest data: title={data.get('contest_title')}, channel_id={data.get('channel_id')}")

    # Создаем конкурс в базе данных с пустым списком каналов
    contest_id = database.create_contest(
        owner_user_id=owner_user_id,
        title=data.get("contest_title", "Розыгрыш"),
        content_text=data["post_text"],
        contest_channel_id=str(data["channel_id"]),
        winners_count=data["winners_count"],
        channels=[],  # Пустой список, задания будут для каждого участника индивидуально
        subscriptions_required=int(data.get("entry_filter", "1")),
        completion_type=data.get("completion_type", "manual"),
        time_limit_minutes=data.get("time_limit_minutes", 0),
        participants_limit=data.get("participants_limit"),
        photo_file_id=data.get("media_file_id"),
    )

    print(f"[CONTEST] Contest created with ID: {contest_id}")

    # Получаем username бота для deep link
    bot_username = await get_bot_username_from_message(message)
    button_text = data.get("button_text", "Участвовать")

    # Публикуем пост в канале
    try:
        channel_id = data["channel_id"]
        post_text = data["post_text"]
        media_file_id = data.get("media_file_id")
        media_type = data.get("media_type")

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text=button_text,
                    url=f"https://t.me/{bot_username}?start=contest_{contest_id}"
                )
            ]]
        )

        posted_message = None
        if media_file_id and media_type == "photo":
            posted_message = await message.bot.send_photo(
                chat_id=channel_id,
                photo=media_file_id,
                caption=post_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif media_file_id and media_type == "video":
            posted_message = await message.bot.send_video(
                chat_id=channel_id,
                video=media_file_id,
                caption=post_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif media_file_id and media_type == "animation":
            posted_message = await message.bot.send_animation(
                chat_id=channel_id,
                animation=media_file_id,
                caption=post_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            posted_message = await message.bot.send_message(
                chat_id=channel_id,
                text=post_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )

        # Сохраняем ID опубликованного сообщения
        if posted_message:
            database.update_contest_posted_message(contest_id, posted_message.message_id)

        await state.clear()

        completion_info = ""
        if data.get("completion_type") == "timer":
            if data.get("end_date_str"):
                completion_info = f"Завершится: <code>{data.get('end_date_str')}</code>"
            else:
                completion_info = f"Завершится через: <code>{data.get('time_limit_minutes', 0)} минут</code>"
        elif data.get("completion_type") == "participants":
            completion_info = f"Завершится при: <code>{data.get('participants_limit', 0)}</code> участниках"
        else:
            completion_info = "Завершение: <code>вручную</code>"

        await message.answer(
            f"<blockquote><b>✅ Розыгрыш успешно создан!</b>\n\n"
            f"Пост опубликован в канале с кнопкой участия</blockquote>\n\n"
            f"<b>Параметры розыгрыша:</b>\n"
            f"├ Победителей: <code>{data['winners_count']}</code>\n"
            f"├ Обязательных подписок: <code>{data.get('entry_filter', '1')}</code>\n"
            f"└ {completion_info}\n\n"
            f"<i>Партнерские задания будут показаны каждому участнику индивидуально</i>",
            parse_mode="HTML"
        )

    except Exception as e:
        print(f"[CONTEST] failed to publish contest: contest_id={contest_id}, error={e}")
        await state.clear()
        await message.answer(
            f"⚠️ Розыгрыш создан (ID: {contest_id}), но не удалось опубликовать в канал.\n\n"
            f"Проверьте:\n"
            f"• Бот является администратором канала\n"
            f"• У бота есть права на публикацию сообщений\n\n"
            f"Ошибка: {str(e)}",
            parse_mode="HTML"
        )


async def get_bot_username_from_message(message: Message) -> str:
    bot_username = os.getenv("BOT_USERNAME")
    if bot_username:
        return bot_username

    me = await message.bot.get_me()
    return me.username


@router.callback_query(F.data.startswith("contest_view:"))
async def contest_view_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_contest_id = callback.data.partition(":")
    try:
        contest_id = int(raw_contest_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор конкурса.")
        return

    contest = database.get_contest(contest_id, owner_user_id=callback.from_user.id)
    if contest is None:
        await callback.message.answer("Конкурс не найден или не принадлежит вам.")
        return

    invite_url = await get_bot_start_url(callback, f"contest_{contest_id}")
    await callback.message.edit_text(
        text=render_contest_card_text(contest, invite_url=invite_url),
        parse_mode="HTML",
        reply_markup=get_contest_manage_keyboard(contest_id, invite_url, contest.get('status', 'active')),
    )


@router.callback_query(F.data.startswith("contest_publish:"))
async def contest_publish_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_contest_id = callback.data.partition(":")
    try:
        contest_id = int(raw_contest_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор конкурса.")
        return

    contest = database.get_contest(contest_id, owner_user_id=callback.from_user.id)
    if contest is None:
        await callback.message.answer("Конкурс не найден или не принадлежит вам.")
        return

    invite_url = await get_bot_start_url(callback, f"contest_{contest_id}")
    published = await publish_contest_button(callback, contest, invite_url)
    if published:
        await callback.message.answer("Кнопка «Участвовать» обновлена под постом.")
    else:
        await callback.message.answer(
            "Не удалось поставить кнопку под постом. "
            "Нужны права администратора канала и возможность редактировать пост."
        )


@router.callback_query(F.data.startswith("contest_draw:"))
async def contest_draw_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_contest_id = callback.data.partition(":")
    try:
        contest_id = int(raw_contest_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор конкурса.")
        return

    contest = database.get_contest(contest_id, owner_user_id=callback.from_user.id)
    if contest is None:
        await callback.message.answer("Конкурс не найден или не принадлежит вам.")
        return

    # Проверяем, что конкурс активен
    if contest.get('status') != 'active':
        await callback.answer("Конкурс уже завершен.", show_alert=True)
        return

    winners = database.draw_contest_winners(contest_id)

    if winners:
        winner_lines = "\n".join(
            f"{idx}. <a href=\"tg://user?id={winner.get('participant_user_id')}\">{winner.get('participant_full_name') or 'Участник'}</a>"
            for idx, winner in enumerate(winners, 1)
        )
        await callback.answer("Конкурс завершен!", show_alert=True)
        await callback.message.answer(f"🎉 Победители выбраны:\n{winner_lines}\n\nКонкурс завершен.", parse_mode="HTML")
    else:
        await callback.answer("Конкурс завершен.", show_alert=True)
        await callback.message.answer("⚠️ Конкурс завершен, но не было участников для выбора победителей.")

    # Обновляем карточку конкурса
    refreshed_contest = database.get_contest(contest_id, owner_user_id=callback.from_user.id)
    if refreshed_contest:
        invite_url = await get_bot_start_url(callback, f"contest_{contest_id}")
        await callback.message.edit_text(
            text=render_contest_card_text(refreshed_contest, invite_url=invite_url),
            parse_mode="HTML",
            reply_markup=get_contest_manage_keyboard(contest_id, invite_url, refreshed_contest.get('status', 'completed')),
        )


@router.callback_query(F.data.startswith("contest_subscribe_check:"))
async def contest_subscribe_check_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_contest_id = callback.data.partition(":")
    try:
        contest_id = int(raw_contest_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор конкурса.")
        return

    contest = database.get_contest(contest_id)
    if contest is None or contest.get("status") != "active":
        await callback.message.answer("Конкурс недоступен.")
        return

    # Получаем партнерские задания для этого участника
    channels = await get_flyer_tasks_for_user(
        user_id=callback.from_user.id,
        language_code=callback.from_user.language_code,
    )

    # Фильтруем только Telegram-каналы
    contest_channels = []
    for item in channels:
        if item.get("target_type") == "channel" and item.get("url"):
            url = item["url"]
            # Проверяем, что это действительно Telegram-канал
            if url.startswith("@") or "t.me/" in url or "telegram.me/" in url:
                contest_channels.append({"title": item["title"], "url": url})

    # Берем нужное количество каналов согласно subscriptions_required
    subscriptions_required = contest.get("subscriptions_required", 1)
    contest_channels = contest_channels[:subscriptions_required]

    if not contest_channels:
        await callback.message.answer("В данный момент нет доступных заданий. Попробуйте позже.")
        return

    # Создаем временный объект конкурса с каналами участника для проверки
    contest_with_channels = dict(contest)
    contest_with_channels["channels"] = contest_channels

    # Проверяем подписки на каналы конкурса
    verified, missing_channels = await verify_contest_channels(callback.bot, contest_with_channels, callback.from_user.id)

    if not verified:
        await callback.message.answer(
            f"❌ Вы подписались не на все каналы.\n\n"
            f"Осталось подписаться: {len(missing_channels)}",
            parse_mode="HTML"
        )
        return

    # Регистрируем участника
    full_name = " ".join(part for part in [callback.from_user.first_name, callback.from_user.last_name] if part).strip()
    created, completion_data = database.register_contest_entry(
        contest_id=contest_id,
        participant_user_id=callback.from_user.id,
        participant_username=callback.from_user.username,
        participant_full_name=full_name or str(callback.from_user.id),
    )

    # Проверяем, завершился ли конкурс
    if completion_data:
        # Конкурс завершился автоматически
        await callback.message.answer(
            f"✅ Вы успешно зарегистрированы в конкурсе!\n\n"
            f"Достигнуто необходимое количество участников.\n\n"
            f"Победители выбраны автоматически. Ожидайте результатов от организатора.",
            parse_mode="HTML"
        )

        # Уведомляем владельца конкурса
        try:
            winners = completion_data['winners']
            if winners:
                winner_lines = "\n".join(
                    f"{idx}. <a href=\"tg://user?id={winner.get('participant_user_id')}\">{winner.get('participant_full_name') or 'Участник'}</a>"
                    for idx, winner in enumerate(winners, 1)
                )
                owner_message = (
                    f"🎉 Конкурс <b>{completion_data['title']}</b> завершен!\n\n"
                    f"Достигнуто необходимое количество участников.\n\n"
                    f"Победители выбраны автоматически:\n{winner_lines}\n\n"
                    f"Конкурс удален из списка."
                )
            else:
                owner_message = (
                    f"⚠️ Конкурс <b>{completion_data['title']}</b> завершен, "
                    f"но не было участников для выбора победителей.\n\n"
                    f"Конкурс удален из списка."
                )

            await callback.bot.send_message(
                chat_id=completion_data['owner_user_id'],
                text=owner_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[CONTEST] Failed to notify owner: {e}")

        return

    if created:
        await callback.message.answer(
            f"✅ Вы успешно приняли участие в конкурсе!\n\n",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            f"ℹ️ Вы уже зарегистрированы в этом конкурсе.\n\n",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("contest_join:"))
async def contest_join_callback(callback: CallbackQuery):
    await callback.answer()
    _, _, raw_contest_id = callback.data.partition(":")
    try:
        contest_id = int(raw_contest_id)
    except ValueError:
        await callback.message.answer("Некорректный идентификатор конкурса.")
        return

    contest = database.get_contest(contest_id)
    if contest is None or contest.get("status") != "active":
        await callback.message.answer("Конкурс недоступен.")
        return

    verified, missing_channels = await verify_contest_channels(callback.bot, contest, callback.from_user.id)
    if not verified:
        await callback.message.answer(
            "Вы подписались не на все обязательные каналы. Подпишитесь и попробуйте снова.",
            reply_markup=get_contest_join_keyboard(contest_id, missing_channels, already_joined=False),
        )
        return

    full_name = " ".join(part for part in [callback.from_user.first_name, callback.from_user.last_name] if part).strip()
    created, completion_data = database.register_contest_entry(
        contest_id=contest_id,
        participant_user_id=callback.from_user.id,
        participant_username=callback.from_user.username,
        participant_full_name=full_name or str(callback.from_user.id),
    )

    # Проверяем, завершился ли конкурс
    if completion_data:
        await callback.message.edit_text(
            text=f"✅ Вы успешно зарегистрированы!\n\n"
                 f"🎉 Конкурс <b>{contest['title']}</b> завершен!\n"
                 f"Достигнуто необходимое количество участников.\n\n"
                 f"Победители выбраны автоматически. Ожидайте результатов от организатора.",
            parse_mode="HTML",
        )

        # Уведомляем владельца конкурса
        try:
            winners = completion_data['winners']
            if winners:
                winner_lines = "\n".join(
                    f"{idx}. <a href=\"tg://user?id={winner.get('participant_user_id')}\">{winner.get('participant_full_name') or 'Участник'}</a>"
                    for idx, winner in enumerate(winners, 1)
                )
                owner_message = (
                    f"🎉 Конкурс <b>{completion_data['title']}</b> завершен!\n\n"
                    f"Достигнуто необходимое количество участников.\n\n"
                    f"Победители выбраны автоматически:\n{winner_lines}\n\n"
                    f"Конкурс удален из списка."
                )
            else:
                owner_message = (
                    f"⚠️ Конкурс <b>{completion_data['title']}</b> завершен, "
                    f"но не было участников для выбора победителей.\n\n"
                    f"Конкурс удален из списка."
                )

            await callback.bot.send_message(
                chat_id=completion_data['owner_user_id'],
                text=owner_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[CONTEST] Failed to notify owner: {e}")

        return

    refreshed = database.get_contest(contest_id)
    if refreshed:
        await callback.message.edit_text(
            text=render_contest_join_text(refreshed, already_joined=True),
            parse_mode="HTML",
            reply_markup=get_contest_join_keyboard(contest_id, refreshed.get("channels", []), already_joined=True),
        )

    if created:
        await callback.message.answer("Вы участвуете в конкурсе.")
    else:
        await callback.message.answer("Вы уже были зарегистрированы в этом конкурсе.")


@router.callback_query(F.data == "contest_joined_info")
async def contest_joined_info_callback(callback: CallbackQuery):
    await callback.answer("Вы уже участвуете в этом конкурсе.", show_alert=True)


@router.callback_query(F.data == "buy_traffic")
async def buy_traffic_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Раздел покупки трафика пока в разработке.")


@router.callback_query(F.data == "cabinet")
async def cabinet_callback(callback: CallbackQuery):
    await callback.answer()
    stats = database.get_owner_stats(callback.from_user.id)
    await callback.message.edit_text(
        text=render_profile_text(stats),
        parse_mode="HTML",
        reply_markup=get_profile_keyboard(),
    )


@router.callback_query(F.data == "back")
async def back_callback(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        text=main_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def group_message_guard(message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    if message.text and message.text.startswith("/"):
        return

    print(
        f"[ROUTES] group_message_guard: chat_id={message.chat.id}, user_id={message.from_user.id}, "
        f"message_id={message.message_id}, text={message.text!r}"
    )

    if database.is_member_approved(chat_id=message.chat.id, member_user_id=message.from_user.id):
        print(
            f"[DB] user already approved in chat: chat_id={message.chat.id}, user_id={message.from_user.id}"
        )
        return

    stored_chat = database.get_chat_runtime(chat_id=message.chat.id)
    if stored_chat is None:
        print(f"[DB] chat is not registered in database: chat_id={message.chat.id}")
        return

    if not bool(stored_chat.get("gate_enabled")):
        print(f"[DB] chat gate is disabled: chat_id={message.chat.id}")
        return

    subscribed = await is_user_subscribed(
        message.from_user.id,
        message.from_user.language_code,
    )
    if subscribed:
        await reward_completed_chat_tasks(
            chat_id=message.chat.id,
            member_user_id=message.from_user.id,
            pending_tasks=[],
        )
        print(
            f"[ROUTES] user is allowed to write: chat_id={message.chat.id}, user_id={message.from_user.id}"
        )
        return

    try:
        await message.delete()
        print(
            f"[ROUTES] message deleted because subscription is required: "
            f"chat_id={message.chat.id}, user_id={message.from_user.id}, message_id={message.message_id}"
        )
    except Exception:
        await message.answer(
            "Не удалось удалить сообщение. Дайте боту права администратора на удаление сообщений."
        )
        print(
            f"[ROUTES] failed to delete message: chat_id={message.chat.id}, "
            f"user_id={message.from_user.id}, message_id={message.message_id}"
        )
        return

    await send_chat_subscription_tasks(
        target=message,
        user_id=message.from_user.id,
        language_code=message.from_user.language_code,
    )
