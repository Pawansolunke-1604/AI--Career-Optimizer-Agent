from fastapi import APIRouter, Response

from app.core.exceptions import ResumeNotGeneratedError, SessionNotFoundError
from app.services.resume_export import DOCX_MIME, build_docx, safe_filename
from app.services.session_service import session_store

router = APIRouter(prefix="/resumes")


@router.get("/{session_id}/docx")
async def download_docx(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        raise SessionNotFoundError("This analysis session has expired. Please analyze your resume again.")
    if session.optimized_resume is None:
        raise ResumeNotGeneratedError("No optimized resume yet. Ask the assistant to generate one first.")
    filename = safe_filename(session.optimized_resume.name)
    return Response(
        content=build_docx(session.optimized_resume),
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )