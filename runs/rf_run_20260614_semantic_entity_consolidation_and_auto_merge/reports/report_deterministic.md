---
schema_version: '0.1'
type: research_report
report_id: report_20260615_semantic_entity_consolidation_and_auto_merge
title: Semantic entity consolidation and auto-merge thresholds in a file-first vault
intent_id: intent_research_20260614_semantic_entity_consolidation_and_auto_merge
evidence_bundle_id: pending
created_at: '2026-06-15T10:18:57-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Resolution uses three decision tiers: scores above the auto-merge threshold merge automatically, scores between the flag and merge thresholds create a SAME_AS link for human review, and scores below the flag threshold create a new entity. [claim:clm_001]
Thresholds are tuned per domain: Financial Services (High Precision) auto_merge 0.98 / flag 0.90; Ecommerce Retail (Balanced) auto_merge 0.95 / flag 0.85; Content/Media (High Recall) auto_merge 0.92 / flag 0.75. [claim:clm_002]
The blended confidence score weights embedding similarity at 70% and fuzzy string matching at 30%, and only entities of the same type are matched to avoid false positives. [claim:clm_003]
The SAME_AS review relationship carries metadata including a numeric confidence, a status of pending/confirmed/rejected, created_at and reviewed_at timestamps, a reviewed_by field, and a method label. [claim:clm_004]
Health monitoring defines healthy ranges of auto-merge rejection rate below 2% (raise auto_merge_threshold if exceeded), flag-to-confirm rate of 60-90%, and orphan entity rate below 10%. [claim:clm_005]
The best LLMs need no or only a few training examples to match the entity-matching accuracy of PLMs fine-tuned on thousands of examples, and are more robust to unseen entities. [claim:clm_006]
GPT-4 zero-shot achieves F1 of 95.78 (Abt-Buy), 89.67 (Walmart-Amazon), 76.38 (Amazon-Google), 89.61 (WDC Products), 89.82 (DBLP-Scholar), and 98.41 (DBLP-ACM). [claim:clm_007]
Zero-shot GPT-4, using no task-specific training data, reaches comparable or better results than PLMs fine-tuned on thousands of training pairs. [claim:clm_008]
Fine-tuned PLM baselines reach F1 of 91.21 (RoBERTa) and 91.31 (Ditto) on Abt-Buy, and 87.02 (RoBERTa) and 86.39 (Ditto) on Walmart-Amazon, which GPT-4 zero-shot beats on the product datasets. [claim:clm_009]
There is no single best prompt; the optimal prompt depends on the specific model/dataset combination and must be tuned per combination. [claim:clm_010]
On unseen (out-of-distribution) entities, fine-tuned PLM matchers degrade sharply (Ditto 36-56% and RoBERTa 22-61% F1 drops) while LLMs remain robust, with GPT-4 outperforming the best transferred PLM by 34% F1. [claim:clm_011]
The Fellegi-Sunter model has three core parameters needed to compute a match probability between two records: lambda (prior match probability), m, and u. [claim:clm_012]
Lambda is the prior probability that any two records match assuming no other knowledge, and it depends on total record count, number of duplicates, and dataset overlap. [claim:clm_013]
The m probability is P(observation | records match) and is largely a measure of data quality; e.g. for a true match on Date of Birth, exact agreement is almost 100%, say m approximately 0.98. [claim:clm_014]
The u probability is P(observation | records do not match) and measures coincidence; e.g. for non-matching records, surname agreeing by chance is under 1%, u approximately 0.005. [claim:clm_015]
The total match weight equals log2(lambda/(1-lambda)) plus the sum over features of log2(m_i/u_i), and match weights are additive because the model assumes features are conditionally independent. [claim:clm_016]
A worked waterfall example sums a prior of -6.67 with feature weights (forename 4.74, surname 6.49, dob -1.97, city -1.12, email 8.00) to a total match weight of 9.48. [claim:clm_017]
Match probability is recovered from total match weight via Pr(Match|Obs)=2^Mobs/(1+2^Mobs); a match weight of 9.48 yields approximately 0.999. [claim:clm_018]
The non-linear weight-to-probability mapping has diminishing returns: a match weight of 0 gives probability 0.5, weight 4 gives 0.95, and weight 7 gives 0.99. [claim:clm_019]
The toolkit implements the standard five-step record linkage workflow — cleaning, indexing, comparing, classifying, and evaluation — with classified pairs optionally feeding back to improve earlier steps. [claim:clm_020]
The project is inspired by FEBRL but, unlike FEBRL, builds extensively on the pandas and numpy data-manipulation stack to make linkage faster and easier to embed in existing data projects. [claim:clm_021]
Candidate pairs are generated with indexing methods such as blocking and sorted neighbourhood indexing, and records are compared with similarity measures spanning strings, numbers, and dates. [claim:clm_022]
String comparison in the Compare class supports configurable methods including Jaro-Winkler and Damerau-Levenshtein with similarity thresholds, alongside exact matching on categorical fields. [claim:clm_023]
Classification supports both a supervised LogisticRegressionClassifier (trained on golden/true linkage data) and an unsupervised BernoulliEMClassifier described as the ECM-algorithm. [claim:clm_024]
The toolkit grounds its workflow and methods in the record linkage literature, citing Christen (2012), Fellegi & Sunter (1969), Dunn (1946), and Herzog, Scheuren & Winkler (2007). [claim:clm_025]
Splink's linkage algorithm is built on the Fellegi-Sunter model of record linkage with customisations to improve accuracy. [claim:clm_026]
Splink performs unsupervised model training requiring no labeled training data. [claim:clm_027]
Splink can link approximately one million records on a laptop in around a minute. [claim:clm_028]
Splink runs in Python on DuckDB or on big-data backends such as AWS Athena or Spark to scale to 100+ million records. [claim:clm_029]
Splink supports term frequency adjustments and user-defined fuzzy matching logic to improve match accuracy. [claim:clm_030]
Splink provides interactive visualisations to help users understand their model and diagnose problems. [claim:clm_031]
RF/MeatyWiki recommended posture keeps Markdown+YAML under Git as the single source of truth and adds a derived, disposable SQLite/Datasette index via the git-history pattern, accepting the single-writer limit unless concurrent agent writes exceed the millisecond turn-taking window. [claim:clm_032]
Git content-addressing names every blob, tree, and commit by the SHA of its own bytes, so any content change changes its key and any commit edit changes every descendant SHA, making history self-verifying and tamper-evident rather than dependent on append-only log discipline. [claim:clm_033]
The derived index in a files-as-truth hybrid is a disposable cache that yields the strongest recovery guarantee of the three postures: git-history regenerates the entire SQLite database deterministically from committed file history, whereas a DB-first store's lost data has no external rebuild source. [claim:clm_034]
File-first/embedded stores share a single-writer ceiling (SQLite serializes to one writer at any instant) and the git-history hybrid materializes every version of every record (10 versions x 30 items = 300 rows), so the derived store grows with history depth times item count. [claim:clm_035]
Obsidian's plain-text local-first vault is editable by any filesystem-aware tool and versionable with stock Git, and an LLM agent can read, grep, and rewrite a Markdown+YAML note with ordinary file operations, whereas a DB-first store requires SQL/stored-procedure semantics and a running engine. [claim:clm_036]
Obsidian is local-first (data stored primarily on the user's local hard disk with Sync as an optional convenience) and connects notes through bidirectional internal links and a Graph view rather than a database schema. [claim:clm_037]
Speculation: multi-agent RF/MeatyWiki swarms will likely be the first workload to breach the file-first single-writer breakpoint, plausibly forcing per-agent branch+merge isolation or a PostgreSQL-backed write coordinator before the corpus itself grows large. [claim:clm_038]
The paper introduces ComEM, a compound entity-matching framework that composes multiple strategies and LLMs to improve both effectiveness and efficiency over single strategies. [claim:clm_039]
The work motivates ComEM by arguing that conventional binary pairwise LLM matching ignores global consistency among record relationships, yielding suboptimal results. [claim:clm_040]
Experiments span 8 entity-resolution datasets and 10 LLMs, and find that incorporating record interactions via the selecting strategy is superior. [claim:clm_041]
ComEM is a two-stage filter-then-identify pipeline: a medium-sized LLM ranks/filters candidates via local matching or comparing, then a more powerful LLM does fine-grained selection on the top-k. [claim:clm_042]
ComEM reaches F1 of 87.62 (Abt-Buy), 69.63 (Amazon-Google), 90.85 (DBLP-ACM), 84.68 (DBLP-Scholar), and 86.37 (Walmart-Amazon). [claim:clm_043]
Supervised baselines reported for comparison are Ditto at 80.69 mean F1 and HierGAT at 83.34 mean F1, both under the Supervised category. [claim:clm_044]
ComEM delivers F1 gains while reducing cost, improving precision without sacrificing the selecting strategy's high recall. [claim:clm_045]
The 10 LLMs evaluated include GPT-4o-mini, GPT-3.5-Turbo, Llama-3.1-8B, Qwen2-7B, Mistral-7B, Mixtral-8x7B, Command-R-35B, Flan-T5-XXL, Flan-UL2, and Solar-10.7B. [claim:clm_046]
The Dedupe class is purpose-built for active learning deduplication of datasets that may contain multiple records referring to the same entity. [claim:clm_047]
Active learning is driven by uncertain_pairs(), which surfaces the record pairs the model is most uncertain about so a human can label them. [claim:clm_048]
Human labels are fed back via mark_pairs(), which adds labeled match/distinct pairs to the training data and updates the matching model, typically incrementally with uncertain_pairs(). [claim:clm_049]
After labeling, train() learns the final pairwise classifier and the fingerprinting (blocking) rules from the accumulated training data. [claim:clm_050]
The probabilistic linkage step is exposed via score(), which assigns each candidate record pair a probability that the pair is a match. [claim:clm_051]
From pairwise similarity scores, cluster() groups records into entity clusters and emits each cluster's record ids alongside per-record confidence scores. [claim:clm_052]
partition() is the end-to-end clustering entry point; it only admits records into a cluster when the cluster's cophenetic similarity exceeds a tunable threshold (default 0.5), trading recall against precision. [claim:clm_053]
The documented release is dedupe 3.0.2, authored by Forest Gregg, Derek Eder, and contributors. [claim:clm_054]
The benchmark comprises 755,540 labeled entity pairs drawn from 293 heterogeneous sources across 31 countries. [claim:clm_055]
The underlying corpus covers 1,002,093 unique entities, each with up to 132 property fields. [claim:clm_056]
The rule-based Nomenklatura baseline reaches 91.33% F1, while the best open-source LLM (DeepSeek-R1-Distill-Qwen-14B) reaches 98.23% F1 and the best proprietary model (GPT-4o) reaches 98.95% F1. [claim:clm_057]
The best-performing prompt frames matching as conflict detection, defaulting to a positive (match) decision unless contradictory evidence is found. [claim:clm_058]
Rule-based and LLM methods exhibit complementary error patterns, with Nomenklatura over-predicting matches and LLMs under-predicting on hard cases such as transliteration. [claim:clm_059]
The authors suggest ensembling rule-based high-recall filtering with LLM re-ranking to exploit the complementary strengths of the two approaches. [claim:clm_060]
Pairwise matching performance is approaching a practical ceiling, motivating a shift of effort toward blocking, clustering, and uncertainty-aware review. [claim:clm_061]
EnsembleLink achieves high-accuracy record linkage with zero labeled training data by leveraging pre-trained language models that have learned semantic relationships from large text corpora. [claim:clm_062]
The pipeline is a three-stage retrieve-and-rerank: union of dense embeddings and sparse character n-grams for high-recall candidate retrieval, then a cross-encoder reranks each query-candidate pair, then the top-scoring candidate is selected. [claim:clm_063]
Because the pre-trained cross-encoder generalizes across domains, no task-specific training or threshold tuning is required and the method can be applied immediately to new linkage tasks without labeled data. [claim:clm_064]
Unlike traditional exact-match blocking, hierarchical blocking fuzzy-matches the blocking variable itself (e.g. matching a misspelled state before searching within it), making blocking robust to the same errors that motivate fuzzy matching. [claim:clm_065]
Without any labeled data, EnsembleLink outperforms both the fastLink (Fellegi-Sunter probabilistic) and supervised fuzzylink baselines on all four political-science benchmark tasks. [claim:clm_066]
On DBLP-Scholar, EnsembleLink reaches 89.0 pair-level F1 at threshold tau=0.8 (matching GPT-4 zero-shot, approaching supervised Ditto 94.3 and DeepMatcher 94.7) and 97.9% top-1 accuracy, all with no training data. [claim:clm_067]
Task-specific fine-tuning of a smaller cross-encoder on 25-300 labeled pairs provides no consistent improvement over the zero-shot pre-trained model, which generalizes effectively without adaptation. [claim:clm_068]
The method runs locally on small open-source models (Qwen3-Embedding-0.6B + Jina Reranker v2 Multilingual) with no external API calls, giving deterministic reproducible results, with accuracy stable at 0.98-0.99 across DBLP-Scholar corpus sizes from 5,000 to 64,263 records. [claim:clm_069]
Splink implements the Fellegi-Sunter / Expectation-Maximisation model as an unsupervised learning algorithm that yields a match score for each pair of record comparisons. [claim:clm_070]
Splink requires no labeled training data because its models can be trained using an unsupervised approach. [claim:clm_071]
Partial match weights can be computed for an arbitrary number of user-defined scenarios (e.g. postcodes within 10 miles of each other), not just binary match or non-match. [claim:clm_072]
A match on date of birth provides more evidence of a match than a match on gender, illustrating that different attributes carry different evidential weight. [claim:clm_073]
The per-attribute partial match weights are combined into an overall match score representing the total weight of evidence that two records are the same. [claim:clm_074]
The documented clustering call resolves pairwise predictions into clusters at a 0.95 match-probability threshold. [claim:clm_075]
Splink is capable of linking very large datasets of over 100 million records using Spark or AWS Athena backends. [claim:clm_076]
The post was originally published on 2020-04-16 and last updated 2022-08-04. [claim:clm_077]
A match-weight threshold partitions record pairs into matches (scores above) and non-matches (scores below). [claim:clm_078]
Precision is maximised by raising the threshold (fewer false positives) and recall by lowering it (fewer false negatives). [claim:clm_079]
Raising the threshold reclassifies some predicted matches as non-matches, converting True Positives to False Negatives and False Positives to True Negatives. [claim:clm_080]
Lowering the threshold to the extreme maximises recall at the cost of precision by generating many more (including false-positive) matches. [claim:clm_081]
The tool visualizes the relationship between match weight and match probability for the scored pairs. [claim:clm_082]
The chart is produced by accuracy_analysis_from_labels_table with output_type='threshold_selection' and optional add_metrics such as f1. [claim:clm_083]

## Inferences

**Inference:** For consolidating semantically equivalent compiled artifacts in a file-first vault, a three-method stack ranks best: a zero-shot retrieve-and-rerank text matcher (EnsembleLink-style) as the primary scorer, Fellegi-Sunter (Splink) as an unsupervised probabilistic backstop, and an LLM-assisted re-ranker (GPT-4o/ComEM-style) reserved for the review band, because this combination needs no labeled training data while spanning the precision/recall/cost frontier. [claim:clm_inf01]
**Inference:** On reported pair-level F1, zero-shot LLM and zero-shot retrieve-rerank methods are statistically comparable to each other and to supervised PLMs on bibliographic data: GPT-4 zero-shot 89.82 and EnsembleLink 89.0 on DBLP-Scholar versus supervised Ditto ~94, so the ~4-5 F1 supervised premium does not justify the labeling cost for a personal vault. [claim:clm_inf02]
**Inference:** Because fine-tuned PLM matchers collapse 22-61% F1 on unseen entities while GPT-4 zero-shot stays robust and beats the best transferred PLM by 34% F1, supervised dedup models should be rejected for an open-ended personal vault whose artifact vocabulary drifts continuously. [claim:clm_inf03]
**Inference:** Pairwise matching is near a practical ceiling (best LLMs ~98-99% F1 on large benchmarks), so the marginal engineering payoff for a file-first vault lies not in a better pair scorer but in blocking, clustering, and the human-review/uncertainty loop. [claim:clm_inf04]
**Inference:** Recommended auto-merge / review-queue / ignore bands for compiled artifacts, expressed on the blended 0-1 confidence scale: auto-merge at >=0.95, human review at 0.80-0.95, and ignore (new entity) below 0.80 -- anchoring on the Ecommerce-Balanced profile but biased toward precision because a wrong auto-merge silently destroys a unique note. [claim:clm_inf05]
**Inference:** The Neo4j 70/30 embedding/fuzzy blend should be extended to a four-signal score for vault artifacts -- approximately body cosine 0.50, title similarity 0.20, provenance (source-card) overlap 0.20, graph-neighborhood (backlink) overlap 0.10 -- because compiled notes carry provenance and link structure that bare entity records lack. [claim:clm_inf06]
**Inference:** Provenance and graph-neighborhood overlap act as a precision multiplier rather than a primary signal: two artifacts compiled from the same source cards or sharing dense backlinks should have their merge confidence boosted into the auto band, while disjoint provenance should cap confidence at the review band even at high body cosine, mirroring same-type gating. [claim:clm_inf07]
**Inference:** Git content-addressing supplies the merge-transaction and rollback primitive a files-as-truth vault needs: each merge is one atomic commit, content-SHA naming makes the pre-merge state tamper-evidently recoverable, and `git revert` is the reversible-merge undo -- so no bespoke transaction log is required. [claim:clm_inf08]
**Inference:** A safe reversible-merge for Markdown-as-truth should: (1) stage all edits then commit as one transaction, (2) rewrite inbound wikilinks/backlinks to the surviving note, (3) leave a redirect-stub note at the merged-away path carrying a SAME_AS-style pointer, and (4) rebuild the derived index from files -- making the operation auditable and undoable via the SAME_AS metadata plus the commit. [claim:clm_inf09]
**Inference:** Survivorship should be field-level, not record-level: keep the title with the higher in-vault backlink count, union (not overwrite) the provenance/source-card lists and tags, prefer the longer-provenance body as the golden record, and route any genuinely conflicting scalar frontmatter (e.g. divergent status) to the human-review queue rather than auto-picking. [claim:clm_inf10]
**Inference:** To stay sub-quadratic to 100K artifacts, candidate generation should use the EnsembleLink-style union of dense-embedding ANN retrieval and sparse character-n-gram (TF-IDF) blocking, optionally wrapped in hierarchical (fuzzy-on-blocking-variable) blocking, rather than Splink-style exact blocking keys, because artifact titles are misspelling- and paraphrase-prone. [claim:clm_inf11]
**Inference:** Splink alone proves blocking-plus-scoring can link ~1M records on a laptop in ~1 minute, so a 100K-artifact vault is comfortably within single-machine, no-big-data-backend reach; the constraining cost is embedding generation, not pair comparison. [claim:clm_inf12]
**Inference:** A personal KB has far lower duplicate prevalence than the balanced ER benchmarks (where positives are engineered to ~ tens of percent), so the prior match probability lambda is small; this class imbalance means the optimal operating point should sit higher than benchmark-tuned thresholds, because even a modest false-positive rate dominates the rare true matches. [claim:clm_inf13]
**Inference:** The review queue should be calibrated by dedupe-style active learning (uncertain_pairs -> human label -> retrain) rather than fixed bands, because human decisions on the most uncertain artifact pairs are exactly the labels that retune the scorer and the band edges over time, converting the unavoidable review effort into model improvement. [claim:clm_inf14]
**Inference:** Operational health metrics should gate the bands: keep auto-merge rejection (false-auto-merge) rate below 2% by raising the auto threshold if breached, target a 60-90% flag-to-confirm rate to keep the review band well-calibrated, and watch orphan/redirect-stub rate below ~10% -- these act as the closed-loop controller for the otherwise-static thresholds. [claim:clm_inf15]
**Inference:** The cost/quality decision rule is tiered by band: run the cheap local zero-shot scorer (dense+sparse retrieve, small open cross-encoder) over all candidate pairs, and invoke an expensive proprietary LLM (GPT-4o/ComEM selecting) only on the review band's top-k -- mirroring ComEM's filter-then-identify pipeline that gained 2-18% F1 while spending less. [claim:clm_inf16]
**Inference:** Determinism and reproducibility favor a fixed-weight local model (EnsembleLink on Qwen3-Embedding-0.6B + Jina reranker) over hosted GPT-4-class APIs for the always-on scorer, because hosted LLM results drift across API snapshots whereas pinned open weights give byte-stable, Git-auditable merge decisions consistent with files-as-truth. [claim:clm_inf17]

## Speculation

**Speculation:** Speculation: as a personal vault grows past ~10K compiled artifacts, the dominant failure mode will shift from missed duplicates to over-merging distinct-but-similar notes, because dense-embedding similarity saturates among topically clustered notes; pre-emptive provenance/graph gating (clm_inf07) will become necessary to hold precision. [claim:clm_spec01]
**Speculation:** Speculation: multi-agent RF/MeatyWiki swarms running auto-merge concurrently will breach the file-first single-writer ceiling before the corpus size does, likely forcing per-agent branch+merge isolation or a merge-coordinator queue so that two agents never rewrite the same backlink graph in the same instant. [claim:clm_spec02]

## Open questions

- None recorded.

## Sources

- src_20260614_rib035_06: Entity Resolution and Deduplication — Neo4j Agent Memory
- src_20260614_rib035_04: Entity Matching using Large Language Models
- src_20260614_rib035_01: The Fellegi-Sunter Model
- src_20260614_rib035_03: Python Record Linkage Toolkit 0.15 documentation - About
- src_20260614_rib035_00: Splink: Fast, accurate and scalable probabilistic data linkage with support for multiple SQL backends (MoJ Analytical Services)
- src_20260614_rib035_11: File-first vs DB-first architectures for LLM knowledge bases (RIB-037 seed report)
- src_20260614_rib035_05: Match, Compare, or Select? An Investigation of Large Language Models for Entity Matching
- src_20260614_rib035_02: dedupe 3.0.2 Library Documentation
- src_20260614_rib035_09: OpenSanctions Pairs: Large-Scale Entity Matching with LLMs
- src_20260614_rib035_10: EnsembleLink: Accurate Record Linkage Without Training Data
- src_20260614_rib035_08: Fuzzy Matching and Deduplicating Hundreds of Millions of Records with Splink
- src_20260614_rib035_07: Threshold Selection Tool — Splink documentation
