---
id: mwb_20260622_dr_trust_first_ux_for_an
evidence_bundle_id: bundle_20260615_intent_research_20260614_for_a_mobile
target_page: meatywiki/decisions/trust_first_ux_for_an_amigurumi.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_for_a_mobile_amigurumi_crochet_os: Zhao et al. (TVCG
  2023) found ordinal forms (Question-mark) calibrate model-usage behavior and are more accessible than '
key_claims:
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf17
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_001
  - clm_006
  - clm_011
  - clm_012
  - clm_009
  - clm_010
  - clm_013
  - clm_026
  - clm_058
  - clm_059
  - clm_060
  - clm_078
  - clm_075
  - clm_080
  - clm_081
  - clm_039
  - clm_040
  - clm_037
  - clm_036
  - clm_050
  - clm_051
  - clm_052
  - clm_049
  - clm_062
  - clm_064
  - clm_065
  - clm_066
  - clm_044
  - clm_045
  - clm_047
  - clm_003
  - clm_021
  - clm_079
  - clm_022
  - clm_023
  - clm_024
  - clm_054
  - clm_055
  - clm_056
  - clm_076
  - clm_077
  - clm_033
  - clm_032
  - clm_041
  - clm_015
  - clm_018
  - clm_019
  - clm_014
  - clm_016
  - clm_017
  - clm_048
  - clm_053
  - clm_067
  - clm_071
  - clm_034
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Trust-First UX for an Amigurumi Crochet OS: A Failure-Mode Catalog, Explainability Primitives, and Confidence/Calibration Design Rules Grounded in Craft-Tech and HCI Evidence

## Context

