"""The workflow engine and its state. This is where "lost to follow-up" is
prevented: every approved item is tracked against an expected date, and the
checks in `run_checks` raise a notification for the clinician whenever the
plan is at risk. All state is in memory; the clock is simulated so a demo can
move weeks in one click.

Loop status:      awaiting_approval -> open -> closed   (needs_review when blocked)
Item status:      proposed -> ordered -> result_awaited -> result_received -> reviewed
"""

from __future__ import annotations

import itertools
from datetime import date, timedelta

from .audit import AuditLog
from .integrations import Integrations
from .rules import (APPOINTMENT_LEAD_DAYS, CHECK_NAMES, RESULT_BUFFER_DAYS, check_plan, earliest_follow_up_date,
                    expected_result_date, next_weekday, resolve_reviewer)
from .schema import ActionPlan, Clinician, GateResult

START_DATE = date(2026, 9, 5)


class Store:
    def __init__(self) -> None:
        self.today: date = START_DATE
        self.loops: dict[str, dict] = {}
        self.notifications: list[dict] = []
        self.audit = AuditLog()
        self.integrations = Integrations()
        self._loop_ids = itertools.count(1)
        self._item_ids = itertools.count(1)
        self._note_ids = itertools.count(1)

    def reset(self) -> None:
        self.__init__()

    # ------------------------------------------------------------ plan stage
    def create_loop(self, patient_id: str, note: str, clinician: Clinician, plan: ActionPlan,
                    source: str) -> dict:
        loop_id = f"L{next(self._loop_ids):03d}"
        self.audit.record(self.today, "AI",
                          f"Action plan extracted from clinic note ({'Claude' if source == 'llm' else 'offline fixture'}): "
                          f"{len(plan.investigations)} investigation(s), "
                          f"follow-up {'requested' if plan.follow_up else 'not mentioned'}",
                          loop_id, {"source": source})
        gate = check_plan(plan, clinician, self.today)
        self._audit_gate(loop_id, gate)

        items = []
        for inv in plan.investigations:
            items.append({
                "id": f"I{next(self._item_ids):03d}", "name": inv.name, "category": inv.category,
                "reason": inv.reason, "urgency": inv.urgency, "evidence": inv.evidence,
                "status": "proposed", "order_id": None, "ordered_on": None, "expected_by": None,
                "result": None, "result_on": None, "overdue": False,
            })
        loop = {
            "id": loop_id, "patient_id": patient_id, "patient": self.integrations.epr.get_patient(patient_id),
            "clinician": clinician.model_dump(), "note": note, "created": self.today.isoformat(),
            "plan": plan.model_dump(), "gate": gate.model_dump(),
            "status": "needs_review" if gate.requires_human_review else "awaiting_approval",
            "items": items, "appointment": None,
            "follow_up_weeks": plan.follow_up.interval_weeks if plan.follow_up else None,
            "reviewer_role": resolve_reviewer(plan, clinician),
            "approved_by": None, "approved_on": None, "closed_on": None,
        }
        self.loops[loop_id] = loop
        return loop

    def _audit_gate(self, loop_id: str, gate: GateResult) -> None:
        passed = [f for f in gate.flags if f.severity != "block"]
        blocked = [f for f in gate.flags if f.severity == "block"]
        if blocked:
            self.audit.record(self.today, "RULE",
                              f"Plan checks: {len(CHECK_NAMES) - len(blocked)}/{len(CHECK_NAMES)} passed, "
                              f"{len(blocked)} blocking -> clinician decision required: "
                              + "; ".join(f.message for f in blocked), loop_id)
        else:
            self.audit.record(self.today, "RULE", f"Plan checks PASS ({len(CHECK_NAMES)}/{len(CHECK_NAMES)}: "
                              + ", ".join(CHECK_NAMES) + ")"
                              + ("; notes: " + "; ".join(f.message for f in passed) if passed else ""), loop_id)

    # --------------------------------------------------------- approval stage
    def approve(self, loop_id: str, approved_item_ids: list[str], approve_follow_up: bool,
                interval_weeks: int | None, approver: Clinician | None = None,
                edits: dict | None = None, added: list | None = None) -> dict:
        loop = self.loops[loop_id]
        if loop["status"] not in ("awaiting_approval", "needs_review"):
            raise ValueError(f"Loop {loop_id} is {loop['status']}, cannot approve")
        approver = approver or Clinician(**loop["clinician"])
        approved_item_ids = list(approved_item_ids)

        # ---- clinician amendments to the extracted plan (recorded as HUMAN actions) ----
        for item_id, edit in (edits or {}).items():
            item = next((i for i in loop["items"] if i["id"] == item_id), None)
            if not item:
                continue
            changes = []
            new_name = (edit.get("name") or "").strip()
            new_reason = (edit.get("reason") or "").strip()
            if new_name and new_name != item["name"]:
                changes.append(f"investigation '{item['name']}' -> '{new_name}'")
                item["name"] = new_name
            if new_reason and new_reason != (item["reason"] or ""):
                changes.append(("added indication" if not item["reason"] else "amended indication") + f" for {item['name']}: '{new_reason}'")
                item["reason"] = new_reason
            if changes:
                item["edited_by_clinician"] = True
                self.audit.record(self.today, "HUMAN", f"{approver.name} amended plan: " + "; ".join(changes), loop_id)
        for new in (added or []):
            item = {
                "id": f"I{next(self._item_ids):03d}", "name": new["name"].strip(), "category": new.get("category", "other"),
                "reason": new["reason"].strip(), "urgency": new.get("urgency", "routine"),
                "evidence": "added by clinician at approval", "edited_by_clinician": True,
                "status": "proposed", "order_id": None, "ordered_on": None, "expected_by": None,
                "result": None, "result_on": None, "overdue": False,
            }
            loop["items"].append(item)
            approved_item_ids.append(item["id"])
            self.audit.record(self.today, "HUMAN", f"{approver.name} added investigation: {item['name']} ({item['category']}) - '{item['reason']}'", loop_id)

        # Clinician resolves any blocking issue by explicit choice
        if loop["gate"]["requires_human_review"]:
            if "conflicting_follow_up_interval" in loop["gate"]["reasons"] or \
               "follow_up_before_results" in loop["gate"]["reasons"] or \
               "missing_follow_up_interval" in loop["gate"]["reasons"]:
                if interval_weeks is None and approve_follow_up:
                    raise ValueError("Plan needs a follow-up interval chosen by the clinician")
            unresolved = [i for i in loop["items"] if i["id"] in approved_item_ids and not i["reason"]]
            if unresolved:
                raise ValueError("Investigations without a clinical indication cannot be approved: "
                                 + ", ".join(i["name"] for i in unresolved))
            self.audit.record(self.today, "HUMAN",
                              f"{approver.name} resolved review: " + ", ".join(loop["gate"]["reasons"]), loop_id)

        if interval_weeks is not None:
            # Clinician-chosen interval must still land after results are expected (same rule as R4)
            earliest = earliest_follow_up_date(ActionPlan.model_validate(loop["plan"]), self.today)
            proposed = next_weekday(self.today + timedelta(weeks=interval_weeks))
            if approve_follow_up and proposed < earliest:
                raise ValueError(f"Follow-up in {interval_weeks} wk ({proposed.isoformat()}) is still before results are "
                                 f"expected ({earliest.isoformat()}). Choose a later interval.")
            loop["follow_up_weeks"] = interval_weeks

        approved = [i for i in loop["items"] if i["id"] in approved_item_ids]
        declined = [i for i in loop["items"] if i["id"] not in approved_item_ids]
        self.audit.record(self.today, "HUMAN",
                          f"{approver.name} ({approver.role}) approved {len(approved)} investigation(s)"
                          + (f", declined {len(declined)}" if declined else "")
                          + (f"; follow-up in {loop['follow_up_weeks']} wk with {loop['reviewer_role']}"
                             if approve_follow_up and loop["follow_up_weeks"] else "; no follow-up booked"),
                          loop_id)
        loop["approved_by"] = approver.model_dump()
        loop["approved_on"] = self.today.isoformat()

        # ---- downstream actions (all via mock integrations) ----
        ig = self.integrations
        for item in declined:
            item["status"] = "declined"
        for item in approved:
            item["order_id"] = ig.orders.order(self.audit, self.today, loop_id, loop["patient_id"],
                                               item["name"], item["reason"] or "", item["urgency"])
            item["status"] = "result_awaited"
            item["ordered_on"] = self.today.isoformat()
            item["expected_by"] = expected_result_date(item["category"], self.today).isoformat()
            self.audit.record(self.today, "RULE",
                              f"Expected result date for {item['name']} set to {item['expected_by']} "
                              f"(turnaround rule: {item['category']})", loop_id)

        if approve_follow_up and loop["follow_up_weeks"]:
            wanted = next_weekday(self.today + timedelta(weeks=loop["follow_up_weeks"]))
            loop["appointment"] = ig.scheduling.book(self.audit, self.today, loop_id, loop["patient_id"], wanted,
                                                     loop["reviewer_role"], approver.name)
            ig.messaging.send(self.audit, self.today, loop_id, loop["patient_id"],
                              f"Your {loop['appointment']['clinic']} follow-up is booked for {loop['appointment']['date']}. "
                              f"Tests ordered today: " + ", ".join(i["name"] for i in approved) + ".")
        ig.epr.write_plan_summary(self.audit, self.today, loop_id, loop["patient_id"], "plan summary")

        loop["status"] = "open"
        self.audit.record(self.today, "SYSTEM", "Loop opened - tracking until results reviewed", loop_id)
        self.run_checks()
        return loop

    # ------------------------------------------------------- events & clock
    def receive_result(self, loop_id: str, item_id: str) -> dict:
        loop = self.loops[loop_id]
        item = next(i for i in loop["items"] if i["id"] == item_id)
        if item["status"] != "result_awaited":
            raise ValueError(f"{item['name']} is {item['status']}, no result expected")
        item["result"] = self.integrations.orders.fetch_result(item["name"], item["category"])
        item["result_on"] = self.today.isoformat()
        item["status"] = "result_received"
        was_overdue = item["overdue"]
        item["overdue"] = False
        self.audit.record(self.today, "API", f"[MOCK RESULTS] Result received for {item['name']} ({item['order_id']})", loop_id)
        self.audit.record(self.today, "RULE", f"Result matched to {item['name']} ({item['order_id']}) -> result_received"
                          + (" - overdue alert cleared" if was_overdue else ""), loop_id)
        self._resolve_notifications(loop_id, item_id=item_id)
        if all(i["status"] in ("result_received", "declined", "reviewed") for i in loop["items"]):
            self.audit.record(self.today, "SYSTEM", "All results in - pre-clinic pack ready for reviewer", loop_id)
        self.run_checks()
        return loop

    def advance(self, days: int) -> None:
        self.today = self.today + timedelta(days=days)
        self.audit.record(self.today, "SYSTEM", f"Clock advanced {days} day(s) -> {self.today.isoformat()}")
        self.run_checks()

    def run_checks(self) -> None:
        """Deterministic safety net, run after every event and clock tick."""
        for loop in self.loops.values():
            if loop["status"] != "open":
                continue
            outstanding = [i for i in loop["items"] if i["status"] == "result_awaited"]
            # C1 - result overdue
            for item in outstanding:
                if self.today > date.fromisoformat(item["expected_by"]) and not item["overdue"]:
                    item["overdue"] = True
                    self._notify(loop, "result_overdue", item_id=item["id"],
                                 message=f"{item['name']} result overdue (expected {item['expected_by']})",
                                 actions=["chase", "acknowledge"])
            # C2 - appointment at risk: results still outstanding as the appointment approaches
            appt = loop["appointment"]
            if appt and appt["status"] == "at_risk" and not outstanding:
                appt["status"] = "booked"
                self._resolve_notifications(loop["id"], kind="appointment_at_risk")
                self.audit.record(self.today, "RULE", f"All results in before {appt['date']} - appointment no longer at risk", loop["id"])
            if appt and appt["status"] == "booked" and outstanding:
                appt_date = date.fromisoformat(appt["date"])
                days_left = (appt_date - self.today).days
                latest_expected = max(date.fromisoformat(i["expected_by"]) for i in outstanding)
                any_overdue = any(i["overdue"] for i in outstanding)
                at_risk = (
                    (any_overdue and days_left <= 2 * APPOINTMENT_LEAD_DAYS)             # overdue result, appointment close
                    or latest_expected + timedelta(days=RESULT_BUFFER_DAYS) > appt_date   # results not expected in time
                )
                if at_risk and not self._has_open(loop["id"], "appointment_at_risk"):
                    appt["status"] = "at_risk"
                    names = ", ".join(i["name"] for i in outstanding)
                    self._notify(loop, "appointment_at_risk",
                                 message=f"Follow-up on {appt['date']} but still awaiting: {names}",
                                 actions=["rebook", "keep"])
            # C3 - appointment passed while loop still open
            if appt and self.today > date.fromisoformat(appt["date"]) and not self._has_open(loop["id"], "appointment_passed"):
                self._notify(loop, "appointment_passed",
                             message=f"Follow-up date {appt['date']} has passed - confirm patient was seen and results reviewed",
                             actions=["close"])

    # ------------------------------------------------------ clinician actions
    def chase(self, loop_id: str, item_id: str, approver_name: str) -> dict:
        loop = self.loops[loop_id]
        item = next(i for i in loop["items"] if i["id"] == item_id)
        self.audit.record(self.today, "HUMAN", f"{approver_name} requested chase for {item['name']}", loop_id)
        self.integrations.orders.chase(self.audit, self.today, loop_id, item["order_id"], item["name"])
        item["expected_by"] = (self.today + timedelta(days=7)).isoformat()
        item["overdue"] = False
        self.audit.record(self.today, "RULE", f"Expected date for {item['name']} reset to {item['expected_by']} after chase", loop_id)
        self._resolve_notifications(loop_id, item_id=item_id)
        self.run_checks()
        return loop

    def rebook(self, loop_id: str, results_expected: date, approver_name: str) -> dict:
        """Clinician has clarified when results will be available; move the appointment after them."""
        loop = self.loops[loop_id]
        new_date = next_weekday(results_expected + timedelta(days=RESULT_BUFFER_DAYS))
        self.audit.record(self.today, "HUMAN",
                          f"{approver_name}: results now expected {results_expected.isoformat()} - rebook follow-up", loop_id)
        for item in loop["items"]:
            if item["status"] == "result_awaited":
                item["expected_by"] = results_expected.isoformat()
                item["overdue"] = False
        loop["appointment"] = self.integrations.scheduling.rebook(self.audit, self.today, loop_id, loop["appointment"], new_date)
        self.integrations.messaging.send(self.audit, self.today, loop_id, loop["patient_id"],
                                         f"Your follow-up has moved to {loop['appointment']['date']} so your results are back in time.")
        self._resolve_notifications(loop_id, kind="appointment_at_risk")
        self._resolve_notifications(loop_id, kind="result_overdue")
        self.run_checks()
        return loop

    def keep_appointment(self, loop_id: str, approver_name: str) -> dict:
        loop = self.loops[loop_id]
        loop["appointment"]["status"] = "booked"
        self.audit.record(self.today, "HUMAN", f"{approver_name} chose to keep the appointment on {loop['appointment']['date']}", loop_id)
        self._resolve_notifications(loop_id, kind="appointment_at_risk")
        return loop

    def acknowledge(self, loop_id: str, notification_id: str, approver_name: str) -> dict:
        n = next(n for n in self.notifications if n["id"] == notification_id)
        n["resolved"] = True
        self.audit.record(self.today, "HUMAN", f"{approver_name} acknowledged: {n['message']}", loop_id)
        return self.loops[loop_id]

    def close(self, loop_id: str, approver_name: str) -> dict:
        loop = self.loops[loop_id]
        for item in loop["items"]:
            if item["status"] == "result_received":
                item["status"] = "reviewed"
        loop["status"] = "closed"
        loop["closed_on"] = self.today.isoformat()
        self.audit.record(self.today, "HUMAN", f"{approver_name} confirmed results reviewed with patient - loop closed", loop_id)
        self._resolve_notifications(loop_id)
        return loop

    # ------------------------------------------------------------ internals
    def _notify(self, loop: dict, kind: str, message: str, actions: list[str], item_id: str | None = None) -> None:
        n = {"id": f"N{next(self._note_ids):03d}", "loop_id": loop["id"], "patient_name": loop["patient"]["name"],
             "kind": kind, "item_id": item_id, "message": message, "actions": actions,
             "created": self.today.isoformat(), "resolved": False,
             "owner": loop["appointment"]["reviewer_name"] if loop.get("appointment") else loop["clinician"]["name"]}
        self.notifications.append(n)
        self.audit.record(self.today, "SYSTEM", f"ALERT to {n['owner']}: {message}", loop["id"])

    def _has_open(self, loop_id: str, kind: str) -> bool:
        return any(n["loop_id"] == loop_id and n["kind"] == kind and not n["resolved"] for n in self.notifications)

    def _resolve_notifications(self, loop_id: str, kind: str | None = None, item_id: str | None = None) -> None:
        for n in self.notifications:
            if n["loop_id"] != loop_id or n["resolved"]:
                continue
            if kind and n["kind"] != kind:
                continue
            if item_id and n["item_id"] != item_id:
                continue
            n["resolved"] = True

    # ------------------------------------------------------------- snapshot
    def loop_counts(self, loop_id: str) -> dict:
        """How much work the software did vs how many decisions the clinician made."""
        entries = self.audit.for_loop(loop_id)
        return {
            "api_actions": sum(1 for e in entries if e["actor"] == "API"),
            "rule_checks": sum(1 for e in entries if e["actor"] == "RULE"),
            "human_decisions": sum(1 for e in entries if e["actor"] == "HUMAN"),
            "alerts": sum(1 for e in entries if e["actor"] == "SYSTEM" and e["message"].startswith("ALERT")),
        }

    def snapshot(self) -> dict:
        for loop in self.loops.values():
            loop["counts"] = self.loop_counts(loop["id"])
        return {
            "today": self.today.isoformat(),
            "loops": list(self.loops.values()),
            "notifications": [n for n in self.notifications if not n["resolved"]],
            "audit": self.audit.entries[-200:],
        }


STORE = Store()
