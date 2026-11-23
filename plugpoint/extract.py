"""The ONE place an LLM is used: turn the clinician's free-text plan into an
ActionPlan. Schema-constrained via structured outputs. The model is told not to
add, infer or recommend anything the note does not say.

Falls back to hand-written fixtures (fixtures.MOCK_PLANS) when there is no API
key or PLUGPOINT_MOCK_LLM=1, so the workflow can be demonstrated offline."""

from __future__ import annotations

import os

from .fixtures import MOCK_PLANS
from .schema import ActionPlan

MODEL = os.environ.get("PLUGPOINT_MODEL", "claude-sonnet-5-5")
# Newer models think before answering and that counts against the output budget, so leave headroom.
MAX_TOKENS = int(os.environ.get("PLUGPOINT_MAX_TOKENS", 4096))

SYSTEM_PROMPT = """You are an extraction service for an outpatient clinic workflow tool.
Read the clinician's clinic note and record the post-consultation ACTION PLAN the clinician has
already decided on, as structured data.

Rules:
- Record only what the note states. Never add, infer or recommend investigations, intervals or
  reviewers that are not written in the note.
- Every investigation the clinician plans to order is one item. Use the name from the note.
- reason: the clinical indication the note gives for that investigation. If the note gives none,
  set reason to null. Do not invent one.
- follow_up.interval_candidates_weeks: list EVERY follow-up interval mentioned anywhere in the note,
  converted to weeks (months x 4, days / 7, round to nearest whole week). If exactly one distinct
  value is mentioned, also set interval_weeks to it. If two or more different values are mentioned,
  leave interval_weeks null.
- If the note explicitly says no clinic follow-up is needed (e.g. discharge, results to GP by letter),
  set follow_up to null. Do not create a follow_up object with no interval in that case.
- reviewer_role: 'consultant' or 'registrar' only if the note explicitly says who should see the
  patient next; otherwise null.
- evidence: short verbatim quotes from the note.
- ambiguities: anything unclear, contradictory or missing that a clinician should confirm.
The note is synthetic demo data."""


class ExtractionUnavailable(RuntimeError):
    pass


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("PLUGPOINT_MOCK_LLM") != "1"


def extract_action_plan(note: str, sample_id: str | None = None,
                        fallback_plan: ActionPlan | None = None) -> tuple[ActionPlan, str]:
    """Returns (plan, source) where source is 'llm' or 'mock'.

    `fallback_plan` is the offline stand-in for this note (used by the gold eval so the
    rules/tracker can be tested without network); it is ignored when the LLM is available."""
    if not llm_available():
        if sample_id in MOCK_PLANS:
            return MOCK_PLANS[sample_id].model_copy(deep=True), "mock"
        if fallback_plan is not None:
            return fallback_plan.model_copy(deep=True), "mock"
        raise ExtractionUnavailable(
            "No ANTHROPIC_API_KEY set (or PLUGPOINT_MOCK_LLM=1) and this note is not one of the "
            "built-in samples. Add a key to .env to extract free-text notes."
        )
    return _extract_with_claude(note), "llm"


def _extract_with_claude(note: str) -> ActionPlan:
    import anthropic  # imported lazily so mock mode has no hard dependency at runtime

    client = anthropic.Anthropic()
    # Structured outputs: the API constrains the reply to the ActionPlan JSON schema. (Forced tool
    # use, the previous mechanism, is rejected with a 400 by claude-sonnet-5-5 and later models.)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"<clinic_note>\n{note}\n</clinic_note>"}],
        output_config={"format": {"type": "json_schema", "schema": anthropic.transform_schema(ActionPlan)}},
    )
    # Check why the model stopped before trusting the text: a refusal or a truncated reply is not
    # guaranteed to match the schema.
    if response.stop_reason == "refusal":
        raise ExtractionUnavailable("The model declined to extract a plan from this note")
    if response.stop_reason == "max_tokens":
        raise ExtractionUnavailable("The model ran out of output tokens before finishing the plan")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise ExtractionUnavailable("Model did not return a structured action plan")
    return ActionPlan.model_validate_json(text)
