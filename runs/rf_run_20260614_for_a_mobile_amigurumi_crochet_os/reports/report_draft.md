---
schema_version: '0.1'
type: research_report
report_id: report_20260614_for_a_mobile_amigurumi_crochet_os
title: 'Trust-First UX for an Amigurumi Crochet OS: A Failure-Mode Catalog, Explainability
  Primitives, and Confidence/Calibration Design Rules Grounded in Craft-Tech and HCI
  Evidence'
intent_id: intent_research_20260614_for_a_mobile_amigurumi_crochet_os
evidence_bundle_id: pending
created_at: '2026-06-14T23:47:30-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Trust-First UX for an Amigurumi Crochet OS

A literature review for KnitWit, an amigurumi-first mobile crochet OS with two flagship surfaces: a **forward preview** (structured pattern -> approximate interactive 3D) and an **inverse generator** (simple watertight mesh -> human-crochetable pattern). The review catalogs crocheter UX failure modes, derives confidence/calibration design rules from HCI uncertainty-visualization and trust-calibration evidence, specifies explainability primitives, sketches a gauge-calibration onboarding spec, and recommends literature-sourced usability/trust acceptance metrics.

## Executive summary

The evidence base for KnitWit splits cleanly into a craft-tech cluster (StitchFlow, CrochetPARADE, CrochetBench, AmiGo) and an HCI trust/uncertainty cluster (uncertainty-visualization, miscalibration, trust-repair, and explanation studies); the explainability features KnitWit most wants are a documented whitespace rather than a re-implementation. [claim:clm_inf09]
The explainability whitespace is precise: best-in-class tooling visualizes how stitches attach and exposes per-stitch metadata, but no tool explains WHY a stitch or decrease count changed or analyzes increase/decrease distribution rationale across rounds. [claim:clm_019]
A machine-checkable Crochet IR with explicit per-round expected_stitch_count is the direct mitigation for the ambiguous/under-specified-pattern-text failure cluster because it forces implicit conventions to be made explicit. [claim:clm_inf07]
On the trust side, miscalibrated confidence is costly in both directions: overconfident output drove over-reliance to ~41.3% versus ~28.2% for well-calibrated output, and underconfident output drove under-reliance to ~17.7% versus ~11.2%. [claim:clm_inf04]
For the confidence meter, ordinal and discrete-frequency encodings beat continuous percentages on both cognitive accessibility and decision quality, so KnitWit should adopt a coarse ordinal scale rather than a bare probability. [claim:clm_inf01]
A bare confidence number is insufficient and potentially harmful; every confidence signal must be paired with a "why this is approximate / under what conditions it may be wrong" explanation. [claim:clm_inf03]
The mesh-to-pattern generator (inverse surface) is academically feasible but not product-ready, leaving gate G4 the most under-evidenced gate in the program. [claim:clm_inf15]
Left-handed mirroring is an outright evidence gap in this corpus and must be resolved by dedicated source discovery before any G5 MVP commitment. [claim:clm_inf17]

## Scope and the two threatened surfaces

KnitWit's forward-preview surface converts a structured pattern into an approximate interactive 3D view, and CrochetPARADE's existing primitives are directly adoptable for this surface (stitch-by-stitch reveal/hide, row/stitch highlight, hide-after isolation, and an over/under-stretched tension flag). [claim:clm_inf14]
KnitWit's inverse-generation surface converts a simple watertight mesh into a human-crochetable pattern, and AmiGo demonstrates exactly this transform from a closed triangle mesh plus a single seed point. [claim:clm_048]
Crochet has uniquely resisted mechanization because no machines can fully replicate the hand movements required to manipulate stitches, keeping it an inherently human, improvisational skill that any preview or generator must respect rather than replace. [claim:clm_034]
Crochet patterns are conventionally shared in two flat representations -- written notation and symbol-based charts -- and proficiency in one format does not necessarily transfer to fluency in the other. [claim:clm_033]

## Failure-mode catalog

The catalog below enumerates crocheter UX failure modes across the four required clusters -- ambiguous pattern text, tension/gauge variability, joins/color-changes/piece-alignment, and left-handed mirroring -- each tagged to the KnitWit surface it threatens (Forward = pattern->3D preview; Inverse = mesh->pattern generation; Both) and cited to craft-tech/HCI/usability evidence.

### Cluster A — Ambiguous / under-specified pattern text

