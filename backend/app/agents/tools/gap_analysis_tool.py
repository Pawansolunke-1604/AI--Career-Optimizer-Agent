# TODO: agents/tools/gap_analysis_tool.py
import logging
import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from app.agents.prompts.gap_analysis import GAP_ANALYSIS_PROMPT
from app.core.exceptions import LLMError
from app.llm.provider import get_structured_llm
from app.schemas.analysis import (
    AnalysisReport,
    Gap,
    GapAdvice,
    MatchResult,
    ReportDraft,
)
from app.schemas.job_description import JobDescriptionData

logger = logging.getLogger(__name__)

MAX_RESUME_CHARS = 12000


def _join(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def build_prompt_inputs(resume_text: str, jd: JobDescriptionData, match: MatchResult) -> dict:
    return {
        "job_title": jd.job_title or "the role",
        "company": jd.company or "the company",
        "responsibilities": "\n".join(f"- {r}" for r in jd.responsibilities[:10]) or "- not listed",
        "matched_required": _join(match.required.matched),
        "missing_required": _join(match.required.missing),
        "matched_preferred": _join(match.preferred.matched),
        "missing_preferred": _join(match.preferred.missing),
        "missing_keywords": _join(match.keywords.missing),
        "resume_text": resume_text[:MAX_RESUME_CHARS],
    }


def build_gaps(match: MatchResult, advice: list[GapAdvice]) -> list[Gap]:
    """Python decides WHICH skills are gaps. The LLM only supplies the advice text."""
    by_skill = {a.skill.strip().lower(): a.suggestion for a in advice}
    gaps: list[Gap] = []
    for importance, skills in (
        ("required", match.required.missing),
        ("preferred", match.preferred.missing),
        ("keyword", match.keywords.missing),
    ):
        for skill in skills:
            gaps.append(
                Gap(
                    skill=skill,
                    importance=importance,
                    suggestion=by_skill.get(
                        skill.lower(), "Learn the basics and build a small project using it."
                    ),
                )
            )
    return gaps


def generate_report(resume_text: str, jd: JobDescriptionData, match: MatchResult) -> AnalysisReport:
    prompt = ChatPromptTemplate.from_template(GAP_ANALYSIS_PROMPT)
    chain = prompt | get_structured_llm(ReportDraft)
    try:
        start = time.perf_counter()
        draft: ReportDraft = chain.invoke(build_prompt_inputs(resume_text, jd, match))
        logger.info("Report generation took %.1fs", time.perf_counter() - start)
    except Exception:
        logger.exception("Report generation failed")
        raise LLMError("Could not generate the detailed report right now. Please try again.")

    return AnalysisReport(
        summary=draft.summary,
        strengths=draft.strengths,
        gaps=build_gaps(match, draft.gap_advice),
        resume_tips=draft.resume_tips,
    )


@tool
def gap_analysis_tool(resume_text: str, job_description: dict, match_result: dict) -> dict:
    """Write a strengths and gaps report for a resume, given the job description and the computed match."""
    report = generate_report(
        resume_text, JobDescriptionData(**job_description), MatchResult(**match_result)
    )
    return report.model_dump()