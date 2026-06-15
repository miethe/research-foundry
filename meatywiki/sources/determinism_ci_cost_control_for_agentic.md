---
id: mwb_20260615_determinism_ci_cost_control_for_agentic
evidence_bundle_id: bundle_20260615_intent_research_20260614_determinism_ci_cost
target_page: meatywiki/sources/determinism_ci_cost_control_for_agentic.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_determinism_ci_cost_control_for_agentic:
  80 supported claim(s) across 12 source card(s).'
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
- claim_id: clm_074
  include: true
- claim_id: clm_075
  include: true
- claim_id: clm_076
  include: true
- claim_id: clm_077
  include: true
- claim_id: clm_078
  include: true
- claim_id: clm_079
  include: true
- claim_id: clm_080
  include: true
links:
  source_cards:
  - src_20260614_rib041_00
  - src_20260614_rib041_01
  - src_20260614_rib041_02
  - src_20260614_rib041_03
  - src_20260614_rib041_04
  - src_20260614_rib041_05
  - src_20260614_rib041_06
  - src_20260614_rib041_07
  - src_20260614_rib041_08
  - src_20260614_rib041_09
  - src_20260614_rib041_10
  - src_20260614_rib041_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Determinism & CI cost-control for agentic eval harnesses

## Summary

Source note distilled from research run rf_run_20260614_determinism_ci_cost_control_for_agentic: 80 supported claim(s) across 12 source card(s).

## Key claims