| ID | Failure mode | Surface threatened | Evidence |
|----|--------------|--------------------|----------|
| FM-A1 | Pattern documentation forces makers to pause, count stitches, take notes, and mentally interpret notations, breaking immersive flow. | Forward | [claim:clm_032] |
| FM-A2 | Two incumbent flat formats (written + symbol chart) with non-transferring fluency mean a maker fluent in one can misread the other. | Forward | [claim:clm_033] |
| FM-A3 | Documenting patterns, tracking progress, and backtracking from mistakes or mid-process changes are the specific tasks that disrupt creative flow. | Forward | [claim:clm_028] |
| FM-A4 | Valid human-written patterns can be penalized because the DSL or rendering cannot capture implicit conventions experienced crafters apply. | Both | [claim:clm_041] |
| FM-A5 | Turning Issues: turning/orientation commands are misplaced, since turning is only valid at the end of a row. | Both | [claim:clm_039] |
| FM-A6 | Multiplier Issues: repeat/scaling multipliers are improperly formatted and not bound to a stitch. | Both | [claim:clm_040] |
| FM-A7 | Model performance drops sharply from surface-level similarity to executable correctness, exposing gaps in long-range symbolic reasoning. | Inverse | [claim:clm_036] |

The root cause of this cluster is the two flat representations plus documented under-specification, and the IR v0.1 expected_stitch_count field is the explicit-count mitigation. [claim:clm_inf07]

### Cluster B — Tension / gauge variability

| ID | Failure mode | Surface threatened | Evidence |
|----|--------------|--------------------|----------|
| FM-B1 | Stitches drift over/under-stretched (blue = too loose, red = too tight by more than ~15%), the existing tension/gauge confidence signal. | Forward | [claim:clm_017] |
| FM-B2 | A maker's true stitch width diverges from the width parameter the generator assumed, distorting fit. | Inverse | [claim:clm_049] |
| FM-B3 | Reliance on a preview is not driven by uncertainty alone; it depends jointly on task difficulty and machine uncertainty, so gauge-hard rounds erode trust faster. | Forward | [claim:clm_001] |

The 's' over/under-stretched flag is a ready-made tension/gauge confidence signal surfaced before crocheting and is directly adoptable as a KnitWit forward-preview surface. [claim:clm_inf14]

### Cluster C — Joins / color-changes / piece-alignment / assembly

| ID | Failure mode | Surface threatened | Evidence |
|----|--------------|--------------------|----------|
| FM-C1 | Existing renderers show how stitches attach (blue working-order arrows, red remaining relationships) but not why counts change, so alignment errors are hard to diagnose. | Forward | [claim:clm_015] |
| FM-C2 | Shapes are segmented into separate crochetable components joined by join-as-you-go, so any mis-segmentation surfaces as an assembly defect. | Inverse | [claim:clm_053] |
| FM-C3 | Shaping (inc/dec) is procedural and curvature-derived, so a wrong curvature read distributes increases incorrectly and warps the join geometry. | Inverse | [claim:clm_052] |
| FM-C4 | Pattern sharing must round-trip through written patterns and crochet charts; a lossy export breaks downstream piece alignment for collaborators. | Forward | [claim:clm_030] |

### Cluster D — Left-handed mirroring

| ID | Failure mode | Surface threatened | Evidence |
|----|--------------|--------------------|----------|
| FM-D1 | None of the gathered sources document handedness/left-mirroring handling in crochet tooling or HCI, so mirrored-experience correctness is ungrounded. | Both | [claim:clm_inf17] |

**Inference:** Left-handed mirroring is an evidence gap in this corpus and remains an open question requiring dedicated source discovery before any G5 MVP commitment. [claim:clm_inf17]

### Cluster E — Trust/reliance failure modes (cross-surface)

| ID | Failure mode | Surface threatened | Evidence |
|----|--------------|--------------------|----------|
| FM-E1 | Failure to calibrate trust causes over-reliance or under-reliance, both diminishing the benefits of the human-automation system. | Both | [claim:clm_003] |
| FM-E2 | Absent appropriate interventions, people are heavily biased to adopt imperfect human judgments over imperfect models. | Both | [claim:clm_004] |
| FM-E3 | Overconfident output increased over-reliance to ~41.3% versus ~28.2% for well-calibrated output, a statistically significant increase. | Both | [claim:clm_054] |
| FM-E4 | Underconfident output increased under-reliance to ~17.7% versus ~11.2% for well-calibrated output, a statistically significant increase. | Both | [claim:clm_055] |
| FM-E5 | Users could not detect miscalibration on their own: 66.7% misjudged an underconfident AI well-calibrated and 64.3% did so for an overconfident AI. | Both | [claim:clm_025] |
| FM-E6 | Early system errors disproportionately shape whole-interaction trust, so a first visible mismatch poisons later accurate previews. | Forward | [claim:clm_078] |
| FM-E7 | Explanations promoted for transparency can instead foster confirmation bias when the output looks acceptable. | Forward | [claim:clm_062] |
| FM-E8 | A confident delivery tone suppresses users' detection of errors while preserving reliance. | Forward | [claim:clm_065] |
| FM-E9 | Without performance indicators, individuals over-rely on the AI regardless of its actual accuracy, even with explanations. | Both | [claim:clm_077] |
| FM-E10 | Users equate trust with agreeing on the outcome, continuing to rely even when the underlying reasoning is flawed. | Forward | [claim:clm_064] |

