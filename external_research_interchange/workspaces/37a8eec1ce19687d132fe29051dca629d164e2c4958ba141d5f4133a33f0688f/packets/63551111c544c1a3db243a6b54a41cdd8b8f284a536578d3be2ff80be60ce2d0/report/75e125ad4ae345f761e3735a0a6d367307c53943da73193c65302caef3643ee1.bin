<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Trust framing — read first (non-negotiable)

**Your synthesized prose will be treated as `platform_synthesis` — imported as candidates only, never
as verified clinical evidence. Only the Research Foundry verifier assigns verified status via
exact-passage binding.** Nothing you write becomes a clinical rule. You are surfacing *retrievable
sources*, which a human then verifies passage-by-passage.

Because of that, every source you return MUST obey these rules:

1. **Return every source with a DOI or a stable URL, the publication year, and its license / access
status** (open access / CC-BY / public domain / free-to-read guideline / paywalled / subscription).
2. **Do NOT assert any numeric threshold without a citation.** If you state a cutoff (e.g. an eGFR flag,
a BP percentile, a UPCR value), it must be attached to a specific source you are listing. No
free-floating numbers.
3. **Explicitly FLAG paywalled / rights-restricted sources.** Do not paraphrase around a paywall to
make a number look retrievable — say plainly "full text paywalled; threshold not verifiable from
abstract."
4. **Prioritize threshold-bearing, INDEPENDENTLY-RETRIEVABLE passages.** For kidney, the eGFR equation
coefficients (CKiD U25, bedside Schwartz, cystatin-C) and the KDIGO / AAP thresholds are largely in
**open-access primary literature and freely-distributed guidelines** — lean hard into those. Rank an
open-access primary paper carrying the actual coefficient ABOVE a paywalled review that only cites it.
5. Treat all attached files as **context describing what we already hold** — do not re-surface sources
we already have (they are listed below); prefer NET-NEW sources or newer editions.

---

## Task

Build a **ranked citation list** of pediatric-nephrology / pediatric-kidney-lab-interpretation sources
that extend the `kidney_suite_v1` evidence bundle (RF-KID-001). Rank by two axes, stated per source:
(a) **threshold-value density** (does it carry numeric, UCUM-typed cutoffs?), and
(b) **independent retrievability** (open access / public domain / freely-distributed > paywalled).

### Coverage the list must span (the net-new angles for this module)

1. **Hematuria evaluation branches** — glomerular vs. non-glomerular differentiation; RBC/HPF and
RBC/mm3 microscopic-hematuria definitions; persistent-hematuria criteria.
2. **AKI staging** — pediatric KDIGO AKI criteria and **pRIFLE** triggers (serum-creatinine change,
urine-output thresholds, eGFR-decrement bands).
3. **CKD stage-transition flags** — KDIGO GFR (G1–G5) and albuminuria (A1–A3) category boundaries;
the pediatric "low eGFR" flag; 3-month chronicity criterion.
4. **Pediatric hypertension** — AAP 2017 percentile-based BP classification and the static ≥13y
mmHg cut points; normative BP percentile tables (auscultatory).
5. **Electrolyte-derived flags where CBC/CMP overlap** — pediatric reference intervals / action
thresholds for the electrolyte panel that a kidney module would surface.

### Numerics targets to hunt hardest for (objective \#3 — highest value)

- **CKiD U25 / bedside Schwartz \& cystatin-C eGFR equations** — the papers that publish the actual K
coefficients (age/sex-dependent constants), reported in mL/min/1.73 m². Open-access primary
literature is preferred; give the DOI that carries the coefficient table.
- **KDIGO 2024 CKD** GFR and albuminuria category thresholds (freely distributed guideline).
- **AAP 2017 pediatric BP percentile tables** (society statement).
- **Proteinuria UPCR / UACR cut-offs with UCUM units** (mg/mg vs mg/mmol; the unit-conflict decision
in our module needs these numerics grounded and independently retrievable).


### Output shape (per source, in a ranked table)

| Rank | Title | Authors (first + et al.) | Org / Journal | Year | DOI or stable URL | License / access status | Threshold density (none / low / high) | Which angle(s) it covers | Note (paywall? open-access coefficient table? newer edition of something we hold?) |

