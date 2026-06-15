---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_patterns_file_watch_hooks_post
title: Broker-less Event Patterns to Close Local-First Agentic OS Seams
intent_id: intent_research_20260614_what_patterns_file_watch_hooks_post
evidence_bundle_id: pending
created_at: '2026-06-14T15:04:58-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# Broker-less Event Patterns to Close Local-First Agentic OS Seams

## Executive summary

**Inference:** The recommended pattern-vs-seam mapping for RF is: research->vault = git post-commit/post-merge trigger; vault->graph = file-watch (watchdog/chokidar) plus reconciliation rescan; telemetry->governance = SSE fan-out with Last-Event-ID resume; with lightweight event sourcing (an append-only event log file) as the cross-cutting reconciliation substrate for all three. [claim:clm_inf07]
**Inference:** No candidate pattern in the evidence base provides exactly-once delivery: file-watch coalesces and drops events, git post-* hooks can re-fire (e.g. amended commits, re-merges) and are skipped on failure, and SSE explicitly guarantees only at-least-once via id-resume; therefore every RF seam MUST make its consumer idempotent rather than rely on transport-level exactly-once. [claim:clm_inf05]
**Inference:** Across the three RF seams, git triggers and event sourcing are complementary rather than competing: git supplies the exactly-once-per-commit edge signal while the append-only log supplies durable replay; combining them (post-commit appends an event record, consumers replay from a cursor) yields the at-least-once-with-idempotency guarantee that no single broker-less primitive achieves alone. [claim:clm_inf15]
**Inference:** A minimal message broker becomes justified for RF only when the seams cross a network or host boundary or exceed local kernel watch/queue limits; the concrete threshold criterion is when (a) producers and consumers no longer share a filesystem, or (b) event volume causes recurrent IN_Q_OVERFLOW/dropped-event rescans, at which point git post-receive on a shared remote is the lowest-cost escalation before a true broker. [claim:clm_inf14]

## Pattern-vs-seam matrix

| Seam | Pattern fit | Rationale | Evidence |
|------|-------------|-----------|----------|
| research->vault | Git post-commit / post-merge trigger | Fires once per atomic VCS operation; no coalescing or queue-overflow loss | **Inference:** Git post-* triggers (post-commit, post-merge) are the best fit for RF's research->vault seam because they fire exactly once per atomic commit/merge with no event coalescing or queue-overflow loss, unlike file-watch primitives which coalesce identical events and silently drop on queue overflow. [claim:clm_inf01] |
| vault->graph | File-watch (watchdog/chokidar) + reconciliation rescan | Most responsive locally, but native backends signal lossy overflow that forces full rescan | **Inference:** For RF's vault->graph seam, a file-watch hook (watchdog on Linux/macOS, chokidar on Node) is the most responsive pattern, but it MUST be paired with a directory-rescan reconciliation pass because every native backend (inotify, FSEvents) signals lossy overflow conditions (IN_Q_OVERFLOW, MustScanSubDirs/Dropped) that force a full rescan rather than per-file delivery. [claim:clm_inf02] |
| telemetry->governance | SSE fan-out with Last-Event-ID resume | One-way broadcast suits read-only observers; only candidate with standardized offline-gap recovery | **Inference:** SSE is unsuitable as the primary trigger for any RF write-path seam (research->vault, vault->graph) because it is a one-way server-to-client channel that cannot carry a tool-to-tool handoff push; SSE's correct role in RF is the telemetry->governance fan-out, broadcasting governance events to dashboards/observers. [claim:clm_inf03] |
| All three (cross-cutting) | Lightweight event sourcing (append-only log) | Highest-durability broker-less substrate; survives restarts; deterministic replay from cursor | **Inference:** Lightweight event sourcing implemented as an append-only newline-delimited log on the local filesystem is the highest-durability broker-less pattern because, unlike file-watch (bounded kernel queues that drop) and unlike in-memory SSE streams, an on-disk log survives tool restarts and offline periods and supports deterministic replay from a stored cursor. [claim:clm_inf08] |

### Pattern capability comparison

