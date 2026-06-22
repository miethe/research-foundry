---
id: mwb_20260622_dr_file_first_vs_db_first
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_are_the
target_page: meatywiki/decisions/file_first_vs_db_first_architectures.md
writeback_type: decision_record
status: written
summary: 'Decision record from run rf_run_20260614_what_are_the_documented_trade_offs: Synthesizes the
  file-first editability/Git-versioning benefit (clm_014, clm_006), the proven hybrid index pattern (clm_0'
key_claims:
- claim_id: clm_inf09
  include: true
- claim_id: clm_inf01
  include: true
- claim_id: clm_inf02
  include: true
- claim_id: clm_inf03
  include: true
- claim_id: clm_inf04
  include: true
- claim_id: clm_inf05
  include: true
- claim_id: clm_inf06
  include: true
- claim_id: clm_inf07
  include: true
- claim_id: clm_inf08
  include: true
- claim_id: clm_inf10
  include: true
links:
  source_cards: []
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
  from_claims:
  - clm_014
  - clm_023
  - clm_024
  - clm_025
  - clm_027
  - clm_049
  - clm_006
  - clm_026
  - clm_050
  - clm_028
  - clm_029
  - clm_008
  - clm_009
  - clm_010
  - clm_011
  - clm_031
  - clm_018
  - clm_019
  - clm_022
  - clm_020
  - clm_030
  - clm_042
  - clm_043
  - clm_044
  - clm_012
  - clm_037
  - clm_039
  - clm_021
  - clm_013
  - clm_017
  - clm_038
  - clm_047
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# Decision Record: File-first vs DB-first architectures for LLM knowledge bases

## Context

- Logical replication replicates data objects and their changes based on a replication identity (usually a primary key), in contrast to physical block-level replication. [claim:clm_001]
- Logical replication uses a publish/subscribe model in which subscribers pull from publications and may re-publish data to enable cascading replication. [claim:clm_002]
- On start it snapshots the publisher table and copies it to the subscriber, then continually sends subsequent changes. [claim:clm_003]
- The subscriber applies changes in the same order as the publisher, guaranteeing transactional consistency for publications within a single subscription. [claim:clm_004]
- Documented use cases include sending incremental changes as they occur and firing triggers for individual changes as they arrive on the subscriber (the basis for CDC/audit patterns). [claim:clm_005]
- Git is a content-addressable filesystem: a key-value store where inserting any content returns a unique key for later retrieval. [claim:clm_006]
- The plumbing command git hash-object stores data in the .git/objects object database and returns the unique key referring to that data; e.g. 'test content' hashes to d670460b4b4aece5915caf5c68d12f560a9fe3e4. [claim:clm_007]
- Git computes an object's SHA-1 by constructing a header (object type, a space, the content's byte size, and a null byte), concatenating it with the original content, and hashing the combined data. [claim:clm_008]
- Tree objects store directory structure: a single tree contains one or more entries, each being the SHA-1 hash of a blob or subtree along with its mode, type, and filename, with blobs holding file content. [claim:clm_009]
- A commit object records the top-level tree SHA for the snapshot, parent commits (if any), author/committer info from user.name/user.email plus a timestamp, and the commit message. [claim:clm_010]
- Git stores each object zlib-compressed as a single file under .git/objects/, named by its SHA-1: the first two characters form the subdirectory name and the remaining 38 characters form the filename. [claim:clm_011]
- Obsidian's design philosophy is built on storing knowledge as plain text, positioning the knowledge base as user-owned rather than locked into a proprietary host. [claim:clm_012]
- Obsidian treats Sync as an optional convenience for multi-device work; the data is always stored primarily on the user's local hard disk (local-first). [claim:clm_013]
- Because the file system replaces the cloud, Obsidian's plain-file model is directly compatible with Git for versioning, plus Dropbox backup and disk encryption. [claim:clm_014]
- Notes are connected through bidirectional Internal links and a Graph view rather than a database schema, with linking treated as a first-class feature for discovering relations. [claim:clm_015]
- Obsidian is described as both a Markdown editor and a knowledge base app, with its core power in managing a densely networked knowledge base. [claim:clm_016]
- Obsidian intentionally ships a minimal foundation (view, edit, search files) plus optional building blocks rather than an opinionated monolithic product. [claim:clm_017]
- git-history is a tool whose stated purpose is analyzing a file's Git commit history by loading it into SQLite. [claim:clm_018]
- The git-history `file` command converts a versioned file's history into a SQLite database, e.g. building incidents.db from incidents.json. [claim:clm_019]
- Using the --id option de-duplicates objects by a unique identifier and reconstructs the change history of each item across commits. [claim:clm_020]
- Running with --id produces six tables, including item_version, capturing item-level change history rather than just raw commits. [claim:clm_021]
- The tool materializes every captured version of every record, so ten historic versions of a 30-incident file yield 300 item rows. [claim:clm_022]
- git-history is distributed as a PyPI package and installable via uv as a tool, with Git as the durable history source and SQLite as the derived query index. [claim:clm_023]
- Generated SQLite databases are intended to be queried and published via Datasette, demonstrated by deployed demo datasets (e.g. PG&E outages, California fire incidents). [claim:clm_024]
- SQLite's core concurrency model allows unlimited simultaneous readers but only a single writer at any instant, which is the file-first concurrent-write breakpoint. [claim:clm_025]
- When many threads/processes must write concurrently and cannot queue and take turns, the docs direct readers to a client/server database engine. [claim:clm_026]
- Because a write transaction typically takes only milliseconds, multiple writers can take turns, making single-writer SQLite acceptable for low-to-medium write concurrency. [claim:clm_027]
- SQLite is documented as suitable for websites with fewer than 100K hits/day. [claim:clm_028]
- sqlite.org itself serves roughly 400K-500K HTTP requests/day, of which about 15-20% are dynamic pages touching the database, illustrating real-world headroom for the single-writer model. [claim:clm_029]
- SQLite's maximum database size is 281 terabytes (2^48 bytes), and the docs recommend a centralized client/server database when data may reach the terabyte range. [claim:clm_030]
- Git is at its core a content-addressable filesystem that uses the SHA-1 hash function to name content such as files, directories, and revisions. [claim:clm_031]
- Because a blob object refers to no other object, its SHA-1 content and SHA-256 content are identical. [claim:clm_032]
- The 2017 SHAttered attack demonstrated a practical SHA-1 collision; although Git moved to a hardened SHA-1, SHA-1 is still considered weak, motivating the move to SHA-256. [claim:clm_033]
- An object's SHA-256 name is the SHA-256 of the concatenation of its type, length, a nul byte, and the object's SHA-256 content, preserving the content-addressable naming model. [claim:clm_034]
- The transition is designed to be incremental and interoperable: it can be done one local repository at a time and a SHA-256 repository can still push/fetch with SHA-1 Git servers. [claim:clm_035]
- Dolt is positioned as 'Git for Data,' a system that version-controls tabular data the way Git version-controls files. [claim:clm_036]
- Dolt's versioning unit is the SQL table rather than the file: it versions tables where Git versions files. [claim:clm_037]
- Dolt is a MySQL-compatible database that can serve as a drop-in replacement for MySQL while adding version control. [claim:clm_038]
- In Dolt, write operations (checkout, commit) are exposed as SQL stored procedures while read operations (diff, log) are exposed as system tables. [claim:clm_039]
- Dolt positions itself as a hybrid combining the version-control semantics of Git with the relational query capabilities of MySQL. [claim:clm_040]
- Dolt's command-line interface mirrors Git's CLI directly, with the versioning target being tables instead of files. [claim:clm_041]
- Before optimization, Git's sparse-checkout pattern matching used a quadratic-time algorithm that took 40 minutes to evaluate the patterns on one large repository. [claim:clm_042]
- After implementing cone-mode sparse-checkout, git status performance dropped to three or four seconds, comparable to the typical VFS for Git case. [claim:clm_043]
- Scaling Git to large repositories relies on a bundle of performance features (partial clone, sparse-checkout, background maintenance, and advanced config) that scalar clone configures together, implying plain git clone does not enable them by default. [claim:clm_044]
- VFS for Git's macOS port was abandoned because Apple deprecated the kernel filesystem-virtualization features that the virtualization approach depended on. [claim:clm_045]
- After moving off filesystem virtualization onto core Git features, the team realized Scalar had become only a command-line interface on top of Git rather than a virtualization layer. [claim:clm_046]
- PostgreSQL maintains data consistency via a multiversion model (MVCC) in which each SQL statement sees a snapshot of data (a database version) as it was at an earlier point, regardless of the current underlying data state. [claim:clm_047]
- The per-statement snapshot prevents statements from viewing inconsistent data produced by concurrent updating transactions, providing transaction isolation for each database session. [claim:clm_048]
- Under MVCC, locks acquired for reading do not conflict with locks acquired for writing, so reading never blocks writing and writing never blocks reading. [claim:clm_049]
- By avoiding traditional locking methodologies, MVCC minimizes lock contention to allow reasonable performance in multiuser environments. [claim:clm_050]
- The documentation asserts qualitatively that proper use of MVCC will generally provide better performance than locks, without benchmark figures. [claim:clm_051]
- PostgreSQL preserves the MVCC snapshot guarantee even at the strictest isolation level via Serializable Snapshot Isolation (SSI). [claim:clm_052]

