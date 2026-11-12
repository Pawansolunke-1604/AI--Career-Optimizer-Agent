# TODO: services/scoring_service.py
from datetime import date

from app.schemas.analysis import MatchResult, ScoreBreakdown, SkillCoverage
from app.schemas.job_description import JobDescriptionData
from app.schemas.resume import Experience, ResumeData
from app.utils.skill_normalizer import appears_in_text, filter_grounded_skills, normalize_skills

# How much each part counts. If the JD has nothing for a part, the rest are rescaled.
WEIGHTS = {"required_skills": 0.55, "preferred_skills": 0.15, "keywords": 0.15, "experience": 0.15}


def _month_index(value: str, today: date) -> int | None:
    """'2025-01' -> months since year 0. 'present' -> current month. Bad input -> None."""
    value = (value or "").strip().lower()
    if value in ("present", "current", "now", "ongoing"):
        return today.year * 12 + today.month
    try:
        year, month = value.split("-")[:2]
        y, m = int(year), int(month)
        if 1 <= m <= 12:
            return y * 12 + m
    except ValueError:
        pass
    return None


def calculate_experience_years(experience: list[Experience], today: date | None = None) -> float:
    """Total months worked (overlapping jobs are counted once), as years."""
    today = today or date.today()
    months: set[int] = set()
    for job in experience:
        start = _month_index(job.start_date, today)
        end = _month_index(job.end_date, today)
        if start is None or end is None or end < start:
            continue
        months.update(range(start, end + 1))  # both end months count
    return round(len(months) / 12, 1)


def _coverage(jd_skills: list[str], resume_keys: set[str], resume_text_lower: str) -> SkillCoverage:
    wanted = normalize_skills(jd_skills)
    if not wanted:
        return SkillCoverage()
    matched, missing = [], []
    for key, display in wanted.items():
        if key in resume_keys or appears_in_text(display, resume_text_lower):
            matched.append(display)
        else:
            missing.append(display)
    return SkillCoverage(matched=matched, missing=missing,
                         score=round(100 * len(matched) / len(wanted), 1))


def _label(score: int) -> str:
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= 40:
        return "Partial match"
    return "Low match"


def compute_match(resume: ResumeData, jd: JobDescriptionData, resume_text: str = "",
            today: date | None = None, extra_skills: list[str] | None = None) -> MatchResult:
    # everything the resume proves: listed skills + technologies used in projects
    skill_pool = list(resume.skills)
    for project in resume.projects:
        skill_pool.extend(project.technologies)

    ignored: list[str] = []
    if resume_text.strip():
        skill_pool, ignored = filter_grounded_skills(skill_pool, resume_text)
    if extra_skills:  # hypothetical skills for "what if I learned X" simulations
        skill_pool = skill_pool + list(extra_skills)
    resume_keys = set(normalize_skills(skill_pool))
    text_lower = resume_text.lower()

    required = _coverage(jd.required_skills, resume_keys, text_lower)
    preferred = _coverage(jd.preferred_skills, resume_keys, text_lower)
    keywords = _coverage(jd.keywords, resume_keys, text_lower)

    candidate_years = calculate_experience_years(resume.experience, today)
    needed = jd.min_experience_years
    exp_score: float | None = None
    exp_met: bool | None = None
    if needed:  # None or 0 means the JD asks for nothing, so it must not inflate the score
        exp_score = round(min(100.0, 100 * candidate_years / needed), 1)
        exp_met = candidate_years >= needed
    elif needed == 0:
        exp_met = True

    parts = {
        "required_skills": required.score,
        "preferred_skills": preferred.score,
        "keywords": keywords.score,
        "experience": exp_score,
    }
    active = {k: v for k, v in parts.items() if v is not None}
    if active:
        total_weight = sum(WEIGHTS[k] for k in active)
        overall = round(sum(WEIGHTS[k] * v for k, v in active.items()) / total_weight)
    else:
        overall = 0

    return MatchResult(
        overall_score=overall,
        label=_label(overall),
        breakdown=ScoreBreakdown(**parts),
        required=required,
        preferred=preferred,
        keywords=keywords,
        candidate_experience_years=candidate_years,
        required_experience_years=needed,
        experience_met=exp_met,
        ignored_skills=ignored,
    )