- Reliance on a model is not driven by uncertainty alone; it depends jointly on task difficulty and the level of machine uncertainty. [claim:clm_001]
- The study tested two uncertainty visualization techniques in a college-admissions forecasting task across two task-difficulty levels on Amazon Mechanical Turk. [claim:clm_002]
- Failure to calibrate trust causes over-reliance or under-reliance on model outputs, both of which diminish the benefits of a joint human-automation system. [claim:clm_003]
- Without appropriate interventions, people are heavily biased to adopt imperfect human judgments over imperfect models, making trust-calibration interventions decisive. [claim:clm_004]
- Five visual representations were compared, grouped into three categories: Table and Histogram (no model prediction), Model-prediction (prediction only), and Violin Plot and Question-mark (which include uncertainty). [claim:clm_005]
- A simple ordinal uncertainty representation (Question-mark) is generally sufficient and more cognitively accessible to general audiences than continuous probability distributions, even though richer detail (Violin Plot) is perceived as more trustworthy. [claim:clm_006]
- Prior evaluations of transit uncertainty displays measured probability extraction, not decision quality, which this study set out to assess directly. [claim:clm_007]
- In a controlled incentivized experiment, subjects decided when to leave to catch a bus using textual uncertainty, uncertainty visualizations, or a no-uncertainty control. [claim:clm_008]
- Frequency-based quantile dotplots, previously shown to aid probability extraction, yielded better decisions than the alternatives. [claim:clm_009]
- Quantile dotplots with 50 outcomes produced decisions averaging 97% of optimal expected payoff, 5 percentage points above the control. [claim:clm_010]
- CDF plots performed nearly as well as quantile dotplots, and both beat textual uncertainty, whose effectiveness depended on the probability interval communicated. [claim:clm_011]
- Quantile dotplots reframe a probability density as countable discrete outcomes, letting non-experts reason about probabilities as counts rather than areas, well suited to space-constrained mobile displays. [claim:clm_012]
- Decision quality with dotplots and CDFs was high from the start and improved with practice, reaching about 95% of optimal by the final trial while becoming more consistent. [claim:clm_013]
- CrochetPARADE animates pattern creation by revealing stitches one-by-one ('a') and hiding them one-by-one (ctrl+a), a direct precedent for row-by-row playback and ghost-next-row overlay. [claim:clm_014]
- The renderer encodes working order via blue connections with arrowheads and shows all remaining stitch relationships as red connections, visualizing how stitches attach rather than why counts change. [claim:clm_015]
- The tool can highlight a specific row or individual stitch (ctrl+f), highlight stitches by label (ctrl+d), and hide everything after a chosen row/stitch (ctrl+h) -- primitives for checkpoint surfacing and piece isolation. [claim:clm_016]
- The 's' key flags over/under-stretched stitches (blue = too loose, red = too tight by more than ~15%), an existing tension/gauge confidence signal surfaced before crocheting. [claim:clm_017]
- Hovering a stitch reveals its row and stitch number plus the stitch type in brackets, and shift+left-click pins a persistent info box -- an inline per-stitch rationale affordance. [claim:clm_018]
- The manual documents no feature that explains why a stitch or decrease count changed, nor any post-hoc analysis of increase/decrease distribution rationale across rounds -- defining the explainability whitespace for KnitWit. [claim:clm_019]
- The study operationalized three confidence conditions against a fixed 70% AI accuracy: underconfident (60% stated confidence), well-calibrated (70%), and overconfident (80%). [claim:clm_020]
- Overconfident AI raised the user switch-to-AI rate to ~69.6% versus ~57% for well-calibrated AI, while underconfident AI lowered it to ~40.5%. [claim:clm_021]
- Overconfident AI increased over-reliance to ~41.3% versus ~28.2% for well-calibrated AI. [claim:clm_022]
- Underconfident AI increased under-reliance to ~17.7% versus ~11.2% for well-calibrated AI. [claim:clm_023]
- Decision-accuracy improvement fell to ~6.5% (underconfident) and ~7.2% (overconfident) versus ~11.9% for well-calibrated confidence. [claim:clm_024]
- Users could not detect miscalibration on their own: 66.7% wrongly judged an underconfident AI well-calibrated and 64.3% made the same error for an overconfident AI. [claim:clm_025]
- Explicitly communicating the calibration level improved detection (76.2% correctly identified underconfidence) but decreased trust in uncalibrated AI and did not improve overall decision efficacy. [claim:clm_026]
- StitchFlow is a peer-reviewed full paper by Zofia Marciniak, Punn Lertjaturaphat, and Andrea Bianchi, published Open Access (CC BY 4.0) in the Proceedings of the 38th Annual ACM Symposium on User Interface Software and Technology (UIST '25). [claim:clm_027]
- The paper identifies documenting patterns, tracking progress, and backtracking from mistakes or mid-process changes as the specific tasks that disrupt a crocheter's creative flow. [claim:clm_028]
- StitchFlow uses a motion sensor to track real-time hand gestures and reconstruct the stitch pattern, letting crocheters work in situ without distraction or needing to remember previous steps. [claim:clm_029]
- The system automatically constructs process documentation that can be composed and exported as traditional written patterns and crochet charts, or as shareable in-system flows other users can follow. [claim:clm_030]
- A user study with 8 crocheters found StitchFlow preserved makers' creative flow, enabled spontaneous exploration, and facilitated pattern sharing. [claim:clm_031]
- The paper frames pattern documentation as requiring makers to pause, count stitches, take notes, and mentally interpret notations, and argues these interruptions break the immersive flow essential to creative exploration. [claim:clm_032]
- Crochet patterns are conventionally shared in two flat representations -- written notation and symbol-based charts -- and proficiency in one format does not necessarily transfer to fluency in the other. [claim:clm_033]
- The paper notes crochet has uniquely resisted mechanization because no machines can fully replicate the hand movements required to manipulate stitches, keeping it an inherently human, improvisational skill. [claim:clm_034]
- CrochetBench evaluates whether multimodal models can shift from describing visual content to generating executable crochet procedures via fine-grained procedural reasoning. [claim:clm_035]
- Model performance drops sharply when evaluation moves from surface-level similarity to executable correctness, exposing gaps in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_036]
- The benchmark adopts the CrochetPARADE DSL as an intermediate representation, enabling structural validation and functional evaluation by executing the generated procedures. [claim:clm_037]
- A range of vision-language models were benchmarked, including GPT-4o, Gemini 2.5 Flash-Lite, Claude Sonnet 4, Qwen2-VL, DeepSeek-VL, BLIP-2, and Gemma 3. [claim:clm_038]
- One execution failure category is Turning Issues, where models misplace turning/orientation commands, since turning is only valid at the end of a row. [claim:clm_039]
- A second failure category is Multiplier Issues, where repeat/scaling multipliers are improperly formatted and not bound to a stitch. [claim:clm_040]
- Textual under-specification matters: valid human-written patterns can be penalized because the DSL or rendering cannot capture implicit conventions experienced crafters apply. [claim:clm_041]
- The paper frames appropriate reliance on AI as a human-centered problem and intervenes via 'human self-confidence calibration,' structured as three studies. [claim:clm_042]
- Calibrating human self-confidence improved human-AI team performance and led to more rational reliance on AI versus an uncalibrated baseline. [claim:clm_043]
- The paper treats trust and reliance as separable constructs: trust is a subjective self-reported attitude toward the AI, while reliance is the objective behavior of acting on its recommendation. [claim:clm_044]
- Inappropriate reliance is split into over-reliance (agreeing with AI when it is wrong) and under-reliance (rejecting AI when it is right), giving measurable behavioral targets. [claim:clm_045]
- In study 3, self-confidence calibration produced more rational reliance and reduced under-reliance and improved task performance, but did not reduce over-reliance. [claim:clm_046]
- Self-reported trust does not reliably track reliance behavior, so the authors study reliance behavior as the more dependable indicator of appropriateness. [claim:clm_047]
- AmiGo generates human-crochetable amigurumi instructions from only a closed triangle mesh plus a single user-specified seed point. [claim:clm_048]
- Beyond the mesh and seed point, the method takes a target stitch width w as an input parameter that parameterizes the generated instructions. [claim:clm_049]
- AmiGo builds a Crochet Graph (geometry plus connectivity) as an explicit intermediate representation that is then translated into the written round-by-round pattern. [claim:clm_050]
- The Crochet Graph encodes stitches as graph elements: vertices are stitch tops/bases, column edges are stitch stems, and row edges connect bases within a row, making the IR inspectable. [claim:clm_051]
- Shaping is procedural: curvature is realized by increase and decrease stitches derived from the graph geometry rather than specified arbitrarily. [claim:clm_052]
- The shape is automatically segmented into separate crochetable components that are joined by the join-as-you-go method, requiring no additional sewing. [claim:clm_053]
- Overconfident AI raised over-reliance to ~41.3% versus ~28.2% for well-calibrated output, a statistically significant increase. [claim:clm_054]
- Underconfident AI raised under-reliance to ~17.7% versus ~11.2% for well-calibrated output, a statistically significant increase. [claim:clm_055]
- Miscalibration shrank accuracy gains: underconfident AI yielded +6.5% and overconfident +7.2% versus +11.9% for well-calibrated AI, both significant reductions. [claim:clm_056]
- AI confidence directly moved switching behavior: switch-to-AI rate fell to ~40.5% under underconfidence versus ~57.0% well-calibrated and rose to ~69.6% under overconfidence. [claim:clm_057]
- Disclosing calibration level sharply improved detection: 73.8% correctly flagged the AI as overconfident, up from 26.2% without disclosure. [claim:clm_058]
- Despite better detection, disclosure yielded no decision-efficacy gain because it increased under-reliance on overconfident AI. [claim:clm_059]
- The authors recommend telling users WHY and under what conditions confidence may be unreliable, not just surfacing a bare confidence number. [claim:clm_060]
- Experiment 1 used 126 unique participants split across conditions (42 per condition). [claim:clm_061]
- Explanations promoted for transparency can instead foster confirmation bias, with users assuming the reasoning is correct whenever the output looks acceptable. [claim:clm_062]
- The study probes the double-edged role of Chain-of-Thought explanations in multimodal moral scenarios by perturbing reasoning chains and manipulating delivery tones in vision language models. [claim:clm_063]
- Users tend to equate trust with agreeing on the outcome, so they keep relying on the system even when the underlying reasoning is flawed. [claim:clm_064]
- A confident delivery tone suppresses users' detection of errors while preserving reliance, showing presentation style can override correctness. [claim:clm_065]
- CoT explanations can simultaneously clarify and mislead, so NLP systems should present explanations that encourage scrutiny and critical thinking rather than blind trust. [claim:clm_066]
- Visualizing AI uncertainty significantly enhanced trust for 58% of participants who held negative attitudes toward AI. [claim:clm_067]
- Across the full sample of 147 participants, displaying uncertainty increased trust in AI for 48% (n=70). [claim:clm_068]
- Size-based uncertainty encoding had a significantly greater impact on trust than transparency (p < 0.05). [claim:clm_069]
- Color saturation was rated highest for intuition and preference, ahead of transparency and size. [claim:clm_070]
- Displaying AI uncertainty raised decision confidence for 44% of participants but lowered it for 56%. [claim:clm_071]
- One-third of participants (33%, n=48) changed their responses after seeing the AI prediction's uncertainty. [claim:clm_072]
- The authors decline to endorse any single uncertainty visualization technique or to push users toward trusting AI, cautioning against over-trust. [claim:clm_073]
- The study is a survey-based between-subjects experiment with 300 participants (150 per task) classifying familiar and unfamiliar stimuli with a simulated AI of varying accuracy across geometric-shape and animal-identification tasks. [claim:clm_074]
- Once trust was eroded, Model Update restored trust above its initial level, followed by Apology, Promise, and the no-repair baseline, with Denial being least effective. [claim:clm_075]
- Most participants used the AI's accuracy on familiar (high-human-expertise) stimuli as a heuristic to calibrate their trust in its output for unfamiliar (low-human-expertise) stimuli they could not independently verify. [claim:clm_076]
- When indicators of an AI's performance are not provided, individuals tend to over-rely on the AI regardless of its actual accuracy, even when explanations are provided. [claim:clm_077]
- Early system errors disproportionately shape trust for the whole interaction, causing negative trust outcomes even if accuracy later improves, so first impressions are weighted more heavily. [claim:clm_078]
- The authors adopt Lee and See's definition of trust as an attitude that an agent will achieve a goal under uncertainty and vulnerability. [claim:clm_079]
- Denial was the least effective repair strategy across both tasks, backfiring and prompting users to distrust the AI despite improved accuracy, with trust similar to the lowest-accuracy phase. [claim:clm_080]
- Model Update outperformed Promise despite identical AI accuracy, restoring trust above its Phase 1 starting level, while Promise was merely as effective as the no-repair baseline. [claim:clm_081]

