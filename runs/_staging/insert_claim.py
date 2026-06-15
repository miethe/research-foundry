#!/usr/bin/env python3
"""Insert clm_inf12 (executive-summary framing claim) before unresolved_questions in the ledger."""
import sys

LEDGER = "runs/rf_run_20260614_what_evidence_grounded_acceptance_test_suites/claims/claim_ledger.yaml"

new_claim = """- claim_id: clm_inf12
  text: This memo specifies a deterministic, evidence-grounded quality-assurance harness for KnitWit's
    two flagship capabilities - Pattern to 3D visualization and 3D Object to crochet pattern generation
    - and traces each acceptance signal to the amigurumi-generation and pattern-representation literature.
  materiality: material
  claim_type: comparative
  status: inference
  confidence: high
  sources: []
  inference_basis:
    from_claims:
    - clm_016
    - clm_017
    - clm_018
    - clm_020
    - clm_inf01
    reasoning_summary: The KnitWit plan defines the two flagship capabilities and their acceptance criteria
      - the 3D visualizer (clm_017), the inverse pattern generator (clm_018, clm_020), and the Crochet IR
      validation rules (clm_016) - and the synthesis (clm_inf01) traces those acceptance signals to the
      amigurumi-generation/pattern-representation literature; this sentence is the scope framing over that
      mapping.
  report_locations: []
  reviewer_notes: ''
"""

with open(LEDGER, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
inserted = False
for line in lines:
    if line.rstrip("\n") == "unresolved_questions: []" and not inserted:
        out.append(new_claim)
        inserted = True
    out.append(line)

if not inserted:
    sys.exit("FAIL: unresolved_questions anchor not found")

with open("runs/_staging/claim_ledger.yaml", "w", encoding="utf-8") as f:
    f.writelines(out)

print("OK: wrote runs/_staging/claim_ledger.yaml with clm_inf12 inserted")
