---
id: mwb_20260622_dr_logprob_vs_self_reported_confidence
evidence_bundle_id: bundle_20260614_intent_research_20260614_do_token_logprob
target_page: meatywiki/decisions/logprob_vs_self_reported_confidence_for.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_do_token_logprob_distributions_provide_more: clm_024
  gives CoCoA the lowest ECE; clm_026 gives it leading AUROC; clm_025 shows MSP ranks well but calibrates
  worse; c'
key_claims:
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf10
  include: true
- claim_id: clm_inf13
  include: true
- claim_id: clm_inf14
  include: true
- claim_id: clm_inf15
  include: true
- claim_id: clm_inf16
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf11
  include: true
- claim_id: clm_inf12
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_020
  - clm_024
  - clm_025
  - clm_026
  - clm_063
  - clm_073
  - clm_011
  - clm_007
  - clm_008
  - clm_009
  - clm_010
  - clm_021
  - clm_022
  - clm_033
  - clm_034
  - clm_037
  - clm_023
  - clm_069
  - clm_070
  - clm_071
  - clm_072
  - clm_004
  - clm_066
  - clm_067
  - clm_002
  - clm_001
  - clm_029
  - clm_013
  - clm_014
  - clm_052
  - clm_058
  - clm_059
  - clm_045
  - clm_047
  - clm_039
  - clm_055
  - clm_044
  - clm_050
  - clm_019
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: Logprob vs self-reported confidence for LLM classification

## Context

