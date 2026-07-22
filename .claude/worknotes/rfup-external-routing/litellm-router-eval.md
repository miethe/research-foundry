# litellm Native-Adapter Evaluation (ADR-0008) — Working Artifact

> **Phase 5 / rfup-external-routing-v1** — incrementally built across P5-001 → P5-004.
> **Mode: eval-only.** No install, no import, no execution of `litellm`; no provider credentials.
> This file is the working evaluation record; P6/DOC-006b formalizes the verdict into
> `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`.

- **Package under review**: `litellm` (PyPI) / `BerriAI/litellm` (GitHub)
- **Verdict target**: ADR-0008 (`pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md`, `proposed`)
- **Existing in-repo adapter**: `src/research_foundry/adapters/litellm_router.py` (degraded-mode, `requires = ("litellm",)`)

## Data-Provenance & Zero-Credential Statement (applies to all tasks)

Every datum below was obtained from **public, unauthenticated, read-only** sources:

| Source | Endpoint used | Auth |
|--------|---------------|------|
| PyPI JSON API | `https://pypi.org/pypi/litellm/json` | none |
| GitHub public REST API | `https://api.github.com/repos/BerriAI/litellm` + `/commits?per_page=5` | none (unauthenticated) |
| OSV vulnerability API | `POST https://api.osv.dev/v1/query` + `GET /v1/vulns/{id}` | none |

**No credentials of any kind were used. No authenticated API calls were made. `litellm` was
never downloaded, installed, imported, or executed in this task.** (`pip download` is P5-002; it
has not run yet.) All three sources are public package-index / advisory-database reads, not
provider or completion-API calls.

---

## P5-001 — Static Metadata Review

**Status**: complete · **Data captured**: 2026-07-22

### AC-P5-1 — Maintainer-activity signal (public GitHub metadata, unauthenticated)

`BerriAI/litellm` is a large, highly active, multi-maintainer project — **not** an
abandoned/single-maintainer risk.

