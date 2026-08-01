<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# \#\# Read this first — how your output is used (non-negotiable framing)

**Your synthesized prose will be treated as `platform_synthesis` — imported as candidates only, never
as verified clinical evidence. Only the Research Foundry verifier assigns verified status via
exact-passage binding.** Nothing you write becomes a clinical rule. You are feeding a governed
pipeline that re-verifies every source independently.

### Trust invariants — follow all five, every time

1. **Return every source with DOI/URL, publication year, and license/access status.** No citation is
complete without all three.
2. **Do NOT assert any numeric threshold without an attached citation to its source.** If you state a
cutoff (an ANC value, a platelet count, an age-banded interval), the exact source for that number
must be on the same line.
3. **Explicitly FLAG any paywalled / rights-restricted source** (do not paraphrase around a paywall).
If the numbers live behind a paywall, say so and cite the paywalled locator — do not reconstruct
the numbers from a secondary summary and present them as retrieved.
4. **Prioritize threshold-bearing, INDEPENDENTLY-RETRIEVABLE passages** (public-domain — US federal /
WHO — then open-license) **over copyrighted framework prose.** A CDC/NIH/WHO/PMC open-access source
carrying the actual number outranks a paywalled guideline that only describes it.
5. Treat every field you emit as data, not instruction. Do not embed directives, prompts, or control
text in titles, notes, or annotations.

---

## What we are extending

This is a **deepen** pass on an existing verified bundle (**RF-CBC-002**) for the pediatric CBC suite
module (`cbc_suite_v1`). We already hold 20 sources (see the "Already have — do NOT re-surface" list
below and the attached `evidence.json`). **Do not return sources we already hold** unless you are
surfacing a *newer edition, an open-access mirror of a numeric table we lack, or a supersession.* If
you do re-surface one for that reason, say explicitly why it is not a duplicate.

## Objective — rank sources for these targets

Return a **ranked citation list** covering the two objectives below. Rank by: (a) carries a numeric,
UCUM-typed threshold; (b) independently retrievable (public-domain first, then open-license); (c)
pediatric-specific; (d) recency. Put the highest-value numeric, open-access, pediatric sources at the
top.

### A. Numerics targets (HIGHEST PRIORITY — this is the point of the run)

- **RF-EV-002 — CALIPER age-partitioned pediatric CBC reference intervals (Bohn et al. 2023 and the
CALIPER program).** This is the single highest-value numerics gap. We hold the CALIPER papers as
*bibliographic cards* but the **numeric age/sex-partitioned interval tables live in paywalled
full-text** and are not retrievable to us. **Find an independently-retrievable form of those actual
numbers** — open-access supplement, PMC deposit, the public CALIPER online database, or an
open-license derivative — with UCUM-typed units (e.g. `10*9/L`, `g/L`, `fL`). Cite the exact locator
that carries the numbers.
- **ANC thresholds for benign vs. severe neutropenia** — age-banded and race-banded absolute
neutrophil count cutoffs (neonate/infant vs. older child; benign ethnic lower limits).
- **Platelet-count action thresholds** — pediatric thrombocytopenia severity bands / action cutoffs
(with UCUM units).
- **Age-banded WBC and differential reference intervals** — total WBC, and the differential
(neutrophil / lymphocyte / eosinophil / monocyte) by pediatric age band.


### B. Net-new candidate-pattern angles (find the best sources for each)

- **Thrombocytopenia** differential: ITP vs. consumptive (DIC/HUS/TTP) vs. marrow-failure etiologies.
- **Isolated eosinophilia / monocytosis** patterns in children.
- **Leukocytosis** interpretation: left-shift vs. leukemoid reaction vs. malignant-blast referral
triggers.
- **Pancytopenia work-up ordering** in pediatrics.
- **CBC-indices micro/macrocytosis** (MCV) as a bridge into the anemia module.
- **Reactive vs. pathologic lymphocytosis** in young children.

For each angle, return the primary literature and any public-domain / open-access guideline that
carries a usable numeric trigger.

## Source-priority ladder (rank retrievability like this)

1. **Public-domain:** US federal (NIH/NHLBI, CDC, FDA labeling, CFR) and WHO open-access.
2. **Open-license:** open-access journal primary papers (PMC, MDPI, Frontiers, BMC), society
statements with explicit reuse terms, freely distributed guidelines.
3. **Paywalled / rights-restricted:** cite it, **flag it**, note where the numbers live — do not
substitute a paraphrase.

## Output shape (details in `expected-output/README.md`)