## Confidence-meter design rules (uncertainty visualization and trust calibration)

### Evidence on encoding choice

A simple ordinal uncertainty representation (Question-mark) is generally sufficient and more cognitively accessible to general audiences than continuous probability distributions, even though richer detail (Violin Plot) is perceived as more trustworthy. [claim:clm_006]
Frequency-based quantile dotplots, previously shown to aid probability extraction, yielded better decisions than the alternatives. [claim:clm_009]
Quantile dotplots with 50 outcomes produced decisions averaging 97% of optimal expected payoff, 5 percentage points above the control. [claim:clm_010]
CDF plots performed nearly as well as quantile dotplots, and both beat textual uncertainty, whose effectiveness depended on the probability interval communicated. [claim:clm_011]
Quantile dotplots reframe a probability density as countable discrete outcomes, letting non-experts reason about probabilities as counts rather than areas, well suited to space-constrained mobile displays. [claim:clm_012]
Decision quality with dotplots and CDFs was high from the start and improved with practice, reaching about 95% of optimal by the final trial while becoming more consistent. [claim:clm_013]
Size-based uncertainty encoding had a significantly greater impact on trust than transparency (p < 0.05). [claim:clm_069]
Color saturation was rated highest for intuition and preference, ahead of transparency and size. [claim:clm_070]

### Evidence on what miscalibration does to behavior

The miscalibration study operationalized three confidence conditions against a fixed 70% AI accuracy: underconfident (60% stated confidence), well-calibrated (70%), and overconfident (80%). [claim:clm_020]
Overconfident AI raised the user switch-to-AI rate to ~69.6% versus ~57% for well-calibrated AI, while underconfident AI lowered it to ~40.5%. [claim:clm_021]
Overconfident AI increased over-reliance to ~41.3% versus ~28.2% for well-calibrated AI. [claim:clm_022]
Underconfident AI increased under-reliance to ~17.7% versus ~11.2% for well-calibrated AI. [claim:clm_023]
Decision-accuracy improvement fell to ~6.5% (underconfident) and ~7.2% (overconfident) versus ~11.9% for well-calibrated confidence. [claim:clm_024]
AI confidence directly moved switching behavior: switch-to-AI rate fell to ~40.5% under underconfidence versus ~57.0% well-calibrated and rose to ~69.6% under overconfidence. [claim:clm_057]
Miscalibration shrank accuracy gains: underconfident AI yielded +6.5% and overconfident +7.2% versus +11.9% for well-calibrated AI, both significant reductions. [claim:clm_056]

### Evidence on disclosure and its limits

Explicitly communicating the calibration level improved detection (76.2% correctly identified underconfidence) but decreased trust in uncalibrated AI and did not improve overall decision efficacy. [claim:clm_026]
Disclosing calibration level sharply improved detection: 73.8% correctly flagged the AI as overconfident, up from 26.2% without disclosure. [claim:clm_058]
Despite better detection, disclosure yielded no decision-efficacy gain because it increased under-reliance on overconfident AI. [claim:clm_059]
The authors recommend telling users WHY and under what conditions confidence may be unreliable, not just surfacing a bare confidence number. [claim:clm_060]
The authors of the uncertainty-visualization survey decline to endorse any single uncertainty visualization technique or to push users toward trusting AI, cautioning against over-trust. [claim:clm_073]

### Confidence-meter encoding comparison

| Encoding | Effect on appropriate trust | Mobile suitability | Verdict for KnitWit | Evidence |
|----------|-----------------------------|--------------------|---------------------|----------|
| Ordinal marker (Question-mark / high-med-low) | Sufficient and more cognitively accessible than continuous distributions. | High | Adopt as the base meter. | [claim:clm_006] |
| Frequency quantile dotplot (50 outcomes) | Best decisions at 97% of optimal, 5 pts above control. | High (count-not-area) | Adopt for per-round fit confidence. | [claim:clm_010] |
| CDF plot | Nearly as good as dotplots; both beat textual. | Medium | Acceptable fallback. | [claim:clm_011] |
| Continuous probability distribution (Violin) | Perceived as more trustworthy but less accessible to general audiences. | Low | Avoid as the primary signal. | [claim:clm_006] |
| Bare confidence number / textual probability | Effectiveness depends on the interval communicated; beaten by dotplots/CDFs. | Low | Do not ship alone. | [claim:clm_011] |
| Size-based encoding | Significantly greater trust impact than transparency (p < 0.05). | Medium | Use as a secondary salience cue. | [claim:clm_069] |
| Color-saturation encoding | Highest-rated for intuition and preference. | High | Use for at-a-glance preference. | [claim:clm_070] |

### Derived design rules

