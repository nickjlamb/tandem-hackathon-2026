"""Synthetic demo data. Every patient, clinician and note here is invented.

`MOCK_PLANS` are hand-written extraction results used when no ANTHROPIC_API_KEY
is set (or PLUGPOINT_MOCK_LLM=1), so the whole workflow can be demonstrated
offline. They mirror what the real extraction step returns for the same note."""

from __future__ import annotations

from .schema import ActionPlan, FollowUp, Investigation

PATIENTS = {
    "P001": {"id": "P001", "name": "Amara Okafor", "age": 58, "sex": "F", "hospital_no": "H-10001",
             "phone": "07700 900001", "clinic": "Urology"},
    "P002": {"id": "P002", "name": "Daniel Reyes", "age": 64, "sex": "M", "hospital_no": "H-10002",
             "phone": "07700 900002", "clinic": "Respiratory"},
    "P003": {"id": "P003", "name": "Priya Nair", "age": 45, "sex": "F", "hospital_no": "H-10003",
             "phone": "07700 900003", "clinic": "Hepatology"},
    "P004": {"id": "P004", "name": "Tomasz Wójcik", "age": 71, "sex": "M", "hospital_no": "H-10004",
             "phone": "07700 900004", "clinic": "Respiratory"},
}

CLINICIANS = [
    {"name": "Dr Sam Patel", "role": "registrar"},
    {"name": "Mr James Hollis", "role": "consultant"},
    {"name": "Dr Elena Fischer", "role": "consultant"},
]

# Consultant roster used by the mock scheduling system, keyed by clinic.
CONSULTANT_ROSTER = {
    "Urology": "Mr James Hollis",
    "Respiratory": "Dr Elena Fischer",
    "Hepatology": "Dr Elena Fischer",
}

SAMPLE_NOTES = {
    "A_routine": {
        "patient_id": "P001",
        "label": "A · Routine renal lesion (happy path)",
        "clinician": {"name": "Dr Sam Patel", "role": "registrar"},
        "note": (
            "Urology clinic 05/09/2026. 58F referred by GP with microscopic haematuria. "
            "Ultrasound shows a 3.2 cm indeterminate lesion in the left kidney. Otherwise well, "
            "BP 138/84, no loin pain. Last creatinine 108 (borderline).\n\n"
            "Plan: MRI abdomen with contrast to characterise the left renal lesion. "
            "Repeat U&E and eGFR before the MRI given the borderline creatinine. "
            "Follow up in clinic in 6 weeks with the results - please book with Mr Hollis "
            "(consultant) as I would like his opinion on the lesion. Patient aware of the plan."
        ),
    },
    "B_conflict": {
        "patient_id": "P002",
        "label": "B · Conflicting follow-up interval (should escalate)",
        "clinician": {"name": "Dr Sam Patel", "role": "registrar"},
        "note": (
            "Respiratory clinic 05/09/2026. 64M, persistent cough for 8 weeks, ex-smoker 30 pack-years. "
            "CXR reports a possible right upper lobe opacity. No haemoptysis, weight stable.\n\n"
            "Plan: CT chest with contrast to further evaluate the RUL opacity. See in clinic in 2 weeks "
            "to discuss. Bloods today: FBC, CRP.\n\n"
            "Addendum: for follow-up, review in 3 months with the CT result. "
            "Consultant review not required at this stage."
        ),
    },
    "C_missing_reason": {
        "patient_id": "P003",
        "label": "C · Investigation without stated indication (should escalate)",
        "clinician": {"name": "Dr Elena Fischer", "role": "consultant"},
        "note": (
            "Hepatology clinic 05/09/2026. 45F, known fatty liver disease, LFTs stable. "
            "Discussed lifestyle measures.\n\n"
            "Plan: liver biopsy. Repeat LFTs. Follow up in 4 weeks."
        ),
    },
    "D_timing": {
        "patient_id": "P004",
        "label": "D · Results not back before appointment (should escalate)",
        "clinician": {"name": "Dr Elena Fischer", "role": "consultant"},
        "note": (
            "Respiratory clinic 05/09/2026. 71M, 2.4 cm spiculated right upper lobe nodule on CT, "
            "PET-avid, no nodal disease. Performance status 1. Discussed at MDT; tissue diagnosis needed "
            "before treatment decision.\n\n"
            "Plan: CT-guided lung biopsy of the RUL nodule to obtain histology. See in clinic in 2 weeks "
            "with the histology result to discuss treatment options. I will review him myself."
        ),
    },
}

