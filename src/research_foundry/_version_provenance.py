"""Version provenance for an AOS CLI — what release is this, and which checkout is it?

VENDORED ARTIFACT. This module is byte-identical across every AOS repo (intenttree,
research-foundry, agentic-research, meatywiki, skillmeat, agentic_meta_dev). It is copied,
not imported across repos, deliberately: an import would couple six independently-versioned
repos to one, and the AOS rule is *borrow concepts, not frameworks*. Edit the upstream
(see ARTIFACT-UPSTREAM-REGISTRY.md) and re-vendor; never patch one copy in place.

Why this exists
---------------
`itt --version` reported the string ``0.1.0`` both BEFORE and AFTER a feature release
landed (measured 2026-08-11 and 2026-08-12, node_01KZVW15TYM9V7MSTT1BGCAVSW). The declared
version had never been bumped, so it could not witness whether a shipped CLI feature was
present — the exact question a cross-host parity check needs answered. Worse, every AOS CLI
is installed as an **editable** tool, so the code that actually runs is whatever the backing
checkout currently sits on: two hosts reported the same ``0.1.0`` while sitting on different
commits (laptop 10e5ee69, node eceb870c). A declared version alone cannot describe an
editable install; the checkout commit is the only honest answer.

So provenance is reported in two layers:

  declared version   the package's own ``version`` — bumped by humans on feature releases,
                     and the only identity a *wheel* install has.
  checkout identity  for an editable install, the resolved path plus ``git describe`` of the
                     backing tree. Automatic, and it changes on every commit, so it
                     distinguishes builds even when nobody remembered to bump.

Hard constraints
----------------
``--version`` is called by health checks, shims, and CI. It therefore MUST NOT hang, and
MUST NOT raise. Every git call is timeout-bounded and every failure degrades to omitting
the field — never to a traceback and never to a wrong value. An absent field means
"could not determine", which is why the machine-readable form distinguishes ``null`` from a
value rather than substituting a placeholder that a caller could mistake for a real commit.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from importlib import metadata as _md
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

__all__ = ["version_info", "version_string", "resolve_checkout"]

# A `--version` call must return promptly even on a pathological repo. Two seconds is far
# above a warm `git describe` (single-digit ms here) and far below anything a caller would
# read as a hang.
_GIT_TIMEOUT_S = 2.0

# `core.fsmonitor` has hung git-adjacent tooling on this machine twice (it broke `skillmeat
# add` and wedged an advisory lock held by a dead pid), and it is now disabled globally for
# that reason. Pinning it off *per invocation* keeps this helper safe on hosts that have not
# had that fix applied — notably the node — rather than relying on ambient config.
_GIT_BASE = ("git", "-c", "core.fsmonitor=false")


def _run_git(cwd: Path, *args: str) -> str | None:
    """Run one git command in ``cwd``; return stripped stdout, or None on ANY failure.

    Deliberately swallows everything: a missing git binary, a non-repo directory, a
    permission error, a timeout, or a non-zero exit all mean the same thing to a caller —
    the checkout identity could not be determined.

    ``None`` means FAILED. An empty string means *succeeded and printed nothing*, and the two
    must stay distinguishable: `git status --porcelain` on a clean tree exits 0 with no
    output, so collapsing empty into None reports a pristine checkout as "dirtiness unknown".
    That is the precise dishonesty this module exists to avoid — an undeterminable field and a
    determined-empty one are different answers.
    """
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [*_GIT_BASE, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _editable_path(dist: _md.Distribution) -> Path | None:
    """Return the source checkout backing an editable install, else None.

    Reads PEP 610 ``direct_url.json``, which pip/uv write for any install from a local
    path. ``dir_info.editable`` is the authoritative editable marker — inferring it from a
    ``site-packages`` path shape guesses wrong for both src-layout and namespace packages.
    """
    try:
        raw = dist.read_text("direct_url.json")
    except Exception:  # noqa: BLE001 - metadata may be absent or unreadable
        return None
    if not raw:
        return None
    try:
        info = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(info, dict):
        return None
    if not (info.get("dir_info") or {}).get("editable"):
        return None  # installed FROM a local dir, but not editable — the wheel is a snapshot
    url = info.get("url")
    if not isinstance(url, str) or not url.startswith("file:"):
        return None
    parsed = urlparse(url)
    # A file: URL's path is percent-encoded; a checkout under "My Repos" would otherwise
    # resolve to a literal "%20".
    path = Path(unquote(parsed.path))
    try:
        return path if path.is_dir() else None
    except OSError:
        return None


def resolve_checkout(path: Path) -> dict[str, Any]:
    """Describe the git checkout at ``path``. Every field may be None (never a placeholder)."""
    toplevel = _run_git(path, "rev-parse", "--show-toplevel") or None
    if toplevel is None:
        # An editable install whose source tree is not a git checkout (a release tarball,
        # a vendored copy). Legitimate — report the path and stop, do not invent a commit.
        return {"root": str(path), "commit": None, "commit_short": None,
                "branch": None, "describe": None, "dirty": None}

    # `or None` normalises a successful-but-empty result to "undeterminable" for fields where
    # an empty string is not a meaningful value (a commit or a branch name never legitimately
    # empties). `dirty` below is the one field where "" IS the answer, so it is handled apart.
    commit = _run_git(path, "rev-parse", "HEAD") or None
    branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD") or None
    describe = _run_git(path, "describe", "--tags", "--always", "--dirty") or None

    # `git status --porcelain` is the reliable dirty check. `describe --dirty` cannot substitute:
    # it only flags tracked-file modifications, and on a repo with no tags (four of the six AOS
    # repos have zero) it degrades to a bare sha carrying no dirty marker at all.
    # `--untracked-files=no` is deliberate — a stray build artifact is not a different build,
    # and counting it would pin every working repo to dirty forever.
    status = _run_git(path, "status", "--porcelain", "--untracked-files=no")
    dirty: bool | None = None if status is None else bool(status)

    return {
        "root": toplevel,
        "commit": commit,
        "commit_short": commit[:8] if commit else None,
        "branch": branch if branch != "HEAD" else None,  # detached HEAD has no branch name
        "describe": describe,
        "dirty": dirty,
    }


def version_info(dist_name: str, prog_name: str | None = None) -> dict[str, Any]:
    """Machine-readable provenance for the installed distribution ``dist_name``.

    Never raises. ``version`` is None only when the distribution is not installed at all
    (e.g. running from a source tree with no install), which is itself the useful answer.
    """
    info: dict[str, Any] = {
        "program": prog_name or dist_name,
        "distribution": dist_name,
        "version": None,
        "install": "unknown",
        "location": None,
        "commit": None,
        "commit_short": None,
        "branch": None,
        "describe": None,
        "dirty": None,
        "host": None,
        "python": platform.python_version(),
    }
    try:
        info["host"] = platform.node() or None
    except Exception:  # noqa: BLE001 - platform can fail in odd sandboxes
        pass

    try:
        dist = _md.distribution(dist_name)
    except _md.PackageNotFoundError:
        info["install"] = "not-installed"
        return info
    except Exception:  # noqa: BLE001 - a corrupt metadata dir must not break --version
        return info

    try:
        info["version"] = dist.metadata["Version"] or None
    except Exception:  # noqa: BLE001
        pass

    checkout_root = _editable_path(dist)
    if checkout_root is None:
        info["install"] = "wheel"
        return info

    info["install"] = "editable"
    info["location"] = str(checkout_root)
    info.update({k: v for k, v in resolve_checkout(checkout_root).items() if k != "root"})
    return info


def version_string(dist_name: str, prog_name: str | None = None) -> str:
    """Human-readable one-line provenance, in click's ``--version`` house style.

    Shapes, by install kind::

        skillmeat, version 0.80.0
        itt, version 0.4.0 (editable a1b2c3d4-dirty on main)
        itt, version 0.4.0 (editable, checkout not a git repo)
        itt (not installed)
    """
    info = version_info(dist_name, prog_name)
    prog = info["program"]

    if info["install"] == "not-installed":
        return f"{prog} (not installed)"

    version = info["version"] or "unknown"
    base = f"{prog}, version {version}"

    if info["install"] != "editable":
        return base

    if not info["commit_short"]:
        return f"{base} (editable, checkout not a git repo)"

    ident = info["commit_short"]
    if info["dirty"]:
        ident += "-dirty"
    if info["branch"]:
        ident += f" on {info['branch']}"
    return f"{base} (editable {ident})"


def _emit(dist_name: str, prog_name: str | None = None) -> None:
    """Print provenance to stdout — JSON when AOS_VERSION_JSON is truthy, else one line.

    The env var is how the fleet-wide `aos version` aggregator collects structured output
    from six CLIs across three arg-parsing frameworks without each needing a bespoke
    `--version --json` flag combination (click's ``version_option`` in particular exits
    before any sibling flag is parsed).
    """
    if os.environ.get("AOS_VERSION_JSON", "").strip().lower() in {"1", "true", "yes", "on"}:
        print(json.dumps(version_info(dist_name, prog_name), indent=2, sort_keys=True))
    else:
        print(version_string(dist_name, prog_name))