KnitWit's confidence meter should adopt a coarse ordinal scale (e.g., a 3-level high/medium/low or question-mark-style marker) rather than a continuous percentage or probability distribution. [claim:clm_inf01]
For per-round approximate-3D fit confidence, a frequency-framed quantile dotplot (e.g., '47 of 50 simulated tensions fit this round') is the strongest mobile-suitable encoding. [claim:clm_inf02]
A bare confidence number on an approximate preview is insufficient and potentially harmful; the meter must pair every confidence signal with a 'why this is approximate / under what conditions it may be wrong' explanation. [claim:clm_inf03]
KnitWit's previews must be deliberately calibrated and never made to look more authoritative than the evidence supports, because both miscalibration directions roughly halve the accuracy benefit. [claim:clm_inf04]

## Explainability primitives

### The whitespace and its substrate

The manual documents no feature that explains why a stitch or decrease count changed, nor any post-hoc analysis of increase/decrease distribution rationale across rounds. [claim:clm_019]
Hovering a stitch reveals its row and stitch number plus the stitch type in brackets, and shift+left-click pins a persistent info box -- an inline per-stitch rationale affordance that already exists to build on. [claim:clm_018]
AmiGo builds a Crochet Graph (geometry plus connectivity) as an explicit intermediate representation that is then translated into the written round-by-round pattern. [claim:clm_050]
The Crochet Graph encodes stitches as graph elements: vertices are stitch tops/bases, column edges are stitch stems, and row edges connect bases within a row, making the IR inspectable. [claim:clm_051]
Shaping is procedural: curvature is realized by increase and decrease stitches derived from the graph geometry rather than specified arbitrarily. [claim:clm_052]
**Inference:** The explainability whitespace for KnitWit is precisely defined and is a genuine, defensible product wedge rather than a re-implementation. [claim:clm_inf09]
KnitWit can ground its 'where/why are increases distributed' explanation in AmiGo's Crochet Graph by attributing each increase to the local curvature that required it, turning an internal geometric fact into a per-round natural-language rationale. [claim:clm_inf10]

### The double-edged risk of surfaced reasoning

The Chain-of-Thought study probes the double-edged role of explanations in multimodal scenarios by perturbing reasoning chains and manipulating delivery tones in vision language models. [claim:clm_063]
Explanations promoted for transparency can instead foster confirmation bias, with users assuming the reasoning is correct whenever the output looks acceptable. [claim:clm_062]
Users tend to equate trust with agreeing on the outcome, so they keep relying on the system even when the underlying reasoning is flawed. [claim:clm_064]
A confident delivery tone suppresses users' detection of errors while preserving reliance, showing presentation style can override correctness. [claim:clm_065]
CoT explanations can simultaneously clarify and mislead, so systems should present explanations that encourage scrutiny and critical thinking rather than blind trust. [claim:clm_066]
Surfacing procedural reasoning (a CoT-style 'why the count changed' overlay) is double-edged for KnitWit, so the explanation UI must invite scrutiny rather than narrate with a confident authoritative tone that suppresses error detection. [claim:clm_inf11]

### Explainability primitive specification (IR-aligned)

| Primitive | Requirement | IR substrate | Scrutiny safeguard | Evidence |
|-----------|-----------------------|-------------------|--------------------|----------|
| Count-delta explainer | 'why did the stitch count change' | rounds[].expected_stitch_count diff vs prior round | Show the count check, not a narrative claim. | [claim:clm_019] |
| Increase-attribution overlay | 'where/why are increases distributed' | ops inc/dec mapped to visual_hint.shape_role increase/decrease | Attribute each inc to local curvature, not authority. | [claim:clm_inf10] |
| Per-stitch rationale pin | inline per-stitch reasoning | rounds[].ops[] op + count metadata | Reuse hover/pin affordance; expose stitch type. | [claim:clm_018] |
| Procedural-reasoning panel | expose reasoning to non-expert makers | Crochet Graph -> rounds[].ops mapping | Flag where the model is least sure. | [claim:clm_inf11] |

## Gauge / yarn-diameter calibration onboarding spec

This section sketches a gauge/yarn-diameter calibration onboarding spec, grounded in swatch/calibration evidence, including handedness requirements.

Beyond the mesh and seed point, the generator takes a target stitch width w as an input parameter that parameterizes the generated instructions, so onboarding must capture an accurate w. [claim:clm_049]
For per-round fit confidence, a frequency-framed quantile dotplot is the strongest mobile-suitable encoding to surface the calibrated gauge result. [claim:clm_inf02]
StitchFlow uses a motion sensor to track real-time hand gestures and reconstruct the stitch pattern, letting crocheters work in situ without distraction or needing to remember previous steps -- a precedent for low-friction capture. [claim:clm_029]
A user study with 8 crocheters found StitchFlow preserved makers' creative flow, enabled spontaneous exploration, and facilitated pattern sharing. [claim:clm_031]
The 's' key flags over/under-stretched stitches (blue = too loose, red = too tight by more than ~15%), an existing tension/gauge confidence signal that a swatch step can drive. [claim:clm_017]

