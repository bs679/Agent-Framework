# Agent Config Schema — Changelog

## v1 (current) — February 2026

Initial schema release. Defines frontmatter for all 6 per-agent config files:
SOUL, USER, IDENTITY, AGENTS, HEARTBEAT, MEMORY.

**Required sensitive categories (MEMORY.md):**
- `member_data`
- `grievance_details`
- `negotiation_strategy`
- `financial_account_info`
- `executive_session_content`

**Migration guide:** n/a (first version)

---

## Versioning policy

- **Additive changes** (new optional fields): update the schema in-place, no version bump required.
- **Renames or removals of required fields**: bump the version suffix in `$id` (e.g. `v1` → `v2`),
  update `FRONTMATTER_MODELS` in `provisioning/cli/types.py`, and document the migration path here.
- Generated config files carry a `version` field in their frontmatter. Validators are version-agnostic
  unless a field meaning changes incompatibly — in that case, branch the validator on `version`.
