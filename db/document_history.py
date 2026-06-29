from .database import get_connection
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def save_document(session_id: str, filename: str) -> None:
    """
    Saves a document record for a given session.

    Args:
        session_id (str): Unique session identifier.
        filename (str): Name of the uploaded file.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If database operation fails.
    """
    logger.debug(
        "[save_document] Saving document | session: %s | filename: %s",
        session_id,
        filename,
    )

    
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    if not filename or not isinstance(filename, str):
        raise ValueError("Invalid filename provided")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO documents (session_id, filename)
            VALUES (?, ?)
            """,
            (session_id, filename),
        )

        conn.commit()

        logger.info(
            "[save_document] Document saved | session: %s | filename: %s",
            session_id,
            filename,
        )

    except Exception as e:
        if conn:
            conn.rollback()  

        logger.exception(
            "[save_document] Failed to save document | session: %s | filename: %s",
            session_id,
            filename,
        )

        raise RuntimeError(
            f"Failed to save document for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close()  



def load_document(session_id: str) -> Optional[str]:
    """
    Retrieves a document filename for a given session.

    Args:
        session_id (str): Unique session identifier.

    Returns:
        Optional[str]: Filename if found, else None.

    Raises:
        ValueError: If session_id is invalid.
        RuntimeError: If database operation fails.
    """
    logger.debug(
        "[load_document] Fetching document | session: %s",
        session_id,
    )

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT filename
            FROM documents
            WHERE session_id = ?
            LIMIT 1
            """,
            (session_id,),
        )

        row = cursor.fetchone()

        if not row:
            logger.debug(
                "[load_document] No document found | session: %s",
                session_id,
            )
            return None

        filename = row[0]

        logger.info(
            "[load_document] Document retrieved | session: %s | filename: %s",
            session_id,
            filename,
        )

        return filename

    except Exception as e:
        logger.exception(
            "[load_document] Failed to load document | session: %s",
            session_id,
        )
        raise RuntimeError(
            f"Failed to load document for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close()


    
def delete_document(session_id: str) -> None:
    """
    Deletes all documents associated with a given session.

    This operation is idempotent — calling it multiple times
    has the same effect as calling it once.

    Args:
        session_id (str): Unique session identifier.

    Raises:
        ValueError: If session_id is invalid.
        RuntimeError: If deletion fails.
    """
    logger.debug(
        "[delete_document] Request received | session: %s",
        session_id,
    )

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM documents WHERE session_id = ?",
            (session_id,),
        )

        deleted_count = cursor.rowcount  

        conn.commit()

        if deleted_count == 0:
            logger.debug(
                "[delete_document] No documents found (already deleted?) | session: %s",
                session_id,
            )
        else:
            logger.info(
                "[delete_document] Documents deleted | session: %s | count: %s",
                session_id,
                deleted_count,
            )

    except Exception as e:
        logger.exception(
            "[delete_document] Failed to delete documents | session: %s",
            session_id,
        )
        raise RuntimeError(
            f"Failed to delete documents for session {session_id}"
        ) from e

    finally:
        if conn:
            conn.close()