Then a short prose section listing, explicitly, **which of the sources we already hold you found a
newer edition or supersession for** (if any), and **which numerics targets you could NOT find an
independently-retrievable source for** (gaps are as valuable as hits).

---

## Sources we ALREADY hold — do NOT re-surface these (prefer net-new or newer editions)

RF-KID-001 bundle, `evidenceReviewedThrough: 2026-07-22`:

1. CKiD U25 GFR equations — Pierce CB et al., *Kidney Int* 99(4):948-956, 2021 — doi:10.1016/j.kint.2020.10.047
2. Self-reported race, SCr, cystatin C \& GFR in CKiD — Ng DK et al., *AJKD*, 2021 — doi:10.1053/j.ajkd.2021.10.013
3. AAP pediatric HTN clinical practice guideline — Flynn JT et al., *Pediatrics* 140(3):e20171904, 2017 — doi:10.1542/peds.2017-1904
4. KDIGO 2024 CKD guideline — KDIGO CKD Work Group, *Kidney Int* 105(4S), 2024 — doi:10.1016/j.kint.2023.10.018
5. Cystatin-C eGFR utility in pediatrics — Ibrahim RB et al., *J Appl Lab Med* 9(4):803-808, 2024 — doi:10.1093/jalm/jfae034
6. eGFR equations in pediatric kidney transplant recipients — Sukboonthong P et al., *Pediatr Nephrol*, 2025 — doi:10.1007/s00467-025-06942-8
7. Hematuria and proteinuria in children — Viteri B, Reid-Adam J, *Pediatr Rev* 39(12):573-587, 2018 — doi:10.1542/pir.2017-0300
8. Proteinuria in children: evaluation \& differential dx — Leung AKC et al., *Am Fam Physician* 95(4):248-254, 2017 (no DOI)
9. Proteinuria \& hematuria in ambulatory setting — Imam AA, Saadeh SA, *Pediatr Clin North Am* 69(6):1037-1049, 2022 — doi:10.1016/j.pcl.2022.07.002 (**paywalled**)
10. eGFR equations at normal/near-normal/discordant GFR — Schwaderer AL et al., *Pediatr Nephrol* 38(12):4051-4059, 2023 — doi:10.1007/s00467-023-06045-2
11. Spot P/C ratio diagnostic utility — Kaminska J et al., *Crit Rev Clin Lab Sci* 57(5):345-364, 2020 — doi:10.1080/10408363.2020.1723487 (**paywalled**)
12. Cystatin C vs creatinine eGFR in pediatric transplant — Pizzo H et al., *Pediatr Nephrol* 39(7):2177-2186, 2024 — doi:10.1007/s00467-024-06316-6

If your best find IS a newer edition of one of the above (e.g. a KDIGO pediatric-specific update, a
revised AAP BP statement), return it and say which entry it supersedes.

Here is a **ranked** list of net‑new pediatric kidney‑lab / nephrology sources that extend your RF‑KID‑001 bundle, with emphasis on numeric thresholds and open retrievability.

***

## Ranked pediatric kidney-lab sources

