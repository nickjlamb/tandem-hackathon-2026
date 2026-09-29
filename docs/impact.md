# Impact: the commercial case for a trust

> **For a trust executive:** PlugPoint removes about **11½ minutes of admin per outpatient action plan**: about 4½ of clinician time and 7 of secretary time. For a mid-sized acute trust (500,000 attended appointments a year), that is roughly **19,000 clinician hours and 29,000 secretary hours a year**. At PSSRU unit costs that time is worth about **£3.4m a year**, with a range of £1.7m–£5.1m. It also turns the "patient lost to follow-up" failure, which national investigations say relies on staff vigilance, into a tracked loop with a named owner and escalation.

All figures come from [`impact_model.py`](impact_model.py) (`python docs/impact_model.py`). Sourced inputs are cited below. The assumptions are labelled as ours and are there to be challenged.

## 1. Minutes saved per patient

We count one **action plan** per attended appointment that ends with at least one investigation to request and/or a follow-up to book and track. The steps come from the manual chain in [`problem.md`](problem.md).

| Step | Who | Today (min) | With PlugPoint (min) |
|---|---|---:|---:|
| Request each investigation in order comms, retyping the indication | Clinician | 3.0 | 0 |
| Email or dictate booking instructions to the secretary | Clinician | 1.0 | 0 |
| Remember, check and chase results before the follow-up | Clinician | 2.0 | 0.5 (act on alerts only) |
| Review and approve the extracted plan | Clinician | 0 | 1.0 |
| Read instructions, find the right clinician's slot, book in PAS | Secretary | 4.0 | 0 |
| Tell the patient what happens next | Secretary | 1.0 | 0 |
| Pre-clinic check that results are back; chase or rebook | Secretary | 3.0 | 1.0 (exceptions only) |
| **Saved per plan** | | | **Clinician 4.5 · Secretary 7.0 · Total 11.5** |

The minute values are **our estimates**. We built them with a clinician on the team, but they have not been measured. A two-clinic time-and-motion study is the first thing a pilot should do (see §6).

**What this time is worth per plan:** £9.07 of consultant time (£4.20 at registrar rates) plus £4.43 of Band 4 secretary time.

## 2. Per clinic and per week

| Scale | Assumption | Clinician time saved | Secretary time saved |
|---|---|---:|---:|
| One clinic | 12 patients, half with an action plan | 27 min | 42 min |
| One consultant-week | 3 clinics | 1.4 h | 2.1 h |

A consultant gets back about one extra patient slot a week. Their secretary gets back about a quarter of a day.

## 3. Per trust and across England

Assumes **50% of attended appointments** produce an action plan. Scenarios scale the minutes saved by ×0.5 (low), ×1 (central) and ×1.5 (high). Time value uses consultant rates for clinician time, so trusts where registrars do most of this work should read the lower end.

| | Action plans / year | Clinician hours saved (central) | Secretary hours saved (central) | Time value, low – **central** – high |
|---|---:|---:|---:|---:|
| Illustrative acute trust (500k attended appts) | 250,000 | 18,750 (≈ 9 consultant WTE) | 29,167 | £1.7m – **£3.4m** – £5.1m |
| England (116.9m attended appts, 2025-26) | 58.5m | 4.4m (≈ 2,100 consultant WTE) | 6.8m | £395m – **£790m** – £1,184m |

**Caveat:** this is **time released, not cash saved**. A trust does not bank it unless it turns it into extra clinic capacity (fewer waiting-list initiative sessions, fewer agency admin hours) or avoided cost. We think the honest pitch is capacity: roughly one extra patient slot per consultant per week.

## 4. The patient-safety case

This is the benefit that falls on the organisation that would pay.

