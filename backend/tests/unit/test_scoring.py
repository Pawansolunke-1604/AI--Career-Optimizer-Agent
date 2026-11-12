from datetime import date

from app.schemas.job_description import JobDescriptionData
from app.schemas.resume import Experience, Project, ResumeData
from app.services.scoring_service import calculate_experience_years, compute_match
from app.utils.skill_normalizer import normalize_skills

TODAY = date(2026, 11, 4)

RESUME = ResumeData(
    name="Pawan Solunke",
    skills=["Java", "Python", "JavaScript", "SQL", "HTML", "CSS", "React.js", "Bootstrap",
            "Spring Boot", "Django", "REST APIs", "fastAPI", "NumPy", "Pandas", "Scikit-learn",
            "LLM", "LangChain", "Vector Embeddings", "RAG", "NLP", "OOP",
            "Data Structures & Algorithms", "DBMS", "MVC Architecture", "Git", "GitHub",
            "Docker", "CI/CD", "Gemini API", "Pydantic", "Random Forest", "Pickle"],
    experience=[
        Experience(company="The Kiran Academy", role="Data Science Intern",
                   start_date="2026-01", end_date="present"),
        Experience(company="Ekatt Innovators LLP", role="Full Stack Developer Intern",
                   start_date="2025-01", end_date="2025-06"),
    ],
    projects=[Project(name="RecruitFit AI", technologies=["Python", "LangChain", "Pydantic"])],
)

JD = JobDescriptionData(
    job_title="Software Engineer (Backend / AI)",
    required_skills=["Java", "Spring Boot", "REST APIs", "OOP", "Data Structures", "Algorithms",
                     "SQL", "MySQL", "PostgreSQL", "Git", "GitHub", "Microservices",
                     "Unit Testing", "JUnit"],
    preferred_skills=["Python", "FastAPI", "RAG", "Embeddings", "LLM APIs", "AWS", "Kafka",
                      "Message Queues", "Kubernetes", "Agile", "Scrum"],
    min_experience_years=0,
    experience_level="fresher",
    keywords=["LangChain", "Vector Databases", "Docker", "CI/CD", "React"],
)


def test_normalizer_merges_spellings():
    assert normalize_skills(["React", "React.js", "reactjs"]) == {"react": "React"}
    sql = normalize_skills(["SQL", "MySQL", "PostgreSQL"])
    assert list(sql.values()) == ["SQL"]


def test_experience_years_uses_dates_not_llm():
    # Ekatt Jan-Jun 2025 = 6 months, Kiran Jan 2026 - Nov 2026 = 11 months
    assert calculate_experience_years(RESUME.experience, TODAY) == 1.4


def test_overlapping_jobs_not_double_counted():
    jobs = [Experience(company="A", role="x", start_date="2025-01", end_date="2025-06"),
            Experience(company="B", role="y", start_date="2025-04", end_date="2025-06")]
    assert calculate_experience_years(jobs, TODAY) == 0.5


def test_bad_dates_are_ignored():
    jobs = [Experience(company="A", role="x", start_date="", end_date="")]
    assert calculate_experience_years(jobs, TODAY) == 0.0


def test_full_match_on_real_example():
    r = compute_match(RESUME, JD, today=TODAY)
    assert "Microservices" in r.required.missing
    assert "Unit Testing" in r.required.missing
    assert "SQL" in r.required.matched          # SQL covers MySQL/PostgreSQL
    assert "Data Structures & Algorithms" in r.required.matched
    assert "AWS" in r.preferred.missing and "Kubernetes" in r.preferred.missing
    assert "React" in r.keywords.matched
    assert "Vector Databases" in r.keywords.missing
    assert r.experience_met is True and r.breakdown.experience is None
    assert 0 <= r.overall_score <= 100


def test_text_fallback_rescues_missed_skill():
    jd = JobDescriptionData(required_skills=["Microservices"])
    r = compute_match(RESUME, jd, resume_text="Built microservices with Spring Boot", today=TODAY)
    assert r.required.missing == [] and r.overall_score == 100


def test_empty_jd_does_not_crash():
    r = compute_match(RESUME, JobDescriptionData(), today=TODAY)
    assert r.overall_score == 0