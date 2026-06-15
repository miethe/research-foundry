---
schema_version: '0.1'
type: research_report
report_id: report_20260615_determinism_ci_cost_control_for_agentic
title: Determinism & CI cost-control for agentic eval harnesses
intent_id: intent_research_20260614_determinism_ci_cost_control_for_agentic
evidence_bundle_id: pending
created_at: '2026-06-15T10:38:49-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

Evals is a framework for evaluating LLMs or systems built using LLMs. [claim:clm_001]
The Completion Function Protocol extends evals beyond plain model completions to advanced use cases such as prompt chains or tool-using agents. [claim:clm_002]
A completion function standardizes inputs (a text string or Chat conversation) and outputs (a list of text strings), generalizing model completions. [claim:clm_003]
Basic eval templates (Match, Includes, FuzzyMatch, JsonMatch) are intended for deterministic ground-truth checks where the desired response has little variation. [claim:clm_004]
Model-graded evals delegate judgment to a model when the desired response can vary significantly, such as open-ended answers, by using the model to grade itself. [claim:clm_005]
Completion functions are registered as YAML under evals/registry/completion_fns and invoked by registered key via the oaieval CLI. [claim:clm_006]
The evals registry data is stored using Git-LFS and fetched via git lfs fetch/pull. [claim:clm_007]
The Pytest and Vitest/Jest eval integrations shipped in beta with v0.3.0 of the LangSmith Python and TypeScript SDKs (published Jan 22, 2025). [claim:clm_008]
In Python, a test is tracked in LangSmith by adding the @pytest.mark.langsmith decorator. [claim:clm_009]
In TypeScript, test cases are tracked in LangSmith by wrapping them in an ls.describe() block. [claim:clm_010]
Testing frameworks naturally support defining pass/fail criteria and raising assertion errors in CI, enabling early regression detection when evals run in a CI pipeline. [claim:clm_011]
LangSmith lets teams log feedback and compare results over time to prevent regressions and keep deploying the best version of an application. [claim:clm_012]
A dedicated GitHub Action to make configuring eval runs in CI easy was announced as forthcoming at publish time. [claim:clm_013]
A concurrency group ensures only a single job or workflow using the same group runs at a time, and the group key can be any string or expression. [claim:clm_014]
When another run in the same group is in progress, a newly queued run becomes pending, and by default an existing pending run is canceled and replaced by the new one. [claim:clm_015]
Setting cancel-in-progress: true cancels any currently running job or workflow in the same concurrency group, and it can also be given as an expression for conditional cancellation. [claim:clm_016]
queue: single (the default) allows at most one pending run per group and cancels/replaces any existing pending run, while queue: max allows up to 100 pending runs and cancels additional runs once the queue is full. [claim:clm_017]
Combining queue: max with cancel-in-progress: true is disallowed and produces a workflow validation error. [claim:clm_018]
Runs in the same concurrency group are processed in FIFO order by the time each started waiting on the group, but because actual start times vary, ordering is not guaranteed. [claim:clm_019]
The recommended workflow-level group key combines github.workflow and github.ref so concurrency is isolated per branch, and group expressions accept the github, inputs, vars, needs, strategy, and matrix contexts. [claim:clm_020]
The Messages API temperature parameter defaults to 1.0 and ranges from 0.0 to 1.0, with guidance to use values closer to 0.0 for analytical / multiple-choice tasks and closer to 1.0 for creative tasks. [claim:clm_021]
The documentation explicitly warns that even at a temperature of 0.0 the results will not be fully deterministic, establishing that low temperature alone does not guarantee reproducible Messages API outputs. [claim:clm_022]
top_p enables nucleus sampling by cutting off the cumulative token probability distribution at a specified threshold, and the docs mark it as recommended for advanced use cases only. [claim:clm_023]
top_k samples only from the top K options for each subsequent token to remove long-tail low-probability responses, and like top_p is marked as recommended for advanced use cases only. [claim:clm_024]
The Messages API request body exposes only temperature, top_p, and top_k as sampling controls and documents no seed or deterministic-seeding parameter, so reproducibility cannot be requested at the API level. [claim:clm_025]
pytest-recording is a pytest plugin built on VCR.py that records and replays HTTP traffic for tests. [claim:clm_026]
The plugin exposes a pytest.mark.vcr marker that maps onto VCR.py's use_cassettes API for per-test cassette control. [claim:clm_027]
By default the plugin runs in VCR's 'none' record mode specifically to prevent unintentional live network requests during tests. [claim:clm_028]
Recording is enabled by passing the --record-mode CLI option (e.g. once) when invoking pytest. [claim:clm_029]
The plugin adds a 'rewrite' record mode that regenerates a cassette from scratch rather than extending it as VCR.py's 'all' mode does. [claim:clm_030]
A pytest.mark.block_network mark blocks network access (socket-based transports and pycurl) to give confidence tests do not go over the wire. [claim:clm_031]
Specific hosts can be whitelisted during network blocking via allowed_hosts (regex), e.g. on the mark or via --allowed-hosts on the CLI. [claim:clm_032]
Cassettes are stored as per-test YAML files on disk (capturing the recorded HTTP request/response), e.g. under cassettes/{module}/test_name.yaml. [claim:clm_033]
OpenAI Chat Completions are non-deterministic by default, meaning identical requests can yield different model outputs. [claim:clm_034]
Setting an integer seed and reusing the same value across requests yields (mostly) deterministic outputs. [claim:clm_035]
Determinism also requires that all other request parameters (such as prompt and temperature) be identical across requests. [claim:clm_036]
Determinism can be broken by OpenAI's own backend model-configuration changes, which it surfaces via the system_fingerprint field. [claim:clm_037]
A change in the system_fingerprint value signals that outputs may differ even when seed and other parameters are held constant. [claim:clm_038]
OpenAI characterizes seed-based reproducibility as only (mostly) deterministic, not guaranteed bit-for-bit identical output. [claim:clm_039]
Specifying the seed parameter makes the system attempt deterministic sampling so that repeated requests with the same seed and parameters return the same result. [claim:clm_040]
To get consistent outputs, developers should set the seed parameter to any integer but reuse the same value across requests. [claim:clm_041]
All other request parameters (prompt, temperature, top_p, etc.) must also be held identical across requests for consistent outputs. [claim:clm_042]
When seed, request parameters, and system_fingerprint all match across requests, model outputs will mostly be identical. [claim:clm_043]
Determinism is best-effort, not guaranteed: outputs can still differ even when parameters and system_fingerprint match, due to inherent model non-determinism. [claim:clm_044]
The seed feature delivers only '(mostly) consistent' outputs, framing determinism as best-effort rather than a hard guarantee. [claim:clm_045]
FakeListLLM is LangChain's fake LLM intended for testing purposes. [claim:clm_046]
The responses attribute is a list[str] whose entries are returned in order, giving deterministic, scripted outputs. [claim:clm_047]
FakeListLLM extends the LLM base class, so it conforms to the standard LangChain language-model interface and can be substituted for a real LLM. [claim:clm_048]
Through its BaseLLM inheritance FakeListLLM exposes the full Runnable surface including sync and async variants (invoke/ainvoke, batch/abatch, stream/astream, generate/agenerate). [claim:clm_049]
An internal index counter i is incremented after every model invocation, which advances through the predefined responses and is exposed primarily for testing. [claim:clm_050]
A sleep attribute (float | None) sets a per-response delay in seconds; it is ignored by FakeListLLM itself but used by subclasses to simulate latency. [claim:clm_051]
FakeListLLM is a long-standing part of langchain_core, available since v0.1 and present in the current reference (labeled v1.4.7 latest). [claim:clm_052]
SGLang's deterministic inference integrates batch-invariant kernels (mean, log-softmax, matrix multiplication) from Thinking Machines Lab. [claim:clm_053]
In deterministic mode every subtest produced 1 unique output across trials, versus 2-18 unique outputs in normal mode (e.g., the prefix test reported 5/8/18/2 in normal FlashInfer). [claim:clm_054]
SGLang reports an average deterministic-mode slowdown of 34.35% on FlashInfer and FlashAttention 3 backends, versus the 61.5% slowdown reported in Thinking Machines Lab's blog. [claim:clm_055]
Enabling CUDA Graphs yields at least a 2.79x speedup across all attention kernels in deterministic mode. [claim:clm_056]
Only TP1 and TP2 are deterministic (consistent floating-point addition order); larger tensor-parallel setups require modifications to reduce kernels to achieve determinism. [claim:clm_057]
Deterministic inference currently supports only dense models such as Qwen3-8B or LLaMa-3.1-8B; MoE models are not yet supported, though planned. [claim:clm_058]
Deterministic multinomial sampling perturbs logits with Gumbel noise from a seeded hash function, so the same (inputs, seed) pair yields the same sample even when temperature > 0. [claim:clm_059]
Phoenix defines an experiment as a structured comparison between versions of an application using identical inputs and evaluation criteria. [claim:clm_060]
Running experiments in code against a stored dataset lets teams test changes and verify whether they actually improve quality rather than assuming improvement. [claim:clm_061]
Experiments rerun the same inputs through different application versions for side-by-side comparison so improvements are measured, not assumed. [claim:clm_062]
An experiment task is a function that takes each dataset example and produces an output by running the application logic or model on the input. [claim:clm_063]
Pulling down the saved dataset and running the experiment over it tests the new version on the exact same inputs that previously failed, enabling deterministic comparison. [claim:clm_064]
The experiment is launched via client.experiments.run_experiment(dataset=..., task=..., evaluators=...), after which Phoenix logs the experiment results automatically. [claim:clm_065]
Beyond the basic flow, datasets/experiments support comparing multiple prompt or model variants and tracking quality improvements over time as the application evolves. [claim:clm_066]
The primary root cause of LLM inference nondeterminism is that server load (and thus batch size) varies nondeterministically, changing reduction order rather than GPU concurrency or floating point alone. [claim:clm_067]
The common hypothesis that concurrency plus floating-point arithmetic explains nondeterminism is incomplete; atomic adds are usually absent from an LLM forward pass. [claim:clm_068]
Running Qwen3-235B at temperature 0 across 1000 runs produced 80 unique completions, with the first divergence occurring at the 103rd token. [claim:clm_069]
Enabling batch-invariant kernels made all 1000 completions identical. [claim:clm_070]
Batch invariance need only be enforced on the three reduction operations: RMSNorm, matrix multiplication, and attention. [claim:clm_071]
Floating-point non-associativity is the underlying mathematical residual: adding the same numbers in a different order can yield a different result. [claim:clm_072]
Deterministic vLLM on Qwen-8B was slower than the default: 26s baseline vs 55s unoptimized deterministic and 42s with improved attention (roughly 1.6x-2.1x slowdown). [claim:clm_073]
Setting LANGSMITH_TEST_CACHE caches all HTTP requests to disk so LLM evals do not re-hit the model on every CI commit, addressing cost control for agentic CI. [claim:clm_074]
Cached requests are written to a cassettes directory and replayed on subsequent runs, and checking the cache into the repo lets CI reuse it for deterministic, near-free reruns. [claim:clm_075]
In langsmith>=0.4.10 caching can be scoped to specific URLs or hostnames via the cached_hosts argument to the langsmith pytest marker. [claim:clm_076]
The pytest plugin requires Python SDK langsmith>=0.3.4, with the langsmith[pytest] extra needed for rich terminal output and test caching. [claim:clm_077]
The langsmith pytest marker is compatible with pytest-xdist, so evaluation tests can be parallelized using the standard -n auto invocation. [claim:clm_078]
Each decorated test automatically logs a pass/fail boolean under the 'pass' feedback key, and an assert in the test fails the run like a normal unit test so eval failures fail the CI job. [claim:clm_079]
Beyond the default pass key, custom feedback (e.g. an LLM-as-judge score) can be recorded with log_feedback and traced separately via the trace_feedback context manager. [claim:clm_080]

