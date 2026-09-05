"""External systems behind clearly named interfaces.

Everything in this file is a MOCK. Each class documents what the production
integration would be. The workflow only ever talks to these interfaces, so
swapping in a real EPR / order comms / scheduling / messaging system does not
touch the workflow logic."""

from __future__ import annotations

import itertools
from datetime import date

from .audit import AuditLog
from .fixtures import CONSULTANT_ROSTER, MOCK_RESULTS, PATIENTS
from .rules import next_weekday

_ids = itertools.count(1000)


class MockEPR:
    """Production: FHIR Patient / DocumentReference on the trust EPR."""

    def get_patient(self, patient_id: str) -> dict:
        return PATIENTS[patient_id]

    def write_plan_summary(self, audit: AuditLog, today: date, loop_id: str, patient_id: str, summary: str) -> str:
        doc_id = f"DOC-{next(_ids)}"
        audit.record(today, "API", f"[MOCK EPR] Action plan written to record as {doc_id}", loop_id)
        return doc_id


class MockOrderComms:
    """Production: order communications (e.g. ICE / Sunrise) via HL7/FHIR ServiceRequest."""

    def order(self, audit: AuditLog, today: date, loop_id: str, patient_id: str, name: str,
              reason: str, urgency: str) -> str:
        order_id = f"ORD-{next(_ids)}"
        audit.record(today, "API", f"[MOCK ORDERS] {name} ordered ({urgency}) - {order_id}", loop_id,
                     {"reason": reason})
        return order_id

    def chase(self, audit: AuditLog, today: date, loop_id: str, order_id: str, name: str) -> None:
        audit.record(today, "API", f"[MOCK ORDERS] Chase sent to reporting department for {name} ({order_id})",
                     loop_id)

    def fetch_result(self, name: str, category: str) -> str:
        return MOCK_RESULTS.get(category, MOCK_RESULTS["other"])


class MockScheduling:
    """Production: PAS / outpatient booking API (e.g. FHIR Appointment)."""

    def book(self, audit: AuditLog, today: date, loop_id: str, patient_id: str, earliest: date,
             reviewer_role: str, author_name: str) -> dict:
        slot = next_weekday(earliest)
        clinic = PATIENTS[patient_id]["clinic"]
        reviewer = CONSULTANT_ROSTER.get(clinic, "Consultant on call") if reviewer_role == "consultant" else author_name
        appt = {"id": f"APT-{next(_ids)}", "date": slot.isoformat(), "reviewer_role": reviewer_role,
                "reviewer_name": reviewer, "clinic": clinic, "status": "booked"}
        audit.record(today, "API", f"[MOCK PAS] Follow-up booked {slot.isoformat()} with {reviewer} ({clinic}) - {appt['id']}",
                     loop_id)
        return appt

    def rebook(self, audit: AuditLog, today: date, loop_id: str, appt: dict, new_date: date) -> dict:
        slot = next_weekday(new_date)
        old = appt["date"]
        appt = {**appt, "id": f"APT-{next(_ids)}", "date": slot.isoformat(), "status": "booked"}
        audit.record(today, "API", f"[MOCK PAS] Follow-up moved {old} -> {slot.isoformat()} with {appt['reviewer_name']} - {appt['id']}",
                     loop_id)
        return appt


class MockPatientMessaging:
    """Production: SMS / patient portal messaging (e.g. NHS App, Accurx-style)."""

    def send(self, audit: AuditLog, today: date, loop_id: str, patient_id: str, text: str) -> str:
        msg_id = f"SMS-{next(_ids)}"
        phone = PATIENTS[patient_id]["phone"]
        audit.record(today, "API", f"[MOCK SMS] Sent to {phone}: \"{text}\" - {msg_id}", loop_id)
        return msg_id


class Integrations:
    def __init__(self) -> None:
        self.epr = MockEPR()
        self.orders = MockOrderComms()
        self.scheduling = MockScheduling()
        self.messaging = MockPatientMessaging()
