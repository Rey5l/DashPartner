from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timezone

from services.database_service import DatabaseService
from services.crypto_service import CryptoService

router = Router()
database = DatabaseService()
crypto_service = CryptoService()


class TopupStates(StatesGroup):
    waiting_amount = State()


class WithdrawStates(StatesGroup):
    waiting_amount = State()


@router.callback_query(F.data == "topup")
async def topup_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки пополнения"""
    await callback.answer()
    await state.set_state(TopupStates.waiting_amount)
    await callback.message.answer(
        "<b>💳 Пополнение баланса</b>\n\n"
        "Введите сумму пополнения в USDT (минимум 1 USDT):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_topup")]
            ]
        )
    )


@router.callback_query(F.data == "cancel_topup")
async def cancel_topup_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена пополнения"""
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Пополнение отменено.")


@router.message(TopupStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения"""
    try:
        amount = float(message.text.strip())

        if amount < 1:
            await message.answer("⚠️ Минимальная сумма пополнения: 1 USDT")
            return

        # Получаем username бота
        bot_username = (await message.bot.get_me()).username

        # Создаем инвойс через CryptoBot
        invoice_data = await crypto_service.create_invoice(
            user_id=message.from_user.id,
            amount=amount,
            description=f"Пополнение баланса пользователя {message.from_user.id}",
            payload_prefix="topup",
            bot_username=bot_username
        )

        if not invoice_data:
            await message.answer(
                "❌ Ошибка создания платежа. Попробуйте позже.",
                parse_mode="HTML"
            )
            await state.clear()
            return

        # Сохраняем транзакцию в БД
        database.create_topup_transaction(
            user_id=message.from_user.id,
            invoice_id=invoice_data['invoice_id'],
            amount=amount
        )

        # Отправляем ссылку на оплату
        await message.answer(
            f"<b>💳 Инвойс для пополнения</b>\n\n"
            f"💰 Сумма: <b>{amount:.2f} USDT</b>\n"
            f"📎 Ссылка для оплаты: {invoice_data['pay_url']}\n\n"
            f"⚠️ <i>После оплаты нажмите кнопку «Проверить оплату»</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить", url=invoice_data['pay_url'])],
                    [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_topup:{invoice_data['invoice_id']}")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_topup")]
                ]
            )
        )

        await state.clear()

    except ValueError:
        await message.answer("⚠️ Введите корректную сумму (число)")


@router.callback_query(F.data.startswith("check_topup:"))
async def check_topup_callback(callback: CallbackQuery):
    """Проверка оплаты пополнения"""
    await callback.answer("🔄 Проверяем оплату...")

    invoice_id = callback.data.split(":")[1]

    # Проверяем статус инвойса через CryptoBot API
    invoice_info = await crypto_service.check_invoice(invoice_id)

    if not invoice_info:
        await callback.answer("⚠️ Ошибка проверки платежа", show_alert=True)
        return

    status = invoice_info.get("status")

    if status == "paid":
        # Проверяем, не был ли уже зачислен
        transaction = database.get_topup_transaction(invoice_id)

        if transaction and transaction['status'] == 'paid':
            await callback.answer("⚠️ Этот платёж уже был зачислен ранее", show_alert=True)
            return

        # Зачисляем средства
        success = database.mark_topup_paid(invoice_id)

        if success:
            amount = transaction['amount']
            await callback.message.answer(
                f"<b>✅ Пополнение успешно!</b>\n\n"
                f"💰 Зачислено: <b>{amount:.2f} USDT</b>\n"
                f"📊 Средства добавлены на ваш баланс",
                parse_mode="HTML"
            )
            await callback.answer("✅ Оплата подтверждена!", show_alert=True)
        else:
            await callback.answer("⚠️ Ошибка зачисления средств", show_alert=True)
    else:
        await callback.answer("⚠️ Платёж ещё не оплачен", show_alert=True)


@router.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки вывода"""
    await callback.answer()

    # Получаем баланс пользователя
    stats = database.get_owner_stats(callback.from_user.id)
    balance = stats.get('balance', 0.0)

    # Константы
    MIN_WITHDRAWAL = 70.0  # Минимальный вывод
    MIN_BALANCE_REQUIRED = 100.0  # Минимальный баланс для вывода
    RESERVE_PERCENT = 30.0  # Резерв 30%
    COMMISSION_PERCENT = 5.0  # Комиссия 5%

    # Расчеты
    reserve_amount = balance * (RESERVE_PERCENT / 100)  # 30% резерв
    available_balance = balance - reserve_amount  # Доступно без резерва

    # Сумма с учетом комиссии (то что получит пользователь)
    can_request = available_balance * (1 - COMMISSION_PERCENT / 100)

    if balance < MIN_BALANCE_REQUIRED:
        await callback.message.answer(
            f"<tg-emoji emoji-id='5310191758255099001'>👛</tg-emoji> <b>Вывод средств</b>\n\n"
            f"Минимальный вывод — <b>{MIN_WITHDRAWAL:.0f}₽</b>\n\n"
            f"Чтобы получить <b>{MIN_WITHDRAWAL:.2f}₽</b>, нужно накопить минимум <b>{MIN_BALANCE_REQUIRED:.2f}₽</b> баланса.\n\n"
            f"Резерв <b>{RESERVE_PERCENT:.0f}%</b> от доступного заработка\n"
            f"остаётся на вашем балансе на случай отписок.\n\n"
            f"Комиссия вывода: <b>{COMMISSION_PERCENT:.0f}%</b>.\n"
            f"Резерв считается отдельно от комиссии.\n\n"
            f"<tg-emoji emoji-id='4958926882994127612'>💰</tg-emoji> Баланс: <b>{balance:.2f} ₽</b>\n"
            f"<tg-emoji emoji-id='5292253342012025042'>📈</tg-emoji> Можно запросить: <b>{can_request:.2f}₽</b>\n"
            f"<tg-emoji emoji-id='5312057711091813718'>💳</tg-emoji> Резерв на балансе: <b>{reserve_amount:.2f}₽</b>",
            parse_mode="HTML"
        )
        return

    await state.set_state(WithdrawStates.waiting_amount)
    await callback.message.answer(
        f"<tg-emoji emoji-id='5310191758255099001'>👛</tg-emoji> <b>Вывод средств</b>\n\n"
        f"Минимальный вывод — <b>{MIN_WITHDRAWAL:.0f}₽</b>\n\n"
        f"Чтобы получить <b>{MIN_WITHDRAWAL:.2f}₽</b>, нужно накопить минимум <b>{MIN_BALANCE_REQUIRED:.2f}₽</b> баланса.\n\n"
        f"Резерв <b>{RESERVE_PERCENT:.0f}%</b> от доступного заработка\n"
        f"остаётся на вашем балансе на случай отписок.\n\n"
        f"Комиссия вывода: <b>{COMMISSION_PERCENT:.0f}%</b>.\n"
        f"Резерв считается отдельно от комиссии.\n\n"
        f"<tg-emoji emoji-id='4958926882994127612'>💰</tg-emoji> Баланс: <b>{balance:.2f} ₽</b>\n"
        f"<tg-emoji emoji-id='5292253342012025042'>📈</tg-emoji> Можно запросить: <b>{can_request:.2f}₽</b>\n"
        f"<tg-emoji emoji-id='5312057711091813718'>💳</tg-emoji> Резерв на балансе: <b>{reserve_amount:.2f}₽</b>\n\n"
        f"Введите сумму для вывода:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 Вывести всё", callback_data=f"withdraw_all:{can_request:.2f}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_withdraw")]
            ]
        )
    )