| Pattern | Delivery direction | Loss/overflow behavior | Resume / replay mechanism | Evidence |
|---------|--------------------|------------------------|---------------------------|----------|
| SSE (server-sent events) | One-way server-to-client | Client reconnects; server can stop it with HTTP 204 | Last-Event-ID header on reconnect | SSE is a one-way (server-to-client) channel, so a client cannot push events to the server over the same connection. [claim:clm_001] |
| Git post-* hooks | Fire-and-forget notification per VCS op | post-merge skipped on conflict; cannot affect outcome | post-receive runs once per updated ref | The post-commit hook takes no parameters, runs after a commit is made, is meant primarily for notification, and cannot affect the outcome of git commit. [claim:clm_013] |
| File-watch (inotify) | Per-directory, non-recursive | Drops on queue overflow with IN_Q_OVERFLOW signal | Coalesces identical unread events; no native replay | Events that exceed the per-instance queue limit are dropped, but an IN_Q_OVERFLOW event is always generated to signal the overflow. [claim:clm_066] |
| File-watch (FSEvents) | Directory-granularity notification | Kernel/user drop forces full monitored-tree scan | MustScanSubDirs flag obligates recursive rescan | FSEvents notifies at directory granularity — it tells you that something in a given directory changed, and the app must scan the directory to learn precisely which files changed. [claim:clm_049] |
| Event sourcing (append-only log) | Local on-disk record | Survives restart/offline; no kernel queue to overflow | Deterministic replay from a stored cursor | Lightweight event sourcing implemented as an append-only newline-delimited log on the local filesystem is the highest-durability broker-less pattern because, unlike file-watch (bounded kernel queues that drop) and unlike in-memory SSE streams, an on-disk log survives tool restarts and offline periods and supports deterministic replay from a stored cursor. **Inference:** [claim:clm_inf08] |

## Derivation: why each pattern maps where it does

### research->vault: commit boundaries over file events

**Inference:** Git post-* triggers (post-commit, post-merge) are the best fit for RF's research->vault seam because they fire exactly once per atomic commit/merge with no event coalescing or queue-overflow loss, unlike file-watch primitives which coalesce identical events and silently drop on queue overflow. [claim:clm_inf01]
**Inference:** File-watch is fundamentally unreliable for tracking renames/moves in any RF seam: inotify's IN_MOVED_FROM/IN_MOVED_TO pairing is racy and may be incomplete, watchexec cannot portably distinguish old-vs-new paths, and these races make rename a leading cause of missed or duplicated handoffs; git triggers avoid this because a rename is just content in the next commit's tree. [claim:clm_inf06]
Pairing IN_MOVED_FROM with IN_MOVED_TO for renames is inherently racy: the pair is usually but not always consecutive, may be interleaved by other events, is not inserted atomically, and IN_MOVED_TO may be absent if the rename leaves the monitored directory. [claim:clm_070]
Rename handling is fundamentally unreliable: it is impossible to portably know which path is old vs new, 'half' and 'unknown' renames can appear, and a rename can split across two debouncing boundaries. [claim:clm_045]
The post-checkout hook is given three parameters (previous HEAD ref, new HEAD ref, and a branch-vs-file checkout flag of 1 or 0) and is run by git checkout/git switch after updating the worktree. [claim:clm_017]
**Inference:** pre-commit and lefthook are both viable hook managers for RF's git-trigger seams, but lefthook is preferable for a local-first agentic OS because it ships as a single dependency-free Go binary (no Python runtime needed for the manager itself) and supports parallel command execution, whereas pre-commit's file-less hooks require always_run:true or they are silently skipped. [claim:clm_inf16]
Hooks that do not operate on files (post-checkout, post-commit, post-merge, post-rewrite, pre-rebase) must be set as always_run: true or they will always be skipped. [claim:clm_008]
Lefthook is distributed as a single dependency-free binary written in Go that can run in any environment. [claim:clm_021]
Lefthook supports parallel execution of hook commands to increase speed. [claim:clm_022]
pre-commit supports ten git hook stages: commit-msg, post-checkout, post-commit, post-merge, post-rewrite, pre-commit, pre-merge-commit, pre-push, pre-rebase, and prepare-commit-msg. [claim:clm_007]
default_install_hook_types is a list of --hook-types used by default when running pre-commit install, and it defaults to [pre-commit], so only the pre-commit hook is installed unless other types are specified. [claim:clm_011]
Lefthook's `skip` option can suppress all or specific commands and scripts, including conditionally on merge, rebase, or specific branches, with glob support for branch names. [claim:clm_059]
Hooks and commands can be skipped while in a git merge or rebase state by listing `merge` and/or `rebase` as skip values. [claim:clm_060]

