# Evaluation

Write the test cases before the code. Aim for 5–10 gold cases; a demo that runs them live beats a slide.

## Gold test cases
| ID | Description | Type (normal / edge / ambiguous) | Expected outcome |
|----|-------------|----------------------------------|------------------|
| G1 |             | normal                           |                  |
| G2 |             | normal                           |                  |
| G3 |             | edge                             |                  |
| G4 |             | ambiguous                        |                  |
- [ ] Location of test inputs (e.g. `tests/cases/`):
- [ ] All cases use synthetic data only

## Expected structured outputs
- [ ] Output schema (JSON / fields):
- [ ] Required vs optional fields:
- [ ] Allowed values / code lists:
- [ ] Example of a correct output:

## Normal cases
- [ ] Typical, complete input → correct output, no escalation
- [ ] Variation in phrasing / format still handled

## Edge cases
- [ ] Missing fields
- [ ] Very long / very short input
- [ ] Unusual formatting (tables, lists, abbreviations)
- [ ] Multiple items where one expected (or vice versa)

## Ambiguous / conflicting cases
- [ ] Contradictory information within the input
- [ ] Information that could map to more than one category
- [ ] Input outside intended scope
- [ ] Expected behaviour: flag, don't guess

## Escalation criteria
- [ ] Confidence below threshold:
- [ ] Any required field missing:
- [ ] Any conflict detected:
- [ ] Any safety-relevant content (allergies, red flags, safeguarding):
- [ ] What "escalate" means in the UI:

## Metrics
| Metric | Definition | Baseline | Result |
|--------|------------|----------|--------|
| Accuracy on gold cases |  |  |  |
| Escalation rate (should escalate / did escalate) |  |  |  |
| False confident outputs (worst case) |  |  |  |
| Time per case (human vs assisted) |  |  |  |
- [ ] How results are captured (script / table / screenshot):

## Known limitations
- [ ] What we didn't test:
- [ ] What we'd do next:
