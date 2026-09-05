# PlugPoint — Tandem Health Hackathon 2026

Built at the NXGN × Tandem Health "Automate Admin, Land a Role" hackathon (5 September 2026).

> Working docs: [strategy](docs/strategy.md) · [problem](docs/problem.md) · [architecture](docs/architecture.md) · [evaluation](docs/evaluation.md). Claude Code build guidance: [`CLAUDE.md`](CLAUDE.md).

## Problem

After an outpatient consultation the clinician has a plan in their head — order a scan, repeat bloods, see the patient again in six weeks with the results. Turning that plan into reality is a chain of manual admin: separate requests, emails to secretaries to book the follow-up, and someone having to remember to check that the results actually came back before the appointment. When clinics are busy, steps get missed and **patients are lost to follow-up**.

## Solution

PlugPoint turns the clinic note's plan into a tracked action plan. The clinician approves it once; the software does the admin and keeps watch until the loop is closed.

- **Extract** (LLM, schema-constrained): investigations + reasons, follow-up interval, who should review.
- **Check** (deterministic rules): every investigation has an indication; one unambiguous follow-up interval; the appointment falls after results are expected.
- **Approve** (clinician): one click. Nothing is ordered or booked until then. Ambiguous plans stop here.
- **Act** (mocked integrations): order investigations, book follow-up with the right clinician, message the patient, write to the EPR.
- **Track** (deterministic): every item has an expected-by date. Overdue results, appointments at risk and investigations put on hold by a department raise an alert to a named owner, with chase / rebook / hold-resolved actions.
- **Audit**: every step labelled AI / RULE / HUMAN / API / SYSTEM.

## Workflow

```
clinic note ─► [AI] extract plan ─► [RULE] checks ─► routine? ──yes──► [HUMAN] approve ─► [API] order · book · message · record
                                                    └──no──► [HUMAN] decide (system never guesses) ─┘
                                                                          │
              [SYSTEM] tracker: expected dates → overdue / appointment-at-risk alerts → [HUMAN] chase · rebook · close
```

## Architecture

`plugpoint/` — single Python package, FastAPI, in-memory state, simulated clock.

| File | Role | Category |
|------|------|----------|
| `extract.py` | one Claude call, forced tool use → `ActionPlan` (offline fixtures without a key) | LLM |
| `rules.py` | completeness / conflict / timing checks, turnaround table, reviewer rule | deterministic |
| `tracker.py` | loop + item state machine, approval, safety-net checks, clinician actions | deterministic |
| `integrations.py` | `MockEPR`, `MockOrderComms`, `MockScheduling`, `MockPatientMessaging` | mocked |
| `audit.py` | append-only trail with actor labels | deterministic |
| `app.py` + `static/index.html` | API and demo UI | — |

See [`docs/architecture.md`](docs/architecture.md).

## Evaluation

15 synthetic gold cases in [`eval/cases.json`](eval/cases.json) — routine, edge, ambiguous/conflicting and must-escalate — each storing the synthetic note, the expected plan/gate output, the expected escalation status and the expected downstream actions (orders, booking, patient message) plus scripted tracker events (results arriving, delays, a scan put on hold). [`eval/run_eval.py`](eval/run_eval.py) pushes every case through the **same** workflow classes the app uses and compares programmatically; nothing in the workflow is tuned for the eval and failures are reported as found.

```bash
python -m eval.run_eval --offline    # rules + gate + tracker, no network, ~1 s
python -m eval.run_eval              # live Claude extraction if ANTHROPIC_API_KEY is set (~1 min)
```

Results are shown at http://localhost:8000/eval (tiles: passed / failed / % / escalation cases / escalations missed) and written to `eval/results.json`. Latest offline run: **15/15, 5/5 escalation cases, 0 escalations auto-actioned**.

## Demo

```bash
git clone https://github.com/nickjlamb/tandem-hackathon-2026.git && cd tandem-hackathon-2026
cp .env.example .env            # optional: add ANTHROPIC_API_KEY to extract free-text notes
./run.sh                        # creates .venv, installs, serves http://localhost:8000
```

Without an API key the three built-in sample notes still run end to end using offline fixtures (identical shape to the live extraction), so the demo does not depend on wifi.

Terminal-only run of the happy path: `python -m plugpoint.cli` (or `python -m plugpoint.cli B_conflict`).

Sample notes: A routine happy path · B conflicting intervals · C missing indication · D follow-up before results. "simulate hold" on an imaging item shows the on-hold escalation.

**Demo script (≈2 min):** sample A → Extract → 5 checks pass → Approve → orders, booking, SMS, EPR in the audit trail → "simulate result" for bloods → +4 weeks, +1 week → MRI overdue + appointment at risk → Rebook after results → follow-up moved, patient told. Then sample B → conflicting intervals → system refuses to guess, clinician picks.

## Team

_TODO: Names and roles._