### vault->graph: responsive watch, authoritative rescan

**Inference:** For RF's vault->graph seam, a file-watch hook (watchdog on Linux/macOS, chokidar on Node) is the most responsive pattern, but it MUST be paired with a directory-rescan reconciliation pass because every native backend (inotify, FSEvents) signals lossy overflow conditions (IN_Q_OVERFLOW, MustScanSubDirs/Dropped) that force a full rescan rather than per-file delivery. [claim:clm_inf02]
**Inference:** RF should select watchdog (Python) or chokidar (Node) over raw inotify/FSEvents and over watchexec for the vault->graph watcher, because both libraries already abstract per-OS backend selection and provide write-coalescing debounce (chokidar atomic 100ms / awaitWriteFinish 2000ms) that prevents partial-file ingestion into the graph. [claim:clm_inf10]
watchdog selects a platform-native backend per OS — inotify on Linux, FSEvents/kqueue on macOS, kqueue on BSD, ReadDirectoryChangesW on Windows — with an OS-independent disk-polling fallback. [claim:clm_039]
The atomic option (default true when useFsEvents and usePolling are both false) coalesces a delete+re-add within 100 ms into a single 'change' event rather than emitting unlink then add. [claim:clm_028]
awaitWriteFinish polls file size to debounce chunked/large writes; stabilityThreshold defaults to 2000 ms and pollInterval defaults to 100 ms. [claim:clm_029]
When an event is dropped, MustScanSubDirs is also set, so checking the dropped-event flags is unnecessary to decide on a full rescan; the dropped flags are purely informational. [claim:clm_053]
Normally an FSEvents consumer scans only the exact directory named in the event path; three exceptions (MustScanSubDirs, dropped events, root changed) require deviating from this. [claim:clm_050]

### telemetry->governance: one-way fan-out with built-in resume

**Inference:** SSE is unsuitable as the primary trigger for any RF write-path seam (research->vault, vault->graph) because it is a one-way server-to-client channel that cannot carry a tool-to-tool handoff push; SSE's correct role in RF is the telemetry->governance fan-out, broadcasting governance events to dashboards/observers. [claim:clm_inf03]
**Inference:** SSE's last-event-ID resume protocol (Last-Event-ID header plus persistent id field) gives the telemetry->governance seam at-least-once delivery across reconnects and tool restarts, making it the only candidate pattern in this evidence set with a built-in, standardized offline-gap recovery mechanism. [claim:clm_inf04]
The Last-Event-ID HTTP request header reports an EventSource object's last event ID string to the server when the user agent reestablishes the connection. [claim:clm_033]
An 'id' field whose value contains no NULL sets the last event ID buffer, and on dispatch the event source's last event ID string is set to that value and persists until the server next sets it, enabling resume of missed events. [claim:clm_034]
Clients reconnect automatically if the connection is closed, and a server can tell a client to stop reconnecting by responding with HTTP 204 No Content. [claim:clm_037]
The server-side script emitting SSE events must respond with the MIME type text/event-stream. [claim:clm_003]
Without HTTP/2, SSE is limited to a very low number of open connections (6) per browser per domain; over HTTP/2 the simultaneous HTTP-stream limit is negotiated (defaulting to 100). [claim:clm_005]

### Cross-cutting reconciliation substrate

**Inference:** Lightweight event sourcing implemented as an append-only newline-delimited log on the local filesystem is the highest-durability broker-less pattern because, unlike file-watch (bounded kernel queues that drop) and unlike in-memory SSE streams, an on-disk log survives tool restarts and offline periods and supports deterministic replay from a stored cursor. [claim:clm_inf08]
**Inference:** Across the three RF seams, git triggers and event sourcing are complementary rather than competing: git supplies the exactly-once-per-commit edge signal while the append-only log supplies durable replay; combining them (post-commit appends an event record, consumers replay from a cursor) yields the at-least-once-with-idempotency guarantee that no single broker-less primitive achieves alone. [claim:clm_inf15]

## Failure-mode catalog and broker-less mitigations

### Missed events

