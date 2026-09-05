# Architecture

See the diagram in the [README](../README.md#how-it-works). Every step is labelled by who does it.

## Deterministic / API components (`rules.py`, `tracker.py`, `integrations.py`)
- **Plan checks** (`rules.check_plan`): indication stated per investigation; exactly one follow-up interval in the note; interval present when follow-up requested; appointment date after the latest expected result + buffer; reviewer defaulting (note author unless the note names someone).
- **Turnaround table** (`rules.TURNAROUND_DAYS`): imaging 14 d, bloods 3 d, biopsy 21 d, other 7 d. Demo constants; production reads the department SLA table.
- **State machine** (`tracker.Store`): loop `awaiting_approval → open → closed` (`needs_review` when blocked); item `proposed → result_awaited → result_received → reviewed`, with `overdue` and `on_hold` flags; appointment `booked ↔ at_risk`.
- **Safety-net checks** (`tracker.run_checks`), run after every event and clock tick: result overdue; appointment at risk (an outstanding item is overdue or on hold within 14 days of the appointment, or its expected date + buffer is after the appointment); appointment passed while the loop is open.
- **Integrations**: `MockEPR`, `MockOrderComms`, `MockScheduling`, `MockPatientMessaging`. Each documents the production equivalent (FHIR ServiceRequest / Appointment / DocumentReference, SMS gateway).

## LLM component (`extract.py`)
One call. Forced tool use against the `ActionPlan` JSON schema. The system prompt forbids adding, inferring or recommending anything not in the note, requires verbatim evidence quotes, and asks for every follow-up interval mentioned so the *rules* can detect conflicts. Offline fixtures stand in when there is no API key.

## Human / clinician checkpoints
- **Approval**: nothing leaves the system before it. The plan is editable (amend, add, drop); edits are HUMAN audit entries.
- **Decision on blocked plans**: choose an interval, add an indication, or drop an item. The clinician's choice is re-checked by the same rules.
- **Alerts**: chase, rebook after results, keep appointment, resolve hold, acknowledge, close loop. Each has a named owner (the reviewing clinician).

## External integrations
| System | Status | Production route |
|--------|--------|------------------|
| Clinic note source (Tandem) | pasted / sample | consultation summary API |
| Order comms | mocked | FHIR ServiceRequest / HL7 ORM |
| Results feed | simulated button | FHIR DiagnosticReport / HL7 ORU |
| PAS / booking | mocked | FHIR Appointment / PAS API |
| Patient messaging | mocked | NHS App / SMS gateway |
| EPR record | mocked | FHIR DocumentReference |

## Audit / provenance
Append-only log (`audit.py`); every entry carries a simulated date, an actor label (AI · RULE · HUMAN · API · SYSTEM), the loop id and a message. Investigations carry the verbatim note quote that justified them. Per-loop counts of API actions, rule checks and human decisions are derived from the log.

## Failure / escalation behaviour
- Extraction unavailable or errors → HTTP error to the UI; nothing proceeds.
- Any blocking rule → `needs_review`; no orders, booking or messages; reason codes shown with plain-English guidance.
- Clinician choice that still violates a rule → refused with the same message.
- Overdue / on hold / at risk / appointment passed → alert to owner; the system never silently waits.
- Unknown loop, item or action → 4xx; state unchanged.

## Deliberately out of scope for the hackathon
Authentication, persistence, real integrations, abnormal-result routing, DNA handling. See the README roadmap.
