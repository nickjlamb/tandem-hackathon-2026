# Contributing to PlugPoint

Thanks for your interest. PlugPoint is a small codebase with strong opinions; the opinions are the point.

## Ground rules

1. **Workflow, not agent.** One structured LLM call for language understanding. Rules, routing, dates and state changes are plain code. If something could be an `if` statement, it must be an `if` statement.
2. **Nothing changes the world without a clinician.** Orders, bookings and messages happen only after explicit approval. New automation must sit behind that gate.
3. **Never guess.** Missing, conflicting or ambiguous information escalates to a human with a reason code. Adding a rule that resolves ambiguity silently will not be merged.
4. **Synthetic data only.** No real patient, clinician or organisation data anywhere in the repo, tests or screenshots.
5. **Mocks stay honest.** External systems live in `plugpoint/integrations.py`, are named `Mock*`, and log `[MOCK …]` in the audit trail. Replacing one with a real client must not change the workflow code.
6. **The eval is the contract.** Behavioural changes come with gold cases in `eval/cases.json`. Do not edit the workflow to make a case pass; fix the case if the case is wrong, and say which in the PR.

## Development

```bash
./run.sh                              # app with auto-reload at http://localhost:8000
python -m plugpoint.cli               # terminal happy path
python -m eval.run_eval --offline     # must pass before you open a PR
python -m eval.run_eval               # live extraction, if you have an API key
```

Python 3.11+, no build step, no frontend toolchain — `static/index.html` is hand-written vanilla JS on purpose.

## Pull requests

- One change per PR, with a short description of *what a clinician would notice*.
- Update `CHANGELOG.md` under **Unreleased**.
- If you touched `rules.py` or `tracker.py`, add or update a gold case.
- CI runs the offline gold evaluation; it must be green.

## Reporting problems

Open an issue with the sample note (synthetic!) and the audit trail. The audit trail is designed to make "who did what" obvious — please include it.

## Code of conduct

Be kind, assume good faith, remember there are patients at the end of this.
