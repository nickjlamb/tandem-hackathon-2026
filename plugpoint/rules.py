"""Deterministic workflow rules. No LLM here: same input -> same output.

Given the extracted ActionPlan and who wrote the note, these rules decide
whether the plan is complete and internally consistent, and compute the dates
the tracker will hold the workflow to."""

from __future__ import annotations

from datetime import date, timedelta

from .schema import ActionPlan, Clinician, Flag, GateResult

# Expected turnaround from order to result, by investigation category (days).
# Demo values; in production these come from the department's SLA table.
TURNAROUND_DAYS = {"imaging": 14, "bloods": 3, "biopsy": 21, "other": 7}

# Results should be back this many days before the follow-up appointment.
RESULT_BUFFER_DAYS = 2

# Warn the clinician if results are still outstanding this close to the appointment.
APPOINTMENT_LEAD_DAYS = 7


def expected_result_date(category: str, ordered_on: date) -> date:
    return ordered_on + timedelta(days=TURNAROUND_DAYS.get(category, TURNAROUND_DAYS["other"]))


def next_weekday(d: date) -> date:
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d += timedelta(days=1)
    return d


def earliest_follow_up_date(plan: ActionPlan, ordered_on: date) -> date:
    """Earliest date on which all planned results should be available."""
    if not plan.investigations:
        return ordered_on
    latest = max(expected_result_date(i.category, ordered_on) for i in plan.investigations)
    return next_weekday(latest + timedelta(days=RESULT_BUFFER_DAYS))


def resolve_reviewer(plan: ActionPlan, author: Clinician) -> str:
    """Who should see the patient next. Explicit in note wins; otherwise the author."""
    if plan.follow_up and plan.follow_up.reviewer_role in ("consultant", "registrar"):
        return plan.follow_up.reviewer_role
    return author.role


def check_plan(plan: ActionPlan, author: Clinician, today: date) -> GateResult:
    flags: list[Flag] = []

    # R1 - every investigation needs a stated clinical indication (order systems reject without one)
    for inv in plan.investigations:
        if not inv.reason or not inv.reason.strip():
            flags.append(Flag(
                code="missing_indication", severity="block",
                message=f"No clinical indication stated for {inv.name}",
                detail={"investigation": inv.name},
            ))

    fu = plan.follow_up
    if fu is None:
        flags.append(Flag(code="no_follow_up", severity="warn",
                          message="No follow-up specified; results will need a named reviewer"))
    else:
        distinct = sorted(set(fu.interval_candidates_weeks))
        # R2 - conflicting intervals in the note -> clinician must choose, never guess
        if len(distinct) > 1:
            flags.append(Flag(
                code="conflicting_follow_up_interval", severity="block",
                message=f"Note states more than one follow-up interval: {', '.join(f'{w} wk' for w in distinct)}",
                detail={"candidates_weeks": distinct},
            ))
        # R3 - follow-up mentioned but no interval at all
        elif fu.interval_weeks is None and not distinct:
            flags.append(Flag(code="missing_follow_up_interval", severity="block",
                              message="Follow-up requested but no interval stated"))
        # R4 - appointment must fall after results are expected back
        else:
            weeks = fu.interval_weeks or distinct[0]
            proposed = next_weekday(today + timedelta(weeks=weeks))
            earliest = earliest_follow_up_date(plan, today)
            if proposed < earliest:
                flags.append(Flag(
                    code="follow_up_before_results", severity="block",
                    message=(f"Follow-up in {weeks} wk ({proposed.isoformat()}) is before results are expected "
                             f"({earliest.isoformat()})"),
                    detail={"proposed_date": proposed.isoformat(), "earliest_date": earliest.isoformat()},
                ))
        # R5 - reviewer defaulting is deterministic and visible
        if fu.reviewer_role not in ("consultant", "registrar"):
            flags.append(Flag(code="reviewer_defaulted", severity="info",
                              message=f"No reviewer named; defaulting to note author ({author.role})"))

    # LLM-reported ambiguities are surfaced to the clinician but do not block on their own;
    # the deterministic rules above decide what blocks.
    for text in plan.ambiguities:
        flags.append(Flag(code="ambiguity_noted", severity="warn", message=text))

    blocking = [f for f in flags if f.severity == "block"]
    return GateResult(
        requires_human_review=bool(blocking),
        reasons=sorted({f.code for f in blocking}),
        flags=flags,
    )