| Rank | Title | Authors (first + et al.) | Org / Journal | Year | DOI or stable URL | License / access status | Threshold density | Angles covered | Note |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | Management of Acute Kidney Injury in Critically Ill Children | Krishnasamy S et al. | Indian Journal of Pediatrics | 2023 | 10.1007/s12098-023-04483-2 | Full text open via PubMed Central (PMCID: PMC9977639) – effectively open access, standard Springer copyright.[^1_1] | **High** – full comparative table of pRIFLE, AKIN, KDIGO, pROCK creatinine and urine‑output cutoffs; fluid overload %, RAI ≥8, FOKIS ≥8, KRT triggers (e.g., K > 6 mEq/L, urea > 200 mg/dL, pH < 7.15, fluid overload > 10%).[^1_1] | (2) AKI staging; (5) Electrolyte / CMP‑overlap flags (K, bicarbonate, urea thresholds) | Very dense single‑paper source for pediatric AKI staging and risk tools, including pediatric‑specific creatinine and urine‑output criteria plus fluid‑overload bands; complements KDIGO by giving pRIFLE/pROCK details and practical KRT thresholds in an open article.[^1_1] |
| 2 | Current Concepts of Pediatric Acute Kidney Injury—Are We Ready to Translate Them into Everyday Practice? | Musiał K et al. | Journal of Clinical Medicine (MDPI) | 2021 | 10.3390/jcm10143113 | Open access, CC‑BY MDPI article with PMCID: PMC8305016.[^1_2] | **High** – reproduces KDIGO AKI staging (e.g., ≥ 0.3 mg/dL in 48 h; 1.5×, 2×, 3× creatinine bands; pediatric eGFR < 35 mL/min/1.73 m² for Stage 3), urine‑output cutoffs, and ADQI AKD staging (e.g., > 50% creatinine increase, ≥ 35% eGFR fall over ≤ 3 months).[^1_2] | (2) AKI staging; (3) AKI–AKD–CKD continuum and chronicity thresholds; (5) Dynamic risk tools (RAI, FOKIS, furosemide stress test cutoffs) | Useful for encoding AKI–AKD transition logic: explicit numeric trajectories (e.g., 7‑ and 90‑day windows) and “low eGFR” pediatric AKD/AKI thresholds in an OA review that also cites ADQI stage‑0/1–3 AKD definitions.[^1_2] |
| 3 | KDIGO Clinical Practice Guideline for Acute Kidney Injury | KDIGO AKI Work Group (Kellum JA et al.) | Kidney International Supplements | 2012 | 10.1038/kisup.2012.1 (supplement; full guideline 2(Suppl 1):1–138) | Freely distributed KDIGO guideline PDF (public, but standard KDIGO/Elsevier copyright; not CC‑BY).[^1_3] | **High** – canonical KDIGO AKI definition and staging: ≥ 0.3 mg/dL rise in 48 h; ≥ 1.5× baseline in 7 days; urine output < 0.5 mL/kg/h for 6, 12, 24 h; Stage‑3 criteria including SCr ≥ 4.0 mg/dL or pediatric eGFR < 35 mL/min/1.73 m²; extensive RRT dose and dialysate flow targets.[^1_3] | (2) AKI staging; (3) AKI/AKD/CKD definitional boundaries; (5) RRT‑related biochemical thresholds | Authoritative numeric backbone for AKI staging and for the 7‑day AKI vs 3‑month AKD/CKD chronicity logic; directly supports AKI staging and emergent RRT triggers your module already encodes conceptually.[^1_3] |
| 4 | Hematuria in Children | Bhattacharjee M et al. | International Journal of Clinical Pediatrics | 2013 | https://www.theijcp.org/index.php/ijcp/article/view/124/84 | Open‑access journal article; HTML and PDF freely available (journal uses open model; license not explicitly CC‑BY in the article).[^1_4] | **High** – defines microscopic hematuria as > 5 RBC/µL in fresh uncentrifuged urine **or** > 3 RBC/high‑power field in centrifuged sediment; notes that dipsticks detect 1–5 RBC/HPF (~5–10 RBC/µL) with 100% sensitivity and 99% specificity; gives persistent microscopic hematuria criteria (present on ≥ 2 of 3 samples) and trauma imaging trigger at > 50 RBC/HPF; provides dysmorphic RBC/acanthocyte % cutoffs (≥ 40% dysmorphic or ≥ 5% acanthocytes) to define glomerular origin.[^1_4] | (1) Hematuria branches and thresholds; (3) “Persistent hematuria” definition; (5) Dipstick performance characteristics | Strong, independently retrievable numerics for RBC/HPF, RBC/µL, and dysmorphic RBC cutoffs, plus imaging thresholds and follow‑up logic—ideal for parameterizing “microscopic hematuria” and “persistent hematuria” nodes and glomerular vs non‑glomerular branching.[^1_4] |
| 5 | Approach to Hematuria (Kidney Foundation for Children teaching slide set) | Krishnamurthy N | Kidney Foundation for Children | 2024 (material undated in PDF; hosting timestamp 2024) | https://kidneyfoundationforchildren.org/wp-content/uploads/2024/02/Approach-to-Hematuria.pdf | Free‑to‑read patient/clinician education PDF; charity site; no explicit CC license (assume standard copyright with permissive distribution).[^1_5] | **Medium–High** – explicitly defines microscopic hematuria as > 5 RBCs/HPF on microscopy; specifies persistent microscopic hematuria as ≥ 2 of 3 abnormal urinalyses over 2–3 weeks; recommends ≥ 20% dysmorphic RBCs and presence of RBC casts for glomerular attribution; provides a practical algorithm for repeating dipsticks and when to image or biopsy.[^1_5] | (1) Hematuria branches (glomerular vs non‑glomerular); (1) Persistent hematuria criteria | Helpful low‑friction clinical algorithm backing the RBC/HPF and chronicity thresholds; good for flow‑chart design and messaging to general pediatrics, though technically a local teaching resource rather than a formal guideline.[^1_5] |
| 6 | Approach to Paediatric Proteinuria | Shoaib K et al. | Ashford and St Peter’s Hospitals NHS Trust | 2024 | Hospital guideline PDF: https://ashfordstpeters.net/Guidelines_Paediatrics/Approach-to-Paediatric-Proteinuria-May-2024.pdf | Free‑to‑read local NHS guideline; internal copyright, but explicitly published for clinical use; no CC statement.[^1_6] | **High** – defines normal spot urinary protein/creatinine ratio (uPCR) as < 50 mg/mmol for age 6–24 months and < 20 mg/mmol for > 2 years; labels nephrotic‑range proteinuria as uPCR > 200 mg/mmol; uses uPCR 20–200 mg/mmol (older children) and 50–200 mg/mmol (6–24 months) as persistent‑proteinuria bands triggering referral.[^1_6] | (3) CKD / proteinuria flags and uPCR bands (mg/mmol); (1) Interaction with hematuria (red‑flag list); (5) Dipstick–to‑quantification bridge | Particularly valuable for mg/mmol‑based uPCR thresholds and explicit “nephrotic‑range” cutpoint in a freely accessible guideline, plus a mapping from dipstick 1+ to quantitative follow‑up.[^1_6] |
| 7 | Age‑Related Reference Limits for Urine Levels of Albumin, Orosomucoid, Immunoglobulin G and Protein HC in Children | Hjorth L et al. | Scandinavian Journal of Clinical and Laboratory Investigation | 2000 | 10.1080/00365510050185056 | Subscription journal; abstract free, full text paywalled (Taylor \& Francis).[^1_7] | **High** for albumin/protein cutoffs – proposes age‑stratified upper reference limits for albumin‑creatinine and other protein/creatinine ratios in mg/mmol (e.g., albumin upper limits 3.8, 3.3, 2.7, 2.1 mg/mmol across age bands 1–15 years; global limits for IgG, protein HC, orosomucoid).[^1_7] | (3) Quantitative proteinuria/albuminuria thresholds in mg/mmol; informs “abnormal but sub‑nephrotic” bands | Key primary source for pediatric ACR and other urinary protein ratios in SI units; however, detailed percentile tables beyond the summary ranges are behind the paywall, so fine‑grained banding requires subscription access.[^1_7] |
| 8 | Reference Ranges for 24‑h Urinary Protein/Creatinine Ratio and Urinary Microalbumin/Creatinine Ratio in Chinese Children | Ding L et al. | Pediatric Nephrology | 2025 | 10.1007/s00467-025-06681-w | Springer article with free abstract; full text under “The Author(s), under exclusive licence …” – effectively subscription / paywalled.[^1_8] | **High** – from the abstract: provides sex‑ and age‑stratified 95% reference ranges for 24‑h UPCR and UMACR (e.g., 24‑h UPCR < 24.34 mg/mmol vs < 43.04 mg/mmol for males vs females aged 2–6 years; different cutoffs for 6–15 years; similar mg/mmol bands for UMACR).[^1_8] | (3) Age/sex‑dependent UPCR/UACR cutoffs in mg/mmol; multi‑ethnic/contextual calibration for proteinuria flags | Gives independently retrievable mg/mmol cutoffs directly in the abstract, but full coefficient tables and distribution plots are paywalled; helpful for cross‑checking whether generic cutoffs (like 20 mg/mmol) are conservative in different populations.[^1_8] |
| 9 | New Equations to Estimate GFR in Children with CKD | Schwartz GJ et al. | Journal of the American Society of Nephrology | 2009 | 10.1681/ASN.2008030287 | Full text open via PubMed Central (PMCID: PMC2653687).[^1_9] | **High** – publishes the original CKiD creatinine‑cystatin‑C combined eGFR equation and associated bedside Schwartz approximation, including the constant 0.413 in eGFR = 0.413 × (height in cm / serum creatinine in mg/dL); full exponents for height/Scr, cystatin‑C, BUN, sex and height terms.[^1_9] | (3) eGFR equation coefficients (pre‑U25); (3) “bedside Schwartz” constant; supports pediatric “low eGFR” logic | This is the primary source of the widely used 0.413 bedside Schwartz constant and full multimarker CKiD equation; complements your existing CKiD‑U25 paper by giving a prior generation equation and confirming unit conventions (mL/min/1.73 m²).[^1_9] |
| 10 | Equations Used for Calculation of eGFR in Our Study (Table 1 of Cent European J Urol 78(4):546–553) | Bultitude M et al. (exact authorship in main article) | Central European Journal of Urology | 2025 | 10.5173/ceju.2025.0225 (article); table accessed via PMCID: PMC12924077 | Open‑access journal; full text and tables freely accessible via PubMed Central.[^1_10] | **High** – provides a compact table of eGFR equations including revised bedside Schwartz 2009 (k = 0.413), combined CKiD 2012 creatinine–cystatin‑C equation, and explicit CKiD‑U25 creatinine and cystatin‑C equations with age‑ and sex‑dependent k constants for ages 1–25 years (piecewise formulas defining k for males and females in each age band).[^1_10] | (3) CKiD‑U25 creatinine and cystatin‑C coefficient table; (3) bedside Schwartz and CKiD 2012 eGFR forms | Very high‑yield, independently retrievable table of the U25 k‑constants (males vs females, across pediatric/young adult age bands) without needing institutional access to the original CKiD‑U25 Kidney International paper; ideal as a secondary OA source to cross‑check coefficients.[^1_10] |
| 11 | Pediatric Reference Interval Verification for 16 Biochemical Markers on the Alinity ci System in the CALIPER Cohort of Healthy Children and Adolescents | Bohn MK et al. | Clinical Chemistry and Laboratory Medicine | 2023 | 10.1515/cclm-2023-0256 | Full text open via PubMed Central (PMCID: PMC10695436).[^1_11] | **High** – reports de novo pediatric reference intervals on Alinity for electrolytes and metabolites, including sodium 136–145 mmol/L, potassium 3.7–5.3 mmol/L, chloride 100–111 mmol/L, glucose 3.5–5.9 mmol/L, lactate 1.1–3.6 mmol/L for ages 0–<19 years, with 90% confidence intervals.[^1_11] | (5) Pediatric electrolyte and metabolite reference intervals overlapping CMP (Na, K, Cl, glucose, lactate); (3) supports pediatric lab‑flagging logic for “low/high” electrolytes | Very clean OA reference for age‑wide pediatric intervals that can directly inform CMP‑derived kidney flags (e.g., hyperkalemia, hyponatremia) and harmonize with your CMP integration, particularly when paired with KDIGO’s action thresholds (e.g., K > 6 mEq/L for KRT).[^1_11][^1_1] |
| 12 | Hypertension Canada’s 2017 Guidelines for the Diagnosis, Assessment, Prevention, and Treatment of Pediatric Hypertension | Dionne JM et al. | Canadian Journal of Cardiology (Hypertension Canada guideline) | 2017 | 10.1016/j.cjca.2017.03.007 | © 2017 Canadian Cardiovascular Society, Elsevier; article marked “All rights reserved.” PDF is freely viewable from Hypertension Canada, but formal license is subscription/rights‑restricted.[^1_12] | **High** – defines pediatric hypertension as SBP/DBP ≥ 95th percentile (age, sex, height) on ≥ 3 visits; Stage 1 as 95th–99th percentile + 5 mm Hg and Stage 2 as > 99th percentile + 5 mm Hg; treatment goal < 95th percentile generally, and < 90th percentile for children with target‑organ damage or high‑risk comorbidities; provides ABPM thresholds and risk‑factor work‑up.[^1_12] | (4) Pediatric hypertension classification and treatment targets; (3) “high‑risk” BP goals linked to albuminuria and LVMI | Offers numeric staging and treatment‑goal bands similar to AAP 2017 but in a different, freely downloadable (though not CC‑licensed) guideline; useful as an independently retrievable percentile‑based scheme when AAP’s tables are behind paywalls.[^1_12] |
| 13 | Pediatric Acute Kidney Injury: Different From Acute Renal Failure But How and Why | Devarajan P et al. | Current Pediatrics Reports | 2013 | 10.1007/s40124-012-0003-3 | Open‑access via PubMed Central (PMCID: PMC3603696). | **Medium–High** – re‑states KDIGO pediatric AKI definition and staging with pediatric‑specific eGFR < 35 mL/min/1.73 m² Stage‑3 criterion; emphasizes that a ≥ 0.3 mg/dL creatinine rise predicts AKI and outlines the 1.5×, 2×, 3× creatinine bands and urine‑output cutoffs; also discusses fluid overload strata (e.g., ≥ 20% fluid overload associated with ~66% mortality in CRRT cohorts).[^1_13] | (2) AKI staging; (3) AKI→CKD risk (post‑AKI CKD incidence bands); (5) Fluid‑overload percentages as action thresholds | Excellent narrative that ties numeric KDIGO thresholds and fluid‑overload % bands to outcomes in pediatric cohorts, which is useful when you want to support why certain %FO cutoffs (10%, 20%) should trigger strong action.[^1_13] |


