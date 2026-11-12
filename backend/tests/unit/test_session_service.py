from app.services.session_service import SessionStore
from app.services.scoring_service import compute_match
from tests.unit.test_scoring import JD, RESUME, RESUME_TEXT, TODAY


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _make(store):
    match = compute_match(RESUME, JD, RESUME_TEXT, today=TODAY)
    return store.create(resume_text=RESUME_TEXT, resume=RESUME, jd_text="jd", jd=JD,
                        match=match, report=None)


def test_create_and_get():
    store = SessionStore()
    s = _make(store)
    assert store.get(s.session_id) is s
    assert store.get("does-not-exist") is None


def test_expired_session_is_gone():
    clock = FakeClock()
    store = SessionStore(ttl_seconds=60, clock=clock)
    s = _make(store)
    clock.t = 61
    assert store.get(s.session_id) is None


def test_oldest_evicted_when_full():
    clock = FakeClock()
    store = SessionStore(max_sessions=2, clock=clock)
    a = _make(store); clock.t = 1
    b = _make(store); clock.t = 2
    c = _make(store)
    assert store.get(a.session_id) is None
    assert store.get(b.session_id) and store.get(c.session_id)