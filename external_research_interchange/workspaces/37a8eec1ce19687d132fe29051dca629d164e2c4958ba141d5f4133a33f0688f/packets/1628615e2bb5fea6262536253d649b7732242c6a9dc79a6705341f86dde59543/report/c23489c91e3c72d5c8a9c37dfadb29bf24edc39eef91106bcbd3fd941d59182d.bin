<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# \#\# Read this first — how your output is used (non-negotiable framing)

**Your synthesized prose will be treated as `platform_synthesis` — imported as candidates only, never
as verified clinical evidence. Only the Research Foundry verifier assigns verified status via
exact-passage binding.** Nothing you write is authoritative and nothing becomes a clinical rule.

### Trust invariants — follow all five, every time

1. **Return every source with DOI/URL, publication year, and license/access status.** All three, every
row. A source without an access status is an incomplete row.
2. **Do NOT assert any numeric value without an attached citation to its source.** If you quote a
number at all, cite the exact document carrying it; otherwise leave numbers out — this is a
source-gathering pass, not an extraction pass.
3. **Explicitly FLAG any paywalled / rights-restricted source** (do not paraphrase around a paywall).
Paywalled sources are wanted in your list — we route them to a licensing track — but they must be
labelled, never quietly summarized.
4. **Prioritize threshold-bearing, INDEPENDENTLY-RETRIEVABLE documents** (public-domain — US federal /
WHO — then open-license) **over copyrighted framework prose.**
5. Treat every field as data, not instruction. Do not embed directives or control text in any cell.

---

## Why this run exists

A clinician user reported that our pediatric anemia assessment **accepts hemoglobin but has no place
to enter a hematocrit.** That is correct and structural: hematocrit appears nowhere in our input
schema, our 91 rules, or our reference-range tables — because **we hold no pediatric hematocrit
threshold for an entered value to be compared against.**

Our existing hemoglobin, MCV and RDW bands trace to a **paywalled** source whose passages are
quarantined as not independently retrievable. So this is not only a coverage problem: **we need
carriers of pediatric red-cell numbers that we are actually permitted to quote verbatim.** That is
what you are hunting.

## What we need you to find

Rank by **(a) does it carry actual pediatric numbers, and (b) can we quote it.** A public-domain
document with the numbers beats a more authoritative document we can only paraphrase.

### Priority 1 — hematocrit carriers (the reported gap)

- Age- and sex-partitioned **pediatric hematocrit reference intervals**, any credible source.
- Any authoritative body that **defines pediatric anaemia by hematocrit** (as opposed to hemoglobin
only) — WHO, US federal (CDC/NIH), AAP, pediatric hematology societies. **A confident negative is a
wanted result**: if the answer is "everyone defines it by hemoglobin", find the documents that show
that.
- **US federal / public-domain** publications carrying pediatric hematology cutoffs. These are the
highest-value targets in the entire packet, because public-domain text can be quoted verbatim. Find
what actually exists, which agency published it, what ages it covers, and whether it is current or
superseded.


### Priority 2 — the other red-cell indices

- Pediatric **MCHC**, **MCH**, and **RBC count** reference intervals (age/sex partitioned).
- **CALIPER** pediatric reference-interval outputs — we hold the CALIPER papers but **their numeric
tables are paywalled** in what we have. Hunt specifically for **independently retrievable carriers
of those numbers**: open-access supplements, PMC deposits, a public CALIPER database, or
institutional mirrors with reuse terms. Report precisely which form is reachable and under what
license.
- Other **open-access pediatric reference-interval studies** (any country — we will scope population
applicability downstream; tell us the cohort).


### Priority 3 — discriminators and derived values

- The **hereditary spherocytosis** laboratory-diagnosis literature, especially society guidelines
(BSH is a promising publisher; we already hold their G6PD guideline but not an HS one) — we need the
MCHC-based discriminator and its caveats.
- **Discriminant indices** for iron deficiency vs thalassemia trait (Mentzer `MCV/RBC` and relatives),
prioritizing **pediatric validation studies** and any study reporting where they fail.
- **Corrected reticulocyte % / reticulocyte production index** sources carrying the age-appropriate
**reference hematocrit** values and maturation-correction factors.
- The **"rule of three"** (`Hct ≈ 3 × Hgb`) — find its actual provenance and any authoritative
statement on whether it is intended for clinical interpretation or only laboratory quality control.
We are researching this to decide **against** using it; find the documents that settle it.


### Priority 4 — methodology and units

- Sources on **measured/spun vs analyzer-calculated (`MCV × RBC`) hematocrit** and whether reference
intervals are method-specific.
- Reference-interval **establishment standards** (e.g. CLSI) — note access status; these are usually
paywalled and that is fine to report.

---

## Required output columns

| \# | column | rule |
| :-- | :-- | :-- |
| 1 | `source_id` | short kebab-case slug you assign |
| 2 | `title` | full document title |
| 3 | `publisher_or_body` | organization |
| 4 | `year` | publication year |
| 5 | `doi_or_url` | **required** — DOI preferred, else stable URL |
| 6 | `access_status` | `public-domain` \| `open-access` \| `free-to-read` \| `paywalled` \| `unknown` |
| 7 | `license` | named license if stated (CC-BY, US Gov work, …) or `unstated` |
| 8 | `carries_numbers` | yes / no / partial — does this document contain the actual pediatric values? |
| 9 | `analytes_covered` | hematocrit / MCHC / MCH / RBC / hemoglobin / MCV / RDW / retic |
| 10 | `age_range_covered` | as published |
| 11 | `population` | cohort: country, health status, sampling basis |
| 12 | `priority` | 1–4 per the sections above |
| 13 | `why_ranked_here` | one line — especially, why we can or cannot quote it |

