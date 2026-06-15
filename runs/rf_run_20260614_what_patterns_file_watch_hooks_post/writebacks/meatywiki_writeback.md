---
id: mwb_20260614_broker_less_event_patterns_to_close
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_patterns_file
target_page: meatywiki/sources/broker_less_event_patterns_to_close.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_patterns_file_watch_hooks_post:
  71 supported claim(s) across 12 source card(s).'
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
links:
  source_cards:
  - src_20260614_rib024_00
  - src_20260614_rib024_01
  - src_20260614_rib024_02
  - src_20260614_rib024_03
  - src_20260614_rib024_04
  - src_20260614_rib024_05
  - src_20260614_rib024_06
  - src_20260614_rib024_07
  - src_20260614_rib024_08
  - src_20260614_rib024_09
  - src_20260614_rib024_10
  - src_20260614_rib024_11
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Broker-less Event Patterns to Close Local-First Agentic OS Seams

## Summary

Source note distilled from research run rf_run_20260614_what_patterns_file_watch_hooks_post: 71 supported claim(s) across 12 source card(s).

## Key claims

- SSE is a one-way (server-to-client) channel, so a client cannot push events to the server over the same connection. [claim:clm_001]
- By default an SSE connection auto-reconnects if it closes, and is terminated explicitly via the .close() method. [claim:clm_002]
- The server-side script emitting SSE events must respond with the MIME type text/event-stream. [claim:clm_003]
- The 'retry' field sets the reconnection wait time in milliseconds (must be an integer, else ignored), and the 'id' field sets the EventSource object's last event ID used on reconnect. [claim:clm_004]
- Without HTTP/2, SSE is limited to a very low number of open connections (6) per browser per domain; over HTTP/2 the simultaneous HTTP-stream limit is negotiated (defaulting to 100). [claim:clm_005]
- The page was last modified on May 15, 2025, fixing its recency. [claim:clm_006]
- pre-commit supports ten git hook stages: commit-msg, post-checkout, post-commit, post-merge, post-rewrite, pre-commit, pre-merge-commit, pre-push, pre-rebase, and prepare-commit-msg. [claim:clm_007]
- Hooks that do not operate on files (post-checkout, post-commit, post-merge, post-rewrite, pre-rebase) must be set as always_run: true or they will always be skipped. [claim:clm_008]
- Hooks can be installed for particular git hook types by passing --hook-type to pre-commit install, which may be specified multiple times. [claim:clm_009]
- The stages property restricts which git hook stages a hook runs on, set in .pre-commit-hooks.yaml or overridden in .pre-commit-config.yaml, falling back to the top-level default_stages option which defaults to all stages. [claim:clm_010]
- default_install_hook_types is a list of --hook-types used by default when running pre-commit install, and it defaults to [pre-commit], so only the pre-commit hook is installed unless other types are specified. [claim:clm_011]
- default_stages is a configuration-wide default for the stages property of hooks, defaults to all stages, and only overrides individual hooks that do not set stages themselves. [claim:clm_012]
- The post-commit hook takes no parameters, runs after a commit is made, is meant primarily for notification, and cannot affect the outcome of git commit. [claim:clm_013]
- The post-merge hook is invoked by git-merge (e.g. on git pull), takes a single status-flag parameter (squash or not), cannot affect the merge outcome, and is not executed if the merge failed due to conflicts. [claim:clm_014]
- The post-receive hook executes on the remote once after all proposed ref updates are processed and only if at least one ref was updated, receiving one stdin line per successfully updated ref. [claim:clm_015]
- The post-receive hook does not affect the outcome of git receive-pack because it is called after the real work is done. [claim:clm_016]
- The post-checkout hook is given three parameters (previous HEAD ref, new HEAD ref, and a branch-vs-file checkout flag of 1 or 0) and is run by git checkout/git switch after updating the worktree. [claim:clm_017]
- Uniquely among the post-* hooks, the post-checkout hook's exit status becomes the exit status of git switch / git checkout, so it can affect the command outcome. [claim:clm_018]
- The post-checkout hook also runs after git clone (unless --no-checkout/-n) with the first param being the null-ref, the second the new HEAD ref, and the flag always 1; likewise for git worktree add. [claim:clm_019]
- Lefthook is a Git hooks manager that targets Node.js, Ruby, Python, and many other types of projects. [claim:clm_020]
- Lefthook is distributed as a single dependency-free binary written in Go that can run in any environment. [claim:clm_021]
- Lefthook supports parallel execution of hook commands to increase speed. [claim:clm_022]
- Lefthook can filter the list of files a hook command runs against using glob and regexp filters. [claim:clm_023]
- The latest lefthook release is v2.1.9, dated May 29, 2026, with 217 prior releases listed. [claim:clm_024]
- The lefthook codebase is approximately 86% Go (Go 86.2%, JavaScript 5.2%, Raku 4.5%, Shell 1.4%, Python 1.4%, Ruby 0.5%). [claim:clm_025]
- Hook command groups can be invoked directly, e.g. running the pre-commit group via the CLI. [claim:clm_026]
- Lefthook can run commands inside a Docker container by specifying a runner that wraps the command. [claim:clm_027]
- The atomic option (default true when useFsEvents and usePolling are both false) coalesces a delete+re-add within 100 ms into a single 'change' event rather than emitting unlink then add. [claim:clm_028]
- awaitWriteFinish polls file size to debounce chunked/large writes; stabilityThreshold defaults to 2000 ms and pollInterval defaults to 100 ms. [claim:clm_029]
- Polling is disabled by default (usePolling default false); when enabled, the file-system polling interval defaults to 100 ms and binaryInterval (for binary files) defaults to 300 ms. [claim:clm_030]
- Running out of file handles produces EMFILE/ENOSPC errors; the inotify watch-limit (ENOSPC) case can be mitigated by raising fs.inotify.max_user_watches via sysctl. [claim:clm_031]
- As of Nov 2025, chokidar v5 is ESM-only and requires Node.js v20+; the prior v4 (Sep 2024) removed glob support and cut the dependency count from 13 to 1. [claim:clm_032]
- The Last-Event-ID HTTP request header reports an EventSource object's last event ID string to the server when the user agent reestablishes the connection. [claim:clm_033]
- An 'id' field whose value contains no NULL sets the last event ID buffer, and on dispatch the event source's last event ID string is set to that value and persists until the server next sets it, enabling resume of missed events. [claim:clm_034]
- The reconnection time is in milliseconds, and the initial reconnection time is an implementation-defined value, probably in the region of a few seconds. [claim:clm_035]
- The event stream format's MIME type is text/event-stream. [claim:clm_036]
- Clients reconnect automatically if the connection is closed, and a server can tell a client to stop reconnecting by responding with HTTP 204 No Content. [claim:clm_037]
- If the 'retry' field value consists only of ASCII digits, it is interpreted as a base-ten integer and set as the event stream's reconnection time. [claim:clm_038]
- watchdog selects a platform-native backend per OS — inotify on Linux, FSEvents/kqueue on macOS, kqueue on BSD, ReadDirectoryChangesW on Windows — with an OS-independent disk-polling fallback. [claim:clm_039]
- Because kqueue uses one file descriptor per watched file, watchdog warns it does not scale to deeply nested directories with many files. [claim:clm_040]
- Because Vim edits via backup files that are swapped in to replace the originals, watchdog's on-modified events do not fire for Vim-edited files. [claim:clm_041]
- For CIFS network mounts, watchdog must be told explicitly to use PollingObserver rather than relying on automatic backend selection. [claim:clm_042]
- watchdog 6.0.0 was released on 2024-11-01 and requires Python 3.9 or newer. [claim:clm_043]
- Watchexec's default debounce window is 50 milliseconds: it waits up to that long after an event before handling it (e.g., running the command), and setting it to 0 is discouraged. [claim:clm_044]
- Rename handling is fundamentally unreliable: it is impossible to portably know which path is old vs new, 'half' and 'unknown' renames can appear, and a rename can split across two debouncing boundaries. [claim:clm_045]
- The --poll flag forces filesystem polling instead of native OS watching, with a default polling interval of 30 seconds when none is specified. [claim:clm_046]
- The --delay-run option makes Watchexec sleep for a specified duration before running the command after an event is detected. [claim:clm_047]
- The graceful stop timeout defaults to 10 seconds; setting it to 0 immediately force-kills the command. [claim:clm_048]
- FSEvents notifies at directory granularity — it tells you that something in a given directory changed, and the app must scan the directory to learn precisely which files changed. [claim:clm_049]
- Normally an FSEvents consumer scans only the exact directory named in the event path; three exceptions (MustScanSubDirs, dropped events, root changed) require deviating from this. [claim:clm_050]
- Near-simultaneous events in a directory and its subdirectory may be coalesced into a single event carrying kFSEventStreamEventFlagMustScanSubDirs, which obligates a recursive rescan of the listed path. [claim:clm_051]
- On a kernel/daemon communication error, kFSEventStreamEventFlagKernelDropped or kFSEventStreamEventFlagUserDropped is set and you must do a full scan of monitored directories because there is no way to determine what changed. [claim:clm_052]
- When an event is dropped, MustScanSubDirs is also set, so checking the dropped-event flags is unnecessary to decide on a full rescan; the dropped flags are purely informational. [claim:clm_053]
- Fanotify directory monitoring is not recursive; monitoring subdirectories requires additional marks per subdirectory. [claim:clm_054]
- Detecting a new subdirectory via FAN_CREATE and then adding a mark is racy: events inside the new subdirectory before the mark is added can be lost. [claim:clm_055]
- Monitoring mounts (FAN_MARK_MOUNT) and filesystems (FAN_MARK_FILESYSTEM) enables whole-directory-tree monitoring in a race-free manner. [claim:clm_056]
- Groups initialized with FAN_REPORT_FID or FAN_REPORT_DIR_FID deliver a fanotify_event_info_fid record using file handles to identify filesystem objects rather than file descriptors. [claim:clm_057]
- Generating events with file descriptors performs no read/write authorization check for the receiving process, posing a security risk for unprivileged users granted CAP_SYS_ADMIN. [claim:clm_058]
- Lefthook's `skip` option can suppress all or specific commands and scripts, including conditionally on merge, rebase, or specific branches, with glob support for branch names. [claim:clm_059]
- Hooks and commands can be skipped while in a git merge or rebase state by listing `merge` and/or `rebase` as skip values. [claim:clm_060]
- Hooks can be skipped on a specific branch or ref using `ref:` (e.g. `ref: main`), and glob patterns such as `ref: dev/*` are supported for branches. [claim:clm_061]
- Conditional skipping runs a shell command and skips the hook when that command exits successfully (return code 0), e.g. `run: test ${SKIP_ME} -eq 1`. [claim:clm_062]
- An existence-guard pattern `skip: - run: "! which <tool>"` lets a command run only when a CLI tool is installed, skipping when the tool is absent. [claim:clm_063]
- Skip can be set at the hook level or per-command/per-script, giving fine-grained suppression of otherwise-automatic triggers. [claim:clm_064]
- inotify coalesces identical successive unread events (same wd, mask, cookie, name) into one, so it cannot be used to reliably count file events. [claim:clm_065]
- Events that exceed the per-instance queue limit are dropped, but an IN_Q_OVERFLOW event is always generated to signal the overflow. [claim:clm_066]
- The overflow notification arrives as an IN_Q_OVERFLOW event whose watch descriptor is set to -1. [claim:clm_067]
- Three per-real-user-ID /proc tunables govern inotify resource limits: max_user_instances (instances), max_user_watches (watches), and max_queued_events (queued events per instance). [claim:clm_068]
- inotify directory monitoring is not recursive; each subdirectory requires its own additional watch. [claim:clm_069]
- Pairing IN_MOVED_FROM with IN_MOVED_TO for renames is inherently racy: the pair is usually but not always consecutive, may be interleaved by other events, is not inserted atomically, and IN_MOVED_TO may be absent if the rename leaves the monitored directory. [claim:clm_070]
- Before Linux 2.6.25, a coalescing bug compared the most recent event against the oldest unread event instead of the two most recent events. [claim:clm_071]

## Sources

- src_20260614_rib024_00 — inotify(7) — Linux manual page
- src_20260614_rib024_01 — fanotify(7) — Linux manual page
- src_20260614_rib024_02 — Using the File System Events API (FSEvents Programming Guide)
- src_20260614_rib024_03 — watchdog — Python API and shell utilities to monitor file system events (GitHub repo)
- src_20260614_rib024_04 — chokidar — Minimal and efficient cross-platform file watching library (README)
- src_20260614_rib024_05 — watchexec(1) — manual page
- src_20260614_rib024_06 — githooks Documentation — Git Reference Manual
- src_20260614_rib024_07 — 9.2 Server-sent events — HTML Living Standard (WHATWG)
- src_20260614_rib024_08 — Using server-sent events — Web APIs | MDN
- src_20260614_rib024_09 — pre-commit — A framework for managing git pre-commit hooks
- src_20260614_rib024_10 — evilmartians/lefthook — A Git hooks manager for Node.js, Ruby, Python and many other types of projects
- src_20260614_rib024_11 — skip — Lefthook Documentation

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
