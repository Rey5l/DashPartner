from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

from config import ADMIN_IDS
from services.database_service import DatabaseService
from keyboards.admin_keyboard import (
    get_admin_panel_keyboard,
    get_admin_resources_keyboard,
    get_admin_settings_keyboard,
    get_admin_back_keyboard,
    get_moderation_actions_keyboard,
    get_category_keyboard,
    get_chat_moderation_actions_keyboard,
    get_chat_category_keyboard,
)
from keyboards.reply_keyboard import get_admin_reply_keyboard
from texts.admin_texts import (
    admin_panel_text,
    render_admin_reserve_text,
    render_admin_statistics_text,
    render_admin_resources_text,
    render_admin_resource_list_text,
    render_admin_resource_stats_text,
    render_admin_settings_text,
    admin_settings_chat_price_text,
    admin_settings_contest_price_text,
)

router = Router()
database = DatabaseService()


class AdminStates(StatesGroup):
    waiting_chat_price = State()
    waiting_contest_price = State()


def is_admin(user_id: int) -> bool:
    """Проверка является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@router.message(F.text == "/admin")
async def admin_panel_command(message: Message):
    """Команда для открытия админ панели"""
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ панели")
        return

    await message.answer(
        admin_panel_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔐 Админ панель")
async def admin_panel_button(message: Message):
    """Кнопка для открытия админ панели"""
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ панели")
        return

    await message.answer(
        admin_panel_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    """Главное меню админ панели"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        admin_panel_text,
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_reserve")
async def admin_reserve_callback(callback: CallbackQuery):
    """Показать баланс резерва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    from services.crypto_service import CryptoService
    crypto_service = CryptoService()

    total_balance = await crypto_service.get_balance()

    # Определяем статус резерва
    if total_balance < 1:
        reserve_status = "🚨 КРИТИЧЕСКИ НИЗКИЙ"
        reserve_emoji = "🔴"
        recommendation = "❌ СРОЧНО ПОПОЛНИТЕ РЕЗЕРВ!"
    elif total_balance < 10:
        reserve_status = "⚠️ НИЗКИЙ"
        reserve_emoji = "🟡"
        recommendation = "💡 Рекомендуется пополнить резерв"
    elif total_balance < 50:
        reserve_status = "ℹ️ СРЕДНИЙ"
        reserve_emoji = "🟢"
        recommendation = "✅ Резерв в норме"
    else:
        reserve_status = "✅ ДОСТАТОЧНЫЙ"
        reserve_emoji = "💚"
        recommendation = "🎉 Отличный запас!"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Пополнить резерв", callback_data="reserve_topup")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(
        f"💰 <b>БАЛАНС СИСТЕМЫ</b>\n\n"
        f"💵 Текущий баланс: <b>{total_balance:.2f} USDT</b>\n"
        f"📊 Статус: {reserve_emoji} <b>{reserve_status}</b>\n\n"
        f"<i>{recommendation}</i>",
        parse_mode='HTML',
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "admin_statistics")
async def admin_statistics_callback(callback: CallbackQuery):
    """Показать статистику системы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    stats = database.get_admin_statistics()

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 10 дней", callback_data="admin_stats_graph_10")
    kb.button(text="📊 20 дней", callback_data="admin_stats_graph_20")
    kb.button(text="📊 30 дней", callback_data="admin_stats_graph_30")
    kb.button(text="🔙 Назад", callback_data="admin_panel")
    kb.adjust(3, 1)

    await callback.message.edit_text(
        render_admin_statistics_text(stats),
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_withdrawals")
async def admin_withdrawals_callback(callback: CallbackQuery):
    """Показать меню заявок на вывод"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    pending = database.count_withdrawals_by_status("pending")
    approved = database.count_withdrawals_by_status("approved")
    refunded = database.count_withdrawals_by_status("refunded")
    declined = database.count_withdrawals_by_status("declined")

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text=f"🕓 Ожидающие [{pending}]", callback_data="wd_list_pending")
    kb.button(text=f"✅ Подтвержд. [{approved}]", callback_data="wd_list_approved")
    kb.button(text=f"↩️ Отклонённые [{refunded}]", callback_data="wd_list_refunded")
    kb.button(text=f"❌ Без возврата [{declined}]", callback_data="wd_list_declined")
    kb.button(text="🔙 Назад", callback_data="admin_panel")
    kb.adjust(2, 2, 1)

    await callback.message.edit_text(
        "<b>Выберите категорию заявок:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_resources")
async def admin_resources_callback(callback: CallbackQuery):
    """Меню управления ресурсами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        render_admin_resources_text(),
        reply_markup=get_admin_resources_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_resource_list")
async def admin_resource_list_callback(callback: CallbackQuery):
    """Показать список всех ресурсов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    resources = database.get_all_resources()
    await callback.message.edit_text(
        render_admin_resource_list_text(resources),
        reply_markup=get_admin_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_resource_stats")
async def admin_resource_stats_callback(callback: CallbackQuery):
    """Показать статистику ресурсов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    stats = database.get_resource_statistics()

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 10 дней", callback_data="resource_stats_graph_10")
    kb.button(text="📊 20 дней", callback_data="resource_stats_graph_20")
    kb.button(text="📊 30 дней", callback_data="resource_stats_graph_30")
    kb.button(text="🔙 Назад", callback_data="admin_resources")
    kb.adjust(3, 1)

    await callback.message.edit_text(
        render_admin_resource_stats_text(stats),
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_resource_add")
async def admin_resource_add_callback(callback: CallbackQuery):
    """Добавить ресурс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    # TODO: Implement resource adding functionality
    await callback.answer("Функционал в разработке", show_alert=True)


@router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery):
    """Меню настроек"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    # TODO: Get prices from database/config
    from config import CHAT_SUBSCRIPTION_REWARD
    chat_price = CHAT_SUBSCRIPTION_REWARD
    contest_price = 0.5  # Default value, should be stored in DB

    await callback.message.edit_text(
        render_admin_settings_text(chat_price, contest_price),
        reply_markup=get_admin_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings_chat_price")
async def admin_settings_chat_price_callback(callback: CallbackQuery, state: FSMContext):
    """Изменить цену за подписку в чате"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_chat_price)
    await callback.message.edit_text(
        admin_settings_chat_price_text,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings_contest_price")
async def admin_settings_contest_price_callback(callback: CallbackQuery, state: FSMContext):
    """Изменить цену за подписку в конкурсе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_contest_price)
    await callback.message.edit_text(
        admin_settings_contest_price_text,
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_chat_price)
async def process_chat_price(message: Message, state: FSMContext):
    """Обработка новой цены за подписку в чате"""
    if not is_admin(message.from_user.id):
        return

    try:
        new_price = float(message.text)
        if new_price < 0:
            await message.answer("Цена не может быть отрицательной")
            return

        # TODO: Save to database
        await message.answer(
            f"✅ Цена за подписку в чате обновлена: {new_price:.2f} ₽\n\n"
            f"⚠️ Примечание: для полного применения изменений требуется перезапуск бота",
            reply_markup=get_admin_back_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат. Отправьте число (например: 0.8)")


# ==================== РЕЗЕРВ И ЗАЯВКИ НА ВЫВОД ====================

class ReserveTopupStates(StatesGroup):
    waiting_amount = State()


@router.message(F.text == "💰 Баланс резерва")
async def admin_reserve_balance(message: Message):
    """Показать баланс резерва"""
    if not is_admin(message.from_user.id):
        return

    from services.crypto_service import CryptoService
    crypto_service = CryptoService()

    total_balance = await crypto_service.get_balance()

    # Определяем статус резерва
    if total_balance < 1:
        reserve_status = "🚨 КРИТИЧЕСКИ НИЗКИЙ"
        reserve_emoji = "🔴"
        recommendation = "❌ СРОЧНО ПОПОЛНИТЕ РЕЗЕРВ!"
    elif total_balance < 10:
        reserve_status = "⚠️ НИЗКИЙ"
        reserve_emoji = "🟡"
        recommendation = "💡 Рекомендуется пополнить резерв"
    elif total_balance < 50:
        reserve_status = "ℹ️ СРЕДНИЙ"
        reserve_emoji = "🟢"
        recommendation = "✅ Резерв в норме"
    else:
        reserve_status = "✅ ДОСТАТОЧНЫЙ"
        reserve_emoji = "💚"
        recommendation = "🎉 Отличный запас!"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Пополнить резерв", callback_data="reserve_topup")]
    ])

    await message.answer(
        f"💰 <b>БАЛАНС СИСТЕМЫ</b>\n\n"
        f"💵 Текущий баланс: <b>{total_balance:.2f} USDT</b>\n"
        f"📊 Статус: {reserve_emoji} <b>{reserve_status}</b>\n\n"
        f"<i>{recommendation}</i>",
        parse_mode='HTML',
        reply_markup=kb
    )


@router.callback_query(F.data == "reserve_topup")
async def admin_topup_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик пополнения резерва"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    from services.crypto_service import CryptoService
    crypto_service = CryptoService()

    total_balance = await crypto_service.get_balance()

    await callback.message.edit_text(
        f"💵 <b>Пополнение резерва системы</b>\n\n"
        f"💰 Текущий баланс кошелька: <b>{total_balance:.2f} USDT</b>\n\n"
        f"Введите сумму в USDT для пополнения:",
        parse_mode='HTML'
    )
    await state.set_state(ReserveTopupStates.waiting_amount)


@router.message(ReserveTopupStates.waiting_amount)
async def process_reserve_topup_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения резерва"""
    if not is_admin(message.from_user.id):
        return

    try:
        amount = float(message.text.strip())

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        if amount < 1:
            await message.answer("❌ Минимальная сумма пополнения: 1 USDT")
            return

        from services.crypto_service import CryptoService
        crypto_service = CryptoService()

        # Получаем username бота
        bot_username = (await message.bot.get_me()).username

        # Создаем инвойс для пополнения резерва
        invoice_data = await crypto_service.create_invoice(
            user_id=message.from_user.id,
            amount=amount,
            description=f"Пополнение резерва системы на {amount} USDT",
            payload_prefix="reserve",
            bot_username=bot_username
        )

        if invoice_data:
            await message.answer(
                f"💳 <b>ИНВОЙС ДЛЯ ПОПОЛНЕНИЯ РЕЗЕРВА</b>\n\n"
                f"💰 Сумма: <b>{amount:.2f} USDT</b>\n"
                f"📎 Ссылка для оплаты: {invoice_data['pay_url']}\n\n"
                f"⚠️ <i>После оплаты средства поступят в резерв системы.</i>\n"
                f"🔧 <i>Используется тот же кошелек, что и для выплат.</i>",
                reply_markup=get_admin_reply_keyboard(),
                parse_mode='HTML'
            )

            # Уведомляем других админов
            for admin_id in ADMIN_IDS:
                if admin_id != message.from_user.id:
                    try:
                        await message.bot.send_message(
                            admin_id,
                            f"👤 Админ @{message.from_user.username or 'N/A'} создал инвойс\n"
                            f"💰 Сумма: {amount:.2f} USDT\n"
                            f"💳 Для пополнения резерва",
                            parse_mode='HTML'
                        )
                    except:
                        pass
        else:
            await message.answer("❌ Не удалось создать инвойс. Попробуйте позже.")

    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (например: 10.5)")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

    await state.clear()


@router.message(F.text == "🧾 Заявки на вывод")
async def show_withdrawal_menu(message: Message):
    """Показать меню заявок на вывод"""
    if not is_admin(message.from_user.id):
        return

    pending = database.count_withdrawals_by_status("pending")
    approved = database.count_withdrawals_by_status("approved")
    refunded = database.count_withdrawals_by_status("refunded")
    declined = database.count_withdrawals_by_status("declined")

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text=f"🕓 Ожидающие [{pending}]", callback_data="wd_list_pending")
    kb.button(text=f"✅ Подтвержд. [{approved}]", callback_data="wd_list_approved")
    kb.button(text=f"↩️ Отклонённые [{refunded}]", callback_data="wd_list_refunded")
    kb.button(text=f"❌ Без возврата [{declined}]", callback_data="wd_list_declined")
    kb.adjust(2, 2)

    await message.answer(
        "<b>Выберите категорию заявок:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("wd_list_"))
async def show_withdrawal_list(callback: CallbackQuery):
    """Показать список заявок по статусу"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    status = callback.data.split("_")[2]
    withdrawals = database.get_withdrawals_by_status(status)

    if not withdrawals:
        await callback.answer("Пусто.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()

    for wd in withdrawals[:20]:  # Показываем первые 20
        wid = wd["id"]
        amount = wd["amount"]
        user_id = wd["user_id"]
        kb.button(text=f"ID:{wid} | {amount:.2f}$ | User:{user_id}", callback_data=f"wd_view:{wid}")

    kb.button(text="🔙 Назад", callback_data="wd_back")
    kb.adjust(1)

    await callback.message.edit_text(
        f"<b>Заявки со статусом: {status}</b>\n\n"
        f"Всего: {len(withdrawals)}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "wd_back")
async def withdrawal_back(callback: CallbackQuery):
    """Вернуться к меню заявок"""
    if not is_admin(callback.from_user.id):
        return

    await callback.answer()

    pending = database.count_withdrawals_by_status("pending")
    approved = database.count_withdrawals_by_status("approved")
    refunded = database.count_withdrawals_by_status("refunded")
    declined = database.count_withdrawals_by_status("declined")

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text=f"🕓 Ожидающие [{pending}]", callback_data="wd_list_pending")
    kb.button(text=f"✅ Подтвержд. [{approved}]", callback_data="wd_list_approved")
    kb.button(text=f"↩️ Отклонённые [{refunded}]", callback_data="wd_list_refunded")
    kb.button(text=f"❌ Без возврата [{declined}]", callback_data="wd_list_declined")
    kb.adjust(2, 2)

    await callback.message.edit_text(
        "<b>Выберите категорию заявок:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("wd_view:"))
async def view_withdrawal(callback: CallbackQuery):
    """Просмотр заявки на вывод"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return

    user_id = wd['user_id']
    amount = wd['amount']
    status = wd['status']
    created_at = wd['created_at'][:19]

    from services.crypto_service import CryptoService
    from services.currency_converter import CurrencyConverter

    crypto_service = CryptoService()

    # Конвертируем рубли в USDT для отображения
    usdt_amount = await CurrencyConverter.rub_to_usdt(amount)
    rate = await CurrencyConverter.get_usdt_rub_rate()

    # Получаем баланс резерва
    reserve_balance = await crypto_service.get_balance()

    # Определяем статус резерва
    if reserve_balance < 1:
        reserve_status = "🚨 КРИТИЧЕСКИ НИЗКИЙ"
        reserve_emoji = "🔴"
    elif reserve_balance < 10:
        reserve_status = "⚠️ НИЗКИЙ"
        reserve_emoji = "🟡"
    elif reserve_balance < 50:
        reserve_status = "ℹ️ СРЕДНИЙ"
        reserve_emoji = "🟢"
    else:
        reserve_status = "✅ ДОСТАТОЧНЫЙ"
        reserve_emoji = "💚"

    # Получаем информацию о пользователе
    try:
        user = await callback.bot.get_chat(user_id)
        username = f"@{user.username}" if user.username else "—"
        full_name = user.full_name or "—"
    except:
        username = "—"
        full_name = "—"

    text = f"""📨 <b>ЗАЯВКА НА ВЫВОД</b>

👤 Пользователь: {full_name}
🆔 Username: <code>{username}</code>
🔢 User ID: <code>{user_id}</code>

💵 Сумма вывода: <b>{amount:.2f} ₽</b> (~{usdt_amount:.2f} USDT)
📊 Курс: 1 USDT = {rate:.2f} ₽
🔖 ID заявки: <code>{wid}</code>
⏳ Статус: <b>{status}</b>
📅 Создана: <code>{created_at}</code>
━━━━━━━━━━━━━━━━━━
💰 Резерв: <b>{reserve_balance:.2f} USDT</b>
📊 Статус резерва: {reserve_emoji} <b>{reserve_status}</b>
"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()

    # Кнопки для просмотра информации о пользователе
    kb.button(text="💬 Чаты", callback_data=f"wd_info_chats:{wid}")
    kb.button(text="📢 Каналы", callback_data=f"wd_info_channels:{wid}")
    kb.button(text="🤖 Боты", callback_data=f"wd_info_bots:{wid}")
    kb.button(text="👥 Рефералы", callback_data=f"wd_info_refs:{wid}")
    kb.adjust(2, 2)

    if status == "pending":
        kb.button(text="✅ Принять", callback_data=f"wd_confirm:{wid}")
        kb.button(text="❌ Отклонить", callback_data=f"wd_decline:{wid}")
        kb.adjust(2, 2, 2)

    kb.button(text="🔙 Назад", callback_data=f"wd_list_{status}")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        # Игнорируем ошибку, если сообщение не изменилось
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("wd_info_chats:"))
async def view_withdrawal_chats(callback: CallbackQuery):
    """Просмотр чатов пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return

    user_id = wd['user_id']
    user_info = database.get_user_detailed_info(user_id)
    chats = user_info['chats']

    if not chats:
        text = f"""💬 <b>Чаты пользователя</b>

🆔 User ID: <code>{user_id}</code>

<i>У пользователя нет подключенных чатов</i>"""
    else:
        chat_lines = []
        for idx, chat in enumerate(chats[:10], 1):
            status = "🟢" if chat['gate_enabled'] else "🔴"
            title = chat['chat_title'] or f"Chat {chat['chat_id']}"
            chat_lines.append(f"{idx}. {status} <b>{title}</b>\n   └ ID: <code>{chat['chat_id']}</code>")

        text = f"""💬 <b>Чаты пользователя</b>

🆔 User ID: <code>{user_id}</code>
📊 Всего чатов: <code>{len(chats)}</code>

{chr(10).join(chat_lines)}"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Чаты", callback_data=f"wd_info_chats:{wid}")
    kb.button(text="📢 Каналы", callback_data=f"wd_info_channels:{wid}")
    kb.button(text="🤖 Боты", callback_data=f"wd_info_bots:{wid}")
    kb.button(text="👥 Рефералы", callback_data=f"wd_info_refs:{wid}")
    kb.adjust(2, 2)
    kb.button(text="🔙 К заявке", callback_data=f"wd_view:{wid}")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("wd_info_channels:"))
