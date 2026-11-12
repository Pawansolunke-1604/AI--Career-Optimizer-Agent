import logging
from pathlib import Path
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    CorruptFileError,
    EmptyDocumentError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.utils.docx_utils import extract_text_from_docx
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)
MIN_TEXT_LENGTH = 50


async def extract_text_from_upload(file: UploadFile) -> str:
    settings = get_settings()
    data = await file.read()

    if not data:
        raise EmptyDocumentError("The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise FileTooLargeError(f"File exceeds {settings.max_upload_mb} MB limit.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".docx", ".txt"):
        raise UnsupportedFileTypeError("Only PDF, DOCX and TXT files are supported.")

    # the real content must match the extension (catches renamed files)
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise CorruptFileError("This file is not a valid PDF.")
    if ext == ".docx" and not data.startswith(b"PK"):
        raise CorruptFileError("This file is not a valid DOCX.")

    try:
        if ext == ".pdf":
            text = extract_text_from_pdf(data)
        elif ext == ".docx":
            text = extract_text_from_docx(data)
        else:
            text = data.decode("utf-8", errors="ignore")
    except AppError:
        raise
    except Exception:
        logger.exception("Failed to parse %s", file.filename)
        raise CorruptFileError(
            "Could not read this file. It may be corrupt or password-protected."
        )

    text = clean_text(text)
    if len(text) < MIN_TEXT_LENGTH:
        raise EmptyDocumentError(
            "Could not read text from this file. It may be a scanned image."
        )
    return text