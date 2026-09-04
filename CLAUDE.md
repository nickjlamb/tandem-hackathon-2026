# Claude Code guidance for this repo

Context: NXGN × Tandem Health hackathon, 5 Sep 2026, ~3 h build window. Read `docs/strategy.md` first; the chosen problem and workflow will be in `docs/problem.md` and `docs/architecture.md`.

## Build brief
Build this as a **workflow, not an autonomous agent**. Use deterministic code for rules, validation, routing and state changes. Use the LLM only where language understanding or generation is required, with schema-constrained structured outputs. Keep clinical judgement behind an explicit human approval step where appropriate. Make external integrations mockable so we can demonstrate the complete workflow end to end.

## Rules
- Smallest working vertical slice first (happy path end to end), then the failure/escalation path, then the gold eval — in that order.
- Label every step deterministic / LLM / human in code and in the audit trail.
- No agent frameworks or multi-agent designs unless the model genuinely has to choose between tools.
- No auth, real databases, real EHR integration, or deployment complexity unless explicitly asked.
- Synthetic data only. Never invent real patient details.
- Mock integrations live in one obvious place and say they are mocks.
- Gold cases run through the same workflow as the demo and report pass/fail + escalation metrics.
- Keep the repo runnable in one command; document it in the README Demo section.
- Don't add "one last feature" after 15:15.

## Before adding a dependency or framework
Ask: is this needed for the demo at 15:55? If not, skip it.
