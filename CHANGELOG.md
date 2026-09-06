# Changelog

All notable changes to PlugPoint are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Hosted demo on Railway: https://web-production-4653b.up.railway.app

### Known issues
- A note that explicitly says "no follow-up needed" can be extracted as a follow-up with no interval, which the rules then escalate. Found by the live gold run; fix pending a one-line clarification of the extraction prompt.

## [0.1.0] — 2026-09-05

First release, built at the NXGN × Tandem Health "Automate Admin, Land a Role" hackathon.

### Added
- **Extraction**: single schema-constrained Claude call turning a clinic note into an `ActionPlan` (investigations with indications and evidence quotes, follow-up interval candidates, reviewer role, ambiguities). Offline fixture mode for demos without network.
- **Rules**: five deterministic plan checks — indication stated, single follow-up interval, interval present, appointment after expected results (turnaround table per category), reviewer resolved — with reason codes and a suggested earliest workable interval.
- **Approval**: editable action plan (amend names and indications, add or drop investigations); every amendment recorded as a HUMAN audit entry. Blocked plans require an explicit clinician choice, which is checked by the same rules.
- **Actions**: mocked order comms, PAS booking (consultant roster by clinic), patient SMS and EPR write, behind named interfaces in `integrations.py`.
- **Tracker**: loop and item state machine with expected-by dates and a simulated clock; alerts to a named owner for overdue results, appointments at risk (results not expected before the booked date), investigations put on hold by a department, and appointments that have passed; chase / rebook / resolve-hold / keep / close actions.
- **Audit trail** labelling every event AI · RULE · HUMAN · API · SYSTEM, per-loop counts of software actions vs clinician decisions, collapsible in the UI.
- **Gold evaluation**: 15 synthetic cases (routine, edge, ambiguous, escalation) run through the production workflow classes; CLI report, `/eval` results page, offline and live modes, separate result files.
- **Demo UI**: four sample notes (routine, conflicting intervals, missing indication, follow-up before results), tracker summary strip, sample switch resets the demo.
- `run.sh` one-command start, GitHub Actions offline eval on every push, MIT license, contributing guide.

[Unreleased]: https://github.com/nickjlamb/tandem-hackathon-2026/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nickjlamb/tandem-hackathon-2026/releases/tag/v0.1.0
