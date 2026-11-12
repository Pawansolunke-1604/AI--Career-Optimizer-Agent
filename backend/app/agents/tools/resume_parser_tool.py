import logging
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.prompts.resume_extraction import RESUME_EXTRACTION_PROMPT
from app.core.exceptions import LLMError
from app.llm.provider import get_structured_llm
from app.schemas.resume import ResumeData

logger = logging.getLogger(__name__)


def extract_resume_data(resume_text: str) -> ResumeData:
    """Plain function: used by services and tests."""
    prompt = ChatPromptTemplate.from_template(RESUME_EXTRACTION_PROMPT)
    chain = prompt | get_structured_llm(ResumeData)
    try:
        start = time.perf_counter()
        result = chain.invoke({"resume_text": resume_text})
        logger.info("Resume extraction took %.1fs", time.perf_counter() - start)
        return result
    except Exception:
        logger.exception("Resume extraction failed")
        raise LLMError("Could not analyze the resume right now. Please try again.")


@tool
def resume_parser_tool(resume_text: str) -> dict:
    """Extract structured data (skills, experience, education, projects) from raw resume text."""
    return extract_resume_data(resume_text).model_dump()