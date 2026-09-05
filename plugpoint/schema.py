"""Structured data contracts shared by the LLM extraction step, the rules
engine, the tracker and the UI. Everything downstream of the LLM works on
these objects, never on free text."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["imaging", "bloods", "biopsy", "other"]
Urgency = Literal["routine", "urgent"]
ReviewerRole = Literal["consultant", "registrar", "any"]
ClinicianRole = Literal["consultant", "registrar"]


# ---------------------------------------------------------------- LLM output
class Investigation(BaseModel):
    name: str = Field(description="Investigation as named in the note, e.g. 'MRI abdomen with contrast'")
    category: Category
    reason: Optional[str] = Field(
        default=None,
        description="Clinical indication stated in the note. Null if the note gives no reason.",
    )
    urgency: Urgency = "routine"
    evidence: str = Field(default="", description="Verbatim quote from the note supporting this item")


class FollowUp(BaseModel):
    interval_weeks: Optional[int] = Field(
        default=None,
        description="Follow-up interval in weeks if exactly one is stated; null if none or conflicting.",
    )
    interval_candidates_weeks: list[int] = Field(
        default_factory=list,
        description="Every follow-up interval mentioned in the note, in weeks (months x4, days /7).",
    )
    reviewer_role: Optional[ReviewerRole] = Field(
        default=None,
        description="Who the note says should see the patient next. Null if not stated.",
    )
    purpose: Optional[str] = None
    evidence: str = ""


class ActionPlan(BaseModel):
    investigations: list[Investigation] = Field(default_factory=list)
    follow_up: Optional[FollowUp] = None
    ambiguities: list[str] = Field(
        default_factory=list,
        description="Anything unclear, contradictory or missing that a clinician should confirm.",
    )


# ------------------------------------------------------------- rules output
Severity = Literal["block", "warn", "info"]


class Flag(BaseModel):
    code: str
    severity: Severity
    message: str
    detail: dict = Field(default_factory=dict)


class GateResult(BaseModel):
    requires_human_review: bool
    reasons: list[str] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)


# ------------------------------------------------------------- API payloads
class Clinician(BaseModel):
    name: str
    role: ClinicianRole


class PlanRequest(BaseModel):
    patient_id: str
    note: str
    clinician: Clinician
    sample_id: Optional[str] = Field(default=None, description="Fixture id; enables offline mock extraction")


class ItemEdit(BaseModel):
    name: Optional[str] = None
    reason: Optional[str] = None


class NewItem(BaseModel):
    name: str
    category: Category = "other"
    reason: str
    urgency: Urgency = "routine"


class ApproveRequest(BaseModel):
    loop_id: str
    approved_investigations: list[str] = Field(description="Item ids the clinician approved")
    approve_follow_up: bool = True
    interval_weeks: Optional[int] = Field(
        default=None, description="Clinician-chosen interval when the plan was ambiguous"
    )
    edits: dict[str, ItemEdit] = Field(default_factory=dict, description="Clinician amendments keyed by item id")
    added: list[NewItem] = Field(default_factory=list, description="Investigations the clinician added")
