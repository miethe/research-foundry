---
schema_version: 2
doc_type: audit
gate_id: DEF-6
feature_slug: source-metadata-propagation
status: complete
created: 2026-08-06
retrieval_date: 2026-08-06
verified_by: agent
closes_gate: false
---

# DEF-6 — Live ToS Re-Verification: Semantic Scholar / NCBI

**Retrieval date for every quotation below: 2026-08-06.**

## What this document is, and what it is not

This is the verification record DEF-6 asks for: the licensing claims in
[`risk-findings.md`](./risk-findings.md) §"Third-Party Terms" were stated from general domain
knowledge of these programs' public policies and had never been checked against the live pages.
They now have been, and two of them did not survive.

**This record does not and cannot close DEF-6.** `config/clearance_gates.yaml` records gate closure
as human-only by exclusion, and `services/governance.py` rule 9 (`no_agent_cleared_clearance_taint`)
blocks any agent-writable path from proposing `state: closed`. It was written by an agent. It is
**not legal advice** — it is a record of what the vendors' own pages said on the retrieval date,
assembled so that a human with standing can make the determination without re-doing the reading.
See "Closing DEF-6" at the end.

DEF-6's stated scope is Semantic Scholar and NCBI only. **The Crossref and OpenAlex CC0 rows were
not re-verified in this pass** and remain general-domain-knowledge claims.

## Sources consulted

| # | URL | Page's own last-updated date | Yield |
|---|---|---|---|
| S1 | `https://www.semanticscholar.org/product/api/license` — S2 API License Agreement | not stated | **Decisive** — the per-dataset deferral clause |
| S2 | `https://www.semanticscholar.org/product/api` | not stated | Rate limits; links only, no license text |
| S3 | `https://allenai.org/terms` — AI2 Terms of Use | effective 2024-09-25 | Defers to S1 |
| S4 | `https://www.semanticscholar.org/product/api/tutorial` | not stated | No license text |
| S5 | `https://api.semanticscholar.org/api-docs/datasets` | not stated | No per-dataset license listing reachable |
| N1 | `https://www.ncbi.nlm.nih.gov/home/about/policies/` — NCBI Website and Data Usage Policies | not stated | Public-domain status; third-party-copyright carve-out; scripting guidance |
| N2 | `https://www.ncbi.nlm.nih.gov/books/NBK25497/` — E-utilities Usage Guidelines | 2022-11-17 | Rate limits; bulk guidance; copyright notice duty |
| N3 | `https://www.nlm.nih.gov/web_policies.html` — NLM Copyright and Reuse | 2024-12-02 | Public domain; attribution requested not required |
| N4 | `https://www.nlm.nih.gov/databases/download/terms_and_conditions.html` — NLM data download terms | 2019-05-21 | **Affirmative redistribution obligations** |

`https://api.semanticscholar.org/` 301-redirects to S2.

## Claim A — Semantic Scholar (S2AG)

> **Prior claim (risk-findings.md):** "S2AG's own terms describe the aggregated dataset under
> **ODC-BY** … redistribution is permitted **with attribution to Semantic Scholar**, not as CC0."

**Verdict: NOT SUBSTANTIATED. Corrected.** The prior claim asserts a single blanket license. The
license agreement asserts the opposite — that there isn't one.

S1, verbatim:

> "Licensee's use of S2 Data accessed via the API are separately governed by the licenses that
> accompany such S2 Data, such as **CC BY-NC or ODC-BY**"

Three consequences, all material to a redistribution gate:

1. **The license is per-dataset, not per-program.** ODC-BY is one possibility the agreement names,
   not the governing license. "S2AG is ODC-BY" is not a statement the vendor makes anywhere.
2. **`CC BY-NC` is explicitly on the list, and NonCommercial is a restriction ODC-BY does not
   carry.** Any S2 dataset arriving under CC BY-NC cannot be redistributed in a bundle intended for
   commercial use, attribution notwithstanding. The prior row's "conditionally — must carry an
   attribution notice" understates this to the point of being wrong for that case.
