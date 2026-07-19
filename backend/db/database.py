import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "chat.db")
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", 5))

def get_connection() -> sqlite3.Connection:
    """
    Creates and returns a new database connection.

    Returns:
        sqlite3.Connection: SQLite connection object.

    Raises:
        RuntimeError: If connection fails.
    """
    try:
        conn = sqlite3.connect(
            DB_PATH,
            timeout=DB_TIMEOUT,
            check_same_thread=False  
        )

        conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA foreign_keys = ON")

        logger.debug("[get_connection] Opened database connection")

        return conn

    except sqlite3.Error as e:
        logger.exception("[get_connection] Failed to connect to database")

        raise RuntimeError("Database connection failed") from e

def init_db() -> None:
    """
    Initializes database tables and indexes.

    This function is safe to call multiple times (idempotent).

    Raises:
        RuntimeError: If database initialization fails.
    """
    logger.debug("[init_db] Initializing database")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        
        cursor.execute("BEGIN")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id)"
        )

        conn.commit()

        logger.info("[init_db] Database initialized successfully")

    except Exception as e:
        if conn:
            conn.rollback()

        logger.exception("[init_db] Database initialization failed")

        raise RuntimeError("Failed to initialize database") from e

    finally:
        if conn:
            conn.close()

