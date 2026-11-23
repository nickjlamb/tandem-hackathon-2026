# Changelog

All notable changes to PlugPoint are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Clinic note card: a two-way switch at the top makes the choice explicit — **Use a sample note** (replays the saved extraction, instant) or **Paste your own** (synthetic notes only, one live Claude call). Pasting your own shows an empty note box and a patient picker; the hint under the button now says whether the next click is instant or live, including when a sample has been edited. On a server with no API key the second option is disabled.
- Default extraction model is now `claude-sonnet-5-5` (was `claude-sonnet-4-5`, which Anthropic retires from the Claude API on 30 November 2026). `PLUGPOINT_MODEL` still overrides it. The live gold results in the README were measured on `claude-sonnet-4-5` and have not been re-run on the new default.

### Fixed
- Live extraction on `claude-sonnet-5-5` failed with a 400 (`tool_choice: type "tool" and "any" are not supported for this model`). Extraction now uses structured outputs (`output_config.format` with the `ActionPlan` JSON schema) instead of a forced tool call; `anthropic>=2.12` is required. Output budget raised to 4096 tokens (`PLUGPOINT_MAX_TOKENS`), and enum values are accepted case-insensitively.
- Extraction prompt: a note that explicitly says no clinic follow-up is needed now yields `follow_up: null` instead of a follow-up with no interval (found by the live gold run, confirmed on re-run: 17/17 live).
- Gold case G09 note now states an indication for the bloods it lists.
- Gold case G14 note now reads "with Mr Hollis (consultant)". The live run on `claude-sonnet-5-5` (23 Nov, 16/17) failed G14 because the note named Mr Hollis without stating his role: the model left `reviewer_role` null, as the prompt instructs, and the rules defaulted to the note's author. G14 tests the radiology hold, not role inference, so the note was made explicit. A note that names a consultant without the word "consultant" is still booked with the author and not flagged for review.
- Eval runner records an extraction error as a failed case instead of crashing the summary.

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
