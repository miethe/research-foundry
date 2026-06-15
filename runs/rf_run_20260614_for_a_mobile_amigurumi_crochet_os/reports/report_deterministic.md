---
schema_version: '0.1'
type: research_report
report_id: report_20260614_for_a_mobile_amigurumi_crochet_os
title: For a mobile amigurumi crochet OS that shows
intent_id: intent_research_20260614_for_a_mobile_amigurumi_crochet_os
evidence_bundle_id: pending
created_at: '2026-06-14T23:47:30-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Reliance on a model is not driven by uncertainty alone; it depends jointly on task difficulty and the level of machine uncertainty. [claim:clm_001]
The study tested two uncertainty visualization techniques in a college-admissions forecasting task across two task-difficulty levels on Amazon Mechanical Turk. [claim:clm_002]
Failure to calibrate trust causes over-reliance or under-reliance on model outputs, both of which diminish the benefits of a joint human-automation system. [claim:clm_003]
Without appropriate interventions, people are heavily biased to adopt imperfect human judgments over imperfect models, making trust-calibration interventions decisive. [claim:clm_004]
Five visual representations were compared, grouped into three categories: Table and Histogram (no model prediction), Model-prediction (prediction only), and Violin Plot and Question-mark (which include uncertainty). [claim:clm_005]
A simple ordinal uncertainty representation (Question-mark) is generally sufficient and more cognitively accessible to general audiences than continuous probability distributions, even though richer detail (Violin Plot) is perceived as more trustworthy. [claim:clm_006]
Prior evaluations of transit uncertainty displays measured probability extraction, not decision quality, which this study set out to assess directly. [claim:clm_007]
In a controlled incentivized experiment, subjects decided when to leave to catch a bus using textual uncertainty, uncertainty visualizations, or a no-uncertainty control. [claim:clm_008]
Frequency-based quantile dotplots, previously shown to aid probability extraction, yielded better decisions than the alternatives. [claim:clm_009]
Quantile dotplots with 50 outcomes produced decisions averaging 97% of optimal expected payoff, 5 percentage points above the control. [claim:clm_010]
CDF plots performed nearly as well as quantile dotplots, and both beat textual uncertainty, whose effectiveness depended on the probability interval communicated. [claim:clm_011]
Quantile dotplots reframe a probability density as countable discrete outcomes, letting non-experts reason about probabilities as counts rather than areas, well suited to space-constrained mobile displays. [claim:clm_012]
Decision quality with dotplots and CDFs was high from the start and improved with practice, reaching about 95% of optimal by the final trial while becoming more consistent. [claim:clm_013]
CrochetPARADE animates pattern creation by revealing stitches one-by-one ('a') and hiding them one-by-one (ctrl+a), a direct precedent for row-by-row playback and ghost-next-row overlay. [claim:clm_014]
The renderer encodes working order via blue connections with arrowheads and shows all remaining stitch relationships as red connections, visualizing how stitches attach rather than why counts change. [claim:clm_015]
The tool can highlight a specific row or individual stitch (ctrl+f), highlight stitches by label (ctrl+d), and hide everything after a chosen row/stitch (ctrl+h) -- primitives for checkpoint surfacing and piece isolation. [claim:clm_016]
The 's' key flags over/under-stretched stitches (blue = too loose, red = too tight by more than ~15%), an existing tension/gauge confidence signal surfaced before crocheting. [claim:clm_017]
Hovering a stitch reveals its row and stitch number plus the stitch type in brackets, and shift+left-click pins a persistent info box -- an inline per-stitch rationale affordance. [claim:clm_018]
The manual documents no feature that explains why a stitch or decrease count changed, nor any post-hoc analysis of increase/decrease distribution rationale across rounds -- defining the explainability whitespace for KnitWit. [claim:clm_019]
The study operationalized three confidence conditions against a fixed 70% AI accuracy: underconfident (60% stated confidence), well-calibrated (70%), and overconfident (80%). [claim:clm_020]
Overconfident AI raised the user switch-to-AI rate to ~69.6% versus ~57% for well-calibrated AI, while underconfident AI lowered it to ~40.5%. [claim:clm_021]
Overconfident AI increased over-reliance to ~41.3% versus ~28.2% for well-calibrated AI. [claim:clm_022]
Underconfident AI increased under-reliance to ~17.7% versus ~11.2% for well-calibrated AI. [claim:clm_023]
Decision-accuracy improvement fell to ~6.5% (underconfident) and ~7.2% (overconfident) versus ~11.9% for well-calibrated confidence. [claim:clm_024]
Users could not detect miscalibration on their own: 66.7% wrongly judged an underconfident AI well-calibrated and 64.3% made the same error for an overconfident AI. [claim:clm_025]
Explicitly communicating the calibration level improved detection (76.2% correctly identified underconfidence) but decreased trust in uncalibrated AI and did not improve overall decision efficacy. [claim:clm_026]
StitchFlow is a peer-reviewed full paper by Zofia Marciniak, Punn Lertjaturaphat, and Andrea Bianchi, published Open Access (CC BY 4.0) in the Proceedings of the 38th Annual ACM Symposium on User Interface Software and Technology (UIST '25). [claim:clm_027]
The paper identifies documenting patterns, tracking progress, and backtracking from mistakes or mid-process changes as the specific tasks that disrupt a crocheter's creative flow. [claim:clm_028]
StitchFlow uses a motion sensor to track real-time hand gestures and reconstruct the stitch pattern, letting crocheters work in situ without distraction or needing to remember previous steps. [claim:clm_029]
The system automatically constructs process documentation that can be composed and exported as traditional written patterns and crochet charts, or as shareable in-system flows other users can follow. [claim:clm_030]
A user study with 8 crocheters found StitchFlow preserved makers' creative flow, enabled spontaneous exploration, and facilitated pattern sharing. [claim:clm_031]
The paper frames pattern documentation as requiring makers to pause, count stitches, take notes, and mentally interpret notations, and argues these interruptions break the immersive flow essential to creative exploration. [claim:clm_032]
Crochet patterns are conventionally shared in two flat representations -- written notation and symbol-based charts -- and proficiency in one format does not necessarily transfer to fluency in the other. [claim:clm_033]
The paper notes crochet has uniquely resisted mechanization because no machines can fully replicate the hand movements required to manipulate stitches, keeping it an inherently human, improvisational skill. [claim:clm_034]
CrochetBench evaluates whether multimodal models can shift from describing visual content to generating executable crochet procedures via fine-grained procedural reasoning. [claim:clm_035]
Model performance drops sharply when evaluation moves from surface-level similarity to executable correctness, exposing gaps in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_036]
The benchmark adopts the CrochetPARADE DSL as an intermediate representation, enabling structural validation and functional evaluation by executing the generated procedures. [claim:clm_037]
A range of vision-language models were benchmarked, including GPT-4o, Gemini 2.5 Flash-Lite, Claude Sonnet 4, Qwen2-VL, DeepSeek-VL, BLIP-2, and Gemma 3. [claim:clm_038]
One execution failure category is Turning Issues, where models misplace turning/orientation commands, since turning is only valid at the end of a row. [claim:clm_039]
A second failure category is Multiplier Issues, where repeat/scaling multipliers are improperly formatted and not bound to a stitch. [claim:clm_040]
Textual under-specification matters: valid human-written patterns can be penalized because the DSL or rendering cannot capture implicit conventions experienced crafters apply. [claim:clm_041]
The paper frames appropriate reliance on AI as a human-centered problem and intervenes via 'human self-confidence calibration,' structured as three studies. [claim:clm_042]
Calibrating human self-confidence improved human-AI team performance and led to more rational reliance on AI versus an uncalibrated baseline. [claim:clm_043]
The paper treats trust and reliance as separable constructs: trust is a subjective self-reported attitude toward the AI, while reliance is the objective behavior of acting on its recommendation. [claim:clm_044]
Inappropriate reliance is split into over-reliance (agreeing with AI when it is wrong) and under-reliance (rejecting AI when it is right), giving measurable behavioral targets. [claim:clm_045]
In study 3, self-confidence calibration produced more rational reliance and reduced under-reliance and improved task performance, but did not reduce over-reliance. [claim:clm_046]
Self-reported trust does not reliably track reliance behavior, so the authors study reliance behavior as the more dependable indicator of appropriateness. [claim:clm_047]
AmiGo generates human-crochetable amigurumi instructions from only a closed triangle mesh plus a single user-specified seed point. [claim:clm_048]
Beyond the mesh and seed point, the method takes a target stitch width w as an input parameter that parameterizes the generated instructions. [claim:clm_049]
AmiGo builds a Crochet Graph (geometry plus connectivity) as an explicit intermediate representation that is then translated into the written round-by-round pattern. [claim:clm_050]
The Crochet Graph encodes stitches as graph elements: vertices are stitch tops/bases, column edges are stitch stems, and row edges connect bases within a row, making the IR inspectable. [claim:clm_051]
Shaping is procedural: curvature is realized by increase and decrease stitches derived from the graph geometry rather than specified arbitrarily. [claim:clm_052]
The shape is automatically segmented into separate crochetable components that are joined by the join-as-you-go method, requiring no additional sewing. [claim:clm_053]
Overconfident AI raised over-reliance to ~41.3% versus ~28.2% for well-calibrated output, a statistically significant increase. [claim:clm_054]
Underconfident AI raised under-reliance to ~17.7% versus ~11.2% for well-calibrated output, a statistically significant increase. [claim:clm_055]
Miscalibration shrank accuracy gains: underconfident AI yielded +6.5% and overconfident +7.2% versus +11.9% for well-calibrated AI, both significant reductions. [claim:clm_056]
AI confidence directly moved switching behavior: switch-to-AI rate fell to ~40.5% under underconfidence versus ~57.0% well-calibrated and rose to ~69.6% under overconfidence. [claim:clm_057]
Disclosing calibration level sharply improved detection: 73.8% correctly flagged the AI as overconfident, up from 26.2% without disclosure. [claim:clm_058]
Despite better detection, disclosure yielded no decision-efficacy gain because it increased under-reliance on overconfident AI. [claim:clm_059]
The authors recommend telling users WHY and under what conditions confidence may be unreliable, not just surfacing a bare confidence number. [claim:clm_060]
Experiment 1 used 126 unique participants split across conditions (42 per condition). [claim:clm_061]
Explanations promoted for transparency can instead foster confirmation bias, with users assuming the reasoning is correct whenever the output looks acceptable. [claim:clm_062]
The study probes the double-edged role of Chain-of-Thought explanations in multimodal moral scenarios by perturbing reasoning chains and manipulating delivery tones in vision language models. [claim:clm_063]
Users tend to equate trust with agreeing on the outcome, so they keep relying on the system even when the underlying reasoning is flawed. [claim:clm_064]
A confident delivery tone suppresses users' detection of errors while preserving reliance, showing presentation style can override correctness. [claim:clm_065]
CoT explanations can simultaneously clarify and mislead, so NLP systems should present explanations that encourage scrutiny and critical thinking rather than blind trust. [claim:clm_066]
Visualizing AI uncertainty significantly enhanced trust for 58% of participants who held negative attitudes toward AI. [claim:clm_067]
Across the full sample of 147 participants, displaying uncertainty increased trust in AI for 48% (n=70). [claim:clm_068]
Size-based uncertainty encoding had a significantly greater impact on trust than transparency (p < 0.05). [claim:clm_069]
Color saturation was rated highest for intuition and preference, ahead of transparency and size. [claim:clm_070]
Displaying AI uncertainty raised decision confidence for 44% of participants but lowered it for 56%. [claim:clm_071]
One-third of participants (33%, n=48) changed their responses after seeing the AI prediction's uncertainty. [claim:clm_072]
The authors decline to endorse any single uncertainty visualization technique or to push users toward trusting AI, cautioning against over-trust. [claim:clm_073]
The study is a survey-based between-subjects experiment with 300 participants (150 per task) classifying familiar and unfamiliar stimuli with a simulated AI of varying accuracy across geometric-shape and animal-identification tasks. [claim:clm_074]
Once trust was eroded, Model Update restored trust above its initial level, followed by Apology, Promise, and the no-repair baseline, with Denial being least effective. [claim:clm_075]
Most participants used the AI's accuracy on familiar (high-human-expertise) stimuli as a heuristic to calibrate their trust in its output for unfamiliar (low-human-expertise) stimuli they could not independently verify. [claim:clm_076]
When indicators of an AI's performance are not provided, individuals tend to over-rely on the AI regardless of its actual accuracy, even when explanations are provided. [claim:clm_077]
Early system errors disproportionately shape trust for the whole interaction, causing negative trust outcomes even if accuracy later improves, so first impressions are weighted more heavily. [claim:clm_078]
The authors adopt Lee and See's definition of trust as an attitude that an agent will achieve a goal under uncertainty and vulnerability. [claim:clm_079]
Denial was the least effective repair strategy across both tasks, backfiring and prompting users to distrust the AI despite improved accuracy, with trust similar to the lowest-accuracy phase. [claim:clm_080]
Model Update outperformed Promise despite identical AI accuracy, restoring trust above its Phase 1 starting level, while Promise was merely as effective as the no-repair baseline. [claim:clm_081]

