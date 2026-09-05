"""Gold evaluation: runs every case in eval/cases.json through the SAME workflow the app
uses (extract -> rules -> gate -> approve -> mocked actions -> tracker) and compares the
observed behaviour with what the team specified.

    python -m eval.run_eval              # live Claude extraction if ANTHROPIC_API_KEY is set, else offline
    python -m eval.run_eval --offline    # force offline fixtures (tests rules/gate/tracker only)
    python -m eval.run_eval --json       # machine-readable output (used by the /eval page)

Failures are reported as they are. The production workflow is never adjusted here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from plugpoint import extract as extract_mod
from plugpoint.extract import extract_action_plan, llm_available
from plugpoint.schema import ActionPlan, Clinician
from plugpoint.tracker import Store

CASES_PATH = Path(__file__).parent / "cases.json"
RESULTS_PATH = Path(__file__).parent / "results.json"


def _open_alert_kinds(store: Store) -> list[str]:
    return sorted({n["kind"] for n in store.notifications if not n["resolved"]})


def _item_by_category(loop: dict, category: str) -> dict:
    return next(i for i in loop["items"] if i["category"] == category and i["status"] == "result_awaited")


def run_case(case: dict) -> dict:
    """Returns {id, passed, checks:[{name, expected, actual, ok}], notes}."""
    inp, exp = case["input"], case["expected"]
    checks: list[dict] = []
    notes: list[str] = []

    def check(name, expected, actual):
        checks.append({"name": name, "expected": expected, "actual": actual, "ok": expected == actual})

    store = Store()
    clinician = Clinician(**inp["clinician"])
    fallback = ActionPlan.model_validate(inp["mock_plan"]) if inp.get("mock_plan") else None
    try:
        plan, source = extract_action_plan(inp["note"], None, fallback_plan=fallback)
    except Exception as e:  # extraction failure is a failed case, not a crash
        return {"id": case["id"], "type": case["type"], "title": case["title"], "passed": False, "source": "error",
                "checks": [{"name": "extraction", "expected": "plan", "actual": f"error: {e}", "ok": False}], "notes": []}

    loop = store.create_loop(inp["patient_id"], inp["note"], clinician, plan, source)

    # ---- plan stage: what the gate decided
    check("requires_human_review", exp["requires_human_review"], loop["gate"]["requires_human_review"])
    check("escalation_reasons", sorted(exp.get("reasons", [])), sorted(loop["gate"]["reasons"]))
    check("investigations_extracted", exp["investigations"], len(loop["items"]))
    if "follow_up_weeks" in exp and not exp["requires_human_review"]:
        check("follow_up_weeks", exp["follow_up_weeks"], loop["follow_up_weeks"])
    if "reviewer_role" in exp:
        check("reviewer_role", exp["reviewer_role"], loop["reviewer_role"])
    if "urgency" in exp:
        check("urgency", sorted(exp["urgency"]), sorted(i["urgency"] for i in loop["items"]))
    for code in exp.get("flags_include", []):
        check(f"flag:{code}", True, any(f["code"] == code for f in loop["gate"]["flags"]))

    # ---- approval + downstream actions (only if the gate let it through, exactly as the app does)
    if not loop["gate"]["requires_human_review"]:
        store.approve(loop["id"], [i["id"] for i in loop["items"]], True, None)
    audit = store.audit.for_loop(loop["id"])
    orders = sum(1 for e in audit if e["actor"] == "API" and "[MOCK ORDERS]" in e["message"] and "ordered" in e["message"])
    booked = loop["appointment"] is not None
    messaged = any(e["actor"] == "API" and "[MOCK SMS]" in e["message"] for e in audit)
    acts = exp.get("actions", {})
    if "orders" in acts:
        check("orders_placed", acts["orders"], orders)
    if "appointment_booked" in acts:
        check("appointment_booked", acts["appointment_booked"], booked)
    if "patient_messaged" in acts:
        check("patient_messaged", acts["patient_messaged"], messaged)
    if loop["gate"]["requires_human_review"]:
        # the critical property: an escalated plan must never have triggered downstream work
        check("no_actions_on_escalation", True, orders == 0 and not booked and not messaged)

    # ---- tracker stage: scripted events, same Store methods the API calls
    for step in case.get("steps", []):
        try:
            if "advance_days" in step:
                store.advance(step["advance_days"])
            elif "result" in step:
                store.receive_result(loop["id"], _item_by_category(loop, step["result"])["id"])
            elif "hold" in step:
                store.hold_investigation(loop["id"], _item_by_category(loop, step["hold"])["id"])
            elif "resolve_hold" in step:
                item = next(i for i in loop["items"] if i["category"] == step["resolve_hold"] and i["on_hold"])
                store.resolve_hold(loop["id"], item["id"], store.today + timedelta(days=step["expected_in_days"]), "Eval clinician")
            elif "rebook" in step:
                store.rebook(loop["id"], store.today + timedelta(days=step["rebook"]), "Eval clinician")
            elif "close" in step:
                store.close(loop["id"], "Eval clinician")
            elif "expect_alerts" in step:
                check(f"alerts@{store.today.isoformat()}", sorted(step["expect_alerts"]), _open_alert_kinds(store))
        except Exception as e:
            checks.append({"name": f"step {step}", "expected": "ok", "actual": f"error: {e}", "ok": False})
    if "alerts" in exp:
        check("open_alerts_at_end", sorted(exp["alerts"]), _open_alert_kinds(store))
    if "loop_status" in exp:
        check("loop_status", exp["loop_status"], loop["status"])
    if "item_statuses" in exp:
        check("item_statuses", sorted(exp["item_statuses"]), sorted(i["status"] for i in loop["items"]))

    return {"id": case["id"], "type": case["type"], "title": case["title"], "source": source,
            "passed": all(c["ok"] for c in checks), "checks": checks, "notes": notes,
            "expected_escalation": exp["requires_human_review"]}


def run_all(offline: bool = False) -> dict:
    if offline:
        os.environ["PLUGPOINT_MOCK_LLM"] = "1"
    cases = json.loads(CASES_PATH.read_text())["cases"]
    t0 = time.time()
    results = [run_case(c) for c in cases]
    passed = [r for r in results if r["passed"]]
    esc = [r for r in results if r["expected_escalation"]]
    esc_passed = [r for r in esc if r["passed"]]
    # false negatives: escalation expected but the gate let it through
    missed = [r for r in esc if any(c["name"] == "requires_human_review" and not c["ok"] for c in r["checks"])]
    summary = {
        "mode": "claude" if llm_available() else "offline fixtures",
        "model": extract_mod.MODEL if llm_available() else None,
        "run_at": date.today().isoformat(),
        "seconds": round(time.time() - t0, 1),
        "total": len(results), "passed": len(passed), "failed": len(results) - len(passed),
        "pass_pct": round(100 * len(passed) / len(results)) if results else 0,
        "escalation_total": len(esc), "escalation_passed": len(esc_passed), "escalation_failed": len(esc) - len(esc_passed),
        "escalations_missed": len(missed),
        "by_type": {t: {"total": sum(1 for r in results if r["type"] == t), "passed": sum(1 for r in results if r["type"] == t and r["passed"])}
                    for t in ["routine", "edge", "ambiguous", "escalation"]},
    }
    out = {"summary": summary, "results": results}
    RESULTS_PATH.write_text(json.dumps(out, indent=2))
    return out


def print_report(out: dict) -> None:
    s = out["summary"]
    print(f"\nPlugPoint gold evaluation  ·  extraction: {s['mode']}{(' (' + s['model'] + ')') if s['model'] else ''}  ·  {s['seconds']}s\n")
    for r in out["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  {mark}  {r['id']}  [{r['type']:10}]  {r['title']}")
        for c in r["checks"]:
            if not c["ok"]:
                print(f"         x {c['name']}: expected {c['expected']!r}, got {c['actual']!r}")
    print(f"\n  Total {s['total']}  ·  passed {s['passed']}  ·  failed {s['failed']}  ·  {s['pass_pct']}%")
    print(f"  Escalation cases: {s['escalation_passed']}/{s['escalation_total']} passed  ·  escalations missed (auto-actioned): {s['escalations_missed']}")
    print("  By type: " + "  ".join(f"{t} {v['passed']}/{v['total']}" for t, v in s["by_type"].items()))
    print(f"\n  Results written to {RESULTS_PATH}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="force offline fixture extraction")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args()
    out = run_all(offline=args.offline)
    if args.json:
        json.dump(out, sys.stdout, indent=2)
    else:
        print_report(out)
    sys.exit(0 if out["summary"]["failed"] == 0 else 1)