| Signal | Value (as of 2026-07-22) |
|--------|--------------------------|
| Stars | 54,373 |
| Forks | 9,976 |
| Watchers (subscribers) | 217 |
| Open issues (incl. PRs) | 4,140 |
| Created | 2023-07-27 |
| Last push (`pushed_at`) | 2026-07-22T15:49Z (**same day** as review) |
| Archived / disabled | No / No |
| License (GitHub SPDX) | `NOASSERTION` (repo declares MIT in-tree; GitHub couldn't map an SPDX id — flagged for P5-002 to confirm from the wheel `METADATA`) |

Recent commit stream (last 5, unauthenticated) shows **daily commits from multiple distinct
maintainers** on 2026-07-22 alone (`mubashir1osmani`, `Mateo Wang`/`mateo-berri`,
`Yassin Kortam`) — active PR-merge cadence and a broad contributor base. Maintainer-activity
signal: **strongly positive** (very active). Caveat: the large open-issue backlog (4,140) is
typical of a fast-moving, high-surface project and is a triage-throughput signal, not an
abandonment signal.

### AC-P5-2 — Release cadence (PyPI public release history)

| Signal | Value |
|--------|-------|
| Total released versions | 1,214 (since 0.1.0 on 2023-07-27) |
| Latest stable | `1.93.0` (2026-07-19) |
| Latest overall | `1.94.0rc3` / `1.95.0.dev1` (2026-07-22) |
| Releases in trailing 30 days | 42 |
| Releases in trailing 90 days | 100 |
| Releases in trailing 365 days | 202 |
| Avg over full span | ~34 releases/month |

Cadence is **extremely high** (multiple releases per day, incl. `rc`/`dev` prereleases). This is
a double-edged signal: strong maintenance velocity, but also a large, fast-moving surface with
frequent breaking-change potential — a pin-and-track-carefully posture would be required on any
future install (developed in P5-004 install/wiring plan).

### AC-P5-3 — CVE / advisory history (OSV public query, read-only)

OSV returns **50 raw records** for `litellm`/PyPI, which dedupe to **27 unique advisories**
(the raw list mirrors each as GHSA + CVE + PYSEC aliases).

| Severity | Unique advisories |
|----------|-------------------|
| CRITICAL | 6 |
| HIGH | 16 |
| MODERATE | 3 |
| (unscored, incl. malware) | 2 |

**Surface distribution (key finding for the verdict)**: the *majority* of these advisories target
the **LiteLLM Proxy / server** component — endpoints and admin surfaces, not the core Python SDK
`litellm.completion()` path that a native adapter would exercise. Examples: authentication bypass
via Host Header / OIDC cache-key collision (CVE-2026-49468, CVE-2026-35030), SQL injection in proxy
API-key verification (CVE-2026-42208), SSTI in `/completions` and `/prompts/test`
(CVE-2024-2952, CVE-2026-42203), privilege escalation via proxy config endpoints (CVE-2026-35029),
`/user/update` role modification (CVE-2026-47102), authenticated command execution via MCP stdio
test endpoints (CVE-2026-42271), SSRF (CVE-2024-6587), and multiple RCE-via-`eval` findings
(CVE-2024-5751, CVE-2024-4264). A precise proxy-vs-SDK split is deferred to P5-003 (adapter
cross-reference), but the first-order read is that **RF's use case — SDK routing, no proxy server —
sidesteps most of the disclosed advisory surface.**

**Supply-chain incident (load-bearing for the install decision)**:
`GHSA-5mg7-485q-xm76` / `MAL-2026-2144` / `PYSEC-2026-2` — "Two LiteLLM versions published
containing credential harvesting malware." Published 2026-03-25. Per OSV detail: after an API-token
exposure from an exploited `trivy` dependency, **versions `1.82.7`–`1.82.8`** were uploaded to PyPI
with auto-activating malware that harvested credentials/files and exfiltrated to a remote API.
Affected range is narrow and **well below** the current `1.93.0`, but this is a concrete
supply-chain event that any install/wiring plan (P5-004) must account for (hash-pin + explicit
version allowlist, avoid the poisoned range).

### AC-P5-4 — Dependency count (PyPI published metadata)

From `requires_dist` on `litellm 1.93.0`:

| Metric | Value |
|--------|-------|
| Total `requires_dist` entries | 82 |
| Core (non-extra) runtime deps | **12** |
| Extra-gated deps | 70 (behind 11 extras) |
| `requires_python` | `>=3.10,<3.15` |

**Core (always-installed) dependencies** — this is the real integration weight for RF's SDK use
case (RF would not install proxy/server extras):
`fastuuid`, `httpx`, `openai (>=2.20,<3)`, `python-dotenv`, `tiktoken`, `importlib-metadata`,
`tokenizers`, `click`, `jinja2`, `aiohttp`, `pydantic (>=2.10,<3)`, `jsonschema`.

**Extras defined** (opt-in, not pulled by a bare `pip install litellm`):
`caching`, `cli`, `extra-proxy`, `google`, `grpc`, `mlflow`, `proxy`, `proxy-runtime`,
`semantic-router`, `stt-nvidia-riva`, `utils` — the heavy/proxy attack-surface deps live here.

**Compatibility flag for the verdict**: `requires_python >=3.10`. RF's `CLAUDE.md` documents a
**Python 3.9+** support floor (with the `tomllib`/`tomli` shim). Installing `litellm` would raise
RF's effective floor to 3.10 — a real (if likely-acceptable) constraint to surface in P5-004.
Transitive/deep dependency-tree count is P5-002 (`pip download --no-deps` inspection).

### AC-P5-5 — Zero-credential / zero-authenticated-call confirmation

Confirmed. See the **Data-Provenance & Zero-Credential Statement** above: all P5-001 data came from
unauthenticated public PyPI/GitHub/OSV reads; no token, key, or credential was presented; no
authenticated endpoint was called; `litellm` was not installed, imported, or executed.

---

## P5-002 — `pip download --no-deps` inspection

**Status**: complete · **Data captured**: 2026-07-22

### AC-P5-6 — Download-only, no install, no import

`pip download --no-deps litellm` was run into an ephemeral scratch dir
(`mktemp -d /tmp/litellm-eval-XXXXXX`), **not** the project `.venv`. The package was
downloaded, not installed; `import litellm` was never executed. The RF `.venv` (uv-managed,
Python 3.14) has no `pip` module, so the download was driven by a **separate** interpreter's
pip (pyenv `python3` 3.12) purely as a download tool — the litellm package was never placed on
any interpreter's import path.

Two artifacts were obtained (both read-only inspected, then the scratch dir was removed):

| Artifact | Version | How obtained | Size |
|----------|---------|--------------|------|
| sdist (`.tar.gz`) | `1.93.0` | `pip download --no-deps litellm` (default; latest stable) | ~16 MB |
| wheel (`.whl`, `py3-none-any`) | `1.91.4` | `pip download --no-deps --only-binary=:all: litellm` | ~17 MB |

**Version-discrepancy caveat**: the bare download resolved the `1.93.0` **sdist** while the
`--only-binary` download resolved the `1.91.4` **wheel** (pip on Python 3.12 picked the newest
*matching* wheel; the two wheels differ only in `Requires-Python` upper bound — 1.91.4 declares
`<3.14`, the 1.93.0 sdist declares `<3.15`). The declared-dependency shape (below) is **identical**
across both, so this does not affect the finding; it is recorded for provenance honesty.

**Build-isolation note (not an install)**: computing sdist metadata caused pip to install
*build* dependencies into an ephemeral isolated env ("Installing build dependencies… Preparing
metadata (pyproject.toml)"). This is pip's metadata-build step — `litellm` itself was **not**
installed into the project venv, **not** imported, and **not** executed; the `litellm` /
`litellm-proxy` / `lite` console-scripts (see AC-P5-8) were **not** placed on PATH.

### AC-P5-7 — Declared dependency tree (from wheel `METADATA` / sdist `PKG-INFO`)

`pip download --no-deps` fetches only the litellm distribution itself, so the "tree" here is
litellm's **declared** `Requires-Dist` set (the first-level edges of a full transitive tree, not
the resolved transitive closure — resolving that would require a non-`--no-deps` download, out of
scope for eval-only). Counts confirmed against the actual downloaded `METADATA`/`PKG-INFO`,
matching P5-001's PyPI-API-derived figures exactly:

| Metric | Value (wheel 1.91.4 METADATA == sdist 1.93.0 PKG-INFO) |
|--------|--------------------------------------------------------|
| Total `Requires-Dist` entries | **82** |
| Core (unconditional) runtime deps | **12** |
| Extra-gated deps | **70** (behind 11 extras) |
| `Provides-Extra` count | **11** |
| `Requires-Python` | `>=3.10,<3.14` (wheel 1.91.4) / `<3.15` (sdist 1.93.0) |
| License | `MIT` (`License-Expression: MIT` — resolves P5-001's `NOASSERTION` GitHub-SPDX flag) |

**12 core (always-installed) deps** — the real integration weight for RF's SDK-routing use case:
`fastuuid`, `httpx`, `openai>=2.20,<3`, `python-dotenv`, `tiktoken`, `importlib-metadata`,
`tokenizers`, `click`, `jinja2`, `aiohttp`, `pydantic>=2.10,<3`, `jsonschema`.

**11 extras** (opt-in; **not** pulled by a bare `pip install litellm`): `caching`, `cli`,
`extra-proxy`, `google`, `grpc`, `mlflow`, `proxy`, `proxy-runtime`, `semantic-router`,
`stt-nvidia-riva`, `utils`. The heavy / high-attack-surface *runtime* deps (fastapi, uvicorn,
gunicorn, boto3, azure-*, mcp, cryptography, prisma, google-cloud-*, restrictedpython,
detect-secrets, opentelemetry, sentry, ddtrace) all live behind `proxy` / `proxy-runtime` /
`extra-proxy` and would **not** be installed for RF's SDK-only path.

**Dependency-overlap note (favourable)**: several core deps are already in RF's own tree or are
ubiquitous (`httpx`, `pydantic>=2`, `jinja2`, `click`, `aiohttp`, `python-dotenv`) — so the *net*
new-package footprint of the 12 core deps is smaller than 12. The one hard version constraint that
matters is `openai>=2.20,<3` (a specific major-version pin RF would inherit) and `pydantic>=2.10`.

### AC-P5-8 — Top-level code surface vs. what `litellm_router.py`'s docstring documents

**Wheel layout**: a single top-level package `litellm/` (no sibling top-level packages — no
namespace pollution). Scale: **2,995 files total, 2,068 `.py` files**. Notable subtrees present in
the **base wheel regardless of extras** (the extras gate runtime *deps*, not the bundled *code*):

| Subtree | Files in wheel | Relevance |
|---------|---------------|-----------|
| `litellm/proxy/` | **1,339** | Full proxy/server + admin surface — the component the **majority of P5-001's CVEs target** (auth bypass, SQLi, SSTI, priv-esc, RCE). Ships on disk even without the `proxy` extra. |
| `litellm/llms/` | 887 | Provider-integration code — the SDK `completion()` path RF would actually exercise. |
| `litellm/integrations/` | 208 | Observability/telemetry callbacks (langfuse, sentry, datadog, opentelemetry, …) — mostly lazy/optional. |

Additional top-level modules/packages beyond a "just route a completion" mental model:
`secret_managers/`, `_redis.py`/`_redis_credential_provider.py`, `experimental_mcp_client/`,
`rust_bridge/`, `containers/`, `sandbox/`, `setup_wizard.py`, `proxy_auth/`, `passthrough/`,
`a2a_protocol/`, plus bundled data JSON (`model_prices_and_context_window_backup.json`,
`blog_posts.json`).

**Console-scripts (entry_points.txt)** — an install would add three executables to the venv `bin/`:
`litellm = litellm:run_server`, `litellm-proxy = litellm.proxy.client.cli:cli`,
`lite = litellm.proxy.client.cli:cli`. All three launch the proxy server/CLI.

**Does this materially expand the security-review surface beyond the docstring? — YES, on disk.**
`litellm_router.py`'s docstring frames the dependency narrowly: "when `litellm` is importable …
honour env-based key availability to pick the first reachable provider" — i.e. a thin SDK
completion client. It does **not** disclose that installing `litellm` also lands a full proxy
server, secret-manager integrations, an experimental MCP client, a rust bridge, sandbox/container
code, and proxy CLI executables on disk. For a security review, that is a real surface expansion
and must be named.

**Two strong mitigations keep the *executed* surface narrow** (basis for P5-004's posture):
1. **Lazy imports** — litellm ships `_lazy_imports.py` + `_lazy_imports_registry.py`; a bare
   `import litellm` does not eagerly import `litellm.proxy` / fastapi / the heavy integrations, so
   the proxy code is **present but dormant** unless explicitly imported/launched.
2. **RF never runs the proxy** — the CVE-heavy surface (proxy endpoints/admin) requires running
   `litellm-proxy`; RF's adapter would only call the in-process SDK routing path. The on-disk
   presence is a supply-chain / audit-scope fact, not an active RF code path — consistent with
   P5-001's finding that RF's SDK-only use "sidesteps most of the disclosed advisory surface."

### AC-P5-9 — Zero-network-beyond-index / zero-credential confirmation

Confirmed. The only network egress in this task was the `pip download` PyPI package-index fetch
(sdist + wheel) — a public, unauthenticated package-index read, **not** a provider/completion API
call. No provider credential, API key, or token was presented or referenced; no `litellm`
completion/proxy endpoint was contacted. `litellm` was downloaded to a scratch dir, statically
inspected (tar/unzip + `grep`/`awk` over METADATA/PKG-INFO/RECORD/entry_points), and the scratch
dir was then removed — never installed into the project venv, never imported, never executed.

## P5-003 — Cross-reference existing `litellm_router.py`

**Status**: complete · **Data captured**: 2026-07-22 · **Read-only refs**:
`src/research_foundry/adapters/litellm_router.py`, `src/research_foundry/adapters/base.py`,
`git show 2d198a8`. No install/import/execution of `litellm`; no credentials. Analysis is a
static read of already-landed code against the P5-001/P5-002 findings.

### AC-P5-10 — Degraded-mode-today vs. would-newly-execute-if-installed

The security-posture judgment for P5-004 rests on one structural fact the module docstring
*understates*: **this adapter never calls `litellm`, in either mode.** It is a config-driven
*router* (profile → `{provider, model, api_base, …}` decision), not a completion client. The
delta between the two modes is therefore far narrower than "offline stub vs. live LLM call."

**Degraded mode (current default — `litellm` absent, no provider keys):**

1. `available()` → `all(module_available(m) for m in ("litellm",))`. Per `base.py`,
   `module_available` is `importlib.util.find_spec(...) is not None` — a **spec probe that does
   not import** the module. With `litellm` absent → `False`.
2. `route()` reads `config/model_profiles.yaml` (local file via `FoundryConfig`), takes
   `chosen = preferred[0]`, and — because `if self.available():` is `False` — **skips the entire
   reachability loop**; `reachable` stays `None`.
3. Result: `selected = preferred[0]`, `live = False`, `degraded = True`,
   `reason = "preferred_fallback"`. `run()` wraps it as an `AdapterResult(degraded=True)` whose
   sole artifact is the YAML of the decision.
4. Net: a **pure, deterministic function of the YAML config** — no network, no secret read, no
   completion, no `litellm` import. Fully reproducible/testable; first preferred entry always wins.

**Would-newly-execute if `litellm` were installed AND a provider key present:**

1. `available()` → `find_spec("litellm")` is now non-`None` → `True`. **Still no import of
   `litellm`** — `find_spec` loads nothing, and this adapter contains no `import litellm`
   statement anywhere. Installing the package only flips a *presence probe*.
2. `route()` now **runs the reachability loop**: for each preferred entry it looks up
   `provider` → `key_var` in `_PROVIDER_KEYS`; if `key_var is None` (local, e.g. `ollama`) **or**
   `env.get(key_var)` is truthy (key present in the environment), it selects that entry and breaks.
   `env.get(key_var)` is a **presence/truthiness read of an env var — it does not transmit,
   validate, or dial the credential anywhere.**
3. Result: `selected` may now be a *later* preferred entry (the first *reachable* one, not
   necessarily `preferred[0]`); `live = True`; `degraded = False`; `reason = "reachable_provider"`.
4. What still does **not** happen even in real mode: no `litellm` client is constructed, no
   `litellm.completion()` / provider HTTP call is made, no credential leaves the process. The
   docstring's own "real mode" wording — "honour env-based key availability to pick the first
   reachable provider" — is **selection, not calling**, and the code confirms it.

**The entire newly-executed surface inside this adapter** is thus a bounded `for`-loop over the
already-in-memory `preferred` list doing dict lookups + env-var presence checks. That is the whole
behavioral delta: (a) `available()` flips `True` (a `find_spec` probe), (b) the loop runs and may
pick a non-first entry, (c) `degraded`/`reason` flip, (d) selection becomes env-sensitive. **No new
network egress, no credential transmission, no `litellm` code executes** from installing the
package to satisfy `requires=("litellm",)`.

**Where the real risk actually lives (scoping the verdict):** the Mode-D live-completion surface —
the thing P5-001's CVEs and P5-002's 2,068-file / proxy-subtree footprint speak to — is **not in
this adapter at all.** It would live in a *future consumer* of the routing decision (the in-process
completion path), which does not exist here; RF's discovery/synthesis swarm is driven **out-of-band
(Path B, Hermes/CC)** and merely *reads* the emitted YAML decision. So "install `litellm` so this
adapter's `available()` is `True`" and "wire a live completion (Mode-D)" are **two separable steps**,
and only the first is in scope for the adapter itself. This substantially de-risks an eventual
"accept": installing the package changes this adapter's behavior only from "always `preferred[0]`,
`degraded`" to "first env-reachable entry, `degraded=False`" — still no live call.

### AC-P5-11 — The `2d198a8` ICA-provider mapping fix as forward-compat groundwork (not activation)

`git show 2d198a8` touched the adapter in exactly **two** places (14 insertions), both pure
correctness scaffolding, **neither adding any live call, import, or credential use**:

1. **`"ica": "RF_LLM_API_KEY"` added to `_PROVIDER_KEYS`.** This is a latent-bug fix, not a new
   capability. Without the mapping, `_PROVIDER_KEYS.get("ica")` returns `None`, and the loop's
   `if key_var is None or env.get(key_var)` branch treats `ica` **like a key-free local provider
   (`ollama`)** — i.e. *reachable without any credential*. That bug is **inert today** (the loop
   never runs while `available()` is `False`) and would **only manifest once `litellm` is
   installed**, at which point an ICA-first profile would be wrongly marked `degraded=False` /
   `reachable_provider` with no `RF_LLM_API_KEY` set. The fix makes the *future* real-mode
   selection correct. It also documents the Mode-D Gate #2 invariant in-code: `ica` carries a
   dedicated `RF_LLM_API_KEY`, never the real-vendor `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`.
2. **`"api_base": selected.get("api_base")` propagation** into the decision dict. Unlike the
   mapping, this line sits **outside** the `if self.available()` guard, so it **does run today** —
   a degraded decision already carries `preferred[0]`'s `api_base` (e.g. the ICA gateway base).
   This is harmless: it is a string field in a YAML artifact; nothing in RF dials it. Its purpose
   is forward-compat — so a downstream/out-of-band consumer targets the right OpenAI-compatible
   endpoint *when* a completion is later wired.

**Assessment consequence:** `2d198a8` means the verdict must treat the adapter as
**already-wired-and-corrected**, not a from-scratch integration. The dual-mode routing logic, the
full provider→key mapping *including the ICA correctness fix*, the `api_base` plumbing, the
`degraded`/`reason` labeling, and the accompanying tests (`tests/test_adapters.py`, +9 lines in the
same commit) **already exist and are correct**. The forward-compat groundwork is deliberately
build-out-ahead-of-install: it makes the code behave correctly the moment `litellm` is present,
without itself constituting an install or an activation. Concretely, the *marginal integration
weight* of an eventual "accept" is reduced to:

- installing the `litellm` package (the 12 core deps, the ~2,068-`.py`-file / proxy-subtree on-disk
  footprint, and the supply-chain posture — hash-pin + version-allowlist avoiding the poisoned
  `1.82.7`–`1.82.8` range — all from P5-001/P5-002) purely to flip `available()` → `True`; **and,
  entirely separately and out of this adapter's scope**,
- a live-completion consumer path (the genuine Mode-D gate), which is *not* implemented here and
  which the out-of-band Path B swarm currently substitutes for.

In short: the adapter is a correctly-built, dormant router. `2d198a8` is groundwork that ensures its
future real-mode is *correct*, not evidence that real-mode is *active*. (P5-004 will convert this
into the accept/reject/conditional verdict + unexecuted install/wiring plan — not started here.)

## P5-004 — Accept/reject verdict + install/wiring plan

**Status**: complete · **Synthesized**: 2026-07-22 · **Inputs**: P5-001 (static metadata),
P5-002 (`pip download --no-deps` inspection), P5-003 (existing-adapter cross-reference). No
install/import/execution of `litellm`; no provider credentials. This is the finalized working
verdict; P6/DOC-006b promotes it into the durable design-spec
`docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`.

### AC-P5-12 — Verdict on ADR-0008

**Verdict: `conditional` (conditional-accept of the native-adapter direction; defer the actual
`litellm` install until a live-completion consumer is scoped).**

ADR-0008 frames the choice as *Path B hardening* vs. *native adapter*. The evidence gathered in
P5-001 → P5-003 does not support a clean `accept` (install now) or a clean `reject` (abandon the
adapter); it supports a **conditional** verdict that separates two decisions ADR-0008 tends to
conflate: (a) is the `litellm_router.py` *direction* sound and worth keeping, and (b) should we
install the `litellm` package *now*.

**Why not a clean `accept` (install now):** the decisive finding from P5-003 is that installing
`litellm` today buys **almost nothing functional**. The adapter never calls `litellm` in either
mode — it is a config-driven *router*, and `available()` is a non-importing `find_spec` presence
probe (P5-003 / AC-P5-10). Installing the package only flips `available()` `False → True`, which
changes the emitted decision from "always `preferred[0]`, `degraded=True`" to "first
env-reachable entry, `degraded=False`". No live completion, no network egress, no credential
transmission results from the install itself. Meanwhile the install carries **real, non-zero
costs** documented in P5-001/P5-002: a Python-floor raise `3.9 → 3.10` (AC-P5-4), a supply-chain
posture obligation from the confirmed credential-harvesting malware in `1.82.7`–`1.82.8`
(AC-P5-3), a pin-and-track burden against an extreme ~34-releases/month cadence (AC-P5-2), and a
2,068-`.py`-file on-disk audit surface that includes a full dormant proxy subtree (AC-P5-8).
Paying those costs to flip a boolean that only improves *routing-metadata* fidelity — while the
actual discovery/synthesis swarm still runs out-of-band via Path B (P5-003) — is a poor trade
**at this moment**.

**Why not a clean `reject` (abandon the adapter / harden Path B only):** the adapter is
demonstrably **well-built, correct, and cheap to keep** (P5-003 / AC-P5-11). `2d198a8` already
landed the dual-mode routing, the full provider→key mapping *including* the ICA correctness fix
and the Mode-D Gate #2 invariant (`ica` → `RF_LLM_API_KEY`, never the real-vendor key), the
`api_base` plumbing, and tests. It is dormant, deterministic, and imposes zero runtime cost while
`litellm` is absent. Deleting it would discard correct forward-compat groundwork and gain nothing.
The security profile is also more favourable than ADR-0008's framing implies: P5-001's CVE surface
is **majority proxy/server**, not the SDK `completion()` path, and P5-002 confirms the proxy code
ships dormant behind lazy imports and is never run by RF. So the native-adapter direction is *not*
disqualified on security grounds — the disqualifier for *acting now* is purely value-vs-cost
timing.

**Net conditional verdict:** Keep `litellm_router.py` as-is (dormant, correct). Pre-approve the
native-adapter *direction*. **Do not install `litellm` until** a concrete live-completion consumer
(the genuine Mode-D path — see AC-P5-10 "where the real risk lives") is scoped and separately
gated; until that consumer exists, an install only raises RF's Python floor and audit/supply-chain
surface for a routing-metadata-fidelity gain that Path B does not currently need. When that
consumer is scoped, the install becomes justified and the (unexecuted) plan below is ready to
execute behind the stated conditions.

**Conditions that convert this `conditional` to an `accept` (all must hold):**
1. A live-completion consumer of the routing decision is scoped as a separate, explicitly Mode-D
   feature (installing `litellm` for `available()` alone does not clear this bar — it is a no-op
   functional gain per P5-003).
2. RF's supported-Python floor is confirmed acceptable to raise `3.9 → 3.10`, or `litellm` is
   isolated so the floor raise is opt-in (P5-002 / AC-P5-7).
3. The install pins an exact, hash-verified version and an allowlist that **excludes** the poisoned
   `1.82.7`–`1.82.8` range (P5-001 / AC-P5-3 supply-chain incident).
4. A pin-and-track (renovate-style) posture is accepted for the fast release cadence (P5-002).

### AC-P5-13 — Install / wiring plan (UNEXECUTED — no step here installs `litellm`)

> **UNEXECUTED.** Nothing in this section is run by this phase or this artifact. It is a forward
> recipe for a *future, separately-gated* feature to consume if/when the AC-P5-12 conditions hold.
> Recorded regardless of verdict direction so a future re-evaluation does not restart from zero.

**Step 0 — Precondition gate (Mode-D).** Do not proceed unless a live-completion consumer is
scoped as its own feature and the four AC-P5-12 conditions are satisfied. Installing to satisfy
`requires=("litellm",)` alone is explicitly *not* sufficient justification (P5-003).

**Step 1 — Dependency declaration (isolated).** Add `litellm` as an **optional/extra** dependency
(e.g. a `litellm` extra in `pyproject.toml`), never a core dep, so the `>=3.10` floor and the 12
core transitive deps (`fastuuid`, `httpx`, `openai>=2.20,<3`, `python-dotenv`, `tiktoken`,
`importlib-metadata`, `tokenizers`, `click`, `jinja2`, `aiohttp`, `pydantic>=2.10,<3`,
`jsonschema` — P5-002) are opt-in. Install **without** any extra (`pip install litellm`, never
`litellm[proxy]`/`[extra-proxy]`/`[proxy-runtime]`) so the CVE-heavy proxy *runtime* deps are
never pulled (P5-002 / AC-P5-7).

**Step 2 — Supply-chain pin.** Pin an exact version at/above current stable (`>=1.93.0`), hash-lock
it (`--require-hashes` / lockfile), and encode an allowlist that forbids `1.82.7`–`1.82.8`
(P5-001 / AC-P5-3). Add the package to whatever dependency-scanning the repo runs.

**Step 3 — Verify `available()` flips, nothing else.** After install, confirm
`litellm_router.available()` returns `True` and that `route()` now runs the reachability loop
(first env-reachable entry, `degraded=False`) — this is the *entire* adapter-level behavioral delta
(P5-003 / AC-P5-10). No adapter code imports or calls `litellm`; the install must not, by itself,
introduce any live call.

**Step 4 — (Separate feature) live-completion consumer.** The genuine Mode-D work — constructing a
client and issuing a real `completion()` — is **out of scope for the adapter and for any install
step**. It is a distinct feature with its own Mode-D gate, credential handling (honouring the
`ica` → `RF_LLM_API_KEY` invariant `2d198a8` encodes, never the real-vendor key), and review. It
must not be folded into the install PR.

**Step 5 — Audit-surface acknowledgement.** Record in the install PR that the base wheel lands a
dormant proxy subtree + secret-manager/MCP/rust-bridge/sandbox code on disk (P5-002 / AC-P5-8),
kept inert by lazy imports and by RF never launching the `litellm`/`litellm-proxy`/`lite`
console-scripts. This is an audit-scope fact to disclose, not an active code path.

**Rollback:** because the adapter degrades deterministically when `litellm` is absent (P5-003),
rollback is simply uninstalling the package — the adapter reverts to `preferred[0]`/`degraded=True`
with no code change required.

### AC-P5-14 — Evaluation-method limitations (confidence calibration for downstream review)

This verdict was produced under the phase's Hard-Constraint-2 eval-only bound. The following limits
bound its confidence — a `karen`/downstream reviewer should weight the conclusion accordingly:

- **No install, no import, no execution.** All package internals were assessed from static
  metadata, the downloaded wheel/sdist layout, and source-read of the in-repo adapter. Runtime
  behavior of `litellm` itself (actual import side-effects, real lazy-import boundaries under load,
  actual `completion()` egress) was **not** observed — it is inferred from declared metadata, file
  layout, and the presence of `_lazy_imports*.py` (P5-002 / AC-P5-8). Confidence on "proxy code is
  dormant" is *high-but-static* (based on lazy-import files + RF never launching the proxy), not
  runtime-verified.
- **Declared, not resolved, dependency tree.** `--no-deps` gives litellm's first-level
  `Requires-Dist` (12 core + 70 extra-gated), **not** the full transitive closure (P5-002 /
  AC-P5-7). The deep transitive count is unquantified; the "net footprint < 12 due to overlap" note
  is a directional estimate, not a resolved-lockfile count.
- **No credential/live-call path exercised.** The claim "install alone triggers no live call" is
  grounded in a static source-read of `litellm_router.py` (no `import litellm`, `find_spec`-only
  probe, env-var *presence* checks — P5-003), which is high-confidence for *this adapter*, but the
  future Mode-D consumer's behavior is by definition unevaluated (it does not exist yet).
- **CVE surface split is first-order.** The "majority proxy, not SDK" finding (P5-001 / AC-P5-3) is
  based on advisory titles/descriptions and the proxy-subtree file weight, not a per-CVE code-path
  trace. A future security review with an actual install could refine the SDK-vs-proxy split.
- **Point-in-time data.** All maintainer/cadence/CVE figures are as-of 2026-07-22 and will drift
  given the ~34-releases/month cadence; re-check before acting on the install plan.

Overall confidence in the **`conditional` verdict direction: high** (it rests on the structural,
static-verifiable fact that install ≠ live-call for this adapter). Confidence in the **quantitative
security/dependency depth: medium** (bounded by no-install). This asymmetry is the point of the
conditional: the *timing/value* judgment is robust; the *deep security clearance* is deferred to
the install-time review the conditions mandate.

### AC-P5-15 — Zero-live-external-calls / zero-credentials statement (phase-wide, load-bearing)

**Explicit confirmation (not mere absence):** Across the entire Phase 5 evaluation — P5-001 through
P5-004 — **zero live external calls to any provider/completion API were made, and zero credentials
of any kind (API keys, tokens, provider keys, `RF_LLM_API_KEY`, `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, or otherwise) were read, referenced, presented, or exercised.** `litellm` was
**never installed into any interpreter's import path, never imported, and never executed**; its
console-scripts (`litellm`/`litellm-proxy`/`lite`) were never placed on PATH or run. The only
network egress in the whole phase was:
1. unauthenticated public reads of PyPI JSON, GitHub public REST, and OSV (P5-001), and
2. the `pip download --no-deps` PyPI package-index fetch of the wheel/sdist (P5-002),

both of which are public, read-only **package-index/advisory** operations — not provider or
completion API calls, and not credentialed. This satisfies the parent plan's Hard Constraint 2 and
the phase exit criterion "0 live external calls, 0 credentials used during evaluation." This
synthesis task (P5-004) itself performed **no** network calls at all — it is pure synthesis of the
P5-001/P5-002/P5-003 records above.

---

**Phase 5 verdict summary (for P6/DOC-006b promotion):**
`conditional` — keep the dormant, correct `litellm_router.py`; pre-approve the native-adapter
direction; defer the `litellm` install until a separately-gated Mode-D live-completion consumer is
scoped, and then only behind the four AC-P5-12 conditions (isolated/optional dep, Python-floor
sign-off, hash-pin excluding `1.82.7`–`1.82.8`, pin-and-track). Recommended next action:
`defer-until: a live-completion (Mode-D) consumer feature is scoped`.