3. **No public page enumerates which dataset carries which license.** S2, S4, and S5 carry no
   license text; S3 defers to S1; S1 defers to the datasets. The mapping is not publicly
   determinable, so it must be captured **at acquisition time, per record**, from whatever license
   accompanies the payload.

Two further provisions from S1 that the prior row omitted:

- The affirmative attribution obligation is real and is on the *licensee*: "Licensee will include an
  attribution to 'Semantic Scholar' on its website or in any published materials for contributions
  from S2 through Licensee's use of the API and/or S2 Data."
- The prohibition clause binds the **API**, not derived data: "repackage, sell, rent, lease, lend,
  distribute, or sublicense the API". No competing-product clause appears.

Informational (S2): unauthenticated callers share a 1000-requests-per-second pool; an API key's
"introductory rate limit … is 1 RPS on all endpoints" — i.e. a key buys reliability, not throughput,
at the introductory tier.

**Bearing on DEF-3/DEF-6:** this *strengthens* the existing architecture rather than undermining it.
`license_basis` per assertion (risk-findings.md §"Concrete Migration Path" item 3) is not
belt-and-braces here — it is the only mechanism that can carry a per-dataset license whose value is
unknowable in advance. A single hardcoded `"ODC-BY"` default for the Semantic Scholar adapter would
be an incorrect assertion of fact.

## Claim B — PubMed / NCBI E-utilities

> **Prior claim (risk-findings.md):** "Governed by NCBI's Data Usage Policies, not a named open-data
> license. … NCBI explicitly disallows systematic bulk scraping/redistribution as a substitute
> product, and API-key/rate limits apply (≥3 req/s requires a key)."

**Verdict: CONFIRMED in its core, with one clause unsupported, one imprecision, and two omissions.**

### Confirmed — no named open-data license; the mechanism is public domain

N3: "Works produced by the U.S. government are not subject to copyright protection in the United
States." N1: "Information that is created by or for the US government on this site is within the
public domain." For molecular data N1 adds: "NCBI itself places no restrictions on the use or
distribution of the data contained therein."

So the prior row is right that no open-data license is involved — but the reason is stronger than
"not a license": NCBI-generated content is uncopyrightable, which is a wider grant than ODC-BY or
CC0 would be. Attribution is **requested, not required** — N3 recommends "Courtesy of the National
Library of Medicine" or "Source: National Library of Medicine".

N1 also disclaims authority to speak for submitters: "NCBI cannot provide comment or unrestricted
permission concerning the use, copying, or distribution of the information."

### Unsupported — the "substitute product" prohibition

**No live page states it.** Nothing in N1, N2, N3, or N4 prohibits systematic retrieval, scraping,
or building a substitute or competing product. What exists is *operational courtesy guidance*, not a
prohibition:

- N1: "Run retrieval scripts on weekends or between 9 pm and 5 am Eastern Time weekdays for any
  series of more than 100 requests."
- N2: rather than fetching records one at a time, "use the Entrez History to upload and/or retrieve
  these records in batches"; for large PubMed projects, "download a local copy of the database" from
  the NLM download site.

NCBI's posture on bulk access is therefore *"use the bulk channel we provide"*, not *"don't do bulk
access"*. The prior row's phrasing invents a restriction the vendor does not impose. Delete it.

### Imprecise — the rate limits

