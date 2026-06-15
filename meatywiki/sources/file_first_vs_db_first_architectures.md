---
id: mwb_20260614_file_first_vs_db_first_architectures
evidence_bundle_id: bundle_20260614_intent_research_20260614_what_are_the
target_page: meatywiki/sources/file_first_vs_db_first_architectures.md
writeback_type: source_note
status: written
summary: 'Source note distilled from research run rf_run_20260614_what_are_the_documented_trade_offs:
  52 supported claim(s) across 9 source card(s).'
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
links:
  source_cards:
  - src_20260614_rib037_00
  - src_20260614_rib037_01
  - src_20260614_rib037_02
  - src_20260614_rib037_03
  - src_20260614_rib037_04
  - src_20260614_rib037_05
  - src_20260614_rib037_06
  - src_20260614_rib037_07
  - src_20260614_rib037_08
  related_pages:
  - '[[Research Foundry]]'
  - '[[Agentic Control Plane]]'
approval:
  required: false
  reason: 'personal/public research: auto-approved'
  approved_by: null
---

# File-first vs DB-first architectures for LLM knowledge bases

## Summary

Source note distilled from research run rf_run_20260614_what_are_the_documented_trade_offs: 52 supported claim(s) across 9 source card(s).

## Key claims

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

## Sources

- src_20260614_rib037_00 — Git - Git Internals: Git Objects (Pro Git book, 2nd ed.)
- src_20260614_rib037_01 — Git - hash-function-transition Documentation (SHA-1 to SHA-256)
- src_20260614_rib037_02 — simonw/git-history — Tools for analyzing Git history using SQLite
- src_20260614_rib037_03 — Git for Data | Dolt Docs
- src_20260614_rib037_04 — PostgreSQL 18 Documentation — Chapter 29: Logical Replication
- src_20260614_rib037_05 — About Obsidian — Obsidian Help (local-first plain-text Markdown vault)
- src_20260614_rib037_06 — Appropriate Uses For SQLite
- src_20260614_rib037_07 — PostgreSQL Documentation: Introduction to Multiversion Concurrency Control (MVCC)
- src_20260614_rib037_08 — The Story of Scalar

## Links

- [[Research Foundry]]
- [[Agentic Control Plane]]