**Speculation:** Because StitchFlow's in-situ stitch tracking preserved creative flow for makers (n=8) and CrochetPARADE already flags over-stretched stitches, KnitWit could plausibly convert a phone-camera or sensor swatch-measurement step into a low-friction gauge-calibration onboarding that feeds stitch-width into AmiGo-style generation, but completion-rate and downstream-fit evidence does not yet exist and must be measured. [claim:clm_spec01]

### Onboarding field spec

| Onboarding step | Captured value | IR field | Note | Evidence |
|-----------------|----------------|---------------|------|----------|
| Yarn measure | yarn diameter | materials.yarns[].diameter_mm | Feeds target stitch width w. | [claim:clm_049] |
| Hook entry | hook diameter | materials.hooks[].diameter_mm | Pairs with yarn for tension. | [claim:clm_049] |
| Swatch | stitches/rows per 10cm | gauge.stitches_per_10cm / rows_per_10cm | Validated by the ~15% stretch flag. | [claim:clm_017] |
| Handedness | left vs right mirroring | (unspecified — evidence gap) | Requires dedicated discovery. | [claim:clm_inf17] |

Left-handed mirroring is an evidence gap in this corpus, so the handedness onboarding field cannot yet be grounded in cited evidence and is flagged as an open question. [claim:clm_inf17]

## Usability / trust acceptance metrics and instruments

This section recommends a concrete, literature-sourced set of usability/trust metrics and measurement instruments usable as KnitWit UX acceptance signals.

The paper treats trust and reliance as separable constructs: trust is a subjective self-reported attitude toward the AI, while reliance is the objective behavior of acting on its recommendation. [claim:clm_044]
Inappropriate reliance is split into over-reliance (agreeing with AI when it is wrong) and under-reliance (rejecting AI when it is right), giving measurable behavioral targets. [claim:clm_045]
Self-reported trust does not reliably track reliance behavior, so the authors study reliance behavior as the more dependable indicator of appropriateness. [claim:clm_047]
The authors adopt Lee and See's definition of trust as an attitude that an agent will achieve a goal under uncertainty and vulnerability. [claim:clm_079]
Reliance and trust must be measured as separate KnitWit UX acceptance signals, and reliance behavior is the more dependable acceptance metric than self-reported trust. [claim:clm_inf12]
A defensible KnitWit UX acceptance protocol can be assembled from the cited studies: percent-of-optimal decision payoff, over/under-reliance and switch-to-recommendation rates, a trust-repair recovery check after an induced visible error, and Lee-and-See-framed trust attitude scales as secondary self-report. [claim:clm_inf13]

### Acceptance-metric instrument set

| Metric | Instrument / protocol | Source study | KnitWit signal | Evidence |
|--------|-----------------------|--------------|-----------------------|----------|
| Decision payoff (% of optimal) | Incentivized task with optimal-payoff baseline | Fernandes et al. (transit dotplots) | Preview-decision quality. | [claim:clm_010] |
| Over-reliance rate | Agreed-with-AI-when-wrong count | Ma et al. (self-confidence calibration) | Following a wrong preview. | [claim:clm_045] |
| Under-reliance rate | Rejected-AI-when-right count | Ma et al. | Rejecting a correct preview. | [claim:clm_045] |
| Switch-to-recommendation rate | Switch tracking across confidence conditions | Li et al. (miscalibration) | Sensitivity to meter framing. | [claim:clm_021] |
| Trust-repair recovery | Induced visible error + repair-strategy phases | Pareek et al. (trust repair) | Recovery after a visible mismatch. | [claim:clm_075] |
| Trust attitude (secondary) | Lee-and-See-framed self-report scale | Pareek et al. / definition | Secondary self-report only. | [claim:clm_079] |

## Analytical derivation: from evidence to KnitWit design rules

This section derives the design rules from the assembled evidence and makes product and technical implications explicit.

