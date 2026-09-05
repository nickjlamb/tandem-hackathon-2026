# Problem

## User
Hospital outpatient clinicians — consultants and registrars — and the secretaries who action their plans. Every clinic, every patient.

## Current workflow
1. Consultation ends; the clinician has a plan (investigations, follow-up, who should see the patient next).
2. Each investigation is requested separately in the order-comms system, with a clinical indication retyped.
3. An email goes to the secretary to book the follow-up "in about six weeks, with the consultant".
4. Somebody has to remember to check that the results came back before that appointment.
5. If a scan is delayed or put on hold by radiology, nobody is told; the patient turns up to an appointment without results, or the appointment is quietly missed.

## Admin pain
Multiple emails per patient; re-entry of the same information into several systems; results that arrive with no owner; patients uncertain what happens next; workforce burnout from carrying open loops in memory.

## What actually requires clinical judgement
Deciding *what* to order and *when* to see the patient — that stays with the clinician, and the note already contains it. Resolving genuine ambiguity in the plan. Interpreting results. Everything else — capturing the plan, checking it is complete, requesting, booking, informing, tracking, chasing, flagging — is admin.

## Proposed workflow
```
TODAY:          the clinician has to request each test, email the secretary, and remember to check results arrived.
OUR SYSTEM:     automatically extracts the plan from the note, checks it, and after one approval orders, books,
                messages the patient and tracks every item against an expected date, alerting a named owner
                when something is late, at risk or on hold.
CLINICIAN ONLY: approve (or amend) the plan; decide when the plan is ambiguous; act on alerts.
RESULT:         one decision instead of a dozen admin steps, and no patient silently lost to follow-up.
```

## Measurable outcome
Per patient: admin actions completed by software vs clinician decisions (shown on the plan card — typically 6 : 1). Per clinic: open loops, results awaited, overdue, alerts open (tracker summary strip). Safety: escalation cases correctly stopped (gold set).

## Selection rationale
Scored highest of our three candidates on real pain (×2), admin removable (×2) and actionability; passed all three vetoes — the downstream action is real (orders, bookings, messages), the integrations are mockable, and the one-sentence clinician pitch is "nothing falls through the cracks".