async def view_withdrawal_channels(callback: CallbackQuery):
    """Просмотр каналов пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return

    user_id = wd['user_id']
    user_info = database.get_user_detailed_info(user_id)
    resources = user_info['resources']
    contests = user_info['contests']

    if not resources and not contests:
        text = f"""📢 <b>Каналы пользователя</b>

🆔 User ID: <code>{user_id}</code>

<i>У пользователя нет добавленных каналов</i>"""
    else:
        resource_lines = []
        if resources:
            for idx, res in enumerate(resources[:10], 1):
                resource_lines.append(f"{idx}. <b>{res['title']}</b>\n   └ {res['url']}")

        contest_lines = []
        if contests:
            for idx, contest in enumerate(contests[:5], 1):
                status = "🟢" if contest['status'] == 'active' else "✅"
                contest_lines.append(
                    f"{idx}. {status} <b>{contest['title']}</b>\n"
                    f"   └ Участников: <code>{contest.get('participants_count', 0)}</code>"
                )

        text = f"""📢 <b>Каналы пользователя</b>

🆔 User ID: <code>{user_id}</code>
📊 Ресурсов: <code>{len(resources)}</code>
🎉 Конкурсов: <code>{len(contests)}</code>

"""
        if resource_lines:
            text += f"<b>Ресурсы:</b>\n{chr(10).join(resource_lines)}\n\n"
        if contest_lines:
            text += f"<b>Конкурсы:</b>\n{chr(10).join(contest_lines)}"

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Чаты", callback_data=f"wd_info_chats:{wid}")
    kb.button(text="📢 Каналы", callback_data=f"wd_info_channels:{wid}")
    kb.button(text="🤖 Боты", callback_data=f"wd_info_bots:{wid}")
    kb.button(text="👥 Рефералы", callback_data=f"wd_info_refs:{wid}")
    kb.adjust(2, 2)
    kb.button(text="🔙 К заявке", callback_data=f"wd_view:{wid}")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("wd_info_bots:"))
async def view_withdrawal_bots(callback: CallbackQuery):
    """Просмотр ботов пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return

    user_id = wd['user_id']
    user_info = database.get_user_detailed_info(user_id)

    text = f"""🤖 <b>Боты пользователя</b>

🆔 User ID: <code>{user_id}</code>

<b>Финансовая статистика:</b>
├ Заработано: <code>{user_info['total_earned']:.2f} ₽</code>
├ Пополнено: <code>{user_info['total_topups']:.2f} ₽</code>
└ Выведено: <code>{user_info['total_withdrawals']:.2f} ₽</code>

<i>Раздел в разработке</i>"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Чаты", callback_data=f"wd_info_chats:{wid}")
    kb.button(text="📢 Каналы", callback_data=f"wd_info_channels:{wid}")
    kb.button(text="🤖 Боты", callback_data=f"wd_info_bots:{wid}")
    kb.button(text="👥 Рефералы", callback_data=f"wd_info_refs:{wid}")
    kb.adjust(2, 2)
    kb.button(text="🔙 К заявке", callback_data=f"wd_view:{wid}")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("wd_info_refs:"))
async def view_withdrawal_refs(callback: CallbackQuery):
    """Просмотр рефералов пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd:
        await callback.answer("❌ Заявка не найдена.", show_alert=True)
        return

    user_id = wd['user_id']

    text = f"""👥 <b>Рефералы пользователя</b>

🆔 User ID: <code>{user_id}</code>

<i>Реферальная система в разработке</i>"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Чаты", callback_data=f"wd_info_chats:{wid}")
    kb.button(text="📢 Каналы", callback_data=f"wd_info_channels:{wid}")
    kb.button(text="🤖 Боты", callback_data=f"wd_info_bots:{wid}")
    kb.button(text="👥 Рефералы", callback_data=f"wd_info_refs:{wid}")
    kb.adjust(2, 2)
    kb.button(text="🔙 К заявке", callback_data=f"wd_view:{wid}")

    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("wd_confirm:"))
async def confirm_withdrawal(callback: CallbackQuery):
    """Подтвердить заявку на вывод"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer("🔄 Создаем чек...")

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd or wd['status'] != 'pending':
        await callback.answer("❌ Заявка недоступна", show_alert=True)
        return

    from services.crypto_service import CryptoService
    from services.currency_converter import CurrencyConverter

    crypto_service = CryptoService()

    # Конвертируем рубли в USDT
    rub_amount = wd['amount']
    usdt_amount = await CurrencyConverter.rub_to_usdt(rub_amount)

    # Получаем курс для отображения
    rate = await CurrencyConverter.get_usdt_rub_rate()

    # Создаем чек в USDT
    success, check_url = await crypto_service.create_check(
        amount=usdt_amount,
        description=f"Вывод средств пользователя {wd['user_id']}"
    )

    if not success or not check_url:
        await callback.answer("❌ Ошибка создания чека", show_alert=True)
        return

    # Обновляем статус заявки (деньги списываются автоматически через withdrawal_requests)
    database.approve_withdrawal(wid, callback.from_user.id, check_url)

    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            wd['user_id'],
            f"<b>✅ Ваша заявка на вывод одобрена!</b>\n\n"
            f"💰 Сумма: <b>{rub_amount:.2f} ₽</b> (~{usdt_amount:.2f} USDT)\n"
            f"🔖 ID заявки: <code>{wid}</code>\n"
            f"📎 Ссылка на чек: {check_url}\n\n"
            f"<i>Перейдите по ссылке, чтобы активировать чек в CryptoBot</i>",
            parse_mode="HTML"
        )
    except:
        pass

    await callback.message.edit_text(
        f"✅ <b>Заявка #{wid} одобрена!</b>\n\n"
        f"💰 Сумма: {rub_amount:.2f} ₽ → {usdt_amount:.2f} USDT\n"
        f"📊 Курс: 1 USDT = {rate:.2f} ₽\n"
        f"📎 Чек создан и отправлен пользователю",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("wd_decline:"))