- For LLMs with at least 70 billion parameters, verbalized-confidence expected calibration error (ECE) is around 0.1, i.e. confidence deviates roughly 10% from true accuracy. [claim:clm_001]
- The best 'combo' prompt method extracts verbalized confidence scores with an average deviation of about 7% from empirical accuracy for large LLMs. [claim:clm_002]
- The smallest evaluated model (gemma1.1-2b) produces verbalized confidence scores that are poorly calibrated and almost independent of its actual accuracy. [claim:clm_003]
- Calibration of verbalized confidence is not intrinsic to the model but depends heavily on how the confidence is elicited via prompt formulation. [claim:clm_004]
- The study benchmarks verbalized confidence reliability across 10 datasets, 11 LLMs, and 17 prompt methods. [claim:clm_005]
- Verbalized confidence is positioned as a prompt- and model-agnostic, low-overhead uncertainty quantification method whose reliability strongly depends on prompting, but which can yield well-calibrated scores with certain prompt methods. [claim:clm_006]
- A selective classifier is formally a pair (f, g) combining a predictor f with a selection function g that decides whether to predict or abstain. [claim:clm_007]
- Coverage is the probability mass of the region of inputs the classifier does not reject (the fraction of inputs accepted). [claim:clm_008]
- Selective risk is the expected loss over accepted (non-rejected) instances, normalized by coverage. [claim:clm_009]
- The SGR algorithm constructs a selection function so the selective risk exceeds the user-specified target r* with probability at most delta (i.e. the desired risk is guaranteed with high probability). [claim:clm_010]
- The full performance profile of a selective classifier is captured by the risk-coverage curve, which plots risk as a function of coverage. [claim:clm_011]
- Empirically, the method guarantees ~2% top-5 ImageNet error with probability 99.9% at almost 60% test coverage, demonstrating the coverage-versus-risk trade-off in practice. [claim:clm_012]
- The logprobs API parameter is a boolean that, when true, returns the log probabilities of each output token in the message content. [claim:clm_013]
- top_logprobs is an integer between 0 and 5 specifying how many most-likely tokens to return at each position, each with an associated log probability, and it requires logprobs to be set to true. [claim:clm_014]
- The notebook focuses on five logprobs use cases: classification tasks, retrieval (Q&A) evaluation, autocomplete, token highlighting and outputting bytes, and calculating perplexity. [claim:clm_015]
- Each token entry includes a bytes field giving the ASCII encoding of each output character, which is useful for reproducing emojis and special characters. [claim:clm_016]
- For classification, logprobs supply a probability per class prediction, letting users set their own classification or confidence thresholds. [claim:clm_017]
- Perplexity is computed by exponentiating the negative of the average of the logprobs. [claim:clm_018]
- The study evaluates four QA uncertainty-estimation methods (VCE, MSP, Sample Consistency, CoCoA) on BoolQ, SQuAD 2.0, TriviaQA, and GSM8K using a LLaMA 3 / 3.2 3B-Instruct model. [claim:clm_019]
- The paper's headline finding is that the hybrid CoCoA approach (confidence plus consistency) yields the best overall reliability, improving both calibration and discrimination. [claim:clm_020]
- Single-sample verbalized confidence (VCE) is severely overconfident, reporting ~97.6% mean confidence on SQuAD and 98.8% on GSM8K despite far lower accuracy, producing large ECE. [claim:clm_021]
- Token-probability MSP is far better calibrated than single-shot VCE: GSM8K ECE 0.104 (MSP) vs 0.335 (VCE single-sample), and TriviaQA ECE 0.147 (MSP) vs 0.309 (VCE single-sample). [claim:clm_022]
- Multi-sample TOP-K aggregation sharply reduces VCE overconfidence: GSM8K VCE ECE falls from 0.335 (single-sample) to 0.129 (TOP-K). [claim:clm_023]
- Hybrid CoCoA is the best-calibrated method overall, achieving ECE 0.062 on SQuAD 2.0 and 0.081 on GSM8K with competitive AUROC. [claim:clm_024]
- MSP gives strong ranking (highest AUROC on TriviaQA 0.841 and GSM8K 0.838) but weaker calibration than CoCoA, making it a dependable ranker rather than a well-calibrated confidence source. [claim:clm_025]
- CoCoA leads discrimination/AUROC across benchmarks: SQuAD 0.844, TriviaQA 0.841 (tie with MSP), GSM8K 0.786, and BoolQ 0.687 (best ranking on BoolQ). [claim:clm_026]
- The study performs an extensive experimental evaluation of post-hoc confidence estimators across 84 pretrained ImageNet classifiers, all computed directly from logits without retraining the underlying model. [claim:clm_027]
- A simple p-norm normalization of the logits followed by taking the maximum logit as the confidence estimator yields considerable selective-classification gains, fixing pathological 'broken' confidence behavior in many classifiers. [claim:clm_028]
- After applying the logit-based fix, a classifier's selective-classification performance becomes almost entirely determined by its accuracy, decoupling it from the original broken confidence estimator. [claim:clm_029]
- The logit-based selective-classification gains are shown to hold under distribution shift, indicating robustness to data drift. [claim:clm_030]
- The paper uses the Area Under the Risk-Coverage curve (AURC) as the standard selective-classification metric. [claim:clm_031]
- The authors introduce a Normalized AURC (NAURC) that maps ideal performance to 0 and random performance to 1, enabling fair comparison of selective-classification quality across classifiers with different accuracies. [claim:clm_032]
- Ollama's OpenAI-compatible /v1/chat/completions documentation explicitly marks Logprobs as unsupported via an unchecked checkbox. [claim:clm_033]
- The documented supported features for /v1/chat/completions include chat completions, streaming, JSON mode, reproducible outputs, vision, tools, and reasoning/thinking control, with only Logprobs left unchecked. [claim:clm_034]
- The documented supported request fields for /v1/chat/completions are model, messages, frequency_penalty, presence_penalty, response_format, seed, stop, stream, stream_options, temperature, top_p, max_tokens, tools, reasoning_effort, and reasoning. [claim:clm_035]
- The reasoning controls reasoning_effort and reasoning are documented as supported request fields, accepting effort values of high, medium, low, and none. [claim:clm_036]
- No top_logprobs request field is documented, and the unsupported request fields explicitly listed are tool_choice, logit_bias, user, and n. [claim:clm_037]
- The OpenAI-compatible API documents endpoints including /v1/chat/completions, /v1/completions, /v1/models, /v1/embeddings, /v1/images/generations, and /v1/responses. [claim:clm_038]
- Setting n_probs greater than 0 makes the /completion endpoint also return the probabilities of the top N tokens for each generated token under the active sampling settings. [claim:clm_039]
- When temperature < 0 the tokens are sampled greedily but token probabilities are still computed via a simple softmax of the logits, ignoring other sampler settings. [claim:clm_040]
- The completion_probabilities response array has length n_predict; each item carries a nested top_logprobs array containing at most n_probs elements, each with id, logprob, token, and bytes fields. [claim:clm_041]
- When post_sampling_probs is set to true, the logprob field is replaced with prob (a value between 0.0 and 1.0) and top_logprobs is replaced with top_probs. [claim:clm_042]
- The number of elements returned in top_probs may be fewer than n_probs. [claim:clm_043]
- The OpenAI-compatible /v1/chat/completions section defers to the OpenAI Chat Completions API docs and only notes that /completion-specific features such as mirostat are supported; n_probs, completion_probabilities, top_logprobs, and post_sampling_probs are documented solely under the /completion endpoint, not for /v1/chat/completions. [claim:clm_044]
- vLLM's v1 engine implements logprobs handling through a LogprobsProcessor dataclass that carries both per-output sample logprobs and prompt logprobs for a request. [claim:clm_045]
- The LogprobsProcessor holds separate optional fields for sample logprobs and prompt logprobs (SampleLogprobs and PromptLogprobs), confirming vLLM tracks both the chosen-token output logprobs and input-prompt logprobs as distinct structures. [claim:clm_046]
- Whether sample logprobs and prompt logprobs are produced is driven by the request's sampling parameters: num_logprobs comes from sampling_params.num_logprobs and num_prompt_logprobs from sampling_params.prompt_logprobs, and each logprobs structure is only created when its count is not None. [claim:clm_047]
- For each generated position, vLLM's sampler places the actually-sampled token's logprob first in the logprobs list, and the processor accumulates it into the running cumulative_logprob. [claim:clm_048]
- Prompt logprobs are aggregated across one or more prefill chunks and returned all at once at the end of prefill; pop_prompt_logprobs returns None if prompt logprobs are disabled for the request, otherwise the full list. [claim:clm_049]
- The token IDs returned at a given logprobs position are alternatives at the same position (sampled token plus top-k alternatives such as [sampled, top1, top2]), not sequential tokens, clarifying that vLLM returns the chosen token alongside its top-ranked alternatives per position. [claim:clm_050]
- vLLM applies UTF-8 correction when detokenizing logprob tokens: byte-fallback tokenization can split multi-byte UTF-8 characters across tokens, producing the U+FFFD replacement character, and the processor uses preceding sampled tokens as context to reconstruct correct text. [claim:clm_051]
- In the Responses API, logprobs are requested by adding the value 'message.output_text.logprobs' to the include array on the create-response request. [claim:clm_052]
- Each returned logprobs object contains a token (string), bytes (array of number), logprob (number), and a top_logprobs array. [claim:clm_053]
- Each nested entry in the top_logprobs array carries its own token, bytes, and logprob fields. [claim:clm_054]
- Logprobs are attached to the assistant message's output_text content (the ResponseOutputText object) rather than to a top-level choices.logprobs field as in Chat Completions. [claim:clm_055]
- A logprob is the natural logarithm of the probability the model assigned to a token, with values closer to 0 indicating higher model confidence. [claim:clm_056]
- A logprob score closer to zero signals higher model confidence in its chosen token. [claim:clm_057]
- Setting response_logprobs=True instructs the Gemini model to return the log probabilities of the tokens it selected for its output. [claim:clm_058]
- The logprobs parameter requests log probabilities for a specified number of top alternative tokens at each step, accepting an integer value between 1 and 20. [claim:clm_059]
- The tutorial demonstrates logprobs using the gemini-2.5-flash model. [claim:clm_060]
- A small gap between the top two log probabilities is a signal of classification ambiguity that can be used to flag low-confidence outputs. [claim:clm_061]
- Averaging the log probabilities of a generated answer yields a grounding or confidence score for retrieval-augmented generation systems. [claim:clm_062]
- ECE is computed by partitioning predictions into M equally-spaced confidence bins and taking the sample-weighted average of the absolute gap between accuracy and average confidence in each bin. [claim:clm_063]
- The paper's standard ECE estimator uses M = 15 bins for its reported vision and NLP results. [claim:clm_064]
- Reliability diagrams plot expected sample accuracy as a function of confidence; a perfectly calibrated model plots the identity diagonal and any deviation from it represents miscalibration. [claim:clm_065]
- Temperature scaling is a single-parameter post-hoc method that divides the logits by one scalar T>0 before the softmax, with T optimized against NLL on the validation set. [claim:clm_066]
- Because T does not change the argmax of the softmax, the class prediction is unchanged and temperature scaling therefore leaves classification accuracy unaffected while reducing miscalibration. [claim:clm_067]
- Modern neural networks are poorly calibrated (systematically overconfident), and depth, width, weight decay, and Batch Normalization are identified as important factors influencing calibration. [claim:clm_068]
- Models exhibit a critical dissociation: their verbal confidence is neither cost-aware nor strategically responsive when deciding to engage or abstain under high-penalty conditions, so calibrated confidence scores alone are insufficient for trustworthy AI. [claim:clm_069]
- Across models and datasets, increasing the error penalty has a negligible effect on model behavior; neither self-evaluated confidence nor the answer/abstain decision changes significantly as incorrect-answer penalties range over [0.1, 100]. [claim:clm_070]
- Under extreme penalties where frequent abstention is the mathematically optimal strategy, models almost never abstain, causing utility collapse. [claim:clm_071]
- Confidence and action are decoupled: models often 'know' their own uncertainty via calibrated verbal estimates yet fail to convert that knowledge into a good abstention policy. [claim:clm_072]
- Verbal-confidence calibration is poor and varies widely by dataset and model: on Humanity's Last Exam (HLE), reported ECE spans 0.474-0.841, Brier 0.332-0.791, and AUARC 0.041-0.533, with substantially better calibration on easier GSM8K (ECE 0.019-0.149). [claim:clm_073]

