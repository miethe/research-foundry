---
schema_version: 2
doc_type: design-spec
title: "Agent Job Server Pepper Storage — Decision (Mode-D Gate #4)"
status: accepted
maturity: shaping
created: 2026-07-07
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
mode_d_gate: 4
gate_status: approved
---

# Agent Job Server Pepper Storage — Decision (Mode-D Gate #4)

## Executive Summary

This document records the decision gate for pepper storage in the Research Foundry agent-job telemetry system. The pepper is a server-side cryptographic constant used to compute HMAC fingerprints of provider API keys, enabling correlation and auditing without storing raw credentials.

**Status**: Draft pending sign-off. This decision implements specifications from ADR-002 and requires explicit human approval before deployment.

---

## Context and Background

### What is the Pepper?

The pepper is a server-side constant used in `services/telemetry.py::make_key_fingerprint()` to compute a 12-hex-char HMAC-SHA256 fingerprint from provider API keys:

```python
def make_key_fingerprint(key: str, pepper: str) -> str:
    """
    Generate a deterministic fingerprint of an API key using pepper.
    
    Returns a 12-hex-char identifier for correlation without exposing raw key.
    """
    hmac_obj = hmac.new(
        pepper.encode(),
        key.encode(),
        hashlib.sha256
    )
    return hmac_obj.hexdigest()[:12]
```

### Why It Matters

1. **Correlation**: Multiple agent runs using the same provider key produce the same fingerprint, enabling audit trails and duplicate detection.
2. **Security**: Raw API keys are never stored; only fingerprints are recorded in run telemetry and writebacks.
3. **Operational**: Pepper rotation enables key fingerprint invalidation without code changes.

### Scope of This Decision

This gate addresses **where and how the pepper is stored at runtime**. It does NOT:
- Re-litigate whether peppers should exist (ADR-002 decision)
- Define pepper generation or rotation procedures (P5 follow-up)
- Set security clearance policies or access controls (P5 RBAC)

---

## Options Evaluated

### Option A: Environment Variable / foundry.yaml Key-Profile (RECOMMENDED)

#### Implementation

The pepper value is stored as a `key_profiles` entry in `foundry.yaml`:

```yaml
key_profiles:
  default:
    provider: local
  pepper:
    provider: local
    value: "{{ env.RF_PEPPER }}"
```

At startup, `rf serve` reads the pepper from foundry.yaml (which resolves the env var):

```python
config = FoundryConfig.load()
pepper = config.key_profiles['pepper']['value']
telemetry_svc = TelemetryService(pepper=pepper)
```

#### Advantages

- **Simple**: Integrates cleanly with existing foundry.yaml key-profile pattern
- **Auditable**: Config file is versioned; pepper references are explicit
- **No dependencies**: Uses existing config machinery
- **Familiar**: Consistent with how other secrets are managed in foundry.yaml

#### Disadvantages

- **Process visibility**: Pepper may appear in `ps` output or process inspection
- **No rotation without restart**: Changing pepper requires restarting `rf serve`
- **Single-operator only**: Assumes loopback-only deployment before P5

#### Security Posture

Acceptable for **pre-P5 single-operator / loopback-only deployment**. Assumes:
- Only trusted operators access the server
- Environment and process inspection is not a threat model
- Pepper rotation is rare (e.g., quarterly or after suspected compromise)

---

### Option B: OS Keyring (Deferred Follow-Up)

#### Implementation

Store pepper in system keyring (via `keyring` library), read at startup:

```python
import keyring

def get_pepper_from_keyring() -> str:
    pepper = keyring.get_password("research-foundry", "agent-job-pepper")
    if not pepper:
        raise RuntimeError("Pepper not found in keyring. Run: keyring set research-foundry agent-job-pepper")
    return pepper

pepper = get_pepper_from_keyring()
telemetry_svc = TelemetryService(pepper=pepper)
```

Fallback to env var if keyring is unavailable (e.g., headless servers):

```python
def get_pepper() -> str:
    try:
        return get_pepper_from_keyring()
    except RuntimeError:
        return os.environ["RF_PEPPER"]
```

#### Advantages

- **OS-level protection**: Keyring enforces access control at OS level
- **Process-invisible**: Pepper does not leak into process inspection
- **Rotation-friendly**: Can rotate without restart (keyring update → next read)
- **Production-ready**: Standard practice for multi-tenant systems

#### Disadvantages

- **Additional dependency**: Requires `keyring` library (minimal but adds complexity)
- **Environment-specific**: Not all systems have keyrings (e.g., some headless/container deploys)
- **Complexity**: Adds setup steps for deployment (keyring initialization)
- **P5 blocker**: Upgrade post-P5.2 when `/agents` is exposed beyond loopback

#### Security Posture

**Preferred for multi-user / public deployment (post-P5)**. Aligns with zero-trust assumptions when the agent-job surface is exposed beyond loopback.

---

### Option C: Dedicated Secrets File (0600)

#### Implementation

Store pepper in a dedicated file with mode 0600:

