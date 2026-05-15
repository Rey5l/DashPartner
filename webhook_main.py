import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

from routes import main_routes, balance_routes, admin_routes, contest_routes
from middlewares.admin_middleware import AdminMiddleware

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Webhook настройки
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://81.29.146.68")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Веб-сервер настройки
WEBAPP_HOST = "0.0.0.0"  # Слушать на всех интерфейсах
WEBAPP_PORT = int(os.getenv("PORT", 8443))  # Порт для Telegram webhook

# SSL сертификаты
SSL_CERT = os.getenv("SSL_CERT", "cert.pem")
SSL_KEY = os.getenv("SSL_KEY", "key.pem")

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("API_TOKEN"))
dp = Dispatcher()

# Подключение роутеров
dp.include_router(main_routes.router)
dp.include_router(balance_routes.router)
dp.include_router(admin_routes.router)
dp.include_router(contest_routes.router)

# Подключение middleware
admin_routes.router.message.middleware(AdminMiddleware())
admin_routes.router.callback_query.middleware(AdminMiddleware())


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    # Устанавливаем webhook
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True,
        certificate=open(SSL_CERT, 'rb') if os.path.exists(SSL_CERT) else None
    )
    logging.info(f"Webhook установлен: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота"""
    # Удаляем webhook
    await bot.delete_webhook()
    logging.info("Webhook удален")


def main() -> None:
    """Запуск бота в режиме webhook"""
    # Регистрируем startup и shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаем aiohttp приложение
    app = web.Application()

    # Создаем обработчик webhook
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )

    # Регистрируем webhook путь
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Настраиваем приложение
    setup_application(app, dp, bot=bot)

    # Создаем SSL контекст если есть сертификаты
    import ssl
    ssl_context = None
    if os.path.exists(SSL_CERT) and os.path.exists(SSL_KEY):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(SSL_CERT, SSL_KEY)
        logging.info("SSL сертификаты загружены")

    # Запускаем веб-сервер
    logging.info(f"Запуск webhook сервера на {WEBAPP_HOST}:{WEBAPP_PORT}")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT, ssl_context=ssl_context)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