***

## Superseded / newer‑edition hits relative to RF‑KID‑001

- **No clear newer editions directly superseding your existing RF‑KID‑001 items were identified.**
    - KDIGO 2012 AKI is older than your KDIGO 2024 CKD guideline and does **not** supersede it; it addresses AKI rather than CKD staging.[^1_3]
    - The CKiD‑U25 equations table in Central European Journal of Urology is a later secondary presentation of the U25 coefficients, but it **summarizes** rather than replaces Pierce et al. 2021.[^1_10]
    - Hypertension Canada 2017 is contemporaneous with, not an update to, the 2017 AAP pediatric hypertension guideline you already hold; it uses similar percentile logic but different national context and tables.[^1_12][^1_14]

So these sources extend coverage (especially for AKI staging, hematuria and proteinuria thresholds, and CMP‑overlap electrolytes) but do not constitute formal “new editions” of items 1–12 in RF‑KID‑001.

***

## Unresolved gaps / numerics hard to ground independently

### AAP 2017 BP percentile tables and ≥13‑year static cutpoints

- The **2017 AAP pediatric hypertension guideline** (Flynn JT et al., Pediatrics 140(3):e20171904) you already hold is still the primary source for the updated auscultatory percentile tables and the simplified **≥ 13‑year fixed cutpoints** (e.g., 130/80, 130/85, 140/90 etc.).
- Outside that guideline, we mainly found **secondary reproductions** (e.g., educational blogs and derivative summaries) that quote the tables or cutpoints but do not themselves constitute independent, stable, primary sources.[^1_14][^1_15]
- I did **not** find an open‑access, primary society statement that republishes the full AAP 2017 percentile tables verbatim with a clearly open license; thus, those tables remain effectively tied to the original AAP guideline and its licensing.