async def decline_withdrawal(callback: CallbackQuery):
    """Отклонить заявку без возврата"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd or wd['status'] != 'pending':
        await callback.answer("❌ Заявка недоступна", show_alert=True)
        return

    # Отклоняем без возврата (деньги списываются автоматически через withdrawal_requests)
    database.decline_withdrawal(wid, callback.from_user.id, refund=False)

    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            wd['user_id'],
            f"<b>❌ Ваша заявка на вывод отклонена</b>\n\n"
            f"💰 Сумма: <b>{wd['amount']:.2f} ₽</b>\n"
            f"🔖 ID заявки: <code>{wid}</code>\n\n"
            f"<i>Средства списаны с баланса</i>",
            parse_mode="HTML"
        )
    except:
        pass

    await callback.message.edit_text(
        f"❌ <b>Заявка #{wid} отклонена</b>\n\n"
        f"Средства списаны с баланса пользователя",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("wd_refund:"))
async def refund_withdrawal(callback: CallbackQuery):
    """Отклонить заявку с возвратом"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа")
        return

    await callback.answer()

    wid = int(callback.data.split(":")[1])
    wd = database.get_withdrawal_request(wid)

    if not wd or wd['status'] != 'pending':
        await callback.answer("❌ Заявка недоступна", show_alert=True)
        return

    # Отклоняем с возвратом
    database.decline_withdrawal(wid, callback.from_user.id, refund=True)

    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            wd['user_id'],
            f"<b>↩️ Ваша заявка на вывод отклонена</b>\n\n"
            f"💰 Сумма: <b>{wd['amount']:.2f} ₽</b>\n"
            f"🔖 ID заявки: <code>{wid}</code>\n\n"
            f"<i>✅ Средства возвращены на ваш баланс</i>",
            parse_mode="HTML"
        )
    except:
        pass

    await callback.message.edit_text(
        f"↩️ <b>Заявка #{wid} отклонена с возвратом</b>\n\n"
        f"Средства возвращены пользователю",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_contest_price)
