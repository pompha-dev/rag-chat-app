from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import os
from db.chat_history import save_message, get_chat_history
import shutil
import logging
from threading import Lock



# LLM
llm = ChatOpenAI()

db_store = {}
FAISS_DIR = "faiss_indexes"
logger = logging.getLogger(__name__)
db_lock = Lock()

class DatabaseDeletionError(Exception):
    """Custom exception for database deletion failures."""
    pass

def load_db(session_id: str):
    """
    Loads FAISS DB from disk for a given session.

    Args:
        session_id (str): Unique session identifier.

    Returns:
        FAISS DB instance or None if not found.

    Raises:
        ValueError: If session_id is invalid.
        RuntimeError: If loading fails.
    """
    logger.debug("[load_db] Loading DB for session: %s", session_id)

  
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    try:
        session_path = os.path.join(FAISS_DIR, session_id)

        if not os.path.exists(session_path):
            logger.debug(
                "[load_db] No DB found on disk for session: %s",
                session_id
            )
            return None

        logger.debug(
            "[load_db] Found DB path: %s for session: %s",
            session_path,
            session_id
        )

        #Initialize embeddings
        embeddings = OpenAIEmbeddings()

        #Load FAISS index
        db = FAISS.load_local(
            session_path,
            embeddings,
            allow_dangerous_deserialization=True
        )

        logger.info(
            "[load_db] Successfully loaded DB for session: %s",
            session_id
        )

        return db

    except ValueError:
        raise  

    except Exception as e:
        logger.exception(
            "[load_db] Failed to load DB for session: %s",
            session_id
        )

        raise RuntimeError(
            f"Failed to load DB for session {session_id}"
        ) from e


def get_db(session_id: str):
    """
    Retrieves FAISS DB for a given session.
    First checks in-memory store, then falls back to disk.

    Args:
        session_id (str): Unique session identifier.

    Returns:
        FAISS DB instance or None if not found.

    Raises:
        ValueError: If session_id is invalid.
        RuntimeError: If loading from disk fails.
    """
    logger.debug("[get_db] Fetching DB for session: %s", session_id)

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    try:
        with db_lock:
            if session_id in db_store:
                logger.debug(
                    "[get_db] Cache HIT for session: %s", session_id
                )
                return db_store[session_id]

        logger.debug(
            "[get_db] Cache MISS for session: %s. Loading from disk...",
            session_id
        )

        db = load_db(session_id)

        if db is None:
            logger.info(
                "[get_db] No DB found on disk for session: %s", session_id
            )
            return None

        with db_lock:
            db_store[session_id] = db

        logger.info(
            "[get_db] Loaded DB from disk and cached for session: %s",
            session_id
        )

        return db

    except ValueError:
        raise  

    except Exception as e:
        logger.exception(
            "[get_db] Failed to retrieve DB for session: %s",
            session_id
        )

        raise RuntimeError(
            f"Failed to retrieve DB for session {session_id}"
        ) from e
    

def save_db(db, session_id: str) -> None:
    """
    Persists FAISS database to disk for a given session.

    Args:
        db: FAISS database instance.
        session_id (str): Unique session identifier.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If saving fails.
    """
    logger.debug("[save_db] Saving DB for session: %s", session_id)

    
    if db is None:
        raise ValueError("DB instance cannot be None")

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    try:
        
        os.makedirs(FAISS_DIR, exist_ok=True)

        session_path = os.path.join(FAISS_DIR, session_id)

        logger.debug(
            "[save_db] Saving FAISS index to path: %s", session_path
        )

     
        db.save_local(session_path)

        logger.info(
            "[save_db] Successfully saved DB for session: %s", session_id
        )

    except Exception as e:
        logger.exception(
            "[save_db] Failed to save DB for session: %s", session_id
        )

        raise RuntimeError(
            f"Failed to save DB for session {session_id}"
        ) from e
    

def create_db_from_file(file_path: str, session_id: str) -> None:
    """
    Creates a FAISS vector database from an uploaded file and stores it in memory and disk.

    Args:
        file_path (str): Path to the uploaded file.
        session_id (str): Unique session identifier.

    Raises:
        ValueError: If inputs are invalid or file type unsupported.
        RuntimeError: If processing or DB creation fails.
    """
    logger.debug("[create_db_from_file] Start for session: %s", session_id)

  
    if not file_path or not isinstance(file_path, str):
        raise ValueError("Invalid file_path provided")

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    if not os.path.exists(file_path):
        raise ValueError(f"File does not exist: {file_path}")

    try:
       
        if file_path.endswith(".txt"):
            loader = TextLoader(file_path, encoding="utf-8")
        elif file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        else:
            raise ValueError("Unsupported file type. Only .txt and .pdf are allowed")

        logger.debug(
            "[create_db_from_file] Loading document for session: %s", session_id
        )
        documents = loader.load()

        if not documents:
            logger.warning(
                "[create_db_from_file] No content found in file for session: %s",
                session_id,
            )
            raise ValueError("Uploaded file contains no readable content")

        #Split text
        text_splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        docs = text_splitter.split_documents(documents)

        logger.debug(
            "[create_db_from_file] Split into %d chunks for session: %s",
            len(docs),
            session_id,
        )

        #Create embeddings
        embeddings = OpenAIEmbeddings()

        #Create FAISS DB
        db = FAISS.from_documents(docs, embeddings)

        #Store safely (thread-safe if needed)
        with db_lock:
            db_store[session_id] = db

        #Persist to disk
        save_db(db, session_id)

        logger.info(
            "[create_db_from_file] Successfully created DB for session: %s | chunks=%d",
            session_id,
            len(docs),
        )

    except ValueError:
        # Let validation errors bubble up cleanly
        raise

    except Exception as e:
        logger.exception(
            "[create_db_from_file] Failed for session: %s", session_id
        )

        raise RuntimeError(
            f"Failed to create DB for session {session_id}"
        ) from e
    

