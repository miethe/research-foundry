---
schema_version: '0.1'
type: research_report
report_id: report_20260614_what_are_the_documented_trade_offs
title: File-first vs DB-first architectures for LLM knowledge bases
intent_id: intent_research_20260614_what_are_the_documented_trade_offs
evidence_bundle_id: pending
created_at: '2026-06-14T15:58:30-04:00'
status: draft
audience: technical
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

# File-first vs DB-first architectures for LLM knowledge bases

## Executive summary

**Inference:** This memo evaluates file-first stores (Markdown + Git), DB-first stores (client/server engines such as PostgreSQL, or version-aware engines such as Dolt), and a hybrid posture for use as LLM-readable knowledge bases such as Research Foundry (RF) and MeatyWiki. [claim:clm_inf10]

**Inference:** File-first wins decisively on human editability and agent-tool compatibility: Obsidian's plain-text local-first vault is editable by any filesystem-aware tool and versionable with stock Git, and an LLM agent can read, grep, and rewrite a Markdown+YAML note with ordinary file operations, whereas a DB-first store requires the agent to speak SQL/stored-procedure semantics (Dolt exposes writes as stored procedures and reads as system tables) and a running engine. [claim:clm_inf08]
**Inference:** Git content-addressing gives file-first knowledge bases a stronger structural reproducibility and tamper-evidence guarantee than a DB migration/audit trail: every blob, tree, and commit is named by the SHA of its own bytes, so any content change necessarily changes its key and any commit edit changes every descendant SHA, making the history self-verifying rather than dependent on append-only log discipline. [claim:clm_inf03]
**Inference:** On concurrent writes, file-first stores and embedded DBs share the same single-writer ceiling while only client/server engines like PostgreSQL scale: SQLite serializes to one writer at any instant, whereas PostgreSQL's MVCC lets reading never block writing and writing never block reading. [claim:clm_inf01]
**Inference:** Recommended posture for RF/MeatyWiki: keep Markdown+YAML under Git as the single source of truth for editability, diffable LLM-authored review, and free rebuild-based recovery, and add a derived, disposable SQLite/Datasette index (git-history pattern) for query performance; accept the single-writer serialization limit and only introduce a PostgreSQL/MVCC write tier if concurrent agent writes exceed the millisecond turn-taking window. [claim:clm_inf09]

## Trade-off matrix

The matrix scores each posture per dimension. "File-first" = Markdown/YAML files under Git; "DB-first" = a client/server engine (PostgreSQL) or table-versioned engine (Dolt); "Hybrid" = files-as-truth with a rebuildable derived index (git-history pattern). Each material verdict carries its citation in the Evidence column.

| Dimension | File-first verdict | DB-first verdict | Hybrid verdict | Evidence |
|-----------|--------------------|------------------|----------------|----------|
| Concurrent writes | Single-writer ceiling: one writer at any instant | Client/server MVCC scales: reads never block writes and vice versa | Inherits file-first write ceiling; index rebuilt offline | [claim:clm_inf01] |
| Concurrency breakpoint | Adequate while writers serialize within the millisecond window (e.g. <100K hits/day) | Required once writers cannot queue and take turns | Same breakpoint as file-first for writes | [claim:clm_inf02] |
| Reproducibility / tamper-evidence | Strongest: Merkle-chained SHA names make history self-verifying | Weaker: audit trail records but does not cryptographically chain history | Same strong guarantee as file-first (Git is the truth) | [claim:clm_inf03] |
| Recovery guarantee | History is the durable source | Database is the sole copy; lost data has no external rebuild source | Strongest: index is a disposable cache, deterministically rebuilt from file history | [claim:clm_inf05] |
| Query / scale degradation | Operational-tooling threshold, not a fixed capacity ceiling | Designed for large datasets and terabyte-range data | Adds query index; index size scales with versions x items | [claim:clm_inf06] |
| Index storage cost | No separate index | N/A (DB is the store) | Index amplification: 10 versions x 30 items = 300 rows | [claim:clm_inf04] |
| Schema evolution | Per-file, locally diffable, human-reviewable frontmatter edits | Coordinated table migration enforces structural integrity | Inherits file-first locality; structured index re-derived | [claim:clm_inf07] |
| Human editability / agent-tool fit | Any filesystem-aware tool and stock Git; LLM agents use ordinary file ops | Requires SQL/stored-procedure semantics and a running engine | File-first edit surface plus derived query surface | [claim:clm_inf08] |

