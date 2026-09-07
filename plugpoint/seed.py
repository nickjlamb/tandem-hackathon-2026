"""Seed a synthetic clinic so the worklist has something to rank.

Six loops are created at different points in the past and the clock is walked forward one
day at a time, so every alert, overdue flag and escalation arises from the same rules the
app applies live - nothing here writes state directly. All patients are invented."""

from __future__ import annotations

from datetime import date, timedelta

from .fixtures import PATIENTS
from .schema import ActionPlan, Clinician, FollowUp, Investigation
from .tracker import Store

REG = Clinician(name="Dr Sam Patel", role="registrar")
CON_R = Clinician(name="Dr Elena Fischer", role="consultant")
CON_U = Clinician(name="Mr James Hollis", role="consultant")


def _plan(items: list[tuple[str, str, str]], weeks: int, reviewer: str | None, purpose: str) -> ActionPlan:
    return ActionPlan(
        investigations=[Investigation(name=n, category=c, reason=r, evidence=n) for n, c, r in items],
        follow_up=FollowUp(interval_weeks=weeks, interval_candidates_weeks=[weeks], reviewer_role=reviewer,
                           purpose=purpose, evidence=f"Follow up in {weeks} weeks"),
    )


# (patient, author, plan, days_ago approved, events after approval as (day_offset, kind, category))
SCENARIOS = [
    # Appointment in 2 days, MRI never came back: overdue for weeks, alert aged through both tiers.
    ("P005", REG, _plan([("MRI abdomen with contrast", "imaging", "Characterise 4 cm left renal mass"),
                          ("U&E and eGFR", "bloods", "Renal function before contrast")], 6, "consultant",
                         "Review MRI, consultant opinion"), 40, [(3, "result", "bloods")]),
    # CT put on hold by radiology 7 days ago, nobody resolved it: escalated to the consultant.
    ("P006", REG, _plan([("CT chest with contrast", "imaging", "Persistent RUL opacity on CXR, 40 pack-years")], 8, "consultant",
                         "Discuss CT"), 20, [(13, "hold", "imaging")]),
    # Bloods 6 days overdue - alert is 6 days old, so it has just escalated to the consultant.
    ("P007", REG, _plan([("LFTs and FIB-4", "bloods", "Rising ALT in known NAFLD")], 4, "consultant",
                        "Review liver function"), 10, []),
    # Approved 3 days ago, everything on track.
    ("P008", CON_U, _plan([("MRI prostate", "imaging", "PSA 7.8, DRE unremarkable"),
                           ("Repeat PSA", "bloods", "Confirm PSA trend")], 6, "consultant",
                          "Review MRI and PSA"), 3, []),
    # Appointment passed 5 days ago and the loop was never closed.
    ("P002", CON_R, _plan([("FBC", "bloods", "Baseline for persistent cough")], 4, "consultant",
                          "Review bloods"), 33, [(2, "result", "bloods")]),
    # All results in, appointment in two weeks: the pack is ready.
    ("P003", CON_R, _plan([("Liver biopsy", "biopsy", "Stage fibrosis"), ("LFTs", "bloods", "Monitoring")], 5, "consultant",
                          "Review histology"), 21, [(2, "result", "bloods"), (18, "result", "biopsy")]),
]


def seed_clinic(store: Store) -> int:
    base = store.today
    schedule: list[tuple[date, str, dict]] = []
    for patient_id, author, plan, days_ago, events in SCENARIOS:
        start = base - timedelta(days=days_ago)
        schedule.append((start, "approve", {"patient_id": patient_id, "author": author, "plan": plan}))
        for offset, kind, category in events:
            schedule.append((start + timedelta(days=offset), kind, {"patient_id": patient_id, "category": category}))
    schedule.sort(key=lambda e: e[0])

    loops_by_patient: dict[str, str] = {}
    day = schedule[0][0]
    store.today = day
    store.audit.record(day, "SYSTEM", f"Seeding synthetic clinic: {len(SCENARIOS)} loops from {day.isoformat()} to {base.isoformat()}")
    while day <= base:
        for when, kind, args in schedule:
            if when != day:
                continue
            if kind == "approve":
                loop = store.create_loop(args["patient_id"], f"[seeded synthetic note for {PATIENTS[args['patient_id']]['name']}]",
                                         args["author"], args["plan"], "seed")
                store.approve(loop["id"], [i["id"] for i in loop["items"]], True, None, approver=args["author"])
                loops_by_patient[args["patient_id"]] = loop["id"]
            else:
                loop = store.loops[loops_by_patient[args["patient_id"]]]
                item = next((i for i in loop["items"] if i["category"] == args["category"] and i["status"] == "result_awaited"), None)
                if item:
                    (store.receive_result if kind == "result" else store.hold_investigation)(loop["id"], item["id"])
        store.run_checks()
        day += timedelta(days=1)
        store.today = day
    store.today = base
    store.run_checks()
    return len(SCENARIOS)
