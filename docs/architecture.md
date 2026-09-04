# Architecture

Sketch first, code second. Every box should be either "deterministic", "LLM", or "human".

## Overview
- [ ] One-paragraph description of the pipeline:
- [ ] Diagram (paste image or ASCII):

```
input → [deterministic] → [LLM] → [clinician review] → output
```

## Deterministic / API components
- [ ] Parsing / extraction / validation (no LLM):
- [ ] Rules, lookups, templates, code lists:
- [ ] Data model / schema for structured outputs:

## LLM components
- [ ] Model(s) and why:
- [ ] Task per call (summarise / extract / draft / classify):
- [ ] Prompt inputs and structured output format:
- [ ] Guardrails (schema validation, allowed values, refusal cases):

## Human / clinician checkpoints
- [ ] Where a clinician must review before anything leaves the system:
- [ ] What they see (diff, highlights, confidence, source snippets):
- [ ] What they can do (approve / edit / reject / escalate):

## External integrations (real or mocked)
| System | Real or mocked? | Direction (in/out) | Notes |
|--------|-----------------|--------------------|-------|
| EHR    | mocked          |                    |       |
|        |                 |                    |       |
- [ ] Synthetic / dummy data source (no real patient data):

## Audit / provenance
- [ ] What is logged per run (inputs, prompts, outputs, model, timestamp, reviewer):
- [ ] How each output claim links back to its source:
- [ ] Versioning of prompts / rules:

## Failure / escalation behaviour
- [ ] Low confidence or missing data → what happens?
- [ ] Conflicting information → what happens?
- [ ] LLM/API error or timeout → what happens?
- [ ] Out-of-scope input → what happens?
- [ ] Default is always: surface to human, never silently proceed.

## Tech choices (decide on the day)
- [ ] Language / framework:
- [ ] UI (if any):
- [ ] Hosting / demo link:
