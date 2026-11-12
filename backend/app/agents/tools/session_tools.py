"""Tools the chat agent can call. Each tool is bound to ONE analysis session, so the LLM only says
what it wants and the tool reads the data itself. The model never passes resume text through arguments."""
import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, tool

from app.agents.prompts.bullet_rewrite import BULLET_REWRITE_PROMPT
from app.core.exceptions import LLMError
from app.llm.provider import get_structured_llm
from app.schemas.agent import BulletRewrite
from app.services import resume_service
from app.services.scoring_service import compute_match
from app.services.session_service import AnalysisSession
from app.utils.skill_normalizer import canonical, skill_variants

logger = logging.getLogger(__name__)

MAX_EVIDENCE_LINES = 5
NEGATIONS = ("don't have", "do not have", "never used", "no experience", "haven't", "have not",
             "not used", "don't know", "do not know", "never worked")


# ---------- plain functions (easy to unit test) ----------

def analysis_overview(session: AnalysisSession) -> dict:
    m = session.match
    return {
        "job_title": session.jd.job_title,
        "company": session.jd.company,
        "overall_score": m.overall_score,
        "label": m.label,
        "breakdown": m.breakdown.model_dump(),
        "required_matched": m.required.matched,
        "required_missing": m.required.missing,
        "preferred_matched": m.preferred.matched,
        "preferred_missing": m.preferred.missing,
        "keywords_missing": m.keywords.missing,
        "candidate_experience_years": m.candidate_experience_years,
        "required_experience_years": m.required_experience_years,
        "strengths": [s.title for s in session.report.strengths] if session.report else [],
        "summary": session.report.summary if session.report else None,
    }


def find_evidence(session: AnalysisSession, topic: str) -> list[str]:
    """Lines of the resume that mention the topic (or a known spelling of it)."""
    variants = skill_variants(topic)
    found: list[str] = []
    for line in session.resume_text.splitlines():
        low = line.lower()
        if any(re.search(rf"(?<![\w+#]){re.escape(v)}(?![\w+#])", low) for v in variants):
            found.append(line.strip())
        if len(found) >= MAX_EVIDENCE_LINES:
            break
    return found


def explain_gap_for(session: AnalysisSession, skill: str) -> dict:
    key = canonical(skill).lower()
    evidence = find_evidence(session, skill)
    if session.report:
        for gap in session.report.gaps:
            if canonical(gap.skill).lower() == key:
                return {"status": "missing", "skill": gap.skill, "importance": gap.importance,
                        "suggestion": gap.suggestion, "related_resume_lines": evidence}
    m = session.match
    all_missing = m.required.missing + m.preferred.missing + m.keywords.missing
    if any(canonical(s).lower() == key for s in all_missing):
        return {"status": "missing", "skill": skill, "related_resume_lines": evidence}
    all_matched = m.required.matched + m.preferred.matched + m.keywords.matched
    if any(canonical(s).lower() == key for s in all_matched):
        return {"status": "already_matched", "skill": skill, "resume_lines": evidence}
    return {"status": "not_in_job_requirements", "skill": skill, "resume_lines": evidence}


def simulate_score_for(session: AnalysisSession, skills_to_add: list[str]) -> dict:
    """What-if only: nothing is saved and the resume is not changed."""
    base = compute_match(session.resume, session.jd, session.resume_text)
    new = compute_match(session.resume, session.jd, session.resume_text, extra_skills=skills_to_add)
    before = set(base.required.matched + base.preferred.matched + base.keywords.matched)
    after = set(new.required.matched + new.preferred.matched + new.keywords.matched)
    return {
        "current_score": base.overall_score,
        "simulated_score": new.overall_score,
        "newly_matched": sorted(after - before),
        "still_missing_required": new.required.missing,
        "still_missing_preferred": new.preferred.missing,
        "note": "Hypothetical only. These skills are NOT on the resume.",
    }


def rewrite_bullet_for(session: AnalysisSession, bullet: str) -> BulletRewrite:
    prompt = ChatPromptTemplate.from_template(BULLET_REWRITE_PROMPT)
    chain = prompt | get_structured_llm(BulletRewrite)
    try:
        return chain.invoke({
            "job_title": session.jd.job_title or "the role",
            "required_skills": ", ".join(session.match.required.matched + session.match.required.missing),
            "bullet": bullet[:1500],
        })
    except Exception:
        logger.exception("Bullet rewrite failed")
        raise LLMError("Could not rewrite the bullet right now. Please try again.")