## Inferences

**Inference:** KnitWit's confidence meter should adopt a coarse ordinal scale (e.g., a 3-level high/medium/low or question-mark-style marker) rather than a continuous percentage or probability distribution, because ordinal uncertainty representations both calibrate usage behavior better and are more cognitively accessible to non-expert makers. [claim:clm_inf01]
**Inference:** For per-round approximate-3D fit confidence, a frequency-framed quantile dotplot (e.g., '47 of 50 simulated tensions fit this round') is the strongest mobile-suitable encoding, because dotplots reached ~97% of optimal decision payoff (5 points above control) and CDFs nearly matched them, both beating textual probability. [claim:clm_inf02]
**Inference:** A bare confidence number on an approximate preview is insufficient and potentially harmful for KnitWit; the meter must pair every confidence signal with a 'why this is approximate / under what conditions it may be wrong' explanation, because disclosing only a calibration number improved detection but did not improve decision efficacy and could erode trust. [claim:clm_inf03]
**Inference:** KnitWit's previews must be deliberately calibrated and never made to look more authoritative than the evidence supports, because overconfident outputs drove over-reliance to ~41% (vs ~28% well-calibrated) and underconfident outputs drove under-reliance to ~18% (vs ~11%), with both miscalibration directions roughly halving the accuracy benefit (to ~6.5-7.2% vs ~11.9%). [claim:clm_inf04]
**Inference:** The single highest-leverage trust risk for KnitWit is the first visible approximate-preview error: because early system errors disproportionately shape whole-interaction trust and denial backfires, the app should front-load its lowest-uncertainty shapes (spheres/heads) in onboarding and, after any visible mismatch, repair via a concrete 'model update / recalculated' fix rather than apology or denial. [claim:clm_inf05]
**Inference:** Because makers cannot independently verify an approximate 3D preview of a shape they have not yet crocheted, they will transfer trust from cases they CAN verify (simple verified spheres/heads) to ones they cannot, so KnitWit's perceived accuracy on its easiest previews becomes the de facto trust anchor for its hardest ones. [claim:clm_inf06]
**Inference:** Crochet's two incumbent flat representations (written notation and symbol charts) plus documented under-specification of human patterns are the root cause of the 'ambiguous/under-specified pattern text' failure-mode cluster, and a machine-checkable Crochet IR with explicit per-round expected_stitch_count is the direct mitigation because it forces the implicit conventions to be made explicit. [claim:clm_inf07]
**Inference:** CrochetBench's DSL error taxonomy maps directly onto the validators KnitWit must ship: 'Turning Issues' (turns only valid at row end) and 'Multiplier Issues' (repeat multipliers not bound to a stitch) correspond to required structural checks on the IR's repeat op and round/row boundaries, making these the first two stitch-count/structure validators to build (de-risking gate G2). [claim:clm_inf08]
**Inference:** The explainability whitespace for KnitWit is precisely defined: existing best-in-class tooling (CrochetPARADE) shows how stitches attach, where tension fails, and per-stitch metadata, but no tool explains WHY a stitch/decrease count changed or analyzes inc/dec distribution rationale, so the 'why did the stitch count change' and 'where/why are increases distributed' features are a genuine, defensible product wedge rather than a re-implementation. [claim:clm_inf09]
**Inference:** KnitWit can ground its 'where/why are increases distributed' explanation in AmiGo's Crochet Graph: because shaping (inc/dec) is derived procedurally from graph geometry/curvature and each stitch is an inspectable graph element, the app can attribute each increase to the local curvature that required it, turning an internal geometric fact into a per-round natural-language rationale. [claim:clm_inf10]
**Inference:** Surfacing procedural reasoning (a CoT-style 'why the count changed' overlay) is double-edged for KnitWit: it can satisfy the explainability requirement but also induce confirmation bias and over-reliance, so the explanation UI must invite scrutiny (e.g., show the stitch-count check, flag where the model is least sure) rather than narrate with a confident authoritative tone that suppresses error detection. [claim:clm_inf11]
**Inference:** Reliance and trust must be measured as separate KnitWit UX acceptance signals, and reliance behavior (acted-on previews) is the more dependable acceptance metric than self-reported trust, with over-reliance (following a wrong preview) and under-reliance (rejecting a correct one) as the two concrete failure metrics to instrument. [claim:clm_inf12]
**Inference:** A defensible KnitWit UX acceptance protocol can be assembled from the cited studies: task-completion / decision-payoff (% of optimal, per Fernandes et al.), over-reliance and under-reliance rates and switch-to-recommendation rate (per Li et al. / Ma et al.), a trust-repair recovery check after an induced visible error (per Pareek et al.), and Lee-and-See-framed trust attitude scales as a secondary self-report. [claim:clm_inf13]
**Inference:** CrochetPARADE's existing primitives are directly adoptable as KnitWit forward-preview surfaces: stitch-by-stitch reveal/hide ('a'/ctrl+a) for row-by-row playback and ghost-next-row overlay, row/stitch highlight (ctrl+f) and hide-after (ctrl+h) for checkpoints and piece isolation, and the 's' over/under-stretched flag (>~15%) as a ready-made tension/gauge confidence signal surfaced before crocheting. [claim:clm_inf14]
**Inference:** The mesh-to-pattern generator should be classified as academically feasible but not product-ready: AmiGo demonstrates closed-mesh + seed-point + stitch-width generation with join-as-you-go in a research paper, but no cited evidence establishes mobile runtime cost, watertight-mesh robustness for casual user inputs, or maker-perceived crochetability, leaving gate G4 (mesh-to-pattern primitive) the most under-evidenced gate. [claim:clm_inf15]
**Inference:** An apparent tension exists between 'show uncertainty to build trust' and 'showing uncertainty lowered decision confidence for the majority': the likely resolution is that uncertainty display reliably aids trust and decision quality when encoded as ordinal/discrete frequency forms but can depress raw confidence when shown as ambiguous continuous signals, so the decision impact is medium and argues for KnitWit using discrete/ordinal encodings. [claim:clm_inf16]
**Inference:** Left-handed mirroring is an evidence-gap in this corpus: none of the gathered sources document handedness/left-mirroring handling in crochet tooling or HCI, so KnitWit's mirrored-experience correctness requirements cannot yet be grounded in cited evidence and remain an open question requiring dedicated source discovery before any G5 MVP commitment. [claim:clm_inf17]

