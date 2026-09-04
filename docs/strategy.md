# Strategy (read this before touching code)

**Mantra:** Don't build the most software. Make the best decision about what to build, prove it works, and make the clinician's remaining job obvious.

Tandem judges on **strength of the idea** and **how well the team executes**. Nominal build time is ~3h15 including a lunch break. Optimise for one convincing, tested vertical slice.

## Hierarchy: ELIMINATE → AUTOMATE → ASSIST → ESCALATE
- **Eliminate** — does this admin step need to exist at all?
- **Automate** — predictable / rule-based → deterministic code (validation, routing, state, lookups, APIs, audit logging).
- **Assist** — LLM only where messy human language must be understood or generated (extraction, intent, drafting, spotting ambiguity). Structured JSON outputs.
- **Escalate** — clinician stays in for judgement, meaningful uncertainty, conflict, risk, accountability.

"Don't use an LLM for something that could reliably be an `if` statement."

## First 15 minutes (12:30–12:45): listen, don't prompt
Ask the clinician / ops teammate:
- What admin this week made you think "why am I doing this?"
- What do you repeatedly copy or re-enter? Chase? Have to remember to check later?
- What gets rejected / returned because information is missing?
- What information do you repeatedly hunt for?
- What do you do after every consultation that doesn't need a medical degree?
- What admin worries you when busy because something could get missed?
- **Show us exactly what happens now.** Which parts truly need clinical judgement?

Look for: chasing · duplication · copy/re-entry · routing · reconciliation · checking · missing ownership · async follow-up · exceptions.

## Problem selection (choose by ~12:45)
Generate several candidates from real experience, narrow to three, score 1–5 (max 50):

| Criterion | Weight | Question |
|-----------|--------|----------|
| Real pain | ×2 | Frequent, genuine clinician burden? |
| Admin removable | ×2 | Do we actually remove meaningful clinician work? |
| Demoability | ×2 | Full before→after demo in ~3 h? |
| Distinctiveness | ×1 | Not "another summariser/chatbot"? |
| Measurability | ×1 | Can we count steps/time/actions removed? |
| Evaluability | ×1 | Clear gold cases with known expected outcomes? |
| Actionability | ×1 | Does the system *do* downstream work, not just emit text? |

Veto questions: (1) Are we basically just generating text? → find the downstream action. (2) Depends on infrastructure we can't demo? → mock it or drop it. (3) Can the clinician say in one sentence why they'd want it? → if not, reject.

Then write (also in `problem.md`):
```
TODAY:          [clinician] has to ______.
OUR SYSTEM:     automatically ______.
CLINICIAN ONLY: ______.
RESULT:         ______.
```
And the demo sentence **before building**:
> "At 15:55 we'll show a clinician doing X today, then giving our system Y, after which they only need to do Z."

## Technical philosophy: workflow-first, not agent-first
For every step, label it **deterministic / LLM / human**. Reference pattern (simplify freely):

```
input → LLM extraction → structured JSON → deterministic rules
      → exception gate ─┬─ routine ──────────────┐
                        └─ uncertain → clinician ─┤
      → API / mocked downstream action → audit trail
```
- Single structured LLM call + deterministic workflow beats agents unless the model must genuinely choose between tools.
- Mocks are fine: `createReferral()`, `sendPatientMessage()`, `createFollowUpTask()`, `updateEHR()`, `scheduleAppointment()`. Label clearly what is real logic vs mocked integration vs production work.

## Gold evaluation set (key differentiator)
10–20 synthetic cases, clinician-approved expected outcomes, run through the **same** workflow as the demo. Include normal, edge, ambiguous, conflicting, and must-escalate cases. Test system behaviour, not prose quality. "Knowing when NOT to automate is a feature."

## Differentiator menu (pick 2–3 once the problem is known)
Failure-state demo (refuse to guess) · audit trail with AI / deterministic / human labels · counted admin removed (before vs after) · end-to-end action after approval.

## Timebox
| Time | Do |
|------|----|
| 12:15–12:30 | Briefing |
| 12:30–12:45 | Clinician pain → pick problem → map workflow → define demo |
| 12:45–14:15 | Build the complete happy path (demoable by lunch) |
| After lunch | Improve core; then eval → failure state → audit trail → action → polish |
| **15:15** | **STOP BUILDING** |
| 15:15–15:45 | Submit, test demo, fill slides, rehearse, check repo/URL works |

## Demo structure (five slides, skeleton in prep deck)
1. Product — one sentence + team. 2. Admin problem — lived story, before/after counts. 3. Solution — workflow; eliminated / deterministic / AI / human. 4. **Live demo** — happy path → failure path. 5. Impact + evidence — admin reduction, gold-set result, escalation rate, "with another week…".

## Team behaviour
This is also a recruitment opportunity. Don't vanish into Claude Code. Frame the problem, listen to clinicians, explain trade-offs, divide work, show progress often, ask "is this how you'd actually want it to work?", show judgement about what NOT to automate.

## Don't waste time on
Auth · production DBs · real EHR/NHS APIs · deployment complexity · multiple agents · frameworks for their own sake · visual polish · feature count · generic chat UI · building past 15:15.