## Inferences

**Inference:** For agentic CI evals where tool-call patterns matter but exact text does not, output-text equality assertions (Match/Includes/JsonMatch) are the wrong gating primitive against live Claude or OpenAI models, because both vendors disclaim bit-for-bit reproducibility (Anthropic warns temperature 0.0 is still not fully deterministic and exposes no seed; OpenAI seed is only '(mostly) deterministic'). [claim:clm_inf01]
**Inference:** Among API-level determinism strategies, OpenAI seed+identical-params is strictly stronger than the Anthropic Messages API for reproducibility (OpenAI offers a seed knob and a system_fingerprint drift signal, whereas Anthropic offers neither), but neither reaches the bit-identical output that self-hosted batch-invariant kernels deliver. [claim:clm_inf02]
**Inference:** Batch-invariant deterministic inference is the only strategy in the evidence base that empirically eliminates output variance (1000/1000 identical completions; 1 unique output per SGLang subtest), but it is unavailable to teams that consume Claude or OpenAI as hosted APIs because it requires self-hosting vLLM/SGLang on dense models at TP1/TP2. [claim:clm_inf03]
**Inference:** The measured cost of true bit-identical determinism is a 34%-62% inference slowdown (SGLang 34.35% average; Thinking Machines 61.5%; deterministic vLLM 1.6x-2.1x on Qwen-8B), which makes batch-invariant determinism economically defensible only for offline regression suites or RL training, not for latency-sensitive per-PR CI gates. [claim:clm_inf04]
**Inference:** For RF's swarm harness, the most reliable CI-gating determinism strategy is to stub the model leg entirely (FakeListLLM scripted responses or recorded VCR/pytest-recording cassettes) rather than to chase API-level reproducibility, because stubs and cassettes are byte-deterministic and network-free by construction whereas seed/temperature only reduce, not remove, live variance. [claim:clm_inf05]
**Inference:** The recommended trajectory-assertion pattern is to wrap the agent in OpenAI evals' Completion Function Protocol (which standardizes tool-using-agent I/O) and assert on the recorded tool-call sequence and arguments captured by a VCR-style cassette, treating the cassette's ordered request log as the canonical trajectory rather than asserting on final answer text. [claim:clm_inf06]
**Inference:** A two-leg split is the minimum viable RF determinism configuration: a deterministic leg (stubbed/cassette-backed tool calls + tool-sequence assertions) that gates every PR with zero API spend, and a stochastic leg (live model, rubric/model-graded judge) that runs nightly or on-demand and never blocks a PR on a single live failure. [claim:clm_inf07]
**Inference:** LangSmith's LANGSMITH_TEST_CACHE (committed cassettes) is the lowest-friction per-PR cost-control pattern for an agentic eval harness because it converts every repeat CI run into a near-free deterministic replay, and from langsmith>=0.4.10 cached_hosts lets teams cache only the expensive model hosts (api.openai.com, api.anthropic.com) while leaving other traffic live. [claim:clm_inf08]
**Inference:** GitHub Actions concurrency groups keyed on github.workflow + github.ref with cancel-in-progress true are the recommended cost ceiling for live (non-cached) agentic eval legs, because they cap a branch to one in-flight run and auto-cancel superseded runs, preventing redundant API spend from rapid pushes. [claim:clm_inf09]
**Inference:** The cached-replay leg and the pytest-xdist parallelism flag are complementary rather than competing cost levers: caching removes per-run API spend while -n auto removes wall-clock time, so an RF deterministic leg should combine committed cassettes with pytest -n auto to keep the gate both cheap and fast. [claim:clm_inf10]
**Inference:** For RF's stochastic leg, the pass/fail threshold should be a rubric-based model-graded score gated as a score-delta against a committed baseline (regression gate) rather than a hard per-run pass/fail, because model-graded judgment varies run to run and a fixed absolute threshold would convert judge variance into flaky CI failures. [claim:clm_inf11]
**Inference:** The Phoenix experiment pattern (rerun a fixed stored dataset through each app version with the same evaluators) is the right harness for RF's nightly stochastic leg, because pinning inputs isolates the variable under test to the agent/prompt change and lets a model-graded score-delta be attributed to the code change rather than to input drift. [claim:clm_inf12]
**Inference:** Recorded tool fixtures (VCR cassettes, LANGSMITH_TEST_CACHE) break down when the recording drifts from live behavior, and because pytest-recording defaults to 'none' mode a stale cassette silently fails the test rather than re-hitting the network, so RF must schedule periodic cassette refreshes via --record-mode=rewrite on the nightly live leg to detect and regenerate drift. [claim:clm_inf13]
**Inference:** OpenAI's system_fingerprint is the only available machine-readable signal in the evidence base for deciding when to invalidate and re-record fixtures, so an RF cassette-refresh policy should treat a changed system_fingerprint (or, for Claude where no such field exists, a fixed time cadence) as the trigger to regenerate recordings. [claim:clm_inf14]
**Inference:** Mapping onto Claude Agent SDK primitives, the load-bearing gap for RF's swarm harness is the absence of any server-side seed or reproducibility parameter on the Anthropic Messages API: RF cannot gate on Claude output determinism at all and must implement trajectory determinism entirely client-side via stubbing, cassette replay, and tool-sequence assertions. [claim:clm_inf15]
**Inference:** On the comparison axes of stability, spend, and tool-call-signal preservation, recorded/cassette replay dominates for per-PR gating (high stability, near-zero spend, full tool-sequence fidelity), batch-invariant inference dominates for offline reproducibility (highest stability, high spend, full fidelity), and live seed/temperature scores lowest on stability for hosted Claude/OpenAI while being the only option that exercises real current model behavior. [claim:clm_inf16]
**Inference:** An acceptable flakiness rate for a gating eval is effectively zero on the deterministic leg (stubs/cassettes are byte-deterministic, so any flake is a real bug), and retries/quarantine should be confined to the stochastic leg; auto-retrying a deterministic-leg failure would mask a genuine regression and is an anti-pattern. [claim:clm_inf17]

