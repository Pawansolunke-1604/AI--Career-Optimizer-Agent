# TODO: agents/tools/match_tool.py
from langchain_core.tools import tool

from app.schemas.job_description import JobDescriptionData
from app.schemas.resume import ResumeData
from app.services.scoring_service import compute_match


@tool
def match_tool(resume: dict, job_description: dict, resume_text: str = "") -> dict:
    """Score how well a structured resume matches a structured job description.
    Returns an overall score plus matched and missing skills."""
    result = compute_match(
        ResumeData(**resume), JobDescriptionData(**job_description), resume_text
    )
    return result.model_dump()