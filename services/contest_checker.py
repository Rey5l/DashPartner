import asyncio
from aiogram import Bot
from services.database_service import DatabaseService


class ContestChecker:
    def __init__(self, bot: Bot, database: DatabaseService):
        self.bot = bot
        self.database = database
        self.running = False

    async def start(self):
        """Запускает периодическую проверку конкурсов"""
        self.running = True
        while self.running:
            try:
                await self.check_contests()
            except Exception as e:
                print(f"[CONTEST_CHECKER] Error checking contests: {e}")

            # Проверяем каждые 60 секунд
            await asyncio.sleep(60)

    async def stop(self):
        """Останавливает проверку конкурсов"""
        self.running = False

    async def check_contests(self):
        """Проверяет и завершает конкурсы по таймеру"""
        completed = self.database.check_and_complete_timer_contests()

        for contest_data in completed:
            try:
                # Уведомляем владельца конкурса о завершении
                owner_id = contest_data['owner_user_id']
                title = contest_data['title']
                winners = contest_data['winners']
                contest_id = contest_data['contest_id']

                if winners:
                    winner_lines = "\n".join(
                        f"{idx}. <a href=\"tg://user?id={winner.get('participant_user_id')}\">{winner.get('participant_full_name') or 'Участник'}</a>"
                        for idx, winner in enumerate(winners, 1)
                    )
                    message = (
                        f"🎉 Конкурс <b>{title}</b> завершен!\n\n"
                        f"Победители выбраны автоматически:\n{winner_lines}\n\n"
                        f"Конкурс удален из списка."
                    )
                else:
                    message = (
                        f"⚠️ Конкурс <b>{title}</b> завершен по таймеру, "
                        f"но не было участников для выбора победителей.\n\n"
                        f"Конкурс удален из списка."
                    )

                await self.bot.send_message(
                    chat_id=owner_id,
                    text=message,
                    parse_mode="HTML"
                )

                # Удаляем конкурс после успешного уведомления
                self.database.delete_completed_contest(contest_id)

                print(f"[CONTEST_CHECKER] Contest {contest_id} completed, owner notified, and deleted")
            except Exception as e:
                print(f"[CONTEST_CHECKER] Failed to notify owner {owner_id}: {e}")
                # Все равно удаляем конкурс, даже если уведомление не удалось
                try:
                    self.database.delete_completed_contest(contest_data['contest_id'])
                except Exception as del_error:
                    print(f"[CONTEST_CHECKER] Failed to delete contest {contest_data['contest_id']}: {del_error}")