| Source of loss | Mechanism and mitigation | Evidence |
|----------------|--------------------------|----------|
| inotify queue overflow | The overflow notification arrives as an IN_Q_OVERFLOW event whose watch descriptor is set to -1. [claim:clm_067] |
| FSEvents kernel/daemon drop | On a kernel/daemon communication error, kFSEventStreamEventFlagKernelDropped or kFSEventStreamEventFlagUserDropped is set and you must do a full scan of monitored directories because there is no way to determine what changed. [claim:clm_052] |
| Conflicted git merge | Because git post-merge does not fire on conflicted merges and is skipped, RF's research->vault seam can silently miss a handoff whenever a merge aborts on conflict; the compensating mechanism is a startup/periodic reconciliation pass that diffs the committed tree against the vault's last-processed commit SHA. **Inference:** [claim:clm_inf09] |
| Editor write patterns | Because Vim edits via backup files that are swapped in to replace the originals, watchdog's on-modified events do not fire for Vim-edited files. [claim:clm_041] |
| inotify watch-limit exhaustion | Running out of file handles produces EMFILE/ENOSPC errors; the inotify watch-limit (ENOSPC) case can be mitigated by raising fs.inotify.max_user_watches via sysctl. [claim:clm_031] |

### Duplicate events

| Source of duplication | Mechanism and mitigation | Evidence |
|-----------------------|--------------------------|----------|
| Atomic-write editors and amend/rebase | The duplicate-trigger failure mode is most acute for file-watch (atomic-write editors emit delete+add or modify sequences) and for git hooks on commit amend/rebase; the uniform broker-less mitigation is content-addressed deduplication keying handoffs on a file hash or commit SHA so reprocessing the same content is a no-op. **Inference:** [claim:clm_inf11] |
| Partial / chunked writes | awaitWriteFinish polls file size to debounce chunked/large writes; stabilityThreshold defaults to 2000 ms and pollInterval defaults to 100 ms. [claim:clm_029] |
| Re-run debounce timing | The --delay-run option makes Watchexec sleep for a specified duration before running the command after an event is detected. [claim:clm_047] |
| No transport exactly-once | No candidate pattern in the evidence base provides exactly-once delivery: file-watch coalesces and drops events, git post-* hooks can re-fire (e.g. amended commits, re-merges) and are skipped on failure, and SSE explicitly guarantees only at-least-once via id-resume; therefore every RF seam MUST make its consumer idempotent rather than rely on transport-level exactly-once. **Inference:** [claim:clm_inf05] |

### Out-of-order events

| Source of disorder | Mechanism and mitigation | Evidence |
|--------------------|--------------------------|----------|
| FSEvents coalescing | Near-simultaneous events in a directory and its subdirectory may be coalesced into a single event carrying kFSEventStreamEventFlagMustScanSubDirs, which obligates a recursive rescan of the listed path. [claim:clm_051] |
| inotify non-atomic rename pairs | Pairing IN_MOVED_FROM with IN_MOVED_TO for renames is inherently racy: the pair is usually but not always consecutive, may be interleaved by other events, is not inserted atomically, and IN_MOVED_TO may be absent if the rename leaves the monitored directory. [claim:clm_070] |
| inotify event coalescing | inotify coalesces identical successive unread events (same wd, mask, cookie, name) into one, so it cannot be used to reliably count file events. [claim:clm_065] |
| Required monotonic ordering source | Ordering races are inherent to broker-less file-watch (FSEvents coalesces directory+subdirectory events and inotify does not atomically order rename pairs), so any RF seam requiring causal order (e.g. vault note created before its graph edge) MUST derive order from a monotonic source such as git commit topology or an append-only log sequence number rather than from filesystem event arrival order. **Inference:** [claim:clm_inf12] |

## Recommendations and decision rules