async def process_contest_price(message: Message, state: FSMContext):
    """Обработка новой цены за подписку в конкурсе"""
    if not is_admin(message.from_user.id):
        return

    try:
        new_price = float(message.text)
        if new_price < 0:
            await message.answer("Цена не может быть отрицательной")
            return

        # TODO: Save to database
        await message.answer(
            f"✅ Цена за подписку в конкурсе обновлена: {new_price:.2f} ₽\n\n"
            f"⚠️ Примечание: для полного применения изменений требуется перезапуск бота",
            reply_markup=get_admin_back_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат. Отправьте число (например: 0.5)")


# Обработчики для графиков статистики

@router.callback_query(F.data.startswith("admin_stats_graph_"))
async def admin_stats_graph_callback(callback: CallbackQuery):
    """Генерация графика общей статистики"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer("Генерирую график...")

    # Извлекаем период из callback_data
    period = int(callback.data.split("_")[-1])

    from services.database_service_stats import DatabaseStatsService
    from services.chart_generator import generate_statistics_chart, cleanup_old_charts
    from aiogram.types import FSInputFile

    stats_service = DatabaseStatsService()

    # Получаем данные за период
    users_data = stats_service.get_users_stats_by_period(period)
    
    # Если нет данных, создаем пустой набор
    if not users_data:
        from datetime import datetime, timedelta
        users_data = [(datetime.now() - timedelta(days=i), 0) for i in range(period)]

    # Генерируем график
    chart_path = generate_statistics_chart(users_data, period, "admin")

    # Отправляем график
    photo = FSInputFile(chart_path)
    await callback.message.answer_photo(
        photo=photo,
        caption=f"📊 Статистика новых пользователей за {period} дней"
    )

    # Очищаем старые графики
    cleanup_old_charts()


@router.callback_query(F.data.startswith("resource_stats_graph_"))
async def resource_stats_graph_callback(callback: CallbackQuery):
    """Генерация графика статистики ресурсов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer("Генерирую график...")

    period = int(callback.data.split("_")[-1])

    from services.database_service_stats import DatabaseStatsService
    from services.chart_generator import generate_statistics_chart, cleanup_old_charts
    from aiogram.types import FSInputFile

    stats_service = DatabaseStatsService()
    resources_data = stats_service.get_resources_stats_by_period(period)

    if not resources_data:
        from datetime import datetime, timedelta
        resources_data = [(datetime.now() - timedelta(days=i), 0) for i in range(period)]

    chart_path = generate_statistics_chart(resources_data, period, "resources")

    photo = FSInputFile(chart_path)
    await callback.message.answer_photo(
        photo=photo,
        caption=f"📊 Статистика новых ресурсов за {period} дней"
    )

    cleanup_old_charts()


# ==================== МОДЕРАЦИЯ РЕСУРСОВ ====================

@router.callback_query(F.data == "admin_moderation")
async def admin_moderation_callback(callback: CallbackQuery):
    """Показать список ресурсов на модерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    pending_resources = database.get_pending_resources()
    pending_count = len(pending_resources)

    if not pending_resources:
        await callback.message.edit_text(
            "✅ <b>Модерация ресурсов</b>\n\n"
            "Нет ресурсов на модерации.",
            parse_mode="HTML",
            reply_markup=get_admin_back_keyboard()
        )
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()

    for resource in pending_resources[:20]:  # Показываем первые 20
        rid = resource["id"]
        title = resource["title"]
        user_id = resource["owner_user_id"]
        username = resource.get("owner_username") or "N/A"

        kb.button(
            text=f"ID:{rid} | @{username} | {title[:30]}",
            callback_data=f"mod_view:{rid}"
        )

    kb.button(text="🔙 Назад", callback_data="admin_panel")
    kb.adjust(1)

    await callback.message.edit_text(
        f"✅ <b>Модерация ресурсов</b>\n\n"
        f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
        f"Выберите ресурс для проверки:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_view:"))
async def mod_view_callback(callback: CallbackQuery):
    """Просмотр ресурса на модерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    resource_id = int(callback.data.split(":")[1])
    resource = database.get_resource_by_id(resource_id)

    if not resource or resource['status'] != 'pending':
        await callback.answer("❌ Ресурс не найден или уже обработан", show_alert=True)
        return

    user_id = resource['owner_user_id']
    username = resource.get('owner_username') or 'N/A'
    title = resource['title']
    url = resource['url']
    created_at = resource['created_at'][:19]

    text = f"""📢 <b>РЕСУРС НА МОДЕРАЦИИ</b>

👤 Пользователь: <code>@{username}</code>
🆔 User ID: <code>{user_id}</code>

📝 Название: <b>{title}</b>
🔗 Ссылка: <code>{url}</code>
📅 Создан: <code>{created_at}</code>
🔖 ID ресурса: <code>{resource_id}</code>
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_moderation_actions_keyboard(resource_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_accept:"))
async def mod_accept_callback(callback: CallbackQuery):
    """Принять ресурс - показать выбор категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    resource_id = int(callback.data.split(":")[1])
    resource = database.get_resource_by_id(resource_id)

    if not resource or resource['status'] != 'pending':
        await callback.answer("❌ Ресурс не найден или уже обработан", show_alert=True)
        return

    await callback.message.edit_text(
        f"📢 <b>Выберите категорию для ресурса</b>\n\n"
        f"📝 Название: <b>{resource['title']}</b>\n"
        f"🔗 Ссылка: <code>{resource['url']}</code>",
        reply_markup=get_category_keyboard(resource_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("mod_category:"))
async def mod_category_callback(callback: CallbackQuery):
    """Установить категорию и одобрить ресурс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    resource_id = int(parts[1])
    category = parts[2]

    resource = database.get_resource_by_id(resource_id)

    if not resource or resource['status'] != 'pending':
        await callback.answer("❌ Ресурс не найден или уже обработан", show_alert=True)
        return

    # Одобряем ресурс с категорией
    success = database.approve_resource(resource_id, callback.from_user.id, category)

    if success:
        await callback.answer("✅ Ресурс одобрен!", show_alert=True)

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                resource['owner_user_id'],
                f"✅ <b>Ваш ресурс одобрен!</b>\n\n"
                f"📝 Название: <b>{resource['title']}</b>\n"
                f"🔗 Ссылка: <code>{resource['url']}</code>\n"
                f"📂 Категория: <b>{category}</b>\n\n"
                f"Теперь вы можете использовать его при создании конкурсов.",
                parse_mode="HTML"
            )
        except:
            pass

        # Возвращаемся к списку модерации
        pending_resources = database.get_pending_resources()
        pending_count = len(pending_resources)

        if not pending_resources:
            await callback.message.edit_text(
                "✅ <b>Модерация ресурсов</b>\n\n"
                "Нет ресурсов на модерации.",
                parse_mode="HTML",
                reply_markup=get_admin_back_keyboard()
            )
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        kb = InlineKeyboardBuilder()

        for res in pending_resources[:20]:
            rid = res["id"]
            title = res["title"]
            username = res.get("owner_username") or "N/A"

            kb.button(
                text=f"ID:{rid} | @{username} | {title[:30]}",
                callback_data=f"mod_view:{rid}"
            )

        kb.button(text="🔙 Назад", callback_data="admin_panel")
        kb.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>Модерация ресурсов</b>\n\n"
            f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
            f"Выберите ресурс для проверки:",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при одобрении", show_alert=True)


@router.callback_query(F.data.startswith("mod_decline:"))
async def mod_decline_callback(callback: CallbackQuery):
    """Отклонить ресурс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    resource_id = int(callback.data.split(":")[1])
    resource = database.get_resource_by_id(resource_id)

    if not resource or resource['status'] != 'pending':
        await callback.answer("❌ Ресурс не найден или уже обработан", show_alert=True)
        return

    # Отклоняем ресурс
    success = database.decline_resource(resource_id, callback.from_user.id)

    if success:
        await callback.answer("❌ Ресурс отклонен", show_alert=True)

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                resource['owner_user_id'],
                f"❌ <b>Ваш ресурс не прошел модерацию</b>\n\n"
                f"📝 Название: <b>{resource['title']}</b>\n"
                f"🔗 Ссылка: <code>{resource['url']}</code>\n\n"
                f"Пожалуйста, проверьте соответствие ресурса правилам платформы.",
                parse_mode="HTML"
            )
        except:
            pass

        # Возвращаемся к списку модерации
        pending_resources = database.get_pending_resources()
        pending_count = len(pending_resources)

        if not pending_resources:
            await callback.message.edit_text(
                "✅ <b>Модерация ресурсов</b>\n\n"
                "Нет ресурсов на модерации.",
                parse_mode="HTML",
                reply_markup=get_admin_back_keyboard()
            )
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        kb = InlineKeyboardBuilder()

        for res in pending_resources[:20]:
            rid = res["id"]
            title = res["title"]
            username = res.get("owner_username") or "N/A"

            kb.button(
                text=f"ID:{rid} | @{username} | {title[:30]}",
                callback_data=f"mod_view:{rid}"
            )

        kb.button(text="🔙 Назад", callback_data="admin_panel")
        kb.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>Модерация ресурсов</b>\n\n"
            f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
            f"Выберите ресурс для проверки:",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отклонении", show_alert=True)


# ==================== МОДЕРАЦИЯ ЧАТОВ ====================

@router.callback_query(F.data == "admin_moderation_chats")
async def admin_moderation_chats_callback(callback: CallbackQuery):
    """Показать список чатов на модерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    pending_chats = database.get_pending_chats()
    pending_count = len(pending_chats)

    if not pending_chats:
        await callback.message.edit_text(
            "✅ <b>Модерация чатов</b>\n\n"
            "Нет чатов на модерации.",
            parse_mode="HTML",
            reply_markup=get_admin_back_keyboard()
        )
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()

    for chat in pending_chats[:20]:  # Показываем первые 20
        chat_id = chat["chat_id"]
        title = chat.get("chat_title") or f"Chat {chat_id}"
        user_id = chat["owner_user_id"]

        kb.button(
            text=f"ID:{chat_id} | User:{user_id} | {title[:30]}",
            callback_data=f"chat_mod_view:{chat_id}"
        )

    kb.button(text="🔙 Назад", callback_data="admin_panel")
    kb.adjust(1)

    await callback.message.edit_text(
        f"💬 <b>Модерация чатов</b>\n\n"
        f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
        f"Выберите чат для проверки:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chat_mod_view:"))
async def chat_mod_view_callback(callback: CallbackQuery):
    """Просмотр чата на модерации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    chat_id = int(callback.data.split(":")[1])
    chat = database.get_chat_by_id(chat_id)

    if not chat or chat['status'] != 'pending':
        await callback.answer("❌ Чат не найден или уже обработан", show_alert=True)
        return

    user_id = chat['owner_user_id']
    title = chat.get('chat_title') or f"Chat {chat_id}"
    chat_link = chat.get('chat_link') or 'не указана'
    created_at = chat['created_at'][:19]

    text = f"""💬 <b>ЧАТ НА МОДЕРАЦИИ</b>

👤 Владелец: <code>{user_id}</code>

📝 Название: <b>{title}</b>
🔗 Ссылка: <code>{chat_link}</code>
🆔 Chat ID: <code>{chat_id}</code>
📅 Добавлен: <code>{created_at}</code>
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_chat_moderation_actions_keyboard(chat_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chat_mod_accept:"))
async def chat_mod_accept_callback(callback: CallbackQuery):
    """Принять чат - показать выбор категории"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    await callback.answer()

    chat_id = int(callback.data.split(":")[1])
    chat = database.get_chat_by_id(chat_id)

    if not chat or chat['status'] != 'pending':
        await callback.answer("❌ Чат не найден или уже обработан", show_alert=True)
        return

    title = chat.get('chat_title') or f"Chat {chat_id}"
    chat_link = chat.get('chat_link') or 'не указана'

    await callback.message.edit_text(
        f"💬 <b>Выберите категорию для чата</b>\n\n"
        f"📝 Название: <b>{title}</b>\n"
        f"🔗 Ссылка: <code>{chat_link}</code>",
        reply_markup=get_chat_category_keyboard(chat_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chat_mod_category:"))
async def chat_mod_category_callback(callback: CallbackQuery):
    """Установить категорию и одобрить чат"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    chat_id = int(parts[1])
    category = parts[2]

    chat = database.get_chat_by_id(chat_id)

    if not chat or chat['status'] != 'pending':
        await callback.answer("❌ Чат не найден или уже обработан", show_alert=True)
        return

    # Одобряем чат с категорией
    success = database.approve_chat(chat_id, callback.from_user.id, category)

    if success:
        await callback.answer("✅ Чат одобрен!", show_alert=True)

        title = chat.get('chat_title') or f"Chat {chat_id}"

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                chat['owner_user_id'],
                f"✅ <b>Ваш чат одобрен!</b>\n\n"
                f"📝 Название: <b>{title}</b>\n"
                f"🆔 Chat ID: <code>{chat_id}</code>\n"
                f"📂 Категория: <b>{category}</b>\n\n"
                f"Теперь вы можете использовать его для продажи трафика.",
                parse_mode="HTML"
            )
        except:
            pass

        # Возвращаемся к списку модерации
        pending_chats = database.get_pending_chats()
        pending_count = len(pending_chats)

        if not pending_chats:
            await callback.message.edit_text(
                "💬 <b>Модерация чатов</b>\n\n"
                "Нет чатов на модерации.",
                parse_mode="HTML",
                reply_markup=get_admin_back_keyboard()
            )
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        kb = InlineKeyboardBuilder()

        for ch in pending_chats[:20]:
            cid = ch["chat_id"]
            title = ch.get("chat_title") or f"Chat {cid}"
            user_id = ch["owner_user_id"]

            kb.button(
                text=f"ID:{cid} | User:{user_id} | {title[:30]}",
                callback_data=f"chat_mod_view:{cid}"
            )

        kb.button(text="🔙 Назад", callback_data="admin_panel")
        kb.adjust(1)

        await callback.message.edit_text(
            f"💬 <b>Модерация чатов</b>\n\n"
            f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
            f"Выберите чат для проверки:",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при одобрении", show_alert=True)


@router.callback_query(F.data.startswith("chat_mod_decline:"))
async def chat_mod_decline_callback(callback: CallbackQuery):
    """Отклонить чат"""
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    chat_id = int(callback.data.split(":")[1])
    chat = database.get_chat_by_id(chat_id)

    if not chat or chat['status'] != 'pending':
        await callback.answer("❌ Чат не найден или уже обработан", show_alert=True)
        return

    # Отклоняем чат
    success = database.decline_chat(chat_id, callback.from_user.id)

    if success:
        await callback.answer("❌ Чат отклонен", show_alert=True)

        title = chat.get('chat_title') or f"Chat {chat_id}"

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                chat['owner_user_id'],
                f"❌ <b>Ваш чат не прошел модерацию</b>\n\n"
                f"📝 Название: <b>{title}</b>\n"
                f"🆔 Chat ID: <code>{chat_id}</code>\n\n"
                f"Пожалуйста, проверьте соответствие чата правилам платформы.",
                parse_mode="HTML"
            )
        except:
            pass

        # Возвращаемся к списку модерации
        pending_chats = database.get_pending_chats()
        pending_count = len(pending_chats)

        if not pending_chats:
            await callback.message.edit_text(
                "💬 <b>Модерация чатов</b>\n\n"
                "Нет чатов на модерации.",
                parse_mode="HTML",
                reply_markup=get_admin_back_keyboard()
            )
            return

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        kb = InlineKeyboardBuilder()

        for ch in pending_chats[:20]:
            cid = ch["chat_id"]
            title = ch.get("chat_title") or f"Chat {cid}"
            user_id = ch["owner_user_id"]

            kb.button(
                text=f"ID:{cid} | User:{user_id} | {title[:30]}",
                callback_data=f"chat_mod_view:{cid}"
            )

        kb.button(text="🔙 Назад", callback_data="admin_panel")
        kb.adjust(1)

        await callback.message.edit_text(
            f"💬 <b>Модерация чатов</b>\n\n"
            f"📊 Всего на модерации: <code>{pending_count}</code>\n\n"
            f"Выберите чат для проверки:",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Ошибка при отклонении", show_alert=True)