**`free-to-read` is not `open-access`.** This distinction is load-bearing for us: a prior discovery run
found that "free to read" was the largest failure class among candidate substitutes — readable does not
mean reusable. When a document is readable but carries no reuse grant, say `free-to-read` and say so in
`why_ranked_here`.

## Scope

Population **6 months to <18 years** primarily; neonatal/young-infant sources are welcome but must be
marked in `population` (our module abstains below 6 months).

Out of scope: treatment, dosing, transfusion thresholds, diagnosis.

Output shape and where to save it: see `expected-output/README.md`. Your prose and this list import as
`platform_synthesis` candidates.

The table below lists high‑yield pediatric hematology sources prioritized by (1) presence of age‑/sex‑partitioned numeric hematocrit and other red‑cell indices, and (2) whether those numbers appear in public‑domain or openly licensed artifacts versus paywalled or rights‑restricted ones.[^1_1][^1_2][^1_3]
Rows marked `public-domain` or `open-access` are especially valuable for your numerics-first run because their tables can be quoted verbatim, whereas `free-to-read` and `paywalled` items will need rights vetting before reuse.[^1_4][^1_5]

> **Note:** No numeric values are restated from paywalled content; for those, only the presence of reference intervals is described.

***

### Pediatric hematocrit / red‑cell index sources (ranked)