def confirm_skill_for(session: AnalysisSession, skill: str, user_quote: str) -> dict:
    """Record a missing skill as confirmed ONLY if the user's own words (a real quote from their
    messages) say they have used it. The model cannot confirm a skill on the user's behalf."""
    quote = user_quote.strip().lower()
    if len(quote) < 5:
        return {"status": "rejected", "reason": "Quote too short. Ask the user to say it in their own words."}
    if not any(quote in m.lower() for m in session.user_messages):
        return {"status": "rejected", "reason": "That quote is not in the user's messages. Ask the user."}
    if any(n in quote for n in NEGATIONS):
        return {"status": "rejected", "reason": "The user said they do NOT have this experience."}
    if not any(re.search(rf"(?<![\w+#]){re.escape(v)}(?![\w+#])", quote) for v in skill_variants(skill)):
        return {"status": "rejected", "reason": f"The quote does not mention {skill}."}
    session.confirmed_skills[canonical(skill)] = user_quote.strip()
    return {"status": "confirmed", "skill": canonical(skill)}

# ---------- LangChain tools bound to one session ----------

def build_session_tools(session: AnalysisSession) -> list[BaseTool]:
    @tool
    def get_analysis_overview() -> dict:
        """Get the full analysis for this candidate: match score, label, score breakdown, matched and
        missing skills, experience years, and the strengths summary. Call this first for any question
        about the score, how well the resume fits, or what is missing overall."""
        return analysis_overview(session)

    @tool
    def explain_gap(skill: str) -> dict:
        """Explain one specific skill for this job: is it missing, how important is it (required or
        preferred), a practical suggestion to close the gap, and any resume lines that relate to it.
        Use it when the user asks about a particular skill such as 'Kubernetes' or 'Microservices'."""
        return explain_gap_for(session, skill)

    @tool
    def find_resume_evidence(topic: str) -> list[str]:
        """Search the candidate's resume for lines mentioning a skill or topic. Use it to check what the
        resume actually says before claiming the candidate has or lacks something."""
        return find_evidence(session, topic)

    @tool
    def simulate_score(skills_to_add: list[str]) -> dict:
        """What-if calculator: show how the match score would change IF the candidate learned the given
        skills. It does not change the resume. Use it for questions like 'what would my score be if I
        learned AWS and Kubernetes?'."""
        return simulate_score_for(session, skills_to_add)

    @tool
    def rewrite_resume_bullet(bullet: str) -> dict:
        """Rewrite ONE resume bullet point so it fits the target job better, using only the facts in the
        bullet. Returns the rewrite, a short note, and questions for facts only the candidate knows
        (such as a metric). Use it when the user pastes or names a bullet to improve."""
        try:
            return rewrite_bullet_for(session, bullet).model_dump()
        except LLMError as exc:
            return {"error": exc.message}

    @tool
    def confirm_skill(skill: str, user_quote: str) -> dict:
        """Record that the USER says they genuinely have experience with a skill that is missing from
        their resume. user_quote must be the user's own words, copied exactly from their message, and
        it must mention the skill. Only call this after the user has actually said it. Never call it
        on your own, and never for a skill the user said they do not have."""
        return confirm_skill_for(session, skill, user_quote)

    @tool
    def generate_optimized_resume() -> dict:
        """Generate an optimized version of the candidate's resume for this job, using only facts from
        the original resume plus skills the user confirmed. The full resume is shown to the user
        automatically, so do NOT retype it. Use it when the user asks for a new, improved or tailored
        resume."""
        try:
            resume, report = resume_service.generate_optimized_resume(session)
        except LLMError as exc:
            return {"error": exc.message}
        return {
            "status": "generated",
            "changes": resume_service.describe_changes(resume, session.resume_text),
            "confirmed_skills_used": list(session.confirmed_skills),
            "skills_removed_because_unconfirmed": report.removed_skills,
            "warnings": report.warnings(),
            "note": "The full resume is displayed to the user automatically. Do NOT retype it. "
                    "Describe what changed using ONLY the 'changes' field (do not claim any other edits) "
                    "and mention any warnings.",
        }

    return [get_analysis_overview, explain_gap, find_resume_evidence, simulate_score,
            rewrite_resume_bullet, confirm_skill, generate_optimized_resume]