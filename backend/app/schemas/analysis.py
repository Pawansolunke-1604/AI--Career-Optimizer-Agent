# TODO: schemas/analysis.py
from pydantic import BaseModel, Field
from typing import Literal


class SkillCoverage(BaseModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    score: float | None = None  # 0-100, None if the JD listed nothing in this category


class ScoreBreakdown(BaseModel):
    required_skills: float | None = None
    preferred_skills: float | None = None
    keywords: float | None = None
    experience: float | None = None


class MatchResult(BaseModel):
    overall_score: int
    label: str
    breakdown: ScoreBreakdown
    required: SkillCoverage
    preferred: SkillCoverage
    keywords: SkillCoverage
    candidate_experience_years: float
    required_experience_years: float | None = None
    experience_met: bool | None = None
    ignored_skills: list[str] = Field(default_factory=list)  # extracted but not found in resume text


class Strength(BaseModel):
    title: str
    evidence: str  # where in the resume this shows up


class GapAdvice(BaseModel):
    """What the LLM returns for one missing skill (it does not decide WHICH skills are missing)."""
    skill: str
    suggestion: str


class ResumeTip(BaseModel):
    section: str
    tip: str


class ReportDraft(BaseModel):
    """The shape the LLM fills in."""
    summary: str = ""
    strengths: list[Strength] = Field(default_factory=list)
    gap_advice: list[GapAdvice] = Field(default_factory=list)
    resume_tips: list[ResumeTip] = Field(default_factory=list)


class Gap(BaseModel):
    skill: str
    importance: Literal["required", "preferred", "keyword"]
    suggestion: str


class AnalysisReport(BaseModel):
    summary: str
    strengths: list[Strength]
    gaps: list[Gap]
    resume_tips: list[ResumeTip]


class AnalysisResponse(BaseModel):
    session_id: str | None = None  # use this to chat with the agent about this analysis
    match: MatchResult
    report: AnalysisReport | None = None
    report_error: str | None = None