**Inference:** Git post-* triggers (post-commit, post-merge) are the best fit for RF's research->vault seam because they fire exactly once per atomic commit/merge with no event coalescing or queue-overflow loss, unlike file-watch primitives which coalesce identical events and silently drop on queue overflow. [claim:clm_inf01]
**Inference:** pre-commit and lefthook are both viable hook managers for RF's git-trigger seams, but lefthook is preferable for a local-first agentic OS because it ships as a single dependency-free Go binary (no Python runtime needed for the manager itself) and supports parallel command execution, whereas pre-commit's file-less hooks require always_run:true or they are silently skipped. [claim:clm_inf16]
**Inference:** For RF's vault->graph seam, a file-watch hook (watchdog on Linux/macOS, chokidar on Node) is the most responsive pattern, but it MUST be paired with a directory-rescan reconciliation pass because every native backend (inotify, FSEvents) signals lossy overflow conditions (IN_Q_OVERFLOW, MustScanSubDirs/Dropped) that force a full rescan rather than per-file delivery. [claim:clm_inf02]
**Inference:** RF should select watchdog (Python) or chokidar (Node) over raw inotify/FSEvents and over watchexec for the vault->graph watcher, because both libraries already abstract per-OS backend selection and provide write-coalescing debounce (chokidar atomic 100ms / awaitWriteFinish 2000ms) that prevents partial-file ingestion into the graph. [claim:clm_inf10]
**Inference:** SSE is unsuitable as the primary trigger for any RF write-path seam (research->vault, vault->graph) because it is a one-way server-to-client channel that cannot carry a tool-to-tool handoff push; SSE's correct role in RF is the telemetry->governance fan-out, broadcasting governance events to dashboards/observers. [claim:clm_inf03]
**Inference:** SSE's last-event-ID resume protocol (Last-Event-ID header plus persistent id field) gives the telemetry->governance seam at-least-once delivery across reconnects and tool restarts, making it the only candidate pattern in this evidence set with a built-in, standardized offline-gap recovery mechanism. [claim:clm_inf04]
**Inference:** No candidate pattern in the evidence base provides exactly-once delivery: file-watch coalesces and drops events, git post-* hooks can re-fire (e.g. amended commits, re-merges) and are skipped on failure, and SSE explicitly guarantees only at-least-once via id-resume; therefore every RF seam MUST make its consumer idempotent rather than rely on transport-level exactly-once. [claim:clm_inf05]
**Inference:** The duplicate-trigger failure mode is most acute for file-watch (atomic-write editors emit delete+add or modify sequences) and for git hooks on commit amend/rebase; the uniform broker-less mitigation is content-addressed deduplication keying handoffs on a file hash or commit SHA so reprocessing the same content is a no-op. [claim:clm_inf11]
**Inference:** Ordering races are inherent to broker-less file-watch (FSEvents coalesces directory+subdirectory events and inotify does not atomically order rename pairs), so any RF seam requiring causal order (e.g. vault note created before its graph edge) MUST derive order from a monotonic source such as git commit topology or an append-only log sequence number rather than from filesystem event arrival order. [claim:clm_inf12]
**Inference:** Lightweight event sourcing implemented as an append-only newline-delimited log on the local filesystem is the highest-durability broker-less pattern because, unlike file-watch (bounded kernel queues that drop) and unlike in-memory SSE streams, an on-disk log survives tool restarts and offline periods and supports deterministic replay from a stored cursor. [claim:clm_inf08]
**Inference:** Across the three RF seams, git triggers and event sourcing are complementary rather than competing: git supplies the exactly-once-per-commit edge signal while the append-only log supplies durable replay; combining them (post-commit appends an event record, consumers replay from a cursor) yields the at-least-once-with-idempotency guarantee that no single broker-less primitive achieves alone. [claim:clm_inf15]

### Threshold and escalation criterion: when a minimal broker is justified