## Decision

Recommended posture for RF/MeatyWiki: keep Markdown+YAML under Git as the single source of truth for editability, diffable LLM-authored review, and free rebuild-based recovery, and add a derived, disposable SQLite/Datasette index (git-history pattern) for query performance; accept the single-writer serialization limit and only introduce a PostgreSQL/MVCC write tier if concurrent agent writes exceed the millisecond turn-taking window. [claim:clm_inf09]

## Rationale

- Synthesizes the file-first editability/Git-versioning benefit (clm_014, clm_006), the proven hybrid index pattern (clm_023, clm_024), the single-writer constraint and its millisecond tolerance (clm_025, clm_027), and the MVCC escape hatch for true concurrent writes (clm_049). The recommendation directly answers the success-criterion architecture posture with documented operational costs and recovery guarantees. [claim:clm_inf09]
- SQLite docs (clm_025-027) cap concurrent writes at one writer and redirect heavy concurrent writers to client/server engines; PostgreSQL MVCC (clm_049-050) removes read/write lock conflict. Git-as-store inherits the same serialized-write limitation as any single-file model, so the comparative verdict is that DB-first (client/server) wins concurrency while file-first and embedded SQLite are co-located at the lower tier. [claim:clm_inf01]
- Combining the single-writer model (clm_025), the millisecond turn-taking rationale (clm_027), the <100K hits/day guidance (clm_028), the real-world 400K-500K req/day headroom with only 15-20% dynamic (clm_029), and the explicit migration trigger (clm_026) yields a concrete, evidence-grounded threshold band where file-first degrades: when concurrent writers cannot serialize within the millisecond write window. [claim:clm_inf02]
- The content-addressable model (clm_006, clm_031), header+content hashing (clm_008), tree/commit objects referencing child SHAs (clm_009, clm_010), and SHA-named on-disk storage (clm_011) together mean the commit DAG is a Merkle structure: mutating any object changes its name and cascades to ancestors. This is a structurally enforced integrity guarantee, contrasted with DB audit trails (clm_005 CDC / clm_039 Dolt system tables) which record history but do not cryptographically chain it by default. [claim:clm_inf03]
- git-history loads file history into SQLite (clm_018, clm_019), with Git durable and SQLite derived (clm_023), published via Datasette (clm_024). The 300-row example (clm_022) quantifies the storage cost of full version materialization, so the hybrid's main operational cost is index size scaling with versions x items rather than live row count. [claim:clm_inf04]
- Because the SQLite DB is built from the versioned file (clm_018, clm_019, clm_023) and --id reconstructs per-item change history from commits (clm_020), the index is a pure function of the Git history and can always be rebuilt. In DB-first systems the database is the sole copy, so the hybrid uniquely treats the query store as recoverable derived state. [claim:clm_inf05]
- SQLite's 281 TB ceiling vs terabyte-range migration advice (clm_030) shows the practical limit precedes the hard limit. Git's 40-minute quadratic sparse-checkout (clm_042), the 3-4s cone-mode result (clm_043), and the requirement for a non-default performance bundle (clm_044) show large-scale file-first stays usable only with specialized tooling, so degradation is operational rather than capacity-bound. [claim:clm_inf06]
- Obsidian's plain-text, Git-versioned files (clm_012, clm_014) make each note's frontmatter an independently editable, diffable unit; Dolt versions tables with commits as stored procedures and diffs as system tables (clm_037, clm_039), and git-history's six-table item_version schema (clm_021) shows structured stores impose coordinated schema. The comparative conclusion follows from contrasting per-file locality against table-wide coordination. [claim:clm_inf07]
- Obsidian's plain-text, local-first, Git-compatible, building-block model (clm_012, clm_013, clm_014, clm_017) means any file tool works directly, which is exactly the interface an LLM file agent already has. Dolt's stored-procedure writes / system-table reads and MySQL-server requirement (clm_039, clm_038) impose a query-protocol and a live engine, raising the agent-tool and human-edit barrier. [claim:clm_inf08]
- The three-posture taxonomy used throughout the memo is grounded in the source claims that define each store class. Git as a content-addressable file store (clm_006) anchors file-first; PostgreSQL's MVCC client/server model (clm_047) and Dolt's table-versioning model (clm_037) anchor DB-first; and git-history's Git-durable plus SQLite-derived pattern (clm_023) anchors the hybrid. The sentence is a scoping/framing classification, not a substantive trade-off verdict. [claim:clm_inf10]

