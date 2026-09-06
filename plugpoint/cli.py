"""Run the happy path in a terminal with no server or browser.

    python -m plugpoint.cli            # sample A, offline fixtures unless ANTHROPIC_API_KEY is set
    python -m plugpoint.cli B_conflict
"""

from __future__ import annotations

import sys

from .extract import extract_action_plan
from .fixtures import SAMPLE_NOTES
from .schema import Clinician
from .tracker import Store


def main(sample_id: str = "A_routine") -> None:
    sample = SAMPLE_NOTES[sample_id]
    store = Store()
    clinician = Clinician(**sample["clinician"])
    plan, source = extract_action_plan(sample["note"], sample_id)
    loop = store.create_loop(sample["patient_id"], sample["note"], clinician, plan, source)

    print(f"\n== {sample['label']}  (extraction: {source})")
    print(f"Loop {loop['id']} status: {loop['status']}")
    for f in loop["gate"]["flags"]:
        print(f"  [{f['severity']:5}] {f['message']}")

    if loop["status"] == "needs_review":
        print("\nClinician decision required:", ", ".join(loop["gate"]["reasons"]))
    else:
        store.approve(loop["id"], [i["id"] for i in loop["items"]], True, None)
        items = loop["items"]
        # simulate: bloods back, then time passes, MRI overdue
        store.advance(4)
        blood = next(i for i in items if i["category"] == "bloods")
        store.receive_result(loop["id"], blood["id"])
        store.advance(14)
        print(f"\nStatus after 18 days: loop={loop['status']} items="
              + ", ".join(f"{i['name']}={i['status']}{' OVERDUE' if i['overdue'] else ''}" for i in items))
        print("Open alerts:", [n["message"] for n in store.notifications if not n["resolved"]])

    print("\n-- audit trail --")
    for e in store.audit.entries:
        print(f"{e['date']}  {e['actor']:6}  {e['message']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "A_routine")