**Inference:** Per-user kernel watch limits set a concrete scaling ceiling for the file-watch approach: because inotify monitoring is non-recursive (one watch per directory) and bounded by max_user_watches, and kqueue consumes one file descriptor per file, a vault that grows past tens of thousands of files will exhaust watch descriptors and force a switch to whole-tree (fanotify mount/filesystem marks) or polling. [claim:clm_inf13]
Three per-real-user-ID /proc tunables govern inotify resource limits: max_user_instances (instances), max_user_watches (watches), and max_queued_events (queued events per instance). [claim:clm_068]
inotify directory monitoring is not recursive; each subdirectory requires its own additional watch. [claim:clm_069]
Because kqueue uses one file descriptor per watched file, watchdog warns it does not scale to deeply nested directories with many files. [claim:clm_040]
**Inference:** A minimal message broker becomes justified for RF only when the seams cross a network or host boundary or exceed local kernel watch/queue limits; the concrete threshold criterion is when (a) producers and consumers no longer share a filesystem, or (b) event volume causes recurrent IN_Q_OVERFLOW/dropped-event rescans, at which point git post-receive on a shared remote is the lowest-cost escalation before a true broker. [claim:clm_inf14]
The post-receive hook executes on the remote once after all proposed ref updates are processed and only if at least one ref was updated, receiving one stdin line per successfully updated ref. [claim:clm_015]
The post-receive hook does not affect the outcome of git receive-pack because it is called after the real work is done. [claim:clm_016]
**Inference:** The fanotify file-descriptor security caveat (events deliver fds with no per-receiver authorization check under CAP_SYS_ADMIN) means RF should NOT escalate to fanotify mount/filesystem-wide marks for scaling unless the watcher runs unprivileged via FAN_REPORT_FID handle-based reporting, keeping the telemetry->governance trust boundary intact. [claim:clm_inf17]
Monitoring mounts (FAN_MARK_MOUNT) and filesystems (FAN_MARK_FILESYSTEM) enables whole-directory-tree monitoring in a race-free manner. [claim:clm_056]
Generating events with file descriptors performs no read/write authorization check for the receiving process, posing a security risk for unprivileged users granted CAP_SYS_ADMIN. [claim:clm_058]
Groups initialized with FAN_REPORT_FID or FAN_REPORT_DIR_FID deliver a fanotify_event_info_fid record using file handles to identify filesystem objects rather than file descriptors. [claim:clm_057]

### Forward-looking design constraints

**Speculation:** If RF's vault grows to multi-host or sync-folder (CIFS/network mount) deployment, file-watch will degrade to forced polling (watchdog requires explicit PollingObserver on CIFS; watchexec --poll defaults to a 30s interval), so RF should pre-emptively design the vault->graph seam to tolerate ~30s detection latency rather than assume sub-second native-watch responsiveness. [claim:clm_spec01]
**Speculation:** As local agentic OSes adopt more frequent automated writes, the dominant broker-less failure will shift from missed events to duplicate/partial-write events, making write-stability debouncing (chokidar awaitWriteFinish ~2000ms, watchexec delay-run) and content-hash idempotency more load-bearing than event-delivery guarantees themselves. [claim:clm_spec02]
The --poll flag forces filesystem polling instead of native OS watching, with a default polling interval of 30 seconds when none is specified. [claim:clm_046]
For CIFS network mounts, watchdog must be told explicitly to use PollingObserver rather than relying on automatic backend selection. [claim:clm_042]
Watchexec's default debounce window is 50 milliseconds: it waits up to that long after an event before handling it (e.g., running the command), and setting it to 0 is discouraged. [claim:clm_044]
The graceful stop timeout defaults to 10 seconds; setting it to 0 immediately force-kills the command. [claim:clm_048]

## Open questions

- What is the measured per-event latency of a watchdog/chokidar watcher on RF's actual vault size, and does it stay sub-second below the kernel watch ceiling?
- At what concrete file count does RF's vault cross from inotify-watchable into fanotify-or-polling territory on the target hosts?
- Does any planned RF deployment place producers and consumers on different hosts, triggering the broker escalation criterion immediately?
- Should the append-only event log be per-seam or a single shared log with a typed event schema?

## Sources

- src_20260614_rib024_00: inotify(7) — Linux manual page
- src_20260614_rib024_01: fanotify(7) — Linux manual page
- src_20260614_rib024_02: Using the File System Events API (FSEvents Programming Guide)
- src_20260614_rib024_03: watchdog — Python API and shell utilities to monitor file system events (GitHub repo)
- src_20260614_rib024_04: chokidar — Minimal and efficient cross-platform file watching library (README)
- src_20260614_rib024_05: watchexec(1) — manual page
- src_20260614_rib024_06: githooks Documentation — Git Reference Manual
- src_20260614_rib024_07: 9.2 Server-sent events — HTML Living Standard (WHATWG)
- src_20260614_rib024_08: Using server-sent events — Web APIs | MDN
- src_20260614_rib024_09: pre-commit — A framework for managing git pre-commit hooks
- src_20260614_rib024_10: evilmartians/lefthook — A Git hooks manager for Node.js, Ruby, Python and many other types of projects
- src_20260614_rib024_11: skip — Lefthook Documentation
