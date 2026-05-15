import asyncio
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import os
import hmac
import hashlib

from services.database_service import DatabaseService
from services.webhook_bot_bridge import notify_task_completed, handle_task_abort, get_bot_instance

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="DashPartner Webhook Server")
database = DatabaseService()

# Секретные ключи для проверки подписи
FLYER_SECRET = os.getenv("FLYER_SECRET", "")
TGRASS_SECRET = os.getenv("TGRASS_SECRET", "")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Проверка подписи webhook"""
    if not secret:
        logger.warning("Secret key not configured")
        return True  # В режиме разработки пропускаем проверку

    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@app.get("/")
async def root():
    """Главная страница"""
    return {
        "service": "DashPartner Webhook Server",
        "status": "running",
        "endpoints": {
            "flyer": "/flyer_webhook",
            "tgrass": "/tgrass_webhook",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}


@app.get("/flyer_webhook")
async def flyer_webhook_info():
    """Информация о Flyer webhook (GET)"""
    return {
        "endpoint": "/flyer_webhook",
        "method": "POST",
        "description": "Webhook для Flyer",
        "example": {
            "type": "test"
        }
    }


@app.post("/flyer_webhook")
async def flyer_webhook(request: Request):
    """
    Webhook для Flyer

    Формат от Flyer:
    {
        "type": "test" | "sub_completed" | "new_status",
        "data": {
            "user_id": 123456789,
            "chat_id": -1001234567890,
            "task_id": "flyer_task_123",
            "status": "abort" (для new_status)
        }
    }
    """
    try:
        # Парсим JSON
        data = await request.json()
        logger.info(f"Received Flyer webhook: {data}")
        logger.info(f"Client IP: {request.client}")

        webhook_type = data.get("type")

        # Тестовый запрос
        if webhook_type == "test":
            logger.info("Flyer test webhook received")
            return {"status": True}

        # Обязательная подписка пройдена
        elif webhook_type == "sub_completed":
            webhook_data = data.get("data", {})
            user_id = webhook_data.get("user_id")
            chat_id = webhook_data.get("chat_id")
            task_id = webhook_data.get("task_id")

            if not all([user_id, chat_id, task_id]):
                logger.warning(f"Missing required fields in sub_completed: {data}")
                return {"status": False, "error": "Missing required fields"}

            # Вознаграждаем пользователя
            success = database.reward_specific_task(
                chat_id=chat_id,
                member_user_id=user_id,
                task_source="flyer",
                task_key=task_id
            )

            if success:
                logger.info(f"✅ Rewarded user {user_id} for Flyer task {task_id}")

                # Отправляем уведомление пользователю через бота
                try:
                    bot = get_bot_instance()
                    await notify_task_completed(bot, user_id, chat_id, task_id, "Flyer")
                    await bot.session.close()
                except Exception as e:
                    logger.error(f"Failed to notify user: {e}")
            else:
                logger.warning(f"⚠️ Task already rewarded or not found: {task_id}")

            return {"status": True}

        # Новый статус задания: отписка от канала
        elif webhook_type == "new_status":
            webhook_data = data.get("data", {})
            status = webhook_data.get("status")

            if status == "abort":
                user_id = webhook_data.get("user_id")
                chat_id = webhook_data.get("chat_id")
                task_id = webhook_data.get("task_id")

                logger.warning(f"⚠️ User {user_id} unsubscribed from task {task_id}")

                # Отправляем предупреждение пользователю
                try:
                    bot = get_bot_instance()
                    await handle_task_abort(bot, user_id, chat_id, task_id, "Flyer")
                    await bot.session.close()
                except Exception as e:
                    logger.error(f"Failed to handle abort: {e}")

            return {"status": True}

        else:
            logger.warning(f"Unknown Flyer webhook type: {webhook_type}")
            return {"status": True}

    except Exception as e:
        logger.error(f"Error processing Flyer webhook: {e}", exc_info=True)
        return {"status": False, "error": str(e)}


@app.post("/tgrass_webhook")
async def tgrass_webhook(request: Request):
    """
    Webhook для TGrass

    Формат от TGrass:
    {
        "tg_user_id": 123456789,
        "offer_link": "https://t.me/channel",
        "status": "subscribed" | "unsubscribed"
    }
    """
    try:
        # Парсим JSON
        data = await request.json()
        logger.info(f"Received TGrass webhook: {data}")
        logger.info(f"Client IP: {request.client}")

        user_id = data.get("tg_user_id")
        offer_link = data.get("offer_link", "")
        status = data.get("status")

        if not all([user_id, status]):
            logger.warning(f"Missing required fields in TGrass webhook: {data}")
            return {"status": False, "error": "Missing required fields"}

        # Генерируем task_id из offer_link
        task_id = f"tgrass_{offer_link.replace('https://t.me/', '')}"

        # Подписка подтверждена
        if status == "subscribed":
            # Для TGrass нужно знать chat_id, но его нет в webhook
            # Попробуем найти задание в базе данных
            # TODO: Нужно доработать логику получения chat_id

            logger.info(f"✅ User {user_id} subscribed to {offer_link}")

            # Временно используем user_id как chat_id (нужно доработать)
            # В реальности нужно хранить связь между offer_link и chat_id

            # Отправляем уведомление пользователю
            try:
                bot = get_bot_instance()
                await bot.send_message(
                    user_id,
                    f"✅ <b>Подписка подтверждена!</b>\n\n"
                    f"📢 Канал: <code>{offer_link}</code>\n"
                    f"💰 Награда будет начислена после проверки\n\n"
                    f"<i>Источник: TGrass</i>",
                    parse_mode="HTML"
                )
                await bot.session.close()
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")

            return {"status": True}

        # Отписка обнаружена
        elif status == "unsubscribed":
            logger.warning(f"⚠️ User {user_id} unsubscribed from {offer_link}")

            # Отправляем предупреждение пользователю
            try:
                bot = get_bot_instance()
                await bot.send_message(
                    user_id,
                    f"⚠️ <b>Обнаружена отписка!</b>\n\n"
                    f"📢 Канал: <code>{offer_link}</code>\n\n"
                    f"Вы отписались от обязательного канала.\n"
                    f"Пожалуйста, подпишитесь снова, чтобы продолжить получать награды.\n\n"
                    f"<i>Источник: TGrass</i>",
                    parse_mode="HTML"
                )
                await bot.session.close()
            except Exception as e:
                logger.error(f"Failed to handle unsubscribe: {e}")

            return {"status": True}

        else:
            logger.warning(f"Unknown TGrass status: {status}")
            return {"status": True}

    except Exception as e:
        logger.error(f"Error processing TGrass webhook: {e}", exc_info=True)
        return {"status": False, "error": str(e)}


if __name__ == "__main__":
    # Настройки сервера
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("WEBHOOK_PORT", 8000))

    logger.info(f"Starting webhook server on {host}:{port}")
    logger.info(f"Flyer webhook: http://{host}:{port}/flyer_webhook")
    logger.info(f"TGrass webhook: http://{host}:{port}/tgrass_webhook")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
