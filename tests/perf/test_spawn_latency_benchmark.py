"""Spawn-latency micro-benchmark for AgentJobService.spawn_job() (SEC-2.5/FU-1).

Benchmark data only -- no pass/fail assertion at this stage.

Standalone usage::

    python tests/perf/test_spawn_latency_benchmark.py

pytest usage::

    PYTHONPATH=src pytest tests/perf/test_spawn_latency_benchmark.py -q -s
"""

from __future__ import annotations

import statistics
import sys
import time
import uuid
from pathlib import Path

# For standalone execution: ensure src/ is importable without PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from research_foundry.services.agent_job_schemas import (  # noqa: E402
    AgentJob,
    AgentJobStatus,
)
from research_foundry.services.agent_job_service import AgentJobService  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Synthetic credential — never reaches any real service (child uses command_override).
_CREDENTIAL_BYTES: bytes = (
    b"sk-test-0000000000000000000000000000000000000000000000"
)

# Lightweight dummy child: sleeps briefly so the process is cleanly reapable.
_DUMMY_COMMAND: list[str] = [
    sys.executable,
    "-c",
    "import time; time.sleep(0.01)",
]

# ---------------------------------------------------------------------------
# Fixture factory
# ---------------------------------------------------------------------------


def _make_job(job_id: str) -> AgentJob:
    """Return a minimal AgentJob fixture for benchmarking.

    Provider is ``claude_sdk`` (not in ``_IN_PROCESS_PROVIDERS``).
    policy_snapshot contains the mandatory ``allowed_tools`` and
    ``data_scopes`` keys so validate_agent_job would pass if called.
    """
    _ts = "2026-01-01T00:00:00Z"
    return AgentJob(
        agent_job_id=job_id,
        project_id="benchmark-project",
        workspace_id=None,
        created_by=None,
        provider="claude_sdk",
        model_profile="haiku",
        request_kind="research",
        input_claim_ids=[],
        input_source_ids=[],
        input_report_id=None,
        policy_snapshot={"allowed_tools": [], "data_scopes": []},
        budget_usd=None,
        max_runtime_minutes=None,
        status=AgentJobStatus.queued,
        created_at=_ts,
        updated_at=_ts,
        started_at=None,
        completed_at=None,
    )


# ---------------------------------------------------------------------------
# Core benchmark
# ---------------------------------------------------------------------------


def run_spawn_benchmark(n: int = 20) -> dict[str, float]:
    """Measure subprocess spawn latency over *n* iterations.

    Each iteration:

    1. Calls ``spawn_job()`` with ``command_override=_DUMMY_COMMAND``.
       This exercises credential temp-file creation + ``subprocess.Popen``
       without depending on any RF agent infrastructure.
    2. Records wall-clock time (``time.perf_counter``) spanning only the
       ``spawn_job()`` call itself.
    3. Immediately calls ``cleanup_job()`` to terminate the child and
       unlink the temp credential file.

    Parameters
    ----------
    n:
        Number of spawn iterations to time.

    Returns
    -------
    dict[str, float]
        Keys ``p50``, ``p95``, ``p99`` in milliseconds.

    Note
    ----
    Benchmark data only — no pass/fail assertion at this stage.
    """
    svc = AgentJobService()
    latencies_ms: list[float] = []

    for _ in range(n):
        job_id = f"bench-{uuid.uuid4().hex[:12]}"
        job = _make_job(job_id)

        t0 = time.perf_counter()
        svc.spawn_job(job, _CREDENTIAL_BYTES, command_override=_DUMMY_COMMAND)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies_ms.append(elapsed_ms)

        # Terminate child and unlink cred file immediately after timing.
        svc.cleanup_job(job_id)

    latencies_ms.sort()

    # statistics.quantiles(data, n=100) returns 99 cut-points representing
    # p1 … p99 at indices 0 … 98 respectively.
    qs = statistics.quantiles(latencies_ms, n=100)
    return {
        "p50": qs[49],
        "p95": qs[94],
        "p99": qs[98],
    }


def _print_results(label: str, results: dict[str, float]) -> None:
    """Print benchmark results in a structured, human-readable format."""
    print(f"\n--- {label} ---")
    print(f"  p50 = {results['p50']:.2f} ms")
    print(f"  p95 = {results['p95']:.2f} ms")
    print(f"  p99 = {results['p99']:.2f} ms")
    print("  (benchmark data only -- no pass/fail assertion at this stage)")


# ---------------------------------------------------------------------------
# pytest test function
# ---------------------------------------------------------------------------


def test_spawn_latency_captures_p99() -> None:
    """Run 5 spawn iterations and apply a loose 5000 ms sanity bound on p99.

    This is a non-blocking, data-capture benchmark.  The 5000 ms bound is
    intentionally loose -- a sanity check only, not a performance contract.
    Actual measured p99 on healthy hardware is expected to be well under
    100 ms; the 5000 ms ceiling catches only catastrophic hangs.
    """
    results = run_spawn_benchmark(n=5)
    _print_results("test_spawn_latency_captures_p99 (N=5)", results)
    assert results["p99"] < 5000.0, (
        f"p99 spawn latency {results['p99']:.1f} ms exceeded 5000 ms sanity bound"
    )


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running spawn latency benchmark (N=20)...")
    _results = run_spawn_benchmark(n=20)
    _print_results("spawn_job() micro-benchmark (N=20)", _results)