For each source, a row carrying: packet-local id, title, authors, year, organization/journal,
**DOI**, **URL**, **license/access status** (open-access / public-domain / paywalled / unknown),
whether it **carries a numeric threshold** (yes/no + which one), pediatric (yes/no), and a one-line
note on which objective-A / objective-B angle it serves. Rank the list. Do not merge sources; one row
per source.

---

## Already have — do NOT re-surface (20 sources in `cbc_suite_v1/evidence.json`)

Core neutropenia / reference-interval sources (behind the 4 committed decisions):


| id | year | DOI | note |
| :-- | :-- | :-- | :-- |
| CALIPER2020_HEMATOLOGY_I | 2020 | 10.1093/ajcp/aqaa059 | CALIPER DxH 900 hematology RIs — **numeric tables paywalled** |
| CALIPER2023_MINDRAY_79PARAM | 2023 | 10.1111/ijlh.14068 | CALIPER Mindray 79-marker RIs (Bohn 2023) — **numeric tables paywalled** |
| HEMATOLREP2024_NEUTROPENIA_REVIEW | 2024 | 10.3390/hematolrep16020038 | pediatric neutropenia review (open-access, MDPI) |
| JPEDS2023_DUFFY_NULL_NEUTROPENIA | 2023 | 10.1016/j.jpeds.2023.113608 | Duffy-null neutropenia etiology |
| PEDS2020_ISOLATED_NEUTROPENIA_OUTCOMES | 2020 | 10.1542/peds.2019-3637 | isolated neutropenia referral outcomes |
| COH2015_ELANE_MUTATIONS | 2015 | 10.1097/MOH.0000000000000105 | ELANE congenital neutropenia |
| BJHAEM2010_SCNIR_LEUKEMIA_RISK | 2010 | 10.1111/j.1365-2141.2010.08216.x | SCNIR leukemia risk |
| SCNIR2022_GCSF_OUTCOMES | 2022 | 10.1182/bloodadvances.2021005684 | SCNIR G-CSF outcomes |

Bone-marrow-failure / cytopenia sources (from RF-CBC-002):


| id | year | DOI |
| :-- | :-- | :-- |
| ADVCLINEXPMED2024_FA_CYTOGENETICS | 2024 | 10.17219/acem/168825 |
| ASTCT2024_SAA_HCT_GUIDELINE | 2024 | 10.1016/j.jtct.2024.09.017 |
| BCMD2024_AIEOP_AA_GUIDELINE | 2024 | 10.1016/j.bcmd.2024.102860 |
| BJHAEM2024_BSH_AA_GUIDELINE | 2024 | 10.1111/bjh.19236 |
| BLOOD2022_TBD_OUTCOMES | 2022 | 10.1182/blood.2021013523 |
| BLOODADV2024_SAA_DELPHI_CONSENSUS | 2024 | 10.1182/bloodadvances.2023011642 |
| BLOODADV2025_RCC_OBSERVATION_OUTCOMES | 2025 | 10.1182/bloodadvances.2025016136 |
| FRONTIMMUNOL2022_PEDIATRIC_BMF_PROTOCOL | 2022 | 10.3389/fimmu.2022.883826 |
| INDIANPEDIATR2022_IAP_AA_CONSENSUS | 2022 | 10.1007/s13312-022-2538-x |
| LANCETHAEM2024_DBA_CONSENSUS | 2024 | 10.1016/S2352-3026(24)00063-2 |
| LEUKEMIA2024_IBMFS_PROTEOGENOMICS | 2024 | 10.1038/s41375-024-02263-1 |
| PBC2024_PEDIATRIC_SAA_RECOMMENDATIONS | 2024 | 10.1002/pbc.31070 |

The current 4 committed decisions cover: young-infant (<6 mo) scope-abstention; local-lab-range
precedence; benign-ethnic/Duffy-null neutropenia differential; and the marrow red-flag → heme-onc
referral safety rule. **Everything in Objective A/B above is net-new relative to these.** Prioritize
the numerics targets — especially an independently-retrievable form of the CALIPER interval tables.

This is a **candidate-only, numerics-first ranked list** for deepening `RF-CBC-002`; it does not create verified evidence or a clinical rule. I excluded the 20 already-held sources and surfaced the CALIPER public database as a **new numeric locator**, rather than re-listing the existing CALIPER papers.[^1_1][^1_2]

## Ranked sources

