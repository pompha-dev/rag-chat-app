from .database import get_connection
import logging

logger = logging.getLogger(__name__)

def save_message(session_id: str, role: str, content: str) -> None:
    """
    Saves a chat message to the database.

    Args:
        session_id (str): Unique session identifier.
        role (str): Role of the sender ("user" or "assistant").
        content (str): Message content.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If database operation fails.
    """
    logger.debug(
        "[save_message] Saving message | session: %s | role: %s",
        session_id,
        role,
    )

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    if role not in {"user", "assistant", "system"}:
        raise ValueError(f"Invalid role: {role}")

    if not isinstance(content, str):
        raise ValueError("Content must be a string")

    if not content.strip():
        logger.debug(
            "[save_message] Skipping empty message for session: %s",
            session_id,
        )
        return 

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO chat_history (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content),
        )

        conn.commit()

        logger.debug(
            "[save_message] Message saved successfully | session: %s",
            session_id,
        )

    except Exception as e:
        if conn:
            conn.rollback()  

        logger.exception(
            "[save_message] Failed to save message | session: %s",
            session_id,
        )

        raise RuntimeError(
            f"Failed to save message for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close()  


def get_chat_history(session_id: str, limit: int = 10) -> list[dict]:
    """
    Retrieves chat history for a given session.

    Args:
        session_id (str): Unique session identifier.
        limit (int): Number of recent messages to retrieve.

    Returns:
        list[dict]: List of messages in chronological order.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If database operation fails.
    """
    logger.debug(
        "[get_chat_history] Fetching history | session: %s | limit: %s",
        session_id,
        limit,
    )

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("Limit must be a positive integer")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, content
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )

        rows = cursor.fetchall()

        rows.reverse()

        result = [{"role": r[0], "content": r[1]} for r in rows]

        logger.debug(
            "[get_chat_history] Retrieved %d messages | session: %s",
            len(result),
            session_id,
        )

        return result

    except Exception as e:
        logger.exception(
            "[get_chat_history] Failed to fetch history | session: %s",
            session_id,
        )

        raise RuntimeError(
            f"Failed to fetch chat history for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close()  



def clear_chat(session_id: str) -> None:
    """
    Deletes all chat history for a given session.

    This function is idempotent: calling it multiple times
    will not raise errors if the session has no messages.

    Args:
        session_id (str): Unique session identifier.

    Raises:
        ValueError: If session_id is invalid.
        RuntimeError: If database operation fails.
    """
    logger.debug(
        "[clear_chat] Attempting to clear chat | session: %s",
        session_id,
    )

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM chat_history WHERE session_id = ?",
            (session_id,),
        )

        deleted_rows = cursor.rowcount  # ✅ useful info

        conn.commit()

        if deleted_rows > 0:
            logger.info(
                "[clear_chat] Deleted %d messages | session: %s",
                deleted_rows,
                session_id,
            )
        else:
            logger.debug(
                "[clear_chat] No messages found (already cleared?) | session: %s",
                session_id,
            )

    except Exception as e:
        if conn:
            conn.rollback()  

        logger.exception(
            "[clear_chat] Failed to clear chat | session: %s",
            session_id,
        )

        raise RuntimeError(
            f"Failed to clear chat for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close() 