## Consequences

- On concurrent writes, file-first stores and embedded DBs share the same single-writer ceiling while only client/server engines like PostgreSQL scale: SQLite serializes to one writer at any instant, whereas PostgreSQL's MVCC lets reading never block writing and writing never block reading. [claim:clm_inf01]
- The documented concurrency breakpoint for a file-first / embedded-DB store is reached when writers can no longer queue and take turns within the millisecond-scale write window; below that (e.g. the <100K hits/day or the observed 400K-500K req/day with 15-20% DB-touching dynamic pages on sqlite.org) single-writer file-first is adequate, above it the docs prescribe migrating writes to a client/server engine. [claim:clm_inf02]
- Git content-addressing gives file-first knowledge bases a stronger structural reproducibility and tamper-evidence guarantee than a DB migration/audit trail: every blob, tree, and commit is named by the SHA of its own bytes, so any content change necessarily changes its key and any commit edit changes every descendant SHA, making the history self-verifying rather than dependent on append-only log discipline. [claim:clm_inf03]
- The git-history tool is the canonical instance of the recommended hybrid posture for RF/MeatyWiki — Git/Markdown as durable, diffable truth with a rebuildable SQLite index for querying — and its operational cost is index amplification: it materializes every version of every record (10 versions x 30 items = 300 rows), so the derived store grows with history depth times item count, not with current state. [claim:clm_inf04]
- The derived index in a files-as-truth + rebuildable-DB hybrid is a disposable cache, which yields the strongest recovery guarantee of the three postures: because git-history regenerates the entire SQLite database deterministically from the committed file history, index loss or corruption is recoverable by re-running the build, whereas a DB-first store's lost data has no external source to rebuild from. [claim:clm_inf05]
- File-first query/scale performance does not degrade at a fixed data-size limit but at an operational-tooling threshold: SQLite tolerates up to 281 TB yet the docs still steer terabyte-range workloads to client/server, and Git's own scaling required a bundle (partial clone, sparse-checkout, background maintenance) where a naive quadratic sparse-checkout matcher cost 40 minutes before cone mode cut git status to 3-4 seconds — so the breakpoint is when default tooling stops being viable, not when a capacity ceiling is hit. [claim:clm_inf06]
- For schema evolution, file-first YAML frontmatter and DB-first models trade off the same way as concurrent writes: editing a Markdown file's frontmatter is a local, individually diffable, human-reviewable change versioned per-file by Git, whereas a relational/table-versioned migration (as in Dolt, where commits are stored procedures and diffs are system tables) centralizes and validates the change but couples all rows to one coordinated migration — favoring file-first for incremental, agent-authored field additions and DB-first for enforced structural integrity. [claim:clm_inf07]
- File-first wins decisively on human editability and agent-tool compatibility: Obsidian's plain-text local-first vault is editable by any filesystem-aware tool and versionable with stock Git, and an LLM agent can read, grep, and rewrite a Markdown+YAML note with ordinary file operations, whereas a DB-first store requires the agent to speak SQL/stored-procedure semantics (Dolt exposes writes as stored procedures and reads as system tables) and a running engine. [claim:clm_inf08]
- This memo evaluates three storage postures as LLM-readable knowledge bases for RF/MeatyWiki: file-first (Markdown + Git content-addressable files), DB-first (client/server engines such as PostgreSQL, or table-versioning engines such as Dolt), and a hybrid of files-as-truth with a rebuildable derived index. [claim:clm_inf10]

## Links

- [[claim:clm_014]]
- [[claim:clm_023]]
- [[claim:clm_024]]
- [[claim:clm_025]]
- [[claim:clm_027]]
- [[claim:clm_049]]
- [[claim:clm_006]]
- [[claim:clm_026]]
- [[claim:clm_050]]
- [[claim:clm_028]]
- [[claim:clm_029]]
- [[claim:clm_008]]
- [[claim:clm_009]]
- [[claim:clm_010]]
- [[claim:clm_011]]
- [[claim:clm_031]]
- [[claim:clm_018]]
- [[claim:clm_019]]
- [[claim:clm_022]]
- [[claim:clm_020]]
- [[claim:clm_030]]
- [[claim:clm_042]]
- [[claim:clm_043]]
- [[claim:clm_044]]
- [[claim:clm_012]]
- [[claim:clm_037]]
- [[claim:clm_039]]
- [[claim:clm_021]]
- [[claim:clm_013]]
- [[claim:clm_017]]
- [[claim:clm_038]]
- [[claim:clm_047]]
- [[Research Foundry]]
- [[Agentic Control Plane]]