## Speculation

**Speculation:** RF will likely need a hybrid gate in which the deterministic cassette leg blocks merges and a quarantined stochastic leg posts an advisory score-delta comment, because the evidence shows no hosted-API path to fully reliable live gating and the promised LangSmith CI GitHub Action (forthcoming as of Jan 2025) had not shipped a stable cross-provider gating story in the captured sources. [claim:clm_spec01]
**Speculation:** If Anthropic adds a seed parameter and a system_fingerprint-equivalent drift field to the Messages API, RF could promote a thin slice of its stochastic leg into a per-PR gate; absent that, batch-invariant determinism reaching MoE and TP greater than 2 (currently future work in SGLang) is the more probable route to reproducible gating for large Claude-class models. [claim:clm_spec02]

## Open questions

- None recorded.

## Sources

- src_20260614_rib041_05: openai/evals — A framework for evaluating LLMs and LLM systems
- src_20260614_rib041_10: Introducing Pytest and Vitest integrations for LangSmith Evaluations
- src_20260614_rib041_08: Control the concurrency of workflows and jobs - GitHub Docs
- src_20260614_rib041_04: Messages - Anthropic Claude API Reference
- src_20260614_rib041_06: pytest-recording (VCR.py-powered HTTP record/replay for pytest)
- src_20260614_rib041_02: Advanced usage (seed and system_fingerprint) - OpenAI API
- src_20260614_rib041_03: How to make your completions outputs consistent with the new seed parameter
- src_20260614_rib041_07: FakeListLLM - LangChain core documentation
- src_20260614_rib041_01: Towards Deterministic Inference in SGLang and Reproducible RL Training
- src_20260614_rib041_11: Optimize Your App with Experiments (Quickstart: Datasets & Experiments) — Arize Phoenix
- src_20260614_rib041_00: Defeating Nondeterminism in LLM Inference
- src_20260614_rib041_09: How to run evaluations with pytest - LangSmith Docs