## Analytical derivation

### Storage and integrity model (file-first)

Git is a content-addressable filesystem: a key-value store where inserting any content returns a unique key for later retrieval. [claim:clm_006]
Git is at its core a content-addressable filesystem that uses the SHA-1 hash function to name content such as files, directories, and revisions. [claim:clm_031]
The plumbing command git hash-object stores data in the .git/objects object database and returns the unique key referring to that data; e.g. 'test content' hashes to d670460b4b4aece5915caf5c68d12f560a9fe3e4. [claim:clm_007]
Git computes an object's SHA-1 by constructing a header (object type, a space, the content's byte size, and a null byte), concatenating it with the original content, and hashing the combined data. [claim:clm_008]
Tree objects store directory structure: a single tree contains one or more entries, each being the SHA-1 hash of a blob or subtree along with its mode, type, and filename, with blobs holding file content. [claim:clm_009]
A commit object records the top-level tree SHA for the snapshot, parent commits (if any), author/committer info from user.name/user.email plus a timestamp, and the commit message. [claim:clm_010]
Git stores each object zlib-compressed as a single file under .git/objects/, named by its SHA-1: the first two characters form the subdirectory name and the remaining 38 characters form the filename. [claim:clm_011]
**Inference:** Git content-addressing gives file-first knowledge bases a stronger structural reproducibility and tamper-evidence guarantee than a DB migration/audit trail: every blob, tree, and commit is named by the SHA of its own bytes, so any content change necessarily changes its key and any commit edit changes every descendant SHA, making the history self-verifying rather than dependent on append-only log discipline. [claim:clm_inf03]

### Hash-function integrity horizon

Because a blob object refers to no other object, its SHA-1 content and SHA-256 content are identical. [claim:clm_032]
The 2017 SHAttered attack demonstrated a practical SHA-1 collision; although Git moved to a hardened SHA-1, SHA-1 is still considered weak, motivating the move to SHA-256. [claim:clm_033]
An object's SHA-256 name is the SHA-256 of the concatenation of its type, length, a nul byte, and the object's SHA-256 content, preserving the content-addressable naming model. [claim:clm_034]
The transition is designed to be incremental and interoperable: it can be done one local repository at a time and a SHA-256 repository can still push/fetch with SHA-1 Git servers. [claim:clm_035]

### Editability and agent-tool surface

Obsidian's design philosophy is built on storing knowledge as plain text, positioning the knowledge base as user-owned rather than locked into a proprietary host. [claim:clm_012]
Obsidian treats Sync as an optional convenience for multi-device work; the data is always stored primarily on the user's local hard disk (local-first). [claim:clm_013]
Because the file system replaces the cloud, Obsidian's plain-file model is directly compatible with Git for versioning, plus Dropbox backup and disk encryption. [claim:clm_014]
Notes are connected through bidirectional Internal links and a Graph view rather than a database schema, with linking treated as a first-class feature for discovering relations. [claim:clm_015]
Obsidian is described as both a Markdown editor and a knowledge base app, with its core power in managing a densely networked knowledge base. [claim:clm_016]
Obsidian intentionally ships a minimal foundation (view, edit, search files) plus optional building blocks rather than an opinionated monolithic product. [claim:clm_017]
**Inference:** File-first wins decisively on human editability and agent-tool compatibility: Obsidian's plain-text local-first vault is editable by any filesystem-aware tool and versionable with stock Git, and an LLM agent can read, grep, and rewrite a Markdown+YAML note with ordinary file operations, whereas a DB-first store requires the agent to speak SQL/stored-procedure semantics (Dolt exposes writes as stored procedures and reads as system tables) and a running engine. [claim:clm_inf08]

