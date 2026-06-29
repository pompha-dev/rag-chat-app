from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from rag import ask_rag
from fastapi import UploadFile, File, Form
import shutil
import os
from rag import create_db_from_file, delete_db
from db.database import init_db
from db.chat_history import clear_chat, get_chat_history
from db.document_history import save_document, load_document, delete_document
from logging_config import setup_logging
import logging
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
from pathlib import Path

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    question: str
    session_id: str

load_dotenv()
setup_logging()
logger = logging.getLogger(__name__)
logger.info("Application started")

app = FastAPI()
templates = Jinja2Templates(directory="templates_html")
init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """
    Render the home page.

    Args:
        request (Request): Incoming HTTP request.

    Returns:
        HTMLResponse: Rendered index page.

    Raises:
        HTTPException: If template rendering fails.
    """
    logger.debug(
        "[home] Request received | method=%s | url=%s",
        request.method,
        request.url,
    )

    try:
        response = templates.TemplateResponse(
            "index.html",
            {"request": request},
        )

        logger.info("[home] Home page rendered successfully")

        return response

    except Exception as e:
        logger.exception("[home] Failed to render home page")

        raise HTTPException(
            status_code=500,
            detail="Internal server error while loading home page",
        ) from e
    
 
@app.post("/chat")
async def chat(req: ChatRequest) -> dict:
    """
    Handle chat requests using RAG pipeline.

    Args:
        req (ChatRequest): Incoming request with question and session_id.

    Returns:
        dict: Response containing the answer.

    Raises:
        HTTPException: If processing fails.
    """
    logger.debug(
        "[chat] Request received | session=%s | question_length=%s",
        req.session_id,
        len(req.question) if req.question else 0,
    )

  
    if not req.question or not isinstance(req.question, str):
        raise HTTPException(
            status_code=400,
            detail="Question must be a non-empty string",
        )

    if not req.session_id or not isinstance(req.session_id, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id",
        )

    try:
        result = await run_in_threadpool(
            ask_rag,
            req.question,
            req.session_id,
        )

        logger.info(
            "[chat] Response generated | session=%s",
            req.session_id,
        )

        return result

    except ValueError as ve:
        logger.warning(
            "[chat] Validation error | session=%s | error=%s",
            req.session_id,
            str(ve),
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.exception(
            "[chat] Failed to process request | session=%s",
            req.session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from e
    
ALLOWED_EXTENSIONS = {".txt", ".pdf"}

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    session_id: str = Form(...)
) -> dict:
    """
    Upload a document, process it, and store embeddings.

    Args:
        file (UploadFile): Uploaded file (.txt or .pdf)
        session_id (str): Session identifier

    Returns:
        dict: Success message

    Raises:
        HTTPException: If validation or processing fails
    """

    logger.debug(
        "[upload] Request received | session=%s | filename=%s",
        session_id,
        file.filename,
    )

    if not session_id or not isinstance(session_id, str):
        raise HTTPException(status_code=400, detail="Invalid session_id")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .txt and .pdf files are allowed",
        )

    safe_filename = os.path.basename(file.filename)

    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    file_path = os.path.join(session_dir, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(
            "[upload] File saved | session=%s | path=%s",
            session_id,
            file_path,
        )

        await run_in_threadpool(create_db_from_file, file_path, session_id)
        await run_in_threadpool(save_document, session_id, safe_filename)

        logger.info(
            "[upload] File processed successfully | session=%s",
            session_id,
        )

        return {
            "message": "File uploaded and processed successfully"
        }

    except ValueError as ve:
        logger.warning(
            "[upload] Validation error | session=%s | error=%s",
            session_id,
            str(ve),
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.exception(
            "[upload] Failed to process file | session=%s",
            session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error during file upload",
        ) from e

    finally:
        file.file.close()

@app.post("/delete_chat")
async def delete_chat(session_id: str = Form(...)) -> dict:
    """
    Delete chat history, associated document, and vector DB.

    Args:
        session_id (str): Session identifier

    Returns:
        dict: Success message

    Raises:
        HTTPException: If deletion fails
    """

    logger.debug("[delete_chat] Request received | session=%s", session_id)

    if not session_id or not isinstance(session_id, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id",
        )

    try:
        await run_in_threadpool(clear_chat, session_id)
        await run_in_threadpool(delete_document, session_id)
        await run_in_threadpool(delete_db, session_id)

        logger.info(
            "[delete_chat] Deletion successful | session=%s",
            session_id,
        )

        return {"message": "Chat deleted successfully"}

    except ValueError as ve:
        logger.warning(
            "[delete_chat] Validation error | session=%s | error=%s",
            session_id,
            str(ve),
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.exception(
            "[delete_chat] Failed to delete resources | session=%s",
            session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error during deletion",
        ) from e

@app.get("/chat_history")
async def chat_history(session_id: str) -> dict:
    """
    Retrieve chat history for a given session.

    Args:
        session_id (str): Session identifier

    Returns:
        dict: Chat messages

    Raises:
        HTTPException: If retrieval fails
    """

    logger.debug(
        "[chat_history] Request received | session=%s",
        session_id,
    )

    if not session_id or not isinstance(session_id, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id",
        )

    try:
        messages = await run_in_threadpool(get_chat_history, session_id)

        logger.info(
            "[chat_history] Retrieved messages | session=%s | count=%s",
            session_id,
            len(messages),
        )

        return {
            "messages": messages
        }

    except ValueError as ve:
        logger.warning(
            "[chat_history] Validation error | session=%s | error=%s",
            session_id,
            str(ve),
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.exception(
            "[chat_history] Failed to fetch messages | session=%s",
            session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching chat history",
        ) from e
    

@app.get("/document")
async def get_document(session_id: str) -> dict:
    """
    Retrieve uploaded document metadata for a session.

    Args:
        session_id (str): Session identifier

    Returns:
        dict: Document details (filename + message)

    Raises:
        HTTPException: If retrieval fails
    """

    logger.debug(
        "[get_document] Request received | session=%s",
        session_id,
    )

    if not session_id or not isinstance(session_id, str):
        raise HTTPException(
            status_code=400,
            detail="Invalid session_id",
        )

    try:
        file_name = await run_in_threadpool(load_document, session_id)

        if file_name:
            logger.info(
                "[get_document] Document found | session=%s | filename=%s",
                session_id,
                file_name,
            )
            return {
                "filename": file_name,
                "message": "Document found",
            }

        else:
            logger.info(
                "[get_document] No document found | session=%s",
                session_id,
            )
            return {
                "filename": None,
                "message": "No document found",
            }

    except ValueError as ve:
        logger.warning(
            "[get_document] Validation error | session=%s | error=%s",
            session_id,
            str(ve),
        )
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.exception(
            "[get_document] Failed to retrieve document | session=%s",
            session_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error while fetching document",
        ) from e