| source_id | title | publisher_or_body | year | doi_or_url | access_status | license | carries_numbers | analytes_covered | age_range_covered | population | priority | why_ranked_here |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| childrensmn-cbc-refs | CBC Reference Value Table | Children’s Minnesota Laboratory Services | unknown | https://www.childrensmn.org/references/lab/hematology/cbc-reference-value-table.pdf | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW | Birth–18 years (plus adult rows)[^1_2] | Hospital CBC reference intervals for apparently healthy children and adolescents in a US tertiary pediatric center.[^1_2] | 1 | Freely viewable lab handbook with age-banded pediatric Hct, RBC, and red-cell index intervals, but no explicit reuse license (readable, not openly licensed).[^1_2] |
| nbtnhs-child-fbc | NORMAL BLOOD COUNT VALUES IN CHILDHOOD | North Bristol NHS Trust Haematology | unknown | https://www.nbt.nhs.uk/sites/default/files/Childrens FBC Reference Ranges.pdf | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW | Birth–18 years (granular infant/child/adolescent bands)[^1_1] | UK hospital pediatric cohort; routine FBC reference ranges for apparently healthy children.[^1_1] | 1 | Single concise PDF giving pediatric Hb, Hct, RBC, and derived RBC indices including MCH and MCHC with age partitions and derived-index table.[^1_1] |
| beaumont-ped-heme-2024 | Hematology – Pediatric Reference Ranges (2024) | Corewell Health (Beaumont Laboratory) | 2024 | https://www.beaumontlaboratory.com/docs/default-source/specimen-collections-manual/blood/hematology-pediatric-reference-ranges-2024.pdf | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW; retic | 1 day–17 years (detailed neonatal, infant, child, adolescent bands)[^1_6] | US hospital laboratory pediatric population; internal reference ranges for “healthy” children presenting for care.[^1_6] | 1 | Rich pediatric table including Hct, RBC, MCV, MCH, MCHC, RDW, and reticulocyte ranges across fine-grained pediatric age bands, but with no explicit reuse license.[^1_6] |
| nationwide-hem-ref | Adjusted Hematology Normal Reference Ranges | Nationwide Children’s Hospital Laboratory Services | 2021 | https://www.nationwidechildrens.org/-/media/nch/specialties/laboratory-services/live-sitecore-lab-services-documents/hematology-normal-reference-ranges.ashx | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; retic | Neonate–≥18 years with distinct pediatric sub-bands (e.g., 6 months–1 year, 2–5, 6–11, 12–17)[^1_7] | US children’s hospital; reference ranges for CBC and reticulocytes in pediatric and adult patients without known hematologic disease.[^1_7] | 1 | Hospital reference card with explicit Hct, RBC, and reticulocyte ranges by pediatric age and sex, useful as an independently retrievable numeric carrier though reuse terms are unstated.[^1_7] |
| chop-labs-ranges | Reference Ranges (Hematology/Coagulation) | Children’s Hospital of Philadelphia Laboratory | 2024 | https://www.chop.edu/sites/default/files/2024-06/chop-labs-reference-ranges.pdf | free-to-read | unstated | partial | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; platelets; WBC | Neonate–adolescence (exact bands detailed in tables)[^1_8] | Large US pediatric center; lab-derived ranges for healthy pediatric patients where criteria are met.[^1_8] | 1 | Comprehensive pediatric CBC reference document; appears to contain Hct and red-cell indices but reuse terms are not clearly licensed (readable but likely copyrighted).[^1_8] |
| cdc-vhs11-247 | Vital and Health Statistics Series 11, No. 247: Hematologic Reference Ranges | National Center for Health Statistics, CDC | 2005 | https://www.cdc.gov/nchs/data/series/sr_11/sr11_247.pdf | public-domain | US federal government work | yes | hematocrit; hemoglobin; RBC; WBC; platelets | Includes pediatric strata (e.g., 9–11, 12–14 years) within broader age tables.[^1_3] | US nationally representative survey participants classified as “healthy” for hematologic reference range derivation.[^1_3] | 1 | US federal public‑domain report with tabulated hematologic reference ranges (including Hct, Hb, RBC) by age, making its numeric intervals fully quotable.[^1_3] |
| iom-iron-def-nbk | Iron Deficiency Anemia: Recommended Guidelines for the Prevention, Detection, and Management Among U.S. Children and Women of Childbearing Age | Institute of Medicine / National Academies Press (NCBI Bookshelf) | 1993 | https://www.ncbi.nlm.nih.gov/books/NBK236499/ | free-to-read | unstated | yes | hematocrit; hemoglobin | Children 0.5–4.9 years and other age/sex groups (cutoffs given by band).[^1_9] | US guideline population, focusing on children and women of childbearing age without major comorbidities.[^1_9] | 1 | Explicitly defines anemia in children 0.5–4.9 years as Hb \<11 g/dL or Hct \<33%, providing one of the few clear pediatric hematocrit-based anemia definitions, albeit under non-public open-license terms.[^1_9] |
| cdc-iron-def-1998 | Recommendations to Prevent and Control Iron Deficiency in the United States | Centers for Disease Control and Prevention | 1998 | https://stacks.cdc.gov/view/cdc/5659 | public-domain | US federal government work | partial | hematocrit; hemoglobin; ferritin | Infants 6–24 months, children 2–5 years, older children, pregnant women (cutoffs and screening ages described).[^1_10][^1_11] | US infants and children at risk for iron deficiency, identified via CDC criteria in a public health context.[^1_11] | 2 | Foundational US federal guidance recommending screening using hemoglobin or hematocrit, but presenting limited explicit pediatric Hct cutoffs compared with Hb and ferritin.[^1_11][^1_4] |
| cdc-anemia-criteria | CDC Criteria for Anemia in Children and Childbearing-Aged Women | Centers for Disease Control and Prevention (MMWR) | 1989 | https://www.cdc.gov/mmwr/preview/mmwrhtml/00001405.htm | public-domain | US federal government work | yes | hemoglobin; hematocrit | Children and adolescents with age- and sex-specific anemia thresholds.[^1_12] | US children and women of childbearing age in national surveillance datasets.[^1_12] | 2 | Public‑domain MMWR document specifying Hb (and, where given, Hct) cutoffs used for defining anemia in children, supporting parallel Hb/Hct criteria but still primarily Hb-focused.[^1_12] |
| who-hb-2011 | Haemoglobin Concentrations for the Diagnosis of Anaemia and Assessment of Severity | World Health Organization | 2011 | https://www.who.int/publications/i/item/WHO-NMH-NHD-MNM-11.1 | open-access | unstated (WHO standard copyright) | yes | hemoglobin | 6–59 months, 5–11 years, 12–14 years, ≥15 years (age bands in Hb cutoff table).[^1_13] | Global populations, including children, defined for public health anemia diagnosis at population level.[^1_13] | 2 | WHO summary of anemia-defining Hb cutoffs, using hemoglobin only (hematocrit not used for thresholds), providing important negative evidence for Hct-based pediatric anemia definitions.[^1_13] |
| who-hb-2024 | Guideline on Haemoglobin Cutoffs to Define Anaemia in Individuals and Populations | World Health Organization | 2024 | https://www.who.int/publications/i/item/9789240088542 | open-access | CC BY-NC-SA 3.0 IGO[^1_5] | yes | hemoglobin | Includes four pediatric Hb cutoff bands for ages 6 months–14 years, plus adults.[^1_14][^1_15] | Children 6 months–14 years and other life stages in global populations, with 5th‑percentile Hb-based cutoffs.[^1_14][^1_15] | 2 | Current WHO normative guideline that defines anemia exclusively via hemoglobin cutoffs (not hematocrit), explicitly describing pediatric bands and thus reinforcing Hb-only definitions.[^1_14][^1_15] |
| nhanes-rbc-refs | Establishing Pediatric and Adult RBC Reference Intervals With NHANES Data Using Piecewise Regression | American Journal of Clinical Pathology | 2019 | https://pubmed.ncbi.nlm.nih.gov/30285066/ | paywalled | unstated | yes | hematocrit; hemoglobin; RBC; MCH; MCHC; MCV; RDW | Children, adolescents, and adults from 2–>80 years (age- and sex-specific intervals derived).[^1_16] | US “healthy” subpopulation from NHANES 1999–2012, nationally representative sample after exclusions.[^1_16] | 2 | Large, methodologically rigorous NHANES-based study deriving age- and sex-specific reference intervals for RBC, Hb, Hct, and indices; numeric tables are paywalled and thus not currently quotable.[^1_16] |
| nhanesiii-cbc-diagrams | Complete Blood Count Reference Interval Diagrams Derived from NHANES III | Laboratory Hematology | 2004 | https://api.semanticscholar.org/CorpusID:20071987 | paywalled | unstated | partial | hematocrit; hemoglobin; RBC; MCHC; MCH; MCV; RDW; platelets | 10–>75 years (with explicit 10–14 and 14–18 year strata that include adolescents).[^1_17] | US NHANES III participants selected as “healthy” per exclusion criteria; age, sex, race stratified.[^1_17] | 2 | Influential NHANES III analysis providing CBC reference interval diagrams by age, sex, and race, including adolescent bands; useful structural evidence but detailed pediatric Hct ranges remain behind a paywall.[^1_17] |
| caliper-mindray-hct | Comprehensive Pediatric Reference Intervals for 79 Hematology Markers in the CALIPER Cohort of Healthy Children and Adolescents Using the Mindray BC-6800Plus System | CALIPER / Int. J. Lab. Hematology (Wiley) | 2023 | https://onlinelibrary.wiley.com/doi/10.1111/ijlh.14068 | paywalled | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW; retic; other hematology markers | 30 days–18 years with age- and sex-partitioned intervals for multiple erythrocyte parameters.[^1_18] | CALIPER cohort of 687 apparently healthy Canadian children and adolescents recruited in the community.[^1_18] | 2 | Key CALIPER hematology paper confirming that Hct, Hb, RBC, MCV, and MCHC all require age/sex partitioning; numeric tables are paywalled, so it is a structural but not quotable numeric source.[^1_18] |
| caliper-ref-database | CALIPER Reference Interval Database | Hospital for Sick Children (CALIPER) | 2024 | https://caliperproject.ca/caliper/database/ | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; many others (platform-specific) | Birth–18 years (continuous coverage, age- and sex-specific where indicated).[^1_19][^1_20][^1_21] | Thousands of healthy Canadian children and teens across multiple platforms and assays in a curated reference-interval repository.[^1_19][^1_20][^1_21] | 2 | Public web front-end and mobile app providing age/sex-specific pediatric reference intervals including hematology; accessible to query but with no explicit open‑reuse license stated, so numeric reuse terms need legal review.[^1_19][^1_20][^1_21] |
| youngchild-cbc-ri | Pediatric Reference Intervals for Hematology Parameters in Healthy Young Children | Journal of Clinical Laboratory Analysis | 2023 | https://pubmed.ncbi.nlm.nih.gov/37442636/ | paywalled | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW; platelets; WBC | 3 days–<30 months, partitioned into 3 days–<4 months, 4–<10, 10–<15, and 4–<30 months.[^1_22] | Healthy children from a single center; early-life pediatric CBC parameters with age partitions; none required sex partitioning.[^1_22] | 2 | Direct pediatric CBC reference-interval study showing that Hct, Hb, RBC, and indices change markedly in early life; numeric intervals available only in the full article.[^1_22] |
| chinese-kids-cbc | Age- and Sex-Specific Reference Intervals for Hematologic Analytes in Chinese Children | Int. J. Lab. Hematology | 2019 | https://onlinelibrary.wiley.com/doi/10.1111/ijlh.12979 | paywalled | unstated | yes | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW; WBC; platelets | 1–7 years (age-stratified by year and sex).[^1_23] | 2164 healthy Han Chinese children from Henan province with direct-method reference interval derivation.[^1_23] | 2 | Provides non‑North‑American pediatric Hb, Hct, RBC, and index intervals using CLSI-compliant methods; paywalled but valuable for cross-population comparison.[^1_23] |
| cdc-anemia-assessment-2022 | Improving Anemia Assessment in Clinical and Public Health Practice | CDC (MMWR Supplement) | 2022 | https://stacks.cdc.gov/view/cdc/154147 | public-domain | US federal government work | partial | hemoglobin; hematocrit; ferritin | Children and pregnant women (various age bands discussed).[^1_4] | US surveillance and EHR cohorts; discusses thresholds and test choices for anemia and iron deficiency.[^1_4] | 2 | Review explicitly notes CDC historical guidance that anemia screening may use Hb or Hct, while emphasizing that Hb is the more direct measure and that hematocrit declines later, supporting hemoglobin-centric practice and clarifying roles of Hct.[^1_4] |
| hs-bcsh-2011 | Guidelines for the Diagnosis and Management of Hereditary Spherocytosis | British Committee for Standards in Haematology (BCSH) | 2011 | https://www.gloshospitals.nhs.uk/documents/1896/BCSH_Guidelines_for_Hereditary_Spherocytosis.pdf | free-to-read | unstated | yes | MCHC; hemoglobin; retic; MCV; RBC; bilirubin | Mainly neonates and children but covers all ages; pediatric-focused diagnostic criteria discussed.[^1_24][^1_25] | Patients with suspected hereditary spherocytosis in high-income settings; includes neonatal and childhood cohorts from cited studies.[^1_24][^1_25] | 3 | Core HS guideline noting that MCHC \>360 g/L in neonates is a useful indicator for HS with reported sensitivity and specificity, and listing analytical artifacts that can spuriously raise MCHC; numerics freely readable but not clearly open-licensed.[^1_24] |
| hs-overview-2025 | Overview on Hereditary Spherocytosis Diagnosis | Int. J. Lab. Hematology | 2025 | https://onlinelibrary.wiley.com/doi/full/10.1111/ijlh.14376 | paywalled | unstated | yes | MCHC; retic; hemoglobin; RBC; MCV | Children and adults (severity classification includes reticulocyte percentages by phenotype).[^1_26] | Mixed-age HS patients; reviews diagnostic markers and severity categories.[^1_26] | 3 | Recent review proposing MCHC \>355 g/L as a cutoff for HS and reticulocyte thresholds for severity stratification; useful for discriminator design but paywalled for exact numeric tables.[^1_26] |
| mentzer-saudi-2024 | Diagnostic Test Performance of the Mentzer Index in Evaluating Saudi Children with Microcytosis | Frontiers in Medicine | 2024 | https://www.frontiersin.org/articles/10.3389/fmed.2024.1361805/full | open-access | likely CC BY 4.0 (Frontiers standard) | yes | MCV; RBC; Mentzer index; hemoglobin | Children with microcytosis in Saudi Arabia (age range given in article; pediatric cohort).[^1_27] | Saudi children with microcytosis evaluated for iron deficiency vs thalassemia trait in a tertiary setting.[^1_27] | 3 | Open‑access pediatric validation of Mentzer index, providing sensitivity/specificity and failure patterns in a contemporary cohort; directly relevant for encoded discriminant-index performance, with reusable numerics pending license confirmation.[^1_27] |
| mentzer-indices-hindawi | Hematological Indices for Differential Diagnosis of Beta Thalassemia Trait and Iron Deficiency Anemia | Anemia (Hindawi) | 2014 | https://onlinelibrary.wiley.com/doi/10.1155/2014/576738 | free-to-read | unstated | yes | MCV; RBC; Mentzer and multiple indices; hemoglobin; RDW | Children 1.1–16 years with Hb 8.7–11.4 g/dL and microcytosis.[^1_28] | 290 carefully selected pediatric patients with either IDA or β‑thalassemia trait, excluding mixed cases.[^1_28] | 3 | Pediatric microcytic cohort comparing 12 discriminant indices, finding Mentzer index highest sensitivity/specificity for β‑thalassemia trait; article appears readable online but reuse license is not clearly stated.[^1_28] |
| mentzer-indices-children-2010 | Reliability of Red Blood Cell Indices and Formulas to Discriminate Between Beta Thalassemia Trait and Iron Deficiency in Children | Hematology | 2010 | https://pubmed.ncbi.nlm.nih.gov/20423571/ | paywalled | unstated | yes | MCV; RBC; Mentzer and other indices; hemoglobin; RDW | Children 1.8–7.5 years with mild hypochromic microcytic anemia.[^1_29] | 458 children (243 ID, 215 β‑thal trait) from a single cohort.[^1_29] | 3 | Pediatric study showing that no RBC index or formula is fully reliable to separate β‑thalassemia trait from iron deficiency, which is critical negative evidence about discriminant indices.[^1_29] |
| mentzer-ash-2013 | Screening For Thalassemia Carriers in Populations With High Rate of Iron Deficiency: Revisiting the Applicability of Mentzer Index | American Society of Hematology (Blood meeting abstract) | 2013 | https://ashpublications.org/blood/article/122/21/1023/103463/Screening-For-Thalassemia-Carriers-In-Populations | free-to-read | unstated | partial | MCV; RBC; modified Mentzer index; HbA2; ferritin | Pediatric patients 1–18 years with diagnoses of ID only, thalassemia minor only, or ID+thalassemia minor.[^1_30] | Children referred to a tertiary lab over 10 years, classified by iron and HbA2 status.[^1_30] | 3 | Abstract-level data showing a modified Mentzer index (mMI) remains useful even with concurrent iron deficiency, supporting index behavior in complex pediatric cases; detailed tables beyond abstract may be restricted.[^1_30] |
| rpi-peds-ajcp-2020 | Evaluation of the Reticulocyte Production Index in the Pediatric Population | American Journal of Clinical Pathology | 2020 | https://academic.oup.com/ajcp/article/154/1/70/5818062 | paywalled | unstated | partial | retic; hematocrit; hemoglobin; RPI | Pediatric age range as defined in study (children and adolescents; exact bands in article).[^1_31] | Pediatric patients with anemia in whom RPI performance and interpretation were evaluated.[^1_31] | 3 | Focused on how RPI behaves in children with anemia, providing pediatric-specific interpretive data for corrected retic and RPI cutoffs, but full numeric details are behind a paywall.[^1_31] |
| retic-ri-pamj-2021 | Reticulocyte Count: A Simple Test but Tricky Interpretation! | Pan African Medical Journal | 2021 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8490160/ | open-access | unstated (likely CC BY) | partial | retic; hematocrit; hemoglobin; RPI | Adults and infants (normal RI ranges described separately).[^1_32] | General population; focuses on interpretive principles rather than establishing pediatric reference intervals.[^1_32] | 3 | Explains formulas for corrected reticulocyte index and RPI using patient Hb/Hct and standard values, with interpretive thresholds (e.g., RI <2% vs >3% with anemia), but not pediatric-specific intervals.[^1_32] |
| loinc-rpi-31111-8 | LOINC 31111-8 Reticulocyte Production Index | Regenstrief Institute / LOINC | 2015 | https://loinc.org/31111-8 | free-to-read | unstated | yes | retic; hematocrit; RPI | Not age-specific (generic clinical use).[^1_33] | Generic clinical population; describes adult “standard” hematocrit 45% and hematocrit-tier maturation factors.[^1_33] | 3 | Defines the RPI concept for coding purposes and specifies the standard formula and hematocrit-dependent maturation factors, which can inform how you encode corrected retic calculations (though adult-based).[^1_33] |
| rpi-wiki-method | Reticulocyte Production Index (encyclopedic summary) | Wikipedia | 2005 (orig.); updated | https://en.wikipedia.org/wiki/Reticulocyte_production_index | free-to-read | unstated | yes | retic; hematocrit; hemoglobin; RPI | Not age-specific; general adult reference Hct and maturation tiers.[^1_34] | General population; educational summary aggregating standard RPI formulas and interpretations.[^1_34] | 4 | Summarizes the standard RPI and corrected reticulocyte formulas and maturation table (Hct tiers and factors); useful for cross-checking other more formal sources but not an authoritative primary reference.[^1_34] |
| ruleofthree-qc-2001 | Using Empirical Rules in Quality Control of Clinical Laboratory Data | PharmaSUG conference proceedings | 2001 | https://pharmasug.org/download/papers/DM05.PDF | free-to-read | unstated | yes | hematocrit; hemoglobin; RBC | Not age-specific (QC rules applied across routine hematology).[^1_35] | Generic clinical lab data used for QC illustrations.[^1_35] | 3 | Explicitly states the “Rule of Three” that hematocrit ≈ three times hemoglobin and that this empirical relationship is intended for quality control error detection rather than clinical interpretation, directly supporting a decision not to use Hct≈3×Hb to back-calculate thresholds.[^1_35] |
| statpearls-cbc-2024 | Normal and Abnormal Complete Blood Count With Differential | StatPearls (NCBI Bookshelf) | 2024 | https://www.ncbi.nlm.nih.gov/books/NBK604207/ | free-to-read | unstated | partial | hematocrit; hemoglobin; RBC; MCV; MCH; MCHC; RDW | Adults primarily; pediatric-specific intervals not detailed.[^1_36] | General clinical population; article focuses on definitions and adult reference intervals.[^1_36] | 4 | Provides formulas linking hematocrit, RBC, and MCV (Hct = RBC × MCV/10) and describes red-cell indices conceptually; valuable for derived-value logic and for clarifying that most modern analyzers calculate Hct from RBC and MCV.[^1_36] |
| hct-methods-review | Hematocrit – A Review of Different Analytical Methods | acutecaretesting.org | 2014 | https://acutecaretesting.org/en/articles/hematocrit--a-review-of-different-analytical-methods | free-to-read | unstated | partial | hematocrit; RBC; MCV | Not age-specific; methods apply across age groups.[^1_37] | General patient samples across multiple analyzers and methods.[^1_37] | 4 | Explains measured (spun) vs calculated (MCV × RBC × 0.1) hematocrit, with emphasis on method-dependent differences, supporting the run’s requirement that any Hct interval be tagged with the measurement method.[^1_37] |
| trapped-plasma-captoday | Q\&A on Discrepant Hematocrit Results | CAP Today | 2009 | http://www.captodayonline.com/Archives/0810/0808_QA.html | free-to-read | unstated | partial | hematocrit | Not age-specific; describes analytic artifacts across patients.[^1_38] | General adult and pediatric samples with abnormal red-cell morphologies.[^1_38] | 4 | Discusses that microhematocrit (“spun crit”) can read approximately 1–3 percentage points higher than analyzer-calculated Hct due to trapped plasma, highlighting a systematic bias between methods relevant for reference-interval alignment.[^1_38] |
| esr-lecture-trapped-plasma | ESR Lectures Notes (Section on Trapped Plasma and Hematocrit) | Academic course notes | 2024 | https://www.studocu.com/ph/document/our-lady-of-fatima-university/hematology-1/esr-lectures-notes-regarding-esr-test-in-the-laboratory/10008663 | free-to-read | unstated | partial | hematocrit | Not age-specific.[^1_39] | Didactic note set; examples drawn from adult and pediatric anemias.[^1_39] | 4 | Teaching notes explicitly stating that spun Hct is typically 1–3% (0.01–0.03 L/L) higher than automated Hct because of trapped plasma, especially in macrocytic or abnormal RBC morphologies, reinforcing method-specific Hct differences.[^1_39] |
| clsi-ep28-a3c | EP28-A3c: Defining, Establishing, and Verifying Reference Intervals in the Clinical Laboratory | Clinical and Laboratory Standards Institute (CLSI) | 2010 (reaffirmed 2020) | https://clsi.org/shop/standards/ep28/ | paywalled | unknown | no | none (methodology only) | Not applicable (method guideline, not a specific cohort).[^1_40][^1_41] | Not applicable; provides study design and statistical guidance for reference-interval establishment and verification.[^1_40][^1_41] | 4 | Core methodological standard (FDA-recognized) for designing reference-interval studies and transferring intervals between labs; essential for evaluating whether pediatric RI papers and lab cards are technically robust, but full text is paywalled.[^1_40][^1_41] |