@router.callback_query(F.data == "cancel_withdraw")
async def cancel_withdraw_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена вывода"""
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Вывод отменён.")


@router.callback_query(F.data.startswith("withdraw_all:"))
async def withdraw_all_callback(callback: CallbackQuery, state: FSMContext):
    """Вывод всей суммы"""
    await callback.answer()
    balance = float(callback.data.split(":")[1])
    await process_withdraw(callback.message, callback.from_user.id, balance, state)


@router.message(WithdrawStates.waiting_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    """Обработка суммы вывода"""
    try:
        amount = float(message.text.strip())
        await process_withdraw(message, message.from_user.id, amount, state)

    except ValueError:
        await message.answer("⚠️ Введите корректную сумму (число)")


async def process_withdraw(message: Message, user_id: int, amount: float, state: FSMContext):
    """Обработка вывода средств"""
    # Получаем баланс пользователя
    stats = database.get_user_stats(user_id)
    balance = stats.get('balance', 0.0)

    # Константы
    MIN_WITHDRAWAL = 70.0
    MIN_BALANCE_REQUIRED = 100.0
    RESERVE_PERCENT = 30.0
    COMMISSION_PERCENT = 5.0

    # Расчеты
    reserve_amount = balance * (RESERVE_PERCENT / 100)
    available_balance = balance - reserve_amount
    can_request = available_balance * (1 - COMMISSION_PERCENT / 100)

    if amount < MIN_WITHDRAWAL:
        await message.answer(f"⚠️ Минимальная сумма вывода: {MIN_WITHDRAWAL:.0f} ₽")
        return

    if amount > can_request:
        await message.answer(
            f"⚠️ Недостаточно средств.\n"
            f"💰 Ваш баланс: <b>{balance:.2f} ₽</b>\n"
            f"📈 Можно запросить: <b>{can_request:.2f} ₽</b>\n"
            f"Резерв на балансе: <b>{reserve_amount:.2f}₽</b>",
            parse_mode="HTML"
        )
        return

    # Рассчитываем сумму, которая будет списана с баланса (с учетом комиссии и резерва)
    # amount - это то, что получит пользователь
    # Нужно вычислить, сколько списать с баланса
    amount_with_commission = amount / (1 - COMMISSION_PERCENT / 100)

    # Создаем заявку на вывод (деньги НЕ списываются до одобрения)
    withdrawal_id = database.create_withdrawal_request(user_id, amount_with_commission)

    # Рассчитываем комиссию
    commission = amount_with_commission - amount

    # Отправляем подтверждение пользователю
    await message.answer(
        f"<b>✅ Заявка на вывод создана!</b>\n\n"
        f"💰 Сумма к получению: <b>{amount:.2f} ₽</b>\n"
        f"💳 Комиссия ({COMMISSION_PERCENT:.0f}%): <b>{commission:.2f} ₽</b>\n"
        f"📊 Списано с баланса: <b>{amount_with_commission:.2f} ₽</b>\n"
        f"🔖 ID заявки: <code>{withdrawal_id}</code>\n\n"
        f"<i>Ваша заявка отправлена администраторам.\n"
        f"Вы получите уведомление после обработки.</i>",
        parse_mode="HTML"
    )

    await state.clear()

    # Уведомляем администраторов
    from config import ADMIN_IDS
    from aiogram import Bot
    import os

    bot = Bot(token=os.getenv("API_TOKEN"))

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

    user_link = f"<a href='tg://user?id={user_id}'>{message.from_user.full_name or 'Пользователь'}</a>"

    admin_message = (
        f"📨 <b>НОВАЯ ЗАЯВКА НА ВЫВОД</b>\n\n"
        f"👤 Пользователь: {user_link}\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"💵 Сумма вывода: <b>{amount:.2f} ₽</b>\n"
        f"🔖 ID заявки: <code>{withdrawal_id}</code>\n"
        f"⏳ Статус: <b>Ожидает</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Резерв: <b>{reserve_balance:.2f} USDT</b>\n"
        f"📊 Статус резерва: {reserve_emoji} <b>{reserve_status}</b>"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"wd_confirm:{withdrawal_id}")],
            [
                InlineKeyboardButton(text="❌ Отклонить (без возврата)", callback_data=f"wd_decline:{withdrawal_id}"),
                InlineKeyboardButton(text="↩️ Отклонить (с возвратом)", callback_data=f"wd_refund:{withdrawal_id}")
            ]
        ]
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                admin_message,
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления админу {admin_id}: {e}")

    await bot.session.close()
