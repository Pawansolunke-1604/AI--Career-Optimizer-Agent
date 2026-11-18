"""Rule-based guardrails. No LLM calls, so they cost nothing on the free Gemini tier."""
import logging
import re
import unicodedata

from app.core.exceptions import InputRejectedError

logger = logging.getLogger(__name__)

MIN_RESUME_CHARS, MAX_RESUME_CHARS = 200, 30_000
MIN_JD_CHARS, MAX_JD_CHARS = 100, 20_000

RESUME_HINTS = ("experience", "education", "skills", "projects", "summary", "objective",
                "certification", "internship", "work history", "profile")
# Weaker signals: used only together with a contact detail, for resumes with creative section names.
SOFT_HINTS = ("university", "college", "institute", "bachelor", "master", "degree", "b.e", "b.tech",
              "b.sc", "m.sc", "mba", "developer", "engineer", "analyst", "intern", "worked", "tools",
              "technologies", "languages", "frameworks", "achievement")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
JD_HINTS = ("responsibilit", "requirement", "qualification", "skills", "experience", "role",
            "position", "we are looking", "preferred", "must have", "apply", "job", "candidate")

_I = re.I
INJECTION_PATTERNS = [re.compile(p, _I) for p in (
    r"ignore (all |any |the )?(previous|prior|above|earlier|your) (instructions|prompts?|rules)",
    r"disregard (all |any |the )?(previous|prior|above|earlier|your) (instructions|prompts?|rules)",
    r"forget (all |everything |any |your |the |previous |prior )*(instructions|rules)",
    r"(reveal|show|print|repeat|tell me) (me )?(your|the) (system |hidden |initial )?(prompt|instructions)",
    r"you are now (a|an|the|in)\b",
    r"act as (a|an|the) (ai|assistant|llm|chatbot|different|unrestricted)",
    r"\b(jailbreak|developer mode|do anything now|dan mode)\b",
    r"(new|updated) (system )?instructions\s*:",
    r"^\s*(system|assistant)\s*:",
    r"<\|.*?\|>",
    r"override (your|the|all) (rules|instructions|safety|guidelines)",
    r"(rate|score|rank) (this|the) (candidate|resume) (as |a )?(100|perfect|10/10|top)",
)]

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(text: str) -> str:
    """Normalize unicode and drop invisible characters (used to hide injections)."""
    text = unicodedata.normalize("NFKC", text)
    return _CONTROL.sub("", _ZERO_WIDTH.sub("", text))


def find_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_PATTERNS)


def _hints(text: str, hints: tuple[str, ...]) -> int:
    low = text.lower()
    return sum(h in low for h in hints)

def _looks_like_resume(text: str) -> bool:
    strong = _hints(text, RESUME_HINTS)
    if strong >= 2:
        return True
    has_contact = bool(EMAIL.search(text) or PHONE.search(text))
    return has_contact and strong + _hints(text, SOFT_HINTS) >= 2


def validate_resume_text(text: str) -> None:
    n = len(text.strip())
    if n < MIN_RESUME_CHARS:
        raise InputRejectedError("This file has too little text to be a resume. If it is a scanned "
                                 "image, please upload a text-based PDF or DOCX.")
    if n > MAX_RESUME_CHARS:
        raise InputRejectedError("This document is too long to be a resume.")
    if not _looks_like_resume(text):
        raise InputRejectedError("This doesn't look like a resume (no sections like skills, "
                                 "experience or education were found).")


def validate_jd_text(text: str) -> None:
    n = len(text.strip())
    if n < MIN_JD_CHARS:
        raise InputRejectedError("The job description is too short. Please paste the full description.")
    if n > MAX_JD_CHARS:
        raise InputRejectedError("The job description is too long.")
    if _hints(text, JD_HINTS) < 3:
        raise InputRejectedError("This doesn't look like a job description.")


def sanitize_document(text: str, kind: str) -> tuple[str, int]:
    """Remove lines that try to instruct the AI. Returns (clean_text, removed_line_count)."""
    kept, removed = [], 0
    for line in clean_text(text).splitlines():
        if find_injection(line):
            removed += 1
        else:
            kept.append(line)
    if removed:
        logger.warning("Guardrail: removed %d suspicious line(s) from %s", removed, kind)
    return "\n".join(kept), removed


def check_chat_message(message: str) -> str:
    msg = clean_text(message).strip()
    if not msg:
        raise InputRejectedError("Please type a message.")
    if find_injection(msg):
        logger.warning("Guardrail: chat message rejected (injection pattern)")
        raise InputRejectedError("I can only help with your resume and this job match. "
                                 "Please rephrase your question.")
    return msg