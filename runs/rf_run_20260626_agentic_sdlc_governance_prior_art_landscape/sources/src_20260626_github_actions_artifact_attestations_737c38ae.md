---
schema_version: '0.1'
type: source_card
source_card_id: src_20260626_github_actions_artifact_attestations_737c38ae
created_at: '2026-06-26T10:18:27-04:00'
created_by_agent: rf_source_carder
sensitivity: personal
source:
  title: GitHub Actions artifact attestations
  source_type: official_doc
  locator:
    url: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds
    file_path: null
    doi: null
    repo: null
  authors: []
  publisher: null
  published_at: null
  accessed_at: '2026-06-26T10:18:27-04:00'
  version: null
trust:
  source_rank: unknown
  reliability_notes: Ingested deterministically; not yet reliability-rated.
  known_limitations: []
  conflicts_with: []
usage:
  allowed_for_public_output: false
  allowed_for_work_output: true
  allowed_for_personal_meatywiki: true
  citation_required: true
  quote_limit_notes: Quote short excerpts only; cite the source.
extracted_points:
- evidence_id: ev_001
  locator: para/1
  summary: 'Using artifact attestations to establish provenance for builds - GitHub Docs Skip to main
    content GitHub Docs Version: Free, Pro, &amp; Team Search or ask Copilot Search or ask Copilot Select
    language'
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_002
  locator: para/2
  summary: Ensure you have the appropriate permissions configured in your workflow.
  quote: "Ensure you have the appropriate permissions configured in your workflow. \n Include a step in\
    \ your workflow that uses the   attest  action ."
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_003
  locator: para/3
  summary: When you run your updated workflows, they will build your artifacts and generate an artifact
    attestation that establishes build provenance.
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_004
  locator: para/4
  summary: In the workflow that builds the binary you would like to attest, add the following permissions.
  quote: "In the workflow that builds the binary you would like to attest, add the following permissions.\
    \ \n   permissions: \n   id-token:   write \n   contents:   read \n   attestations:   write"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_005
  locator: para/5
  summary: After the step where the binary has been built, add the following step.
  quote: "After the step where the binary has been built, add the following step. \n   -   name:   Generate\
    \   artifact   attestation \n   uses:   actions/attest@v4 \n   with: \n     subject-path:   'PATH/TO/ARTIFACT'"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_006
  locator: para/6
  summary: The value of the subject-path parameter should be set to the path to the binary you want to
    attest.
  quote: The value of the  subject-path  parameter should be set to the path to the binary you want to
    attest.
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_007
  locator: para/7
  summary: Generating build provenance for container images
  quote: Generating build provenance for container images
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_008
  locator: para/8
  summary: In the workflow that builds the container image you would like to attest, add the following
    permissions.
  quote: "In the workflow that builds the container image you would like to attest, add the following\
    \ permissions. \n   permissions: \n   id-token:   write \n   contents:   read \n   attestations: \
    \  write \n   packages:   write"
  supports_potential_claims:
  - clm_pending
---

# Source Card: GitHub Actions artifact attestations

## Summary

Using artifact attestations to establish provenance for builds - GitHub Docs Skip to main content GitHub Docs Version: Free, Pro, &amp; Team Search or ask Copilot Search or ask Copilot Select language

## Key evidence

- (ev_001) Using artifact attestations to establish provenance for builds - GitHub Docs Skip to main content GitHub Docs Version: Free, Pro, &amp; Team Search or ask Copilot Search or ask Copilot Select language
- (ev_002) Ensure you have the appropriate permissions configured in your workflow.
- (ev_003) When you run your updated workflows, they will build your artifacts and generate an artifact attestation that establishes build provenance.
- (ev_004) In the workflow that builds the binary you would like to attest, add the following permissions.
- (ev_005) After the step where the binary has been built, add the following step.
- (ev_006) The value of the subject-path parameter should be set to the path to the binary you want to attest.
- (ev_007) Generating build provenance for container images
- (ev_008) In the workflow that builds the container image you would like to attest, add the following permissions.

## Limitations

- None recorded.

## Related source cards
