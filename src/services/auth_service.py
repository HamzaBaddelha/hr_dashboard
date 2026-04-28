import sqlite3
from contextlib import closing

from src.config.settings import (
    DEFAULT_ADMIN_FULL_NAME,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    MIN_PASSWORD_LENGTH,
    VALID_ROLES,
)
from src.core.database import get_connection
from src.core.security import hash_password, verify_password


def ensure_default_admin() -> None:
    with closing(get_connection()) as conn:
        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()

        password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)

        if existing_admin:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, username = ?, password_hash = ?, is_approved = 1, is_active = 1
                WHERE id = ?
                """,
                (
                    DEFAULT_ADMIN_FULL_NAME,
                    DEFAULT_ADMIN_USERNAME.strip().lower(),
                    password_hash,
                    int(existing_admin["id"]),
                ),
            )
            conn.commit()
            return

        conn.execute(
            """
            INSERT INTO users (full_name, username, password_hash, password_salt, role, is_approved, is_active)
            VALUES (?, ?, ?, '', 'admin', 1, 1)
            """,
            (DEFAULT_ADMIN_FULL_NAME, DEFAULT_ADMIN_USERNAME.strip().lower(), password_hash),
        )
        conn.commit()


def register_user(full_name: str, username: str, password: str, role: str = "viewer") -> tuple[bool, str]:
    clean_name = full_name.strip()
    clean_username = username.strip().lower()
    clean_role = role.strip().lower()

    if len(clean_name) < 3:
        return False, "Full name must be at least 3 characters."
    if len(clean_username) < 4:
        return False, "Username must be at least 4 characters."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if clean_role not in VALID_ROLES - {"admin"}:
        return False, "Invalid role. Allowed roles are hr_user and viewer."

    password_hash = hash_password(password)

    try:
        with closing(get_connection()) as conn:
            conn.execute(
                """
                INSERT INTO users (full_name, username, password_hash, password_salt, role, is_approved, is_active)
                VALUES (?, ?, ?, '', ?, 0, 1)
                """,
                (clean_name, clean_username, password_hash, clean_role),
            )
            conn.commit()
        return True, "Registration submitted. Awaiting admin approval."
    except sqlite3.IntegrityError:
        return False, "Username already exists."


def authenticate_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    clean_username = username.strip().lower()
    with closing(get_connection()) as conn:
        user = conn.execute(
            """
            SELECT id, full_name, username, password_hash, role, is_approved, is_active
            FROM users
            WHERE username = ?
            """,
            (clean_username,),
        ).fetchone()

    if not user:
        return False, "Invalid username or password.", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid username or password.", None

    if not bool(user["is_active"]):
        return False, "Your account is disabled. Please contact admin.", None

    if user["role"] != "admin" and not bool(user["is_approved"]):
        return False, "Your account is pending admin approval.", None

    return (
        True,
        "Login successful.",
        {
            "id": user["id"],
            "full_name": user["full_name"],
            "username": user["username"],
            "role": user["role"],
            "is_approved": bool(user["is_approved"]),
            "is_active": bool(user["is_active"]),
        },
    )


def list_users() -> list[dict]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT id, full_name, username, role, is_approved, is_active, created_at, approved_at
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_user_by_id(user_id: int) -> dict | None:
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT id, full_name, username, role, is_approved, is_active
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def approve_user(user_id: int, admin_user_id: int) -> tuple[bool, str]:
    with closing(get_connection()) as conn:
        current = conn.execute(
            "SELECT id, role, is_approved FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not current:
            return False, "User not found."
        if current["role"] == "admin":
            return False, "Admin users are always approved."
        if bool(current["is_approved"]):
            return False, "User is already approved."

        conn.execute(
            """
            UPDATE users
            SET is_approved = 1, approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (admin_user_id, user_id),
        )
        conn.commit()
    return True, "User approved successfully."


def set_user_active(user_id: int, is_active: bool) -> tuple[bool, str]:
    with closing(get_connection()) as conn:
        current = conn.execute(
            "SELECT id, role, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not current:
            return False, "User not found."
        if current["role"] == "admin" and not is_active:
            return False, "Cannot disable admin user."
        if bool(current["is_active"]) == is_active:
            return False, "No status change required."

        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id),
        )
        conn.commit()
    return True, "User status updated successfully."
