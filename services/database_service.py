import sqlite3
from random import sample
from datetime import datetime, timezone
from pathlib import Path

from config import CHAT_SUBSCRIPTION_REWARD, DATABASE_PATH


class DatabaseService:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_owners (
                    chat_id INTEGER PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL,
                    owner_username TEXT,
                    owner_full_name TEXT,
                    chat_title TEXT,
                    gate_enabled INTEGER NOT NULL DEFAULT 1,
                    chat_category TEXT,
                    max_sponsors INTEGER NOT NULL DEFAULT 3,
                    subscription_reset_minutes INTEGER NOT NULL DEFAULT 60,
                    bot_message_delete_seconds INTEGER NOT NULL DEFAULT 60,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_access (
                    chat_id INTEGER NOT NULL,
                    member_user_id INTEGER NOT NULL,
                    approved_at TEXT NOT NULL,
                    reward_granted INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (chat_id, member_user_id)
                );

                CREATE TABLE IF NOT EXISTS earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    member_user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, member_user_id, reason)
                );

                CREATE TABLE IF NOT EXISTS task_assignments (
                    chat_id INTEGER NOT NULL,
                    member_user_id INTEGER NOT NULL,
                    task_source TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    task_title TEXT,
                    task_url TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    completed_at TEXT,
                    rewarded_at TEXT,
                    PRIMARY KEY (chat_id, member_user_id, task_source, task_key)
                );

                CREATE TABLE IF NOT EXISTS task_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    member_user_id INTEGER NOT NULL,
                    task_source TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    task_title TEXT,
                    amount REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(chat_id, member_user_id, task_source, task_key)
                );

                CREATE TABLE IF NOT EXISTS contests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_text TEXT,
                    photo_file_id TEXT,
                    contest_channel_id TEXT NOT NULL,
                    posted_message_id INTEGER,
                    post_url TEXT,
                    winners_count INTEGER NOT NULL,
                    channels_required_count INTEGER NOT NULL,
                    subscriptions_required INTEGER NOT NULL DEFAULT 1,
                    time_limit_minutes INTEGER NOT NULL DEFAULT 1440,
                    participants_limit INTEGER,
                    completion_type TEXT NOT NULL DEFAULT 'manual',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS contest_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contest_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS contest_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contest_id INTEGER NOT NULL,
                    participant_user_id INTEGER NOT NULL,
                    participant_username TEXT,
                    participant_full_name TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(contest_id, participant_user_id)
                );

                CREATE TABLE IF NOT EXISTS contest_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contest_id INTEGER NOT NULL,
                    participant_user_id INTEGER NOT NULL,
                    participant_username TEXT,
                    participant_full_name TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(contest_id, participant_user_id)
                );

                CREATE TABLE IF NOT EXISTS user_resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(owner_user_id, url)
                );

                CREATE TABLE IF NOT EXISTS topup_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    invoice_id TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    paid_at TEXT
                );

                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    processed_by INTEGER,
                    check_url TEXT,
                    decline_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            self._ensure_column(connection, "chat_owners", "gate_enabled", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "chat_owners", "chat_category", "TEXT")
            self._ensure_column(connection, "chat_owners", "max_sponsors", "INTEGER NOT NULL DEFAULT 3")
            self._ensure_column(connection, "chat_owners", "subscription_reset_minutes", "INTEGER NOT NULL DEFAULT 60")
            self._ensure_column(connection, "chat_owners", "bot_message_delete_seconds", "INTEGER NOT NULL DEFAULT 60")
            self._ensure_column(connection, "contests", "content_text", "TEXT")
            self._ensure_column(connection, "contests", "photo_file_id", "TEXT")
            self._ensure_column(connection, "contests", "contest_channel_id", "TEXT")
            self._ensure_column(connection, "contests", "posted_message_id", "INTEGER")
            self._ensure_column(connection, "contests", "subscriptions_required", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(connection, "contests", "time_limit_minutes", "INTEGER NOT NULL DEFAULT 1440")
            self._ensure_column(connection, "contests", "participants_limit", "INTEGER")
            self._ensure_column(connection, "contests", "completion_type", "TEXT NOT NULL DEFAULT 'manual'")
            # Migrate post_url to be nullable
            self._migrate_contests_post_url_nullable(connection)

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_names = {column["name"] for column in columns}
        if column_name in existing_names:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _migrate_contests_post_url_nullable(self, connection: sqlite3.Connection) -> None:
        """Migrate contests table to make post_url nullable"""
        # Check if post_url column exists and its constraints
        columns = connection.execute("PRAGMA table_info(contests)").fetchall()
        post_url_col = next((c for c in columns if c["name"] == "post_url"), None)
        
        if post_url_col is None:
            # Column doesn't exist, will be created by _ensure_column
            return
        
        # If column already allows NULL (notnull=0), we're good
        if post_url_col["notnull"] == 0:
            return
        
        # Need to migrate: create new table with correct schema
        print("[DB] Migrating contests table to make post_url nullable...")
        try:
            connection.execute("BEGIN TRANSACTION")
            
            # Get all existing data
            existing = connection.execute("SELECT * FROM contests").fetchall()
            col_names = [description[0] for description in connection.execute("PRAGMA table_info(contests)").fetchall()]
            
            # Drop old table
            connection.execute("DROP TABLE IF EXISTS contests_old")
            connection.execute("ALTER TABLE contests RENAME TO contests_old")
            
            # Create new table with correct schema
            connection.execute("""
                CREATE TABLE contests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content_text TEXT,
                    photo_file_id TEXT,
                    contest_channel_id TEXT NOT NULL,
                    posted_message_id INTEGER,
                    post_url TEXT,
                    winners_count INTEGER NOT NULL,
                    channels_required_count INTEGER NOT NULL,
                    subscriptions_required INTEGER NOT NULL DEFAULT 1,
                    time_limit_minutes INTEGER NOT NULL DEFAULT 1440,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Copy data back (only columns that exist)
            for row in existing:
                row_dict = dict(zip(col_names, row))
                # Prepare values for new table, handling missing columns
                values = (
                    row_dict.get('id'),
                    row_dict.get('owner_user_id'),
                    row_dict.get('title'),
                    row_dict.get('content_text'),
                    row_dict.get('photo_file_id'),
                    row_dict.get('contest_channel_id'),
                    row_dict.get('posted_message_id'),
                    row_dict.get('post_url'),
                    row_dict.get('winners_count'),
                    row_dict.get('channels_required_count'),
                    row_dict.get('subscriptions_required', 1),
                    row_dict.get('time_limit_minutes', 1440),
                    row_dict.get('status', 'active'),
                    row_dict.get('created_at'),
                    row_dict.get('updated_at'),
                )
                connection.execute("""
                    INSERT INTO contests (
                        id, owner_user_id, title, content_text, photo_file_id, contest_channel_id,
                        posted_message_id, post_url, winners_count, channels_required_count,
                        subscriptions_required, time_limit_minutes, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
            
            # Drop old table
            connection.execute("DROP TABLE contests_old")
            
            connection.execute("COMMIT")
            print("[DB] Migration completed successfully")
        except Exception as e:
            connection.execute("ROLLBACK")
            print(f"[DB] Migration failed: {e}")
            raise

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def register_chat_owner(
        self,
        chat_id: int,
        owner_user_id: int,
        owner_username: str | None,
        owner_full_name: str,
        chat_title: str | None,
    ) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_owners (
                    chat_id, owner_user_id, owner_username, owner_full_name, chat_title, gate_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    owner_user_id = excluded.owner_user_id,
                    owner_username = excluded.owner_username,
                    owner_full_name = excluded.owner_full_name,
                    chat_title = excluded.chat_title,
                    updated_at = excluded.updated_at
                """,
                (chat_id, owner_user_id, owner_username, owner_full_name, chat_title, now, now),
            )

    def register_task_assignments(self, chat_id: int, member_user_id: int, tasks: list[dict]) -> int:
        now = self._now()
        inserted_or_updated = 0
        with self._connect() as connection:
            for task in tasks:
                task_source = str(task.get("source") or "unknown")
                task_key = str(task.get("task_key") or "")
                if not task_key:
                    continue

                connection.execute(
                    """
                    INSERT INTO task_assignments (
                        chat_id, member_user_id, task_source, task_key, task_title, task_url, first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id, member_user_id, task_source, task_key) DO UPDATE SET
                        task_title = excluded.task_title,
                        task_url = excluded.task_url,
                        last_seen_at = excluded.last_seen_at
                    """,
                    (
                        chat_id,
                        member_user_id,
                        task_source,
                        task_key,
                        task.get("title"),
                        task.get("url"),
                        now,
                        now,
                    ),
                )
                inserted_or_updated += 1
        return inserted_or_updated

    def create_contest(
        self,
        owner_user_id: int,
        title: str,
        content_text: str,
        contest_channel_id: str,
        winners_count: int,
        channels: list[dict],
        subscriptions_required: int = 1,
        completion_type: str = 'manual',
        time_limit_minutes: int = 1440,
        participants_limit: int | None = None,
        photo_file_id: str | None = None,
        post_url: str | None = None,
    ) -> int:
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO contests (
                    owner_user_id, title, content_text, photo_file_id, contest_channel_id, post_url,
                    winners_count, channels_required_count, subscriptions_required, time_limit_minutes,
                    participants_limit, completion_type, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (owner_user_id, title, content_text, photo_file_id, contest_channel_id, post_url,
                 winners_count, len(channels), subscriptions_required, time_limit_minutes,
                 participants_limit, completion_type, now, now),
            )
            contest_id = cursor.lastrowid
            for index, channel in enumerate(channels, start=1):
                connection.execute(
                    """
                    INSERT INTO contest_channels (contest_id, title, url, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        contest_id,
                        channel["title"],
                        channel["url"],
                        index,
                    ),
                )
        return int(contest_id)

    def list_owner_contests(self, owner_user_id: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.content_text,
                    c.photo_file_id,
                    c.contest_channel_id,
                    c.posted_message_id,
                    c.post_url,
                    c.winners_count,
                    c.channels_required_count,
                    c.subscriptions_required,
                    c.time_limit_minutes,
                    c.status,
                    (
                        SELECT COUNT(*)
                        FROM contest_entries e
                        WHERE e.contest_id = c.id
                    ) AS participants_count
                FROM contests c
                WHERE c.owner_user_id = ?
                ORDER BY c.updated_at DESC, c.id DESC
                """,
                (owner_user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_contest(self, contest_id: int, owner_user_id: int | None = None) -> dict | None:
        with self._connect() as connection:
            if owner_user_id is None:
                row = connection.execute(
                    """
                    SELECT
                        c.id,
                        c.owner_user_id,
                        c.title,
                        c.content_text,
                        c.photo_file_id,
                        c.contest_channel_id,
                        c.posted_message_id,
                        c.post_url,
                        c.winners_count,
                        c.channels_required_count,
                        c.subscriptions_required,
                        c.time_limit_minutes,
                        c.status,
                        (
                            SELECT COUNT(*)
                            FROM contest_entries e
                            WHERE e.contest_id = c.id
                        ) AS participants_count
                    FROM contests c
                    WHERE c.id = ?
                    """,
                    (contest_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT
                        c.id,
                        c.owner_user_id,
                        c.title,
                        c.content_text,
                        c.photo_file_id,
                        c.contest_channel_id,
                        c.posted_message_id,
                        c.post_url,
                        c.winners_count,
                        c.channels_required_count,
                        c.subscriptions_required,
                        c.time_limit_minutes,
                        c.status,
                        (
                            SELECT COUNT(*)
                            FROM contest_entries e
                            WHERE e.contest_id = c.id
                        ) AS participants_count
                    FROM contests c
                    WHERE c.id = ? AND c.owner_user_id = ?
                    """,
                    (contest_id, owner_user_id),
                ).fetchone()
            if row is None:
                return None

            contest = dict(row)
            channels = connection.execute(
                """
                SELECT title, url, sort_order
                FROM contest_channels
                WHERE contest_id = ?
                ORDER BY sort_order ASC, id ASC
                """,
                (contest_id,),
            ).fetchall()
            contest["channels"] = [dict(channel) for channel in channels]

            winners = connection.execute(
                """
                SELECT participant_user_id, participant_username, participant_full_name, created_at
                FROM contest_winners
                WHERE contest_id = ?
                ORDER BY id ASC
                """,
                (contest_id,),
            ).fetchall()
            contest["winners"] = [dict(winner) for winner in winners]
        return contest

    def update_contest_posted_message(self, contest_id: int, message_id: int) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE contests
                SET posted_message_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (message_id, now, contest_id),
            )

    def register_contest_entry(
        self,
        contest_id: int,
        participant_user_id: int,
        participant_username: str | None,
        participant_full_name: str,
    ) -> tuple[bool, dict | None]:
        """
        Регистрирует участника конкурса.
        Возвращает (created, contest_completed_data)
        где contest_completed_data содержит информацию о завершении, если конкурс завершился
        """
        now = self._now()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO contest_entries (
                        contest_id, participant_user_id, participant_username, participant_full_name, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (contest_id, participant_user_id, participant_username, participant_full_name, now),
                )
            except sqlite3.IntegrityError:
                return False, None

            connection.execute(
                """
                UPDATE contests
                SET updated_at = ?
                WHERE id = ?
                """,
                (now, contest_id),
            )

            # Проверяем, нужно ли автоматически завершить конкурс
            contest = connection.execute(
                """
                SELECT completion_type, participants_limit, winners_count, owner_user_id, title
                FROM contests
                WHERE id = ?
                """,
                (contest_id,),
            ).fetchone()

            if contest and contest['completion_type'] == 'participants' and contest['participants_limit']:
                current_count = connection.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM contest_entries
                    WHERE contest_id = ?
                    """,
                    (contest_id,),
                ).fetchone()['count']

                if current_count >= contest['participants_limit']:
                    # Автоматически выбираем победителей
                    winners = self._auto_draw_winners(connection, contest_id, contest['winners_count'], now)
                    return True, {
                        'contest_id': contest_id,
                        'owner_user_id': contest['owner_user_id'],
                        'title': contest['title'],
                        'winners': winners
                    }

        return True, None

    def is_contest_participant(self, contest_id: int, participant_user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM contest_entries
                WHERE contest_id = ? AND participant_user_id = ?
                """,
                (contest_id, participant_user_id),
            ).fetchone()
        return row is not None

    def _auto_draw_winners(self, connection: sqlite3.Connection, contest_id: int, winners_count: int, now: str) -> list[dict]:
        """Внутренний метод для автоматического выбора победителей"""
        participants = connection.execute(
            """
            SELECT participant_user_id, participant_username, participant_full_name
            FROM contest_entries
            WHERE contest_id = ?
            ORDER BY id ASC
            """,
            (contest_id,),
        ).fetchall()

        if not participants:
            selected = []
        else:
            actual_winners_count = min(winners_count, len(participants))
            selected = sample([dict(row) for row in participants], actual_winners_count)

            for winner in selected:
                connection.execute(
                    """
                    INSERT INTO contest_winners (
                        contest_id, participant_user_id, participant_username, participant_full_name, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        contest_id,
                        winner["participant_user_id"],
                        winner["participant_username"],
                        winner["participant_full_name"],
                        now,
                    ),
                )

        # Обновляем статус на completed
        connection.execute(
            """
            UPDATE contests
            SET status = 'completed', updated_at = ?
            WHERE id = ?
            """,
            (now, contest_id),
        )

        return selected

    def draw_contest_winners(self, contest_id: int) -> list[dict]:
        now = self._now()
        with self._connect() as connection:
            contest = connection.execute(
                """
                SELECT winners_count, status
                FROM contests
                WHERE id = ?
                """,
                (contest_id,),
            ).fetchone()
            if contest is None:
                return []

            existing = connection.execute(
                """
                SELECT participant_user_id, participant_username, participant_full_name, created_at
                FROM contest_winners
                WHERE contest_id = ?
                ORDER BY id ASC
                """,
                (contest_id,),
            ).fetchall()
            if existing:
                return [dict(row) for row in existing]

            return self._auto_draw_winners(connection, contest_id, contest["winners_count"], now)

    def delete_contest(self, contest_id: int, owner_user_id: int) -> bool:
        with self._connect() as connection:
            contest = connection.execute(
                """
                SELECT id
                FROM contests
                WHERE id = ? AND owner_user_id = ?
                """,
                (contest_id, owner_user_id),
            ).fetchone()
            if contest is None:
                return False

            connection.execute("DELETE FROM contest_winners WHERE contest_id = ?", (contest_id,))
            connection.execute("DELETE FROM contest_entries WHERE contest_id = ?", (contest_id,))
            connection.execute("DELETE FROM contest_channels WHERE contest_id = ?", (contest_id,))
            connection.execute("DELETE FROM contests WHERE id = ?", (contest_id,))
        return True

    def check_and_complete_timer_contests(self) -> list[dict]:
        """Проверяет и завершает конкурсы по таймеру"""
        now = self._now()
        completed_contests = []

        with self._connect() as connection:
            # Находим конкурсы, которые должны завершиться по таймеру
            contests = connection.execute(
                """
                SELECT id, owner_user_id, title, winners_count, created_at, time_limit_minutes
                FROM contests
                WHERE status = 'active'
                  AND completion_type = 'timer'
                  AND time_limit_minutes > 0
                """,
            ).fetchall()

            for contest in contests:
                from datetime import datetime, timezone, timedelta
                created_at = datetime.fromisoformat(contest['created_at'])
                time_limit = timedelta(minutes=contest['time_limit_minutes'])
                now_dt = datetime.now(timezone.utc)

                if now_dt >= created_at + time_limit:
                    # Время истекло, выбираем победителей
                    winners = self._auto_draw_winners(connection, contest['id'], contest['winners_count'], now)

                    # Обновляем статус конкурса на 'completed'
                    connection.execute(
                        "UPDATE contests SET status = 'completed', updated_at = ? WHERE id = ?",
                        (now, contest['id'])
                    )

                    completed_contests.append({
                        'contest_id': contest['id'],
                        'owner_user_id': contest['owner_user_id'],
                        'title': contest['title'],
                        'winners': winners
                    })

        return completed_contests

    def add_user_resource(self, owner_user_id: int, title: str, url: str) -> bool:
        """Добавляет ресурс пользователя"""
        now = self._now()
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO user_resources (owner_user_id, title, url, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (owner_user_id, title, url, now),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_user_resources(self, owner_user_id: int) -> list[dict]:
        """Получает список ресурсов пользователя"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, url, created_at
                FROM user_resources
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                """,
                (owner_user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_user_resource(self, owner_user_id: int, resource_id: int) -> bool:
        """Удаляет ресурс пользователя"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM user_resources
                WHERE id = ? AND owner_user_id = ?
                """,
                (resource_id, owner_user_id),
            )
        return cursor.rowcount > 0

    def delete_completed_contest(self, contest_id: int) -> bool:
        """Удаляет завершенный конкурс"""
        with self._connect() as connection:
            connection.execute("DELETE FROM contest_winners WHERE contest_id = ?", (contest_id,))
            connection.execute("DELETE FROM contest_entries WHERE contest_id = ?", (contest_id,))
            connection.execute("DELETE FROM contest_channels WHERE contest_id = ?", (contest_id,))
            cursor = connection.execute("DELETE FROM contests WHERE id = ?", (contest_id,))
        return cursor.rowcount > 0

    def reward_tasks_not_in_pending(
        self,
        chat_id: int,
        member_user_id: int,
        pending_tasks: list[dict],
    ) -> dict:
        pending_keys = {
            (str(task.get("source") or "unknown"), str(task.get("task_key") or ""))
            for task in pending_tasks
            if task.get("task_key")
        }
        now = self._now()
        rewarded_count = 0
        rewarded_amount = 0.0

        with self._connect() as connection:
            owner = connection.execute(
                """
                SELECT owner_user_id
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
            if owner is None:
                return {"count": 0, "amount": 0.0}

            rows = connection.execute(
                """
                SELECT task_source, task_key, task_title
                FROM task_assignments
                WHERE chat_id = ? AND member_user_id = ? AND rewarded_at IS NULL
                """,
                (chat_id, member_user_id),
            ).fetchall()

            for row in rows:
                identity = (row["task_source"], row["task_key"])
                if identity in pending_keys:
                    continue

                try:
                    connection.execute(
                        """
                        INSERT INTO task_rewards (
                            owner_user_id, chat_id, member_user_id, task_source, task_key, task_title, amount, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            owner["owner_user_id"],
                            chat_id,
                            member_user_id,
                            row["task_source"],
                            row["task_key"],
                            row["task_title"],
                            CHAT_SUBSCRIPTION_REWARD,
                            now,
                        ),
                    )
                except sqlite3.IntegrityError:
                    connection.execute(
                        """
                        UPDATE task_assignments
                        SET completed_at = COALESCE(completed_at, ?), rewarded_at = COALESCE(rewarded_at, ?)
                        WHERE chat_id = ? AND member_user_id = ? AND task_source = ? AND task_key = ?
                        """,
                        (now, now, chat_id, member_user_id, row["task_source"], row["task_key"]),
                    )
                    continue

                connection.execute(
                    """
                    UPDATE task_assignments
                    SET completed_at = COALESCE(completed_at, ?), rewarded_at = ?
                    WHERE chat_id = ? AND member_user_id = ? AND task_source = ? AND task_key = ?
                    """,
                    (now, now, chat_id, member_user_id, row["task_source"], row["task_key"]),
                )
                rewarded_count += 1
                rewarded_amount += CHAT_SUBSCRIPTION_REWARD

        return {"count": rewarded_count, "amount": round(rewarded_amount, 2)}

    def reward_specific_task(
        self,
        chat_id: int,
        member_user_id: int,
        task_source: str,
        task_key: str,
    ) -> bool:
        now = self._now()
        with self._connect() as connection:
            owner = connection.execute(
                """
                SELECT owner_user_id
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
            if owner is None:
                return False

            assignment = connection.execute(
                """
                SELECT task_title
                FROM task_assignments
                WHERE chat_id = ? AND member_user_id = ? AND task_source = ? AND task_key = ?
                """,
                (chat_id, member_user_id, task_source, task_key),
            ).fetchone()
            if assignment is None:
                return False

            try:
                connection.execute(
                    """
                    INSERT INTO task_rewards (
                        owner_user_id, chat_id, member_user_id, task_source, task_key, task_title, amount, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        owner["owner_user_id"],
                        chat_id,
                        member_user_id,
                        task_source,
                        task_key,
                        assignment["task_title"],
                        CHAT_SUBSCRIPTION_REWARD,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                connection.execute(
                    """
                    UPDATE task_assignments
                    SET completed_at = COALESCE(completed_at, ?), rewarded_at = COALESCE(rewarded_at, ?)
                    WHERE chat_id = ? AND member_user_id = ? AND task_source = ? AND task_key = ?
                    """,
                    (now, now, chat_id, member_user_id, task_source, task_key),
                )
                return False

            connection.execute(
                """
                UPDATE task_assignments
                SET completed_at = COALESCE(completed_at, ?), rewarded_at = ?
                WHERE chat_id = ? AND member_user_id = ? AND task_source = ? AND task_key = ?
                """,
                (now, now, chat_id, member_user_id, task_source, task_key),
            )
        return True

    def list_owner_chats(self, owner_user_id: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.chat_id,
                    c.chat_title,
                    c.gate_enabled,
                    (
                        SELECT COUNT(*)
                        FROM chat_access a
                        WHERE a.chat_id = c.chat_id
                    ) AS approved_members,
                    (
                        SELECT COALESCE(SUM(e.amount), 0)
                        FROM earnings e
                        WHERE e.chat_id = c.chat_id
                          AND e.owner_user_id = c.owner_user_id
                    ) + (
                        SELECT COALESCE(SUM(tr.amount), 0)
                        FROM task_rewards tr
                        WHERE tr.chat_id = c.chat_id
                          AND tr.owner_user_id = c.owner_user_id
                    ) AS earned_total
                FROM chat_owners c
                WHERE c.owner_user_id = ?
                ORDER BY c.updated_at DESC, c.chat_title ASC
                """,
                (owner_user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_chat_settings(self, owner_user_id: int, chat_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    c.chat_id,
                    c.chat_title,
                    c.owner_user_id,
                    c.gate_enabled,
                    c.chat_category,
                    c.max_sponsors,
                    c.subscription_reset_minutes,
                    c.bot_message_delete_seconds,
                    (
                        SELECT COUNT(*)
                        FROM chat_access a
                        WHERE a.chat_id = c.chat_id
                    ) AS approved_members,
                    (
                        SELECT COUNT(*)
                        FROM task_rewards tr
                        WHERE tr.chat_id = c.chat_id
                          AND tr.owner_user_id = c.owner_user_id
                    ) AS completed_tasks,
                    (
                        SELECT COALESCE(SUM(e.amount), 0)
                        FROM earnings e
                        WHERE e.chat_id = c.chat_id
                          AND e.owner_user_id = c.owner_user_id
                    ) + (
                        SELECT COALESCE(SUM(tr.amount), 0)
                        FROM task_rewards tr
                        WHERE tr.chat_id = c.chat_id
                          AND tr.owner_user_id = c.owner_user_id
                    ) AS earned_total
                FROM chat_owners c
                WHERE c.owner_user_id = ? AND c.chat_id = ?
                """,
                (owner_user_id, chat_id),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_chat_runtime(self, chat_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT chat_id, owner_user_id, chat_title, gate_enabled
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def set_chat_gate_enabled(self, owner_user_id: int, chat_id: int, enabled: bool) -> bool:
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_owners
                SET gate_enabled = ?, updated_at = ?
                WHERE owner_user_id = ? AND chat_id = ?
                """,
                (1 if enabled else 0, now, owner_user_id, chat_id),
            )
        return cursor.rowcount > 0

    def update_chat_max_sponsors(self, owner_user_id: int, chat_id: int, max_sponsors: int) -> bool:
        """Обновляет максимальное количество спонсоров для чата"""
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_owners
                SET max_sponsors = ?, updated_at = ?
                WHERE owner_user_id = ? AND chat_id = ?
                """,
                (max_sponsors, now, owner_user_id, chat_id),
            )
        return cursor.rowcount > 0

    def update_chat_subscription_reset(self, owner_user_id: int, chat_id: int, reset_minutes: int) -> bool:
        """Обновляет время сброса подписки для чата"""
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_owners
                SET subscription_reset_minutes = ?, updated_at = ?
                WHERE owner_user_id = ? AND chat_id = ?
                """,
                (reset_minutes, now, owner_user_id, chat_id),
            )
        return cursor.rowcount > 0

    def update_chat_bot_message_delete(self, owner_user_id: int, chat_id: int, delete_seconds: int) -> bool:
        """Обновляет время удаления сообщения бота для чата"""
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_owners
                SET bot_message_delete_seconds = ?, updated_at = ?
                WHERE owner_user_id = ? AND chat_id = ?
                """,
                (delete_seconds, now, owner_user_id, chat_id),
            )
        return cursor.rowcount > 0

    def is_member_approved(self, chat_id: int, member_user_id: int) -> bool:
        """Проверяет, одобрен ли пользователь для доступа к чату с учетом времени сброса"""
        with self._connect() as connection:
            # Получаем настройки чата для проверки времени сброса
            chat_runtime = connection.execute(
                """
                SELECT owner_user_id
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()

            if not chat_runtime:
                return False

            # Получаем настройки чата
            chat_settings = connection.execute(
                """
                SELECT subscription_reset_minutes
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()

            reset_minutes = chat_settings['subscription_reset_minutes'] if chat_settings else 60

            # Проверяем доступ с учетом времени сброса
            row = connection.execute(
                """
                SELECT approved_at
                FROM chat_access
                WHERE chat_id = ? AND member_user_id = ?
                """,
                (chat_id, member_user_id),
            ).fetchone()

            if not row:
                return False

            # Проверяем, не истекло ли время доступа
            from datetime import datetime, timezone, timedelta
            approved_at = datetime.fromisoformat(row['approved_at'])
            now = datetime.now(timezone.utc)
            reset_delta = timedelta(minutes=reset_minutes)

            # Если прошло больше времени, чем установлено в настройках, удаляем доступ
            if now >= approved_at + reset_delta:
                connection.execute(
                    """
                    DELETE FROM chat_access
                    WHERE chat_id = ? AND member_user_id = ?
                    """,
                    (chat_id, member_user_id),
                )
                return False

            return True

    def approve_member(self, chat_id: int, member_user_id: int) -> bool:
        now = self._now()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT reward_granted
                FROM chat_access
                WHERE chat_id = ? AND member_user_id = ?
                """,
                (chat_id, member_user_id),
            ).fetchone()
            if existing is not None:
                return False

            connection.execute(
                """
                INSERT INTO chat_access (chat_id, member_user_id, approved_at, reward_granted)
                VALUES (?, ?, ?, 0)
                """,
                (chat_id, member_user_id, now),
            )
        return True

    def reward_chat_owner_for_member(self, chat_id: int, member_user_id: int) -> bool:
        now = self._now()
        with self._connect() as connection:
            owner = connection.execute(
                """
                SELECT owner_user_id
                FROM chat_owners
                WHERE chat_id = ?
                """,
                (chat_id,),
            ).fetchone()
            if owner is None:
                return False

            access_row = connection.execute(
                """
                SELECT reward_granted
                FROM chat_access
                WHERE chat_id = ? AND member_user_id = ?
                """,
                (chat_id, member_user_id),
            ).fetchone()
            if access_row is None or access_row["reward_granted"]:
                return False

            try:
                connection.execute(
                    """
                    INSERT INTO earnings (owner_user_id, chat_id, member_user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        owner["owner_user_id"],
                        chat_id,
                        member_user_id,
                        CHAT_SUBSCRIPTION_REWARD,
                        "chat_subscription",
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                return False

            connection.execute(
                """
                UPDATE chat_access
                SET reward_granted = 1
                WHERE chat_id = ? AND member_user_id = ?
                """,
                (chat_id, member_user_id),
            )
        return True

    def get_owner_stats(self, owner_user_id: int) -> dict:
        with self._connect() as connection:
            chats_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM chat_owners
                WHERE owner_user_id = ?
                """,
                (owner_user_id,),
            ).fetchone()[0]

            approved_users = connection.execute(
                """
                SELECT COUNT(*)
                FROM earnings
                WHERE owner_user_id = ? AND reason = 'chat_subscription'
                """,
                (owner_user_id,),
            ).fetchone()[0]

            rewarded_tasks = connection.execute(
                """
                SELECT COUNT(*)
                FROM task_rewards
                WHERE owner_user_id = ?
                """,
                (owner_user_id,),
            ).fetchone()[0]

            # Заработано (только положительные суммы)
            legacy_balance = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM earnings
                WHERE owner_user_id = ? AND amount > 0
                """,
                (owner_user_id,),
            ).fetchone()[0]

            task_balance = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM task_rewards
                WHERE owner_user_id = ?
                """,
                (owner_user_id,),
            ).fetchone()[0]

            # Пополнения
            total_topup = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM topup_transactions
                WHERE user_id = ? AND status = 'paid'
                """,
                (owner_user_id,),
            ).fetchone()[0]

            # Выведено (одобренные + отклоненные)
            total_withdrawn = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM withdrawal_requests
                WHERE user_id = ? AND status IN ('approved', 'declined')
                """,
                (owner_user_id,),
            ).fetchone()[0]

            recent_rows = connection.execute(
                """
                SELECT chat_id, member_user_id, amount, created_at
                FROM earnings
                WHERE owner_user_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (owner_user_id,),
            ).fetchall()

            recent_task_rows = connection.execute(
                """
                SELECT chat_id, member_user_id, amount, created_at, task_title
                FROM task_rewards
                WHERE owner_user_id = ?
                ORDER BY id DESC
                LIMIT 5
                """,
                (owner_user_id,),
            ).fetchall()

        combined_recent = [dict(row) for row in recent_rows] + [dict(row) for row in recent_task_rows]
        combined_recent.sort(key=lambda item: item.get("created_at", ""), reverse=True)

        # Баланс = заработано + пополнения - выведено
        current_balance = float((legacy_balance or 0) + (task_balance or 0) + (total_topup or 0) - (total_withdrawn or 0))

        return {
            "chats_count": chats_count,
            "approved_users": approved_users + rewarded_tasks,
            "balance": round(current_balance, 2),
            "reward_per_subscription": CHAT_SUBSCRIPTION_REWARD,
            "recent_earnings": combined_recent[:5],
        }

    def get_user_stats(self, user_id: int) -> dict:
        """Alias for get_owner_stats for consistency"""
        return self.get_owner_stats(user_id)

    def get_user_profile_stats(self, user_id: int) -> dict:
        """Получить расширенную статистику профиля пользователя"""
        with self._connect() as connection:
            # Доходы - всего заработано (только положительные суммы)
            total_earned = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM earnings
                WHERE owner_user_id = ? AND amount > 0
                """,
                (user_id,),
            ).fetchone()[0]

            task_earned = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM task_rewards
                WHERE owner_user_id = ?
                """,
                (user_id,),
            ).fetchone()[0]

            # Пополнения
            total_topup = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM topup_transactions
                WHERE user_id = ? AND status = 'paid'
                """,
                (user_id,),
            ).fetchone()[0]

            # Выведено (одобренные заявки)
            total_withdrawn = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM withdrawal_requests
                WHERE user_id = ? AND status = 'approved'
                """,
                (user_id,),
            ).fetchone()[0]

            # Отклоненные заявки (тоже списываются)
            total_declined = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM withdrawal_requests
                WHERE user_id = ? AND status = 'declined'
                """,
                (user_id,),
            ).fetchone()[0]

            # Потрачено на трафик (это будет 0, если нет такой функциональности)
            # Можно добавить позже, если будет покупка трафика
            spent_on_traffic = 0.0

            # Текущий баланс = заработано + пополнения - выведено - отклоненные
            current_balance = float((total_earned or 0) + (task_earned or 0) + (total_topup or 0) - (total_withdrawn or 0) - (total_declined or 0))

            # Накопленный бонус (заработано от подписок и заданий)
            accumulated_bonus = float((total_earned or 0) + (task_earned or 0))

            # Доступно к выплате (текущий баланс)
            available_for_withdrawal = current_balance

            # Количество чатов
            chats_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM chat_owners
                WHERE owner_user_id = ?
                """,
                (user_id,),
            ).fetchone()[0]

            # Количество выполненных заданий
            approved_users = connection.execute(
                """
                SELECT COUNT(*)
                FROM earnings
                WHERE owner_user_id = ? AND reason = 'chat_subscription'
                """,
                (user_id,),
            ).fetchone()[0]

            rewarded_tasks = connection.execute(
                """
                SELECT COUNT(*)
                FROM task_rewards
                WHERE owner_user_id = ?
                """,
                (user_id,),
            ).fetchone()[0]

        return {
            "total_earned": round(accumulated_bonus, 2),
            "accumulated_bonus": round(accumulated_bonus, 2),
            "spent_on_traffic": round(spent_on_traffic, 2),
            "total_withdrawn": round(float((total_withdrawn or 0) + (total_declined or 0)), 2),
            "balance": round(current_balance, 2),
            "total_topup": round(float(total_topup or 0), 2),
            "available_for_withdrawal": round(available_for_withdrawal, 2),
            "chats_count": chats_count,
            "approved_users": approved_users + rewarded_tasks,
            "reward_per_subscription": CHAT_SUBSCRIPTION_REWARD,
        }

    # Admin methods
    def get_total_reserve(self) -> float:
        """Получить общий резерв системы (сумма всех балансов)"""
        with self._connect() as connection:
            # Сумма из earnings
            earnings_total = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM earnings"
            ).fetchone()[0]

            # Сумма из task_rewards
            task_rewards_total = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM task_rewards"
            ).fetchone()[0]

            return round(float((earnings_total or 0) + (task_rewards_total or 0)), 2)

    def get_admin_statistics(self) -> dict:
        """Получить статистику для админ панели"""
        with self._connect() as connection:
            # Подсчет уникальных пользователей из всех таблиц
            total_users = connection.execute(
                """
                SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT owner_user_id as user_id FROM chat_owners
                    UNION
                    SELECT owner_user_id as user_id FROM earnings
                    UNION
                    SELECT owner_user_id as user_id FROM task_rewards
                    UNION
                    SELECT owner_user_id as user_id FROM contests
                    UNION
                    SELECT owner_user_id as user_id FROM user_resources
                    UNION
                    SELECT participant_user_id as user_id FROM contest_entries
                )
                """
            ).fetchone()[0]

            # Подключенные чаты
            connected_chats = connection.execute(
                "SELECT COUNT(*) FROM chat_owners"
            ).fetchone()[0]

            # Активные конкурсы
            active_contests = connection.execute(
                "SELECT COUNT(*) FROM contests WHERE status = 'active'"
            ).fetchone()[0]

            return {
                "total_users": total_users,
                "connected_chats": connected_chats,
                "active_contests": active_contests,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

    def get_all_resources(self) -> list[dict]:
        """Получить все ресурсы в системе"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, owner_user_id, title, url, created_at
                FROM user_resources
                ORDER BY created_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_resource_statistics(self) -> dict:
        """Получить статистику по ресурсам"""
        with self._connect() as connection:
            total_resources = connection.execute(
                "SELECT COUNT(*) FROM user_resources"
            ).fetchone()[0]

            unique_owners = connection.execute(
                "SELECT COUNT(DISTINCT owner_user_id) FROM user_resources"
            ).fetchone()[0]

            return {
                "total_resources": total_resources,
                "unique_owners": unique_owners
            }

    def create_topup_transaction(self, user_id: int, invoice_id: str, amount: float) -> int:
        """Создать транзакцию пополнения"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO topup_transactions (user_id, invoice_id, amount, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (user_id, invoice_id, amount, datetime.now(timezone.utc).isoformat())
            )
            connection.commit()
            return cursor.lastrowid

    def get_topup_transaction(self, invoice_id: str) -> dict | None:
        """Получить транзакцию пополнения по invoice_id"""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM topup_transactions
                WHERE invoice_id = ?
                """,
                (invoice_id,)
            ).fetchone()
            return dict(row) if row else None

    def mark_topup_paid(self, invoice_id: str) -> bool:
        """Отметить транзакцию как оплаченную и начислить баланс"""
        with self._connect() as connection:
            # Получаем транзакцию
            transaction = connection.execute(
                """
                SELECT user_id, amount, status FROM topup_transactions
                WHERE invoice_id = ?
                """,
                (invoice_id,)
            ).fetchone()

            if not transaction:
                return False

            # Если уже оплачена
            if transaction['status'] == 'paid':
                return False

            user_id = transaction['user_id']
            amount = float(transaction['amount'])

            # Обновляем статус транзакции
            connection.execute(
                """
                UPDATE topup_transactions
                SET status = 'paid', paid_at = ?
                WHERE invoice_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), invoice_id)
            )

            # Начисляем баланс пользователю
            stats = self.get_user_stats(user_id)
            new_balance = stats.get('balance', 0.0) + amount

            connection.execute(
                """
                INSERT INTO chat_owners (chat_id, owner_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO NOTHING
                """,
                (user_id, user_id, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat())
            )

            # Обновляем баланс через earnings
            connection.execute(
                """
                INSERT INTO earnings (owner_user_id, chat_id, member_user_id, amount, reason, created_at)
                VALUES (?, ?, ?, ?, 'topup', ?)
                """,
                (user_id, user_id, user_id, amount, datetime.now(timezone.utc).isoformat())
            )

            connection.commit()
            return True

    def get_user_topup_transactions(self, user_id: int, limit: int = 10) -> list[dict]:
        """Получить историю пополнений пользователя"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM topup_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    def create_withdrawal_request(self, user_id: int, amount: float) -> int:
        """Создать заявку на вывод"""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO withdrawal_requests (user_id, amount, status, created_at)
                VALUES (?, ?, 'pending', ?)
                """,
                (user_id, amount, datetime.now(timezone.utc).isoformat())
            )
            connection.commit()
            return cursor.lastrowid

    def get_withdrawal_request(self, withdrawal_id: int) -> dict | None:
        """Получить заявку на вывод по ID"""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM withdrawal_requests
                WHERE id = ?
                """,
                (withdrawal_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_withdrawals_by_status(self, status: str) -> list[dict]:
        """Получить заявки на вывод по статусу"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM withdrawal_requests
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,)
            ).fetchall()
            return [dict(row) for row in rows]

    def count_withdrawals_by_status(self, status: str) -> int:
        """Подсчитать количество заявок по статусу"""
        with self._connect() as connection:
            count = connection.execute(
                """
                SELECT COUNT(*) FROM withdrawal_requests
                WHERE status = ?
                """,
                (status,)
            ).fetchone()[0]
            return count

    def approve_withdrawal(self, withdrawal_id: int, admin_id: int, check_url: str) -> bool:
        """Одобрить заявку на вывод"""
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE withdrawal_requests
                SET status = 'approved', processed_at = ?, processed_by = ?, check_url = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), admin_id, check_url, withdrawal_id)
            )
            connection.commit()
            return True

    def decline_withdrawal(self, withdrawal_id: int, admin_id: int, refund: bool, reason: str = None) -> bool:
        """Отклонить заявку на вывод"""
        with self._connect() as connection:
            withdrawal = self.get_withdrawal_request(withdrawal_id)
            if not withdrawal:
                return False

            status = 'refunded' if refund else 'declined'

            connection.execute(
                """
                UPDATE withdrawal_requests
                SET status = ?, processed_at = ?, processed_by = ?, decline_reason = ?
                WHERE id = ?
                """,
                (status, datetime.now(timezone.utc).isoformat(), admin_id, reason, withdrawal_id)
            )

            # Если возврат средств, возвращаем баланс пользователю
            if refund:
                user_id = withdrawal['user_id']
                amount = withdrawal['amount']

                connection.execute(
                    """
                    INSERT INTO earnings (owner_user_id, chat_id, member_user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?, 'withdrawal_refund', ?)
                    """,
                    (user_id, user_id, user_id, amount, datetime.now(timezone.utc).isoformat())
                )

            connection.commit()
            return True

    def get_user_withdrawal_requests(self, user_id: int, limit: int = 10) -> list[dict]:
        """Получить историю заявок на вывод пользователя"""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM withdrawal_requests
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    # Settings methods
    def get_setting(self, key: str, default: str = None) -> str | None:
        """Получить значение настройки"""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            ).fetchone()
            return row['value'] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Установить значение настройки"""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value)
            )
            connection.commit()

    def get_withdrawal_fee_percent(self) -> float:
        """Получить процент комиссии за вывод (по умолчанию 20%)"""
        value = self.get_setting('withdrawal_fee_percent', '20')
        try:
            return float(value)
        except ValueError:
            return 20.0

    def set_withdrawal_fee_percent(self, percent: float) -> None:
        """Установить процент комиссии за вывод"""
        self.set_setting('withdrawal_fee_percent', str(percent))

    def get_user_detailed_info(self, user_id: int) -> dict:
        """Получить детальную информацию о пользователе для админа"""
        with self._connect() as connection:
            # Чаты пользователя
            chats = connection.execute(
                """
                SELECT chat_id, chat_title, gate_enabled, created_at
                FROM chat_owners
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

            # Конкурсы (каналы)
            contests = connection.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.status,
                    c.created_at,
                    (SELECT COUNT(*) FROM contest_entries e WHERE e.contest_id = c.id) as participants_count
                FROM contests c
                WHERE c.owner_user_id = ?
                ORDER BY c.created_at DESC
                LIMIT 10
                """,
                (user_id,),
            ).fetchall()

            # Ресурсы пользователя
            resources = connection.execute(
                """
                SELECT title, url, created_at
                FROM user_resources
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

            # Статистика заработка
            total_earned = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM earnings
                WHERE owner_user_id = ?
                """,
                (user_id,),
            ).fetchone()[0]

            task_earned = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM task_rewards
                WHERE owner_user_id = ?
                """,
                (user_id,),
            ).fetchone()[0]

            # Пополнения
            topups = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM topup_transactions
                WHERE user_id = ? AND status = 'paid'
                """,
                (user_id,),
            ).fetchone()[0]

            # Выводы
            withdrawals = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM withdrawal_requests
                WHERE user_id = ? AND status = 'approved'
                """,
                (user_id,),
            ).fetchone()[0]

        return {
            "chats": [dict(row) for row in chats],
            "contests": [dict(row) for row in contests],
            "resources": [dict(row) for row in resources],
            "total_earned": round(float((total_earned or 0) + (task_earned or 0)), 2),
            "total_topups": round(float(topups or 0), 2),
            "total_withdrawals": round(float(withdrawals or 0), 2),
        }