This table should give you a concrete starting pool of:

- **P1 numeric carriers** for pediatric Hct and red-cell indices (especially the US children’s-hospital tables and the public‑domain CDC Series 11 hematologic ranges).[^1_6][^1_2][^1_7][^1_3][^1_1]
- **P2 global and national guideline context** showing that modern anemia definitions are overwhelmingly hemoglobin‑based, with only older or secondary sources giving explicit pediatric Hct cutoffs.[^1_14][^1_9][^1_13][^1_12][^1_4]
- **P3 discriminant and derived-index sources** for MCHC‑based HS rules, Mentzer and related indices, and reticulocyte/RPI methodology, including pediatric cohorts and failure modes.[^1_35][^1_27][^1_28][^1_29][^1_26][^1_24][^1_32][^1_33][^1_31]
- **P4 methodological and unit-handling references** for measured vs calculated hematocrit and reference-interval establishment standards.[^1_40][^1_37][^1_39][^1_38]
<span style="display:none">[^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56][^1_57][^1_58][^1_59][^1_60][^1_61][^1_62][^1_63][^1_64][^1_65][^1_66][^1_67][^1_68][^1_69][^1_70][^1_71][^1_72][^1_73][^1_74][^1_75][^1_76][^1_77][^1_78][^1_79][^1_80][^1_81][^1_82][^1_83][^1_84][^1_85][^1_86][^1_87][^1_88]</span>

