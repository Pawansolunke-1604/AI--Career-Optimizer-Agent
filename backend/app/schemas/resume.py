# TODO: schemas/resume.py
from pydantic import BaseModel, Field


class Experience(BaseModel):
    company: str
    role: str
    start_date: str = ""   # YYYY-MM
    end_date: str = ""     # YYYY-MM or "present"
   


class Education(BaseModel):
    institution: str
    degree: str = ""
    year: str = ""


class Project(BaseModel):
    name: str
    technologies: list[str] = Field(default_factory=list)
    


class ResumeData(BaseModel):
    name: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    