Not "≥3 req/s requires a key". N2, verbatim: without a key, "no more than three URL requests per
second"; with a key, "up to 10 requests per second by default". N1 states the same 3/s floor. Both
`tool` (a space-free string identifying the software) and `email` (the developer's address) are the
identification parameters NCBI requires for a registered caller.

### Omission 1 — third-party copyright *inside* the databases is the actual constraint

The prior row's conclusion ("no blanket redistribution right") is directionally correct but
attributes it to the wrong party. The constraint is upstream publisher copyright, not NCBI policy:

- N1 flags PubMed Central, Bookshelf, OMIM, and PubChem as containing third-party copyrighted
  material requiring compliance with the original holders' terms.
- N2: abstracts "may incorporate material that may be protected by U.S. and foreign copyright laws"
  and reproduction beyond fair use requires "written permission of the copyright owners".
- N3: reproducing such material "beyond that allowed by fair use requires written permission of the
  copyright holders", and the user bears responsibility for determining copyright status.

**This is the live risk for RF specifically**, because the thing RF redistributes in a bundle is
frequently an *abstract or a quoted passage* — precisely the copyrighted layer — not the
public-domain bibliographic skeleton (PMID, title, authors, dates), which is unencumbered.
The redistribution question therefore splits by field, not by source. The current table has no row
shape that can express that.

### Omission 2 — NLM bulk-download terms impose affirmative duties

N4 is a terms-and-conditions page the prior analysis never reached, and it attaches obligations to
redistribution rather than merely permitting it:

- **Staleness disclosure:** "maintain the most current version of all distributed data, or make
  known in a clear and conspicuous manner that the products/services/applications do not reflect the
  most current/accurate data available from NLM."
- **Required acknowledgement:** "acknowledge NLM as the source of the data by including the phrase
  'Courtesy of the U.S. National Library of Medicine' in a clear and conspicuous manner" — note this
  is *required* here, unlike N3's merely-requested attribution for general content.
- **No implied endorsement:** "not indicate or imply that NLM has endorsed its
  products/services/applications."
- "No charges, usage fees or royalties are paid to NLM for this data."

The staleness-disclosure duty is a direct hit on risk-findings.md §"Staleness Invariant": for
NLM-derived data, disclosing staleness is not merely an internal correctness property, it is a term
of use. A bundle carrying a stale `observed_at` without conspicuous disclosure is out of compliance
with N4, independent of whether RF considers it correct.

## Net effect on the gate

| | Prior table's posture | Live-verified posture |
|---|---|---|
| Semantic Scholar | ODC-BY; redistributable with attribution | **Per-dataset, possibly CC BY-NC**; blanket redistribution cannot be asserted; capture license per record |
| NCBI — bibliographic fields | usable per-record, no blanket redistribution right | **Public domain, unencumbered**; attribution requested |
| NCBI — abstracts / passages | (not distinguished) | **Third-party copyright; fair use or written permission** |
| NCBI — bulk-derived data | (not addressed) | Redistributable under **four affirmative N4 duties**, incl. staleness disclosure |

Neither finding argues for opening DEF-6's `redistribution` scope. Claim A got *less* permissive
(NonCommercial is live and unresolvable from public pages). Claim B got *more* permissive for
bibliographic metadata and *sharper* for abstracts. A human with standing may reasonably conclude
that redistribution stays blocked pending the per-dataset license capture Claim A requires.

## Closing DEF-6

Requires a human with standing. The edit is to `config/clearance_gates.yaml`, gate `DEF-6`:

```yaml
  - gate_id: DEF-6
    blocks_scope: redistribution
    state: open          # ← a human may set this to `closed` if satisfied; rule 9 blocks agents
    closed_by: docs/project_plans/exploration/source-metadata-propagation/spikes/def-6-tos-verification-2026-08-06.md
```

Before closing, note the two findings above are *corrections*, not clearances — Claim A leaves the
Semantic Scholar redistribution license genuinely undetermined from public sources. Closing DEF-6
on this record alone would record "ToS re-verified" as true (it is) while leaving the redistribution
question it was gating still open on the merits. Resolving that likely means either reading the
license accompanying each S2 dataset payload at acquisition, or asking Semantic Scholar directly.

## Re-verification cadence

Every page above is a live document and three carry dates older than this record. AI2's terms already
turned over on
2024-09-25. N4 (2019-05-21) and N2 (2022-11-17) have been stable for years; S1 and S3 are the
volatile pair. Re-check S1 before any release that widens redistribution scope.