### DB-first comparators

PostgreSQL maintains data consistency via a multiversion model (MVCC) in which each SQL statement sees a snapshot of data (a database version) as it was at an earlier point, regardless of the current underlying data state. [claim:clm_047]
The per-statement snapshot prevents statements from viewing inconsistent data produced by concurrent updating transactions, providing transaction isolation for each database session. [claim:clm_048]
Under MVCC, locks acquired for reading do not conflict with locks acquired for writing, so reading never blocks writing and writing never blocks reading. [claim:clm_049]
By avoiding traditional locking methodologies, MVCC minimizes lock contention to allow reasonable performance in multiuser environments. [claim:clm_050]
The documentation asserts qualitatively that proper use of MVCC will generally provide better performance than locks, without benchmark figures. [claim:clm_051]
PostgreSQL preserves the MVCC snapshot guarantee even at the strictest isolation level via Serializable Snapshot Isolation (SSI). [claim:clm_052]
Logical replication replicates data objects and their changes based on a replication identity (usually a primary key), in contrast to physical block-level replication. [claim:clm_001]
Logical replication uses a publish/subscribe model in which subscribers pull from publications and may re-publish data to enable cascading replication. [claim:clm_002]
On start it snapshots the publisher table and copies it to the subscriber, then continually sends subsequent changes. [claim:clm_003]
The subscriber applies changes in the same order as the publisher, guaranteeing transactional consistency for publications within a single subscription. [claim:clm_004]
Documented use cases include sending incremental changes as they occur and firing triggers for individual changes as they arrive on the subscriber (the basis for CDC/audit patterns). [claim:clm_005]
Dolt is positioned as 'Git for Data,' a system that version-controls tabular data the way Git version-controls files. [claim:clm_036]
Dolt's versioning unit is the SQL table rather than the file: it versions tables where Git versions files. [claim:clm_037]
Dolt is a MySQL-compatible database that can serve as a drop-in replacement for MySQL while adding version control. [claim:clm_038]
In Dolt, write operations (checkout, commit) are exposed as SQL stored procedures while read operations (diff, log) are exposed as system tables. [claim:clm_039]
Dolt positions itself as a hybrid combining the version-control semantics of Git with the relational query capabilities of MySQL. [claim:clm_040]
Dolt's command-line interface mirrors Git's CLI directly, with the versioning target being tables instead of files. [claim:clm_041]

### Hybrid index pattern

git-history is a tool whose stated purpose is analyzing a file's Git commit history by loading it into SQLite. [claim:clm_018]
The git-history `file` command converts a versioned file's history into a SQLite database, e.g. building incidents.db from incidents.json. [claim:clm_019]
Using the --id option de-duplicates objects by a unique identifier and reconstructs the change history of each item across commits. [claim:clm_020]
Running with --id produces six tables, including item_version, capturing item-level change history rather than just raw commits. [claim:clm_021]
The tool materializes every captured version of every record, so ten historic versions of a 30-incident file yield 300 item rows. [claim:clm_022]
git-history is distributed as a PyPI package and installable via uv as a tool, with Git as the durable history source and SQLite as the derived query index. [claim:clm_023]
Generated SQLite databases are intended to be queried and published via Datasette, demonstrated by deployed demo datasets (e.g. PG&E outages, California fire incidents). [claim:clm_024]
**Inference:** The git-history tool is the canonical instance of the recommended hybrid posture for RF/MeatyWiki — Git/Markdown as durable, diffable truth with a rebuildable SQLite index for querying — and its operational cost is index amplification: it materializes every version of every record (10 versions x 30 items = 300 rows), so the derived store grows with history depth times item count, not with current state. [claim:clm_inf04]
**Inference:** The derived index in a files-as-truth + rebuildable-DB hybrid is a disposable cache, which yields the strongest recovery guarantee of the three postures: because git-history regenerates the entire SQLite database deterministically from the committed file history, index loss or corruption is recoverable by re-running the build, whereas a DB-first store's lost data has no external source to rebuild from. [claim:clm_inf05]