MOCK_PLANS = {
    "A_routine": ActionPlan(
        investigations=[
            Investigation(
                name="MRI abdomen with contrast", category="imaging",
                reason="Characterise 3.2 cm indeterminate left renal lesion seen on ultrasound",
                urgency="routine",
                evidence="MRI abdomen with contrast to characterise the left renal lesion",
            ),
            Investigation(
                name="U&E and eGFR", category="bloods",
                reason="Borderline creatinine (108); required before contrast MRI",
                urgency="routine",
                evidence="Repeat U&E and eGFR before the MRI given the borderline creatinine",
            ),
        ],
        follow_up=FollowUp(
            interval_weeks=6, interval_candidates_weeks=[6], reviewer_role="consultant",
            purpose="Review MRI and renal function results; consultant opinion on lesion",
            evidence="Follow up in clinic in 6 weeks with the results - please book with Mr Hollis (consultant)",
        ),
        ambiguities=[],
    ),
    "B_conflict": ActionPlan(
        investigations=[
            Investigation(
                name="CT chest with contrast", category="imaging",
                reason="Further evaluate possible right upper lobe opacity on CXR in ex-smoker with 8-week cough",
                urgency="routine",
                evidence="CT chest with contrast to further evaluate the RUL opacity",
            ),
            Investigation(name="FBC", category="bloods", reason="Baseline bloods for persistent cough",
                          urgency="routine", evidence="Bloods today: FBC, CRP."),
            Investigation(name="CRP", category="bloods", reason="Baseline bloods for persistent cough",
                          urgency="routine", evidence="Bloods today: FBC, CRP."),
        ],
        follow_up=FollowUp(
            interval_weeks=None, interval_candidates_weeks=[2, 12], reviewer_role="registrar",
            purpose="Discuss CT result",
            evidence="See in clinic in 2 weeks to discuss ... review in 3 months with the CT result",
        ),
        ambiguities=["Note states both a 2-week and a 3-month follow-up interval."],
    ),
    "C_missing_reason": ActionPlan(
        investigations=[
            Investigation(name="Liver biopsy", category="biopsy", reason=None, urgency="routine",
                          evidence="Plan: liver biopsy."),
            Investigation(name="LFTs", category="bloods", reason="Monitoring of known fatty liver disease",
                          urgency="routine", evidence="Repeat LFTs."),
        ],
        follow_up=FollowUp(interval_weeks=4, interval_candidates_weeks=[4], reviewer_role=None,
                           purpose="Review results", evidence="Follow up in 4 weeks."),
        ambiguities=["No indication is given for the liver biopsy."],
    ),
}

MOCK_PLANS["D_timing"] = ActionPlan(
    investigations=[
        Investigation(
            name="CT-guided lung biopsy (RUL nodule)", category="biopsy",
            reason="Tissue diagnosis of 2.4 cm PET-avid spiculated RUL nodule prior to treatment decision",
            urgency="urgent",
            evidence="CT-guided lung biopsy of the RUL nodule to obtain histology",
        ),
    ],
    follow_up=FollowUp(
        interval_weeks=2, interval_candidates_weeks=[2], reviewer_role="consultant",
        purpose="Discuss histology result and treatment options",
        evidence="See in clinic in 2 weeks with the histology result ... I will review him myself",
    ),
    ambiguities=[],
)

# Canned result text used by the mock results feed, keyed by category.
MOCK_RESULTS = {
    "imaging": "Report available. Findings documented; see full report in PACS. [synthetic]",
    "bloods": "Results within reference ranges except where flagged. [synthetic]",
    "biopsy": "Histology report issued. [synthetic]",
    "other": "Result received. [synthetic]",
}
