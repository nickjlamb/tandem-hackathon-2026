# Evaluation

## What is tested
`eval/cases.json` holds 15 synthetic cases. Each stores the input (patient, note author, clinic note, and an offline extraction stand-in), the expected gate output (`requires_human_review`, reason codes, item count, follow-up weeks, reviewer, flags), the expected downstream actions (orders placed, appointment booked, patient messaged) and, for tracker cases, scripted events with the alerts expected at each point.

| Type | Cases | Behaviour |
|------|-------|-----------|
| routine | G01 G02 G03 G06 G15 | plan passes, actions fire, loop tracked and closed |
| edge | G04 G05 G07 G08 | no investigations; no follow-up; biopsy timing; interval in days |
| ambiguous | G09 G10 | conflicting intervals; follow-up without interval → escalate |
| escalation | G11 G12 G13 G14 | missing indication; follow-up before results; both at once; scan on hold |

## How it runs
`eval/run_eval.py` builds a fresh `Store` per case and calls the same `extract_action_plan`, `create_loop`, `approve`, `advance`, `receive_result`, `hold_investigation`, `resolve_hold` and `close` methods the API calls. Checks are exact comparisons; a case passes only if every check passes. The critical property is asserted separately for every escalation case: **no orders, booking or messages when the gate blocked**.

## Metrics
Total / passed / failed / pass %; escalation cases passed; escalations missed (blocked plans that were nonetheless actioned); pass counts by type. Results are written to `eval/results-offline.json` or `eval/results-live.json` and shown at `/eval`.

## Results so far
| Run | Passed | Escalation cases | Escalations auto-actioned |
|-----|--------|------------------|---------------------------|
| Offline (rules + gate + tracker) | 15/15 | 5/5 | 0 |
| Live extraction (first run) | 11/15 | 3/5 | 0 |

Live-run failures: G15 and G13 were case errors (note lacked the indication the stand-in assumed; bronchoscopy category ambiguous) and G09 an over-strict item count — all three fixed in the cases, not the workflow. G05 is a genuine extraction gap ("no follow-up needed" returned as a follow-up with no interval), recorded as a known issue.

## Rules for this eval
The production workflow is never modified merely to make a case pass. A wrong case is fixed and the commit says so. Failures are reported as found.

## Next
Clinician-authored cases; more dictation-style noise; measure extraction across models; abnormal-result and DNA scenarios once those flows exist.
