# ADR 002: Ollama Local-First AI Routing, External APIs Only for Non-Sensitive Tasks

- **Status:** Accepted
- **Date:** 2026-07-06

## Context

Every agent capability in AIOS/Pulse is backed by LLM inference — grievance
summaries, email triage, check-ins, minutes, wage costing, contract
proposals, testimony, agendas, research synthesis.

CHCA is a healthcare workers' union. Much of what the agents process is
sensitive by nature: member lists and PII, grievance and discipline details,
dues accounts, executive-session material, and contract negotiation strategy.
`Claude.md` (Hard Rules) states the constraint plainly: sensitive data
"stays on Ollama only, never sent to external APIs," and
`prompts/README.md` repeats it as cross-cutting rule #2 for every build
phase. Sending this data to a third-party API is not a quality tradeoff —
it is a confidentiality breach affecting members and bargaining position.

At the same time, some tasks are public-facing and quality-critical —
legislative testimony, CT General Assembly hearing summaries, board agendas,
BLS/public-data research — where a local 8B model (llama3.1:8b) is
noticeably weaker than frontier hosted models and the content contains no
member data. We therefore need routing enforced in code, not by convention,
with sensitivity a property of the task type rather than a per-call judgment.

## Decision

All AI calls go through a single routing layer, `AIRouter` in
`integrations/ai/router.py`, configured by `config/ai-routing.yaml`
("Single Source of Truth — never hardcode model choices in application
code"). No code calls Ollama, Kimi K2, or Claude directly.

Three model tiers are configured:

- **ollama** — local (`OLLAMA_BASE_URL`, default `http://localhost:11434`,
  model `llama3.1:8b`), always enabled. Primary for all sensitive work.
- **kimi_k2** — `moonshotai/kimi-k2` via the NVIDIA NIM API, disabled by
  default (`KIMI_ENABLED`). Preferred external tier for non-sensitive,
  quality-critical tasks.
- **claude** — `claude-sonnet-4-6` via the Anthropic API, disabled by
  default (`CLAUDE_ENABLED`). External fallback tier.

The routing table in `config/ai-routing.yaml` assigns each task type a
model, a `sensitive` flag, and a fallback:

- **Sensitive tasks route to Ollama with `fallback: null`** — fail rather
  than leak. This covers `grievance_summary`, `email_triage`,
  `checkin_summary`, `minutes_draft` (executive-session risk),
  `wage_costing`, `contract_proposal`, `quick_capture` (unknown content
  defaults safe), `weekly_report_summary`, and `email_thread_summary`.
  If Ollama is down, `AIRouter.complete()` raises `RuntimeError` instead
  of falling back externally.
- **Non-sensitive tasks prefer `kimi_k2` with `fallback: ollama`** —
  `testimony_draft`, `legislative_summary`, `agenda_draft`,
  `bls_research_synthesis`. If the external model is unavailable
  (disabled, missing API key, or errored), the router degrades to Ollama.

Three defense layers back the policy in `router.py`:

1. `sensitive: true` (or the caller passing `force_local=True`) forces the
   target to Ollama before any availability logic runs.
2. A last-resort sanitizer (`_contains_sensitive_data`) scans every
   externally-bound prompt against `_SENSITIVE_PATTERNS` — SSNs, grievance
   case numbers (`#NN-NNN`, `GRV-NNNN`), member IDs, badge numbers, dues
   account references, phone numbers, and emails near grievance/discipline/
   negotiation keywords — and overrides the target to Ollama on any match.
3. Routing decisions are logged (task, target, sensitivity, fallback) but
   prompt content is never logged.

## Consequences

### Positive

- The confidentiality guarantee is mechanical: a misconfigured task, an
  outage, or a developer mistake results in a hard failure or a local
  fallback — never silent external routing of sensitive data.
- `sensitive` classification lives in one reviewable YAML file; adding a
  task type forces an explicit sensitivity decision, and unknown task
  types raise `ValueError`.
- Zero marginal inference cost for the bulk of daily agent work; external
  API keys are optional (both external tiers default to disabled).
- Public-facing outputs (testimony, legislative summaries) still get
  frontier-model quality when keys are configured, with graceful
  degradation to Ollama.

### Negative

- Sensitive-task output quality is capped by local hardware and
  llama3.1:8b — grievance summaries and contract costing get the weakest
  model precisely because they matter most. Mitigation is a bigger local
  model or GPU, never external routing.
- Ollama is a single point of failure for all sensitive tasks by design
  (`fallback: null`); errors direct operators to check
  `curl localhost:11434/api/version`.
- The regex sanitizer is a safety net, not a guarantee — novel PII formats
  can pass. Primary protection remains the per-task `sensitive` flag, with
  `quick_capture` classified default-safe to cover unknown content.
- Two external providers (NVIDIA NIM and Anthropic) mean two key/billing
  relationships, though both are optional.

## Alternatives Considered

1. **External API (Claude) as primary for everything.** Best quality and
   simplest ops, but violates the non-negotiable Hard Rule — member data,
   grievances, and negotiation strategy would transit a third party.
   Rejected outright.
2. **Ollama-only, no external tier.** Maximally safe and simpler, but
   public-facing quality-critical work (testimony, legislative analysis)
   would be permanently limited to an 8B model even though it contains no
   sensitive data. Rejected; instead external tiers default to disabled,
   so this remains the effective posture until keys are provisioned.
3. **Per-call sensitivity decisions by calling code.** Rejected: pushes a
   security-critical judgment to every call site. Task-type routing in
   `config/ai-routing.yaml` centralizes the decision and makes it auditable.
4. **Content-classification-only routing (classifier decides local vs
   external per prompt).** Rejected as the primary mechanism — a classifier
   can misfire, and a false negative leaks data. The pattern scanner is
   retained only as a backstop behind the static task-type policy.
