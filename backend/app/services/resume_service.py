"""Resume generation. The LLM writes the draft, but Python checks it against the original resume,
so the final resume cannot quietly contain skills or numbers the candidate never had."""
import logging
import re
import time
from dataclasses import dataclass, field

from langchain_core.prompts import ChatPromptTemplate

from app.agents.prompts.resume_generation import RESUME_GENERATION_PROMPT
from app.core.exceptions import LLMError
from app.llm.provider import get_structured_llm
from app.schemas.agent import OptimizedResume, SkillGroup
from app.services.session_service import AnalysisSession
from app.utils.skill_normalizer import appears_in_text, canonical, is_literally_present

logger = logging.getLogger(__name__)

MAX_RESUME_CHARS = 12000
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class VerificationReport:
    removed_skills: list[str] = field(default_factory=list)        # not on resume, not confirmed
    unverified_numbers: list[str] = field(default_factory=list)    # numbers not in the original
    unconfirmed_mentions: list[str] = field(default_factory=list)  # missing skills used in the prose

    def warnings(self) -> list[str]:
        out = [f"The number '{n}' is not in your original resume. Check or remove it."
               for n in self.unverified_numbers]
        out += [f"The text mentions '{s}', which is not on your resume. Check or remove it."
                for s in self.unconfirmed_mentions]
        return out


def _prose(resume: OptimizedResume) -> str:
    parts = [resume.summary]
    for job in resume.experience:
        parts += job.bullets
    for project in resume.projects:
        parts += project.bullets + project.technologies
    return "\n".join(parts)


def verify_generated_resume(resume: OptimizedResume, resume_text: str,
                            confirmed_skills: list[str],
                            missing_skills: list[str] | None = None) -> tuple[OptimizedResume, VerificationReport]:
    text_lower = resume_text.lower()
    confirmed_keys = {canonical(s).lower() for s in confirmed_skills}
    report = VerificationReport()

    groups: list[SkillGroup] = []
    for group in resume.skill_groups:
        kept = []
        for skill in group.skills:
            if canonical(skill).lower() in confirmed_keys or is_literally_present(skill, text_lower):
                kept.append(skill)
            else:
                report.removed_skills.append(skill)
        if kept:
            groups.append(SkillGroup(name=group.name, skills=kept))
    cleaned = resume.model_copy(update={"skill_groups": groups})

    original_numbers = set(_NUMBER.findall(resume_text))
    prose = _prose(cleaned)
    for n in _NUMBER.findall(prose):
        if n not in original_numbers and n not in report.unverified_numbers:
            report.unverified_numbers.append(n)

    prose_lower = prose.lower()
    for skill in missing_skills or []:
        if canonical(skill).lower() in confirmed_keys:
            continue
        if appears_in_text(canonical(skill), prose_lower):
            report.unconfirmed_mentions.append(skill)
    return cleaned, report

def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def describe_changes(resume: OptimizedResume, original_text: str) -> dict:
    """What really changed versus the original, computed by code, so the chat reply cannot overclaim."""
    original = _squash(original_text)
    bullets = [b for j in resume.experience for b in j.bullets]
    bullets += [b for p in resume.projects for b in p.bullets]
    return {
        "summary_rewritten": bool(resume.summary) and _squash(resume.summary) not in original,
        "bullets_total": len(bullets),
        "bullets_reworded": sum(1 for b in bullets if _squash(b) not in original),
    }


def generate_optimized_resume(session: AnalysisSession) -> tuple[OptimizedResume, VerificationReport]:
    m = session.match
    confirmed = list(session.confirmed_skills)
    prompt = ChatPromptTemplate.from_template(RESUME_GENERATION_PROMPT)
    chain = prompt | get_structured_llm(OptimizedResume)
    try:
        start = time.perf_counter()
        draft: OptimizedResume = chain.invoke({
            "job_title": session.jd.job_title or "the role",
            "company": session.jd.company or "the company",
            "required_skills": ", ".join(m.required.matched + m.required.missing) or "none listed",
            "preferred_skills": ", ".join(m.preferred.matched + m.preferred.missing) or "none listed",
            "confirmed_skills": ", ".join(confirmed) or "none",
            "resume_text": session.resume_text[:MAX_RESUME_CHARS],
        })
        logger.info("Resume generation took %.1fs", time.perf_counter() - start)
    except Exception:
        logger.exception("Resume generation failed")
        raise LLMError("Could not generate the resume right now. Please try again.")

    missing = m.required.missing + m.preferred.missing + m.keywords.missing
    cleaned, report = verify_generated_resume(draft, session.resume_text, confirmed, missing)
    session.optimized_resume = cleaned
    return cleaned, report


def render_markdown(r: OptimizedResume) -> str:
    out = [f"# {r.name}"]
    if r.contact_line:
        out.append(r.contact_line)
    if r.summary:
        out += ["", "## Summary", r.summary]
    if r.skill_groups:
        out += ["", "## Skills"] + [f"- **{g.name}:** {', '.join(g.skills)}" for g in r.skill_groups]
    if r.experience:
        out += ["", "## Experience"]
        for job in r.experience:
            out.append(f"**{job.role}**, {job.company}" + (f" ({job.dates})" if job.dates else ""))
            out += [f"- {b}" for b in job.bullets]
            out.append("")
    if r.projects:
        out += ["## Projects"]
        for p in r.projects:
            tech = f" _({', '.join(p.technologies)})_" if p.technologies else ""
            out.append(f"**{p.name}**{tech}")
            out += [f"- {b}" for b in p.bullets]
            out.append("")
    if r.education:
        out += ["## Education"]
        for e in r.education:
            line = f"**{e.institution}**" + (f", {e.degree}" if e.degree else "") + (f" ({e.dates})" if e.dates else "")
            out += [line + (f" - {e.detail}" if e.detail else ""), ""]  
    if r.extras:
        out += ["", "## Certificates & Achievements"] + [f"- {x}" for x in r.extras]
    return "\n".join(out).strip() + "\n"