## Decision

KnitWit's confidence meter should adopt a coarse ordinal scale (e.g., a 3-level high/medium/low or question-mark-style marker) rather than a continuous percentage or probability distribution, because ordinal uncertainty representations both calibrate usage behavior better and are more cognitively accessible to non-expert makers. [claim:clm_inf01]

## Rationale

- Zhao et al. (TVCG 2023) found ordinal forms (Question-mark) calibrate model-usage behavior and are more accessible than continuous distributions (clm_006), while Fernandes et al. (CHI 2018) show even rich encodings work best when reframed as countable discrete outcomes rather than areas (clm_011, clm_012); together they argue against a bare continuous percentage on a space-constrained mobile crocheter UI. [claim:clm_inf01]
- Fernandes et al. found quantile dotplots (50 outcomes) yielded the best decisions at 97% of optimal (clm_009, clm_010), CDFs nearly as good and both beating textual uncertainty (clm_011), with the count-not-area reframing explicitly suited to space-constrained mobile displays (clm_012); decision quality also improved with practice (clm_013), matching a repeated-use crochet app. [claim:clm_inf02]
- Li et al. show disclosing the calibration level raised detection (to 73.8-76.2%) but yielded no decision-efficacy gain because it traded over- for under-reliance (clm_026, clm_058, clm_059), and the authors explicitly recommend telling users WHY and under what conditions confidence may be unreliable rather than surfacing a bare number (clm_060). [claim:clm_inf03]
- Pareek et al. show early errors dominate whole-interaction trust (clm_078), Model Update repair restored trust above its initial level while Denial was least effective and backfired (clm_075, clm_080, clm_081); applied to KnitWit this argues for sequencing reliable shapes first and using technical-fix framing for repair. [claim:clm_inf05]
- CrochetBench's Turning and Multiplier failure categories (clm_039, clm_040) and its use of the CrochetPARADE DSL for structural+functional validation (clm_037), plus the executable-correctness collapse (clm_036), identify concrete validation rules that map to the IR v0.1 repeat op and round boundaries — the G2 Crochet-IR viability experiments. [claim:clm_inf08]
- AmiGo builds an explicit inspectable Crochet Graph IR (clm_050, clm_051) and realizes curvature via increases/decreases derived from graph geometry (clm_052) parameterized by stitch width (clm_049); these internal facts are exactly the substrate for a 'this increase is here because the surface curves outward' explanation. [claim:clm_inf10]
- Park et al. show explanations foster confirmation bias when outputs look acceptable (clm_062), users equate trust with outcome agreement and rely on flawed reasoning (clm_064), and confident delivery tone suppresses error detection (clm_065), concluding systems should encourage scrutiny (clm_066) — so KnitWit's rationale overlay must be deliberately scrutiny-inviting. [claim:clm_inf11]
- Ma et al. treat trust and reliance as separable (clm_044), split inappropriate reliance into over- and under-reliance (clm_045), and find self-reported trust does not reliably track reliance behavior (clm_047); with miscalibrated trust causing both failure modes (clm_003), reliance behavior is the better acceptance signal. [claim:clm_inf12]
- Combines Fernandes et al.'s percent-of-optimal decision metric (clm_010), Li et al.'s reliance/switch metrics (clm_021), Ma et al.'s over/under-reliance targets (clm_045), Pareek et al.'s trust-repair recovery (clm_075) and the Lee and See trust definition (clm_079) into one acceptance instrument set. [claim:clm_inf13]
- Li et al.'s two-direction miscalibration results (clm_021-024, clm_054-056) establish that both overconfidence and underconfidence are costly and that well-calibration is the optimal operating point, directly implying KnitWit must tune preview/pattern confidence framing to its true approximation accuracy rather than to user-pleasing optimism. [claim:clm_inf04]
- Pareek et al. found users use AI accuracy on familiar high-expertise stimuli to calibrate trust on unverifiable unfamiliar stimuli (clm_076) and over-rely absent performance indicators (clm_077); since preview reliance also depends on task difficulty (clm_001), KnitWit's hard-shape trust is anchored by its easy-shape accuracy. [claim:clm_inf06]
- StitchFlow notes the two flat formats with non-transferring fluency (clm_033) and that interpreting notation forces error-prone mental work (clm_032); CrochetBench shows valid human patterns get penalized by under-specification (clm_041) and executable correctness collapses without explicit structure (clm_036); the IR v0.1 expected_stitch_count field is the explicit-count mitigation. [claim:clm_inf07]
- CrochetPARADE visualizes attachment (clm_015) and per-stitch info (clm_018) but documents no why-the-count-changed or inc/dec-distribution-rationale feature (clm_019); AmiGo derives inc/dec procedurally from graph geometry (clm_052), meaning the rationale exists internally and is exposable — defining the unfilled wedge. [claim:clm_inf09]
- CrochetPARADE animates reveal/hide (clm_014), highlights/isolates rows and stitches (clm_016), and flags over/under-stretched stitches beyond ~15% (clm_017); these map one-to-one onto KnitWit's required playback, ghost-row, checkpoint, isolation, and tension-confidence surfaces. [claim:clm_inf14]
- AmiGo's research-demo capability (clm_048, clm_049, clm_053) sits on the 'shown in a paper' side; CrochetBench's executable-correctness collapse for automated generation (clm_036) plus the absence of any cited mobile-runtime or user-crochetability evidence put mesh-to-pattern below the product-readiness line, making G4 the least-evidenced gate. [claim:clm_inf15]
- Reyes et al. found uncertainty display raised trust for ~48-58% (clm_067) yet lowered decision confidence for 56% (clm_071); reconciling with Zhao et al.'s ordinal-is-better (clm_006) and Fernandes et al.'s discrete-frequency-wins (clm_010) resolves the contradiction toward encoding choice, a medium-impact design decision. [claim:clm_inf16]
- No source card addresses handedness or left-mirroring; the closest signals (CrochetPARADE's documented feature set in clm_019 and crochet's hand-movement-dependent nature in clm_034) confirm the topic is unaddressed, so the honest analytic conclusion is an explicit evidence gap rather than a fabricated requirement. [claim:clm_inf17]

