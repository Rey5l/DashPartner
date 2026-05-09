import asyncio
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from config import DEFAULT_HTTP_HOST, DEFAULT_HTTP_PORT
from routes.api_routes import setup_api_routes
from routes.main_routes import router
from routes.admin_routes import router as admin_router
from routes.balance_routes import router as balance_router
from services.partner_store import PartnerStore
from services.database_service import DatabaseService
from services.contest_checker import ContestChecker

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)
dp.include_router(admin_router)
dp.include_router(balance_router)
partner_store = PartnerStore()


async def start_http_server() -> web.AppRunner:
    app = web.Application()
    setup_api_routes(app, partner_store)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host=DEFAULT_HTTP_HOST, port=DEFAULT_HTTP_PORT)
    await site.start()
    print(f"HTTP server is running on http://{DEFAULT_HTTP_HOST}:{DEFAULT_HTTP_PORT}")
    return runner


async def main():
    runner = await start_http_server()
    bot = Bot(token=API_TOKEN) if API_TOKEN else None

    if bot is None:
        print("API_TOKEN is not set. HTTP server is running without Telegram bot.")
        try:
            await asyncio.Future()
        finally:
            await runner.cleanup()
        return

    print("Bot is starting...")

    # Инициализируем проверку конкурсов
    database = DatabaseService()
    contest_checker = ContestChecker(bot, database)
    checker_task = asyncio.create_task(contest_checker.start())

    try:
        await dp.start_polling(bot)
    finally:
        await contest_checker.stop()
        checker_task.cancel()
        try:
            await checker_task
        except asyncio.CancelledError:
            pass
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