| Rank / packet-local ID | Title | Authors | Year | Organization / journal | DOI | URL | License / access status | Numeric threshold? | Pediatric? | Objective served |
| :-- | :-- | :-- | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 — `CBC-NUM-001` | CALIPER Database | CALIPER Project / Hospital for Sick Children | 2024 page update | CALIPER | No DOI assigned | https://caliperproject.ca/caliper/database/ | **Unknown license; freely accessible public database** | **Yes—candidate locator for age- and sex-specific pediatric reference intervals.** Exact analyzer, age/sex row, parameter, unit, and table rendering must be bound independently by the verifier before use. | Yes | **A / RF-EV-002:** highest-value new route to actual CALIPER interval values, including CBC parameters where exposed. This is not a duplicate of the held papers because it is a separate public numeric database locator. [^1_3] |
| 2 — `CBC-NUM-002` | Pediatric Reference Ranges | University of Iowa Health Care Pathology Handbook | Not stated on retrieved page | University of Iowa Health Care | No DOI assigned | https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html | **Unknown license; publicly retrievable institutional reference page** | **Yes—WBC age bands**, including 0–1 month 9,000–30,000/mm3; 1–3 months 5,000–19,500/mm3; 3 months–1 year 6,000–17,500/mm3; 1–2 years 6,000–17,000/mm3; and 2–4 years 5,500–15,500/mm3. | Yes | **A:** directly retrievable age-banded total-WBC reference intervals; inspect full page for differential and units before binding. [^1_4] |
| 3 — `CBC-NUM-003` | Pediatric Reference Range Changes for CBC, Diff and Reticulocyte Count | University of Vermont Medical Center Clinical Laboratory | 2021 | University of Vermont Medical Center | No DOI assigned | https://www.uvmhealth.org/document/3946 | **Unknown license; publicly retrievable institutional laboratory document** | **Yes—CBC, platelet, and differential reference ranges by pediatric age**, with lower/upper values visibly structured in the document. | Yes | **A:** candidate numeric table for WBC, differential components, platelets, and CBC indices; verify assay, age rows, and units from the original document. [^1_5] |
| 4 — `CBC-NUM-004` | Pediatric CBC Reference Values (LTR10211) | Associated Laboratories / American Board of Pathology-hosted document | 2021 document version | Associated Laboratories | No DOI assigned | https://abpath.org/wp-content/uploads/2023/07/Pediatric-CBC-ref-ranges_2.1.21.pdf | **Unknown license; publicly retrievable PDF** | **Yes—CBC table including WBC in `10*9/L` and MCV ranges**, with age/sex partitions shown. | Yes | **A and B:** numeric WBC and MCV bridge candidate; useful for age-banded CBC-index sourcing, but institution/method specificity must remain explicit. [^1_6] |
| 5 — `CBC-NUM-005` | Complete Blood Count Reference Intervals and Patterns of Changes Across Pediatric, Adult, and Geriatric Ages | Eun Hee Nah, et al. | 2018 | *Annals of Laboratory Medicine* | 10.3343/alm.2018.38.6.503 | https://pmc.ncbi.nlm.nih.gov/articles/PMC6056383/ | **Open access via PMC; journal reuse terms require verifier review** | **Yes—age- and sex-stratified CBC reference-interval tables**, including WBC and platelets; the article reports that WBC and platelet counts peak in early childhood and decline with age. | Yes, though not exclusively pediatric | **A:** independently retrievable peer-reviewed table source for WBC/platelet age patterns and a secondary check against local/CALIPER ranges. [^1_7] |
| 6 — `CBC-PLT-001` | Diagnosis and Management of Immune Thrombocytopenia in Children: A Comprehensive Review | Y. Thakur, et al. | 2024 | *Children* / PMC | 10.3390/children11101280 | https://pmc.ncbi.nlm.nih.gov/articles/PMC11488990/ | **Open access via PMC; journal license must be checked at source** | **Yes—isolated thrombocytopenia below 100,000/uL** is stated as the diagnostic count criterion described by the review. | Yes | **A and B:** ITP candidate and platelet-count threshold; supports the isolated-thrombocytopenia branch, but does not alone distinguish consumptive or marrow etiologies. [^1_8] |
| 7 — `CBC-PLT-002` | Diagnosis and Management of Typical, Newly Diagnosed Primary Immune Thrombocytopenia in Children | Canadian Paediatric Society | 2018 | Canadian Paediatric Society | 10.1093/pch/pxy150 | https://cps.ca/en/documents/position/immune-thrombocytopenia | **Freely available guideline; explicit reuse license not identified** | **Yes—some experts use platelet counts above 10 or 20 `10*9/L` as hemostatic targets; the document also states that management is driven by bleeding severity rather than count alone.** | Yes, 90 days–17 years | **A and B:** best accessible pediatric ITP action-threshold candidate in this sweep; retain the source’s count-versus-bleeding-context distinction during verification. [^1_9] |
| 8 — `CBC-EOS-001` | An Approach to the Evaluation of Persistent Hypereosinophilia in Pediatric Patients | J. T. Schwartz, et al. | 2018 | *Frontiers in Immunology* | 10.3389/fimmu.2018.01359 | https://pmc.ncbi.nlm.nih.gov/articles/PMC6130221/ | **Open access via PMC; Frontiers article license should be captured by verifier** | **Yes—hypereosinophilia is defined as AEC at or above 1,500 cells/uL**, equivalent to 1.5 `10*9/L`. | Yes | **B:** primary candidate for isolated/persistent eosinophilia pattern and numeric referral/work-up trigger. [^1_10] |
| 9 — `CBC-MONO-001` | Differential Diagnosis and Workup of Monocytosis: A Systematic Approach to a Common Hematologic Finding | A. A. Mangaonkar, et al. | 2021 | *Frontiers in Oncology* | 10.3389/fonc.2021.606722 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8057007/ | **Open access via PMC; Frontiers article license should be captured by verifier** | **Yes—WHO persistent monocytosis definition: absolute monocytes above 1 `10*9/L`, more than 10% of leukocytes, persisting more than 3 months.** | No—general/adult-oriented | **B:** numeric monocytosis persistence candidate; explicitly non-pediatric, so it should rank below pediatric sources and not substitute for a pediatric-specific trigger. [^1_11] |
| 10 — `CBC-LEUK-001` | Leukocytosis | V. Mank, et al. | 2024 content; 2026 page update | StatPearls / NCBI Bookshelf | No DOI assigned | https://www.ncbi.nlm.nih.gov/books/NBK560882/ | **Publicly available through NIH-hosted NCBI Bookshelf; copyright/license status requires source-level capture** | **Yes—WBC above 11,000 cells/uL is described as general leukocytosis**, while the source expressly notes that normal limits vary by age and physiologic state. | No—general reference | **B:** provisional leukocytosis/left-shift work-up locator only; do not use its adult/general threshold as a pediatric threshold. [^1_12] |
| 11 — `CBC-ITP-002` | Immune Thrombocytopenia (ITP) in Children Clinical Guideline | Royal Cornwall Hospitals NHS Trust | Not stated on retrieved document | Royal Cornwall Hospitals NHS Trust | No DOI assigned | Retrieved document locator: https://doclibrary-rcht.cornwall.nhs.uk/DocumentsLibrary/RoyalCornwallHospitalsTrust/Clinical/Paediatrics/HaematologyAndOncology | **Unknown license; publicly retrievable NHS Trust document** | **Yes—the guideline states that low platelet counts alone, including counts below 10 `10*9/L`, are not themselves an indication for treatment.** | Yes | **A and B:** secondary pediatric ITP severity/action context; useful as a conflict-visible candidate alongside the CPS guidance, not as a universal platelet-only action rule. [^1_13] |
| 12 — `CBC-THROMBO-001` | Approach to Thrombocytopenia | PedsCases | 2021 | PedsCases | No DOI assigned | https://www.pedscases.com/approach-thrombocytopenia | **Unknown license; publicly retrievable educational resource** | **No numeric threshold identified in retrieved result.** | Yes | **B:** candidate differential framework for ITP versus consumptive, infectious, marrow-production, and other thrombocytopenia mechanisms; use only if full source contains independently retrievable, attributable content. [^1_14] |

