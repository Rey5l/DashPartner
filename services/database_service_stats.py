"""
Дополнительные методы для получения статистики за период
"""
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
from config import DATABASE_PATH


class DatabaseStatsService:
    """Сервис для получения статистики за период"""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_users_stats_by_period(self, period_days: int) -> list[tuple[datetime, int]]:
        """
        Получить статистику пользователей за период

        Args:
            period_days: Количество дней

        Returns:
            Список кортежей (дата, количество новых пользователей)
        """
        with self._connect() as connection:
            # Получаем данные из chat_owners (регистрация владельцев чатов)
            result = connection.execute(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM chat_owners
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (period_days,)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), row['count']) for row in result]

    def get_earnings_stats_by_period(self, period_days: int) -> list[tuple[datetime, float]]:
        """
        Получить статистику заработка за период

        Args:
            period_days: Количество дней

        Returns:
            Список кортежей (дата, сумма заработка)
        """
        with self._connect() as connection:
            result = connection.execute(
                """
                SELECT DATE(earned_at) as date, SUM(amount) as total
                FROM earnings
                WHERE earned_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(earned_at)
                ORDER BY date
                """,
                (period_days,)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), float(row['total'] or 0)) for row in result]

    def get_resources_stats_by_period(self, period_days: int) -> list[tuple[datetime, int]]:
        """
        Получить статистику ресурсов за период

        Args:
            period_days: Количество дней

        Returns:
            Список кортежей (дата, количество новых ресурсов)
        """
        with self._connect() as connection:
            result = connection.execute(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM resources
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (period_days,)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), row['count']) for row in result]

    def get_contests_stats_by_period(self, period_days: int, owner_user_id: int = None) -> list[tuple[datetime, int]]:
        """
        Получить статистику конкурсов за период

        Args:
            period_days: Количество дней
            owner_user_id: ID владельца (опционально)

        Returns:
            Список кортежей (дата, количество участников)
        """
        with self._connect() as connection:
            if owner_user_id:
                result = connection.execute(
                    """
                    SELECT DATE(ce.created_at) as date, COUNT(*) as count
                    FROM contest_entries ce
                    JOIN contests c ON ce.contest_id = c.id
                    WHERE ce.created_at >= datetime('now', '-' || ? || ' days')
                    AND c.owner_user_id = ?
                    GROUP BY DATE(ce.created_at)
                    ORDER BY date
                    """,
                    (period_days, owner_user_id)
                ).fetchall()
            else:
                result = connection.execute(
                    """
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM contest_entries
                    WHERE created_at >= datetime('now', '-' || ? || ' days')
                    GROUP BY DATE(created_at)
                    ORDER BY date
                    """,
                    (period_days,)
                ).fetchall()

            return [(datetime.fromisoformat(row['date']), row['count']) for row in result]

    def get_chat_access_stats_by_period(self, period_days: int) -> list[tuple[datetime, int]]:
        """
        Получить статистику одобренных пользователей за период

        Args:
            period_days: Количество дней

        Returns:
            Список кортежей (дата, количество одобренных)
        """
        with self._connect() as connection:
            result = connection.execute(
                """
                SELECT DATE(approved_at) as date, COUNT(*) as count
                FROM chat_access
                WHERE approved_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(approved_at)
                ORDER BY date
                """,
                (period_days,)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), row['count']) for row in result]

    def get_withdrawals_stats_by_period(self, period_days: int) -> list[tuple[datetime, float]]:
        """
        Получить статистику выводов за период

        Args:
            period_days: Количество дней

        Returns:
            Список кортежей (дата, сумма выводов)
        """
        with self._connect() as connection:
            result = connection.execute(
                """
                SELECT DATE(created_at) as date, SUM(amount) as total
                FROM withdrawal_requests
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                AND status = 'approved'
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (period_days,)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), float(row['total'] or 0)) for row in result]

    def get_chat_stats_by_period(self, chat_id: int, period_days: int) -> list[tuple[datetime, int]]:
        """
        Получить статистику одобренных пользователей для конкретного чата за период

        Args:
            chat_id: ID чата
            period_days: Количество дней

        Returns:
            Список кортежей (дата, количество одобренных пользователей)
        """
        with self._connect() as connection:
            result = connection.execute(
                """
                SELECT DATE(approved_at) as date, COUNT(*) as count
                FROM chat_access
                WHERE chat_id = ?
                AND approved_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(approved_at)
                ORDER BY date
                """,
                (chat_id, period_days)
            ).fetchall()

            return [(datetime.fromisoformat(row['date']), row['count']) for row in result]