## Speculation

**Speculation:** Because StitchFlow's in-situ stitch tracking preserved creative flow for makers (n=8) and CrochetPARADE already flags over-stretched stitches, KnitWit could plausibly convert a phone-camera or sensor swatch-measurement step into a low-friction gauge-calibration onboarding that feeds stitch-width into AmiGo-style generation, but completion-rate and downstream-fit evidence does not yet exist and must be measured. [claim:clm_spec01]
**Speculation:** Forward-looking risk (severity high, likelihood medium): the 'it lied to me' trust-collapse from a visible approximate-preview error may be more damaging for an emotionally invested hobby craft than the lab studies suggest, because makers commit hours of physical yarn before discovering a mismatch; mitigation is to label previews 'approximate' up front, lead with verified shapes, and offer an instant recalculated fix. Labeled speculation. [claim:clm_spec02]
**Speculation:** KnitWit's approximate-3D preview should be positioned as a 'forecast under known uncertainty' rather than a 'photo of the finished object', and the most de-risking next experiment is EXP-005/EXP-010 (stitch-graph to approximate 3D and the mesh to pattern to visualizer round-trip) instrumented with a discrete-frequency fit-confidence display and an over/under-reliance measure, because this jointly tests gates G3 and the trust-encoding hypotheses on the same artifact. [claim:clm_spec03]