## Decision

The headline recommendation is a hybrid: combining logprob/consistency with confidence (CoCoA) is the best-calibrated method overall (ECE 0.062 SQuAD, 0.081 GSM8K) while also leading discrimination (AUROC up to 0.844), beating either MSP or VCE alone on calibration. [claim:clm_inf03]

## Rationale

- clm_024 gives CoCoA the lowest ECE; clm_026 gives it leading AUROC; clm_025 shows MSP ranks well but calibrates worse; clm_020 states the hybrid yields best overall reliability. Together they support a hybrid recommendation over single signals. [claim:clm_inf03]
- clm_025 shows MSP strong on AUROC but weaker on ECE, proving the metrics are non-redundant; clm_063 defines ECE, clm_073 pairs ECE/Brier/AUARC, clm_011 frames risk-coverage. Therefore both calibration (ECE/Brier) and ranking (AUROC/RC) metrics are needed. [claim:clm_inf04]
- clm_007-clm_011 define selective classification, coverage, selective risk, the SGR risk guarantee, and the risk-coverage curve; applying that machinery to an LLM confidence signal yields a principled threshold rule. [claim:clm_inf05]
- Combines the overconfidence of single-sample VCE (clm_021), MSP's cheap strong ranking (clm_022/clm_025), and CoCoA's best calibration (clm_024) into a tiered default-plus-escalation routing policy. [claim:clm_inf07]
- clm_033/clm_034/clm_037 establish the documented-unsupported status; the source card's conflicts_with field flags the v0.12.11 release-note conflict, so capability is version-dependent and should be probed at runtime. [claim:clm_inf10]
- Weighs the 2-3x calibration gain of single-call MSP (clm_022 vs clm_021) against the ~M-fold cost of multi-sample hybrids (clm_023/clm_024) to bound where the gain is worth the spend. [claim:clm_inf13]
- clm_069-clm_072 document the confidence-action dissociation; the implication for a classify-then-route pipeline is that routing logic, not the model's self-decision, must own the abstain threshold. [claim:clm_inf14]
- clm_010 supplies the SGR threshold construction, clm_004 the prompt/model dependence requiring re-fitting, clm_063 the ECE recompute, clm_024 the hybrid re-check band. Composes them into an operational policy. [claim:clm_inf15]
- clm_066/clm_067 give temperature scaling as an accuracy-preserving recalibration for logprob-derived softmax confidence; clm_002/clm_004 give prompt choice as the analogous lever for verbalized confidence. Applying 2017 temperature scaling to LLM logprobs is an inference across modalities. [claim:clm_inf16]
- clm_022 reports MSP ECE 0.104/0.147 against clm_021's VCE single-sample 0.335/0.309 on the same model and benchmarks; the ratio is a direct comparison of the two signals. [claim:clm_inf01]
- clm_001/clm_002 put large-LLM verbalized ECE near 0.1 / 7% deviation; clm_022 puts MSP ECE at 0.104 on GSM8K. The two signals land in the same calibration band for large models, so logprobs' edge collapses at scale. [claim:clm_inf02]
- clm_029 (ImageNet) shows selective performance becomes accuracy-determined once the estimator is fixed; clm_025/clm_026 show MSP/CoCoA rank well via AUROC. Transferring the logit-fix finding to LLM logprobs is an inference (different modality), hence medium confidence. [claim:clm_inf06]
- Each cell maps to a per-provider supported claim: OpenAI Chat (clm_013/clm_014), Responses (clm_052), Gemini (clm_058/clm_059), vLLM (clm_045/clm_047), llama.cpp (clm_039), Ollama-unsupported (clm_033/clm_037). [claim:clm_inf08]
- clm_055 documents the Chat-vs-Responses shape divergence; clm_044 the llama.cpp endpoint split; clm_033/clm_037 the Ollama omission. Together they imply an adapter plus a fallback are required for portability. [claim:clm_inf09]
- clm_013/clm_014/clm_039/clm_059 show logprobs are returned for already-generated output tokens with a bounded top-k; clm_050 confirms per-position alternatives. No source prices tokens, so the $-overhead conclusion is labeled inference. [claim:clm_inf11]
- clm_023 (TOP-K) and clm_024 (CoCoA) are multi-sample methods; the source card notes CoCoA uses M=10 separate decodes (clm_019 context). The ~M-fold cost multiplier is an arithmetic inference from the sampling count, not a sourced price. [claim:clm_inf12]