The miscalibration evidence establishes that well-calibration is the optimal operating point because both overconfidence and underconfidence are costly, directly implying KnitWit must tune preview confidence framing to its true approximation accuracy rather than to user-pleasing optimism. [claim:clm_inf04]
The single highest-leverage trust risk for KnitWit is the first visible approximate-preview error, so the app should front-load its lowest-uncertainty shapes (spheres/heads) in onboarding and repair any visible mismatch via a concrete 'model update / recalculated' fix rather than apology or denial. [claim:clm_inf05]
**Inference:** Because makers cannot independently verify an approximate 3D preview of a shape they have not yet crocheted, KnitWit's perceived accuracy on its easiest previews becomes the de facto trust anchor for its hardest ones. [claim:clm_inf06]
Most participants used the AI's accuracy on familiar (high-human-expertise) stimuli as a heuristic to calibrate their trust in its output for unfamiliar (low-human-expertise) stimuli they could not independently verify. [claim:clm_076]
Once trust was eroded, Model Update restored trust above its initial level, followed by Apology, Promise, and the no-repair baseline, with Denial being least effective. [claim:clm_075]
Model Update outperformed Promise despite identical AI accuracy, restoring trust above its Phase 1 starting level, while Promise was merely as effective as the no-repair baseline. [claim:clm_081]
Denial was the least effective repair strategy across both tasks, backfiring and prompting users to distrust the AI despite improved accuracy, with trust similar to the lowest-accuracy phase. [claim:clm_080]
CrochetBench's DSL error taxonomy maps directly onto the validators KnitWit must ship, making Turning and Multiplier checks the first two stitch-count/structure validators to build (de-risking gate G2). [claim:clm_inf08]
CrochetPARADE animates pattern creation by revealing stitches one-by-one ('a') and hiding them one-by-one (ctrl+a), a direct precedent for row-by-row playback and ghost-next-row overlay. [claim:clm_014]
The tool can highlight a specific row or individual stitch (ctrl+f), highlight stitches by label (ctrl+d), and hide everything after a chosen row/stitch (ctrl+h) -- primitives for checkpoint surfacing and piece isolation. [claim:clm_016]

### Product and technical implications

**Inference:** The product implication of the explainability whitespace is a defensible feature wedge, while the technical implication is that the rationale already exists internally in a Crochet Graph and only needs to be exposed as a per-round natural-language attribution. [claim:clm_inf10]
**Inference:** The product implication of the miscalibration evidence is that KnitWit must resist user-pleasing optimism in its meter, while the technical implication is that the confidence value must be derived from the model's true per-round approximation accuracy. [claim:clm_inf04]
**Inference:** The product implication of the first-error finding is an onboarding that leads with reliable shapes, while the technical implication is a 'recalculate' repair path wired to fire on any detected mismatch. [claim:clm_inf05]
**Inference:** The product implication of CrochetBench's taxonomy is that two concrete validators ship first, while the technical implication is that they map to the IR's repeat op and round/row boundaries. [claim:clm_inf08]

## Academic feasibility vs product readiness