- Evals is a framework for evaluating LLMs or systems built using LLMs. [claim:clm_001]
- The Completion Function Protocol extends evals beyond plain model completions to advanced use cases such as prompt chains or tool-using agents. [claim:clm_002]
- A completion function standardizes inputs (a text string or Chat conversation) and outputs (a list of text strings), generalizing model completions. [claim:clm_003]
- Basic eval templates (Match, Includes, FuzzyMatch, JsonMatch) are intended for deterministic ground-truth checks where the desired response has little variation. [claim:clm_004]
- Model-graded evals delegate judgment to a model when the desired response can vary significantly, such as open-ended answers, by using the model to grade itself. [claim:clm_005]
- Completion functions are registered as YAML under evals/registry/completion_fns and invoked by registered key via the oaieval CLI. [claim:clm_006]
- The evals registry data is stored using Git-LFS and fetched via git lfs fetch/pull. [claim:clm_007]
- The Pytest and Vitest/Jest eval integrations shipped in beta with v0.3.0 of the LangSmith Python and TypeScript SDKs (published Jan 22, 2025). [claim:clm_008]
- In Python, a test is tracked in LangSmith by adding the @pytest.mark.langsmith decorator. [claim:clm_009]
- In TypeScript, test cases are tracked in LangSmith by wrapping them in an ls.describe() block. [claim:clm_010]
- Testing frameworks naturally support defining pass/fail criteria and raising assertion errors in CI, enabling early regression detection when evals run in a CI pipeline. [claim:clm_011]
- LangSmith lets teams log feedback and compare results over time to prevent regressions and keep deploying the best version of an application. [claim:clm_012]
- A dedicated GitHub Action to make configuring eval runs in CI easy was announced as forthcoming at publish time. [claim:clm_013]
- A concurrency group ensures only a single job or workflow using the same group runs at a time, and the group key can be any string or expression. [claim:clm_014]
- When another run in the same group is in progress, a newly queued run becomes pending, and by default an existing pending run is canceled and replaced by the new one. [claim:clm_015]
- Setting cancel-in-progress: true cancels any currently running job or workflow in the same concurrency group, and it can also be given as an expression for conditional cancellation. [claim:clm_016]
- queue: single (the default) allows at most one pending run per group and cancels/replaces any existing pending run, while queue: max allows up to 100 pending runs and cancels additional runs once the queue is full. [claim:clm_017]
- Combining queue: max with cancel-in-progress: true is disallowed and produces a workflow validation error. [claim:clm_018]
- Runs in the same concurrency group are processed in FIFO order by the time each started waiting on the group, but because actual start times vary, ordering is not guaranteed. [claim:clm_019]
- The recommended workflow-level group key combines github.workflow and github.ref so concurrency is isolated per branch, and group expressions accept the github, inputs, vars, needs, strategy, and matrix contexts. [claim:clm_020]
- The Messages API temperature parameter defaults to 1.0 and ranges from 0.0 to 1.0, with guidance to use values closer to 0.0 for analytical / multiple-choice tasks and closer to 1.0 for creative tasks. [claim:clm_021]
- The documentation explicitly warns that even at a temperature of 0.0 the results will not be fully deterministic, establishing that low temperature alone does not guarantee reproducible Messages API outputs. [claim:clm_022]
- top_p enables nucleus sampling by cutting off the cumulative token probability distribution at a specified threshold, and the docs mark it as recommended for advanced use cases only. [claim:clm_023]
- top_k samples only from the top K options for each subsequent token to remove long-tail low-probability responses, and like top_p is marked as recommended for advanced use cases only. [claim:clm_024]
- The Messages API request body exposes only temperature, top_p, and top_k as sampling controls and documents no seed or deterministic-seeding parameter, so reproducibility cannot be requested at the API level. [claim:clm_025]
- pytest-recording is a pytest plugin built on VCR.py that records and replays HTTP traffic for tests. [claim:clm_026]
- The plugin exposes a pytest.mark.vcr marker that maps onto VCR.py's use_cassettes API for per-test cassette control. [claim:clm_027]
- By default the plugin runs in VCR's 'none' record mode specifically to prevent unintentional live network requests during tests. [claim:clm_028]
- Recording is enabled by passing the --record-mode CLI option (e.g. once) when invoking pytest. [claim:clm_029]
- The plugin adds a 'rewrite' record mode that regenerates a cassette from scratch rather than extending it as VCR.py's 'all' mode does. [claim:clm_030]
- A pytest.mark.block_network mark blocks network access (socket-based transports and pycurl) to give confidence tests do not go over the wire. [claim:clm_031]
- Specific hosts can be whitelisted during network blocking via allowed_hosts (regex), e.g. on the mark or via --allowed-hosts on the CLI. [claim:clm_032]
- Cassettes are stored as per-test YAML files on disk (capturing the recorded HTTP request/response), e.g. under cassettes/{module}/test_name.yaml. [claim:clm_033]
- OpenAI Chat Completions are non-deterministic by default, meaning identical requests can yield different model outputs. [claim:clm_034]
- Setting an integer seed and reusing the same value across requests yields (mostly) deterministic outputs. [claim:clm_035]
- Determinism also requires that all other request parameters (such as prompt and temperature) be identical across requests. [claim:clm_036]
- Determinism can be broken by OpenAI's own backend model-configuration changes, which it surfaces via the system_fingerprint field. [claim:clm_037]
- A change in the system_fingerprint value signals that outputs may differ even when seed and other parameters are held constant. [claim:clm_038]
- OpenAI characterizes seed-based reproducibility as only (mostly) deterministic, not guaranteed bit-for-bit identical output. [claim:clm_039]
- Specifying the seed parameter makes the system attempt deterministic sampling so that repeated requests with the same seed and parameters return the same result. [claim:clm_040]
- To get consistent outputs, developers should set the seed parameter to any integer but reuse the same value across requests. [claim:clm_041]
- All other request parameters (prompt, temperature, top_p, etc.) must also be held identical across requests for consistent outputs. [claim:clm_042]
- When seed, request parameters, and system_fingerprint all match across requests, model outputs will mostly be identical. [claim:clm_043]
- Determinism is best-effort, not guaranteed: outputs can still differ even when parameters and system_fingerprint match, due to inherent model non-determinism. [claim:clm_044]
- The seed feature delivers only '(mostly) consistent' outputs, framing determinism as best-effort rather than a hard guarantee. [claim:clm_045]
- FakeListLLM is LangChain's fake LLM intended for testing purposes. [claim:clm_046]
- The responses attribute is a list[str] whose entries are returned in order, giving deterministic, scripted outputs. [claim:clm_047]
- FakeListLLM extends the LLM base class, so it conforms to the standard LangChain language-model interface and can be substituted for a real LLM. [claim:clm_048]
- Through its BaseLLM inheritance FakeListLLM exposes the full Runnable surface including sync and async variants (invoke/ainvoke, batch/abatch, stream/astream, generate/agenerate). [claim:clm_049]
- An internal index counter i is incremented after every model invocation, which advances through the predefined responses and is exposed primarily for testing. [claim:clm_050]
- A sleep attribute (float | None) sets a per-response delay in seconds; it is ignored by FakeListLLM itself but used by subclasses to simulate latency. [claim:clm_051]
- FakeListLLM is a long-standing part of langchain_core, available since v0.1 and present in the current reference (labeled v1.4.7 latest). [claim:clm_052]
- SGLang's deterministic inference integrates batch-invariant kernels (mean, log-softmax, matrix multiplication) from Thinking Machines Lab. [claim:clm_053]
- In deterministic mode every subtest produced 1 unique output across trials, versus 2-18 unique outputs in normal mode (e.g., the prefix test reported 5/8/18/2 in normal FlashInfer). [claim:clm_054]
- SGLang reports an average deterministic-mode slowdown of 34.35% on FlashInfer and FlashAttention 3 backends, versus the 61.5% slowdown reported in Thinking Machines Lab's blog. [claim:clm_055]
- Enabling CUDA Graphs yields at least a 2.79x speedup across all attention kernels in deterministic mode. [claim:clm_056]
- Only TP1 and TP2 are deterministic (consistent floating-point addition order); larger tensor-parallel setups require modifications to reduce kernels to achieve determinism. [claim:clm_057]
- Deterministic inference currently supports only dense models such as Qwen3-8B or LLaMa-3.1-8B; MoE models are not yet supported, though planned. [claim:clm_058]
- Deterministic multinomial sampling perturbs logits with Gumbel noise from a seeded hash function, so the same (inputs, seed) pair yields the same sample even when temperature > 0. [claim:clm_059]
- Phoenix defines an experiment as a structured comparison between versions of an application using identical inputs and evaluation criteria. [claim:clm_060]
- Running experiments in code against a stored dataset lets teams test changes and verify whether they actually improve quality rather than assuming improvement. [claim:clm_061]
- Experiments rerun the same inputs through different application versions for side-by-side comparison so improvements are measured, not assumed. [claim:clm_062]
- An experiment task is a function that takes each dataset example and produces an output by running the application logic or model on the input. [claim:clm_063]
- Pulling down the saved dataset and running the experiment over it tests the new version on the exact same inputs that previously failed, enabling deterministic comparison. [claim:clm_064]
- The experiment is launched via client.experiments.run_experiment(dataset=..., task=..., evaluators=...), after which Phoenix logs the experiment results automatically. [claim:clm_065]
- Beyond the basic flow, datasets/experiments support comparing multiple prompt or model variants and tracking quality improvements over time as the application evolves. [claim:clm_066]
- The primary root cause of LLM inference nondeterminism is that server load (and thus batch size) varies nondeterministically, changing reduction order rather than GPU concurrency or floating point alone. [claim:clm_067]
- The common hypothesis that concurrency plus floating-point arithmetic explains nondeterminism is incomplete; atomic adds are usually absent from an LLM forward pass. [claim:clm_068]
- Running Qwen3-235B at temperature 0 across 1000 runs produced 80 unique completions, with the first divergence occurring at the 103rd token. [claim:clm_069]
- Enabling batch-invariant kernels made all 1000 completions identical. [claim:clm_070]
- Batch invariance need only be enforced on the three reduction operations: RMSNorm, matrix multiplication, and attention. [claim:clm_071]
- Floating-point non-associativity is the underlying mathematical residual: adding the same numbers in a different order can yield a different result. [claim:clm_072]
- Deterministic vLLM on Qwen-8B was slower than the default: 26s baseline vs 55s unoptimized deterministic and 42s with improved attention (roughly 1.6x-2.1x slowdown). [claim:clm_073]
- Setting LANGSMITH_TEST_CACHE caches all HTTP requests to disk so LLM evals do not re-hit the model on every CI commit, addressing cost control for agentic CI. [claim:clm_074]
- Cached requests are written to a cassettes directory and replayed on subsequent runs, and checking the cache into the repo lets CI reuse it for deterministic, near-free reruns. [claim:clm_075]
- In langsmith>=0.4.10 caching can be scoped to specific URLs or hostnames via the cached_hosts argument to the langsmith pytest marker. [claim:clm_076]
- The pytest plugin requires Python SDK langsmith>=0.3.4, with the langsmith[pytest] extra needed for rich terminal output and test caching. [claim:clm_077]
- The langsmith pytest marker is compatible with pytest-xdist, so evaluation tests can be parallelized using the standard -n auto invocation. [claim:clm_078]
- Each decorated test automatically logs a pass/fail boolean under the 'pass' feedback key, and an assert in the test fails the run like a normal unit test so eval failures fail the CI job. [claim:clm_079]
- Beyond the default pass key, custom feedback (e.g. an LLM-as-judge score) can be recorded with log_feedback and traced separately via the trace_feedback context manager. [claim:clm_080]

## Sources

- src_20260614_rib041_00 — Defeating Nondeterminism in LLM Inference
- src_20260614_rib041_01 — Towards Deterministic Inference in SGLang and Reproducible RL Training
- src_20260614_rib041_02 — Advanced usage (seed and system_fingerprint) - OpenAI API
- src_20260614_rib041_03 — How to make your completions outputs consistent with the new seed parameter
- src_20260614_rib041_04 — Messages - Anthropic Claude API Reference
- src_20260614_rib041_05 — openai/evals — A framework for evaluating LLMs and LLM systems
- src_20260614_rib041_06 — pytest-recording (VCR.py-powered HTTP record/replay for pytest)
- src_20260614_rib041_07 — FakeListLLM - LangChain core documentation
- src_20260614_rib041_08 — Control the concurrency of workflows and jobs - GitHub Docs
- src_20260614_rib041_09 — How to run evaluations with pytest - LangSmith Docs
- src_20260614_rib041_10 — Introducing Pytest and Vitest integrations for LangSmith Evaluations
- src_20260614_rib041_11 — Optimize Your App with Experiments (Quickstart: Datasets & Experiments) — Arize Phoenix

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