## CALIPER finding

The public CALIPER database is the strongest new candidate for **RF-EV-002** because it is described as an age- and sex-specific pediatric reference-interval database covering more than 200 tests.  The separately held 2020 CALIPER hematology article remains non-duplicated in this packet: it is already in `RF-CBC-002`, while the database is a different access path that may expose the actual numeric rows missing from the bundle.[^1_15][^1_3][^1_1]

The database page itself does **not** establish, in the retrieved result, that every desired CBC parameter is available for each analyzer or that its values carry an open reuse license.  The verifier should capture a source-local record for every intended parameter with: database version/date, analyzer, specimen/method, age and sex partition, lower/upper value, displayed unit normalized to UCUM, and an exact stable locator or archived rendering.[^1_2][^1_3]

## Coverage gaps

- **Age-banded WBC plus differential:** the Iowa, UVM, ABPath, and CALIPER candidates are the highest-yield numeric locators found here; the UVM document specifically advertises WBC, differential cell counts, platelets, hematocrit, hemoglobin, and reticulocyte pediatric ranges.[^1_5][^1_4][^1_3]
- **ANC benign versus severe neutropenia:** this remains a gap in the *net-new* list because the best directly relevant open pediatric review is already held in the bundle and therefore was intentionally not resurfaced.[^1_1]
- **Platelet severity/action bands:** the CPS and Royal Cornwall sources give useful accessible count-context statements, but neither should be represented as a universal platelet-only action policy; both make bleeding severity clinically material.[^1_13][^1_9]
- **Leukemoid reaction versus blasts:** no pediatric-specific, independently retrievable numeric leukemoid/blast-referral passage was identified in this sweep; `CBC-LEUK-001` is explicitly only a general locator.[^1_12]
- **Pancytopenia work-up ordering:** no new source is ranked because the existing bundle already contains a pediatric open-access protocolized marrow-failure evaluation source; it should remain the starting point, with a future sweep focused narrowly on a separately retrievable, numeric pancytopenia definition or triage table.[^1_1]
- **Microcytosis/macrocytosis:** `CBC-NUM-004` is the best newly surfaced numeric MCV-reference candidate, but anemia-etiology triggers should remain owned by the anemia module rather than inferred from a CBC reference table alone.[^1_6][^1_2]
<span style="display:none">[^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34]</span>

