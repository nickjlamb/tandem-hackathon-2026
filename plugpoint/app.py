"""PlugPoint API + static demo UI.

Run:  uvicorn plugpoint.app:app --reload --port 8000   then open http://localhost:8000
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .extract import ExtractionUnavailable, extract_action_plan, llm_available
from .fixtures import CLINICIANS, PATIENTS, SAMPLE_NOTES
from .schema import ApproveRequest, PlanRequest
from .tracker import STORE

app = FastAPI(title="PlugPoint", version="0.1.0")
STATIC = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/meta")
def meta():
    return {
        "today": STORE.today.isoformat(),
        "llm": "claude" if llm_available() else "offline fixtures",
        "patients": list(PATIENTS.values()),
        "clinicians": CLINICIANS,
        "samples": [{"id": k, **v} for k, v in SAMPLE_NOTES.items()],
    }


@app.get("/api/state")
def state():
    return STORE.snapshot()


@app.post("/api/reset")
def reset():
    STORE.reset()
    return STORE.snapshot()


@app.post("/api/plan")
def plan(req: PlanRequest):
    if req.patient_id not in PATIENTS:
        raise HTTPException(404, "Unknown patient")
    try:
        action_plan, source = extract_action_plan(req.note, req.sample_id)
    except ExtractionUnavailable as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # API/network errors surface to the UI, never silently proceed
        raise HTTPException(502, f"Extraction failed: {e}")
    loop = STORE.create_loop(req.patient_id, req.note, req.clinician, action_plan, source)
    return {"loop": loop, "state": STORE.snapshot()}


@app.post("/api/approve")
def approve(req: ApproveRequest):
    try:
        loop = STORE.approve(req.loop_id, req.approved_investigations, req.approve_follow_up, req.interval_weeks)
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"loop": loop, "state": STORE.snapshot()}


class Event(BaseModel):
    loop_id: str
    item_id: Optional[str] = None
    notification_id: Optional[str] = None
    actor: str = "Clinician"
    results_expected: Optional[date] = None


@app.post("/api/simulate/result")
def simulate_result(ev: Event):
    try:
        STORE.receive_result(ev.loop_id, ev.item_id)
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop/item")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return STORE.snapshot()


@app.post("/api/simulate/advance")
def simulate_advance(days: int = 7):
    STORE.advance(days)
    return STORE.snapshot()


@app.post("/api/action/{action}")
def clinician_action(action: str, ev: Event):
    try:
        if action == "chase":
            STORE.chase(ev.loop_id, ev.item_id, ev.actor)
        elif action == "rebook":
            if not ev.results_expected:
                raise HTTPException(400, "results_expected date required")
            STORE.rebook(ev.loop_id, ev.results_expected, ev.actor)
        elif action == "keep":
            STORE.keep_appointment(ev.loop_id, ev.actor)
        elif action == "acknowledge":
            STORE.acknowledge(ev.loop_id, ev.notification_id, ev.actor)
        elif action == "close":
            STORE.close(ev.loop_id, ev.actor)
        else:
            raise HTTPException(404, f"Unknown action {action}")
    except (KeyError, StopIteration):
        raise HTTPException(404, "Unknown loop/item/notification")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return STORE.snapshot()
