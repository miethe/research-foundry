Read-only result: credential leak paths exist. No CRITICAL findings found.

**Findings**
1. **HIGH** `src/research_foundry/services/governance.py:201`, `src/research_foundry/services/governance.py:203`, `src/research_foundry/services/agent_job_service.py:600`  
   `redact_payload` redacts dict/list string values, but leaves dict keys untouched and does not walk tuples. Scenario: child emits `{"usage": {"sk-ant-...": 1}}` or `{"args": ("sk-ant-...",)}`; `_safe_write_json` persists the raw credential into `events.jsonl` or artifact JSON.

2. **HIGH** `src/research_foundry/services/governance.py:32`, `src/research_foundry/services/governance.py:227`, `src/research_foundry/services/agent_job_service.py:600`  
   Agent-job writes call `redact_payload(data)` without repo config, so only built-ins apply. Any provider credential shape not in those regexes, or added only in `config/governance.yaml`, bypasses as a plain string. Scenario: a hyphenated/project-style provider key in an event value is written raw.

3. **HIGH** `src/research_foundry/services/agent_job_service.py:396`, `src/research_foundry/services/agent_job_service.py:400`  
   `artifact_id` is used unredacted in the filename before payload redaction. Scenario: child submits `artifact_id="sk-ant-..."`; content may redact, but the artifact path `artifact_sk-ant-....json` leaks the credential via directory listing, backups, and path logs.

4. **HIGH** `src/research_foundry/services/agent_job_service.py:562`  
   Tool exceptions are logged before redaction. Scenario: provider/tool raises `Invalid API key sk-ant-...`; `logger.warning(..., exc)` writes the raw credential to logs, though the returned error payload is redacted.

5. **HIGH** `src/research_foundry/services/agent_job_service.py:249`, `src/research_foundry/services/agent_job_service.py:305`, `src/research_foundry/services/agent_job_service.py:344`, `src/research_foundry/services/agent_job_service.py:617`, `src/research_foundry/services/agent_job_service.py:970`  
   Temp file mode is set before write, and spawn/write exceptions clean up, but unlink is not crash-guaranteed. Scenario: parent or child is SIGKILLed before child unlink/`cleanup_job`; `/tmp/rf_job_<oldpid>_...cred` remains. Reaper only scans current PID files, so a restart misses old-PID credential files. Also the temp path is argv-visible until child unlinks it.

6. **MED** `src/research_foundry/services/telemetry.py:358`, `src/research_foundry/services/telemetry.py:368`  
   HMAC fingerprint is non-reversible assuming a secret pepper and high-entropy key, but pepper handling is unsafe: missing `RF_KEY_PROFILE_PEPPER` silently falls back to a hard-coded interim pepper. Scenario: production env misconfigured; fingerprints become stable/recomputable across installs. No raw key is written to telemetry in the reviewed code.

**Gate Answers**
- Raw escape: yes, into event/artifact files and logs via findings above. No direct raw credential path found into telemetry rows or `subprocess.Popen(env=...)`.
- Temp lifecycle: 0600-before-write yes; unlink-on-parent/child crash no.
- `redact_payload`: incomplete for dict keys, tuple payloads, and nonmatching/config-only credential formats.
- HMAC: construction is HMAC-SHA256 and not a raw prefix hash, but pepper fallback violates safe production handling.

