# TODO: api/v1/endpoints/analysis.py
import asyncio
from app.services.scoring_service import compute_match
from fastapi import APIRouter, File, UploadFile

from app.services.file_service import extract_text_from_upload
from fastapi.concurrency import run_in_threadpool
from app.agents.tools.resume_parser_tool import extract_resume_data
from fastapi import Form
from app.agents.tools.jd_parser_tool import extract_jd_data
from app.core.exceptions import EmptyDocumentError, FileTooLargeError
from app.utils.text_cleaner import clean_text
from app.schemas.analysis import AnalysisResponse
from app.services.analysis_service import analyze

router = APIRouter(prefix="/analysis")


@router.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    text = await extract_text_from_upload(file)
    return {"filename": file.filename, "characters": len(text), "preview": text}

@router.post("/extract-resume")
async def extract_resume(file: UploadFile = File(...)):
    text = await extract_text_from_upload(file)
    data = await run_in_threadpool(extract_resume_data, text)
    return data

@router.post("/extract-jd")
async def extract_jd(jd_text: str = Form(...)):
    jd_text = clean_text(jd_text)
    if len(jd_text) < 50:
        raise EmptyDocumentError("The job description is too short.")
    if len(jd_text) > 15000:
        raise FileTooLargeError("The job description is too long.")
    return await run_in_threadpool(extract_jd_data, jd_text)


@router.post("/score")
async def score(file: UploadFile = File(...), jd_text: str = Form(...)):
    resume_text = await extract_text_from_upload(file)
    jd_text = clean_text(jd_text)
    if len(jd_text) < 50:
        raise EmptyDocumentError("The job description is too short.")
    if len(jd_text) > 15000:
        raise FileTooLargeError("The job description is too long.")

    resume, jd = await asyncio.gather(
        run_in_threadpool(extract_resume_data, resume_text),
        run_in_threadpool(extract_jd_data, jd_text),
    )
    return compute_match(resume, jd, resume_text)

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(file: UploadFile = File(...), jd_text: str = Form(...)):
    resume_text = await extract_text_from_upload(file)
    jd_text = clean_text(jd_text)
    if len(jd_text) < 50:
        raise EmptyDocumentError("The job description is too short.")
    if len(jd_text) > 15000:
        raise FileTooLargeError("The job description is too long.")
    return await analyze(resume_text, jd_text)