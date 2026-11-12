from pydantic import BaseModel, Field


class BulletRewrite(BaseModel):
    rewritten: str
    notes: str = ""
    needs_from_user: list[str] = Field(default_factory=list)  # facts only the candidate can supply


class SkillGroup(BaseModel):
    name: str
    skills: list[str] = Field(default_factory=list)


class ResumeJob(BaseModel):
    company: str
    role: str
    dates: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeProject(BaseModel):
    name: str
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    institution: str
    degree: str = ""
    dates: str = ""
    detail: str = ""


class OptimizedResume(BaseModel):
    name: str
    contact_line: str = ""
    summary: str = ""
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    experience: list[ResumeJob] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    extras: list[str] = Field(default_factory=list)  # certificates, achievements