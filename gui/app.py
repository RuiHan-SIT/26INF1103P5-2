import sqlite3
import hashlib
import secrets
import hmac

from pathlib import Path

# Database is stored inside the GUI folder
DB_PATH = Path(__file__).resolve().parent / "users.db"

# Password hashing configuration
ITERATIONS = 310_000


def get_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def hash_password(password, salt=None):
    """Securely hash a password using PBKDF2."""

    if salt is None:
        salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )

    return salt.hex(), password_hash.hex()


def initialise_database():
    """Create the user table if it does not exist."""

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)


def create_user(username, password):
    """Register a new user."""

    username = username.strip().lower()

    if not username or not password:
        return False, "Please fill in all fields."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt, password_hash = hash_password(password)

    try:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO users (username, salt, password_hash)
                VALUES (?, ?, ?)
            """, (username, salt, password_hash))

        return True, "Account created successfully!"

    except sqlite3.IntegrityError:
        return False, "Username already exists."


def verify_user(username, password):
    """Verify login credentials."""

    username = username.strip().lower()

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT salt, password_hash
            FROM users
            WHERE username = ?
        """, (username,))

        result = cursor.fetchone()

    if result is None:
        return False

    salt, stored_hash = result

    _, entered_hash = hash_password(
        password,
        bytes.fromhex(salt)
    )

    return hmac.compare_digest(stored_hash, entered_hash)
