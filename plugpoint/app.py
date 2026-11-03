"""PlugPoint API + static demo UI.

Run:  uvicorn plugpoint.app:app --reload --port 8000   then open http://localhost:8000
"""

from __future__ import annotations

import os
import secrets
import threading
import time
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from .extract import ExtractionUnavailable, extract_action_plan, llm_available
from .fixtures import CLINICIANS, MOCK_PLANS, PATIENTS, SAMPLE_NOTES
from .schema import ApproveRequest, PlanRequest
from .tracker import Store

app = FastAPI(title="PlugPoint", version="0.1.0")

# ------------------------------------------------------------------ canonical address
# Requests to an old host (e.g. the original Railway URL) get a permanent redirect to the same path
# on the canonical domain. Only hosts listed here are redirected, so localhost and the canonical
# domain are untouched.
CANONICAL_HOST = os.environ.get("PLUGPOINT_CANONICAL_HOST", "plugpoint.pharmatools.ai")
REDIRECT_HOSTS = {h.strip().lower() for h in os.environ.get(
    "PLUGPOINT_REDIRECT_HOSTS", "web-production-4653b.up.railway.app").split(",") if h.strip()}


@app.middleware("http")
async def redirect_old_hosts(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0].lower()
    if CANONICAL_HOST and host in REDIRECT_HOSTS:
        target = f"https://{CANONICAL_HOST}{request.url.path}"
        if request.url.query:
            target += f"?{request.url.query}"
        # 301 for page loads; 308 keeps the method and body for any API calls still using the old host
        return RedirectResponse(target, status_code=301 if request.method in ("GET", "HEAD") else 308)
    return await call_next(request)
STATIC = Path(__file__).parent / "static"

# ------------------------------------------------------------------ public-demo safeguards
# All tunable from the environment so the hosted demo can be loosened or tightened without a deploy.
SESSION_COOKIE = "pp_sid"
SESSION_IDLE_SECONDS = int(os.environ.get("PLUGPOINT_SESSION_IDLE_SECONDS", 2 * 60 * 60))
MAX_SESSIONS = int(os.environ.get("PLUGPOINT_MAX_SESSIONS", 500))
IP_HOURLY = int(os.environ.get("PLUGPOINT_IP_HOURLY", 5))          # live extractions per visitor IP per hour
DAILY_CAP = int(os.environ.get("PLUGPOINT_DAILY_CAP", 50))         # live extractions per day, whole server
MAX_NOTE_CHARS = int(os.environ.get("PLUGPOINT_MAX_NOTE_CHARS", 4000))
PUBLIC_LIVE_EVAL = os.environ.get("PLUGPOINT_PUBLIC_LIVE_EVAL") == "1"  # 17 model calls per click: off by default
SAMPLES_LIVE = os.environ.get("PLUGPOINT_SAMPLES_LIVE") == "1"     # unedited samples use their saved extraction

_lock = threading.Lock()
_sessions: dict[str, tuple[Store, float]] = {}
_ip_hits: dict[str, list[float]] = {}
_day = {"date": date.today(), "count": 0}


def get_store(request: Request, response: Response) -> Store:
    """Each visitor gets their own demo state, keyed by a session cookie and dropped after
    SESSION_IDLE_SECONDS of inactivity, so one visitor's notes never appear in another's worklist."""
    now = time.time()
    sid = request.cookies.get(SESSION_COOKIE)
    with _lock:
        for k, (_, seen) in list(_sessions.items()):
            if now - seen > SESSION_IDLE_SECONDS:
                del _sessions[k]
        if not sid or sid not in _sessions:
            if len(_sessions) >= MAX_SESSIONS:
                del _sessions[min(_sessions, key=lambda k: _sessions[k][1])]
            sid = secrets.token_urlsafe(18)
            _sessions[sid] = (Store(), now)
            https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
            response.set_cookie(SESSION_COOKIE, sid, max_age=SESSION_IDLE_SECONDS, httponly=True,
                                samesite="lax", secure=https)
        store = _sessions[sid][0]
        _sessions[sid] = (store, now)
    return store


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _take_live_quota(ip: str) -> None:
    """Counts one live (paid) extraction against the per-IP hourly and server-wide daily limits."""
    now = time.time()
    with _lock:
        if _day["date"] != date.today():
            _day.update(date=date.today(), count=0)
        if _day["count"] >= DAILY_CAP:
            raise HTTPException(429, "The live demo has reached today's limit for new notes. "
                                     "The built-in samples still work, or try again tomorrow.")
        hits = [t for t in _ip_hits.get(ip, []) if now - t < 3600]
        if len(hits) >= IP_HOURLY:
            raise HTTPException(429, "You've reached the hourly limit for new notes. "
                                     "The built-in samples still work, or try again later.")
        hits.append(now)
        _ip_hits[ip] = hits
        _day["count"] += 1


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/eval")
def eval_page():
    return FileResponse(STATIC / "eval.html")


@app.get("/api/eval/results")
def eval_results():
    from eval.run_eval import RESULTS_PATH
    import json
    if not RESULTS_PATH.exists():
        return {"summary": None, "results": []}
    return json.loads(RESULTS_PATH.read_text())


