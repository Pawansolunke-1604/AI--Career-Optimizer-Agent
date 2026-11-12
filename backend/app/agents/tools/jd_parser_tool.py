import logging
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.prompts.jd_extraction import JD_EXTRACTION_PROMPT
from app.core.exceptions import LLMError
from app.llm.provider import get_structured_llm
from app.schemas.job_description import JobDescriptionData

logger = logging.getLogger(__name__)


def extract_jd_data(jd_text: str) -> JobDescriptionData:
    prompt = ChatPromptTemplate.from_template(JD_EXTRACTION_PROMPT)
    chain = prompt | get_structured_llm(JobDescriptionData)
    try:
        start = time.perf_counter()
        result = chain.invoke({"jd_text": jd_text})
        logger.info("JD extraction took %.1fs", time.perf_counter() - start)
        return result
    except Exception:
        logger.exception("JD extraction failed")
        raise LLMError("Could not analyze the job description right now. Please try again.")


@tool
def jd_parser_tool(jd_text: str) -> dict:
    """Extract structured requirements (skills, experience, responsibilities) from raw job description text."""
    return extract_jd_data(jd_text).model_dump()