# External Reviewer Integration

Use this reference when a council run includes reviewers outside the local Claude Code session.

## When To Add External Reviewers

External reviewers are useful when:

- A PR needs a separate code-review perspective.
- A model/provider specializes in the target domain.
- A platform owns context not available locally.
- Cross-provider disagreement is part of the review objective.

Keep the reviewer set small. External results increase adjudication work and should be justified by the objective.

## Inputs

Give external reviewers the same run contract:

- Target.
- Objective.
- Constraints.
- Required finding schema.
- Evidence expectations.
- Excluded paths or prohibited actions.

Do not include other reviewers' conclusions unless the task is explicitly a challenge or adjudication pass.

## Normalization

Normalize external outputs into `schemas/finding.schema.json` before adjudication.

Preserve:

- Provider and model metadata when known.
- Original source locators.
- Confidence and uncertainty.
- Disagreement or caveats from the external reviewer.

Do not promote an external finding to accepted status until the adjudicator verifies evidence and validation path.
