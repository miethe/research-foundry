---
id: mwb_20260614_logprob_vs_self_reported_confidence_for
evidence_bundle_id: bundle_20260614_intent_research_20260614_do_token_logprob
target_page: meatywiki/sources/logprob_vs_self_reported_confidence_for.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_do_token_logprob_distributions_provide_more:
  73 supported claim(s) across 12 source card(s).'
key_claims:
- claim_id: clm_001
  include: true
- claim_id: clm_002
  include: true
- claim_id: clm_003
  include: true
- claim_id: clm_004
  include: true
- claim_id: clm_005
  include: true
- claim_id: clm_006
  include: true
- claim_id: clm_007
  include: true
- claim_id: clm_008
  include: true
- claim_id: clm_009
  include: true
- claim_id: clm_010
  include: true
- claim_id: clm_011
  include: true
- claim_id: clm_012
  include: true
- claim_id: clm_013
  include: true
- claim_id: clm_014
  include: true
- claim_id: clm_015
  include: true
- claim_id: clm_016
  include: true
- claim_id: clm_017
  include: true
- claim_id: clm_018
  include: true
- claim_id: clm_019
  include: true
- claim_id: clm_020
  include: true
- claim_id: clm_021
  include: true
- claim_id: clm_022
  include: true
- claim_id: clm_023
  include: true
- claim_id: clm_024
  include: true
- claim_id: clm_025
  include: true
- claim_id: clm_026
  include: true
- claim_id: clm_027
  include: true
- claim_id: clm_028
  include: true
- claim_id: clm_029
  include: true
- claim_id: clm_030
  include: true
- claim_id: clm_031
  include: true
- claim_id: clm_032
  include: true
- claim_id: clm_033
  include: true
- claim_id: clm_034
  include: true
- claim_id: clm_035
  include: true
- claim_id: clm_036
  include: true
- claim_id: clm_037
  include: true
- claim_id: clm_038
  include: true
- claim_id: clm_039
  include: true
- claim_id: clm_040
  include: true
- claim_id: clm_041
  include: true
- claim_id: clm_042
  include: true
- claim_id: clm_043
  include: true
- claim_id: clm_044
  include: true
- claim_id: clm_045
  include: true
- claim_id: clm_046
  include: true
- claim_id: clm_047
  include: true
- claim_id: clm_048
  include: true
- claim_id: clm_049
  include: true
- claim_id: clm_050
  include: true
- claim_id: clm_051
  include: true
- claim_id: clm_052
  include: true
- claim_id: clm_053
  include: true
- claim_id: clm_054
  include: true
- claim_id: clm_055
  include: true
- claim_id: clm_056
  include: true
- claim_id: clm_057
  include: true
- claim_id: clm_058
  include: true
- claim_id: clm_059
  include: true
- claim_id: clm_060
  include: true
- claim_id: clm_061
  include: true
- claim_id: clm_062
  include: true
- claim_id: clm_063
  include: true
- claim_id: clm_064
  include: true
- claim_id: clm_065
  include: true
- claim_id: clm_066
  include: true
- claim_id: clm_067
  include: true
- claim_id: clm_068
  include: true
- claim_id: clm_069
  include: true
- claim_id: clm_070
  include: true
- claim_id: clm_071
  include: true
- claim_id: clm_072
  include: true
- claim_id: clm_073
  include: true
links:
  source_cards:
  - src_20260614_rib045_00
  - src_20260614_rib045_01
  - src_20260614_rib045_02
  - src_20260614_rib045_03
  - src_20260614_rib045_04
  - src_20260614_rib045_05
  - src_20260614_rib045_06
  - src_20260614_rib045_07
  - src_20260614_rib045_08
  - src_20260614_rib045_09
  - src_20260614_rib045_10
  - src_20260614_rib045_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Logprob vs self-reported confidence for LLM classification

## Summary

Source note distilled from research run rf_run_20260614_do_token_logprob_distributions_provide_more: 73 supported claim(s) across 12 source card(s).

## Key claims

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

## Sources

- src_20260614_rib045_00 — Systematic Evaluation of Uncertainty Estimation Methods in Large Language Models
- src_20260614_rib045_01 — On Verbalized Confidence Scores for LLMs
- src_20260614_rib045_02 — On Calibration of Modern Neural Networks
- src_20260614_rib045_03 — Selective Classification for Deep Neural Networks
- src_20260614_rib045_04 — How to Fix a Broken Confidence Estimator: Evaluating Post-hoc Methods for Selective Classification with Deep Neural Networks
- src_20260614_rib045_05 — Are LLM Decisions Faithful to Verbal Confidence?
- src_20260614_rib045_06 — Using logprobs (OpenAI Cookbook)
- src_20260614_rib045_07 — Create a model response (OpenAI Responses API Reference)
- src_20260614_rib045_08 — Unlock Gemini's reasoning: A step-by-step guide to logprobs on Vertex AI
- src_20260614_rib045_09 — logprobs - vllm.v1.engine.logprobs API Reference (vLLM Documentation)
- src_20260614_rib045_10 — llama.cpp server README (tools/server)
- src_20260614_rib045_11 — OpenAI compatibility

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
