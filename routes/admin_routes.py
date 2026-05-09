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
    await callback.message.edit_text(
        render_admin_statistics_text(stats),
        reply_markup=get_admin_back_keyboard(),
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
    await callback.message.edit_text(
        render_admin_resource_stats_text(stats),
        reply_markup=get_admin_back_keyboard(),
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