<div align="center">⁂</div>

[^1_1]: https://www.nbt.nhs.uk/sites/default/files/Childrens FBC Reference Ranges.pdf

[^1_2]: https://www.childrensmn.org/references/lab/hematology/cbc-reference-value-table.pdf

[^1_3]: https://www.cdc.gov/nchs/data/series/sr_11/sr11_247.pdf

[^1_4]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9612197/

[^1_5]: https://iris.who.int/items/80a8b7b3-b3e9-4673-8a47-90eeee11ccaa

[^1_6]: https://www.beaumontlaboratory.com/docs/default-source/specimen-collections-manual/blood/hematology-pediatric-reference-ranges-2024.pdf?sfvrsn=a83a92ab_1

[^1_7]: https://www.nationwidechildrens.org/-/media/nch/specialties/laboratory-services/live-sitecore-lab-services-documents/hematology-normal-reference-intervals---new-and-old.ashx?la=en\&hash=E63869A8AB541AA79BF45D317F6198A7

[^1_8]: https://www.chop.edu/sites/default/files/2024-06/chop-labs-reference-ranges.pdf

[^1_9]: https://www.ncbi.nlm.nih.gov/books/NBK236499/

[^1_10]: https://stacks.cdc.gov/view/cdc/5659/cdc_5659_DS1.pdf