- **The national evidence says the current safety net is people remembering.** HSSIB's investigation into [outpatient appointments intended but not booked](https://www.hssib.org.uk/patient-safety-investigations/outpatient-appointments-intended-but-not-booked-after-inpatient-stays/investigation-report/) (2021) found that assurance "often relies on the vigilance and diligence of staff". It recommended national standards that use "technology and automation … so that there is less reliance on staff vigilance". That investigation looked at follow-ups after inpatient stays, but the failure mode is the same one PlugPoint targets after clinic. The review it cites of 145,234 ophthalmology episodes found that 54.8% of lost-to-follow-up cases were caused by administrative processes.
- **Results that nobody acts on are a known harm route.** HSSIB's report on [failures to communicate or follow up significant radiology findings](https://www.hssib.org.uk/patient-safety-investigations/failures-in-communication-or-follow-up-of-unexpected-significant-radiological-findings/investigation-report/) (2022) found "very little assurance that the actions indicated by the findings have been taken". PlugPoint's tracker gives every result an owner and an expected-by date, and escalates unactioned alerts from the owner to the consultant to the service lead.
- **The cost of harm is large.** NHS Resolution paid [£3.1bn in clinical negligence claims in 2024/25](https://resolution.nhs.uk/2025/07/17/nhs-resolution-resolves-record-numbers-of-compensation-claims-through-collaboration/), and the annual cost of harm for CNST is £4.6bn. We have not found a published figure for the share caused by lost follow-up. We have not attached a number, and we don't think anyone should until a trust's own incident data supplies one. Each prevented serious incident also avoids a patient safety investigation (PSII/PSIRF), a wasted clinic slot and possible litigation.

The safety design is what makes this credible to a clinical safety officer. There is one constrained AI call, deterministic rules for everything consequential, and mandatory clinician approval before anything is ordered or booked. Every step is audited and labelled AI, rule, human or API. The gold set shows that **0 escalation cases were auto-actioned** in every run so far (see [`evaluation.md`](evaluation.md)).

## 5. Market sizing (England)

| | Basis | Size |
|---|---|---|
| Buyers | Acute trusts ([134 ranked in the NHS Oversight Framework, Q2 2025/26](https://www.imperial.nhs.uk/about-us/how-we-are-doing/nhs-oversight-framework-rankings)) | 134 trusts |
| Volume | 116.9m attended outpatient appointments × 50% with a plan | ~58m action plans / year |
| Revenue pool | per actioned plan at £0.50 / **£1** / £2 | £29m / **£58m** / £117m a year |

**Price sense-check:** at £1 per plan, a mid-sized trust pays about £250k a year for about £3.4m of released time (central), which is a 13× return. Even the low scenario covers the fee six times over. Pricing per plan (rather than per seat) matches cost to use.

**Why this fits Tandem:** PlugPoint's input is the consultation note Tandem already produces. For a trust already using Tandem, "note → tracked action plan" is an add-on to an existing contract, not a new procurement. The patient-safety benefit also gives that add-on a budget line (patient safety or outpatient transformation) separate from the ambient-scribe business case.

## 6. What would make these numbers real

1. **Time-and-motion study in two clinics** (one consultant-led, one registrar-heavy): measure today's minutes per step, then re-measure with PlugPoint in shadow mode.
2. **Baseline the safety metric:** the trust's own incidents coded as lost to follow-up or result not actioned over 24 months, plus an audit of how many planned follow-ups were never booked.
3. **Measure the share of attendances with an action plan** by specialty. The 50% figure is a placeholder.
4. **Track in production:** plans actioned without edits, time from approval to booking, alerts raised and resolved, and loops closed before the follow-up appointment.

## Sources

- NHS England, [Hospital Outpatient Activity 2025-26](https://digital.nhs.uk/data-and-information/publications/statistical/hospital-outpatient-activity/2025-26) (published 24 Sep 2026): 150.3m appointments, 116.9m attended.
- Jones K.C. et al. (2025), [*Unit Costs of Health and Social Care 2024 Manual*](https://kar.kent.ac.uk/109563/), PSSRU (Kent) & CHE (York). Cost per working hour, 2023/24 prices, excluding qualifications: consultant (medical) £121, registrar £56 (Table 11.3.2); hospital Band 4 £38 (Table 11.1.2), used as a proxy for a medical secretary.
- HSSIB (2021), [Outpatient appointments intended but not booked after inpatient stays](https://www.hssib.org.uk/patient-safety-investigations/outpatient-appointments-intended-but-not-booked-after-inpatient-stays/investigation-report/).
- HSSIB (2022), [Failures in communication or follow-up of unexpected significant radiological findings](https://www.hssib.org.uk/patient-safety-investigations/failures-in-communication-or-follow-up-of-unexpected-significant-radiological-findings/investigation-report/).
- NHS Resolution (2025), [Annual report and accounts 2024/25 press release](https://resolution.nhs.uk/2025/07/17/nhs-resolution-resolves-record-numbers-of-compensation-claims-through-collaboration/).
- Imperial College Healthcare NHS Trust, [NHS Oversight Framework rankings](https://www.imperial.nhs.uk/about-us/how-we-are-doing/nhs-oversight-framework-rankings) (Q2 2025/26: 134 acute trusts).
