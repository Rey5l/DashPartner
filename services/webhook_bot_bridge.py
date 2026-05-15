"""
Модуль для взаимодействия между webhook сервером и ботом
"""
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.database_service import DatabaseService
import os
from dotenv import load_dotenv

load_dotenv()

database = DatabaseService()


async def notify_task_completed(bot: Bot, user_id: int, chat_id: int, task_id: str, task_source: str):
    """
    Уведомить пользователя о выполнении задания и удалить его из списка

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        chat_id: ID чата
        task_id: ID задания
        task_source: Источник задания (flyer, tgrass)
    """
    try:
        # Получаем информацию о награде
        from config import CHAT_SUBSCRIPTION_REWARD

        # Отправляем уведомление пользователю
        await bot.send_message(
            user_id,
            f"✅ <b>Задание выполнено!</b>\n\n"
            f"💰 Начислено: <b>{CHAT_SUBSCRIPTION_REWARD:.2f} ₽</b>\n"
            f"📋 Источник: <code>{task_source}</code>\n"
            f"🔖 ID задания: <code>{task_id}</code>",
            parse_mode="HTML"
        )

        return True

    except Exception as e:
        print(f"Error notifying user {user_id}: {e}")
        return False


async def handle_task_abort(bot: Bot, user_id: int, chat_id: int, task_id: str, task_source: str):
    """
    Обработать отписку пользователя от задания

    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        chat_id: ID чата
        task_id: ID задания
        task_source: Источник задания (flyer, tgrass)
    """
    try:
        # Отправляем предупреждение пользователю
        await bot.send_message(
            user_id,
            f"⚠️ <b>Обнаружена отписка!</b>\n\n"
            f"Вы отписались от обязательного канала.\n"
            f"Пожалуйста, подпишитесь снова, чтобы продолжить получать награды.\n\n"
            f"📋 Источник: <code>{task_source}</code>\n"
            f"🔖 ID задания: <code>{task_id}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data=f"recheck_sub:{task_id}")]
                ]
            )
        )

        # TODO: Можно списать награду обратно, если она была начислена

        return True

    except Exception as e:
        print(f"Error handling abort for user {user_id}: {e}")
        return False


def get_bot_instance():
    """Получить экземпляр бота"""
    token = os.getenv("API_TOKEN")
    if not token:
        raise ValueError("API_TOKEN not found in environment")
    return Bot(token=token)
