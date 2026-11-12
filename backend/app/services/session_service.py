"""In-memory store for finished analyses, so the chat agent has context for follow-up questions.

Good enough for one server process. Later (multi-worker / restarts) swap the dict for Redis or a
database: the rest of the app only talks to `session_store.create / get`.
"""
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable
from app.schemas.agent import OptimizedResume
from app.schemas.analysis import AnalysisReport, MatchResult
from app.schemas.job_description import JobDescriptionData
from app.schemas.resume import ResumeData


@dataclass
class AnalysisSession:
    session_id: str
    resume_text: str
    resume: ResumeData
    jd_text: str
    jd: JobDescriptionData
    match: MatchResult
    report: AnalysisReport | None
    created_at: float
    user_messages: list[str] = field(default_factory=list)  # what the user actually typed
    confirmed_skills: dict[str, str] = field(default_factory=dict)  # skill -> user's own words
    optimized_resume: OptimizedResume | None = None


class SessionStore:
    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 500,
                 clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._max = max_sessions
        self._clock = clock
        self._items: dict[str, AnalysisSession] = {}
        self._lock = threading.Lock()

    def create(self, *, resume_text: str, resume: ResumeData, jd_text: str,
               jd: JobDescriptionData, match: MatchResult,
               report: AnalysisReport | None) -> AnalysisSession:
        session = AnalysisSession(
            session_id=uuid.uuid4().hex,
            resume_text=resume_text, resume=resume, jd_text=jd_text, jd=jd,
            match=match, report=report, created_at=self._clock(),
        )
        with self._lock:
            self._evict()
            self._items[session.session_id] = session
        return session

    def get(self, session_id: str) -> AnalysisSession | None:
        with self._lock:
            session = self._items.get(session_id)
            if session is None:
                return None
            if self._clock() - session.created_at > self._ttl:
                del self._items[session_id]
                return None
            return session

    def _evict(self) -> None:
        """Drop expired sessions, then the oldest ones if we are over the size limit."""
        now = self._clock()
        for sid in [s for s, v in self._items.items() if now - v.created_at > self._ttl]:
            del self._items[sid]
        while len(self._items) >= self._max:
            oldest = min(self._items.values(), key=lambda v: v.created_at)
            del self._items[oldest.session_id]


session_store = SessionStore()