## Consequences

- For per-round approximate-3D fit confidence, a frequency-framed quantile dotplot (e.g., '47 of 50 simulated tensions fit this round') is the strongest mobile-suitable encoding, because dotplots reached ~97% of optimal decision payoff (5 points above control) and CDFs nearly matched them, both beating textual probability. [claim:clm_inf02]
- A bare confidence number on an approximate preview is insufficient and potentially harmful for KnitWit; the meter must pair every confidence signal with a 'why this is approximate / under what conditions it may be wrong' explanation, because disclosing only a calibration number improved detection but did not improve decision efficacy and could erode trust. [claim:clm_inf03]
- The single highest-leverage trust risk for KnitWit is the first visible approximate-preview error: because early system errors disproportionately shape whole-interaction trust and denial backfires, the app should front-load its lowest-uncertainty shapes (spheres/heads) in onboarding and, after any visible mismatch, repair via a concrete 'model update / recalculated' fix rather than apology or denial. [claim:clm_inf05]
- CrochetBench's DSL error taxonomy maps directly onto the validators KnitWit must ship: 'Turning Issues' (turns only valid at row end) and 'Multiplier Issues' (repeat multipliers not bound to a stitch) correspond to required structural checks on the IR's repeat op and round/row boundaries, making these the first two stitch-count/structure validators to build (de-risking gate G2). [claim:clm_inf08]
- KnitWit can ground its 'where/why are increases distributed' explanation in AmiGo's Crochet Graph: because shaping (inc/dec) is derived procedurally from graph geometry/curvature and each stitch is an inspectable graph element, the app can attribute each increase to the local curvature that required it, turning an internal geometric fact into a per-round natural-language rationale. [claim:clm_inf10]
- Surfacing procedural reasoning (a CoT-style 'why the count changed' overlay) is double-edged for KnitWit: it can satisfy the explainability requirement but also induce confirmation bias and over-reliance, so the explanation UI must invite scrutiny (e.g., show the stitch-count check, flag where the model is least sure) rather than narrate with a confident authoritative tone that suppresses error detection. [claim:clm_inf11]
- Reliance and trust must be measured as separate KnitWit UX acceptance signals, and reliance behavior (acted-on previews) is the more dependable acceptance metric than self-reported trust, with over-reliance (following a wrong preview) and under-reliance (rejecting a correct one) as the two concrete failure metrics to instrument. [claim:clm_inf12]
- A defensible KnitWit UX acceptance protocol can be assembled from the cited studies: task-completion / decision-payoff (% of optimal, per Fernandes et al.), over-reliance and under-reliance rates and switch-to-recommendation rate (per Li et al. / Ma et al.), a trust-repair recovery check after an induced visible error (per Pareek et al.), and Lee-and-See-framed trust attitude scales as a secondary self-report. [claim:clm_inf13]
- KnitWit's previews must be deliberately calibrated and never made to look more authoritative than the evidence supports, because overconfident outputs drove over-reliance to ~41% (vs ~28% well-calibrated) and underconfident outputs drove under-reliance to ~18% (vs ~11%), with both miscalibration directions roughly halving the accuracy benefit (to ~6.5-7.2% vs ~11.9%). [claim:clm_inf04]
- Because makers cannot independently verify an approximate 3D preview of a shape they have not yet crocheted, they will transfer trust from cases they CAN verify (simple verified spheres/heads) to ones they cannot, so KnitWit's perceived accuracy on its easiest previews becomes the de facto trust anchor for its hardest ones. [claim:clm_inf06]
- Crochet's two incumbent flat representations (written notation and symbol charts) plus documented under-specification of human patterns are the root cause of the 'ambiguous/under-specified pattern text' failure-mode cluster, and a machine-checkable Crochet IR with explicit per-round expected_stitch_count is the direct mitigation because it forces the implicit conventions to be made explicit. [claim:clm_inf07]
- The explainability whitespace for KnitWit is precisely defined: existing best-in-class tooling (CrochetPARADE) shows how stitches attach, where tension fails, and per-stitch metadata, but no tool explains WHY a stitch/decrease count changed or analyzes inc/dec distribution rationale, so the 'why did the stitch count change' and 'where/why are increases distributed' features are a genuine, defensible product wedge rather than a re-implementation. [claim:clm_inf09]
- CrochetPARADE's existing primitives are directly adoptable as KnitWit forward-preview surfaces: stitch-by-stitch reveal/hide ('a'/ctrl+a) for row-by-row playback and ghost-next-row overlay, row/stitch highlight (ctrl+f) and hide-after (ctrl+h) for checkpoints and piece isolation, and the 's' over/under-stretched flag (>~15%) as a ready-made tension/gauge confidence signal surfaced before crocheting. [claim:clm_inf14]
- The mesh-to-pattern generator should be classified as academically feasible but not product-ready: AmiGo demonstrates closed-mesh + seed-point + stitch-width generation with join-as-you-go in a research paper, but no cited evidence establishes mobile runtime cost, watertight-mesh robustness for casual user inputs, or maker-perceived crochetability, leaving gate G4 (mesh-to-pattern primitive) the most under-evidenced gate. [claim:clm_inf15]
- An apparent tension exists between 'show uncertainty to build trust' and 'showing uncertainty lowered decision confidence for the majority': the likely resolution is that uncertainty display reliably aids trust and decision quality when encoded as ordinal/discrete frequency forms but can depress raw confidence when shown as ambiguous continuous signals, so the decision impact is medium and argues for KnitWit using discrete/ordinal encodings. [claim:clm_inf16]
- Left-handed mirroring is an evidence-gap in this corpus: none of the gathered sources document handedness/left-mirroring handling in crochet tooling or HCI, so KnitWit's mirrored-experience correctness requirements cannot yet be grounded in cited evidence and remain an open question requiring dedicated source discovery before any G5 MVP commitment. [claim:clm_inf17]