@app.post("/api/eval/run")
def eval_run(offline: bool = False):
    """Runs the gold set through the same workflow classes the app uses. Synchronous; ~1 s offline,
    ~1 min with live extraction."""
    if not offline and not PUBLIC_LIVE_EVAL:
        raise HTTPException(403, "Live evaluation is switched off on the public demo (it makes 17 model "
                                 "calls). Run it locally with python -m eval.run_eval; the latest live "
                                 "result is recorded in the README.")
    from eval.run_eval import run_all
    import os
    prev = os.environ.get("PLUGPOINT_MOCK_LLM")
    try:
        return run_all(offline=offline)
    finally:  # do not leave the app in offline mode because the eval asked for it
        if prev is None:
            os.environ.pop("PLUGPOINT_MOCK_LLM", None)
        else:
            os.environ["PLUGPOINT_MOCK_LLM"] = prev


@app.get("/api/meta")
def meta(store: Store = Depends(get_store)):
    return {
        "today": store.today.isoformat(),
        "llm": "claude" if llm_available() else "offline fixtures",
        "live_eval": llm_available() and PUBLIC_LIVE_EVAL,
        "samples_live": SAMPLES_LIVE,
        "max_note_chars": MAX_NOTE_CHARS,
        "patients": list(PATIENTS.values()),
        "clinicians": CLINICIANS,
        "samples": [{"id": k, **v} for k, v in SAMPLE_NOTES.items()],
    }


@app.get("/api/state")
def state(store: Store = Depends(get_store)):
    return store.snapshot()


@app.post("/api/seed")
def seed(store: Store = Depends(get_store)):
    """Populate a synthetic clinic (6 backdated loops walked forward day by day) so the worklist has
    something to rank. Adds to whatever is already there; Reset demo clears it."""
    from .seed import seed_clinic
    n = seed_clinic(store)
    return {"seeded": n, "state": store.snapshot()}


@app.post("/api/reset")
def reset(store: Store = Depends(get_store)):
    store.reset()
    return store.snapshot()


@app.post("/api/plan")
def plan(req: PlanRequest, request: Request, store: Store = Depends(get_store)):
    if req.patient_id not in PATIENTS:
        raise HTTPException(404, "Unknown patient")
    if len(req.note) > MAX_NOTE_CHARS:
        raise HTTPException(400, f"Notes are limited to {MAX_NOTE_CHARS:,} characters in the demo.")
    sample = SAMPLE_NOTES.get(req.sample_id or "")
    unedited_sample = sample is not None and req.sample_id in MOCK_PLANS and req.note.strip() == sample["note"].strip()
    use_saved = unedited_sample and not SAMPLES_LIVE
    if not use_saved and llm_available():
        _take_live_quota(_client_ip(request))  # raises 429 before any model call
    try:
        if use_saved:
            # Built-in samples replay their saved extraction: instant, free and identical for every visitor.
            action_plan, source = MOCK_PLANS[req.sample_id].model_copy(deep=True), "mock"
        else:
            action_plan, source = extract_action_plan(req.note, req.sample_id)
    except ExtractionUnavailable as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # API/network errors surface to the UI, never silently proceed
        raise HTTPException(502, f"Extraction failed: {e}")
    loop = store.create_loop(req.patient_id, req.note, req.clinician, action_plan, source)
    return {"loop": loop, "state": store.snapshot()}


@app.post("/api/approve")
def approve(req: ApproveRequest, store: Store = Depends(get_store)):
    try:
        loop = store.approve(req.loop_id, req.approved_investigations, req.approve_follow_up, req.interval_weeks,
                             edits={k: v.model_dump() for k, v in req.edits.items()},
                             added=[a.model_dump() for a in req.added])
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"loop": loop, "state": store.snapshot()}


class Event(BaseModel):
    loop_id: str
    item_id: Optional[str] = None
    notification_id: Optional[str] = None
    actor: str = "Clinician"
    results_expected: Optional[date] = None


@app.post("/api/simulate/result")
def simulate_result(ev: Event, store: Store = Depends(get_store)):
    try:
        store.receive_result(ev.loop_id, ev.item_id)
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop/item")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return store.snapshot()


@app.post("/api/simulate/hold")
def simulate_hold(ev: Event, store: Store = Depends(get_store)):
    try:
        store.hold_investigation(ev.loop_id, ev.item_id)
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop/item")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return store.snapshot()


@app.post("/api/simulate/advance")
def simulate_advance(days: int = 7, store: Store = Depends(get_store)):
    store.advance(days)
    return store.snapshot()


@app.post("/api/action/{action}")
def clinician_action(action: str, ev: Event, store: Store = Depends(get_store)):
    try:
        if action == "chase":
            store.chase(ev.loop_id, ev.item_id, ev.actor)
        elif action == "rebook":
            if not ev.results_expected:
                raise HTTPException(400, "results_expected date required")
            store.rebook(ev.loop_id, ev.results_expected, ev.actor)
        elif action == "resolve_hold":
            if not ev.results_expected:
                raise HTTPException(400, "results_expected date required")
            store.resolve_hold(ev.loop_id, ev.item_id, ev.results_expected, ev.actor)
        elif action == "keep":
            store.keep_appointment(ev.loop_id, ev.actor)
        elif action == "acknowledge":
            store.acknowledge(ev.loop_id, ev.notification_id, ev.actor)
        elif action == "close":
            store.close(ev.loop_id, ev.actor)
        else:
            raise HTTPException(404, f"Unknown action {action}")
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop/item/notification")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return store.snapshot()