AmiGo generates human-crochetable amigurumi instructions from only a closed triangle mesh plus a single user-specified seed point, establishing academic feasibility of the inverse transform. [claim:clm_048]
The shape is automatically segmented into separate crochetable components that are joined by the join-as-you-go method, requiring no additional sewing. [claim:clm_053]
CrochetBench evaluates whether multimodal models can shift from describing visual content to generating executable crochet procedures via fine-grained procedural reasoning. [claim:clm_035]
Model performance drops sharply when evaluation moves from surface-level similarity to executable correctness, exposing gaps in long-range symbolic reasoning and 3D-aware procedural synthesis. [claim:clm_036]
StitchFlow is a peer-reviewed full paper published Open Access (CC BY 4.0) in the Proceedings of the 38th Annual ACM Symposium on User Interface Software and Technology (UIST '25). [claim:clm_027]
A user study with 8 crocheters found StitchFlow preserved makers' creative flow, enabled spontaneous exploration, and facilitated pattern sharing. [claim:clm_031]
The mesh-to-pattern generator should be classified as academically feasible but not product-ready, leaving gate G4 (mesh-to-pattern primitive) the most under-evidenced gate. [claim:clm_inf15]

### Feasibility-vs-readiness matrix

| Capability | Academic feasibility | Product readiness | Unproven for product | Evidence |
|------------|----------------------|-------------------|----------------------|----------|
| Mesh -> crochetable pattern (inverse) | Demonstrated (closed mesh + seed point). | Not established. | Mobile runtime cost, mesh robustness, maker-perceived crochetability. | [claim:clm_inf15] |
| Procedural inc/dec shaping | Derived from graph geometry. | Partially — needs validation. | Crochetability of generated inc/dec under casual inputs. | [claim:clm_052] |
| Executable correctness of generated procedures | Benchmarked; drops sharply. | Not ready. | Long-range symbolic reasoning gaps. | [claim:clm_036] |
| In-situ flow-preserving capture | Shown with n=8 study. | Promising; small-N. | Generalization beyond 8 makers. | [claim:clm_031] |
| Forward preview primitives | Exist in CrochetPARADE. | Adoptable directly. | Integration into mobile surface. | [claim:clm_inf14] |

## Contradictions & open disagreements

Visualizing AI uncertainty significantly enhanced trust for 58% of participants who held negative attitudes toward AI. [claim:clm_067]
Across the full sample of 147 participants, displaying uncertainty increased trust in AI for 48% (n=70). [claim:clm_068]
Displaying AI uncertainty raised decision confidence for 44% of participants but lowered it for 56%. [claim:clm_071]
One-third of participants (33%, n=48) changed their responses after seeing the AI prediction's uncertainty. [claim:clm_072]
**Inference:** An apparent tension exists between 'show uncertainty to build trust' and 'showing uncertainty lowered decision confidence for the majority'; the likely resolution is that uncertainty display reliably aids trust and decision quality when encoded as ordinal/discrete frequency forms but can depress raw confidence when shown as ambiguous continuous signals, so the decision impact is medium and argues for KnitWit using discrete/ordinal encodings. [claim:clm_inf16]
In study 3, self-confidence calibration produced more rational reliance and reduced under-reliance and improved task performance, but did not reduce over-reliance. [claim:clm_046]
Calibrating human self-confidence improved human-AI team performance and led to more rational reliance on AI versus an uncalibrated baseline. [claim:clm_043]

### Contradiction matrix

| Topic | Side A | Side B | Resolution | Decision impact | Evidence |
|-------|--------|--------|-------------------|-----------------|----------|
| Uncertainty display vs decision confidence | Uncertainty raised trust for ~48-58%. | Uncertainty lowered decision confidence for 56%. | Encoding-dependent; ordinal/discrete wins. | Medium | [claim:clm_inf16] |
| Disclosure of calibration | Disclosure improved detection to 73.8%. | Disclosure yielded no efficacy gain. | Pair disclosure with the WHY, not a bare number. | Medium | [claim:clm_059] |
| Self-confidence calibration scope | Calibration reduced under-reliance. | Calibration did not reduce over-reliance. | Calibration is partial; needs encoding + repair. | Medium | [claim:clm_046] |

## Risks

| Risk | Category | Severity | Likelihood | Mitigation | Evidence |
|------|----------|----------|------------|------------|----------|
| First visible preview error poisons whole-interaction trust | UX trust | High | Medium | Front-load reliable spheres/heads; repair via recalculate. | [claim:clm_inf05] |
| Miscalibrated meter induces over/under-reliance | UX trust | High | Medium | Calibrate to true approximation accuracy. | [claim:clm_inf04] |
| Authoritative-tone rationale suppresses error detection | UX trust | Medium | High | Scrutiny-inviting overlay; flag low-confidence rounds. | [claim:clm_inf11] |
| Mesh->pattern not product-ready | Model accuracy / generation | High | High | Treat G4 as least-evidenced; gate behind prototypes. | [claim:clm_inf15] |
| Under-specified pattern text breaks generation/preview | Generation crochetability | Medium | High | Adopt IR expected_stitch_count + Turning/Multiplier checks. | [claim:clm_inf08] |
| Left-mirroring correctness ungrounded | UX / correctness | Medium | High | Dedicated source discovery before G5. | [claim:clm_inf17] |

**Speculation:** Forward-looking risk (severity high, likelihood medium): the 'it lied to me' trust-collapse from a visible approximate-preview error may be more damaging for an emotionally invested hobby craft than the lab studies suggest, because makers commit hours of physical yarn before discovering a mismatch; mitigation is to label previews 'approximate' up front, lead with verified shapes, and offer an instant recalculated fix. Labeled speculation. [claim:clm_spec02]

## Prototype experiments & decision-gate relevance

CrochetBench's DSL error taxonomy maps directly onto the first two stitch-count/structure validators to build, de-risking gate G2. [claim:clm_inf08]
The benchmark adopts the CrochetPARADE DSL as an intermediate representation, enabling structural validation and functional evaluation by executing the generated procedures. [claim:clm_037]
One execution failure category is Turning Issues, where models misplace turning/orientation commands, since turning is only valid at the end of a row. [claim:clm_039]
A second failure category is Multiplier Issues, where repeat/scaling multipliers are improperly formatted and not bound to a stitch. [claim:clm_040]
CrochetPARADE's existing primitives are directly adoptable as KnitWit forward-preview surfaces for playback, ghost-row, checkpoints, isolation, and tension confidence. [claim:clm_inf14]
The mesh-to-pattern generator leaves gate G4 the most under-evidenced gate, requiring primitive-mesh->rounds and mesh-pattern->IR experiments before any product-roadmap commitment. [claim:clm_inf15]

### Findings-to-gate map

| Gate | Gates | Informing finding | Next experiment | Evidence |
|------|---------------|-------------------------|-----------------------------|----------|
| G1 Evidence quality | Synthesis | The acceptance-instrument corpus is assembled from cited studies. | None — evidence corpus stands. | [claim:clm_inf13] |
| G2 Crochet-IR viability | Visualizer prototyping | Turning/Multiplier checks map to IR repeat op + boundaries. | EXP-002 stitch-count validator; EXP-003 repeat expansion. | [claim:clm_inf08] |
| G3 Pattern->3D viability | Inverse generator | CrochetPARADE primitives adoptable for preview surfaces. | EXP-004 IR->stitch-graph; EXP-005 stitch-graph->approx-3D; EXP-006 row-highlight export. | [claim:clm_inf14] |
| G4 Mesh->pattern primitive | Product roadmap | Mesh->pattern academically feasible, not product-ready. | EXP-008 primitive-mesh->rounds; EXP-009 mesh-pattern->IR; EXP-010 round-trip evaluator. | [claim:clm_inf15] |
| G5 MVP recommendation | Final decision | Left-mirroring evidence gap blocks MVP commitment. | Dedicated handedness source discovery. | [claim:clm_inf17] |

**Speculation:** KnitWit's approximate-3D preview should be positioned as a 'forecast under known uncertainty' rather than a 'photo of the finished object', and the most de-risking next experiment is EXP-005/EXP-010 (stitch-graph to approximate 3D and the mesh to pattern to visualizer round-trip) instrumented with a discrete-frequency fit-confidence display and an over/under-reliance measure, because this jointly tests gates G3 and the trust-encoding hypotheses on the same artifact. [claim:clm_spec03]

## Recommendations / decision rules

**Inference:** KnitWit's confidence meter should adopt a coarse ordinal scale rather than a continuous percentage or probability distribution. [claim:clm_inf01]
**Inference:** For per-round approximate-3D fit confidence, KnitWit should use a frequency-framed quantile dotplot as the strongest mobile-suitable encoding. [claim:clm_inf02]
**Inference:** KnitWit must pair every confidence signal with a 'why this is approximate / under what conditions it may be wrong' explanation rather than a bare number. [claim:clm_inf03]
KnitWit's previews must be deliberately calibrated and never made to look more authoritative than the evidence supports. [claim:clm_inf04]
KnitWit should front-load its lowest-uncertainty shapes in onboarding and repair any visible mismatch via a concrete 'model update / recalculated' fix rather than apology or denial. [claim:clm_inf05]
**Inference:** KnitWit should adopt a machine-checkable Crochet IR with explicit per-round expected_stitch_count to make implicit conventions explicit. [claim:clm_inf07]
KnitWit should build the Turning and Multiplier structural validators first to de-risk gate G2. [claim:clm_inf08]
KnitWit should ground its 'where/why are increases distributed' explanation in AmiGo's Crochet Graph by attributing each increase to local curvature. [claim:clm_inf10]
**Inference:** KnitWit's rationale overlay must be deliberately scrutiny-inviting rather than authoritative in tone. [claim:clm_inf11]
**Inference:** KnitWit should measure reliance and trust separately, treating reliance behavior as the primary acceptance signal. [claim:clm_inf12]
**Inference:** KnitWit should adopt the assembled acceptance protocol of decision payoff, over/under-reliance, switch rate, trust-repair recovery, and a secondary trust scale. [claim:clm_inf13]
**Inference:** KnitWit should adopt CrochetPARADE's playback, highlight, isolation, and tension primitives directly for its forward-preview surface. [claim:clm_inf14]
**Inference:** KnitWit should treat the mesh-to-pattern generator as academically feasible but not product-ready and gate it behind G4 prototypes. [claim:clm_inf15]

## Open questions

- How should KnitWit handle left-handed mirroring given that no cited source documents handedness handling in crochet tooling or HCI?
- What is the calibration-onboarding completion rate and downstream fit accuracy of a phone-camera or sensor swatch step?
- What is the mobile runtime cost and watertight-mesh robustness of AmiGo-style generation on casual user inputs?
- Does the ordinal-vs-continuous encoding advantage hold for crochet fit confidence specifically rather than the studied forecasting and transit tasks?
- Will a 'recalculate' repair strategy restore trust as effectively in a high-sunk-cost physical craft as Model Update did in the lab tasks?

## Sources

- src_20260614_kw010_04: Evaluating the Impact of Uncertainty Visualization on Model Reliance
- src_20260614_kw010_06: Uncertainty Displays Using Quantile Dotplots or CDFs Improve Transit Decision-Making
- src_20260614_kw010_09: CrochetPARADE Manual (Pattern Renderer, Analyzer, and Debugger)
- src_20260614_kw010_03: Understanding the Effects of Miscalibrated AI Confidence on User Trust, Reliance, and Decision Efficacy
- src_20260614_kw010_01: StitchFlow: Enabling In-Situ Creative Explorations of Crochet Patterns With Stitch Tracking and Process Sharing
- src_20260614_kw010_00: CrochetBench: Can Vision-Language Models Move from Describing to Doing in Crochet Domain?
- src_20260614_kw010_07: "Are You Really Sure?" Understanding the Effects of Human Self-Confidence Calibration in AI-Assisted Decision Making
- src_20260614_kw010_08: AmiGo: Computational Design of Amigurumi Crochet Patterns
- src_20260614_kw010_10: Understanding the Effects of Miscalibrated AI Confidence on User Trust, Reliance, and Decision Efficacy
- src_20260614_kw010_11: Critical or Compliant? The Double-Edged Sword of Reasoning in Chain-of-Thought Explanations
- src_20260614_kw010_02: Trusting AI: does uncertainty visualization affect decision-making?
- src_20260614_kw010_05: Trust Development and Repair in AI-Assisted Decision-Making during Complementary Expertise
