import asyncio

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.agents.tools.jd_parser_tool import extract_jd_data
from app.agents.tools.resume_parser_tool import extract_resume_data
from app.core.exceptions import EmptyDocumentError, FileTooLargeError
from app.core.rate_limit import rate_limit
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import analyze
from app.services.file_service import extract_text_from_upload
from app.services.scoring_service import compute_match
from app.utils.text_cleaner import clean_text

router = APIRouter(prefix="/analysis")

# One Gemini key is shared by everyone, so these limits protect the free quota:
# 5 requests per IP per 10 minutes, and 4 per minute across all users together.
llm_limit = Depends(rate_limit("analyze", per_ip=5, window_s=600, global_limit=4))


def _checked_jd(jd_text: str) -> str:
    jd_text = clean_text(jd_text)
    if len(jd_text) < 50:
        raise EmptyDocumentError("The job description is too short.")
    if len(jd_text) > 15000:
        raise FileTooLargeError("The job description is too long.")
    return jd_text


@router.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    text = await extract_text_from_upload(file)
    return {"filename": file.filename, "characters": len(text), "preview": text}


@router.post("/extract-resume", dependencies=[llm_limit])
async def extract_resume(file: UploadFile = File(...)):
    text = await extract_text_from_upload(file)
    return await run_in_threadpool(extract_resume_data, text)


@router.post("/extract-jd", dependencies=[llm_limit])
async def extract_jd(jd_text: str = Form(...)):
    return await run_in_threadpool(extract_jd_data, _checked_jd(jd_text))


@router.post("/score", dependencies=[llm_limit])
async def score(file: UploadFile = File(...), jd_text: str = Form(...)):
    resume_text = await extract_text_from_upload(file)
    jd_text = _checked_jd(jd_text)
    resume, jd = await asyncio.gather(
        run_in_threadpool(extract_resume_data, resume_text),
        run_in_threadpool(extract_jd_data, jd_text),
    )
    return compute_match(resume, jd, resume_text)


@router.post("/analyze", response_model=AnalysisResponse, dependencies=[llm_limit])
async def analyze_endpoint(file: UploadFile = File(...), jd_text: str = Form(...)):
    resume_text = await extract_text_from_upload(file)
    return await analyze(resume_text, _checked_jd(jd_text))