### Schema evolution

**Inference:** For schema evolution, file-first YAML frontmatter and DB-first models trade off the same way as concurrent writes: editing a Markdown file's frontmatter is a local, individually diffable, human-reviewable change versioned per-file by Git, whereas a relational/table-versioned migration (as in Dolt, where commits are stored procedures and diffs are system tables) centralizes and validates the change but couples all rows to one coordinated migration — favoring file-first for incremental, agent-authored field additions and DB-first for enforced structural integrity. [claim:clm_inf07]

## Scale and concurrency breakpoints

SQLite's core concurrency model allows unlimited simultaneous readers but only a single writer at any instant, which is the file-first concurrent-write breakpoint. [claim:clm_025]
Because a write transaction typically takes only milliseconds, multiple writers can take turns, making single-writer SQLite acceptable for low-to-medium write concurrency. [claim:clm_027]
When many threads/processes must write concurrently and cannot queue and take turns, the docs direct readers to a client/server database engine. [claim:clm_026]
SQLite is documented as suitable for websites with fewer than 100K hits/day. [claim:clm_028]
sqlite.org itself serves roughly 400K-500K HTTP requests/day, of which about 15-20% are dynamic pages touching the database, illustrating real-world headroom for the single-writer model. [claim:clm_029]
SQLite's maximum database size is 281 terabytes (2^48 bytes), and the docs recommend a centralized client/server database when data may reach the terabyte range. [claim:clm_030]
Before optimization, Git's sparse-checkout pattern matching used a quadratic-time algorithm that took 40 minutes to evaluate the patterns on one large repository. [claim:clm_042]
After implementing cone-mode sparse-checkout, git status performance dropped to three or four seconds, comparable to the typical VFS for Git case. [claim:clm_043]
Scaling Git to large repositories relies on a bundle of performance features (partial clone, sparse-checkout, background maintenance, and advanced config) that scalar clone configures together, implying plain git clone does not enable them by default. [claim:clm_044]
VFS for Git's macOS port was abandoned because Apple deprecated the kernel filesystem-virtualization features that the virtualization approach depended on. [claim:clm_045]
After moving off filesystem virtualization onto core Git features, the team realized Scalar had become only a command-line interface on top of Git rather than a virtualization layer. [claim:clm_046]
**Inference:** On concurrent writes, file-first stores and embedded DBs share the same single-writer ceiling while only client/server engines like PostgreSQL scale: SQLite serializes to one writer at any instant, whereas PostgreSQL's MVCC lets reading never block writing and writing never block reading. [claim:clm_inf01]
**Inference:** The documented concurrency breakpoint for a file-first / embedded-DB store is reached when writers can no longer queue and take turns within the millisecond-scale write window; below that (e.g. the <100K hits/day or the observed 400K-500K req/day with 15-20% DB-touching dynamic pages on sqlite.org) single-writer file-first is adequate, above it the docs prescribe migrating writes to a client/server engine. [claim:clm_inf02]
**Inference:** File-first query/scale performance does not degrade at a fixed data-size limit but at an operational-tooling threshold: SQLite tolerates up to 281 TB yet the docs still steer terabyte-range workloads to client/server, and Git's own scaling required a bundle (partial clone, sparse-checkout, background maintenance) where a naive quadratic sparse-checkout matcher cost 40 minutes before cone mode cut git status to 3-4 seconds — so the breakpoint is when default tooling stops being viable, not when a capacity ceiling is hit. [claim:clm_inf06]

