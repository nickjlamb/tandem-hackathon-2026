# PlugPoint v0.1.0 — "nothing falls through the cracks"

First release, built at the NXGN × Tandem Health "Automate Admin, Land a Role" hackathon, 5 September 2026.

PlugPoint closes the loop after outpatient clinic. It reads the clinician's plan from the clinic note, checks it with deterministic rules, waits for a one-click approval, then orders, books, messages the patient and tracks every item against an expected date — alerting a named owner when a result is overdue, an appointment is at risk, or a scan is put on hold.

**Highlights**
- One schema-constrained LLM call; everything else is code you can test.
- The system never guesses: conflicting intervals, missing indications and impossible timings stop for a clinician, with a reason and a suggested fix.
- Editable action plan; every amendment is an audit entry.
- Gold evaluation: 15 synthetic cases through the production workflow — offline 15/15, live extraction 11/15 with **0 escalations auto-actioned** in either run.
- Runs in 60 seconds with no API key.

Full details in [CHANGELOG.md](CHANGELOG.md).