## Links

- [[claim:clm_001]]
- [[claim:clm_006]]
- [[claim:clm_011]]
- [[claim:clm_012]]
- [[claim:clm_009]]
- [[claim:clm_010]]
- [[claim:clm_013]]
- [[claim:clm_026]]
- [[claim:clm_058]]
- [[claim:clm_059]]
- [[claim:clm_060]]
- [[claim:clm_078]]
- [[claim:clm_075]]
- [[claim:clm_080]]
- [[claim:clm_081]]
- [[claim:clm_039]]
- [[claim:clm_040]]
- [[claim:clm_037]]
- [[claim:clm_036]]
- [[claim:clm_050]]
- [[claim:clm_051]]
- [[claim:clm_052]]
- [[claim:clm_049]]
- [[claim:clm_062]]
- [[claim:clm_064]]
- [[claim:clm_065]]
- [[claim:clm_066]]
- [[claim:clm_044]]
- [[claim:clm_045]]
- [[claim:clm_047]]
- [[claim:clm_003]]
- [[claim:clm_021]]
- [[claim:clm_079]]
- [[claim:clm_022]]
- [[claim:clm_023]]
- [[claim:clm_024]]
- [[claim:clm_054]]
- [[claim:clm_055]]
- [[claim:clm_056]]
- [[claim:clm_076]]
- [[claim:clm_077]]
- [[claim:clm_033]]
- [[claim:clm_032]]
- [[claim:clm_041]]
- [[claim:clm_015]]
- [[claim:clm_018]]
- [[claim:clm_019]]
- [[claim:clm_014]]
- [[claim:clm_016]]
- [[claim:clm_017]]
- [[claim:clm_048]]
- [[claim:clm_053]]
- [[claim:clm_067]]
- [[claim:clm_071]]
- [[claim:clm_034]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