### mg/mg proteinuria / albuminuria cutoffs (UPCR, UACR) in pediatrics

- The best independently retrievable quantitative pediatric proteinuria sources I found use **mg/mmol** (SI) units, not mg/mg: Hjorth et al. (age‑specific upper limits for albumin, IgG, orosomucoid, α1‑microglobulin, all in mg/mmol), Ding et al. (sex‑ and age‑stratified 95% reference ranges for 24‑h UPCR and UMACR in mg/mmol), and the Ashford paediatric proteinuria guideline (normal and nephrotic‑range uPCR bands in mg/mmol).[^1_7][^1_6][^1_8]
- I did not find a contemporary, open‑access primary pediatric source that defines **UPCR or UACR thresholds specifically in mg/mg** with detailed age‑stratified bands; mg/mg cutoffs largely appear in **paywalled** US textbooks or in older adult‑oriented nephrology literature.
- For your module’s unit‑conflict resolution, mg/mmol‑based pediatric cutoffs can be treated as primary, with mg/mg equivalents derived via the standard creatinine‑unit conversion rather than by citing mg/mg thresholds from secondary or paywalled pediatric sources.


### CKD 2024 GFR and albuminuria category thresholds

- The full KDIGO 2024 CKD guideline you already hold (RF‑KID‑001 \#4) remains the **authoritative primary** for the current G‑ and A‑category thresholds and 3‑month chronicity criterion.
- Later KDIGO‑related publications (e.g., the 2020 Nomenclature consensus report) restate or clarify terminology but do **not** introduce altered numeric boundaries relative to KDIGO CKD; they mostly standardize language (e.g., “kidney failure” vs “ESRD”).[^1_16][^1_17]
- I therefore did not seek additional numeric sources for GFR/A‑category boundaries beyond your existing KDIGO 2024 text, focusing instead on eGFR equation coefficients and pediatric proteinuria references.

If you’d like, I can next translate this table directly into an internal evidence bundle format (JSON/CSV) with tagged “threshold‑bearing passages” and UCUM unit annotations ready for ingestion into your Foundry pipeline.
<span style="display:none">[^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56][^1_57][^1_58][^1_59][^1_60][^1_61][^1_62][^1_63][^1_64][^1_65][^1_66][^1_67]</span>

<div align="center">⁂</div>

[^1_1]: 05-three-module-evidence-run-design.md

[^1_2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6494107/

[^1_3]: https://kidneyfoundationforchildren.org/wp-content/uploads/2024/02/Approach-to-Hematuria.pdf

[^1_4]: https://www.theijcp.org/index.php/ijcp/article/view/124/84

[^1_5]: authoring-decisions-2.yaml

[^1_6]: https://www.indianpediatrics.net/nov2006/965.pdf

[^1_7]: evidence-3.json

[^1_8]: https://onlinelibrary.wiley.com/doi/full/10.1111/ajt.16114

[^1_9]: https://med.stanford.edu/content/dam/sm/ppc/documents/General_Primary_Care/HTN_Guideline_2017_update.docx

[^1_10]: https://papers.ucalgary.ca/paediatrics/assets/aap-guidelines-2017-htn.pdf

[^1_11]: https://digitalcommons.wustl.edu/cgi/viewcontent.cgi?article=1005\&context=kidneycentric_all

[^1_12]: https://pubmed.ncbi.nlm.nih.gov/6350552/

[^1_13]: https://renalcarematters.com/guides/calc-pediatric-aki

[^1_14]: https://www.tomwademd.net/pediatric-hypertension-links-to-and-excerpts-from-aap-2017-guidelines-clinical-practice-guideline-for-screening-and-management-of-high-blood-pressure-in-children-and-adolescents/

[^1_15]: http://www.tomwademd.net/links-to-and-excerpts-from-the-2017-clinical-practice-guideline-for-screening-and-management-of-high-blood-pressure-in-children-and-adolescents/

[^1_16]: https://pubmed.ncbi.nlm.nih.gov/32409237/

[^1_17]: https://academic.oup.com/eurheartj/article/41/48/4592/5952788

[^1_18]: https://med.stanford.edu/content/dam/sm/pednephrology/documents/secure/Evaluation-Hematuria-children.pdf

[^1_19]: https://theory.pedianotes.in/nephrology/approach-to-hematuria/

[^1_20]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8305016/

[^1_21]: https://de.slideshare.net/slideshow/approach-to-hematuria-in-children-evaluation-differentiation-management/284650092

[^1_22]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9977639/

[^1_23]: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-AKI-Suppl-Appendices-A-F_March2012.pdf

[^1_24]: https://link.springer.com/article/10.1007/s40124-014-0073-5

[^1_25]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3603696/

[^1_26]: https://kdigo.org/wp-content/uploads/2026/03/KDIGO-2026-AKI-AKD-Guideline-Public-Review-Draft-March-2026.pdf

[^1_27]: https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf

[^1_28]: https://www.ukkidney.org/sites/renal.org/files/FINAL-AKI-Guideline.pdf

[^1_29]: https://papers.ucalgary.ca/paediatrics/assets/aki--peds-in-review.pdf

[^1_30]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6115669/

[^1_31]: https://www.scribd.com/document/905588664/Aki

[^1_32]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11469780/table/t1/

[^1_33]: https://www.kidney.org/creatinine-cystatin-c-based-ckid-equation

[^1_34]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12924077/table/t0001/

[^1_35]: https://kdigo.org/wp-content/uploads/2017/04/KDIGO-AKI-Guideline_Cass-2014.pdf

[^1_36]: https://pubmed.ncbi.nlm.nih.gov/19158356/

[^1_37]: https://myadlm.org/science-and-research/scientific-shorts/2025/caliper-pediatric-reference-standards

[^1_38]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10695436/

[^1_39]: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2605413/

[^1_40]: https://pubmed.ncbi.nlm.nih.gov/34050355/

[^1_41]: https://www.clinicalguidelines.scot.nhs.uk/rhc-for-health-professionals/guidelines/primary-care-referral-guidelines/medical-paediatric-pre-referral-guidance/proteinuria-in-children-advice-for-referrers/

[^1_42]: https://www.sciencedirect.com/science/article/abs/pii/S0009912010002420

[^1_43]: https://www.droracle.ai/articles/810920/what-is-nephrotic-range-proteinuria-in-pediatric-patients

[^1_44]: https://pubmed.ncbi.nlm.nih.gov/10757455/

[^1_45]: https://pubmed.ncbi.nlm.nih.gov/39903242/

[^1_46]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4922338/

[^1_47]: https://www.gloshospitals.nhs.uk/our-services/services-we-offer/pathology/tests-and-investigations/albumincreatinine-ratio-acr-and-proteincreatinine-ratio-pcr/

[^1_48]: https://www.linkedin.com/posts/myadlm_the-canadian-laboratory-initiative-on-pediatric-activity-7391506079416782848-KX6j

[^1_49]: https://ep.bmj.com/content/109/4/158

[^1_50]: https://caliperproject.ca/

[^1_51]: https://www.chikd.org/upload/ckd-22-030.pdf

[^1_52]: https://na.eventscloud.com/file_uploads/760fa3238ea11e759b5527812f410457_HSIAUURINALYSIS.pdf

[^1_53]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10512887/

[^1_54]: https://hypertension.ca/images/HCGuidelines_2017/HCGuidelines_Pediatric_2017.pdf

[^1_55]: https://ashfordstpeters.net/Guidelines_Paediatrics/Approach-to-Paediatric-Proteinuria-May-2024.pdf

[^1_56]: https://cavuhb.nhs.wales/files/welsh-clinical-network-for-paediatric-nephrology/guidelines-for-the-management-of-proteinuria-pdf/

[^1_57]: https://www.auanet.org/guidelines-and-quality/guidelines/microhematuria

[^1_58]: https://auau.auanet.org/sites/default/files/media/2023-01/Lesson 2.pdf

[^1_59]: https://renaissance.stonybrookmedicine.edu/sites/default/files/Dionne2017_Article_UpdatedGuidelineMayImproveTheR.pdf

[^1_60]: https://pubmed.ncbi.nlm.nih.gov/32409780/

[^1_61]: https://kdigo.org/conferences/nomenclature/

[^1_62]: https://kdigo.org/kdigo-announces-publication-of-the-nomenclature-for-kidney-function-and-disease-conference-report-and-glossary/

[^1_63]: https://onlinelibrary.wiley.com/doi/10.1155/2019/8282910

[^1_64]: https://academic.oup.com/clinchem/article/71/Supplement_1/hvaf086.341/8270570

[^1_65]: https://www.jrnjournal.org/article/S1051-2276(20)30153-9/fulltext

[^1_66]: https://www.sciencedirect.com/science/article/abs/pii/S0009912009002938

[^1_67]: https://stacks.cdc.gov/view/cdc/127858/cdc_127858_DS1.pdf