## Recommendations and decision rules

**Inference:** Recommended posture for RF/MeatyWiki: keep Markdown+YAML under Git as the single source of truth for editability, diffable LLM-authored review, and free rebuild-based recovery, and add a derived, disposable SQLite/Datasette index (git-history pattern) for query performance; accept the single-writer serialization limit and only introduce a PostgreSQL/MVCC write tier if concurrent agent writes exceed the millisecond turn-taking window. [claim:clm_inf09]
**Inference:** The derived index in a files-as-truth + rebuildable-DB hybrid is a disposable cache, which yields the strongest recovery guarantee of the three postures: because git-history regenerates the entire SQLite database deterministically from the committed file history, index loss or corruption is recoverable by re-running the build, whereas a DB-first store's lost data has no external source to rebuild from. [claim:clm_inf05]
**Inference:** The documented concurrency breakpoint for a file-first / embedded-DB store is reached when writers can no longer queue and take turns within the millisecond-scale write window; below that (e.g. the <100K hits/day or the observed 400K-500K req/day with 15-20% DB-touching dynamic pages on sqlite.org) single-writer file-first is adequate, above it the docs prescribe migrating writes to a client/server engine. [claim:clm_inf02]
**Inference:** The git-history tool is the canonical instance of the recommended hybrid posture for RF/MeatyWiki — Git/Markdown as durable, diffable truth with a rebuildable SQLite index for querying — and its operational cost is index amplification: it materializes every version of every record (10 versions x 30 items = 300 rows), so the derived store grows with history depth times item count, not with current state. [claim:clm_inf04]
**Speculation:** Multi-agent RF/MeatyWiki swarms will likely be the first workload to breach the file-first single-writer breakpoint, because parallel carder/synthesizer agents committing to the same Git index cannot 'queue and take turns' within milliseconds the way one writer can, plausibly forcing either per-agent branch+merge isolation or a PostgreSQL-backed write coordinator before the corpus itself grows large. [claim:clm_spec01]
**Speculation:** Git's SHA-256 transition will become a prerequisite for file-first knowledge bases used as long-horizon evidence ledgers, because the SHAttered-demonstrated SHA-1 weakness undermines the tamper-evidence that gives Git-as-truth its reproducibility advantage; the incremental, server-interoperable migration path makes adoption low-risk enough that compliance-sensitive RF deployments will plausibly move first. [claim:clm_spec02]

## Open questions

- At what concrete write-concurrency level (commits/second across parallel agents) does the file-first single-writer ceiling actually bind for RF/MeatyWiki swarms?
- Does per-agent branch+merge isolation suffice as a mitigation, or is a PostgreSQL-backed write coordinator required before the corpus grows large?
- What is the rebuild-time cost of the derived SQLite/Datasette index as history depth times item count grows, and where does that re-derivation become operationally painful?
- For which compliance-sensitive RF deployments, if any, is the Git SHA-256 transition a hard prerequisite rather than an optional hardening step?

## Sources

- src_20260614_rib037_04: PostgreSQL 18 Documentation — Chapter 29: Logical Replication
- src_20260614_rib037_00: Git - Git Internals: Git Objects (Pro Git book, 2nd ed.)
- src_20260614_rib037_05: About Obsidian — Obsidian Help (local-first plain-text Markdown vault)
- src_20260614_rib037_02: simonw/git-history — Tools for analyzing Git history using SQLite
- src_20260614_rib037_06: Appropriate Uses For SQLite
- src_20260614_rib037_01: Git - hash-function-transition Documentation (SHA-1 to SHA-256)
- src_20260614_rib037_03: Git for Data | Dolt Docs
- src_20260614_rib037_08: The Story of Scalar
- src_20260614_rib037_07: PostgreSQL Documentation: Introduction to Multiversion Concurrency Control (MVCC)
