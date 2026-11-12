# TODO: schemas/job_description.py
from pydantic import BaseModel, Field


class JobDescriptionData(BaseModel):
    job_title: str = ""
    company: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    experience_level: str = ""  # e.g. fresher, junior, mid, senior
    education_requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)  # domain/ATS terms