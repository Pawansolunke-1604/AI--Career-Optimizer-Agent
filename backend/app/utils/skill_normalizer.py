"""Maps skill spellings to one canonical name so 'React.js' == 'React', and so that
one JD requirement is never counted as several gaps (SQL / MySQL / PostgreSQL)."""
import re

# canonical display name -> every spelling that counts as the same thing
_GROUPS: dict[str, list[str]] = {
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite", "sql server", "mssql",
            "relational databases", "rdbms"],
    "Data Structures & Algorithms": ["data structures", "algorithms", "dsa",
                                     "data structures & algorithms",
                                     "data structures and algorithms"],
    "REST APIs": ["rest apis", "rest api", "restful apis", "restful api", "rest", "restful"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs", "node"],
    "JavaScript": ["javascript", "js"],
    "Spring Boot": ["spring boot", "springboot"],
    "FastAPI": ["fastapi", "fast api"],
    "Unit Testing": ["unit testing", "junit", "testng"],
    "Message Queues": ["message queues", "message queue", "kafka", "rabbitmq"],
    "Agile": ["agile", "scrum", "agile/scrum"],
    "AWS": ["aws", "amazon web services", "ec2", "s3"],
    "CI/CD": ["ci/cd", "cicd", "ci cd"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Embeddings": ["embeddings", "vector embeddings"],
    "Vector Databases": ["vector databases", "vector database", "vector db", "faiss",
                         "chromadb", "pinecone"],
    "LLM": ["llm", "llms", "llm apis", "llm api", "large language models",
            "gemini api", "openai api"],
    "Machine Learning": ["machine learning", "ml"],
    "Microservices": ["microservices", "microservice architecture"],
}

_ALIAS_TO_CANON: dict[str, str] = {}
_CANON_TO_ALIASES: dict[str, list[str]] = {}
for _canon, _aliases in _GROUPS.items():
    _all = set(_aliases) | {_canon.lower()}
    _CANON_TO_ALIASES[_canon] = sorted(_all)
    for _a in _all:
        _ALIAS_TO_CANON[_a] = _canon


def _clean(skill: str) -> str:
    return re.sub(r"\s+", " ", skill.strip().lower()).strip(" .,;:")


def canonical(skill: str) -> str:
    """Return the canonical display name of a skill."""
    cleaned = _clean(skill)
    return _ALIAS_TO_CANON.get(cleaned, skill.strip())


def normalize_skills(skills: list[str]) -> dict[str, str]:
    """Return {canonical lowercase key: display name}, de-duplicated, order preserved."""
    result: dict[str, str] = {}
    for s in skills:
        if not s or not s.strip():
            continue
        name = canonical(s)
        result.setdefault(name.lower(), name)
    return result


def appears_in_text(skill_name: str, text_lower: str) -> bool:
    """Fallback check on the raw resume text, in case the LLM missed a skill."""
    variants = _CANON_TO_ALIASES.get(skill_name, [skill_name.lower()])
    for v in variants:
        if len(v) < 2:
            continue
        if re.search(rf"(?<![\w+#]){re.escape(v)}(?![\w+#])", text_lower):
            return True
    return False

def _found(variant: str, text_lower: str) -> bool:
    return bool(re.search(rf"(?<![\w+#]){re.escape(variant)}(?![\w+#])", text_lower))


def is_grounded(skill: str, text_lower: str) -> bool:
    """True if the skill (or a known spelling of it) is actually written in the resume text."""
    name = canonical(skill)
    variants = set(_CANON_TO_ALIASES.get(name, [])) | {skill.strip().lower(), name.lower()}
    variants = {v for v in variants if len(v) >= 2}
    if any(_found(v, text_lower) for v in variants):
        return True
    # PDF text sometimes has stray spaces ("Sc ikit-learn"): retry with all whitespace removed
    squashed_text = re.sub(r"\s+", "", text_lower)
    for v in variants:
        squashed = re.sub(r"\s+", "", v)
        if len(squashed) >= 5 and squashed in squashed_text:
            return True
    return False


def filter_grounded_skills(skills: list[str], resume_text: str) -> tuple[list[str], list[str]]:
    """Split LLM-extracted skills into (kept, removed). A skill the resume never mentions is removed."""
    text_lower = resume_text.lower()
    kept, removed = [], []
    for s in skills:
        (kept if is_grounded(s, text_lower) else removed).append(s)
    return kept, removed

def skill_variants(skill: str) -> set[str]:
    """All spellings that count as the same skill (lowercase), including the skill itself."""
    name = canonical(skill)
    variants = set(_CANON_TO_ALIASES.get(name, [])) | {skill.strip().lower(), name.lower()}
    return {v for v in variants if len(v) >= 2}

def is_literally_present(skill: str, text_lower: str) -> bool:
    """Strict check: the skill's OWN wording is in the text (no alias groups).
    Tolerates PDF spacing glitches ("W eb") and punctuation/spacing differences. Used for the
    generated resume, where 'MySQL' must not pass just because the original says 'SQL'."""
    chars = [re.escape(c) for c in re.sub(r"\s+", "", skill.strip().lower())]
    if len(chars) < 2:
        return False
    pattern = r"(?<![\w+#])" + r"\s*".join(chars) + r"(?![\w+#])"
    return bool(re.search(pattern, text_lower))