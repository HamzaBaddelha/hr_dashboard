import sqlite3
from contextlib import closing

from src.config.settings import DATA_DIR, DB_PATH


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'viewer',
                is_approved INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                approved_by INTEGER,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _run_user_table_migrations(conn)
        conn.commit()


def _run_user_table_migrations(conn: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    migration_statements = {
        "password_salt": "ALTER TABLE users ADD COLUMN password_salt TEXT NOT NULL DEFAULT ''",
        "role": "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'viewer'",
        "is_approved": "ALTER TABLE users ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 0",
        "is_active": "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "approved_by": "ALTER TABLE users ADD COLUMN approved_by INTEGER",
        "approved_at": "ALTER TABLE users ADD COLUMN approved_at TIMESTAMP",
    }

    for column_name, statement in migration_statements.items():
        if column_name not in existing_columns:
            conn.execute(statement)