## Consequences

- Metric selection should be split by purpose: ECE and Brier capture the accept/route calibration question (does a 0.8 confidence mean 80% correct), while AUROC / area-under-risk-coverage capture the abstain ranking question (does higher confidence rank correct answers above incorrect), and MSP's high AUROC but weaker ECE shows a signal can win one without the other. [claim:clm_inf04]
- An abstention/escalation threshold should be set on the risk-coverage curve via the SGR guarantee rather than a fixed confidence cutoff: pick the target selective risk r* and the coverage it permits at confidence 1-delta, which converts any chosen signal (MSP, CoCoA, or self-report) into a tunable accept-rate-at-fixed-error operating point. [claim:clm_inf05]
- Concrete recommendation for a classify-then-route vault: use single-call logprob sequence probability (MSP) as the default accept/route signal because it needs no extra decode passes and ranks well (AUROC ~0.84), escalate to a logprob+self-report or logprob+consistency hybrid (CoCoA-style) only for the abstain/borderline band, and avoid relying on single-sample self-reported JSON confidence alone given its severe overconfidence (ECE 0.31-0.34). [claim:clm_inf07]
- The Ollama logprobs capability is version-contested and must be treated as a runtime feature-probe, not a static assumption: the OpenAI-compatibility docs mark Logprobs unsupported while v0.12.11 release notes claim support, so a portable design should detect logprob availability at connect time and degrade to self-report when absent. [claim:clm_inf10]
- At stated vault scale (thousands of artifacts, repeated reclassification), the calibration gain justifies single-call logprobs over a self-report-only baseline because the overhead is sub-linear (metadata on existing tokens) while the ECE/ranking gain is 2-3x on small models, but it does NOT justify always-on multi-sample hybrids; reserve the ~M-fold-cost hybrid for the low-confidence escalation band only. [claim:clm_inf13]
- Calibrated confidence is necessary but not sufficient for an automated routing policy: LLMs that produce well-calibrated verbal confidence still fail to act on it (risk-invariant abstention, utility collapse under high penalties), so the abstain/escalate decision must be enforced by an external thresholding/router on the confidence signal rather than delegated to the model's own answer/abstain choice. [claim:clm_inf14]
- A reusable classify-abstain-threshold-policy follows: (1) emit the chosen confidence signal per artifact, (2) fix target selective risk r* and confidence 1-delta via the SGR construction, (3) accept above the resulting threshold, route the borderline band to a logprob+self-report hybrid re-check, and (4) hold out a labeled calibration set to recompute ECE/Brier and re-fit the threshold whenever the model or prompt changes, since calibration is prompt- and model-dependent. [claim:clm_inf15]
- A confidence-calibration-recipe should pair the raw signal with a one-parameter post-hoc rescaling (temperature scaling), since dividing logits by a single scalar T reduces miscalibration without changing the predicted label; for self-report fields, the analogous fix is choosing a calibration-optimal prompt ('combo'), because verbalized calibration is elicitation-dependent rather than intrinsic. [claim:clm_inf16]
- On a single fixed model (LLaMA 3.2 3B-Instruct), token-logprob sequence probability (MSP) is far better calibrated than single-sample self-reported confidence (VCE), cutting ECE roughly 2-3x (GSM8K 0.104 vs 0.335; TriviaQA 0.147 vs 0.309), so at small model scale logprobs are the more calibrated signal. [claim:clm_inf01]
- The logprob calibration advantage is conditional on model scale and prompting, not absolute: large (>=70B) LLMs reach verbalized-confidence ECE ~0.1 (best 'combo' prompt ~7% deviation), which is comparable to MSP's GSM8K ECE of 0.104, so for large models a well-prompted self-report is roughly on par with single-call logprobs on calibration. [claim:clm_inf02]
- The selective-classification literature predicts the accept-rate-at-fixed-error tradeoff is governed primarily by signal monotonicity and base accuracy, not the confidence scalar's nominal value: once a signal ranks errors correctly (as MSP/CoCoA do via AUROC ~0.78-0.84), selective performance is near-fully determined by accuracy, so the practical coverage gain from logprobs comes from better ranking, not better numeric calibration. [claim:clm_inf06]
- A multi-provider portability table shows usable token logprobs are exposed by OpenAI Chat Completions (logprobs + top_logprobs 0-5), OpenAI Responses API (include message.output_text.logprobs), Google Gemini on Vertex AI (response_logprobs plus logprobs 1-20), self-hosted vLLM (sampling_params.num_logprobs and prompt_logprobs), and llama.cpp's native /completion (n_probs), while Ollama's OpenAI-compatible /v1/chat/completions documents Logprobs as unsupported. [claim:clm_inf08]
- Portability cost is concentrated in two seams: endpoint-shape divergence (logprobs live under choices.logprobs in Chat Completions but under output_text in the Responses API, and only under llama.cpp's /completion, not its /v1/chat/completions) and feature absence (Ollama's OpenAI-compatible chat endpoint omits logprobs entirely), so a logprob-dependent classifier needs a per-provider adapter layer and a self-report fallback path for providers like Ollama. [claim:clm_inf09]
- Per-call overhead of single-call logprobs is near-zero in billed output tokens because top_logprobs/n_probs/response_logprobs return per-token metadata on tokens the model already emits, not extra generated text; the real overhead is response-payload size (top-k alternatives per position) and a modest serialization/parse cost, making single-call logprobs cheaper than any sampling-based self-report aggregation. (cost assumption labeled inference) [claim:clm_inf11]
- The dominant cost driver at vault scale is multi-sample aggregation, not logprobs: CoCoA and multi-sample TOP-K require ~M (e.g. 10) independent decode passes per artifact, multiplying token, latency, and dollar cost ~M-fold, whereas single-call MSP logprobs add roughly one pass; for thousands of artifacts with repeated reclassification this makes a single-call logprob default the only economically defensible always-on signal. (cost-multiplier assumption labeled inference) [claim:clm_inf12]

## Links

- [[claim:clm_020]]
- [[claim:clm_024]]
- [[claim:clm_025]]
- [[claim:clm_026]]
- [[claim:clm_063]]
- [[claim:clm_073]]
- [[claim:clm_011]]
- [[claim:clm_007]]
- [[claim:clm_008]]
- [[claim:clm_009]]
- [[claim:clm_010]]
- [[claim:clm_021]]
- [[claim:clm_022]]
- [[claim:clm_033]]
- [[claim:clm_034]]
- [[claim:clm_037]]
- [[claim:clm_023]]
- [[claim:clm_069]]
- [[claim:clm_070]]
- [[claim:clm_071]]
- [[claim:clm_072]]
- [[claim:clm_004]]
- [[claim:clm_066]]
- [[claim:clm_067]]
- [[claim:clm_002]]
- [[claim:clm_001]]
- [[claim:clm_029]]
- [[claim:clm_013]]
- [[claim:clm_014]]
- [[claim:clm_052]]
- [[claim:clm_058]]
- [[claim:clm_059]]
- [[claim:clm_045]]
- [[claim:clm_047]]
- [[claim:clm_039]]
- [[claim:clm_055]]
- [[claim:clm_044]]
- [[claim:clm_050]]
- [[claim:clm_019]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
