"""Приведение старой базы (версия на tkinter) к новой схеме.

База `finance.db` уже существует и содержит данные: 7 пользователей, счета, журнал.
Удалять её нельзя — на ней же проверялись дефекты ISSUE-1…16. Поэтому при первом
запуске новой версии выполняется идемпотентная миграция:

1. добавляются недостающие колонки;
2. пароли из открытого вида превращаются в хэши, колонка с открытым паролем затирается;
3. тип счёта нормализуется из подписей формы («счет?»/«вклад?») в `checking`/`saving`;
4. заполняются даты создания и оклад сотрудников.
"""
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from models import DEFAULT_SALARY, utcnow

LEGACY_ACCOUNT_TYPES = {
    "счет?": "checking",
    "вклад?": "saving",
    "счёт?": "checking",
    "checking": "checking",
    "saving": "saving",
    "": "checking",
}

# колонка -> SQL-выражение для ALTER TABLE ADD COLUMN
NEW_COLUMNS = {
    "users": {
        "full_name": "VARCHAR(200)",
        "password_hash": "VARCHAR(255)",
        "is_rejected": "BOOLEAN DEFAULT 0",
        "created_at": "DATETIME",
    },
    "accounts": {"is_closed": "BOOLEAN DEFAULT 0", "created_at": "DATETIME"},
    "transaction_logs": {"actor_id": "INTEGER", "payload": "TEXT"},
    "salary_requests": {
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
        "last_paid_at": "DATETIME",
    },
    "employment": {"salary_amount": "FLOAT", "hired_at": "DATETIME"},
}

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def _existing_columns(conn, table: str) -> list[str]:
    return [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()]


def _has_column(conn, table: str, column: str) -> bool:
    return column in _existing_columns(conn, table)


def _now() -> str:
    return utcnow().strftime(DATETIME_FMT)


def migrate_legacy_schema(engine, logger) -> None:
    """Идемпотентно обновляет старую БД. На чистой БД ничего не делает."""
    with engine.begin() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'"),
            ).fetchall()
        }
        if "users" not in tables:
            return

        added = []
        for table, columns in NEW_COLUMNS.items():
            if table not in tables:
                continue
            for column, sql_type in columns.items():
                if not _has_column(conn, table, column):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
                    added.append(f"{table}.{column}")

        # --- пользователи: хэш пароля вместо открытого текста (ISSUE-1) ---
        has_plain = _has_column(conn, "users", "password")
        query = "SELECT id, username, password_hash" + (", password" if has_plain else "") + " FROM users"
        hashed = 0
        for row in conn.execute(text(query)).fetchall():
            user_id, _username, password_hash = row[0], row[1], row[2]
            if password_hash:
                continue
            source = (row[3] if has_plain and len(row) > 3 else None) or "123456"
            conn.execute(
                text("UPDATE users SET password_hash = :hash WHERE id = :id"),
                {"hash": generate_password_hash(source), "id": user_id},
            )
            hashed += 1

        if has_plain:
            # затираем открытые пароли; колонку удаляем, если SQLite умеет
            conn.execute(text("UPDATE users SET password = ''"))
            try:
                conn.execute(text("ALTER TABLE users DROP COLUMN password"))
                added.append("users.password removed")
            except Exception:  # старый SQLite — колонка остаётся пустой
                logger.warning("SQLite не поддерживает DROP COLUMN: password очищен, но остался")

        conn.execute(text("UPDATE users SET full_name = username WHERE full_name IS NULL OR full_name = ''"))
        conn.execute(text("UPDATE users SET created_at = :now WHERE created_at IS NULL"), {"now": _now()})

        # --- счета: тип из подписи формы в значение (ISSUE-10) ---
        if _has_column(conn, "accounts", "acc_type"):
            for legacy, target in LEGACY_ACCOUNT_TYPES.items():
                if legacy == target:
                    continue
                conn.execute(
                    text("UPDATE accounts SET acc_type = :target WHERE acc_type = :legacy"),
                    {"target": target, "legacy": legacy},
                )
        conn.execute(text("UPDATE accounts SET created_at = :now WHERE created_at IS NULL"), {"now": _now()})
        conn.execute(text("UPDATE accounts SET balance = 0 WHERE balance IS NULL"))

        # --- журнал: даты, статусы ---
        if _has_column(conn, "transaction_logs", "timestamp"):
            conn.execute(text("UPDATE transaction_logs SET timestamp = :now WHERE timestamp IS NULL"), {"now": _now()})
        if _has_column(conn, "transaction_logs", "status"):
            conn.execute(text("UPDATE transaction_logs SET status = 'completed' WHERE status IS NULL"))

        # --- заявки: даты ---
        if _has_column(conn, "salary_requests", "created_at"):
            conn.execute(text("UPDATE salary_requests SET created_at = :now WHERE created_at IS NULL"), {"now": _now()})
            conn.execute(text("UPDATE salary_requests SET updated_at = created_at WHERE updated_at IS NULL"))

        # --- штат: оклад ---
        if _has_column(conn, "employment", "salary_amount"):
            conn.execute(
                text("UPDATE employment SET salary_amount = :amount WHERE salary_amount IS NULL"),
                {"amount": DEFAULT_SALARY},
            )
            if _has_column(conn, "employment", "hired_at"):
                conn.execute(text("UPDATE employment SET hired_at = :now WHERE hired_at IS NULL"), {"now": _now()})

        logger.info("Миграция старой БД: добавлено/изменено %s", added or "ничего")
        if hashed:
            logger.info("Пароли переведены в хэши: %s", hashed)