[^1_11]: https://www.cdc.gov/mmwr/preview/mmwrhtml/00051880.htm

[^1_12]: https://www.cdc.gov/mmwr/preview/mmwrhtml/00001405.htm

[^1_13]: https://www.who.int/publications/i/item/WHO-NMH-NHD-MNM-11.1

[^1_14]: https://www.who.int/publications/i/item/9789240088542

[^1_15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11300700/

[^1_16]: https://pubmed.ncbi.nlm.nih.gov/30285066/

[^1_17]: https://www.semanticscholar.org/paper/Complete-blood-count-reference-interval-diagrams-by-Cheng-Chan/c175e6888ec1c894e3aa1873365992832e3abf0d

[^1_18]: https://onlinelibrary.wiley.com/doi/10.1111/ijlh.14068

[^1_19]: https://pubmed.ncbi.nlm.nih.gov/29017389/

[^1_20]: https://caliperproject.ca/caliper/database/

[^1_21]: https://www.re3data.org/repository/r3d100013928

[^1_22]: https://pubmed.ncbi.nlm.nih.gov/37442636/

[^1_23]: https://onlinelibrary.wiley.com/doi/10.1111/ijlh.12979

[^1_24]: https://www.gloshospitals.nhs.uk/documents/1896/BCSH_Guidelines_for_Hereditary_Spherocytosis.pdf

[^1_25]: https://www.thebloodproject.com/wp-content/uploads/2022/06/HS_GUIDELINES.pdf

[^1_26]: https://onlinelibrary.wiley.com/doi/full/10.1111/ijlh.14376

[^1_27]: https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2024.1361805/pdf

[^1_28]: https://onlinelibrary.wiley.com/doi/10.1155/2014/576738

[^1_29]: https://pubmed.ncbi.nlm.nih.gov/20423571/

[^1_30]: https://ashpublications.org/blood/article/122/21/1023/103463/Screening-For-Thalassemia-Carriers-In-Populations

[^1_31]: https://academic.oup.com/ajcp/article/154/1/70/5818062

[^1_32]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8490160/

[^1_33]: https://loinc.org/31111-8

[^1_34]: https://en.wikipedia.org/wiki/Reticulocyte_production_index

[^1_35]: https://pharmasug.org/download/papers/DM05.PDF

[^1_36]: https://www.ncbi.nlm.nih.gov/sites/books/NBK604207/

[^1_37]: https://acutecaretesting.org/en/articles/hematocrit--a-review-of-different-analytical-methods

[^1_38]: http://www.captodayonline.com/Archives/0810/0808_QA.html

[^1_39]: https://www.studocu.com/ph/document/our-lady-of-fatima-university/hematology-1/esr-lectures-notes-regarding-esr-test-in-the-laboratory/105551606

[^1_40]: https://clsi.org/shop/standards/ep28/

[^1_41]: https://webstore.ansi.org/standards/clsi/clsiep28a3c

[^1_42]: 06-anemia-red-cell-indices-evidence-run.md

[^1_43]: evidence-2.json

[^1_44]: reference-ranges-3.json

[^1_45]: https://www.healthcare.uiowa.edu/path_handbook/appendix/heme/pediatric_normals.html

[^1_46]: https://pubmed.ncbi.nlm.nih.gov/35968555/

[^1_47]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12239707/

[^1_48]: https://www.accp.com/docs/sap/Lab_values_Table_PedSAP.pdf

[^1_49]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6306047/

[^1_50]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11101252/

[^1_51]: https://register.awmf.org/assets/guidelines/025-018l-S1_Hereditaere-Sphaerozytose_2023-09_1.pdf

[^1_52]: https://www.onkopedia.com/en/onkopedia/guidelines/hereditary-spherocytosis-spherocytic-anemia

[^1_53]: https://publications.aap.org/pediatrics/article/135/6/1107/75753/A-Pediatrician-s-Practical-Guide-to-Diagnosing-and

[^1_54]: https://emedicine.medscape.com/article/206107-guidelines

[^1_55]: https://jmscr.igmpublication.org/v4-i12/135 jmscr.pdf

[^1_56]: https://pubmed.ncbi.nlm.nih.gov/18556182/

[^1_57]: https://www.ncbi.nlm.nih.gov/books/NBK539797/

[^1_58]: https://meddiscoveries.org/pdf/1135.pdf

[^1_59]: https://www.quickmedcalc.com/calculators/reticulocyte-production-index

[^1_60]: https://clinideck.com/corrected-reticulocyte-percentage-reticulocyte-production-index-rpi/

[^1_61]: https://www.droracle.ai/articles/1042707/how-is-the-corrected-reticulocyte-count-calculated-and-interpreted

[^1_62]: https://www.mdapp.co/reticulocyte-index-calculator-102/

[^1_63]: https://renalcarematters.com/guides/calc-reticulocyte-rpi

[^1_64]: https://top10k.com/tool/corrected-reticulocyte-count

[^1_65]: https://www.omnicalculator.com/health/crc

[^1_66]: https://taylorandfrancis.com/knowledge/Medicine_and_healthcare/Hematology/Reticulocyte_production_index/

[^1_67]: https://eclinpath.com/hematology/tests/absolute-reticulocyte-count/

[^1_68]: https://ngdc.cncb.ac.cn/openlb/publication/OLB-PM-36990763

[^1_69]: https://onlinelibrary.wiley.com/doi/full/10.1002/ajh.25904

[^1_70]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11668587/

[^1_71]: https://www.alexslemonade.org/childhood-cancer/guides/childhood-leukemia/appendix-blood-tests-and-what-they-mean/values-healthy

[^1_72]: https://academic.oup.com/clinchem/article-abstract/61/8/1075/5611520?redirectedFrom=fulltext

[^1_73]: https://www.tandfonline.com/doi/full/10.1080/00365513.2022.2100820

[^1_74]: https://onlinelibrary.wiley.com/doi/10.1111/bjh.16430

[^1_75]: https://iris.who.int/server/api/core/bitstreams/f9f74397-1440-478d-a63c-26f29a01552f/content

[^1_76]: https://iris.who.int/bitstreams/f9f74397-1440-478d-a63c-26f29a01552f/download

[^1_77]: https://www.guidelinecentral.com/guideline/3534081/

[^1_78]: https://stacks.cdc.gov/view/cdc/154147/cdc_154147_DS1.pdf

[^1_79]: https://www.uspreventiveservicestaskforce.org/Home/GetFile/1/798/ironscrev/pdf

[^1_80]: https://digital.ahrq.gov/anemia-age-7months-and

[^1_81]: https://symbiosisonlinepublishing.com/hematology/hematology05.php

[^1_82]: https://webstore.ansi.org/preview-pages/CLSI/preview_CLSI+EP28-A3C.pdf

[^1_83]: https://www.ncss.com/wp-content/themes/ncss/pdf/Procedures/NCSS/Reference_Intervals.pdf

[^1_84]: https://clsi.org/media/1722/clsi_document-and-code-changes.pdf

[^1_85]: https://bibbase.org/network/publication/anonymous-ep28a3cdefineandverifyreferenceintervalsinlab

[^1_86]: https://clinmedjournals.org/articles/ijbrd/ijbrd-2-012.pdf

[^1_87]: https://www.intertekinform.com/en-gb/standards/clsi-ep28-a3-3ed-2010-357319_saig_clsi_clsi_813967/

[^1_88]: https://content.veeabb.com/1d09429b-8373-419f-8f1a-d28f9586863a/89300f78-b6ea-46fb-81eb-10444b78f78e/89300f78-b6ea-46fb-81eb-10444b78f78e_source__v.pdf

