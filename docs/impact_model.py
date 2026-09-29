"""PlugPoint impact model: minutes saved per patient / clinic / week / trust / England.

Every number used in docs/impact.md comes out of this script, so the
assumptions can be challenged and re-run:

    python docs/impact_model.py

SOURCED inputs are marked with their source. ASSUMPTIONS are ours: they
should be checked against time-and-motion data from a real clinic before
any business case relies on them.
"""

# ---------------------------------------------------------------- sourced inputs
# NHS England, Hospital Outpatient Activity 2025-26 (published 24 Sep 2026)
ATTENDED_APPTS_ENGLAND = 116_900_000
# NHS Oversight Framework segmentation, Q2 2025/26: 134 acute trusts ranked
ACUTE_TRUSTS = 134
# PSSRU/CHE Unit Costs of Health and Social Care 2024, cost per working hour
# (2023/24 prices, excluding qualifications)
COST_PER_HOUR = {
    "consultant": 121,   # Table 11.3.2, Consultant: medical
    "registrar": 56,     # Table 11.3.2, Registrar
    "band4": 38,         # Table 11.1.2, hospital-based staff, AfC Band 4 (medical secretary proxy)
}

# ------------------------------------------------------------------ assumptions
# Share of attended appointments that end with a post-clinic action plan
# (at least one investigation and/or a follow-up to book and track).
SHARE_WITH_PLAN = 0.5
PATIENTS_PER_CLINIC = 12
CLINICS_PER_CONSULTANT_WEEK = 3
ILLUSTRATIVE_TRUST_ATTENDANCES = 500_000   # a mid-sized acute trust

# Minutes per patient-with-a-plan: (today, with PlugPoint).
# Today's steps follow docs/problem.md; "with PlugPoint" keeps the clinician's
# review-and-approve step and the human handling of exceptions/alerts.
CLINICIAN_STEPS = {
    "request each investigation in order comms, retyping the indication": (3.0, 0.0),
    "email/dictate booking instructions to the secretary":                 (1.0, 0.0),
    "remember, check and chase results before the follow-up":               (2.0, 0.5),
    "review and approve the extracted plan":                                (0.0, 1.0),
}
SECRETARY_STEPS = {
    "read instructions, find the right clinician's slot, book in PAS": (4.0, 0.0),
    "inform the patient of what happens next":                          (1.0, 0.0),
    "pre-clinic check that results are back; chase or rebook":          (3.0, 1.0),
}

# Low / central / high multipliers on the minutes saved.
SCENARIOS = {"low": 0.5, "central": 1.0, "high": 1.5}


def saved(steps):
    return sum(before - after for before, after in steps.values())


def main():
    clin = saved(CLINICIAN_STEPS)
    sec = saved(SECRETARY_STEPS)
    plans_per_clinic = PATIENTS_PER_CLINIC * SHARE_WITH_PLAN
    rate_c, rate_s = COST_PER_HOUR["consultant"], COST_PER_HOUR["band4"]

    print(f"Per patient with a plan (central): clinician {clin:.1f} min, secretary {sec:.1f} min, total {clin + sec:.1f} min")
    print(f"  value: clinician £{clin * rate_c / 60:.2f} (consultant) / £{clin * COST_PER_HOUR['registrar'] / 60:.2f} (registrar),"
          f" secretary £{sec * rate_s / 60:.2f}")
    print(f"Per clinic ({PATIENTS_PER_CLINIC} patients, {plans_per_clinic:.0f} with a plan): "
          f"clinician {clin * plans_per_clinic:.0f} min, secretary {sec * plans_per_clinic:.0f} min")
    wk = plans_per_clinic * CLINICS_PER_CONSULTANT_WEEK
    print(f"Per consultant-week ({CLINICS_PER_CONSULTANT_WEEK} clinics): clinician {clin * wk / 60:.1f} h, secretary {sec * wk / 60:.1f} h")
    print()

    def block(label, attendances):
        plans = attendances * SHARE_WITH_PLAN
        print(f"{label}: {attendances:,.0f} attended appointments -> {plans:,.0f} action plans/year")
        for name, m in SCENARIOS.items():
            ch = plans * clin * m / 60
            sh = plans * sec * m / 60
            val = ch * rate_c + sh * rate_s
            print(f"  {name:>7}: clinician {ch:,.0f} h (~{ch / 2073:,.1f} consultant WTE at 2,073 h/yr)"
                  f", secretary {sh:,.0f} h, time value £{val / 1e6:,.2f}m")
        return plans

    block("Illustrative trust", ILLUSTRATIVE_TRUST_ATTENDANCES)
    print()
    plans_eng = block("England", ATTENDED_APPTS_ENGLAND)
    print(f"  average per acute trust (upper bound; national total includes non-acute providers):"
          f" {ATTENDED_APPTS_ENGLAND / ACUTE_TRUSTS:,.0f} attendances")
    print()
    for price in (0.50, 1.00, 2.00):
        print(f"Market at £{price:.2f} per actioned plan: £{plans_eng * price / 1e6:,.0f}m/year (England)")


if __name__ == "__main__":
    main()
