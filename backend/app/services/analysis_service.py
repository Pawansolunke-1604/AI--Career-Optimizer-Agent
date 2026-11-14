import asyncio
import logging

from fastapi.concurrency import run_in_threadpool

from app.agents.tools.gap_analysis_tool import generate_report
from app.agents.tools.jd_parser_tool import extract_jd_data
from app.agents.tools.resume_parser_tool import extract_resume_data
from app.core.exceptions import LLMError
from app.schemas.analysis import AnalysisResponse
from app.services import guardrails
from app.services.scoring_service import compute_match
from app.services.session_service import session_store

logger = logging.getLogger(__name__)



async def analyze(resume_text: str, jd_text: str) -> AnalysisResponse:
    """Full pipeline: extract resume + JD (in parallel) -> score -> report -> save session."""
    guardrails.validate_resume_text(resume_text)
    guardrails.validate_jd_text(jd_text)
    resume_text, _ = guardrails.sanitize_document(resume_text, "resume")
    jd_text, _ = guardrails.sanitize_document(jd_text, "job description")
    resume, jd = await asyncio.gather(
        run_in_threadpool(extract_resume_data, resume_text),
        run_in_threadpool(extract_jd_data, jd_text),
    )
    match = compute_match(resume, jd, resume_text)

    # The score is already useful on its own, so a failed report must not lose it.
    report, report_error = None, None
    try:
        report = await run_in_threadpool(generate_report, resume_text, jd, match)
    except LLMError as exc:
        logger.warning("Returning score without report: %s", exc.message)
        report_error = exc.message

    session = session_store.create(
        resume_text=resume_text, resume=resume, jd_text=jd_text,
        jd=jd, match=match, report=report,
    )
    return AnalysisResponse(
        session_id=session.session_id, match=match, report=report, report_error=report_error
    )