<div align="center">⁂</div>

[^1_1]: evidence-3.json

[^1_2]: 05-three-module-evidence-run-design-4.md

[^1_3]: https://caliperproject.ca/caliper/database/

[^1_4]: https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html

[^1_5]: https://www.uvmhealth.org/document/3946

[^1_6]: https://abpath.org/wp-content/uploads/2023/07/Pediatric-CBC-ref-ranges_2.1.21.pdf

[^1_7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6056383/

[^1_8]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11488990/

[^1_9]: https://cps.ca/en/documents/position/immune-thrombocytopenia

[^1_10]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6130221/

[^1_11]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8057007/

[^1_12]: https://www.ncbi.nlm.nih.gov/books/NBK560882/

[^1_13]: https://doclibrary-rcht.cornwall.nhs.uk/DocumentsLibrary/RoyalCornwallHospitalsTrust/Clinical/Paediatrics/HaematologyAndOncology/ImmuneThrombocytopeniaITPInChildrenClinicalGuideline.pdf

[^1_14]: https://www.pedscases.com/approach-thrombocytopenia

[^1_15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7403759/

[^1_16]: candidates-2.json

[^1_17]: authoring-decisions.yaml

[^1_18]: https://www.childrensmn.org/references/lab/hematology/cbc-reference-value-table.pdf

[^1_19]: https://www.labcorp.com/content/dam/labcorp/drupal/178250_DX_TL_PediatricTestRef_Final.pdf

[^1_20]: https://www.ncbi.nlm.nih.gov/books/NBK603670/

[^1_21]: https://dashboard.protocolosclinicos.com.br/download/anexo/3389/documento-oficial-aafp.pdf

[^1_22]: https://pubmed.ncbi.nlm.nih.gov/41005704/

[^1_23]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6842676/

[^1_24]: https://caliper.research.sickkids.ca/

[^1_25]: https://www.ucsfbenioffchildrens.org/medical-tests/eosinophil-count---absolute

[^1_26]: https://onlinelibrary.wiley.com/doi/10.1111/ijlh.14068

[^1_27]: https://synapse.koreamed.org/articles/1059057

[^1_28]: https://myadlm.org/science-and-research/clinical-chemistry/clinical-chemistry-podcasts/2012/closing-the-gaps-in-pediatric-laboratory-reference-intervals

[^1_29]: https://www.contemporarypediatrics.com/view/eosinophilia-what-does-it-mean

[^1_30]: https://cscc-sccc.ca/education-scientific-affairs/interest-groups-committees/caliper-sig/

[^1_31]: https://www.droracle.ai/articles/789049/what-is-the-significance-of-an-elevated-absolute-eosinophil

[^1_32]: https://labmed.org.uk/our-resources/news/acb-recommends-caliper.html

[^1_33]: https://pubmed.ncbi.nlm.nih.gov/37041294/

[^1_34]: https://www.tandfonline.com/doi/full/10.1080/10408363.2017.1379945