## Open questions

- None recorded.

## Sources

- src_20260614_kw010_04: Evaluating the Impact of Uncertainty Visualization on Model Reliance
- src_20260614_kw010_06: Uncertainty Displays Using Quantile Dotplots or CDFs Improve Transit Decision-Making
- src_20260614_kw010_09: CrochetPARADE Manual (Pattern Renderer, Analyzer, and Debugger)
- src_20260614_kw010_03: Understanding the Effects of Miscalibrated AI Confidence on User Trust, Reliance, and Decision Efficacy
- src_20260614_kw010_01: StitchFlow: Enabling In-Situ Creative Explorations of Crochet Patterns With Stitch Tracking and Process Sharing
- src_20260614_kw010_00: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw010_07: “Are You Really Sure?” Understanding the Effects of Human Self-Confidence Calibration in AI-Assisted Decision Making
- src_20260614_kw010_08: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw010_10: Understanding the Effects of Miscalibrated AI Confidence on User Trust, Reliance, and Decision Efficacy
- src_20260614_kw010_11: Critical or Compliant? The Double-Edged Sword of Reasoning in Chain-of-Thought Explanations
- src_20260614_kw010_02: Trusting AI: does uncertainty visualization affect decision-making?
- src_20260614_kw010_05: Trust Development and Repair in AI-Assisted Decision-Making during Complementary Expertise