```python
def get_pepper_from_file(pepper_file_path: str) -> str:
    if not os.path.exists(pepper_file_path):
        raise FileNotFoundError(f"Pepper file not found: {pepper_file_path}")
    
    stat_info = os.stat(pepper_file_path)
    if stat_info.st_mode & 0o077:  # Check world/group readability
        raise PermissionError(f"Pepper file has insecure permissions: {oct(stat_info.st_mode)}")
    
    with open(pepper_file_path, 'r') as f:
        return f.read().strip()

pepper = get_pepper_from_file("/etc/research-foundry/pepper")
telemetry_svc = TelemetryService(pepper=pepper)
```

Path is specified in foundry.yaml:

```yaml
telemetry:
  pepper_file: /etc/research-foundry/pepper
```

#### Advantages

- **Explicit control**: File ownership and permissions are visible and auditable
- **No additional dependencies**: Pure filesystem
- **Simple**: Straightforward read at startup

#### Disadvantages

- **Manual permissions management**: Operator must maintain 0600 permissions across deploys
- **Rotation still requires restart**: Changing pepper still requires `rf serve` restart
- **Setup complexity**: Requires filesystem setup outside foundry.yaml
- **No access control**: File access relies on OS permissions alone

#### Security Posture

Equivalent to **Option A** with explicit file-based isolation. Better for auditing but more operational overhead. Not recommended for this phase.

---

## Recommendation

### Immediate Deployment (Pre-P5): **Option A**

**Option A (Environment Variable / foundry.yaml)** is recommended for initial pre-P5 deployment because:

1. **Operational simplicity**: Integrates seamlessly with existing foundry.yaml key-profile pattern
2. **Adequate security posture**: Loopback-only + single-operator deployment assumes low threat model
3. **No scope creep**: Avoids pulling in OS keyring dependency before P5 requirement
4. **Immediate unblocking**: Allows agent-job telemetry to ship on schedule

**Implementation checklist**:
- Add `key_profiles.pepper` entry to foundry.yaml documentation
- Default to `RF_PEPPER` env var (not checked into git)
- Document pepper initialization in setup guide
- Add rotation procedure to runbook

### Post-P5.2: **Option B**

**Option B (OS Keyring)** becomes the required implementation when:
- The `/agents` endpoint is exposed beyond loopback (post-P5.2 RBAC gate)
- Multi-operator scenarios are enabled (P5.3 workspace isolation)
- Zero-trust threat model applies

**Migration path**:
- P5.1: Implement Option B with fallback to env var (non-breaking)
- P5.2: After RBAC is live, default to keyring (env var fallback retained for headless environments)
- P5.3: Post-workspace isolation, evaluate removing env var fallback

---

## Sign-Off Block (Gate #4)

**CRITICAL**: This block must remain empty. The operator provides explicit sign-off.

```
### Mode-D Gate #4 Sign-Off

Approver: nick
Date: 2026-07-07
Decision: Option A approved for pre-P5 loopback-only deployment; Option B (OS keyring)
  required before any non-loopback / public exposure.
Notes: Missing RF_KEY_PROFILE_PEPPER must log a loud startup WARNING (implemented in
  telemetry.make_key_fingerprint); fail-closed enforcement is deferred to P5. This
  also resolves the Codex adversarial-firewall-review MED finding #6 (silent interim-
  pepper fallback). Reviewed against the three evaluated options in this doc.
```

---

## Post-Sign-Off Next Steps

### Immediate (After Sign-Off)

1. **Document configuration example**
   - Update `docs/development/setup-guides/agent-job-setup.md`
   - Add section: "Configuring the Telemetry Pepper"
   - Provide example foundry.yaml snippet

2. **Update implementation**
   - Ensure `foundry.yaml` loader handles `key_profiles.pepper` entry
   - Add validation: pepper length >= 16 chars, alphanumeric + symbol
   - Log pepper presence at startup (not value): `"Telemetry pepper loaded (length: {len})"`

3. **Testing**
   - Unit test: `make_key_fingerprint()` produces consistent output
   - Integration test: Agent-job records correct fingerprint in run telemetry
   - Deployment test: `rf serve` starts with pepper configured

### Before Non-Loopback Exposure (P5.2+)

1. **Evaluate Option B**
   - Prototype keyring integration
   - Test on supported platforms (Linux/macOS/Windows)
   - Plan migration from env var

2. **Security review**
   - Audit pepper usage across codebase
   - Verify no raw keys are logged
   - Validate fingerprint collision resistance

### Operational Procedures

**Pepper Rotation** (e.g., after suspected compromise):
1. Generate new pepper value (32+ random bytes, hex-encoded)
2. Update `RF_PEPPER` env var
3. Restart `rf serve`
4. Old fingerprints remain valid; new runs use new fingerprint

**Deployment Checklist**:
- [ ] `RF_PEPPER` set in deployment environment
- [ ] Pepper length >= 16 chars
- [ ] `rf serve` starts without errors
- [ ] First agent run produces valid 12-hex-char fingerprint

---

## Appendix: Related Documents

- **ADR-002**: Pepper cryptography and fingerprint design (decision already approved)
- **PEP-P4-agents-v1**: Public multi-user P4 agents feature PRD
- **Agent Job Implementation Plan**: Detailed implementation timeline