def ask_rag(question: str, session_id: str) -> dict:
    """
    Handles RAG-based question answering for a session.

    Args:
        question (str): User question.
        session_id (str): Unique session identifier.

    Returns:
        dict: {"answer": str}

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If LLM or retrieval fails.
    """
    logger.debug("[ask_rag] Received question for session: %s", session_id)

  
    if not isinstance(question, str):
        raise ValueError("Question must be a string")
    
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")
    
    if not question.strip():
        logger.debug("[ask_rag] Empty question received for session: %s", session_id)
        save_message(session_id, "user", question)
        save_message(session_id, "assistant", "Please enter a question.")
        return {"answer": "Please enter a question."}

    try:
        # Get DB
        db = get_db(session_id)

        if db is None:
            logger.info("[ask_rag] No DB found for session: %s", session_id)

            save_message(session_id, "user", question)
            save_message(session_id, "assistant", "Please upload a document first.")

            return {"answer": "Please upload a document first."}

        # Get chat history
        chat_history = get_chat_history(session_id)

        #Retrieve docs
        docs_and_scores = db.similarity_search_with_score(question, k=2)

        threshold = 0.6
        relevant_docs = [
            doc for doc, score in docs_and_scores if score < threshold
        ]

        if not relevant_docs:
            logger.info(
                "[ask_rag] No relevant docs found for session: %s", session_id
            )

            save_message(session_id, "user", question)
            save_message(session_id, "assistant", "I don't know.")

            return {"answer": "I don't know."}

        #Build context
        context = "\n".join([doc.page_content for doc in relevant_docs])

        #Construct messages
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant.\n"
                    "Answer the question using ONLY the provided context.\n\n"
                    "Rules:\n"
                    "1. If the answer is clearly present in the context, answer it.\n"
                    "2. If the context is unrelated to the question, say 'I don't know'.\n"
                    "3. Do NOT try to make up an answer.\n"
                    "4. Do NOT reuse unrelated parts of the context.\n"
                ),
            },
            {
                "role": "system",
                "content": f"Context:\n{context}",
            },
        ]

        messages.extend(chat_history)

        messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        #Call LLM
        logger.debug("[ask_rag] Invoking LLM for session: %s", session_id)
        response = llm.invoke(messages)

        answer = response.content

        #Persist chat
        save_message(session_id, "user", question)
        save_message(session_id, "assistant", answer)

        logger.debug(
            "[ask_rag] Completed successfully for session: %s | Answer length: %d",
            session_id,
            len(answer),
        )

        return {"answer": answer}

    except Exception as e:
        logger.exception("[ask_rag] Failed for session: %s", session_id)

        raise RuntimeError(
            f"RAG query failed for session {session_id}"
        ) from e
    

    
def delete_faiss_index(session_id: str) -> None:
    """
    Deletes FAISS index directory for a given session.

    This function is idempotent: calling it multiple times with the same
    session_id will not raise errors if the directory does not exist.

    Args:
        session_id (str): Unique identifier for the session.

    Raises:
        ValueError: If session_id is invalid.
        DatabaseDeletionError: If deletion fails unexpectedly.
    """
    logger.debug("[delete_faiss_index] Attempting to delete FAISS index for session: %s", session_id)

    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session_id provided")

    base_path = "faiss_indexes"
    session_path = os.path.join(base_path, session_id)

    try:
        if not os.path.exists(session_path):
            logger.debug(
                "[delete_faiss_index] FAISS index not found (already deleted?): %s", session_id
            )
            return

        shutil.rmtree(session_path)
        logger.debug("[delete_faiss_index] Deleted FAISS index for session: %s", session_id)

    except Exception as e:
        logger.exception(
            "[delete_faiss_index] Failed to delete FAISS index for session: %s", session_id
            )
        raise DatabaseDeletionError(
            f"Failed to delete FAISS index for session {session_id}"
            ) from e
    


def delete_db(session_id):
    """
    Deletes session data from in-memory store and associated FAISS index.

    This function is idempotent: calling it multiple times with the same
    session_id will not raise errors if the session does not exist.

    Args:
        session_id (str): Unique identifier for the session.

    Raises:
        ValueError: If session_id is invalid.
        DatabaseDeletionError: If FAISS index deletion fails.
    """
    logger.debug("Attempting to delete session: %s", session_id)
    try:
        with db_lock:
           removed = db_store.pop(session_id, None)

        if removed is not None:
            logger.info("[delete_db] Deleted session from db_store: %s", session_id)
        else:
            logger.debug("[delete_db] Session not found in db_store (already deleted?): %s", session_id)

    except Exception as e:
        logger.exception("[delete_db] Failed to delete session from db_store: %s", session_id)
        raise DatabaseDeletionError(f"Failed to delete session {session_id} from db_store") from e
    
    try:
        delete_faiss_index(session_id)
        logger.info("[delete_db] Deleted FAISS index for session: %s", session_id)

    except Exception as e:
        logger.exception("[delete_db] Failed to delete FAISS index: %s", session_id)
        raise DatabaseDeletionError(f"Failed to delete FAISS index for session {session_id}") from e